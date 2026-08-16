"""Deterministic functional-cluster inputs and one-call batch planning."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence

from src.semantic.models import SemanticLedger

from .models import BatchPlan, ClusterRecord, FileCard, SymbolCard, first_sentence, stable_digest


_PATH_SAFE = re.compile(r"[^a-z0-9]+")


def _coerce_ledger(value: SemanticLedger | Mapping[str, object]) -> SemanticLedger:
    if isinstance(value, SemanticLedger):
        return value
    if isinstance(value, Mapping):
        return SemanticLedger.model_validate(value)
    raise TypeError("ledger must be a SemanticLedger or JSON mapping")


def _slug(value: str) -> str:
    base = _PATH_SAFE.sub("-", value.lower()).strip("-") or "cluster"
    return base


def _file_revision(ledger: SemanticLedger, path: str) -> str:
    record = ledger.files[path]
    rows = [f"file={path}", f"status={record.status.value}", f"reason={record.reason}"]
    rows.extend(
        f"{symbol_id}\t{symbol.content_hash}"
        for symbol_id, symbol in sorted(ledger.symbols.items())
        if symbol.path == path
    )
    return stable_digest(rows)


def _symbol_one_liner(ledger: SemanticLedger, symbol_id: str) -> str:
    record = ledger.symbols[symbol_id]
    if record.explanation is None:
        return "等待确定层语义解释；本页不补写源码推断。"
    return first_sentence(record.explanation.text)


def build_file_cards(
    ledger_value: SemanticLedger | Mapping[str, object],
    *,
    file_revisions: Mapping[str, str] | None = None,
) -> tuple[FileCard, ...]:
    """Project the ledger into the C input contract without reading source bytes."""

    ledger = _coerce_ledger(ledger_value)
    revision_map = dict(file_revisions or {})
    cards: list[FileCard] = []
    for path, status in sorted(ledger.files.items()):
        symbols = tuple(
            sorted(symbol_id for symbol_id, symbol in ledger.symbols.items() if symbol.path == path)
        )
        purpose = (
            f"{path} 的确定层解释状态为 {status.status.value}；包含 {len(symbols)} 个可枚举符号。"
        )
        cards.append(
            FileCard(
                path=path,
                purpose=purpose,
                symbol_ids=symbols,
                revision=revision_map.get(path, _file_revision(ledger, path)),
                line_count=max((ledger.symbols[sid].span[1] for sid in symbols), default=0),
            )
        )
    return tuple(cards)


def build_symbol_cards(
    ledger_value: SemanticLedger | Mapping[str, object],
) -> tuple[SymbolCard, ...]:
    ledger = _coerce_ledger(ledger_value)
    return tuple(
        SymbolCard(
            symbol_id=symbol_id,
            path=record.path,
            qualified_name=record.qualified_name,
            one_liner=_symbol_one_liner(ledger, symbol_id),
            span=record.span,
            content_hash=record.content_hash,
            fresh=record.is_fresh,
        )
        for symbol_id, record in sorted(ledger.symbols.items())
    )


def _citation_edges(ledger: SemanticLedger) -> tuple[tuple[str, str], ...]:
    known = set(ledger.symbols)
    return tuple(
        sorted(
            {
                (symbol_id, cited)
                for symbol_id, record in ledger.symbols.items()
                if record.explanation is not None
                for cited in record.explanation.cited_symbol_ids
                if cited in known and cited != symbol_id
            }
        )
    )


def _layers(symbol_ids: Sequence[str], edges: Iterable[tuple[str, str]]) -> tuple[tuple[str, ...], ...]:
    """Return deterministic DAG layers; cycles are one explicit residual layer."""

    nodes = set(symbol_ids)
    outgoing: dict[str, set[str]] = {node: set() for node in nodes}
    indegree: dict[str, int] = {node: 0 for node in nodes}
    for source, target in edges:
        if source not in nodes or target not in nodes or target in outgoing[source]:
            continue
        outgoing[source].add(target)
        indegree[target] += 1
    remaining = set(nodes)
    result: list[tuple[str, ...]] = []
    while remaining:
        ready = tuple(sorted(node for node in remaining if indegree[node] == 0))
        if not ready:
            result.append(tuple(sorted(remaining)))
            break
        result.append(ready)
        remaining.difference_update(ready)
        for source in ready:
            for target in outgoing[source]:
                indegree[target] -= 1
    return tuple(result)


def build_cluster_records(
    ledger_value: SemanticLedger | Mapping[str, object],
    *,
    cluster_by_file: Mapping[str, str],
    cluster_names: Mapping[str, str] | None = None,
    cluster_purposes: Mapping[str, str] | None = None,
    explicit_edges: Iterable[tuple[str, str]] = (),
    dag_layers_by_cluster: Mapping[str, Sequence[Sequence[str]]] | None = None,
    file_revisions: Mapping[str, str] | None = None,
) -> tuple[ClusterRecord, ...]:
    """Turn current L2 output into C's batch input.

    Functional ownership is supplied by L2; this function does not invent a
    Louvain partition.  Files without an assignment are explicit
    ``unassigned`` facts rather than silently dropped.
    """

    ledger = _coerce_ledger(ledger_value)
    file_cards = {card.path: card for card in build_file_cards(ledger, file_revisions=file_revisions)}
    symbol_cards = {card.symbol_id: card for card in build_symbol_cards(ledger)}
    by_cluster: dict[str, list[FileCard]] = defaultdict(list)
    for path in sorted(ledger.files):
        cluster_id = str(cluster_by_file.get(path, "unassigned"))
        by_cluster[cluster_id].append(file_cards[path])
    symbols_by_cluster: dict[str, list[SymbolCard]] = defaultdict(list)
    for card in file_cards.values():
        cluster_id = str(cluster_by_file.get(card.path, "unassigned"))
        symbols_by_cluster[cluster_id].extend(symbol_cards[sid] for sid in card.symbol_ids)

    all_edges = set(_citation_edges(ledger)) | set(explicit_edges)
    name_map = dict(cluster_names or {})
    purpose_map = dict(cluster_purposes or {})
    layer_map = dag_layers_by_cluster or {}
    records: list[ClusterRecord] = []
    for cluster_id in sorted(by_cluster):
        cluster_symbols = tuple(sorted(symbols_by_cluster.get(cluster_id, ()), key=lambda item: item.symbol_id))
        symbol_ids = {card.symbol_id for card in cluster_symbols}
        internal_edges = tuple(sorted(edge for edge in all_edges if edge[0] in symbol_ids and edge[1] in symbol_ids))
        supplied_layers = layer_map.get(cluster_id)
        layers = (
            tuple(tuple(str(item) for item in layer) for layer in supplied_layers)
            if supplied_layers is not None
            else _layers(tuple(symbol_ids), internal_edges)
        )
        records.append(
            ClusterRecord(
                cluster_id=cluster_id,
                name=name_map.get(cluster_id, cluster_id),
                purpose=purpose_map.get(
                    cluster_id,
                    f"功能簇 {cluster_id} 的文件与符号事实；语义边界由 L2 记录。",
                ),
                files=tuple(sorted(by_cluster[cluster_id], key=lambda item: item.path)),
                symbols=cluster_symbols,
                edges=internal_edges,
                dag_layers=layers,
            )
        )
    return tuple(records)


def _part_paths(base: str, symbol_count: int) -> tuple[str, ...]:
    parts = max(1, (symbol_count + 39) // 40)
    if parts == 1:
        return (base,)
    stem, suffix = base.rsplit("/DETAIL.md", 1) if "/DETAIL.md" in base else (base[:-3], "")
    return tuple(f"{stem}/PART-{number}.md" for number in range(1, parts + 1))


def plan_batches(
    clusters: Sequence[ClusterRecord],
    *,
    split_at_three_layers: bool = True,
    max_batch_calls: int = 12,
) -> tuple[BatchPlan, ...]:
    """Plan one producer call per cluster or cluster DAG layer.

    Symbol pagination is a render concern: ``part_paths`` may contain several
    pages, but all parts share one LLM batch and therefore one call receipt.
    """

    if max_batch_calls < 1:
        raise ValueError("max_batch_calls must be positive")
    used_slugs: dict[str, str] = {}
    plans: list[BatchPlan] = []
    for cluster in clusters:
        slug = _slug(cluster.cluster_id)
        if slug in used_slugs and used_slugs[slug] != cluster.cluster_id:
            slug = f"{slug}-{hashlib.sha256(cluster.cluster_id.encode()).hexdigest()[:8]}"
        used_slugs[slug] = cluster.cluster_id
        layer_groups = cluster.dag_layers if split_at_three_layers and cluster.layer_count >= 3 else (cluster.symbol_ids,)
        for index, layer_symbols in enumerate(layer_groups, start=1):
            layer_name = f"layer-{index:02d}" if len(layer_groups) > 1 else "cluster"
            base = f"clusters/{slug}/{layer_name}/DETAIL.md" if layer_name != "cluster" else f"clusters/{slug}/DETAIL.md"
            paths = _part_paths(base, len(layer_symbols))
            files = tuple(
                sorted({symbol.path for symbol in cluster.symbols if symbol.symbol_id in set(layer_symbols)})
            ) or cluster.file_paths
            plans.append(
                BatchPlan(
                    batch_id=f"{cluster.cluster_id}:{layer_name}",
                    cluster_id=cluster.cluster_id,
                    cluster_name=cluster.name,
                    layer=layer_name,
                    symbol_ids=tuple(layer_symbols),
                    file_paths=files,
                    output_path=paths[0],
                    part_paths=paths,
                )
            )
    if split_at_three_layers and len(plans) > max_batch_calls:
        # The architecture permits a whole functional cluster as one call.
        # Keep DAG layers in the input facts and let deterministic pagination
        # preserve the page cap without reintroducing per-file calls.
        return plan_batches(
            clusters,
            split_at_three_layers=False,
            max_batch_calls=max_batch_calls,
        )
    return tuple(plans)
