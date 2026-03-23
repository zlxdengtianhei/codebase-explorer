"""Weighted multi-relation dependency graph builder.

Constructs a weighted dependency graph by combining three types of
code relationships:
- Import edges (weight=1): Static import statements
- Call edges (weight=2): Function call dependencies
- Inheritance edges (weight=3): Class inheritance relationships

When multiple relations exist between the same pair of files,
weights are accumulated (not maxed) to reflect total coupling strength.

This replaces the simple import-only dependency graph in V1.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import networkx as nx

from src.parser.codebase import CodebaseSnapshot


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EDGE_WEIGHTS = {
    "import": 1,
    "call": 2,
    "inherit": 3,
}
"""Weight multipliers for each edge type."""


# ---------------------------------------------------------------------------
# Result Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WeightedGraphResult:
    """Result of weighted dependency graph construction.

    Attributes:
        graph: NetworkX DiGraph with weighted edges.
            Each edge has 'weight' (int) and 'edge_types' (list[str]) attributes.
        node_count: Number of nodes in the graph.
        edge_count: Number of edges in the graph.
        total_weight: Sum of all edge weights.
        summary: Human-readable summary of edge statistics.
    """

    graph: nx.DiGraph
    node_count: int
    edge_count: int
    total_weight: int
    summary: str


# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------


def build_weighted_dependency_graph(snapshot: CodebaseSnapshot) -> WeightedGraphResult:
    """Build a weighted dependency graph from codebase snapshot.

    Combines three types of dependencies:
    1. Import edges (weight=1): file.import_sources
    2. Call edges (weight=2): function.dependencies (file paths)
    3. Inheritance edges (weight=3): class.base_classes (name lookup)

    For duplicate function/class names, uses conservative strategy:
    skips creating edges to avoid incorrect associations.

    Args:
        snapshot: Parsed codebase snapshot.

    Returns:
        WeightedGraphResult with graph and metadata.

    Example:
        >>> snapshot = parser.parse("/path/to/codebase")
        >>> result = build_weighted_dependency_graph(snapshot)
        >>> print(result.summary)
        '2 nodes, 1 edges (import_edges=1, call_edges=0, inherit_edges=0, total_weight=1)'
    """
    G = nx.DiGraph()

    # Build file set for fast lookup
    file_set = {fi.filepath for fi in snapshot.files}

    # Step 1: Build lookup tables for name resolution
    # Only include unique names to avoid ambiguity
    func_name_count: dict[str, int] = defaultdict(int)
    for func in snapshot.functions:
        func_name_count[func.name] += 1

    func_name_to_file: dict[str, str] = {
        func.name: func.filepath
        for func in snapshot.functions
        if func_name_count[func.name] == 1
    }

    class_name_count: dict[str, int] = defaultdict(int)
    for cls in snapshot.classes:
        class_name_count[cls.name] += 1

    class_name_to_file: dict[str, str] = {
        cls.name: cls.filepath
        for cls in snapshot.classes
        if class_name_count[cls.name] == 1
    }

    # Step 2: Add nodes
    for fi in snapshot.files:
        G.add_node(
            fi.filepath,
            language=fi.language,
            line_count=fi.line_count,
            function_count=len(fi.function_names),
            class_count=len(fi.class_names),
        )

    # Step 3: Accumulate edge weights
    edge_weights: dict[tuple[str, str], int] = defaultdict(int)
    edge_types: dict[tuple[str, str], set[str]] = defaultdict(set)

    # Source 1: Import edges (weight=1)
    for fi in snapshot.files:
        src = fi.filepath
        for target in fi.import_sources:
            if target in file_set and target != src:
                edge_weights[(src, target)] += EDGE_WEIGHTS["import"]
                edge_types[(src, target)].add("import")

    # Source 2: Call edges (weight=2)
    # func.dependencies contains file paths directly
    for func in snapshot.functions:
        src = func.filepath
        for dep_path in func.dependencies:
            if dep_path in file_set and dep_path != src:
                edge_weights[(src, dep_path)] += EDGE_WEIGHTS["call"]
                edge_types[(src, dep_path)].add("call")

    # Source 3: Inheritance edges (weight=3)
    # Resolve class name to file path via lookup table
    for cls in snapshot.classes:
        src = cls.filepath
        for base_name in cls.base_classes:
            base_file = class_name_to_file.get(base_name)
            if base_file and base_file in file_set and base_file != src:
                edge_weights[(src, base_file)] += EDGE_WEIGHTS["inherit"]
                edge_types[(src, base_file)].add("inherit")

    # Step 4: Add edges with accumulated weights
    for (src, tgt), weight in edge_weights.items():
        types = sorted(edge_types[(src, tgt)])
        G.add_edge(src, tgt, weight=weight, edge_types=types)

    # Build result metadata
    node_count = G.number_of_nodes()
    edge_count = G.number_of_edges()
    total_weight = sum(edge_data["weight"] for _, _, edge_data in G.edges(data=True))

    # Count edge types for summary
    import_count = sum(1 for _, _, d in G.edges(data=True) if "import" in d.get("edge_types", []))
    call_count = sum(1 for _, _, d in G.edges(data=True) if "call" in d.get("edge_types", []))
    inherit_count = sum(1 for _, _, d in G.edges(data=True) if "inherit" in d.get("edge_types", []))

    summary = (
        f"{node_count} nodes, {edge_count} edges "
        f"(import_edges={import_count}, call_edges={call_count}, "
        f"inherit_edges={inherit_count}, total_weight={total_weight})"
    )

    return WeightedGraphResult(
        graph=G,
        node_count=node_count,
        edge_count=edge_count,
        total_weight=total_weight,
        summary=summary,
    )
