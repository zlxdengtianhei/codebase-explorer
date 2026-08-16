"""Cluster projection: clus shared-signature partition, else ledger.module_id.

Capability names live on L2 result / namer cache, not yet written back into
partition JSON. This module merges them at load time. Zero LLM.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

from src.semantic.models import SemanticLedger
from src.synthesis.variant_b.edges import file_dag_layers
from src.synthesis.variant_b.text import slug_base
from src.synthesis.variant_b.types import Cluster


UNASSIGNED_ID = "unassigned"


def file_module_assignments(
    ledger: SemanticLedger,
) -> tuple[dict[str, str], dict[str, str]]:
    symbols_by_file: dict[str, list] = {path: [] for path in ledger.files}
    for symbol in ledger.symbols.values():
        symbols_by_file[symbol.path].append(symbol)
    raw_by_file: dict[str, str] = {}
    reasons: dict[str, str] = {}
    for path in sorted(ledger.files):
        candidates = [item.module_id for item in symbols_by_file[path] if item.module_id]
        counts = Counter(candidates)
        if counts:
            raw_by_file[path] = min(counts, key=lambda item: (-counts[item], item))
        else:
            raw_by_file[path] = "unclassified"
            status = ledger.files[path].status.value
            extra = ledger.files[path].reason.strip()
            reasons[path] = extra or f"file status `{status}` and no symbol carries module_id"
    return raw_by_file, reasons


def load_name_map(path: Path | None) -> dict[str, dict[str, str]]:
    """cluster_id → {name, purpose} from l2_result JSON or a router receipt."""

    if path is None or not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    clusters = data.get("clusters") if isinstance(data, dict) else None
    if clusters is None and isinstance(data, dict) and isinstance(data.get("result_text"), str):
        inner = json.loads(data["result_text"])
        clusters = inner.get("clusters") if isinstance(inner, dict) else None
    out: dict[str, dict[str, str]] = {}
    for row in clusters or ():
        if not isinstance(row, dict):
            continue
        cluster_id = str(row.get("cluster_id") or "").strip()
        name = str(row.get("name") or "").strip()
        if not cluster_id or not name:
            continue
        out[cluster_id] = {
            "name": name,
            "purpose": str(row.get("purpose") or "").strip(),
        }
    return out


def _fallback_display(candidate: Mapping[str, object]) -> str:
    members = [str(item) for item in (candidate.get("member_paths") or ())]
    stems: list[str] = []
    for path in members[:3]:
        name = Path(path).name
        parent = Path(path).parent.name
        stems.append(f"{parent}/{name}" if name == "__init__.py" and parent else name)
    extra = f" +{len(members) - 3}" if len(members) > 3 else ""
    layer = candidate.get("layer_index")
    layer_s = f" L{layer}" if isinstance(layer, int) else ""
    kind = "独占" if candidate.get("kind") == "exclusive" else "共享"
    body = ", ".join(stems) + extra + layer_s
    return f"{kind} {body}".strip() or str(candidate.get("cluster_id") or "cluster")


def _unique_slugs(pairs: list[tuple[str, str]]) -> dict[str, str]:
    """cluster_id → directory slug from display name; hash suffix on collision."""

    by_base: dict[str, list[str]] = {}
    for cluster_id, display in pairs:
        by_base.setdefault(slug_base(display), []).append(cluster_id)
    result: dict[str, str] = {}
    for base, cluster_ids in by_base.items():
        for cluster_id in cluster_ids:
            suffix = ""
            if len(cluster_ids) > 1:
                suffix = "-" + cluster_id[-6:] if len(cluster_id) >= 6 else "-" + cluster_id
            slug = (base + suffix).strip("-") or "cluster"
            result[cluster_id] = slug
    used: dict[str, str] = {}
    out: dict[str, str] = {}
    for cluster_id, slug in result.items():
        if slug in used and used[slug] != cluster_id:
            slug = f"{slug}-{cluster_id[-6:]}"
        used[slug] = cluster_id
        out[cluster_id] = slug
    return out


def _symbols_for(ledger: SemanticLedger, files: tuple[str, ...]) -> tuple[str, ...]:
    wanted = set(files)
    return tuple(
        sorted(symbol_id for symbol_id, record in ledger.symbols.items() if record.path in wanted)
    )


def _cluster_record(
    *,
    cluster_id: str,
    slug: str,
    display: str,
    files: tuple[str, ...],
    ledger: SemanticLedger,
    edges: set[tuple[str, str]],
    unassigned_reason: str | None = None,
    purpose: str = "",
    name_source: str = "cluster_id",
) -> Cluster:
    symbol_path = {symbol_id: record.path for symbol_id, record in ledger.symbols.items()}
    return Cluster(
        cluster_id=cluster_id,
        slug=slug,
        display=display,
        files=files,
        symbol_ids=_symbols_for(ledger, files),
        dag_layers=file_dag_layers(files, symbol_path, edges),
        unassigned_reason=unassigned_reason,
        purpose=purpose,
        name_source=name_source,
    )


def _build_from_module_id(ledger: SemanticLedger, edges: set[tuple[str, str]]) -> tuple[Cluster, ...]:
    raw_by_file, reasons = file_module_assignments(ledger)
    pairs = [(raw, raw) for raw in sorted(set(raw_by_file.values()))]
    slugs = _unique_slugs(pairs)
    files_by_raw: dict[str, list[str]] = {}
    for path, raw in raw_by_file.items():
        files_by_raw.setdefault(raw, []).append(path)
    clusters: list[Cluster] = []
    for raw in sorted(files_by_raw):
        files = tuple(sorted(files_by_raw[raw]))
        unassigned = None
        if raw in {"unclassified", UNASSIGNED_ID}:
            unassigned = "; ".join(f"{path}: {reasons[path]}" for path in files if path in reasons)
        clusters.append(
            _cluster_record(
                cluster_id=raw,
                slug=slugs[raw],
                display=slugs[raw],
                files=files,
                ledger=ledger,
                edges=edges,
                unassigned_reason=unassigned,
                name_source="module_id",
            )
        )
    return tuple(clusters)


def _build_from_partition(
    ledger: SemanticLedger,
    edges: set[tuple[str, str]],
    partition_path: Path,
    names: Mapping[str, dict[str, str]],
) -> tuple[Cluster, ...]:
    data = json.loads(partition_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("candidates"), list):
        raise ValueError(f"clus partition must contain candidates: {partition_path}")
    covered: set[str] = set()
    pending: list[dict[str, object]] = []
    for raw in data["candidates"]:
        if not isinstance(raw, dict):
            continue
        cluster_id = str(raw.get("cluster_id") or "").strip()
        files = tuple(str(item) for item in (raw.get("member_paths") or ()) if str(item).strip())
        if not cluster_id or not files:
            continue
        covered.update(files)
        named = names.get(cluster_id) or {}
        display = str(named.get("name") or "").strip() or _fallback_display(raw)
        pending.append(
            {
                "cluster_id": cluster_id,
                "files": files,
                "display": display,
                "purpose": str(named.get("purpose") or ""),
                "name_source": "l2_name" if named.get("name") else "partition_fallback",
            }
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
            covered.add(path)

    slug_pairs = [(str(item["cluster_id"]), str(item["display"])) for item in pending]
    if leftovers:
        slug_pairs.append((UNASSIGNED_ID, UNASSIGNED_ID))
    slugs = _unique_slugs(slug_pairs)

    clusters = [
        _cluster_record(
            cluster_id=str(item["cluster_id"]),
            slug=slugs[str(item["cluster_id"])],
            display=str(item["display"]),
            files=tuple(item["files"]),  # type: ignore[arg-type]
            ledger=ledger,
            edges=edges,
            purpose=str(item["purpose"]),
            name_source=str(item["name_source"]),
        )
        for item in pending
    ]
    if leftovers:
        leftover_paths = tuple(path for path, _ in leftovers)
        clusters.append(
            _cluster_record(
                cluster_id=UNASSIGNED_ID,
                slug=slugs[UNASSIGNED_ID],
                display=UNASSIGNED_ID,
                files=leftover_paths,
                ledger=ledger,
                edges=edges,
                unassigned_reason="; ".join(f"{path}: {reason}" for path, reason in leftovers),
                name_source="partition_unassigned",
            )
        )
    return tuple(clusters)


def build_clusters(
    ledger: SemanticLedger,
    edges: set[tuple[str, str]],
    *,
    partition_path: Path | None = None,
    names_path: Path | None = None,
) -> tuple[Cluster, ...]:
    if partition_path is None:
        return _build_from_module_id(ledger, edges)
    return _build_from_partition(ledger, edges, Path(partition_path), load_name_map(names_path))


def symbol_cluster(clusters: tuple[Cluster, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for cluster in clusters:
        for symbol_id in cluster.symbol_ids:
            out[symbol_id] = cluster.cluster_id
    return out


def file_cluster(clusters: tuple[Cluster, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for cluster in clusters:
        for path in cluster.files:
            out[path] = cluster.cluster_id
    return out


def cluster_by_id(clusters: tuple[Cluster, ...]) -> Mapping[str, Cluster]:
    return {cluster.cluster_id: cluster for cluster in clusters}


def partition_cluster_ids(clusters: tuple[Cluster, ...]) -> tuple[str, ...]:
    return tuple(cluster.cluster_id for cluster in clusters if cluster.cluster_id != UNASSIGNED_ID)
