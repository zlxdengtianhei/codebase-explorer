"""Module grouping via Feature Cone extraction and Louvain community detection.

V2 Architecture:
- Feature Cone extraction is the primary grouping strategy (horizontal slices)
- Louvain community detection is fallback for specific cases (flat directories)

Utility nodes (high in-degree) are isolated before detection and
assigned to a dedicated utility group.
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict
from dataclasses import dataclass

import networkx as nx

from src.parser.codebase import CodebaseSnapshot

logger = logging.getLogger(__name__)

# Try importing python-louvain; fall back to networkx built-in Louvain.
_USE_COMMUNITY_LOUVAIN = False
try:
    from community import community_louvain  # type: ignore[import-untyped]

    _USE_COMMUNITY_LOUVAIN = True
except ImportError:
    logger.debug(
        "python-louvain not installed; falling back to "
        "networkx.community.louvain_communities"
    )


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

UTILITY_MODULE_PREFIX = "_utilities"


@dataclass(frozen=True)
class ModuleMetrics:
    """Complexity metrics for a detected module group."""

    name: str
    file_count: int
    function_count: int
    class_count: int
    line_count: int
    estimated_tokens: int
    internal_edges: int
    external_edges: int
    subpackage_count: int


@dataclass(frozen=True)
class GroupingResult:
    """Result of the module grouping process."""

    modules: dict[str, tuple[str, ...]]  # module_name -> file_paths
    utility_files: frozenset[str]
    modularity_score: float
    module_count: int


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def group_modules(
    graph: nx.DiGraph,
    snapshot: CodebaseSnapshot | None = None,
    resolution: float = 1.0,
    utility_threshold: float = 0.1,
) -> GroupingResult:
    """Group codebase files into logical modules via Louvain detection.

    Args:
        graph: Dependency DiGraph from ``build_dependency_graph``.
        snapshot: Optional ``CodebaseSnapshot`` (reserved for future use).
        resolution: Louvain resolution (>1 yields smaller communities).
        utility_threshold: In-degree fraction to mark a node as utility.

    Returns:
        ``GroupingResult`` with module assignments and quality score.
    """
    if graph.number_of_nodes() == 0:
        return GroupingResult(
            modules={}, utility_files=frozenset(), modularity_score=0.0, module_count=0
        )

    # -- Step 1: Identify utility nodes ------------------------------------
    utilities = identify_utility_nodes(graph, threshold=utility_threshold)

    # -- Step 2: Remove utilities and run Louvain --------------------------
    filtered = graph.copy()
    filtered.remove_nodes_from(utilities)

    partition = _louvain_partition(filtered, resolution)

    # -- Step 3: Organise into {module_name: file_list} --------------------
    community_map: dict[int, list[str]] = defaultdict(list)
    for node, comm_id in partition.items():
        community_map[comm_id].append(node)

    modules: dict[str, tuple[str, ...]] = {}
    for comm_id, files in sorted(community_map.items()):
        name = _derive_module_name(files, comm_id)
        modules[name] = tuple(sorted(files))

    # Add utility group if non-empty
    if utilities:
        modules[UTILITY_MODULE_PREFIX] = tuple(sorted(utilities))

    # -- Step 4: Compute modularity ----------------------------------------
    modularity = _compute_modularity(graph, modules)

    logger.info(
        "Grouped %d files into %d modules (modularity=%.3f, utilities=%d)",
        graph.number_of_nodes(),
        len(modules),
        modularity,
        len(utilities),
    )

    return GroupingResult(
        modules=modules,
        utility_files=frozenset(utilities),
        modularity_score=modularity,
        module_count=len(modules),
    )


def identify_utility_nodes(
    graph: nx.DiGraph,
    threshold: float = 0.1,
    utility_dir_patterns: tuple[str, ...] | None = None,
) -> frozenset[str]:
    """Identify utility/shared nodes with high in-degree.

    A node is utility if:
    - Its in-degree exceeds *threshold* x total_nodes, **or**
    - It resides in a well-known utility directory.

    Args:
        graph: Dependency DiGraph.
        threshold: In-degree fraction marking a node as utility.
        utility_dir_patterns: Directory name patterns to match.

    Returns:
        Frozenset of file paths identified as utility nodes.
    """
    if utility_dir_patterns is None:
        utility_dir_patterns = (
            "utils",
            "util",
            "common",
            "shared",
            "helpers",
            "lib",
            "tools",
        )

    total = graph.number_of_nodes()
    if total == 0:
        return frozenset()

    utilities: set[str] = set()
    for node in graph.nodes():
        # High in-degree check
        if graph.in_degree(node) > threshold * total:
            utilities.add(node)
            continue
        # Directory name check
        for pattern in utility_dir_patterns:
            if f"/{pattern}/" in node or node.startswith(f"{pattern}/"):
                utilities.add(node)
                break

    return frozenset(utilities)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _louvain_partition(
    directed_graph: nx.DiGraph,
    resolution: float,
) -> dict[str, int]:
    """Run Louvain community detection, returning {node: community_id}.

    Louvain requires an undirected graph, so the directed graph is
    converted first.  Isolated nodes receive their own community id.
    """
    if directed_graph.number_of_nodes() == 0:
        return {}

    undirected = directed_graph.to_undirected()

    if _USE_COMMUNITY_LOUVAIN:
        partition: dict[str, int] = community_louvain.best_partition(
            undirected,
            weight="weight",
            resolution=resolution,
            random_state=42,
        )
    else:
        # NetworkX built-in Louvain (3.x+)
        communities = nx.community.louvain_communities(
            undirected,
            weight="weight",
            resolution=resolution,
            seed=42,
        )
        partition = {}
        for idx, comm in enumerate(communities):
            for node in comm:
                partition[node] = idx

    return partition


def _derive_module_name(files: list[str], community_id: int) -> str:
    """Derive a human-readable module name from file paths.

    Attempts to find the longest common directory prefix among *files*.
    Falls back to ``module_<community_id>`` when no common prefix exists.
    """
    if not files:
        return f"module_{community_id}"

    parts_list = [os.path.dirname(f).split(os.sep) for f in files]

    # Find longest common prefix
    prefix_parts: list[str] = []
    for segments in zip(*parts_list):
        if len(set(segments)) == 1 and segments[0]:
            prefix_parts.append(segments[0])
        else:
            break

    if prefix_parts:
        name = "/".join(prefix_parts)
        # Remove leading src/ or ./ for cleaner names
        for strip_prefix in ("src/", "./"):
            if name.startswith(strip_prefix):
                name = name[len(strip_prefix):]
        return name or f"module_{community_id}"

    return f"module_{community_id}"


def _compute_modularity(
    graph: nx.DiGraph,
    modules: dict[str, tuple[str, ...]],
) -> float:
    """Compute modularity score for the given partition.

    Uses NetworkX's ``modularity()`` on the undirected projection.
    Returns 0.0 on failure (e.g. empty graph or single community).
    """
    undirected = graph.to_undirected()

    communities = [
        {f for f in files if f in undirected}
        for files in modules.values()
    ]
    # Filter out empty communities
    communities = [c for c in communities if c]

    if len(communities) < 2 or undirected.number_of_edges() == 0:
        return 0.0

    try:
        return float(nx.community.modularity(undirected, communities))
    except (nx.NetworkXError, ZeroDivisionError):
        logger.warning("Modularity computation failed", exc_info=True)
        return 0.0

