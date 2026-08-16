"""L2 structural layer: partition files by function, then name the partition.

The partition is computed deterministically from shared signatures; only the
*naming* uses a model, and it runs a constant one-to-two times regardless of
repository size.  The split matters: a partition produced by a model cannot be
reconciled against the signatures, and that reconciliation is the only
mechanical grip this layer has.  So the model may argue for a merge or a split
(:class:`ClusterAdvice`), but the executed partition stays deterministic.

Why signatures rather than communities: Louvain optimises edge density, so a
utility shared by every feature is "close" to all of them and the graph
collapses into one bucket (flask 82.7%, httpx 88.7% before this module).  A
shared signature asks a different question -- *which* entries reach this file.
"Shared by the client and the server" and "shared by auth and caching" are two
groups; asking only whether a file is shared merges them.  Measured after this
module: flask 33.5%, httpx 26.7%.

Requirement anchor (EV-10, user, 2026-04-03), quoted rather than paraphrased:

    我们应该还是从功能出发，将不同的功能作为不同的分类；同时在这些不同的功能中，
    也要维持该功能所拥有的代码层级之间的这种关系。
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import networkx as nx

from src.graph.feature_cone import PublicSurfaceEntry, SurfaceReachability
from src.graph.file_cards import FileCard, clustering_payload

logger = logging.getLogger(__name__)

MAX_CLUSTER_FILES = 12
"""Above this file count a candidate is split by DAG layer (F1 §3.2 depth rule)."""

MAX_CLUSTER_SYMBOLS = 60
"""Above this symbol count a candidate is split by DAG layer (F1 §3.2 depth rule)."""

STRUCTURAL_WORDS = (
    "工具", "通用", "共享", "基础设施", "杂项", "其他", "辅助", "公共",
    "util", "utils", "utility", "common", "shared", "infrastructure",
    "misc", "helper", "helpers", "core", "base", "general", "module",
)
"""Structure words a cluster name must not lean on.

A name like "utility module" tells a reader where code sits, not what it does.
The rule exists because the current partition's worst page is literally named
``shared-infrastructure``.
"""

UNASSIGNED_REASONS = {
    "package_facade": "包门面本身：它声明公共面，不被任何公共面入口反向到达",
    "cli_shim": "命令行入口壳：无人 import，真实实现已挂在它委托的模块上",
    "unreferenced_public_module": "可被外部直接 import，但没有任何公共面入口到达它",
    "outside_graph": "不在运行时依赖图中（解析失败或非源码文件）",
}
"""Every residual carries one of these, so nothing is silently swallowed.

r003 N-3: the previous partition dropped such files without a word.  Sourcetrail
draws them with hatching instead of hiding them; a residual you cannot see is
indistinguishable from a file that does not exist.
"""


class ClusterError(ValueError):
    """Raised when partitioning or naming is given unusable input."""


@dataclass(frozen=True)
class CandidateCluster:
    """A deterministically derived partition cell, before naming.

    ``seed_kind`` records *what kind of seed* produced the cell.  A cluster
    seeded by the public surface answers "what can a caller do with this"; one
    seeded by directory structure answers "where does this sit".  Those are not
    the same claim, so they are not allowed to share a field value -- a reader
    (and the renderer) must be able to tell a capability group from a shelf.
    """

    cluster_id: str
    kind: str
    signature: frozenset[str]
    member_paths: tuple[str, ...]
    symbol_count: int
    layer_index: int | None = None
    seed_kind: str = "public_surface"
    fallback_reason: str | None = None
    signature_group_id: str = ""
    """Cells sharing this belong to one function, split only by DAG layer.

    A layer split is EV-10's second dimension (the level chain inside a
    function), not a second function, so the layers must nest under one INDEX
    entry rather than appear as siblings.  Measured on flask, 5 of 13
    single-file cells are layer slices of 2 functions; reading them as 5
    separate capabilities is what makes the entry list look fragmented.  The
    field exists so a consumer groups on data instead of parsing ``--L<n>`` off
    the id.
    """


@dataclass(frozen=True)
class UnassignedFile:
    """A file no public-surface entry reaches, with the reason it stayed out."""

    path: str
    reason_code: str
    reason: str


@dataclass(frozen=True)
class ClusterRelation:
    """A directed relation between two clusters, carrying edge evidence."""

    to_cluster: str
    kind: str
    edge_evidence: tuple[tuple[str, str], ...]
    evidence_granularity: str = "file"


@dataclass(frozen=True)
class ClusterAdvice:
    """A model's merge/split suggestion. Advisory: the partition stays deterministic."""

    action: str
    cluster_ids: tuple[str, ...]
    paths: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class ClusterRecord:
    """A named cluster (F1 §3.4)."""

    cluster_id: str
    name: str
    purpose: str
    boundary_not: tuple[str, ...]
    member_paths: tuple[str, ...]
    entry_symbol_ids: tuple[str, ...]
    relations: tuple[ClusterRelation, ...]
    confidence: str
    signature: frozenset[str] = frozenset()
    kind: str = "shared"
    seed_kind: str = "public_surface"


@dataclass(frozen=True)
class L2Partition:
    """The full L2 result: clusters, explicit residuals, and the readings."""

    clusters: tuple[ClusterRecord, ...]
    candidates: tuple[CandidateCluster, ...]
    unassigned: tuple[UnassignedFile, ...]
    advice: tuple[ClusterAdvice, ...] = ()
    diagnostics: tuple[str, ...] = ()

    def readings(self, total_symbols: int, total_paths: int) -> dict[str, object]:
        """The three readings F1 §3.7 names as this layer's abort conditions."""
        if total_symbols <= 0 or total_paths <= 0:
            raise ClusterError("readings need positive symbol and path totals")
        sizes = [(c.cluster_id, c.symbol_count) for c in self.candidates]
        largest = max((n for _, n in sizes), default=0)
        confidences = [c.confidence for c in self.clusters]
        return {
            "largest_cluster_symbol_share": round(largest / total_symbols, 4),
            "largest_cluster_id": max(sizes, key=lambda kv: kv[1])[0] if sizes else None,
            "cluster_count": len(self.candidates),
            "unassigned_path_share": round(len(self.unassigned) / total_paths, 4),
            "unassigned_paths": [u.path for u in self.unassigned],
            "confidence_distribution": {
                level: confidences.count(level) for level in ("high", "medium", "low")
            },
            "total_symbols": total_symbols,
            "total_paths": total_paths,
            "cluster_symbol_counts": dict(sizes),
        }


# ---------------------------------------------------------------------------
# Deterministic partition
# ---------------------------------------------------------------------------


def partition_by_shared_signature(
    reachability: SurfaceReachability,
    graph: nx.DiGraph,
    universe: Iterable[str],
    symbols_per_path: Mapping[str, int],
    *,
    max_files: int = MAX_CLUSTER_FILES,
    max_symbols: int = MAX_CLUSTER_SYMBOLS,
) -> tuple[tuple[CandidateCluster, ...], tuple[UnassignedFile, ...]]:
    """Group files by which surface entries reach them.

    ``|S(f)| == 1`` puts a file in that entry's own cluster; ``|S(f)| >= 2``
    groups it with every file carrying the *same* signature.  Groups over
    budget split further by DAG layer inside the group, which is also what
    keeps the second half of EV-10 (the level relationships inside a function)
    visible instead of flattened.

    Raises:
        ClusterError: If the universe is empty.
    """
    paths = sorted(set(universe))
    if not paths:
        raise ClusterError("partition needs a non-empty universe")

    grouped: dict[frozenset[str], list[str]] = defaultdict(list)
    unassigned: list[UnassignedFile] = []
    for path in paths:
        signature = reachability.signature_of(path)
        if not signature:
            code = _residual_reason_code(path, graph)
            unassigned.append(
                UnassignedFile(path=path, reason_code=code, reason=UNASSIGNED_REASONS[code])
            )
            continue
        grouped[signature].append(path)

    candidates: list[CandidateCluster] = []
    for signature, members in sorted(grouped.items(), key=lambda kv: (-len(kv[1]), sorted(kv[0]))):
        kind = "exclusive" if len(signature) == 1 else "shared"
        base_id = _signature_id(signature, kind)
        symbol_total = sum(symbols_per_path.get(p, 0) for p in members)
        over_budget = len(members) > max_files or symbol_total > max_symbols
        if not over_budget or len(members) == 1:
            candidates.append(
                CandidateCluster(
                    cluster_id=base_id,
                    kind=kind,
                    signature=signature,
                    member_paths=tuple(sorted(members)),
                    symbol_count=symbol_total,
                    signature_group_id=base_id,
                )
            )
            continue
        for layer_index, layer_members in enumerate(_dag_layers(graph, members)):
            candidates.append(
                CandidateCluster(
                    cluster_id=f"{base_id}--L{layer_index}",
                    kind=kind,
                    signature=signature,
                    member_paths=tuple(sorted(layer_members)),
                    symbol_count=sum(symbols_per_path.get(p, 0) for p in layer_members),
                    layer_index=layer_index,
                    signature_group_id=base_id,
                )
            )

    logger.info(
        "Shared-signature partition: %d candidates, %d unassigned files",
        len(candidates),
        len(unassigned),
    )
    return tuple(candidates), tuple(unassigned)


DIRECTORY_FALLBACK_REASON = (
    "公共面种子到达不了本文件，按 F1 §2.5 第一条回退到目录结构作二级种子"
)
"""Recorded on every fallback cluster, because §2.5 requires the retreat be visible."""

PACKAGE_ROOT_KEY = "(package_root)"
"""Group key for files sitting directly in the package root, which has no directory name."""

DIRECT_MEMBER_SUFFIX = "(directly)"
"""Distinguishes a directory's own files from its subdirectories after a second split."""


def apply_directory_fallback(
    unassigned: Sequence[UnassignedFile],
    symbols_per_path: Mapping[str, int],
    *,
    max_files: int = MAX_CLUSTER_FILES,
) -> tuple[tuple[CandidateCluster, ...], tuple[UnassignedFile, ...]]:
    """Group residual files by directory so nothing is left outside the partition.

    F1 §2.5 pre-registers this retreat for repositories whose public surface is
    too small to reach most files.  Applied per residual file rather than per
    repository: the same condition (no surface entry reaches this file) holds
    for three files in flask and for 523 in django, and the fix is the same.

    What this buys and what it does not: measured across five repositories it
    takes unassigned 30-58% to zero and coverage to 100%, and it leaves the
    largest cluster untouched -- the shares that move do so because the
    denominator grew.  A directory name answers "where", so these clusters are
    marked ``seed_kind="directory"`` and never merged with surface-seeded ones.

    Returns:
        The fallback clusters and the residuals they absorbed.  The absorbed
        records keep their original ``reason_code``, so the reason a file needed
        the fallback survives into the rendered page (r003 N-3).
    """
    by_path = {residual.path: residual for residual in unassigned}
    if not by_path:
        return (), ()

    clusters: list[CandidateCluster] = []
    for key, members in _directory_groups(sorted(by_path), max_files=max_files).items():
        cluster_id = f"dirseed--{_directory_slug(key)}--L0"
        clusters.append(
            CandidateCluster(
                cluster_id=cluster_id,
                kind="directory_fallback",
                signature=frozenset({f"dir:{key}"}),
                member_paths=tuple(members),
                symbol_count=sum(symbols_per_path.get(p, 0) for p in members),
                layer_index=0,
                seed_kind="directory",
                fallback_reason=DIRECTORY_FALLBACK_REASON,
                signature_group_id=cluster_id,
            )
        )

    absorbed = tuple(by_path[path] for cluster in clusters for path in cluster.member_paths)
    logger.info(
        "Directory fallback: %d clusters absorbing %d residual files",
        len(clusters),
        len(absorbed),
    )
    return tuple(clusters), absorbed


def _directory_groups(
    paths: Sequence[str],
    *,
    max_files: int,
) -> dict[str, list[str]]:
    """Group by first path segment, splitting one level deeper when over budget.

    Only one extra level: recursing would chase the file-count budget down to
    leaf directories and turn the fallback into a directory mirror.  Groups that
    stay fat after the second level are left fat and handled by the renderer's
    existing depth rule (F1 §3.2), which is the layer that owns page size.
    """
    level_one: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        level_one[_directory_key(path, 1)].append(path)

    groups: dict[str, list[str]] = {}
    for key in sorted(level_one):
        members = sorted(level_one[key])
        if len(members) <= max_files or key == PACKAGE_ROOT_KEY:
            groups[key] = members
            continue
        level_two: dict[str, list[str]] = defaultdict(list)
        for path in members:
            segments = path.split("/")
            if len(segments) <= 2:
                level_two[f"{key}/{DIRECT_MEMBER_SUFFIX}"].append(path)
            else:
                level_two["/".join(segments[:2])].append(path)
        for sub_key in sorted(level_two):
            groups[sub_key] = sorted(level_two[sub_key])
    return groups


def _directory_key(path: str, level: int) -> str:
    """First *level* path segments, or the package-root key for shallow paths."""
    segments = path.split("/")
    if len(segments) <= level:
        return PACKAGE_ROOT_KEY
    return "/".join(segments[:level])


def _directory_slug(key: str) -> str:
    """Filesystem- and id-safe form of a directory group key."""
    return key.replace("/", "-").replace("(", "").replace(")", "").lower()


def _residual_reason_code(path: str, graph: nx.DiGraph) -> str:
    """Classify why a file was reached by no surface entry."""
    if path not in graph:
        return "outside_graph"
    if path.endswith("__main__.py"):
        return "cli_shim"
    if path.endswith("__init__.py"):
        return "package_facade"
    return "unreferenced_public_module"


def _signature_id(signature: frozenset[str], kind: str) -> str:
    """Stable, readable, and *unique* id for a signature group.

    The readable head is truncated to three stems, so it alone collides between
    different signatures sharing a prefix (measured on httpx: three collisions
    across 19 clusters).  A collision silently merges two clusters in every
    downstream path-to-cluster map, so the full signature is folded into a
    short digest and appended.
    """
    stems = sorted(_path_stem(p) for p in signature)
    digest = hashlib.sha256("\x1f".join(sorted(signature)).encode("utf-8")).hexdigest()[:6]
    if kind == "exclusive":
        return f"feature--{stems[0]}--{digest}"
    head = "-".join(stems[:3])
    suffix = f"-plus{len(stems) - 3}" if len(stems) > 3 else ""
    return f"shared--{head}{suffix}--{digest}"


def _path_stem(path: str) -> str:
    """Readable stem for a path (``json/__init__.py`` -> ``json``)."""
    cleaned = path[:-3] if path.endswith(".py") else path
    if cleaned.endswith("/__init__"):
        cleaned = cleaned[: -len("/__init__")]
    if cleaned == "__init__":
        return "root"
    stem = cleaned.replace("/", "-").lstrip("_")
    return stem or cleaned.replace("/", "-")


def _dag_layers(graph: nx.DiGraph, members: Sequence[str]) -> list[list[str]]:
    """Split *members* into dependency layers, callers before callees.

    Cycles inside the group are condensed first, so a circular import cannot
    make layering fail; every member lands in exactly one layer.
    """
    subgraph = graph.subgraph([m for m in members if m in graph]).copy()
    missing = [m for m in members if m not in graph]
    if subgraph.number_of_nodes() == 0:
        return [sorted(members)]

    condensed = nx.condensation(subgraph)
    depth: dict[int, int] = {}
    for node in nx.topological_sort(condensed):
        preds = list(condensed.predecessors(node))
        depth[node] = 1 + max((depth[p] for p in preds), default=-1)

    layers: dict[int, list[str]] = defaultdict(list)
    for scc_node, level in depth.items():
        for member in condensed.nodes[scc_node]["members"]:
            layers[level].append(member)
    if missing:
        layers[max(layers) + 1 if layers else 0].extend(missing)
    return [sorted(layers[level]) for level in sorted(layers)]


def cluster_relations(
    candidates: Sequence[CandidateCluster],
    graph: nx.DiGraph,
) -> dict[str, tuple[ClusterRelation, ...]]:
    """Derive inter-cluster relations with concrete edge evidence.

    Evidence is file-level here because the resolved symbol-level call graph is
    too sparse to carry it: measured on flask, 74 of 901 call relations resolve
    to an in-repository symbol.  ``evidence_granularity`` records that fact on
    every relation rather than letting a file pair pass as a symbol pair.
    """
    owner: dict[str, str] = {}
    for candidate in candidates:
        for path in candidate.member_paths:
            owner[path] = candidate.cluster_id

    evidence: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for source, target in graph.edges():
        src_cluster = owner.get(source)
        dst_cluster = owner.get(target)
        if src_cluster is None or dst_cluster is None or src_cluster == dst_cluster:
            continue
        evidence[(src_cluster, dst_cluster)].append((source, target))

    result: dict[str, list[ClusterRelation]] = defaultdict(list)
    for (src_cluster, dst_cluster), pairs in sorted(evidence.items()):
        result[src_cluster].append(
            ClusterRelation(
                to_cluster=dst_cluster,
                kind="uses",
                edge_evidence=tuple(sorted(pairs)),
                evidence_granularity="file",
            )
        )
    return {k: tuple(v) for k, v in result.items()}


@dataclass(frozen=True)
class MemberCohesion:
    """How well one file fits the cluster it was placed in."""

    path: str
    symbol_count: int
    internal_degree: int
    kind_divergence: float | None


@dataclass(frozen=True)
class ClusterCohesion:
    """Deterministic evidence that a cluster's members belong together.

    ``flag_reasons`` names which signal fired, and ``low_cohesion`` is just
    "some signal fired".  Both mark a cluster as *worth a look*, never as wrong:
    deciding whether a member really belongs means reading the name against the
    code, which is the judgement a mechanical gate cannot make
    (``rules/code-and-agent.md`` §1).  This layer only narrows the candidates.

    ``seed_kind`` travels with the score because a directory-seeded cluster is a
    shelf by construction -- low cohesion there is expected, not a finding, and
    consumers must be able to split the list before counting.
    """

    cluster_id: str
    seed_kind: str
    member_count: int
    symbol_count: int
    internal_edges: int
    edge_density: float | None
    isolated_members: tuple[str, ...]
    zero_symbol_members: tuple[str, ...]
    max_kind_divergence: float | None
    members: tuple[MemberCohesion, ...]
    flag_reasons: tuple[str, ...]
    low_cohesion: bool


@dataclass(frozen=True)
class SingleFileClusterDistance:
    """Pairwise signals for deciding whether singleton candidates need review.

    ``dependency_edge_density`` is deliberately named at file level: the
    graph supplied to this layer is the runtime import/dependency projection,
    not the sparse resolved symbol-call graph.  It is a useful proxy for
    adjacency, not proof that two files implement one capability.
    """

    left_cluster_id: str
    right_cluster_id: str
    left_path: str
    right_path: str
    same_signature_group: bool
    signature_jaccard: float
    directory_proximity: float
    dependency_edge_density: float
    edge_evidence: tuple[tuple[str, str], ...]


COHESION_FLAGS = {
    "zero_symbol_member": (
        "成员在 L1 里一个符号都没有：簇名只可能是从别的成员推出来的，与它无关"
    ),
    "isolated_member": (
        "成员与簇内其它成员没有任何运行时依赖边：它进这个簇只因为共享签名相同"
    ),
}
"""What each flag means, so a consumer reads the reason instead of guessing it."""


def cluster_cohesion(
    candidates: Sequence[CandidateCluster],
    graph: nx.DiGraph,
    symbol_kinds_by_path: Mapping[str, Mapping[str, int]],
) -> tuple[ClusterCohesion, ...]:
    """Score every cluster on whether its members hang together.

    Two independent signals, because they catch different failures:

    * **Zero-symbol member.**  A file that contributes no symbol contributes no
      content, so whatever the cluster ended up named, the name was derived from
      the other members.  This is the ``ctx.py`` + ``typing.py`` case: flask's
      ``typing.py`` is module-level type aliases only and carries 0 of that
      cluster's 30 symbols, so a name about pushing an application context can
      not be describing it.
    * **Isolated member.**  A member with no runtime import or call edge to any
      sibling sits in the cluster only because the same entries reach it.

    Neither subsumes the other, and the first is the one that matters here: the
    edge signal alone misses ``typing.py`` outright, because ``ctx.py`` really
    does import it at runtime.  Reporting only edges would have produced a
    confident green on the one case that is known to be wrong.
    """
    members_by_cluster = {c.cluster_id: set(c.member_paths) for c in candidates}
    results: list[ClusterCohesion] = []
    for candidate in candidates:
        members = members_by_cluster[candidate.cluster_id]
        internal_pairs = {
            (source, target)
            for source, target in graph.edges()
            if source in members and target in members and source != target
        }
        degree: dict[str, int] = {path: 0 for path in candidate.member_paths}
        for source, target in internal_pairs:
            degree[source] += 1
            degree[target] += 1

        member_scores = tuple(
            MemberCohesion(
                path=path,
                symbol_count=sum((symbol_kinds_by_path.get(path) or {}).values()),
                internal_degree=degree[path],
                kind_divergence=_kind_divergence(path, candidate.member_paths, symbol_kinds_by_path),
            )
            for path in candidate.member_paths
        )
        size = len(candidate.member_paths)
        possible = size * (size - 1)
        isolated = tuple(m.path for m in member_scores if size > 1 and m.internal_degree == 0)
        empty = tuple(m.path for m in member_scores if m.symbol_count == 0)
        divergences = [m.kind_divergence for m in member_scores if m.kind_divergence is not None]

        reasons: list[str] = []
        if empty:
            reasons.append("zero_symbol_member")
        if isolated:
            reasons.append("isolated_member")

        results.append(
            ClusterCohesion(
                cluster_id=candidate.cluster_id,
                seed_kind=candidate.seed_kind,
                member_count=size,
                symbol_count=candidate.symbol_count,
                internal_edges=len(internal_pairs),
                edge_density=round(len(internal_pairs) / possible, 4) if possible else None,
                isolated_members=isolated,
                zero_symbol_members=empty,
                max_kind_divergence=round(max(divergences), 4) if divergences else None,
                members=member_scores,
                flag_reasons=tuple(reasons),
                low_cohesion=bool(reasons),
            )
        )
    return tuple(results)


def _kind_divergence(
    path: str,
    members: Sequence[str],
    symbol_kinds_by_path: Mapping[str, Mapping[str, int]],
) -> float | None:
    """1 - cosine similarity between this file's symbol kinds and its siblings'.

    ``None`` when either side has no symbols: an empty vector has no direction,
    and reporting 0.0 there would read as "identical to its siblings", which is
    the opposite of what an empty file means.  The zero-symbol flag carries that
    case instead, so it stays visible rather than collapsing into a null.
    """
    own = symbol_kinds_by_path.get(path) or {}
    rest: dict[str, int] = defaultdict(int)
    for other in members:
        if other == path:
            continue
        for kind, count in (symbol_kinds_by_path.get(other) or {}).items():
            rest[kind] += count
    if not own or not rest:
        return None
    keys = set(own) | set(rest)
    dot = sum(own.get(k, 0) * rest.get(k, 0) for k in keys)
    own_norm = sum(v * v for v in own.values()) ** 0.5
    rest_norm = sum(v * v for v in rest.values()) ** 0.5
    if not own_norm or not rest_norm:
        return None
    return round(1.0 - dot / (own_norm * rest_norm), 4)


def measure_single_file_cluster_distances(
    candidates: Sequence[CandidateCluster],
    graph: nx.DiGraph,
) -> tuple[SingleFileClusterDistance, ...]:
    """Measure merge-relevant signals between one-file candidate clusters.

    The function reports every singleton pair.  Consumers can filter
    ``same_signature_group`` to inspect DAG layer slices, while retaining the
    other pairs as a negative comparison.  A signature match alone is not a
    merge decision: layer slices intentionally share a signature, but their
    directory and dependency signals can still disagree.
    """
    singletons = sorted(
        (candidate for candidate in candidates if len(candidate.member_paths) == 1),
        key=lambda candidate: (candidate.member_paths[0], candidate.cluster_id),
    )
    edge_set = {(source, target) for source, target in graph.edges()}
    distances: list[SingleFileClusterDistance] = []
    for index, left in enumerate(singletons):
        left_path = left.member_paths[0]
        for right in singletons[index + 1 :]:
            right_path = right.member_paths[0]
            union = left.signature | right.signature
            intersection = left.signature & right.signature
            signature_jaccard = len(intersection) / len(union) if union else 1.0
            edge_evidence = tuple(
                sorted(
                    edge
                    for edge in ((left_path, right_path), (right_path, left_path))
                    if edge in edge_set
                )
            )
            group_match = bool(
                left.signature_group_id
                and left.signature_group_id == right.signature_group_id
            )
            if not left.signature_group_id and not right.signature_group_id:
                group_match = left.signature == right.signature
            distances.append(
                SingleFileClusterDistance(
                    left_cluster_id=left.cluster_id,
                    right_cluster_id=right.cluster_id,
                    left_path=left_path,
                    right_path=right_path,
                    same_signature_group=group_match,
                    signature_jaccard=round(signature_jaccard, 4),
                    directory_proximity=_directory_proximity(left_path, right_path),
                    dependency_edge_density=round(len(edge_evidence) / 2, 4),
                    edge_evidence=edge_evidence,
                )
            )
    return tuple(distances)


def _directory_proximity(left_path: str, right_path: str) -> float:
    """Return common-directory-prefix depth normalized to the deeper path."""
    left_parts = tuple(left_path.split("/")[:-1])
    right_parts = tuple(right_path.split("/")[:-1])
    if left_parts == right_parts:
        return 1.0
    common = 0
    for left_part, right_part in zip(left_parts, right_parts):
        if left_part != right_part:
            break
        common += 1
    depth = max(len(left_parts), len(right_parts), 1)
    return round(common / depth, 4)


def entry_symbols_for(
    candidate: CandidateCluster,
    surface: Sequence[PublicSurfaceEntry],
    symbol_ids_by_path: Mapping[str, Sequence[str]],
) -> tuple[str, ...]:
    """Public-surface symbols that a cluster owns."""
    members = set(candidate.member_paths)
    result: list[str] = []
    for entry in surface:
        if entry.defining_path not in members:
            continue
        for symbol_id in symbol_ids_by_path.get(entry.defining_path, ()):
            if symbol_id.endswith(f"::{entry.defining_name}"):
                result.append(symbol_id)
    return tuple(sorted(set(result)))


# ---------------------------------------------------------------------------
# Naming (the only model call in this layer)
# ---------------------------------------------------------------------------


def build_naming_prompt(
    candidates: Sequence[CandidateCluster],
    cards: Sequence[FileCard],
    relations: Mapping[str, Sequence[ClusterRelation]],
    *,
    repo_name: str,
) -> str:
    """Assemble the L2 naming prompt.

    The payload is card fields only (see :func:`clustering_payload`); the model
    is asked to name a partition it is not allowed to change.
    """
    cards_by_path = {card.path: card for card in cards}
    blocks = []
    for candidate in candidates:
        member_cards = [cards_by_path[p] for p in candidate.member_paths if p in cards_by_path]
        blocks.append(
            {
                "cluster_id": candidate.cluster_id,
                "kind": candidate.kind,
                "reached_by_entries": sorted(candidate.signature),
                "files": clustering_payload(member_cards),
                "uses_clusters": [r.to_cluster for r in relations.get(candidate.cluster_id, ())],
            }
        )

    return f"""You are naming a fixed partition of the `{repo_name}` codebase.

The partition is already computed and is NOT yours to change. Each cluster below
is the set of files reachable from the same set of public API entry points.

For every cluster, return:
- `name`: what capability this cluster provides, in the language a user of the
  library would use ("send an HTTP request", "render a template"). A name that
  describes structure rather than capability is rejected. Specifically, do not
  use: {", ".join(STRUCTURAL_WORDS)}.
- `purpose`: one sentence.
- `boundary_not`: 1-3 things this cluster does NOT do, each a concrete
  capability a reader might otherwise assume lives here. It must not be the
  negation of `purpose` ("does not render templates" for a template cluster is
  rejected). Leave nothing empty.
- `relations`: for each cluster in `uses_clusters`, one sentence on what it uses
  it for.
- `confidence`: "high" | "medium" | "low" -- how well the evidence below
  supports the name. Answer honestly; "low" is a useful signal, not a failure.

You may additionally propose merges or splits in `advice` (action: "merge" or
"split", with `cluster_ids`, `paths`, and `rationale`). These are suggestions
only; the partition itself stays as given.

Evidence (file cards; no source code is provided by design):

{json.dumps(blocks, ensure_ascii=False, indent=1)}

Return a single JSON object, no prose around it:
{{"clusters": [{{"cluster_id": "...", "name": "...", "purpose": "...",
  "boundary_not": ["..."], "relations": [{{"to_cluster": "...", "why": "..."}}],
  "confidence": "high"}}],
 "advice": [{{"action": "merge", "cluster_ids": ["..."], "paths": ["..."],
  "rationale": "..."}}]}}
"""


def parse_naming_response(text: str) -> tuple[dict[str, dict[str, object]], tuple[ClusterAdvice, ...]]:
    """Parse the naming model's JSON reply.

    Raises:
        ClusterError: If no JSON object can be recovered.
    """
    payload = _extract_json_object(text)
    if payload is None:
        raise ClusterError("naming response contained no JSON object")

    named: dict[str, dict[str, object]] = {}
    for item in payload.get("clusters", []):
        if not isinstance(item, dict) or "cluster_id" not in item:
            continue
        named[str(item["cluster_id"])] = item

    advice: list[ClusterAdvice] = []
    for item in payload.get("advice", []):
        if not isinstance(item, dict):
            continue
        advice.append(
            ClusterAdvice(
                action=str(item.get("action", "")),
                cluster_ids=tuple(str(c) for c in item.get("cluster_ids", [])),
                paths=tuple(str(p) for p in item.get("paths", [])),
                rationale=str(item.get("rationale", "")),
            )
        )
    return named, tuple(advice)


def _extract_json_object(text: str) -> dict[str, object] | None:
    """Recover the outermost JSON object from a model reply."""
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    start = stripped.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(stripped)):
        char = stripped[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(stripped[start : index + 1])
                except json.JSONDecodeError:
                    return None
                return parsed if isinstance(parsed, dict) else None
    return None


def name_is_structural(name: str) -> bool:
    """Whether a cluster name leans on a structure word instead of a capability."""
    lowered = name.lower()
    return any(word in lowered for word in STRUCTURAL_WORDS)


def boundary_is_purpose_negation(boundary: str, purpose: str) -> bool:
    """Whether a ``boundary_not`` entry merely negates ``purpose``.

    Catches the degenerate answer ("renders templates" / "does not render
    templates"), which satisfies a non-empty check while carrying no
    information.
    """
    negations = ("not ", "no ", "does not", "doesn't", "不", "无", "非")
    stripped = boundary.lower()
    if not any(marker in stripped for marker in negations):
        return False
    core = re.sub(r"(does not|doesn't|not |no |不会|不做|不|无|非)", " ", stripped)
    core_tokens = {t for t in re.split(r"[\s,，。.;；、]+", core) if len(t) > 2}
    purpose_tokens = {t for t in re.split(r"[\s,，。.;；、]+", purpose.lower()) if len(t) > 2}
    if not core_tokens:
        return False
    overlap = len(core_tokens & purpose_tokens) / len(core_tokens)
    return overlap >= 0.6


def assemble_clusters(
    candidates: Sequence[CandidateCluster],
    named: Mapping[str, Mapping[str, object]],
    relations: Mapping[str, Sequence[ClusterRelation]],
    entry_symbols: Mapping[str, Sequence[str]],
) -> tuple[tuple[ClusterRecord, ...], tuple[str, ...]]:
    """Merge model names onto the deterministic partition, flagging weak names.

    A cluster the model did not name still becomes a record, marked ``low``
    confidence with a placeholder name.  Dropping it would let a naming failure
    shrink the partition, and the file count is the one thing that must not move.
    """
    records: list[ClusterRecord] = []
    diagnostics: list[str] = []
    for candidate in candidates:
        payload = named.get(candidate.cluster_id, {})
        name = str(payload.get("name", "")).strip()
        purpose = str(payload.get("purpose", "")).strip()
        boundary_raw = payload.get("boundary_not", [])
        boundary = tuple(
            str(b).strip() for b in boundary_raw if isinstance(b, str) and str(b).strip()
        ) if isinstance(boundary_raw, list) else ()
        confidence = str(payload.get("confidence", "low")).lower()
        if confidence not in {"high", "medium", "low"}:
            confidence = "low"

        if not name:
            name = f"<unnamed:{candidate.cluster_id}>"
            confidence = "low"
            diagnostics.append(f"unnamed_cluster:{candidate.cluster_id}")
        elif name_is_structural(name):
            diagnostics.append(f"structural_name:{candidate.cluster_id}:{name}")
        if payload and not boundary:
            # F1 §2.3: an empty `boundary_not` means the model could not say what
            # the cluster excludes, which is the documented reject condition.  It
            # only applies when the model answered: an absent payload means naming
            # was never run (the deterministic-only path), and rejecting there
            # would make a partition unbuildable without a model call.
            diagnostics.append(f"empty_boundary_not:{candidate.cluster_id}")
            raise ClusterError(
                f"naming response rejected: boundary_not is empty for "
                f"{candidate.cluster_id}"
            )
        for item in boundary:
            if boundary_is_purpose_negation(item, purpose):
                diagnostics.append(
                    f"boundary_negates_purpose:{candidate.cluster_id}:{item}"
                )

        records.append(
            ClusterRecord(
                cluster_id=candidate.cluster_id,
                name=name,
                purpose=purpose,
                boundary_not=boundary,
                member_paths=candidate.member_paths,
                entry_symbol_ids=tuple(entry_symbols.get(candidate.cluster_id, ())),
                relations=tuple(relations.get(candidate.cluster_id, ())),
                confidence=confidence,
                signature=candidate.signature,
                kind=candidate.kind,
                seed_kind=candidate.seed_kind,
            )
        )
    return tuple(records), tuple(diagnostics)
