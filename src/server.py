"""Codebase Explorer MCP Server -- FastMCP entry point with 7 tools (V2).

V2 Architecture:
- No SQLite (replaced with JSON state file)
- No Jinja2 templates (docs written by LLM agents)
- 7 streamlined tools (down from 15 in V1)
- Feature Cone based grouping (replaces Louvain as primary)
"""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

import networkx as nx

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from src.budget.estimator import estimate_tokens_from_chars
from src.doc.depth_planner import build_task_manifest
from src.graph.feature_cone import extract_feature_cones, FeatureCone
from src.graph.strategies import list_strategies
from src.graph.weighted_graph import build_weighted_dependency_graph
from src.parser.codebase import CodebaseParser, CodebaseParseError
from src.server_helpers import (
    build_graph_from_dag,
    compute_cone_layers,
    compute_depends_on_cones,
    find_latest_project_dir,
    is_utility_cone,
    now_iso,
    project_id_from_path,
    render_mermaid,
    resolve_output_dir,
    validate_json_files_exist,
    write_analysis_outputs,
)
from src.state.json_store import atomic_write_state, read_state, update_task_status

logger = logging.getLogger(__name__)

MAX_HOPS = 5
"""Maximum number of hops for file-scope dependency graph traversal."""

# ---------------------------------------------------------------------------
# FastMCP Server Setup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(server: FastMCP):
    """Initialize parser for the server lifespan."""
    parser = CodebaseParser()
    yield {"parser": parser}


mcp = FastMCP(
    "codebase-explorer",
    instructions="Codebase analysis server with feature-cone grouping and token-aware task planning.",
    lifespan=_lifespan,
)

# ---------------------------------------------------------------------------
# Context Helpers
# ---------------------------------------------------------------------------


def _lc(ctx):
    """Get lifespan context."""
    return ctx.request_context.lifespan_context


def _parser(ctx) -> CodebaseParser:
    """Get parser from context."""
    return _lc(ctx)["parser"]


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

    output_path = resolve_output_dir(str(resolved_path), output_dir)
    project_id = project_id_from_path(str(resolved_path))

    # Check cache
    if not force_reindex and validate_json_files_exist(output_path):
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

    # Step 3b: DAG layer calculation via SCC condensation + topological ordering
    # First: compute file-level layers using SCC condensation on the full graph
    condensed = nx.condensation(graph)
    file_layer: dict[str, int] = {}
    # Kahn-style layer assignment on condensed DAG
    remaining = set(condensed.nodes())
    layer_idx = 0
    while remaining:
        current = {n for n in remaining if all(p not in remaining for p in condensed.predecessors(n))}
        if not current:
            current = remaining.copy()
        for scc_node in current:
            members = condensed.nodes[scc_node].get("members", set())
            for member in members:
                file_layer[member] = layer_idx
        remaining -= current
        layer_idx += 1
    total_layers = layer_idx

    # Derive cone layer = max file layer among exclusive files
    cone_layer: dict[str, int] = {}
    for cid, cone in cones.items():
        if cone.exclusive_files:
            cone_layer[cid] = max(file_layer.get(f, 0) for f in cone.exclusive_files)
        else:
            cone_layer[cid] = 0

    logger.info("[PIPELINE] SCC condensation: %d components, DAG layering: %d layers computed",
                condensed.number_of_nodes(), total_layers)

    updated_cones: dict[str, FeatureCone] = {}
    for cid, cone in cones.items():
        updated_cones[cid] = FeatureCone(
            cone_id=cone.cone_id, entry_point=cone.entry_point,
            exclusive_files=cone.exclusive_files, shared_deps=cone.shared_deps,
            layer=cone_layer.get(cid, 0), token_count=cone.token_count,
        )
    cones = updated_cones

    # Step 3c: Louvain fallback when feature cones are degraded
    single_file = sum(1 for c in cones.values() if len(c.exclusive_files) <= 1)
    if len(cones) > 3 and single_file / len(cones) > 0.7:
        logger.warning(
            "[PIPELINE] Louvain fallback triggered — feature cones degraded (%d/%d single-file)",
            single_file, len(cones),
        )
        from src.graph.grouper import group_modules
        grouping = group_modules(graph, snapshot)
        cones = {}
        for mod_name, mod_files in grouping.modules.items():
            cones[mod_name] = FeatureCone(
                cone_id=mod_name, entry_point=mod_name,
                exclusive_files=tuple(mod_files), shared_deps=(),
            )
        infrastructure = grouping.utility_files
        logger.info("[PIPELINE] Louvain produced %d modules", len(cones))

    logger.info(
        "[PIPELINE] feature cones: %d cones, %d layers",
        len(cones), total_layers,
    )

    # Step 4: Estimate tokens per file
    logger.info("[analyze_codebase] Estimating tokens...")
    file_tokens = {}
    file_details = []
    for file_info in snapshot.files:
        lang = file_info.language or "default"
        tokens = estimate_tokens_from_chars(file_info.char_count, lang)
        file_tokens[file_info.filepath] = tokens
        file_details.append(
            {
                "filepath": file_info.filepath,
                "language": lang,
                "char_count": file_info.char_count,
                "line_count": file_info.line_count,
                "estimated_tokens": tokens,
                "method": "chars",
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

    # Step 6: Write JSON files + state.json
    write_analysis_outputs(
        output_path=output_path,
        project_id=project_id,
        resolved_path=resolved_path,
        snapshot=snapshot,
        weighted_result=weighted_result,
        graph=graph,
        cones=cones,
        infrastructure=infrastructure,
        cone_dicts=cone_dicts,
        file_tokens=file_tokens,
        file_details=file_details,
        task_manifest=task_manifest,
    )

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
    project_dir = find_latest_project_dir()
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
    project_dir = find_latest_project_dir()
    if not project_dir:
        raise ToolError("No project found. Run analyze_codebase first.")

    cones_path = project_dir / "03_feature_cones.json"
    if not cones_path.exists():
        raise ToolError(f"Feature cones file not found: {cones_path}")

    cones_data = json.loads(cones_path.read_text(encoding="utf-8"))
    cones = cones_data.get("cones", {})
    total_cones = len(cones)

    # Return summary list
    if not cone_id:
        summaries = [
            {
                "cone_id": cid,
                "name": c.get("entry_point", cid),
                "entry_file": c.get("entry_point", ""),
                "is_utility": is_utility_cone(
                    cid,
                    layer=c.get("layer", 0),
                    total_cones=total_cones,
                    all_cones=cones,
                ),
                "file_count": len(c.get("exclusive_files", [])),
                "total_tokens": c.get("token_count", 0),
                "layer": c.get("layer", 0),
            }
            for cid, c in cones.items()
        ]

        return {
            "status": "success",
            "total_cones": total_cones,
            "cones": summaries,
        }

    # Return specific cone details
    cone = cones.get(cone_id)
    if not cone:
        raise ToolError(f"Cone '{cone_id}' not found")

    # Compute is_utility for this specific cone
    is_utility = is_utility_cone(
        cone_id,
        layer=cone.get("layer", 0),
        total_cones=total_cones,
        all_cones=cones,
    )

    # Compute internal layer breakdown from DAG data
    dag_path = project_dir / "02_dag.json"
    layers: list[list[str]] = []
    if dag_path.exists():
        dag_data = json.loads(dag_path.read_text(encoding="utf-8"))
        dag_nodes = dag_data.get("nodes", [])
        dag_edges = dag_data.get("edges", [])
        cone_files = list(cone.get("exclusive_files", []))
        cone_files.extend(cone.get("shared_deps", []))
        layers = compute_cone_layers(cone_files, dag_nodes, dag_edges)

    # Compute inter-cone dependencies from shared_deps
    depends_on = compute_depends_on_cones(
        cone_id,
        cone.get("shared_deps", []),
        cones,
    )

    return {
        "status": "success",
        "cone_id": cone_id,
        "name": cone.get("entry_point", cone_id),
        "entry_file": cone.get("entry_point", ""),
        "is_utility": is_utility,
        "file_count": len(cone.get("exclusive_files", [])),
        "total_tokens": cone.get("token_count", 0),
        "layer": cone.get("layer", 0),
        "files": cone.get("exclusive_files", []),
        "layers": layers,
        "shared_deps": cone.get("shared_deps", []),
        "depends_on_cones": depends_on,
    }


# ---------------------------------------------------------------------------
# Tool 3b: get_modules (V5 format)
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
async def get_modules(
    module_id: Annotated[
        str | None,
        Field(description="Module ID for detail view. None = summary of all modules."),
    ] = None,
) -> dict:
    """Query functional modules in V5 format.

    Two modes:
    - Summary (no args): Module list with metadata only (<3KB). No file lists.
    - Detail (module_id): Single module with file list and token counts.

    Use summary first to get module IDs, then detail for specific modules.
    """
    project_dir = find_latest_project_dir()
    if not project_dir:
        raise ToolError("No project found. Run analyze_codebase first.")

    cones_path = project_dir / "03_feature_cones.json"
    if not cones_path.exists():
        raise ToolError("Feature cones not found. Run analyze_codebase first.")

    cones_data = json.loads(cones_path.read_text(encoding="utf-8"))
    cones = cones_data.get("cones", {})
    infra_files = cones_data.get("infrastructure", [])

    # Load file tokens
    tokens_path = project_dir / "04_file_tokens.json"
    file_tokens: dict[str, int] = {}
    if tokens_path.exists():
        tokens_data = json.loads(tokens_path.read_text(encoding="utf-8"))
        for ft in tokens_data.get("files", []):
            file_tokens[ft["filepath"]] = ft.get("estimated_tokens", 0)

    def _dir_hint(files: tuple | list) -> str:
        if not files:
            return ""
        dirs: dict[str, int] = {}
        for f in files:
            d = str(Path(f).parent)
            dirs[d] = dirs.get(d, 0) + 1
        return max(dirs.items(), key=lambda x: x[1])[0] + "/"

    def _friendly_name(cone_id: str) -> str:
        return cone_id.replace("_", " ").replace("::", " / ").title()

    # --- Summary mode (no module_id) ---
    if not module_id:
        total_files = sum(len(c.get("exclusive_files", [])) for c in cones.values())
        total_tokens = sum(c.get("token_count", 0) for c in cones.values())
        infra_tokens = sum(file_tokens.get(f, 0) for f in infra_files)

        modules = []
        for cid, cone in cones.items():
            modules.append({
                "module_id": cid,
                "file_count": len(cone.get("exclusive_files", [])),
                "token_count": cone.get("token_count", 0),
                "layer": cone.get("layer", 0),
            })

        return {
            "status": "success",
            "total_modules": len(cones),
            "total_files": total_files,
            "total_tokens": total_tokens,
            "grouping": {
                "strategy_used": "feature_cone",
                "available_strategies": list_strategies(),
                "interface": "GroupingStrategy protocol",
                "config": "Set CODEBASE_EXPLORER_STRATEGY env var to switch algorithm",
            },
            "token_budget": {
                "total_project_tokens": total_tokens,
                "budget_limit": 100_000,
                "within_budget": total_tokens <= 100_000,
                "stop_condition": "Modules exceeding budget are split into sub-tasks in task_manifest",
            },
            "modules": modules,
            "infrastructure": {
                "file_count": len(infra_files),
                "token_count": infra_tokens,
            },
        }

    # --- Detail mode (specific module_id) ---
    cone = cones.get(module_id)
    if not cone:
        raise ToolError(f"Module '{module_id}' not found")

    exclusive_files = cone.get("exclusive_files", [])
    files_with_tokens = [
        {"filepath": f, "token_count": file_tokens.get(f, 0)}
        for f in exclusive_files
    ]

    deps = compute_depends_on_cones(
        module_id, cone.get("shared_deps", []), cones,
    )

    # Compute internal layers from DAG
    dag_path = project_dir / "02_dag.json"
    internal_layers: list[list[str]] = []
    if dag_path.exists():
        dag_data = json.loads(dag_path.read_text(encoding="utf-8"))
        cone_files = list(exclusive_files) + list(cone.get("shared_deps", []))
        internal_layers = compute_cone_layers(
            cone_files, dag_data.get("nodes", []), dag_data.get("edges", []),
        )

    return {
        "status": "success",
        "module_id": module_id,
        "name": _friendly_name(module_id),
        "layer": cone.get("layer", 0),
        "depends_on": deps,
        "files": files_with_tokens,
        "internal_layers": internal_layers,
        "token_count": cone.get("token_count", 0),
    }


# ---------------------------------------------------------------------------
# Tool 3c: get_function_deps
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
async def get_function_deps(
    file: Annotated[str, Field(description="File path to query function dependencies for")],
    module_id: Annotated[
        str | None,
        Field(description="Optional: limit results to within-module dependencies"),
    ] = None,
) -> dict:
    """Get cross-file function-level dependencies for a specific file.

    Returns which functions in the given file call functions in other files.
    Only cross-file calls are included (same-file internal calls excluded).

    Use this when writing DETAIL docs to describe dependency relationships.
    """
    project_dir = find_latest_project_dir()
    if not project_dir:
        raise ToolError("No project found. Run analyze_codebase first.")

    deps_path = project_dir / "06_function_deps.json"
    if not deps_path.exists():
        raise ToolError(
            "Function deps not found. Re-run analyze_codebase with force_reindex=true."
        )

    deps_data = json.loads(deps_path.read_text(encoding="utf-8"))
    function_deps = deps_data.get("function_deps", {})

    file_deps = function_deps.get(file)
    if file_deps is None:
        return {
            "status": "success",
            "file": file,
            "dependencies": [],
            "message": "No cross-file function dependencies found for this file",
        }

    # Optional: filter to within-module deps
    if module_id:
        cones_path = project_dir / "03_feature_cones.json"
        if cones_path.exists():
            cones_data = json.loads(cones_path.read_text(encoding="utf-8"))
            cone = cones_data.get("cones", {}).get(module_id)
            if cone:
                module_files = set(cone.get("exclusive_files", []))
                filtered = []
                for dep_entry in file_deps:
                    filtered_calls = [
                        c for c in dep_entry["calls"]
                        if c["target_file"] in module_files
                    ]
                    if filtered_calls:
                        filtered.append({
                            "source_function": dep_entry["source_function"],
                            "calls": filtered_calls,
                        })
                file_deps = filtered

    return {
        "status": "success",
        "file": file,
        "dependencies": file_deps,
    }


# ---------------------------------------------------------------------------
# Tool 3d: doc_operation (V5)
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
async def doc_operation(
    operation: Annotated[
        Literal["get_template", "get_protocol"],
        Field(description="Operation: 'get_template' for DETAIL/INDEX format, 'get_protocol' for workflow"),
    ],
) -> dict:
    """Get documentation templates and protocols for DETAIL/INDEX generation.

    Operations:
    - get_template: Returns YAML front matter + HTML comment format for DETAIL and INDEX docs
    - get_protocol: Returns the three-step DETAIL protocol and INDEX assembly rules
    """
    if operation == "get_template":
        return {
            "status": "success",
            "detail_template": {
                "yaml_front_matter": (
                    "---\n"
                    "module: {module_id}\n"
                    "file: {filepath}\n"
                    "token_count: {token_count}\n"
                    "layer: {layer}\n"
                    "---"
                ),
                "html_markers": {
                    "module_start": "<!-- module:{module_id} -->",
                    "module_end": "<!-- /module:{module_id} -->",
                    "file_start": "<!-- file:{filepath} -->",
                    "file_end": "<!-- /file:{filepath} -->",
                    "index_fragment": "<!-- index-fragment:{module_id} -->",
                },
                "sections": [
                    "## Functions (Step 1: function descriptions)",
                    "## Dependencies (Step 2: cross-file calls from get_function_deps)",
                    "## Index Fragment (Step 3: summary paragraph for INDEX assembly)",
                ],
            },
            "index_template": {
                "yaml_front_matter": (
                    "---\n"
                    "project: {project_id}\n"
                    "total_modules: {total_modules}\n"
                    "generated_by: codebase-explorer\n"
                    "---"
                ),
                "assembly_rule": "INDEX is assembled by concatenating all Step 3 INDEX fragments from DETAIL sub-agents. No separate Agent rewrites the INDEX.",
                "format": (
                    "<!-- index:start -->\n"
                    "# {project_name} Architecture\n\n"
                    "{concatenated_index_fragments}\n"
                    "<!-- index:end -->"
                ),
            },
        }

    if operation == "get_protocol":
        return {
            "status": "success",
            "detail_protocol": {
                "name": "Three-Step DETAIL Protocol",
                "steps": [
                    {
                        "step": 1,
                        "name": "Function Descriptions",
                        "input": "Source file content",
                        "output": "Function names, signatures, and purpose descriptions",
                        "tool": "Read source file directly",
                    },
                    {
                        "step": 2,
                        "name": "Dependency Analysis",
                        "input": "get_function_deps(file=filepath)",
                        "output": "Cross-file call relationships with target functions",
                        "tool": "get_function_deps",
                    },
                    {
                        "step": 3,
                        "name": "INDEX Fragment",
                        "input": "Steps 1-2 output",
                        "output": "One paragraph summarizing this module for INDEX assembly",
                        "tool": "Agent writes <!-- index-fragment:{module_id} --> block",
                    },
                ],
                "token_budget_rule": "Stop if cumulative tokens exceed module token_count from get_modules",
            },
            "index_assembly": {
                "method": "Direct concatenation of all index-fragment blocks from DETAIL outputs",
                "no_rewrite": True,
                "format": "Fragments ordered by module layer (low to high)",
            },
        }

    return {"status": "error", "message": f"Unknown operation: {operation}"}


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
    hops: Annotated[
        int, Field(description="N-hop neighbors for scope=file (default 1)")
    ] = 1,
) -> dict:
    """Generate Mermaid dependency graph from 02_dag.json.

    Scopes:
    - project: Full DAG dependency graph (all nodes and edges)
    - cone: File-level graph within a specific feature cone
    - file: N-hop neighbor subgraph centered on a single file

    include_weights=True annotates edges with weight and relationship type.
    """
    logger.info("[DEP-GRAPH] Generating dependency graph scope=%s", scope)

    project_dir = find_latest_project_dir()
    if not project_dir:
        raise ToolError("No project found. Run analyze_codebase first.")

    dag_path = project_dir / "02_dag.json"
    if not dag_path.exists():
        raise ToolError(f"DAG file not found: {dag_path}")

    dag_data = json.loads(dag_path.read_text(encoding="utf-8"))

    # --- Reconstruct NetworkX graph from persisted DAG data ---------------
    all_nodes: list[str] = dag_data.get("nodes", [])
    all_edges: list[dict] = dag_data.get("edges", [])

    graph = build_graph_from_dag(all_nodes, all_edges)

    # --- Detect circular dependencies (SCC with >1 member) ---------------
    circular_deps = [
        sorted(scc)
        for scc in nx.strongly_connected_components(graph)
        if len(scc) > 1
    ]

    # --- Extract subgraph based on scope ----------------------------------
    if scope == "project":
        subgraph = graph

    elif scope == "cone":
        if not target:
            raise ToolError("target (cone_id) is required when scope='cone'")

        cones_path = project_dir / "03_feature_cones.json"
        if not cones_path.exists():
            raise ToolError(f"Feature cones file not found: {cones_path}")

        cones_data = json.loads(cones_path.read_text(encoding="utf-8"))
        cone = cones_data.get("cones", {}).get(target)
        if not cone:
            raise ToolError(f"Cone '{target}' not found")

        # Collect all files relevant to this cone: exclusive + shared_deps
        cone_files = set(cone.get("exclusive_files", []))
        cone_files.update(cone.get("shared_deps", []))
        valid_nodes = [n for n in cone_files if n in graph]
        subgraph = graph.subgraph(valid_nodes).copy()

    elif scope == "file":
        if not target:
            raise ToolError("target (file_path) is required when scope='file'")

        if target not in graph:
            raise ToolError(f"File '{target}' not found in dependency graph")

        # Collect N-hop neighbors (both predecessors and successors)
        clamped_hops = max(1, min(hops, MAX_HOPS))
        nodes_to_include = {target}
        frontier = {target}
        for _ in range(clamped_hops):
            new_frontier = set()
            for node in frontier:
                new_frontier.update(graph.predecessors(node))
                new_frontier.update(graph.successors(node))
            nodes_to_include.update(new_frontier)
            frontier = new_frontier

        subgraph = graph.subgraph(nodes_to_include).copy()

    else:
        raise ToolError(f"Invalid scope: {scope}")

    # --- Build Mermaid diagram from subgraph ------------------------------
    mermaid_graph = render_mermaid(subgraph, include_weights=include_weights)

    # --- Build structured node and edge lists for the response ------------
    result_nodes = sorted(subgraph.nodes())
    result_edges = [
        {
            "source": u,
            "target": v,
            "weight": data.get("weight", 1),
            "edge_types": data.get("edge_types", []),
        }
        for u, v, data in sorted(subgraph.edges(data=True))
    ]

    node_count = subgraph.number_of_nodes()
    edge_count = subgraph.number_of_edges()

    logger.info(
        "[DEP-GRAPH] Graph generated: %d nodes, %d edges",
        node_count,
        edge_count,
    )

    return {
        "status": "success",
        "scope": scope,
        "target": target,
        "mermaid_graph": mermaid_graph,
        "nodes": result_nodes,
        "edges": result_edges,
        "node_count": node_count,
        "edge_count": edge_count,
        "circular_deps": circular_deps,
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
    project_dir = find_latest_project_dir()
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
    project_dir = find_latest_project_dir()
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
    project_dir = find_latest_project_dir()
    if not project_dir:
        raise ToolError("No project found. Run analyze_codebase first.")

    state_path = project_dir / "state.json"
    project_root = project_dir.parent  # .codebase-analysis sits inside the project

    # Verify files exist, validate paths are within project directory, and append end marker
    end_marker = "\n<!-- codebase-explorer: end -->\n"
    for path in detail_paths + snippet_paths:
        p = Path(path).resolve()
        if not p.is_relative_to(project_root):
            raise ToolError(f"Path traversal rejected — file is outside project directory: {path}")
        if not p.exists():
            raise ToolError(f"File not found: {path}")
        content = p.read_text(encoding="utf-8")
        if "<!-- codebase-explorer: end -->" not in content:
            p.write_text(content + end_marker, encoding="utf-8")

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
