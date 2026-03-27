"""Feature Cone extraction via Louvain community detection.

V3 algorithm: Louvain partitioning on weighted dependency graph, followed by
infrastructure identification, test-file separation, and semantic renaming.
"""
from __future__ import annotations

import logging
import posixpath
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

import networkx as nx

from src.graph.semantic_hints import classify_file, is_reexport_facade, directory_affinity_score
from src.parser.codebase import CodebaseSnapshot

logger = logging.getLogger(__name__)

_EXTRA_INFRA_STEMS = frozenset({
    "abc", "log", "logging", "compat", "_compat",
    "globals", "types", "base", "registry",
})
"""Additional file stems that indicate infrastructure when combined
with above-median in-degree."""


@dataclass(frozen=True)
class FeatureCone:
    """A cohesive feature group: exclusive files + shared infrastructure deps."""

    cone_id: str
    entry_point: str
    exclusive_files: tuple[str, ...]
    shared_deps: tuple[str, ...]
    layer: int = 0
    token_count: int = 0


# ---------------------------------------------------------------------------
# Core pipeline helpers
# ---------------------------------------------------------------------------


def _louvain_communities(dag: nx.DiGraph) -> list[set[str]]:
    """Louvain community detection on undirected graph (preserving weights)."""
    from networkx.algorithms.community import louvain_communities as _louvain

    if dag.number_of_nodes() == 0:
        return []

    udag = dag.to_undirected()
    communities = _louvain(udag, weight="weight", resolution=1.0, seed=42)
    return [set(c) for c in communities]


def _merge_small_communities(
    communities: list[set[str]],
    dag: nx.DiGraph,
    min_size: int = 3,
) -> list[set[str]]:
    """Merge communities smaller than *min_size* into their best neighbour."""
    if not communities:
        return communities

    node_to_comm: dict[str, int] = {}
    for idx, comm in enumerate(communities):
        for node in comm:
            node_to_comm[node] = idx

    small_indices: list[int] = []
    large_indices: list[int] = []
    for idx, comm in enumerate(communities):
        (small_indices if len(comm) < min_size else large_indices).append(idx)

    if not large_indices:
        return communities

    merged = {i: set(communities[i]) for i in large_indices}
    for si in small_indices:
        small_files = communities[si]
        edge_counts: dict[int, int] = defaultdict(int)
        for f in small_files:
            for neighbor in list(dag.predecessors(f)) + list(dag.successors(f)):
                ni = node_to_comm.get(neighbor)
                if ni is not None and ni in merged:
                    edge_counts[ni] += 1

        if edge_counts:
            max_edges = max(edge_counts.values())
            best_target = None
            best_score = -1.0
            for target_idx, edges in edge_counts.items():
                # Calculate average directory affinity between small and target communities
                target_files = merged[target_idx]
                if target_files and small_files:
                    total_affinity = sum(
                        directory_affinity_score(sf, tf)
                        for sf in small_files
                        for tf in list(target_files)[:20]  # Cap to avoid O(n^2) explosion
                    )
                    avg_affinity = total_affinity / (len(small_files) * min(len(target_files), 20))
                else:
                    avg_affinity = 0.0
                score = edges + avg_affinity * max_edges
                if score > best_score:
                    best_score = score
                    best_target = target_idx
        else:
            best_target = large_indices[0]
            small_dirs = {posixpath.dirname(f) for f in small_files}
            for li in large_indices:
                large_dirs = {posixpath.dirname(f) for f in merged[li]}
                if small_dirs & large_dirs:
                    best_target = li
                    break

        merged[best_target].update(small_files)
        for f in small_files:
            node_to_comm[f] = best_target

    return list(merged.values())


def _identify_infrastructure(
    dag: nx.DiGraph,
    communities: list[set[str]],
    root_path: str | None = None,
) -> set[str]:
    """Identify infra nodes via semantic classification + in-degree analysis.

    Criteria (any one sufficient):
    1. classify_file returns config/utils/exceptions AND above-median in-degree
    2. File stem in _EXTRA_INFRA_STEMS AND above-median in-degree
    3. __init__.py that is a re-export facade (via is_reexport_facade)
    """
    infra_categories = {"config", "utils", "exceptions"}

    in_degrees = dict(dag.in_degree())
    if not in_degrees:
        return set()

    median_indeg = sorted(in_degrees.values())[len(in_degrees) // 2]
    high_indeg_threshold = max(2, median_indeg)

    # Build file -> community index
    f2comm: dict[str, int] = {}
    for i, comm in enumerate(communities):
        for f in comm:
            f2comm[f] = i

    n_communities = len(communities)
    cross_cut_threshold = max(2, int(n_communities * 0.4))

    infra: set[str] = set()
    for node in dag.nodes():
        classification = classify_file(node)
        has_high_indegree = in_degrees.get(node, 0) >= high_indeg_threshold

        # Criterion 1: semantic infra type + above-median in-degree
        if classification in infra_categories and has_high_indegree:
            infra.add(node)
            continue

        # Criterion 2: extra infra stems + above-median in-degree
        stem = posixpath.splitext(posixpath.basename(node))[0].lower()
        if stem in _EXTRA_INFRA_STEMS and has_high_indegree:
            infra.add(node)
            continue

        # Criterion 3: __init__.py re-export facade (no in-degree requirement)
        if root_path and node.endswith("__init__.py"):
            try:
                if is_reexport_facade(node, root_path):
                    infra.add(node)
                    continue
            except Exception:  # noqa: BLE001
                pass

        # Criterion 4: imported by files in >= 40% of communities
        importer_communities: set[int] = set()
        for pred in dag.predecessors(node):
            ci = f2comm.get(pred)
            if ci is not None:
                importer_communities.add(ci)

        if len(importer_communities) >= cross_cut_threshold:
            infra.add(node)

    return infra


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def extract_feature_cones(
    dag: nx.DiGraph,
    snapshot: CodebaseSnapshot,
    shared_threshold: int | None = None,
) -> tuple[dict[str, FeatureCone], frozenset[str]]:
    """Extract feature cones from the dependency DAG using Louvain communities.

    Args:
        dag: Weighted dependency DAG.
        snapshot: Codebase snapshot for metadata.
        shared_threshold: Legacy parameter (ignored). Kept for API compat.

    Returns:
        (cone_dict, infrastructure_frozenset)

    Raises:
        ValueError: If the DAG has no nodes.
    """
    if dag.number_of_nodes() == 0:
        raise ValueError("Cannot extract feature cones from an empty DAG")

    communities = _louvain_communities(dag)
    communities = _merge_small_communities(communities, dag, min_size=3)
    infrastructure_nodes = _identify_infrastructure(
        dag, communities, root_path=snapshot.root_path,
    )

    # Build FeatureCone objects from communities
    cones: dict[str, FeatureCone] = {}

    for comm in communities:
        # Remove infra files from this community's exclusive files
        exclusive = sorted(f for f in comm if f not in infrastructure_nodes)
        if not exclusive:
            continue

        # Entry point: the file with highest out-degree in this community
        entry = max(exclusive, key=lambda f: dag.out_degree(f))
        shared_refs = sorted(f for f in comm if f in infrastructure_nodes)

        cone_id = entry  # Will be renamed later
        cones[cone_id] = FeatureCone(
            cone_id=cone_id,
            entry_point=entry,
            exclusive_files=tuple(exclusive),
            shared_deps=tuple(shared_refs),
        )

    # Post-processing: separate tests, then rename
    cone_list = _separate_testing_files(list(cones.values()))
    cone_list = _rename_cones(cone_list)
    return {c.cone_id: c for c in cone_list}, frozenset(infrastructure_nodes)


# ---------------------------------------------------------------------------
# Post-processing helpers
# ---------------------------------------------------------------------------


def _parent_dir(filepath: str) -> str:
    """Parent directory of *filepath* (posixpath; ``""`` for root-level)."""
    return posixpath.dirname(filepath)


def _separate_testing_files(cones: list[FeatureCone]) -> list[FeatureCone]:
    """Split testing files out of mixed cones into their own sub-cones."""
    result: list[FeatureCone] = []
    for cone in cones:
        if len(cone.exclusive_files) < 2:
            result.append(cone)
            continue

        testing = [f for f in cone.exclusive_files if classify_file(f) == "testing"]
        runtime = [f for f in cone.exclusive_files if classify_file(f) != "testing"]

        if not testing or not runtime:
            result.append(cone)
            continue

        result.append(FeatureCone(
            cone.cone_id, cone.entry_point, tuple(sorted(runtime)),
            tuple(cone.shared_deps), cone.layer, 0,
        ))
        result.append(FeatureCone(
            f"{cone.cone_id}::testing", cone.entry_point, tuple(sorted(testing)),
            tuple(cone.shared_deps), cone.layer, 0,
        ))
        logger.info(
            "[REBALANCE] separated %d testing files from cone '%s'",
            len(testing), cone.cone_id,
        )
    return result


def _generate_cone_name(files: Sequence[str]) -> str:
    """Derive a human-readable cone name from its files' semantic categories."""
    if not files:
        return "empty"

    categories = [classify_file(f) for f in files]
    known = {k: v for k, v in Counter(categories).items() if k != "unknown"}
    if known:
        dominant = max(known, key=known.__getitem__)  # type: ignore[arg-type]
        if known[dominant] / len(files) >= 0.4:
            return dominant

    # Fallback: use common directory prefix
    dirs = [_parent_dir(f) for f in files]
    unique_dirs = set(dirs)
    if len(unique_dirs) == 1:
        d = unique_dirs.pop()
        if d:
            return posixpath.basename(d)

    # Fallback: use deepest common directory across all files
    if unique_dirs:
        all_dirs = sorted(unique_dirs)
        if all_dirs:
            common = posixpath.commonpath(all_dirs) if len(all_dirs) > 1 else all_dirs[0]
            if common:
                return posixpath.basename(common)

    # Fallback: use "core" for root-level files, or first file stem
    if all(not _parent_dir(f) for f in files):
        return "core-runtime"

    # Use first file's stem, but replace __init__ with parent dir name
    stem = posixpath.splitext(posixpath.basename(files[0]))[0]
    if stem == "__init__":
        parent = _parent_dir(files[0])
        if parent:
            return posixpath.basename(parent)
    return stem


def _semantic_suffix(files: Sequence[str]) -> str:
    """Short semantic suffix from most-common file stem (excluding __init__)."""
    stems = [
        posixpath.splitext(posixpath.basename(f))[0]
        for f in files
        if posixpath.splitext(posixpath.basename(f))[0] != "__init__"
    ]
    if stems:
        counts = Counter(stems)
        return counts.most_common(1)[0][0]
    # All files are __init__.py -- use deepest dir
    dirs = [_parent_dir(f) for f in files if _parent_dir(f)]
    if dirs:
        return posixpath.basename(dirs[0])
    return "misc"


def _rename_cones(cones: list[FeatureCone]) -> list[FeatureCone]:
    """Rename cones with semantic names; disambiguate duplicates via suffixes."""
    # Generate candidate names
    candidates: list[tuple[FeatureCone, str]] = []
    for cone in cones:
        base_name = _generate_cone_name(cone.exclusive_files)
        candidates.append((cone, base_name))

    # Count duplicates
    name_counts: dict[str, int] = defaultdict(int)
    for _, name in candidates:
        name_counts[name] += 1

    # Track used suffixes per name to avoid clashes
    name_used_suffixes: dict[str, set[str]] = defaultdict(set)
    name_numeric: dict[str, int] = defaultdict(int)
    result: list[FeatureCone] = []

    for cone, name in candidates:
        if name_counts[name] > 1:
            suffix = _semantic_suffix(cone.exclusive_files)
            # If this suffix was already used for this name, add numeric
            if suffix in name_used_suffixes[name]:
                name_numeric[name] += 1
                final_name = f"{name}-{suffix}-{name_numeric[name]}"
            else:
                name_used_suffixes[name].add(suffix)
                final_name = f"{name}-{suffix}"
        else:
            final_name = name

        result.append(
            FeatureCone(
                cone_id=final_name,
                entry_point=cone.entry_point,
                exclusive_files=tuple(cone.exclusive_files),
                shared_deps=tuple(cone.shared_deps),
                layer=cone.layer,
                token_count=cone.token_count,
            )
        )

    return result
