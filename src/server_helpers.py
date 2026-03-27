"""Server helper functions extracted from server.py for testability.

Pure functions with no MCP dependencies — can be tested in isolation.
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import networkx as nx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Simple helpers
# ---------------------------------------------------------------------------


def now_iso() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(UTC).isoformat()


def project_id_from_path(path: str) -> str:
    """Generate deterministic project ID from path."""
    return hashlib.sha256(path.encode()).hexdigest()[:12]


_MAX_SEARCH_DEPTH = 4
"""Maximum directory depth to search for .codebase-analysis directories."""


def _depth_limited_search(base: Path, max_depth: int) -> list[Path]:
    """Search for .codebase-analysis directories up to *max_depth* levels."""
    results: list[Path] = []
    for depth in range(max_depth + 1):
        pattern = "/".join(["*"] * depth + [".codebase-analysis"]) if depth else ".codebase-analysis"
        for p in base.glob(pattern):
            if p.is_dir() and (p / "state.json").exists():
                results.append(p)
    return results


def find_latest_project_dir() -> Path | None:
    """Find the most recently modified .codebase-analysis directory.

    Both CWD and HOME are searched with depth-limited glob
    (up to _MAX_SEARCH_DEPTH levels) to avoid unbounded traversal.
    """
    candidates: list[Path] = []

    cwd = Path.cwd()
    if cwd.exists():
        candidates.extend(_depth_limited_search(cwd, _MAX_SEARCH_DEPTH))

    home = Path.home()
    if home.exists() and home != cwd:
        candidates.extend(_depth_limited_search(home, _MAX_SEARCH_DEPTH))

    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def resolve_output_dir(path: str, output_dir: str | None) -> Path:
    """Resolve output directory for analysis results."""
    if output_dir:
        return Path(output_dir).resolve()
    return Path(path).resolve() / ".codebase-analysis"


def validate_json_files_exist(output_dir: Path) -> bool:
    """Check if all required JSON files exist."""
    required = [
        "01_structure.json",
        "02_dag.json",
        "03_feature_cones.json",
        "04_file_tokens.json",
        "05_task_manifest.json",
        "06_function_deps.json",
    ]
    return all((output_dir / f).exists() for f in required)


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------


def build_graph_from_dag(
    nodes: list[str],
    edges: list[dict],
) -> nx.DiGraph:
    """Reconstruct a NetworkX DiGraph from persisted 02_dag.json data.

    Args:
        nodes: List of node identifiers (file paths).
        edges: List of edge dicts with source, target, weight, and
               optional edge_types fields.

    Returns:
        A new NetworkX DiGraph with all node and edge attributes.
    """
    graph = nx.DiGraph()
    for node in nodes:
        graph.add_node(node)
    for edge in edges:
        src = edge["source"]
        tgt = edge["target"]
        weight = edge.get("weight", 1)
        edge_types = edge.get("edge_types", [])
        graph.add_edge(src, tgt, weight=weight, edge_types=edge_types)
    return graph


# ---------------------------------------------------------------------------
# Mermaid helpers
# ---------------------------------------------------------------------------


def short_mermaid_label(filepath: str) -> str:
    """Create a short display label from a file path for Mermaid diagrams.

    Uses at most the last two path components and escapes Mermaid-unsafe
    characters.
    """
    parts = PurePosixPath(filepath).parts
    label = "/".join(parts[-2:]) if len(parts) >= 2 else filepath
    return label.replace('"', "'").replace("[", "(").replace("]", ")")


def render_mermaid(
    graph: nx.DiGraph,
    *,
    include_weights: bool = False,
) -> str:
    """Render a NetworkX DiGraph as a Mermaid flowchart string.

    Args:
        graph: The subgraph to render.
        include_weights: When True, annotate edges with weight and
                         relationship types (import/call/inherit).

    Returns:
        Complete Mermaid graph definition string.
    """
    if graph.number_of_nodes() == 0:
        return "graph TD\n    empty[No nodes]"

    lines: list[str] = ["graph TD"]
    node_ids: dict[str, str] = {}

    for idx, node in enumerate(sorted(graph.nodes())):
        safe_id = f"n{idx}"
        node_ids[node] = safe_id
        label = short_mermaid_label(node)
        lines.append(f'    {safe_id}["{label}"]')

    for src, tgt, data in sorted(graph.edges(data=True)):
        src_id = node_ids[src]
        tgt_id = node_ids[tgt]
        if include_weights:
            weight = data.get("weight", 1)
            edge_types = data.get("edge_types", [])
            type_str = "/".join(edge_types) if edge_types else "dep"
            lines.append(f"    {src_id} -->|{type_str} w={weight}| {tgt_id}")
        else:
            lines.append(f"    {src_id} --> {tgt_id}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Feature-cone helpers
# ---------------------------------------------------------------------------

_UTILITY_KEYWORDS = frozenset({
    "utils", "util", "helpers", "helper", "common", "shared", "lib",
    "core", "base", "internal", "config", "constants", "types",
    "middleware", "logging", "errors", "exceptions",
})

_HIGH_FAN_OUT_THRESHOLD = 3
"""Cones depended on by >= this many other cones are considered utility."""


def is_utility_cone(
    cone_name: str,
    *,
    layer: int = 0,
    total_cones: int = 1,
    all_cones: dict | None = None,
) -> bool:
    """Determine if a cone is a utility/infrastructure module.

    A cone is classified as utility when:
    - Its name (entry_point / cone_id) contains utility-related keywords, OR
    - It sits at layer 0 (leaf dependency) while there are upper-layer cones, OR
    - It has high fan-out: many other cones list it among their shared_deps.
    """
    name_lower = cone_name.lower().replace("\\", "/")
    path_parts = PurePosixPath(name_lower).parts
    stem = PurePosixPath(name_lower).stem
    for part in (*path_parts, stem):
        if part in _UTILITY_KEYWORDS:
            return True

    if layer == 0 and total_cones > 2:
        return True

    if all_cones is not None:
        exclusive_files = set(
            all_cones.get(cone_name, {}).get("exclusive_files", [])
        )
        if exclusive_files:
            dependents = sum(
                1
                for cid, c in all_cones.items()
                if cid != cone_name
                and exclusive_files & set(c.get("shared_deps", []))
            )
            if dependents >= _HIGH_FAN_OUT_THRESHOLD:
                return True

    return False


def compute_cone_layers(
    cone_files: list[str],
    dag_nodes: list[str],
    dag_edges: list[dict],
) -> list[list[str]]:
    """Compute topological layer groups for files within a single cone.

    Builds a subgraph containing only the cone's files, then assigns each
    file to a layer using Kahn-style BFS (predecessors-first).
    """
    if not cone_files:
        return []

    cone_set = set(cone_files)
    subgraph = nx.DiGraph()
    for node in cone_files:
        subgraph.add_node(node)
    for edge in dag_edges:
        src = edge["source"]
        tgt = edge["target"]
        if src in cone_set and tgt in cone_set:
            subgraph.add_edge(src, tgt)

    remaining = set(subgraph.nodes())
    layers: list[list[str]] = []
    while remaining:
        current_layer = {
            n for n in remaining
            if all(p not in remaining for p in subgraph.predecessors(n))
        }
        if not current_layer:
            current_layer = remaining.copy()
        layers.append(sorted(current_layer))
        remaining -= current_layer

    return layers


def compute_depends_on_cones(
    cone_id: str,
    cone_shared_deps: list[str],
    all_cones: dict,
) -> list[str]:
    """Find which other cones the given cone depends on via shared dependencies."""
    if not cone_shared_deps:
        return []

    shared_set = set(cone_shared_deps)
    dependent_cones: set[str] = set()

    for cid, c in all_cones.items():
        if cid == cone_id:
            continue
        other_exclusive = set(c.get("exclusive_files", []))
        if shared_set & other_exclusive:
            dependent_cones.add(cid)

    return sorted(dependent_cones)


def build_file_to_cone_map(cones: dict) -> dict[str, str]:
    """Build a mapping from file path to the cone that owns it (exclusive_files)."""
    file_to_cone: dict[str, str] = {}
    for cone_id, cone in cones.items():
        for f in cone.get("exclusive_files", []):
            file_to_cone[f] = cone_id
    return file_to_cone


def compute_inter_module_deps_from_dag(
    cones: dict,
    dag_edges: list[dict],
) -> dict[str, set[str]]:
    """Compute inter-module dependency sets from DAG edges.

    For each edge (source→target) where source and target belong to
    different cones, record that source_cone depends on target_cone.

    Returns:
        Dict mapping cone_id → set of cone_ids it depends on.
    """
    file_to_cone = build_file_to_cone_map(cones)
    deps: dict[str, set[str]] = {cid: set() for cid in cones}

    for edge in dag_edges:
        src_cone = file_to_cone.get(edge["source"])
        tgt_cone = file_to_cone.get(edge["target"])
        if src_cone and tgt_cone and src_cone != tgt_cone:
            deps[src_cone].add(tgt_cone)

    return deps


def build_module_level_graph(
    cones: dict,
    dag_edges: list[dict],
) -> nx.DiGraph:
    """Build a module-level aggregated graph from file-level DAG edges.

    Nodes = cone IDs, edges = aggregated cross-module dependencies with
    weight = number of file-level edges between the two modules.
    """
    file_to_cone = build_file_to_cone_map(cones)

    # Count cross-module edges
    edge_weights: dict[tuple[str, str], int] = {}
    for edge in dag_edges:
        src_cone = file_to_cone.get(edge["source"])
        tgt_cone = file_to_cone.get(edge["target"])
        if src_cone and tgt_cone and src_cone != tgt_cone:
            key = (src_cone, tgt_cone)
            edge_weights[key] = edge_weights.get(key, 0) + 1

    graph = nx.DiGraph()
    for cone_id in cones:
        graph.add_node(cone_id)
    for (src, tgt), weight in edge_weights.items():
        graph.add_edge(src, tgt, weight=weight)

    return graph


# ---------------------------------------------------------------------------
# JSON output writer
# ---------------------------------------------------------------------------


def write_analysis_outputs(
    *,
    output_path: Path,
    project_id: str,
    resolved_path: Path,
    snapshot,
    weighted_result,
    graph: nx.DiGraph,
    cones: dict,
    infrastructure: Sequence[str],
    cone_dicts: dict,
    file_tokens: dict[str, int],
    file_details: list[dict],
    task_manifest: dict,
) -> dict:
    """Write the 5 JSON files + state.json to the output directory.

    Returns the state dict that was written.
    """
    from src.state.json_store import atomic_write_state

    ts = now_iso()

    # 01_structure.json
    structure_data = {
        "project_id": project_id,
        "path": str(resolved_path),
        "analyzed_at": ts,
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
            {
                "source": u,
                "target": v,
                "weight": graph[u][v].get("weight", 1),
                "edge_types": graph[u][v].get("edge_types", []),
            }
            for u, v in graph.edges()
        ],
    }
    (output_path / "02_dag.json").write_text(
        json.dumps(dag_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 03_feature_cones.json
    cones_data = {
        "project_id": project_id,
        "strategy_used": "feature_cone",
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

    # 06_function_deps.json — cross-file function call relationships
    # Build function name → filepath (unique names only)
    func_name_count: dict[str, int] = {}
    for fn in snapshot.functions:
        func_name_count[fn.name] = func_name_count.get(fn.name, 0) + 1

    func_name_to_file: dict[str, str] = {
        fn.name: fn.filepath
        for fn in snapshot.functions
        if func_name_count.get(fn.name, 0) == 1
    }

    # Also build class name → filepath for constructor/usage deps
    class_name_count: dict[str, int] = {}
    for ci in snapshot.classes:
        class_name_count[ci.name] = class_name_count.get(ci.name, 0) + 1

    class_name_to_file: dict[str, str] = {
        ci.name: ci.filepath
        for ci in snapshot.classes
        if class_name_count.get(ci.name, 0) == 1
    }

    # Build per-file function deps (check both function and class names)
    function_deps: dict[str, list] = {}
    for fn in snapshot.functions:
        calls = []
        for call_name in fn.calls:
            target_file = func_name_to_file.get(call_name)
            dep_type = "call"
            if not target_file:
                target_file = class_name_to_file.get(call_name)
                dep_type = "class_usage"
            if target_file and target_file != fn.filepath:
                calls.append({
                    "target_file": target_file,
                    "target_function": call_name,
                    "dep_type": dep_type,
                })
        if calls:
            function_deps.setdefault(fn.filepath, []).append({
                "source_function": fn.name,
                "calls": calls,
            })

    function_deps_data = {
        "project_id": project_id,
        "analyzed_at": ts,
        "total_files_with_deps": len(function_deps),
        "function_deps": function_deps,
    }
    (output_path / "06_function_deps.json").write_text(
        json.dumps(function_deps_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # state.json
    state = {
        "project_id": project_id,
        "path": str(resolved_path),
        "created_at": ts,
        "status": "analysis_complete",
        "tasks": {
            task_id: {
                "status": "pending",
                "created_at": ts,
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

    return state
