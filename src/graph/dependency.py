"""Dependency graph construction from a CodebaseSnapshot.

Builds a NetworkX DiGraph where nodes are source file paths and edges
represent import/dependency relationships.  All returned data structures
are immutable.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import PurePosixPath

import networkx as nx

from src.parser.codebase import CodebaseSnapshot, FileInfo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

STDLIB_HINT = "stdlib"
THIRD_PARTY_HINT = "third_party"
LOCAL_HINT = "local"


@dataclass(frozen=True)
class DependencyEdge:
    """A directed edge in the dependency graph."""

    source: str  # source file path
    target: str  # target file path
    weight: int  # number of import/call references
    edge_type: str  # "import" | "call" | "inherit"


@dataclass(frozen=True)
class DependencyGraphResult:
    """Immutable result of dependency graph construction."""

    graph: nx.DiGraph
    file_count: int
    edge_count: int
    edges: tuple[DependencyEdge, ...]
    circular_deps: tuple[tuple[str, ...], ...]  # SCC groups with > 1 member


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_dependency_graph(snapshot: CodebaseSnapshot) -> DependencyGraphResult:
    """Build a file-level dependency graph from a codebase snapshot.

    Constructs a NetworkX DiGraph where:
    - Nodes are source file paths.
    - Edges represent import relationships.
    - Edge weights reflect how many import statements link two files.

    Node attributes:
        file_path, language, line_count, function_count, class_count

    Edge attributes:
        weight, import_type (``"local"`` always for resolved internal imports)

    Args:
        snapshot: ``CodebaseSnapshot`` produced by the parser layer.

    Returns:
        ``DependencyGraphResult`` with the graph and metadata.
    """
    graph = nx.DiGraph()

    # -- Build lookup tables (path -> FileInfo) ----------------------------
    file_lookup: dict[str, FileInfo] = {fi.filepath: fi for fi in snapshot.files}

    # -- Add nodes ---------------------------------------------------------
    for fi in snapshot.files:
        graph.add_node(
            fi.filepath,
            file_path=fi.filepath,
            language=fi.language,
            line_count=fi.line_count,
            function_count=len(fi.function_names),
            class_count=len(fi.class_names),
        )

    # -- Add edges from import_sources -------------------------------------
    edge_weights: dict[tuple[str, str], int] = defaultdict(int)
    for fi in snapshot.files:
        src = fi.filepath
        for target in fi.import_sources:
            if target in file_lookup and target != src:
                edge_weights[(src, target)] += 1

    # -- Also account for function-level dependencies ----------------------
    for func in snapshot.functions:
        src = func.filepath
        for dep_path in func.dependencies:
            if dep_path in file_lookup and dep_path != src:
                edge_weights[(src, dep_path)] += 1

    edges: list[DependencyEdge] = []
    for (src, tgt), weight in edge_weights.items():
        import_type = _classify_import(src, tgt, snapshot.root_path)
        graph.add_edge(src, tgt, weight=weight, import_type=import_type)
        edges.append(
            DependencyEdge(source=src, target=tgt, weight=weight, edge_type="import")
        )

    # -- Detect circular dependencies (SCC with >1 member) -----------------
    circular_deps = tuple(
        tuple(sorted(scc))
        for scc in nx.strongly_connected_components(graph)
        if len(scc) > 1
    )

    logger.info(
        "Built dependency graph: %d files, %d edges, %d circular groups",
        graph.number_of_nodes(),
        graph.number_of_edges(),
        len(circular_deps),
    )

    return DependencyGraphResult(
        graph=graph,
        file_count=graph.number_of_nodes(),
        edge_count=graph.number_of_edges(),
        edges=tuple(edges),
        circular_deps=circular_deps,
    )


def get_module_dependency_subgraph(
    graph: nx.DiGraph,
    module_files: list[str],
) -> nx.DiGraph:
    """Extract a subgraph for a specific module's files.

    Args:
        graph: Full dependency graph.
        module_files: File paths belonging to the module.

    Returns:
        Subgraph containing only the specified files and their inter-edges.
    """
    valid_nodes = [f for f in module_files if f in graph]
    return graph.subgraph(valid_nodes).copy()


def get_dependency_graph_mermaid(graph: nx.DiGraph) -> str:
    """Export the dependency graph to Mermaid flowchart format.

    Produces a ``graph TD`` diagram with sanitised node identifiers.

    Args:
        graph: NetworkX DiGraph to export.

    Returns:
        Mermaid-compatible string.
    """
    if graph.number_of_nodes() == 0:
        return "graph TD\n    empty[No nodes]"

    lines: list[str] = ["graph TD"]
    node_ids: dict[str, str] = {}

    for idx, node in enumerate(sorted(graph.nodes())):
        safe_id = f"n{idx}"
        node_ids[node] = safe_id
        label = _short_label(node)
        lines.append(f"    {safe_id}[\"{label}\"]")

    for src, tgt, data in sorted(graph.edges(data=True)):
        src_id = node_ids[src]
        tgt_id = node_ids[tgt]
        weight = data.get("weight", 1)
        if weight > 1:
            lines.append(f"    {src_id} -->|{weight}| {tgt_id}")
        else:
            lines.append(f"    {src_id} --> {tgt_id}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _classify_import(source: str, target: str, root_path: str) -> str:
    """Classify an import edge as local / stdlib / third_party.

    Since ``import_sources`` from graph-sitter are resolved to actual
    file paths within the project, any successfully resolved import that
    lives under *root_path* is ``local``.  Unresolved imports never
    appear in the graph because they have no corresponding node.
    """
    try:
        src_parts = PurePosixPath(source).parts
        tgt_parts = PurePosixPath(target).parts
        root_parts = PurePosixPath(root_path).parts
        if (
            src_parts[: len(root_parts)] == root_parts
            and tgt_parts[: len(root_parts)] == root_parts
        ):
            return LOCAL_HINT
    except (IndexError, TypeError):
        pass
    return LOCAL_HINT  # resolved imports are always local in practice


def _short_label(filepath: str) -> str:
    """Create a short display label from a file path.

    Uses at most the last two path components and escapes Mermaid-unsafe
    characters.
    """
    parts = PurePosixPath(filepath).parts
    label = "/".join(parts[-2:]) if len(parts) >= 2 else filepath
    # Escape characters that break Mermaid syntax
    return label.replace('"', "'").replace("[", "(").replace("]", ")")
