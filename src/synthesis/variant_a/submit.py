"""Accept or reject claims. Gates reject; discarded claims are counted."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime

from src.synthesis.variant_a.gates import GateContext, check_claim, compute_page_hash
from src.synthesis.variant_a.models import (
    RejectedClaim,
    SynthesisClaim,
    SynthesisLedger,
    SynthesisPage,
    SynthesisPageKind,
    SynthesisResidual,
)


def now_utc() -> datetime:
    return datetime.now(UTC)


def auto_cite(claim: SynthesisClaim, ctx: GateContext) -> SynthesisClaim:
    cited_sym = list(claim.cited_symbol_ids)
    cited_surf = list(claim.cited_surface_ids)
    cited = set(cited_sym) | set(cited_surf)
    if claim.graph_edge is not None:
        for endpoint in claim.graph_edge:
            if endpoint in ctx.ledger.symbols and endpoint not in cited:
                cited_sym.append(endpoint)
                cited.add(endpoint)
            if endpoint in ctx.surface.by_id and endpoint not in cited:
                cited_surf.append(endpoint)
                cited.add(endpoint)
    for ident in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", claim.text):
        allowed = ctx.name_index.get(ident)
        if not allowed or (allowed & cited):
            continue
        surf = [item for item in allowed if item in ctx.surface.by_id]
        syms = [
            item
            for item in allowed
            if item in ctx.ledger.symbols and ctx.ledger.symbols[item].is_fresh
        ]
        pick = surf[:1] or syms[:1]
        for item in pick:
            if item in ctx.surface.by_id:
                cited_surf.append(item)
            else:
                cited_sym.append(item)
            cited.add(item)
    return claim.model_copy(
        update={
            "cited_symbol_ids": tuple(dict.fromkeys(cited_sym)),
            "cited_surface_ids": tuple(dict.fromkeys(cited_surf)),
        }
    )


def submit_claims(
    *,
    page_id: str,
    page_kind: SynthesisPageKind,
    producer: str,
    drafts: Iterable[SynthesisClaim],
    ctx: GateContext,
) -> tuple[SynthesisPage | None, list[RejectedClaim]]:
    accepted: list[SynthesisClaim] = []
    rejected: list[RejectedClaim] = []
    for draft in drafts:
        claim = auto_cite(draft, ctx)
        fails = check_claim(claim, ctx)
        if fails:
            for item in fails:
                rejected.append(
                    item.model_copy(update={"page_id": page_id}) if not item.page_id else item
                )
            continue
        accepted.append(claim)
    if not accepted:
        return None, rejected
    cited_sym = tuple(dict.fromkeys(sid for claim in accepted for sid in claim.cited_symbol_ids))
    cited_surf = tuple(dict.fromkeys(sid for claim in accepted for sid in claim.cited_surface_ids))
    digest = compute_page_hash(
        source_revision=ctx.ledger.source_revision,
        surface=ctx.surface,
        cited_symbol_ids=cited_sym,
        cited_surface_ids=cited_surf,
        ledger=ctx.ledger,
    )
    page = SynthesisPage(
        page_id=page_id,
        page_kind=page_kind,
        producer=producer,
        created_at=now_utc(),
        cited_symbol_ids=cited_sym,
        cited_surface_ids=cited_surf,
        explained_content_hash=digest,
        claims=tuple(accepted),
    )
    return page, rejected


def assemble_ledger(
    *,
    repo_root: str,
    source_revision: str,
    pages: list[SynthesisPage],
    rejected: list[RejectedClaim],
    residuals: list[SynthesisResidual],
) -> SynthesisLedger:
    return SynthesisLedger(
        schema="cbe-synthesis-ledger-1",
        repo_root=repo_root,
        source_revision=source_revision,
        pages={page.page_id: page for page in pages},
        residuals=tuple(residuals),
        rejected_claims=tuple(rejected),
        omitted_page_ids=tuple(item.residual_id for item in residuals),
    )
