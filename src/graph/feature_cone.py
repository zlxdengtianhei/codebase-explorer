"""Feature Cone extraction algorithm for codebase module grouping.

Implements the core algorithm for identifying feature-based module groups
by analyzing dependency structure in the codebase DAG.

Algorithm Overview:
1. Find feature roots (entry points with in-degree=0)
2. For each root, trace dependencies via weight-aware affinity-decay BFS (T-04)
3. Identify shared infrastructure nodes (dynamic threshold T-05)
4. Promote high fan-in files to infrastructure (T-12 CRITICAL #1)
5. Rebalance cones: split mega-cones + merge orphans (T-06)
   - Import-graph clustering for same-directory mega-cones (T-12 CRITICAL #2)
   - Separate testing files from runtime cones (T-12 HIGH #3)
   - Generate meaningful cone names (T-12 HIGH #4)
6. Assign SCC groups to dominant cone or infrastructure

This replaces Louvain as the primary grouping strategy in V2.
"""

from __future__ import annotations

import logging
import posixpath
from collections import Counter, defaultdict
from dataclasses import dataclass

import networkx as nx

logger = logging.getLogger(__name__)

from src.graph.semantic_hints import classify_file
from src.parser.codebase import CodebaseSnapshot


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHARED_THRESHOLD_MIN = 2
"""Minimum number of cones that must share a node for infrastructure classification."""

FANIN_INFRASTRUCTURE_RATIO = 0.5
"""Files imported by >= this fraction of all cones are promoted to infrastructure."""

# T-04: Weight-aware affinity-decay BFS edge weights
EDGE_AFFINITY = {
    1: 0.3,   # import edge (weight=1 in weighted graph)
    2: 0.5,   # call edge (weight=2)
    3: 0.7,   # inheritance edge (weight=3)
}
"""Affinity scores by edge type: import=0.3, call=0.5, inherit=0.7."""

AFFINITY_DECAY = 0.7
"""Multiplicative decay applied to affinity at each BFS hop."""

AFFINITY_CUTOFF = 0.08
"""Nodes with accumulated affinity below this threshold are excluded from the cone."""


def compute_shared_threshold(n_roots: int) -> int:
    """T-05: Dynamic shared threshold = max(2, round(N * 0.3)).

    Args:
        n_roots: Number of feature roots (cones) detected.

    Returns:
        Shared threshold for infrastructure classification.
    """
    return max(SHARED_THRESHOLD_MIN, round(n_roots * 0.3))


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeatureCone:
    """A feature cone representing a cohesive feature or use case.

    A cone is rooted at a feature entry point and contains all files
    that are uniquely used by that feature, plus references to shared
    infrastructure dependencies.
    """

    cone_id: str
    """Unique identifier for this cone (typically the entry point path)."""

    entry_point: str
    """The root file that defines this feature's entry point."""

    exclusive_files: list[str]
    """Files uniquely owned by this cone (not shared with other cones)."""

    shared_deps: list[str]
    """Infrastructure files shared with other cones."""

    layer: int = 0
    """DAG layer depth for this cone (0 = top-level entry)."""

    token_count: int = 0
    """Estimated token count for all files in this cone."""


# ---------------------------------------------------------------------------
# Feature Root Detection
# ---------------------------------------------------------------------------


def find_feature_roots(dag: nx.DiGraph) -> list[str]:
    """Find feature entry points in the DAG.

    Feature roots are nodes with in-degree=0 (no internal code depends on them).
    These represent top-level entry points like CLI commands, API endpoints, etc.

    For library code where all nodes have in-degree>0, falls back to selecting
    nodes with in-degree <= min+1.

    Args:
        dag: The dependency DAG (possibly after SCC condensation).

    Returns:
        List of node IDs that are feature roots.
    """
    in_degrees = dict(dag.in_degree())

    # Ideal case: find nodes with in-degree = 0
    roots = [node for node, deg in in_degrees.items() if deg == 0]

    if roots:
        return sorted(roots)  # Sort for deterministic ordering

    # Library code fallback: no pure entry points
    # Take nodes with minimal in-degree (or min+1)
    min_deg = min(in_degrees.values())
    roots = [node for node, deg in in_degrees.items() if deg <= min_deg + 1]

    return sorted(roots)


# ---------------------------------------------------------------------------
# T-04: Weight-aware affinity-decay BFS
# ---------------------------------------------------------------------------


def _affinity_bfs(
    dag: nx.DiGraph,
    root: str,
) -> dict[str, float]:
    """T-04: Weight-aware affinity-decay BFS from *root*.

    At each hop the affinity score is multiplied by both the edge-type
    affinity weight and the global decay factor.  Nodes whose accumulated
    affinity falls below ``AFFINITY_CUTOFF`` are excluded.

    Args:
        dag: Weighted dependency DAG.
        root: Starting node.

    Returns:
        Mapping of node -> best affinity score for nodes reachable from *root*
        with affinity >= AFFINITY_CUTOFF.
    """
    best: dict[str, float] = {root: 1.0}
    # queue: (node, current_affinity)
    queue: list[tuple[str, float]] = [(root, 1.0)]

    while queue:
        node, affinity = queue.pop(0)

        for successor in dag.successors(node):
            edge_data = dag[node][successor]
            if "weight" in edge_data:
                edge_affinity = EDGE_AFFINITY.get(edge_data["weight"], 0.5)
            else:
                # Unweighted edge: use moderate affinity (generic dependency)
                edge_affinity = 0.5
            new_affinity = affinity * edge_affinity * AFFINITY_DECAY

            if new_affinity < AFFINITY_CUTOFF:
                continue

            if successor not in best or new_affinity > best[successor]:
                best[successor] = new_affinity
                queue.append((successor, new_affinity))

    return best


# ---------------------------------------------------------------------------
# T-12 CRITICAL #1: High fan-in infrastructure promotion
# ---------------------------------------------------------------------------


def _promote_high_fanin_to_infrastructure(
    cones: dict[str, FeatureCone],
    infrastructure_nodes: set[str],
    dag: nx.DiGraph,
) -> tuple[dict[str, FeatureCone], set[str]]:
    """Promote high fan-in files to infrastructure.

    Files that appear in exclusive_files of >= FANIN_INFRASTRUCTURE_RATIO of all
    cones are reclassified as shared infrastructure.  This handles cases where
    files like ``globals.py`` or ``__init__.py`` are imported by many cones but
    were not caught by the initial shared-threshold check (e.g. because the
    threshold was too high or the BFS did not reach them from every root).

    Additionally, files with high in-degree in the DAG (imported by many
    different files) are also considered for promotion.

    Args:
        cones: Current cone mapping (cone_id -> FeatureCone).
        infrastructure_nodes: Current set of infrastructure node IDs.
        dag: The dependency DAG.

    Returns:
        Updated (cones, infrastructure_nodes) with high fan-in files promoted.
    """
    if not cones:
        return cones, infrastructure_nodes

    n_cones = len(cones)
    fanin_threshold = max(2, int(n_cones * FANIN_INFRASTRUCTURE_RATIO))

    # Count how many cones each file appears in (as exclusive)
    file_cone_count: dict[str, int] = defaultdict(int)
    for cone in cones.values():
        for f in cone.exclusive_files:
            file_cone_count[f] += 1

    # Also check DAG in-degree: files imported by many others are infrastructure
    dag_in_degrees = dict(dag.in_degree())

    # Compute median in-degree for adaptive threshold
    all_in_degrees = sorted(dag_in_degrees.values())
    if all_in_degrees:
        median_idx = len(all_in_degrees) // 2
        median_in_degree = all_in_degrees[median_idx]
    else:
        median_in_degree = 0

    # High in-degree threshold: files with in-degree > 2x median and >= 3
    high_indegree_threshold = max(3, median_in_degree * 2)

    newly_promoted: set[str] = set()
    for f, count in file_cone_count.items():
        if f in infrastructure_nodes:
            continue
        # Promote if file is in >= fanin_threshold cones
        if count >= fanin_threshold:
            newly_promoted.add(f)
            continue
        # Also promote if DAG in-degree is very high (heavily imported)
        if dag_in_degrees.get(f, 0) >= high_indegree_threshold and count >= 2:
            newly_promoted.add(f)

    if not newly_promoted:
        return cones, infrastructure_nodes

    logger.info(
        "[FANIN] promoting %d high fan-in files to infrastructure: %s",
        len(newly_promoted),
        sorted(newly_promoted),
    )

    # Build updated infrastructure set (new copy, not mutating)
    updated_infra = infrastructure_nodes | newly_promoted

    # Rebuild cones: move promoted files from exclusive to shared_deps
    updated_cones: dict[str, FeatureCone] = {}
    for cone_id, cone in cones.items():
        new_exclusive = [f for f in cone.exclusive_files if f not in newly_promoted]
        promoted_from_this = [f for f in cone.exclusive_files if f in newly_promoted]
        new_shared = sorted(set(cone.shared_deps) | set(promoted_from_this))

        updated_cones[cone_id] = FeatureCone(
            cone_id=cone.cone_id,
            entry_point=cone.entry_point,
            exclusive_files=sorted(new_exclusive),
            shared_deps=new_shared,
            layer=cone.layer,
            token_count=cone.token_count,
        )

    return updated_cones, updated_infra


# ---------------------------------------------------------------------------
# Feature Cone Extraction
# ---------------------------------------------------------------------------


def extract_feature_cones(
    dag: nx.DiGraph,
    snapshot: CodebaseSnapshot,
    shared_threshold: int | None = None,
) -> tuple[dict[str, FeatureCone], frozenset[str]]:
    """Extract feature cones from the dependency DAG.

    Uses T-04 weight-aware affinity-decay BFS to trace dependencies from
    each feature root.  Nodes shared by >= threshold cones are classified
    as infrastructure (T-05 dynamic threshold).

    Args:
        dag: The dependency DAG (possibly after SCC condensation).
        snapshot: Codebase snapshot for metadata.
        shared_threshold: Override for the dynamic threshold.  When ``None``
            the threshold is computed as ``max(2, round(N * 0.3))`` where
            *N* is the number of feature roots.

    Returns:
        Tuple of:
        - Dictionary mapping cone_id -> FeatureCone
        - Set of infrastructure node IDs

    Example:
        >>> dag = nx.DiGraph()
        >>> dag.add_edge("cli.py", "app.py")
        >>> dag.add_edge("app.py", "utils.py")
        >>> cones, infra = extract_feature_cones(dag, snapshot)
        >>> "cli.py" in cones
        True
    """
    # Find all feature roots
    roots = find_feature_roots(dag)

    # T-05: Dynamic shared threshold
    if shared_threshold is None:
        shared_threshold = compute_shared_threshold(len(roots))

    # T-04: Weight-aware affinity-decay BFS from each root
    # Track which cones each node belongs to
    node_cones: dict[str, set[str]] = defaultdict(set)

    for root in roots:
        reachable = _affinity_bfs(dag, root)
        for node in reachable:
            node_cones[node].add(root)

    # Classify nodes: exclusive vs shared infrastructure
    infrastructure_nodes: set[str] = set()
    for node, belonging_cones in node_cones.items():
        if len(belonging_cones) >= shared_threshold:
            infrastructure_nodes.add(node)

    # Build FeatureCone objects
    cones: dict[str, FeatureCone] = {}

    for root in roots:
        exclusive: list[str] = []
        shared_refs: list[str] = []

        # Collect nodes for this cone
        for node, belonging_cones in node_cones.items():
            if root in belonging_cones:
                if node in infrastructure_nodes:
                    shared_refs.append(node)
                else:
                    exclusive.append(node)

        cones[root] = FeatureCone(
            cone_id=root,
            entry_point=root,
            exclusive_files=sorted(exclusive),  # Sort for determinism
            shared_deps=sorted(shared_refs),
        )

    # T-12 CRITICAL #1: Promote high fan-in files to infrastructure
    cones, infrastructure_nodes = _promote_high_fanin_to_infrastructure(
        cones, infrastructure_nodes, dag,
    )

    # Collect all files assigned to at least one cone
    assigned_files: set[str] = set()
    for cone in cones.values():
        assigned_files.update(cone.exclusive_files)
    assigned_files.update(infrastructure_nodes)

    # Create orphan cones for unassigned files (affinity decayed below cutoff)
    all_nodes = set(dag.nodes())
    unassigned = sorted(all_nodes - assigned_files)
    for orphan_file in unassigned:
        cones[orphan_file] = FeatureCone(
            cone_id=orphan_file,
            entry_point=orphan_file,
            exclusive_files=[orphan_file],
            shared_deps=[],
            layer=0,
            token_count=0,
        )

    # T-06: Post-processing: rebalance cones (split mega-cones, merge orphans)
    total_files = dag.number_of_nodes()
    rebalanced = rebalance_cones(list(cones.values()), total_files, dag)
    cones = {c.cone_id: c for c in rebalanced}

    return cones, frozenset(infrastructure_nodes)


# ---------------------------------------------------------------------------
# Cone Rebalancing (T-06)
# ---------------------------------------------------------------------------


def _parent_dir(filepath: str) -> str:
    """Return the parent directory of a file path.

    Uses posixpath for consistent behavior across platforms (file paths in
    the codebase DAG use forward slashes). Files at the root level return
    an empty string ``""``.

    Args:
        filepath: A relative file path (e.g. ``"src/auth/login.py"``).

    Returns:
        The parent directory (e.g. ``"src/auth"``), or ``""`` for root-level files.
    """
    return posixpath.dirname(filepath)


def _split_mega_cone(
    cone: FeatureCone,
    total_files: int,
    dag: nx.DiGraph,
) -> list[FeatureCone]:
    """Split a mega-cone (>50% of total files) into smaller sub-cones.

    Groups exclusive files by their parent directory, creating one sub-cone
    per directory. Files at the repository root are grouped under ``"<root>"``.

    If directory-based splitting produces only one group (all files in the
    same directory), falls back to DAG-layer splitting: files are grouped
    by topological depth from the cone's entry point.

    Args:
        cone: The mega-cone to split.
        total_files: Total number of files across the codebase.
        dag: The dependency DAG (used for layer-based fallback).

    Returns:
        A list of new ``FeatureCone`` objects. If the cone does not qualify
        as a mega-cone, returns a single-element list containing the original.
    """
    if len(cone.exclusive_files) <= total_files * 0.5:
        return [cone]

    # --- Strategy 1: Split by directory boundary ---
    dir_groups: dict[str, list[str]] = defaultdict(list)
    for filepath in cone.exclusive_files:
        parent = _parent_dir(filepath)
        key = parent if parent else "<root>"
        dir_groups[key].append(filepath)

    if len(dir_groups) >= 2:
        sub_cones: list[FeatureCone] = []
        for dir_name, files in sorted(dir_groups.items()):
            sub_cone_id = f"{cone.cone_id}::{dir_name}"
            sub_cones.append(
                FeatureCone(
                    cone_id=sub_cone_id,
                    entry_point=cone.entry_point,
                    exclusive_files=sorted(files),
                    shared_deps=list(cone.shared_deps),
                    layer=cone.layer,
                    token_count=0,
                )
            )
        logger.info(
            "[REBALANCE] split mega-cone '%s' (%d files) into %d sub-cones by directory",
            cone.cone_id,
            len(cone.exclusive_files),
            len(sub_cones),
        )
        return sub_cones

    # --- Strategy 2: Import-graph clustering (T-12 CRITICAL #2) ---
    # Build a subgraph of only the cone's files and find clusters
    # of tightly connected files.
    cone_file_set = set(cone.exclusive_files)
    sub = dag.subgraph(cone_file_set).copy()

    # Build undirected version for connectivity-based clustering
    undirected = sub.to_undirected()

    # Find connected components first -- disconnected clusters are natural splits
    components = list(nx.connected_components(undirected))

    if len(components) >= 2:
        sub_cones = []
        for idx, component in enumerate(sorted(components, key=lambda c: sorted(c))):
            files = sorted(component)
            sub_cone_id = f"{cone.cone_id}::cluster{idx}"
            sub_cones.append(
                FeatureCone(
                    cone_id=sub_cone_id,
                    entry_point=cone.entry_point,
                    exclusive_files=files,
                    shared_deps=list(cone.shared_deps),
                    layer=cone.layer,
                    token_count=0,
                )
            )
        logger.info(
            "[REBALANCE] split mega-cone '%s' (%d files) into %d sub-cones "
            "by connected components",
            cone.cone_id,
            len(cone.exclusive_files),
            len(sub_cones),
        )
        return sub_cones

    # All files are connected -- use degree-based clustering.
    # Identify hub nodes (high internal degree) vs leaf nodes.
    # Group hub nodes with their immediate neighbors; leftover nodes
    # form a separate group.
    internal_degree: dict[str, int] = {}
    for node in cone_file_set:
        deg = 0
        if dag.has_node(node):
            for succ in dag.successors(node):
                if succ in cone_file_set:
                    deg += 1
            for pred in dag.predecessors(node):
                if pred in cone_file_set:
                    deg += 1
        internal_degree[node] = deg

    if not internal_degree:
        return [cone]

    avg_degree = sum(internal_degree.values()) / len(internal_degree)
    # Hub threshold: files with above-average internal connectivity
    hub_threshold = max(1, avg_degree)

    hubs = {n for n, d in internal_degree.items() if d > hub_threshold}
    non_hubs = cone_file_set - hubs

    if hubs and non_hubs:
        # Assign non-hub nodes to the hub they are most connected to,
        # or keep them in a "peripheral" group
        hub_group = sorted(hubs)
        peripheral_group = sorted(non_hubs)

        sub_cones = [
            FeatureCone(
                cone_id=f"{cone.cone_id}::core",
                entry_point=cone.entry_point,
                exclusive_files=hub_group,
                shared_deps=list(cone.shared_deps),
                layer=cone.layer,
                token_count=0,
            ),
            FeatureCone(
                cone_id=f"{cone.cone_id}::peripheral",
                entry_point=cone.entry_point,
                exclusive_files=peripheral_group,
                shared_deps=list(cone.shared_deps),
                layer=cone.layer,
                token_count=0,
            ),
        ]
        logger.info(
            "[REBALANCE] split mega-cone '%s' (%d files) into core (%d) + "
            "peripheral (%d) by import-graph clustering",
            cone.cone_id,
            len(cone.exclusive_files),
            len(hub_group),
            len(peripheral_group),
        )
        return sub_cones

    # Fallback: DAG-layer splitting
    depths: dict[str, int] = {}
    bfs_queue: list[tuple[str, int]] = [(cone.entry_point, 0)]
    visited: set[str] = set()

    while bfs_queue:
        node, depth = bfs_queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        if node in cone_file_set:
            depths[node] = depth
        if dag.has_node(node):
            for successor in dag.successors(node):
                if successor in cone_file_set and successor not in visited:
                    bfs_queue.append((successor, depth + 1))

    max_depth = max(depths.values()) + 1 if depths else 1
    for f in cone.exclusive_files:
        if f not in depths:
            depths[f] = max_depth

    layer_groups: dict[int, list[str]] = defaultdict(list)
    for filepath, depth in depths.items():
        layer_groups[depth].append(filepath)

    if len(layer_groups) >= 2:
        sub_cones = []
        for layer_idx, files in sorted(layer_groups.items()):
            sub_cone_id = f"{cone.cone_id}::layer{layer_idx}"
            sub_cones.append(
                FeatureCone(
                    cone_id=sub_cone_id,
                    entry_point=cone.entry_point,
                    exclusive_files=sorted(files),
                    shared_deps=list(cone.shared_deps),
                    layer=cone.layer,
                    token_count=0,
                )
            )
        logger.info(
            "[REBALANCE] split mega-cone '%s' (%d files) into %d sub-cones by DAG layer",
            cone.cone_id,
            len(cone.exclusive_files),
            len(sub_cones),
        )
        return sub_cones

    # Unable to split meaningfully
    return [cone]


def _merge_orphan_cones(cones: list[FeatureCone]) -> list[FeatureCone]:
    """Merge single-file cones that share the same parent directory.

    Identifies cones whose ``exclusive_files`` contains exactly one file,
    groups them by directory, and merges groups of 2+ into a combined cone.
    Single-file cones that are alone in their directory pass through unchanged.

    Args:
        cones: The current list of feature cones.

    Returns:
        A new list with orphan cones merged where possible.
    """
    single_file_cones: list[FeatureCone] = []
    non_single_cones: list[FeatureCone] = []

    for cone in cones:
        if len(cone.exclusive_files) == 1:
            single_file_cones.append(cone)
        else:
            non_single_cones.append(cone)

    if not single_file_cones:
        return list(cones)

    dir_groups: dict[str, list[FeatureCone]] = defaultdict(list)
    for cone in single_file_cones:
        parent = _parent_dir(cone.exclusive_files[0])
        key = parent if parent else "<root>"
        dir_groups[key].append(cone)

    result: list[FeatureCone] = list(non_single_cones)

    for dir_name, group in sorted(dir_groups.items()):
        if len(group) < 2:
            result.extend(group)
            continue

        merged_files: list[str] = []
        merged_shared: set[str] = set()
        for cone in group:
            merged_files.extend(cone.exclusive_files)
            merged_shared.update(cone.shared_deps)

        merged_cone_id = f"dir::{dir_name}"
        merged_cone = FeatureCone(
            cone_id=merged_cone_id,
            entry_point=group[0].entry_point,
            exclusive_files=sorted(merged_files),
            shared_deps=sorted(merged_shared),
            layer=0,
            token_count=0,
        )
        result.append(merged_cone)
        logger.info(
            "[REBALANCE] merged %d single-file cones in '%s' -> '%s'",
            len(group),
            dir_name,
            merged_cone_id,
        )

    return result


def _separate_testing_files(cones: list[FeatureCone]) -> list[FeatureCone]:
    """T-12 HIGH #3: Separate testing files from runtime cones.

    For each cone with >= 2 files, check if any are classified as "testing"
    by ``classify_file``.  If a cone contains both testing and non-testing
    files, split the testing files into their own sub-cone.

    Args:
        cones: The current list of feature cones.

    Returns:
        A new list with testing files separated where appropriate.
    """
    result: list[FeatureCone] = []

    for cone in cones:
        if len(cone.exclusive_files) < 2:
            result.append(cone)
            continue

        testing_files: list[str] = []
        runtime_files: list[str] = []

        for f in cone.exclusive_files:
            if classify_file(f) == "testing":
                testing_files.append(f)
            else:
                runtime_files.append(f)

        if not testing_files or not runtime_files:
            # All testing or all runtime -- no split needed
            result.append(cone)
            continue

        # Split: runtime files stay in original cone, testing files get own cone
        runtime_cone = FeatureCone(
            cone_id=cone.cone_id,
            entry_point=cone.entry_point,
            exclusive_files=sorted(runtime_files),
            shared_deps=list(cone.shared_deps),
            layer=cone.layer,
            token_count=0,
        )
        testing_cone = FeatureCone(
            cone_id=f"{cone.cone_id}::testing",
            entry_point=cone.entry_point,
            exclusive_files=sorted(testing_files),
            shared_deps=list(cone.shared_deps),
            layer=cone.layer,
            token_count=0,
        )
        result.append(runtime_cone)
        result.append(testing_cone)
        logger.info(
            "[REBALANCE] separated %d testing files from cone '%s' into '%s'",
            len(testing_files),
            cone.cone_id,
            testing_cone.cone_id,
        )

    return result


def _generate_cone_name(files: list[str]) -> str:
    """T-12 HIGH #4: Generate a meaningful name for a cone based on its files.

    Classifies each file using ``classify_file`` and picks the dominant
    semantic category.  Falls back to the common directory prefix or
    entry-point stem.

    Args:
        files: List of file paths in the cone.

    Returns:
        A human-readable cone name like ``"core-runtime"`` or ``"cli"``.
    """
    if not files:
        return "empty"

    # Classify all files
    categories = [classify_file(f) for f in files]
    category_counts = Counter(categories)

    # Remove "unknown" for name generation (but count it)
    known_counts = {k: v for k, v in category_counts.items() if k != "unknown"}

    if known_counts:
        dominant = max(known_counts, key=known_counts.__getitem__) # type: ignore[arg-type]
        dominant_ratio = known_counts[dominant] / len(files)
        if dominant_ratio >= 0.4:
            return dominant

    # Fallback: use common directory prefix
    dirs = [_parent_dir(f) for f in files]
    unique_dirs = set(dirs)
    if len(unique_dirs) == 1:
        d = unique_dirs.pop()
        if d:
            # Use last directory component
            return posixpath.basename(d)

    # Fallback: use "core" for root-level files, or first file stem
    if all(not _parent_dir(f) for f in files):
        return "core-runtime"

    return posixpath.splitext(posixpath.basename(files[0]))[0]


def _rename_cones(cones: list[FeatureCone]) -> list[FeatureCone]:
    """T-12 HIGH #4: Rename cones with meaningful semantic names.

    Replaces generic ``dir::`` prefixed names and file-path names with
    human-readable names based on semantic classification.

    Args:
        cones: The current list of feature cones.

    Returns:
        A new list with improved cone names. Duplicate names are
        disambiguated with numeric suffixes.
    """
    # Generate candidate names
    candidates: list[tuple[FeatureCone, str]] = []
    for cone in cones:
        base_name = _generate_cone_name(cone.exclusive_files)
        candidates.append((cone, base_name))

    # Disambiguate duplicate names
    name_counts: dict[str, int] = defaultdict(int)
    for _, name in candidates:
        name_counts[name] += 1

    name_used: dict[str, int] = defaultdict(int)
    result: list[FeatureCone] = []
    for cone, name in candidates:
        if name_counts[name] > 1:
            name_used[name] += 1
            final_name = f"{name}-{name_used[name]}"
        else:
            final_name = name

        result.append(
            FeatureCone(
                cone_id=final_name,
                entry_point=cone.entry_point,
                exclusive_files=list(cone.exclusive_files),
                shared_deps=list(cone.shared_deps),
                layer=cone.layer,
                token_count=cone.token_count,
            )
        )

    return result


def rebalance_cones(
    cones: list[FeatureCone],
    total_files: int,
    dag: nx.DiGraph,
) -> list[FeatureCone]:
    """Post-processing pass to rebalance feature cones.

    Applies four transformations:

    1. **Split mega-cones**: Cones with ``len(exclusive_files) > total_files * 0.5``
       are split by directory boundary, import-graph clustering, or DAG layer.

    2. **Merge orphan cones**: Single-file cones (``len(exclusive_files) == 1``)
       sharing the same parent directory are merged into one combined cone.

    3. **Separate testing files** (T-12 HIGH #3): Testing-classified files are
       split out of runtime cones into their own sub-cones.

    4. **Rename cones** (T-12 HIGH #4): Generate meaningful semantic names
       instead of generic directory/file path names.

    Returns a new list of ``FeatureCone`` objects. The input list and its
    cones are never mutated (``FeatureCone`` is a frozen dataclass).

    Args:
        cones: The initial list of feature cones to rebalance.
        total_files: Total number of files in the codebase.
        dag: The dependency DAG (used for mega-cone splitting fallback).

    Returns:
        A rebalanced list of ``FeatureCone`` objects.
    """
    if total_files <= 0 or not cones:
        return list(cones)

    # Step 1: Split mega-cones
    after_split: list[FeatureCone] = []
    for cone in cones:
        after_split.extend(_split_mega_cone(cone, total_files, dag))

    # Step 2: Merge orphan single-file cones
    after_merge = _merge_orphan_cones(after_split)

    # Step 3: Separate testing files from runtime cones (T-12 HIGH #3)
    after_testing = _separate_testing_files(after_merge)

    # Step 4: Rename cones with meaningful names (T-12 HIGH #4)
    after_rename = _rename_cones(after_testing)

    return after_rename


# ---------------------------------------------------------------------------
# SCC Assignment
# ---------------------------------------------------------------------------


def assign_scc_to_cone(
    scc_members: list[str],
    cone_assignments: dict[str, str],
) -> str:
    """Determine which cone an SCC (strongly connected component) belongs to.

    Strategy: Assign SCC to the cone that contains the most SCC members.
    In case of a tie, classify as infrastructure.

    Args:
        scc_members: List of file paths in the SCC.
        cone_assignments: Dictionary mapping file path -> cone_id for non-SCC nodes.

    Returns:
        Cone ID that owns this SCC, or "infrastructure" if tied or unassigned.

    Example:
        >>> members = ["app.py", "ctx.py", "globals.py"]
        >>> assignments = {"app.py": "cone1", "ctx.py": "cone1", "globals.py": "cone2"}
        >>> assign_scc_to_cone(members, assignments)
        'cone1'
    """
    # Count how many SCC members belong to each cone
    cone_member_count: dict[str, int] = defaultdict(int)

    for member in scc_members:
        if member in cone_assignments:
            cone_id = cone_assignments[member]
            cone_member_count[cone_id] += 1

    # No members assigned to any cone
    if not cone_member_count:
        return "infrastructure"

    # Find cone(s) with maximum membership
    max_count = max(cone_member_count.values())
    winners = [cone_id for cone_id, count in cone_member_count.items() if count == max_count]

    # Tie goes to infrastructure
    if len(winners) == 1:
        return winners[0]
    else:
        return "infrastructure"
