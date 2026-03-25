"""Feature Cone extraction algorithm for codebase module grouping.

Implements the core algorithm for identifying feature-based module groups
by analyzing dependency structure in the codebase DAG.

Algorithm Overview:
1. Find feature roots (entry points with in-degree=0)
2. For each root, trace dependencies via weight-aware affinity-decay BFS (T-04)
3. Identify shared infrastructure nodes (dynamic threshold T-05)
4. Rebalance cones: split mega-cones + merge orphans (T-06)
5. Assign SCC groups to dominant cone or infrastructure

This replaces Louvain as the primary grouping strategy in V2.
"""

from __future__ import annotations

import logging
import posixpath
from collections import defaultdict
from dataclasses import dataclass

import networkx as nx

logger = logging.getLogger(__name__)

from src.parser.codebase import CodebaseSnapshot


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHARED_THRESHOLD_MIN = 2
"""Minimum number of cones that must share a node for infrastructure classification."""

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

    # --- Strategy 2: Split by DAG layer (topological depth) ---
    depths: dict[str, int] = {}
    cone_file_set = set(cone.exclusive_files)
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

    # Files not reachable from the entry point get a fallback depth
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


def rebalance_cones(
    cones: list[FeatureCone],
    total_files: int,
    dag: nx.DiGraph,
) -> list[FeatureCone]:
    """Post-processing pass to rebalance feature cones.

    Applies two transformations:

    1. **Split mega-cones**: Cones with ``len(exclusive_files) > total_files * 0.5``
       are split by directory boundary (or by DAG layer as a fallback).

    2. **Merge orphan cones**: Single-file cones (``len(exclusive_files) == 1``)
       sharing the same parent directory are merged into one combined cone.

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

    return after_merge


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
