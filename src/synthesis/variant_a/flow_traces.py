"""Named traces over probe call edges. Deterministic; no LLM."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from src.semantic.inventory import SemanticInventory
from src.semantic.models import SemanticLedger
from src.semantic.scheduler import _probe_compatible_call_edges
from src.synthesis.variant_a.surface import PublicSurface


SEED_TAILS = (
    "__call__",
    "wsgi_app",
    "full_dispatch_request",
    "preprocess_request",
    "dispatch_request",
    "finalize_request",
    "process_response",
    "handle_exception",
    "request",
    "send",
    "stream",
    "get",
    "post",
    "Client",
    "AsyncClient",
    "build_request",
    "send_request",
)


@dataclass(frozen=True)
class FlowTrace:
    trace_id: str
    entry_symbol_id: str
    ordered_symbol_ids: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]


def ledger_call_edges(ledger: SemanticLedger) -> set[tuple[str, str]]:
    """Same-file probe call edges. Citation-only pairs are not IR."""

    inventory = SemanticInventory(
        repo_root=ledger.repo_root,
        source_revision=ledger.source_revision,
        files=ledger.files,
        symbols=ledger.symbols,
    )
    return _probe_compatible_call_edges(inventory)


def _ids_by_tail(ledger: SemanticLedger) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for symbol_id, record in ledger.symbols.items():
        tail = record.qualified_name.rsplit(".", 1)[-1]
        grouped.setdefault(tail, []).append(symbol_id)
    return grouped


def _walk(
    start: str,
    edges: Mapping[str, tuple[str, ...]],
    *,
    limit: int = 12,
) -> tuple[str, ...]:
    path = [start]
    seen = {start}
    current = start
    while len(path) < limit:
        nxt = [dst for dst in edges.get(current, ()) if dst not in seen]
        if not nxt:
            break
        nxt.sort(
            key=lambda sid: (
                0 if sid.rsplit("::", 1)[-1].rsplit(".", 1)[-1] in SEED_TAILS else 1,
                sid,
            )
        )
        current = nxt[0]
        path.append(current)
        seen.add(current)
    return tuple(path)


def build_traces(
    ledger: SemanticLedger,
    surface: PublicSurface,
    *,
    ir_edges: Iterable[tuple[str, str]] | None = None,
) -> tuple[FlowTrace, ...]:
    edges = set(ir_edges) if ir_edges is not None else ledger_call_edges(ledger)
    outbound: dict[str, list[str]] = {}
    for src, dst in sorted(edges):
        outbound.setdefault(src, []).append(dst)
    frozen = {key: tuple(value) for key, value in outbound.items()}
    by_tail = _ids_by_tail(ledger)

    starts: list[str] = []
    for tail in SEED_TAILS:
        for symbol_id in by_tail.get(tail, ()):
            if symbol_id not in starts:
                starts.append(symbol_id)
    for binding in surface.bindings:
        starts.extend(sid for sid in binding.resolved_symbol_ids if sid not in starts)

    traces: list[FlowTrace] = []
    seen_paths: set[tuple[str, ...]] = set()
    for start in starts:
        ordered = _walk(start, frozen)
        if len(ordered) < 2:
            continue
        path_edges = tuple(
            (ordered[i], ordered[i + 1])
            for i in range(len(ordered) - 1)
            if (ordered[i], ordered[i + 1]) in edges
        )
        if len(path_edges) < 1:
            continue
        if ordered in seen_paths:
            continue
        seen_paths.add(ordered)
        traces.append(
            FlowTrace(
                trace_id=f"trace:{ordered[0]}",
                entry_symbol_id=ordered[0],
                ordered_symbol_ids=ordered,
                edges=path_edges,
            )
        )
    traces.sort(key=lambda item: (-len(item.ordered_symbol_ids), item.trace_id))
    return tuple(traces)


def longest_edge_chain(
    ir_edges: set[tuple[str, str]],
    ledger: SemanticLedger,
    *,
    limit: int = 8,
) -> tuple[str, ...]:
    """Fallback when named traces are short: longest simple path on probe edges."""

    if not ir_edges:
        return ()
    outbound: dict[str, list[str]] = {}
    inbound: set[str] = set()
    for src, dst in ir_edges:
        outbound.setdefault(src, []).append(dst)
        inbound.add(dst)
    starts = [node for node in outbound if node not in inbound] or list(outbound)
    best: tuple[str, ...] = ()

    def walk(node: str, path: tuple[str, ...], seen: set[str]) -> None:
        nonlocal best
        if len(path) > len(best):
            best = path
        if len(path) >= limit:
            return
        for dst in outbound.get(node, ()):
            if dst in seen:
                continue
            walk(dst, (*path, dst), seen | {dst})

    for start in starts:
        if start in ledger.symbols:
            walk(start, (start,), {start})
    return best
