"""Codebase Explorer MCP Server -- FastMCP entry point with 7 tools (V2).

V2 Architecture:
- No SQLite (replaced with JSON state file)
- No Jinja2 templates (docs written by LLM agents)
- 7 streamlined tools (down from 15 in V1)
- Feature Cone based grouping (replaces Louvain as primary)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from src.budget.estimator import estimate_tokens_from_chars
from src.doc.depth_planner import calculate_feature_cone_depth, build_task_manifest
from src.doc.mermaid import MermaidGenerator
from src.graph.dependency import get_module_dependency_subgraph
from src.graph.feature_cone import extract_feature_cones, FeatureCone
from src.graph.ordering import topological_order
from src.graph.weighted_graph import build_weighted_dependency_graph
from src.parser.codebase import CodebaseParser, CodebaseParseError
from src.state.json_store import atomic_write_state, read_state, update_task_status

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type Aliases
# ---------------------------------------------------------------------------

_Str = Annotated[str | None, Field(description="Project ID. None = latest.")]

# ---------------------------------------------------------------------------
# FastMCP Server Setup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(server: FastMCP):
    """Initialize parser for the server lifespan."""
    parser = CodebaseParser()
    try:
        yield {"parser": parser}
    finally:
        pass


mcp = FastMCP(
    "codebase-explorer",
    instructions="Codebase analysis server with feature-cone grouping and token-aware task planning.",
    lifespan=_lifespan,
)

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _lc(ctx):
    """Get lifespan context."""
    return ctx.request_context.lifespan_context


def _parser(ctx) -> CodebaseParser:
    """Get parser from context."""
    return _lc(ctx)["parser"]


def _now() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(UTC).isoformat()


def _project_id_from_path(path: str) -> str:
    """Generate deterministic project ID from path."""
    return hashlib.sha256(path.encode()).hexdigest()[:12]


def _find_latest_project_dir() -> Path | None:
    """Find the most recently modified .codebase-analysis directory."""
    # Search in common locations
    search_paths = [Path.cwd(), Path.home()]

    candidates = []
    for base in search_paths:
        if not base.exists():
            continue
        for p in base.rglob(".codebase-analysis"):
            if p.is_dir() and (p / "state.json").exists():
                candidates.append(p)

    if not candidates:
        return None

    # Return most recently modified
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _resolve_output_dir(path: str, output_dir: str | None) -> Path:
    """Resolve output directory for analysis results."""
    if output_dir:
        return Path(output_dir).resolve()
    return Path(path).resolve() / ".codebase-analysis"


def _validate_json_files_exist(output_dir: Path) -> bool:
    """Check if all required JSON files exist."""
    required = [
        "01_structure.json",
        "02_dag.json",
        "03_feature_cones.json",
        "04_file_tokens.json",
        "05_task_manifest.json",
    ]
    return all((output_dir / f).exists() for f in required)


# ---------------------------------------------------------------------------
# Tool 1: analyze_codebase
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": False, "idempotentHint": True})
async def analyze_codebase(
    path: Annotated[str, Field(description="Absolute path to the codebase root")],
    languages: Annotated[
        list[Literal["python", "typescript", "javascript"]] | None,
        Field(description="Languages to analyze. None = auto-detect."),
    ] = None,
    output_dir: Annotated[
        str | None,
        Field(description="Output directory for JSON files. None = {path}/.codebase-analysis/"),
    ] = None,
    force_reindex: Annotated[
        bool, Field(description="Force reindex even if cache exists.")
    ] = False,
    ctx: Context = None,
) -> dict:
    """Run complete analysis pipeline and generate 5 JSON files + state.json.

    This is the main entry point that replaces V1's index_codebase + create_analysis_plan.
    Performs purely deterministic analysis (no LLM calls).

    Pipeline:
      1. Parse codebase → CodebaseSnapshot
      2. Build weighted dependency graph → nx.DiGraph
      3. Extract feature cones via SCC + DAG analysis
      4. Estimate tokens per file (chars ÷ 4)
      5. Build task manifest (greedy bin packing)
      6. Write 5 JSON files + state.json

    Returns:
        Project metadata and paths to all generated files.
    """
    resolved_path = Path(path).resolve()
    if not resolved_path.is_dir():
        raise ToolError(f"Not a directory: {path}")

    output_path = _resolve_output_dir(str(resolved_path), output_dir)
    project_id = _project_id_from_path(str(resolved_path))

    # Check cache
    if not force_reindex and _validate_json_files_exist(output_path):
        logger.info(f"[analyze_codebase] Cache hit for {resolved_path}")
        return {
            "status": "success",
            "project_id": project_id,
            "output_dir": str(output_path),
            "cached": True,
            "message": "Using cached analysis results",
            "files": {
                "01_structure": str(output_path / "01_structure.json"),
                "02_dag": str(output_path / "02_dag.json"),
                "03_feature_cones": str(output_path / "03_feature_cones.json"),
                "04_file_tokens": str(output_path / "04_file_tokens.json"),
                "05_task_manifest": str(output_path / "05_task_manifest.json"),
            },
            "state_file": str(output_path / "state.json"),
        }

    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)

    # Step 1: Parse codebase
    logger.info(f"[analyze_codebase] Parsing {resolved_path}...")
    try:
        snapshot = _parser(ctx).parse(str(resolved_path), languages=languages)
    except CodebaseParseError as e:
        raise ToolError(str(e)) from e

    # Step 2: Build weighted dependency graph
    logger.info("[analyze_codebase] Building weighted dependency graph...")
    weighted_result = build_weighted_dependency_graph(snapshot)
    graph = weighted_result.graph

    # Step 3: Extract feature cones
    logger.info("[analyze_codebase] Extracting feature cones...")
    cones, infrastructure = extract_feature_cones(graph, snapshot)
    logger.info(
        f"[analyze_codebase] Found {len(cones)} cones, {len(infrastructure)} infrastructure files"
    )

    # Step 4: Estimate tokens per file
    logger.info("[analyze_codebase] Estimating tokens...")
    file_tokens = {}
    file_details = []
    for file_info in snapshot.files:
        lang = file_info.language or "default"
        estimate = estimate_tokens_from_chars(file_info.char_count, lang)
        file_tokens[file_info.filepath] = estimate.source_tokens
        file_details.append(
            {
                "filepath": file_info.filepath,
                "language": lang,
                "char_count": file_info.char_count,
                "line_count": file_info.line_count,
                "estimated_tokens": estimate.source_tokens,
                "method": estimate.method,
            }
        )

    # Step 5: Build DAG layers and task manifest
    logger.info("[analyze_codebase] Building task manifest...")
    cone_dicts = {}
    for cone_id, cone in cones.items():
        cone_tokens = sum(file_tokens.get(f, 0) for f in cone.exclusive_files)
        cone_dicts[cone_id] = {
            "cone_id": cone_id,
            "entry_point": cone.entry_point,
            "exclusive_files": cone.exclusive_files,
            "shared_deps": cone.shared_deps,
            "layer": cone.layer,
            "token_count": cone_tokens,
        }

    task_manifest = build_task_manifest(cone_dicts, file_tokens)

    # Step 6: Write JSON files
    # 01_structure.json
    structure_data = {
        "project_id": project_id,
        "path": str(resolved_path),
        "analyzed_at": _now(),
        "languages": list(snapshot.languages_detected),
        "file_count": len(snapshot.files),
        "function_count": len(snapshot.functions),
        "class_count": len(snapshot.classes),
        "total_lines": snapshot.total_lines,
        "files": [
            {
                "filepath": f.filepath,
                "language": f.language,
                "line_count": f.line_count,
                "char_count": f.char_count,
                "function_names": f.function_names,
                "class_names": f.class_names,
                "import_sources": f.import_sources,
            }
            for f in snapshot.files
        ],
    }
    (output_path / "01_structure.json").write_text(
        json.dumps(structure_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 02_dag.json
    dag_data = {
        "project_id": project_id,
        "node_count": weighted_result.node_count,
        "edge_count": weighted_result.edge_count,
        "total_weight": weighted_result.total_weight,
        "nodes": list(graph.nodes()),
        "edges": [
            {"source": u, "target": v, "weight": graph[u][v].get("weight", 1)}
            for u, v in graph.edges()
        ],
    }
    (output_path / "02_dag.json").write_text(
        json.dumps(dag_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 03_feature_cones.json
    cones_data = {
        "project_id": project_id,
        "cone_count": len(cones),
        "infrastructure_files": list(infrastructure),
        "cones": cone_dicts,
    }
    (output_path / "03_feature_cones.json").write_text(
        json.dumps(cones_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 04_file_tokens.json
    tokens_data = {
        "project_id": project_id,
        "total_tokens": sum(file_tokens.values()),
        "file_count": len(file_tokens),
        "files": file_details,
    }
    (output_path / "04_file_tokens.json").write_text(
        json.dumps(tokens_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 05_task_manifest.json
    (output_path / "05_task_manifest.json").write_text(
        json.dumps(task_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # state.json
    state = {
        "project_id": project_id,
        "path": str(resolved_path),
        "created_at": _now(),
        "status": "analysis_complete",
        "tasks": {
            task_id: {
                "status": "pending",
                "created_at": _now(),
                "output_files": [],
            }
            for task_id in task_manifest.get("tasks", {})
        },
        "documentation": {
            "output_dir": str(output_path),
            "index_written": False,
            "details_written": 0,
            "snippets_written": 0,
            "total_planned": len(task_manifest.get("tasks", {})),
            "source_files_covered": [],
            "source_file_coverage_percent": 0.0,
        },
    }
    atomic_write_state(output_path / "state.json", state)

    logger.info(f"[analyze_codebase] Analysis complete. Output: {output_path}")

    return {
        "status": "success",
        "project_id": project_id,
        "output_dir": str(output_path),
        "files_analyzed": len(snapshot.files),
        "feature_cones_found": len(cones),
        "task_count": len(task_manifest.get("tasks", {})),
        "total_tokens": sum(file_tokens.values()),
        "files": {
            "01_structure": str(output_path / "01_structure.json"),
            "02_dag": str(output_path / "02_dag.json"),
            "03_feature_cones": str(output_path / "03_feature_cones.json"),
            "04_file_tokens": str(output_path / "04_file_tokens.json"),
            "05_task_manifest": str(output_path / "05_task_manifest.json"),
        },
        "state_file": str(output_path / "state.json"),
    }


# ---------------------------------------------------------------------------
# Tool 2: get_structure
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
async def get_structure(
    module: Annotated[str | None, Field(description="Module/cone name")] = None,
    file: Annotated[str | None, Field(description="File path")] = None,
    function: Annotated[str | None, Field(description="Function name")] = None,
) -> dict:
    """Query code structure from 01_structure.json.

    Three mutually exclusive query modes:
    - module: Get all files in a cone/module
    - file: Get detailed info for a single file
    - function: Get function signature and dependencies
    - None: Return project summary
    """
    # Find the latest project directory
    project_dir = _find_latest_project_dir()
    if not project_dir:
        raise ToolError("No project found. Run analyze_codebase first.")

    structure_path = project_dir / "01_structure.json"
    if not structure_path.exists():
        raise ToolError(f"Structure file not found: {structure_path}")

    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    files = structure.get("files", [])

    # Mode: Summary
    if not any([module, file, function]):
        language_breakdown = {}
        for f in files:
            lang = f.get("language", "unknown")
            language_breakdown[lang] = language_breakdown.get(lang, 0) + 1

        # Find most imported files
        import_counts = {}
        for f in files:
            for imp in f.get("import_sources", []):
                import_counts[imp] = import_counts.get(imp, 0) + 1
        most_imported = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "status": "success",
            "query_type": "summary",
            "file_count": structure.get("file_count", 0),
            "function_count": structure.get("function_count", 0),
            "class_count": structure.get("class_count", 0),
            "language_breakdown": language_breakdown,
            "most_imported_files": [
                {"filepath": fp, "import_count": cnt} for fp, cnt in most_imported
            ],
        }

    # Mode: Module/Cone query
    if module:
        # Load feature cones to get files in the module
        cones_path = project_dir / "03_feature_cones.json"
        if not cones_path.exists():
            raise ToolError("Feature cones file not found")

        cones_data = json.loads(cones_path.read_text(encoding="utf-8"))
        cone = cones_data.get("cones", {}).get(module)
        if not cone:
            raise ToolError(f"Module/cone '{module}' not found")

        module_files = [
            f for f in files if f["filepath"] in cone.get("exclusive_files", [])
        ]

        return {
            "status": "success",
            "query_type": "module",
            "module_name": module,
            "files": module_files,
            "file_count": len(module_files),
            "total_functions": sum(len(f.get("function_names", [])) for f in module_files),
            "total_classes": sum(len(f.get("class_names", [])) for f in module_files),
        }

    # Mode: File query
    if file:
        file_info = next((f for f in files if f["filepath"] == file), None)
        if not file_info:
            raise ToolError(f"File not found: {file}")

        # Build reverse index (imported_by)
        imported_by = []
        for f in files:
            if file in f.get("import_sources", []):
                imported_by.append(f["filepath"])

        return {
            "status": "success",
            "query_type": "file",
            "filepath": file_info["filepath"],
            "language": file_info.get("language", "unknown"),
            "line_count": file_info.get("line_count", 0),
            "functions": [
                {
                    "name": fn,
                    # Note: function details not available in structure.json
                    # Would need to parse functions array from snapshot
                }
                for fn in file_info.get("function_names", [])
            ],
            "classes": [
                {"name": cn} for cn in file_info.get("class_names", [])
            ],
            "import_sources": file_info.get("import_sources", []),
            "imported_by": imported_by,
        }

    # Mode: Function query
    if function:
        matches = []
        for f in files:
            if function in f.get("function_names", []):
                matches.append(
                    {
                        "filepath": f["filepath"],
                        # Note: line_start, line_end, calls not available in structure.json
                    }
                )

        if not matches:
            raise ToolError(f"Function '{function}' not found")

        return {
            "status": "success",
            "query_type": "function",
            "function_name": function,
            "matches": matches,
        }

    # Should not reach here
    raise ToolError("Invalid query parameters")


# ---------------------------------------------------------------------------
# Tool 3: get_feature_cones
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
async def get_feature_cones(
    cone_id: Annotated[str | None, Field(description="Cone ID. None = all cones.")] = None,
) -> dict:
    """Query feature cones from 03_feature_cones.json.

    A feature cone represents a cohesive feature unit containing
    all files from entry point to implementation.
    """
    project_dir = _find_latest_project_dir()
    if not project_dir:
        raise ToolError("No project found. Run analyze_codebase first.")

    cones_path = project_dir / "03_feature_cones.json"
    if not cones_path.exists():
        raise ToolError(f"Feature cones file not found: {cones_path}")

    cones_data = json.loads(cones_path.read_text(encoding="utf-8"))
    cones = cones_data.get("cones", {})

    # Return summary list
    if not cone_id:
        summaries = [
            {
                "cone_id": cid,
                "name": c.get("entry_point", cid),
                "entry_file": c.get("entry_point", ""),
                "is_utility": False,  # TODO: determine from layer or naming
                "file_count": len(c.get("exclusive_files", [])),
                "total_tokens": c.get("token_count", 0),
                "layer": c.get("layer", 0),
            }
            for cid, c in cones.items()
        ]

        return {
            "status": "success",
            "total_cones": len(cones),
            "cones": summaries,
        }

    # Return specific cone details
    cone = cones.get(cone_id)
    if not cone:
        raise ToolError(f"Cone '{cone_id}' not found")

    # TODO: Add layer breakdown (would need to compute from DAG)
    # TODO: Add depends_on_cones (would need cross-cone dependency analysis)

    return {
        "status": "success",
        "cone_id": cone_id,
        "name": cone.get("entry_point", cone_id),
        "entry_file": cone.get("entry_point", ""),
        "is_utility": False,
        "file_count": len(cone.get("exclusive_files", [])),
        "total_tokens": cone.get("token_count", 0),
        "layer": cone.get("layer", 0),
        "files": cone.get("exclusive_files", []),
        "layers": [],  # TODO: implement layer breakdown
        "shared_deps": cone.get("shared_deps", []),
        "depends_on_cones": [],  # TODO: implement
    }


# ---------------------------------------------------------------------------
# Tool 4: get_dependency_graph
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
async def get_dependency_graph(
    scope: Annotated[
        Literal["project", "cone", "file"],
        Field(description="Scope: 'project', 'cone', or 'file'"),
    ] = "project",
    target: Annotated[
        str | None,
        Field(description="Cone ID or file path (required for scope=cone/file)"),
    ] = None,
    include_weights: Annotated[
        bool, Field(description="Include edge weights in diagram")
    ] = False,
) -> dict:
    """Generate Mermaid dependency graph from 02_dag.json.

    Scopes:
    - project: Cone-level dependency graph
    - cone: File-level graph within a cone
    - file: Direct dependencies of a single file
    """
    project_dir = _find_latest_project_dir()
    if not project_dir:
        raise ToolError("No project found. Run analyze_codebase first.")

    dag_path = project_dir / "02_dag.json"
    if not dag_path.exists():
        raise ToolError(f"DAG file not found: {dag_path}")

    dag_data = json.loads(dag_path.read_text(encoding="utf-8"))

    # TODO: Implement actual Mermaid graph generation
    # This is a placeholder that returns basic graph info

    return {
        "status": "success",
        "scope": scope,
        "target": target,
        "mermaid_graph": f"graph TD\n    %% Placeholder for {scope} graph\n",
        "node_count": dag_data.get("node_count", 0),
        "edge_count": dag_data.get("edge_count", 0),
        "circular_deps": [],  # TODO: extract from SCC analysis
    }


# ---------------------------------------------------------------------------
# Tool 5: get_progress
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
async def get_progress(
    project_id: Annotated[
        str | None, Field(description="Project ID. None = latest project.")
    ] = None,
) -> dict:
    """Query task completion status from state.json."""
    project_dir = _find_latest_project_dir()
    if not project_dir:
        raise ToolError("No project found. Run analyze_codebase first.")

    state_path = project_dir / "state.json"
    if not state_path.exists():
        raise ToolError(f"State file not found: {state_path}")

    state = read_state(state_path)
    if not state:
        raise ToolError("Failed to read state file")

    tasks = state.get("tasks", {})
    total = len(tasks)
    pending = sum(1 for t in tasks.values() if t.get("status") == "pending")
    in_progress = sum(1 for t in tasks.values() if t.get("status") == "in_progress")
    complete = sum(1 for t in tasks.values() if t.get("status") == "complete")
    failed = sum(1 for t in tasks.values() if t.get("status") == "failed")

    progress_percent = (complete / total * 100) if total > 0 else 0.0

    next_pending = [
        tid for tid, t in tasks.items() if t.get("status") == "pending"
    ][:10]  # Limit to 10

    doc_info = state.get("documentation", {})

    return {
        "status": "success",
        "project_id": state.get("project_id"),
        "tasks": {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "complete": complete,
            "failed": failed,
            "progress_percent": round(progress_percent, 2),
        },
        "documentation": {
            "output_dir": doc_info.get("output_dir", ""),
            "index_written": doc_info.get("index_written", False),
            "details_written": doc_info.get("details_written", 0),
            "snippets_written": doc_info.get("snippets_written", 0),
            "total_planned": doc_info.get("total_planned", 0),
            "source_file_coverage_percent": doc_info.get(
                "source_file_coverage_percent", 0.0
            ),
        },
        "next_pending_tasks": next_pending,
    }


# ---------------------------------------------------------------------------
# Tool 6: get_file_tokens
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
async def get_file_tokens(
    file: Annotated[str | None, Field(description="File path. None = all files.")] = None,
    module: Annotated[
        str | None, Field(description="Module/cone ID. None = all modules.")
    ] = None,
) -> dict:
    """Query file token estimates from 04_file_tokens.json."""
    project_dir = _find_latest_project_dir()
    if not project_dir:
        raise ToolError("No project found. Run analyze_codebase first.")

    tokens_path = project_dir / "04_file_tokens.json"
    if not tokens_path.exists():
        raise ToolError(f"Tokens file not found: {tokens_path}")

    tokens_data = json.loads(tokens_path.read_text(encoding="utf-8"))
    files = tokens_data.get("files", [])

    # Mode: All files
    if not file and not module:
        return {
            "status": "success",
            "total_tokens": tokens_data.get("total_tokens", 0),
            "file_count": tokens_data.get("file_count", 0),
            "files": files,
        }

    # Mode: Single file
    if file:
        file_info = next((f for f in files if f["filepath"] == file), None)
        if not file_info:
            raise ToolError(f"File not found: {file}")

        return {
            "status": "success",
            "filepath": file_info["filepath"],
            "language": file_info.get("language", "unknown"),
            "char_count": file_info.get("char_count", 0),
            "line_count": file_info.get("line_count", 0),
            "estimated_tokens": file_info.get("estimated_tokens", 0),
            "method": file_info.get("method", "unknown"),
            "cone_id": file_info.get("cone_id"),
        }

    # Mode: Module/Cone
    if module:
        # Load cone data to get files
        cones_path = project_dir / "03_feature_cones.json"
        if not cones_path.exists():
            raise ToolError("Feature cones file not found")

        cones_data = json.loads(cones_path.read_text(encoding="utf-8"))
        cone = cones_data.get("cones", {}).get(module)
        if not cone:
            raise ToolError(f"Module/cone '{module}' not found")

        cone_files = [
            f
            for f in files
            if f["filepath"] in cone.get("exclusive_files", [])
        ]

        total = sum(f.get("estimated_tokens", 0) for f in cone_files)
        max_tokens = max((f.get("estimated_tokens", 0) for f in cone_files), default=0)

        return {
            "status": "success",
            "cone_id": module,
            "file_count": len(cone_files),
            "total_tokens": total,
            "avg_tokens_per_file": (total / len(cone_files)) if cone_files else 0.0,
            "max_file_tokens": max_tokens,
            "files": cone_files,
        }

    raise ToolError("Invalid query parameters")


# ---------------------------------------------------------------------------
# Tool 7: submit_analysis
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": False})
async def submit_analysis(
    task_id: Annotated[str, Field(description="Task ID from task_manifest")],
    detail_paths: Annotated[
        list[str], Field(description="Paths to written DETAIL.md files")
    ],
    snippet_paths: Annotated[
        list[str], Field(description="Paths to written SNIPPET.md files")
    ],
    tokens_used: Annotated[int, Field(description="Tokens consumed")],
    source_files_covered: Annotated[
        list[str] | None,
        Field(description="Source files covered by this analysis"),
    ] = None,
    project_id: Annotated[
        str | None, Field(description="Project ID. None = latest.")
    ] = None,
) -> dict:
    """Submit analysis completion and update state.json.

    Called by DETAIL Agent after writing documentation files.
    Atomically updates task status and coverage metrics.
    """
    project_dir = _find_latest_project_dir()
    if not project_dir:
        raise ToolError("No project found. Run analyze_codebase first.")

    state_path = project_dir / "state.json"

    # Verify files exist
    for path in detail_paths + snippet_paths:
        if not Path(path).exists():
            raise ToolError(f"File not found: {path}")

    # Update task status
    output_files = [
        {"path": p, "type": "detail", "status": "complete"}
        for p in detail_paths
    ] + [
        {"path": p, "type": "snippet", "status": "complete"}
        for p in snippet_paths
    ]

    state = update_task_status(
        state_path,
        task_id,
        status="complete",
        output_files=output_files,
    )

    # Update documentation metrics
    doc = state.get("documentation", {})
    doc["details_written"] = doc.get("details_written", 0) + len(detail_paths)
    doc["snippets_written"] = doc.get("snippets_written", 0) + len(snippet_paths)

    if source_files_covered:
        existing = set(doc.get("source_files_covered", []))
        existing.update(source_files_covered)
        doc["source_files_covered"] = list(existing)

        # Recalculate coverage
        structure_path = project_dir / "01_structure.json"
        if structure_path.exists():
            structure = json.loads(structure_path.read_text(encoding="utf-8"))
            total_files = structure.get("file_count", 0)
            if total_files > 0:
                doc["source_file_coverage_percent"] = (
                    len(existing) / total_files * 100
                )

    state["documentation"] = doc
    atomic_write_state(state_path, state)

    # Calculate remaining tasks
    tasks = state.get("tasks", {})
    remaining = sum(
        1
        for t in tasks.values()
        if t.get("status") in ("pending", "in_progress")
    )
    complete = sum(1 for t in tasks.values() if t.get("status") == "complete")
    total = len(tasks)
    progress = (complete / total * 100) if total > 0 else 0.0

    return {
        "status": "success",
        "task_id": task_id,
        "tasks_remaining": remaining,
        "progress_percent": round(progress, 2),
        "source_file_coverage_percent": doc.get("source_file_coverage_percent", 0.0),
    }


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
