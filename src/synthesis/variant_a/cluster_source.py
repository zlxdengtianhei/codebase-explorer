"""Cluster → page-tree input. Today's source is ledger ``module_id``.

The page tree consumes ``ClusterInput`` only. When ``clus`` lands L2
shared-signature clusters, write a ``cbe-cluster-input-1`` JSON file and
pass ``--clusters``; this module does not need to change.

L2 names live in ``l2_result_*.json`` ``clusters[]`` (name / purpose /
boundary_not). Join them here by ``cluster_id``; do not wait for clus to
write names back into the partition file.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from src.semantic.models import SemanticLedger
from src.synthesis.variant_a.models import CLUSTER_INPUT_SCHEMA, ClusterBundle, ClusterInput


STRUCTURAL_NAME_RE = re.compile(
    r"(工具|通用|共享|基础设施|独占|PART-?\d*|shared[\s-]*infra)",
    re.IGNORECASE,
)
_SLUG_KEEP = re.compile(r"[a-z0-9]+")


class ClusterSource(Protocol):
    def load(self, ledger: SemanticLedger, ir_edges: set[tuple[str, str]]) -> tuple[ClusterInput, ...]:
        ...


def _slug(raw: str) -> str:
    tokens = _SLUG_KEEP.findall(raw.lower().replace("_", "-"))
    return "-".join(tokens) or "cluster"


def extract_l2_names(data: Mapping[str, object]) -> dict[str, tuple[str, str, tuple[str, ...]]]:
    """cluster_id → (name, purpose, boundary_not)."""

    out: dict[str, tuple[str, str, tuple[str, ...]]] = {}
    raw_clusters = data.get("clusters")
    if not isinstance(raw_clusters, list):
        return out
    for raw in raw_clusters:
        if not isinstance(raw, dict):
            continue
        cluster_id = str(raw.get("cluster_id") or "")
        name = str(raw.get("name") or "").strip()
        if not cluster_id or not name:
            continue
        purpose = str(raw.get("purpose") or "").strip()
        boundary_raw = raw.get("boundary_not") or ()
        if isinstance(boundary_raw, str):
            boundary = (boundary_raw.strip(),) if boundary_raw.strip() else ()
        else:
            boundary = tuple(str(item).strip() for item in boundary_raw if str(item).strip())
        out[cluster_id] = (name, purpose, boundary)
    return out


def apply_l2_names(
    clusters: tuple[ClusterInput, ...],
    names: Mapping[str, tuple[str, str, tuple[str, ...]]],
) -> tuple[ClusterInput, ...]:
    if not names:
        return clusters
    filled: list[ClusterInput] = []
    for cluster in clusters:
        hit = names.get(cluster.cluster_id)
        if hit is None or cluster.is_unassigned:
            filled.append(cluster)
            continue
        name, purpose, boundary = hit
        filled.append(
            cluster.model_copy(
                update={
                    "display_name": name,
                    "purpose": purpose or cluster.purpose,
                    "boundary_not": boundary or cluster.boundary_not,
                }
            )
        )
    return tuple(filled)


def discover_l2_names_path(partition_path: Path) -> Path | None:
    name = partition_path.name
    if name.startswith("partition_") and name.endswith(".json"):
        sibling = partition_path.with_name("l2_result_" + name[len("partition_") :])
        if sibling.is_file():
            return sibling
    return None


def cluster_dir_map(clusters: tuple[ClusterInput, ...] | list[ClusterInput]) -> dict[str, str]:
    """Stable unique directory names. Prefer the capability ``display_name``."""

    used: set[str] = set()
    mapping: dict[str, str] = {}
    reserved = {"index", "overlay", "unassigned", "_overlay", "_unassigned"}
    for cluster in clusters:
        if cluster.is_unassigned:
            mapping[cluster.cluster_id] = "_unassigned"
            continue
        base = _slug(cluster.display_name) if cluster.purpose else _slug(cluster.cluster_id)
        slug = base
        n = 2
        while slug in used or slug in reserved:
            slug = f"{base}-{n}"
            n += 1
        used.add(slug)
        mapping[cluster.cluster_id] = slug
    return mapping


def _file_layers(
    paths: tuple[str, ...],
    ir_edges: set[tuple[str, str]],
    ledger: SemanticLedger,
) -> dict[str, int]:
    """Topological layers inside one cluster. Layer 0 = no intra-cluster callers."""

    path_set = set(paths)
    file_of = {sid: rec.path for sid, rec in ledger.symbols.items()}
    inbound: dict[str, set[str]] = {path: set() for path in paths}
    outbound: dict[str, set[str]] = {path: set() for path in paths}
    for src, dst in ir_edges:
        src_path = file_of.get(src)
        dst_path = file_of.get(dst)
        if src_path in path_set and dst_path in path_set and src_path != dst_path:
            outbound[src_path].add(dst_path)
            inbound[dst_path].add(src_path)

    remaining = set(paths)
    layers: dict[str, int] = {}
    layer = 0
    while remaining:
        frontier = [path for path in sorted(remaining) if not (inbound[path] & remaining)]
        if not frontier:
            for path in sorted(remaining):
                layers[path] = layer
            break
        for path in frontier:
            layers[path] = layer
            remaining.remove(path)
        layer += 1
    return layers


def _unassigned_reason(path: str, ledger: SemanticLedger) -> str:
    record = ledger.files.get(path)
    status = record.status.value if record is not None else "missing"
    if status == "no_symbols":
        return (
            "no_symbols: file has no FunctionDef/ClassDef; module_id cannot "
            "ride on a symbol, so the file was not clustered"
        )
    symbols = [item for item in ledger.symbols.values() if item.path == path]
    if not symbols:
        return f"{status}: no symbols recorded for this path"
    if any(item.module_id for item in symbols):
        return ""
    return "unclassified: symbols carry no module_id"


class ExistingLedgerModuleSource:
    """Reproduce today's clustering: majority ``module_id`` per file."""

    def load(self, ledger: SemanticLedger, ir_edges: set[tuple[str, str]]) -> tuple[ClusterInput, ...]:
        symbols_by_file: dict[str, list] = {path: [] for path in ledger.files}
        for symbol in ledger.symbols.values():
            symbols_by_file[symbol.path].append(symbol)

        owner: dict[str, str] = {}
        unassigned_paths: list[str] = []
        unassigned_reasons: dict[str, str] = {}
        for path in sorted(ledger.files):
            candidates = [item.module_id for item in symbols_by_file[path] if item.module_id]
            if candidates:
                counts = Counter(candidates)
                owner[path] = min(counts, key=lambda item: (-counts[item], item))
            else:
                unassigned_paths.append(path)
                unassigned_reasons[path] = _unassigned_reason(path, ledger)

        grouped: dict[str, list[str]] = defaultdict(list)
        for path, cluster_id in owner.items():
            grouped[cluster_id].append(path)

        clusters: list[ClusterInput] = []
        for cluster_id, paths in sorted(grouped.items()):
            path_tuple = tuple(sorted(paths))
            symbol_ids = tuple(
                sorted(
                    sid
                    for sid, rec in ledger.symbols.items()
                    if rec.path in path_tuple
                )
            )
            clusters.append(
                ClusterInput(
                    cluster_id=cluster_id,
                    display_name=" ".join(cluster_id.replace("_", " ").replace("-", " ").split()),
                    paths=path_tuple,
                    symbol_ids=symbol_ids,
                    dag_layer_by_path=_file_layers(path_tuple, ir_edges, ledger),
                    purpose="",
                    unassigned_reason="",
                )
            )
        if unassigned_paths:
            clusters.append(
                ClusterInput(
                    cluster_id="unassigned",
                    display_name="unassigned",
                    paths=tuple(unassigned_paths),
                    symbol_ids=(),
                    dag_layer_by_path={path: 0 for path in unassigned_paths},
                    purpose="",
                    unassigned_reason="; ".join(
                        f"{path}: {unassigned_reasons[path]}" for path in unassigned_paths
                    ),
                )
            )
        return tuple(clusters)


def _clus_display_name(candidate: Mapping[str, object]) -> str:
    members = [str(item) for item in (candidate.get("member_paths") or ())]
    stems: list[str] = []
    for path in members[:3]:
        name = Path(path).name
        parent = Path(path).parent.name
        stems.append(f"{parent}/{name}" if name == "__init__.py" and parent else name)
    extra = f" +{len(members) - 3}" if len(members) > 3 else ""
    layer = candidate.get("layer_index")
    layer_s = f" · L{layer}" if layer is not None else ""
    kind = "独占" if candidate.get("kind") == "exclusive" else "共享"
    return f"{kind} {', '.join(stems)}{extra}{layer_s}" or str(candidate.get("cluster_id") or "cluster")


def _candidate_rows(data: Mapping[str, object]) -> list[object]:
    raw_candidates = data.get("candidates")
    if isinstance(raw_candidates, list) and raw_candidates:
        return raw_candidates
    raw_named = data.get("clusters")
    if isinstance(raw_named, list) and raw_named:
        if any(isinstance(item, dict) and item.get("member_paths") for item in raw_named):
            return raw_named
    return []


def clusters_from_clus_partition(
    data: Mapping[str, object],
    ledger: SemanticLedger,
    ir_edges: set[tuple[str, str]],
) -> tuple[ClusterInput, ...]:
    """Accept the clus ``partition_*.json`` or ``l2_result_*.json`` shape."""

    raw_candidates = _candidate_rows(data)
    if not raw_candidates:
        raise ValueError("clus partition must contain a candidates list")
    covered: set[str] = set()
    clusters: list[ClusterInput] = []
    for raw in raw_candidates:
        if not isinstance(raw, dict):
            continue
        cluster_id = str(raw.get("cluster_id") or "")
        paths = tuple(str(item) for item in (raw.get("member_paths") or ()))
        if not cluster_id or not paths:
            continue
        covered.update(paths)
        path_set = set(paths)
        symbol_ids = tuple(sorted(sid for sid, rec in ledger.symbols.items() if rec.path in path_set))
        layer_hint = raw.get("layer_index")
        default_layer = int(layer_hint) if isinstance(layer_hint, int) else 0
        layers = _file_layers(paths, ir_edges, ledger) or {path: default_layer for path in paths}
        clusters.append(
            ClusterInput(
                cluster_id=cluster_id,
                display_name=_clus_display_name(raw),
                paths=paths,
                symbol_ids=symbol_ids,
                dag_layer_by_path=dict(layers),
                purpose="",
                unassigned_reason="",
            )
        )
    leftovers: list[tuple[str, str]] = []
    for raw in data.get("unassigned") or ():
        if isinstance(raw, dict):
            path = str(raw.get("path") or "")
            reason = str(raw.get("reason") or raw.get("reason_code") or "unassigned")
        else:
            path, reason = str(raw), "unassigned"
        if path and path not in covered:
            leftovers.append((path, reason))
            covered.add(path)
    for path in ledger.files:
        if path not in covered:
            leftovers.append((path, "not in L2 partition"))
    names = extract_l2_names(data)
    if leftovers:
        leftover_paths = tuple(path for path, _ in leftovers)
        leftover_set = set(leftover_paths)
        clusters.append(
            ClusterInput(
                cluster_id="unassigned",
                display_name="unassigned",
                paths=leftover_paths,
                symbol_ids=tuple(
                    sorted(sid for sid, rec in ledger.symbols.items() if rec.path in leftover_set)
                ),
                dag_layer_by_path={path: 0 for path in leftover_paths},
                purpose="",
                unassigned_reason="; ".join(f"{path}: {reason}" for path, reason in leftovers),
            )
        )
    return apply_l2_names(tuple(clusters), names)


class JsonClusterSource:
    """Load ``cbe-cluster-input-1``, a clus partition, or an L2 result."""

    def __init__(self, path: Path, names_path: Path | None = None) -> None:
        self.path = path
        self.names_path = names_path

    def load(self, ledger: SemanticLedger, ir_edges: set[tuple[str, str]]) -> tuple[ClusterInput, ...]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("cluster json must be an object")
        clus_shaped = data.get("schema") != CLUSTER_INPUT_SCHEMA and (
            bool(_candidate_rows(data)) or bool(data.get("candidates"))
        )
        if clus_shaped:
            filled = list(clusters_from_clus_partition(data, ledger, ir_edges))
        else:
            bundle = ClusterBundle.model_validate(data)
            filled = []
            for cluster in bundle.clusters:
                layers = cluster.dag_layer_by_path or _file_layers(cluster.paths, ir_edges, ledger)
                filled.append(cluster.model_copy(update={"dag_layer_by_path": dict(layers)}))
        extra_names: dict[str, tuple[str, str, tuple[str, ...]]] = {}
        sidecar = self.names_path or discover_l2_names_path(self.path)
        if sidecar is not None and sidecar.resolve() != self.path.resolve():
            extra = json.loads(sidecar.read_text(encoding="utf-8"))
            if isinstance(extra, dict):
                extra_names = extract_l2_names(extra)
        return apply_l2_names(tuple(filled), extra_names)


def load_clusters(
    ledger: SemanticLedger,
    ir_edges: set[tuple[str, str]],
    *,
    json_path: Path | None = None,
    l2_names_path: Path | None = None,
) -> tuple[ClusterInput, ...]:
    source: ClusterSource
    if json_path is not None:
        source = JsonClusterSource(json_path, names_path=l2_names_path)
    else:
        source = ExistingLedgerModuleSource()
    return source.load(ledger, ir_edges)


def cluster_dir_name(cluster_id: str) -> str:
    return _slug(cluster_id)
