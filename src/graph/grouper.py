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

from src.parser.codebase import CodebaseSnapshot, FileInfo
from src.graph.feature_cone import (
    extract_feature_cones as _extract_feature_cones,
    FeatureCone,
)
from src.graph.weighted_graph import build_weighted_dependency_graph

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


def recursive_subgroup(
    graph: nx.DiGraph,
    module_files: list[str],
    min_size: int = 5,
    resolution: float = 1.5,
) -> dict[str, list[str]]:
    """Recursively sub-group a large module via Louvain.

    When the module's file count exceeds *min_size*, a second round of
    community detection is applied to the module's subgraph.

    Args:
        graph: Full dependency graph.
        module_files: Files belonging to the module.
        min_size: Minimum file count before sub-grouping is attempted.
        resolution: Louvain resolution (higher = more sub-groups).

    Returns:
        Mapping of sub-group name to file list.  If the module is too
        small, returns a single entry.
    """
    if len(module_files) <= min_size:
        name = _derive_module_name(module_files, 0)
        return {name: list(module_files)}

    valid_nodes = [f for f in module_files if f in graph]
    if len(valid_nodes) <= min_size:
        name = _derive_module_name(valid_nodes, 0)
        return {name: valid_nodes}

    subgraph = graph.subgraph(valid_nodes).copy()
    partition = _louvain_partition(subgraph, resolution)

    groups: dict[int, list[str]] = defaultdict(list)
    for node, comm_id in partition.items():
        groups[comm_id].append(node)

    result: dict[str, list[str]] = {}
    for comm_id, files in sorted(groups.items()):
        name = _derive_module_name(files, comm_id)
        result[name] = sorted(files)

    return result


def get_module_metrics(
    graph: nx.DiGraph,
    modules: dict[str, tuple[str, ...] | list[str]],
    file_lookup: dict[str, FileInfo] | None = None,
) -> dict[str, ModuleMetrics]:
    """Compute complexity metrics for each module.

    Args:
        graph: Full dependency graph.
        modules: Module name to file paths mapping.
        file_lookup: Optional mapping of filepath -> ``FileInfo`` for
            richer metadata.  When *None*, node attributes from the
            graph are used.

    Returns:
        Dict of module name to ``ModuleMetrics``.
    """
    all_files_set = {f for files in modules.values() for f in files}
    metrics: dict[str, ModuleMetrics] = {}

    for name, files in modules.items():
        file_set = frozenset(files)
        func_count = 0
        class_count = 0
        line_count = 0
        subpackages: set[str] = set()

        for f in files:
            if file_lookup and f in file_lookup:
                fi = file_lookup[f]
                func_count += len(fi.function_names)
                class_count += len(fi.class_names)
                line_count += fi.line_count
            elif f in graph.nodes:
                data = graph.nodes[f]
                func_count += data.get("function_count", 0)
                class_count += data.get("class_count", 0)
                line_count += data.get("line_count", 0)

            # Count distinct parent directories as subpackages
            parent = os.path.dirname(f)
            if parent:
                subpackages.add(parent)

        internal_edges = 0
        external_edges = 0
        for f in files:
            if f not in graph:
                continue
            for successor in graph.successors(f):
                if successor in file_set:
                    internal_edges += 1
                elif successor in all_files_set:
                    external_edges += 1
            for predecessor in graph.predecessors(f):
                if predecessor not in file_set and predecessor in all_files_set:
                    external_edges += 1

        # Rough token estimate: ~15 tokens per line of code
        estimated_tokens = line_count * 15

        metrics[name] = ModuleMetrics(
            name=name,
            file_count=len(files),
            function_count=func_count,
            class_count=class_count,
            line_count=line_count,
            estimated_tokens=estimated_tokens,
            internal_edges=internal_edges,
            external_edges=external_edges,
            subpackage_count=len(subpackages),
        )

    return metrics


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


# ---------------------------------------------------------------------------
# V2 Feature Cone Integration
# ---------------------------------------------------------------------------


def extract_feature_cones(
    snapshot: CodebaseSnapshot,
    shared_threshold: int = 2,
) -> tuple[dict[str, FeatureCone], frozenset[str]]:
    """Extract feature cones from codebase snapshot.

    This is the V2 primary grouping strategy. Uses weighted dependency graph
    and Feature Cone extraction algorithm.

    Args:
        snapshot: Parsed codebase snapshot.
        shared_threshold: Minimum cones sharing a node for infrastructure classification.

    Returns:
        Tuple of (cone_dict, infrastructure_nodes).

    Example:
        >>> snapshot = parser.parse("/path/to/codebase")
        >>> cones, infra = extract_feature_cones(snapshot)
        >>> for cone_id, cone in cones.items():
        ...     print(f"{cone_id}: {len(cone.exclusive_files)} files")
    """
    # Build weighted dependency graph
    weighted_result = build_weighted_dependency_graph(snapshot)
    graph = weighted_result.graph

    # Extract feature cones
    cones, infrastructure = _extract_feature_cones(graph, snapshot, shared_threshold)

    logger.info(
        "[grouper] Feature Cone mode: extracted %d cones from DAG (%d infrastructure nodes)",
        len(cones),
        len(infrastructure),
    )

    return cones, infrastructure


def get_cone_metrics(
    cone: FeatureCone,
    file_lookup: dict[str, FileInfo] | None = None,
) -> ModuleMetrics:
    """Compute complexity metrics for a feature cone.

    Args:
        cone: FeatureCone object.
        file_lookup: Optional mapping of filepath -> FileInfo for metadata.

    Returns:
        ModuleMetrics for the cone.

    Example:
        >>> cones, _ = extract_feature_cones(snapshot)
        >>> metrics = get_cone_metrics(cones["cli.py"])
        >>> print(f"Token estimate: {metrics.estimated_tokens}")
    """
    # Combine exclusive and shared files
    all_files = list(cone.exclusive_files) + list(cone.shared_deps)

    # Compute basic counts
    function_count = 0
    class_count = 0
    line_count = 0
    char_count = 0

    if file_lookup:
        for filepath in all_files:
            if filepath in file_lookup:
                fi = file_lookup[filepath]
                function_count += len(fi.function_names)
                class_count += len(fi.class_names)
                line_count += fi.line_count
                # Note: FileInfo doesn't have char_count in current schema
                # Use line_count * 40 as rough estimate
                char_count += fi.line_count * 40

    # Estimate tokens (chars / 4)
    estimated_tokens = char_count // 4 if char_count > 0 else line_count * 10

    logger.info(
        "[grouper] get_cone_metrics: cone '%s' metrics computed (%d files, %d tokens)",
        cone.cone_id,
        len(all_files),
        estimated_tokens,
    )

    return ModuleMetrics(
        name=cone.cone_id,
        file_count=len(all_files),
        function_count=function_count,
        class_count=class_count,
        line_count=line_count,
        estimated_tokens=estimated_tokens,
        internal_edges=0,  # Not computed for cones
        external_edges=0,  # Not computed for cones
        subpackage_count=0,  # Not computed for cones
    )
