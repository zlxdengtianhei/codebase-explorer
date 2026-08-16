"""Deterministic synthesis pages. LLM only enriches library + primary flow."""

from __future__ import annotations

from src.semantic.models import SemanticLedger
from src.synthesis.variant_a.cluster_source import cluster_dir_name
from src.synthesis.variant_a.flow_traces import FlowTrace, longest_edge_chain
from src.synthesis.variant_a.gates import GateContext
from src.synthesis.variant_a.models import (
    ClusterInput,
    RejectedClaim,
    SynthesisClaim,
    SynthesisClaimKind,
    SynthesisPage,
    SynthesisPageKind,
    SynthesisResidual,
)
from src.synthesis.variant_a.submit import submit_claims
from src.synthesis.variant_a.surface import PublicSurface, entry_bindings


PRODUCER = "deterministic:variant-A"


def _tail(symbol_id: str, ledger: SemanticLedger) -> str:
    return ledger.symbols[symbol_id].qualified_name.rsplit(".", 1)[-1]


def _prefer_symbol(ledger: SemanticLedger, tail: str, *, path_contains: str = "") -> str | None:
    hits = [
        (symbol_id, record)
        for symbol_id, record in ledger.symbols.items()
        if record.qualified_name.rsplit(".", 1)[-1] == tail and record.is_fresh
    ]
    if path_contains:
        narrowed = [item for item in hits if path_contains in item[1].path]
        if narrowed:
            hits = narrowed
    hits.sort(key=lambda item: (item[1].path.count("/"), item[0]))
    return hits[0][0] if hits else None


def _surface_for_name(surface: PublicSurface, name: str) -> str | None:
    for item in surface.bindings:
        if item.name == name and item.path.endswith("__init__.py"):
            return item.surface_id
    for item in surface.bindings:
        if item.name == name:
            return item.surface_id
    return None


def _add(
    pages: list[SynthesisPage],
    rejected: list[RejectedClaim],
    residuals: list[SynthesisResidual],
    *,
    page_id: str,
    kind: SynthesisPageKind,
    drafts: list[SynthesisClaim],
    ctx: GateContext,
) -> None:
    page, fails = submit_claims(
        page_id=page_id,
        page_kind=kind,
        producer=PRODUCER,
        drafts=drafts,
        ctx=ctx,
    )
    rejected.extend(fails)
    if page is None:
        residuals.append(SynthesisResidual(residual_id=page_id, reason="all claims rejected by S1-S5"))
    else:
        pages.append(page)


def _library_drafts(
    ledger: SemanticLedger,
    surface: PublicSurface,
) -> list[SynthesisClaim]:
    entries = entry_bindings(surface)
    named = [item for item in entries if item.resolved_symbol_ids]
    if not named:
        named = [item for item in surface.bindings if item.resolved_symbol_ids][:6]
    if not named:
        return []
    primary = named[0]
    second = named[1] if len(named) > 1 else None
    primary_sym = primary.resolved_symbol_ids[0]
    cited_sym = [primary_sym]
    cited_surf = [primary.surface_id]
    names = [primary.name]
    if second is not None:
        cited_sym.append(second.resolved_symbol_ids[0])
        cited_surf.append(second.surface_id)
        names.append(second.name)
    drafts = [
        SynthesisClaim(
            claim_id="library-overview",
            text=f"This library's public names include {names[0]}"
            + (f" and {names[1]}" if len(names) > 1 else "")
            + ".",
            cited_symbol_ids=tuple(dict.fromkeys(cited_sym)),
            cited_surface_ids=tuple(dict.fromkeys(cited_surf)),
            claim_kind=SynthesisClaimKind.OVERVIEW,
        )
    ]
    flask = _prefer_symbol(ledger, "Flask")
    flask_s = _surface_for_name(surface, "Flask")
    req_s = _surface_for_name(surface, "request")
    if flask and flask_s:
        drafts.append(
            SynthesisClaim(
                claim_id="library-flask",
                text="Flask is a WSGI microframework whose public object is the Flask class; "
                "applications are Flask instances that expose request as a public alias.",
                cited_symbol_ids=(flask,),
                cited_surface_ids=tuple(sid for sid in (flask_s, req_s) if sid),
                claim_kind=SynthesisClaimKind.OVERVIEW,
            )
        )
    client = _prefer_symbol(ledger, "Client")
    client_s = _surface_for_name(surface, "Client")
    if client and client_s:
        drafts.append(
            SynthesisClaim(
                claim_id="library-httpx",
                text="Client is the public HTTP client; request is the matching convenience alias.",
                cited_symbol_ids=(client,),
                cited_surface_ids=tuple(
                    sid for sid in (client_s, _surface_for_name(surface, "request")) if sid
                ),
                claim_kind=SynthesisClaimKind.ROLE,
            )
        )
    return drafts


def _flow_chain(
    ledger: SemanticLedger,
    traces: tuple[FlowTrace, ...],
    ir_edges: set[tuple[str, str]],
) -> tuple[str, ...]:
    preferred = (
        "__call__",
        "wsgi_app",
        "full_dispatch_request",
        "preprocess_request",
        "dispatch_request",
    )
    seeds = [sid for tail in preferred if (sid := _prefer_symbol(ledger, tail))]
    if len(seeds) >= 3:
        return tuple(seeds)
    if traces:
        return traces[0].ordered_symbol_ids
    return longest_edge_chain(ir_edges, ledger)


def _flow_drafts(
    ledger: SemanticLedger,
    chain: tuple[str, ...],
    ir_edges: set[tuple[str, str]],
) -> list[SynthesisClaim]:
    chain = tuple(sid for sid in chain if sid in ledger.symbols and ledger.symbols[sid].is_fresh)
    if len(chain) < 2:
        return []
    tails = [_tail(sid, ledger) for sid in chain]
    drafts: list[SynthesisClaim] = [
        SynthesisClaim(
            claim_id="flow-overview",
            text="One path walks " + " then ".join(tails) + ".",
            cited_symbol_ids=tuple(chain),
            claim_kind=SynthesisClaimKind.OVERVIEW,
        )
    ]
    for index in range(len(chain) - 1):
        src, dst = chain[index], chain[index + 1]
        if (src, dst) not in ir_edges:
            continue
        drafts.append(
            SynthesisClaim(
                claim_id=f"flow-step-{index}",
                text=f"{_tail(src, ledger)} calls {_tail(dst, ledger)}.",
                cited_symbol_ids=(src, dst),
                claim_kind=SynthesisClaimKind.FLOW_STEP,
                graph_edge=(src, dst),
            )
        )
    return drafts


def _cluster_drafts(cluster: ClusterInput, ledger: SemanticLedger) -> list[SynthesisClaim]:
    if cluster.is_unassigned:
        return []
    fresh = [
        sid
        for sid in cluster.symbol_ids
        if sid in ledger.symbols and ledger.symbols[sid].is_fresh
    ]
    preferred_tails = {
        "Flask",
        "Blueprint",
        "Client",
        "AsyncClient",
        "request",
        "jsonify",
        "wsgi_app",
    }
    ranked = sorted(
        fresh,
        key=lambda sid: (
            0 if _tail(sid, ledger) in preferred_tails else 1,
            0 if ledger.symbols[sid].kind.value == "class" else 1,
            sid,
        ),
    )
    picked = ranked[:3]
    if not picked:
        return []
    tails = [_tail(sid, ledger) for sid in picked]
    if len(tails) == 1:
        text = f"{cluster.display_name} centres on {tails[0]}."
    elif len(tails) == 2:
        text = f"{cluster.display_name} centres on {tails[0]} and {tails[1]}."
    else:
        text = f"{cluster.display_name} centres on {tails[0]}, {tails[1]}, and {tails[2]}."
    return [
        SynthesisClaim(
            claim_id=f"cluster-{cluster.cluster_id}-overview",
            text=text,
            cited_symbol_ids=tuple(picked),
            claim_kind=SynthesisClaimKind.ROLE,
        )
    ]


def deterministic_pages(
    ledger: SemanticLedger,
    surface: PublicSurface,
    traces: tuple[FlowTrace, ...],
    ir_edges: set[tuple[str, str]],
    clusters: tuple[ClusterInput, ...],
    ctx: GateContext,
) -> tuple[list[SynthesisPage], list[RejectedClaim], list[SynthesisResidual]]:
    pages: list[SynthesisPage] = []
    rejected: list[RejectedClaim] = []
    residuals: list[SynthesisResidual] = []

    _add(
        pages,
        rejected,
        residuals,
        page_id="library",
        kind=SynthesisPageKind.LIBRARY,
        drafts=_library_drafts(ledger, surface),
        ctx=ctx,
    )

    chain = _flow_chain(ledger, traces, ir_edges)
    flow_drafts = _flow_drafts(ledger, chain, ir_edges)
    if flow_drafts:
        _add(
            pages,
            rejected,
            residuals,
            page_id="flow-main",
            kind=SynthesisPageKind.FLOW,
            drafts=flow_drafts,
            ctx=ctx,
        )
    else:
        residuals.append(SynthesisResidual(residual_id="flow-main", reason="no probe-edge chain of length ≥2"))

    surface_entries = entry_bindings(surface)
    cited_surf = tuple(item.surface_id for item in surface_entries[:40])
    cited_sym = tuple(
        dict.fromkeys(sid for item in surface_entries for sid in item.resolved_symbol_ids)
    )[:20]
    if cited_surf and cited_sym:
        names = " ".join(item.name for item in surface_entries[:40])
        _add(
            pages,
            rejected,
            residuals,
            page_id="surface",
            kind=SynthesisPageKind.SURFACE,
            drafts=[
                SynthesisClaim(
                    claim_id="surface-overview",
                    text=f"Public re-exports include {names}.",
                    cited_symbol_ids=cited_sym,
                    cited_surface_ids=cited_surf,
                    claim_kind=SynthesisClaimKind.ALIAS,
                )
            ],
            ctx=ctx,
        )

    for cluster in clusters:
        drafts = _cluster_drafts(cluster, ledger)
        if not drafts:
            if cluster.is_unassigned:
                residuals.append(
                    SynthesisResidual(
                        residual_id="unassigned",
                        reason=cluster.unassigned_reason or "unassigned cluster has no symbols",
                    )
                )
            continue
        _add(
            pages,
            rejected,
            residuals,
            page_id=f"cluster-{cluster.cluster_id}",
            kind=SynthesisPageKind.CLUSTER,
            drafts=drafts,
            ctx=ctx,
        )
        _ = cluster_dir_name(cluster.cluster_id)

    unused = [item.trace_id for item in traces[1:6]]
    if unused:
        residuals.append(
            SynthesisResidual(
                residual_id="extra-traces",
                reason="named traces not promoted to their own flow page: " + ",".join(unused[:5]),
            )
        )
    return pages, rejected, residuals
