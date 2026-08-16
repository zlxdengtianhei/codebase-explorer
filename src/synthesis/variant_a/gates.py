"""Submit-time gates S1–S7. Rejection is the write path, not a report."""

from __future__ import annotations

import hashlib
import keyword
import re
from collections.abc import Mapping
from dataclasses import dataclass

from src.semantic.models import SemanticLedger
from src.synthesis.variant_a.models import RejectedClaim, SynthesisClaim, SynthesisClaimKind, SynthesisPage
from src.synthesis.variant_a.surface import PublicSurface


_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_SKIP_IDENTS = frozenset(keyword.kwlist) | {"self", "cls", "True", "False", "None"}


class SynthesisGateError(ValueError):
    def __init__(self, gate: str, reason: str, *, claim_id: str = "") -> None:
        self.gate = gate
        self.reason = reason
        self.claim_id = claim_id
        super().__init__(f"{gate}: {reason}")


@dataclass(frozen=True)
class GateContext:
    ledger: SemanticLedger
    surface: PublicSurface
    ir_edges: frozenset[tuple[str, str]]
    name_index: Mapping[str, frozenset[str]]


def build_name_index(ledger: SemanticLedger, surface: PublicSurface) -> dict[str, frozenset[str]]:
    index: dict[str, set[str]] = {}
    for symbol_id, record in ledger.symbols.items():
        tail = record.qualified_name.rsplit(".", 1)[-1]
        index.setdefault(tail, set()).add(symbol_id)
        index.setdefault(record.qualified_name, set()).add(symbol_id)
    for binding in surface.bindings:
        index.setdefault(binding.name, set()).add(binding.surface_id)
        index.setdefault(binding.surface_id, set()).add(binding.surface_id)
    return {key: frozenset(value) for key, value in index.items()}


def overlay_file_hash_blob(surface: PublicSurface) -> str:
    return "\n".join(
        f"{path}\0{digest}"
        for path, digest in sorted(surface.overlay_file_hashes.items())
    )


def cited_pairs_for_hash(
    ledger: SemanticLedger,
    surface: PublicSurface,
    symbol_ids: tuple[str, ...],
    surface_ids: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for symbol_id in sorted(set(symbol_ids)):
        record = ledger.symbols[symbol_id]
        pairs.append((symbol_id, record.content_hash))
    by_id = surface.by_id
    for sid in sorted(set(surface_ids)):
        binding = by_id[sid]
        file_hash = surface.overlay_file_hashes.get(binding.path, "sha256:" + ("0" * 64))
        pairs.append((sid, file_hash))
    return tuple(sorted(pairs))


def compute_page_hash(
    *,
    source_revision: str,
    surface: PublicSurface,
    cited_symbol_ids: tuple[str, ...],
    cited_surface_ids: tuple[str, ...],
    ledger: SemanticLedger,
) -> str:
    pairs = cited_pairs_for_hash(ledger, surface, cited_symbol_ids, cited_surface_ids)
    framed = (
        source_revision.encode("utf-8")
        + b"\n"
        + overlay_file_hash_blob(surface).encode("utf-8")
        + b"\n"
        + b"\n".join(f"{item_id}\0{digest}".encode("utf-8") for item_id, digest in pairs)
    )
    return "sha256:" + hashlib.sha256(framed).hexdigest()


def check_claim(claim: SynthesisClaim, ctx: GateContext) -> list[RejectedClaim]:
    rejected: list[RejectedClaim] = []
    page_id = ""
    known_symbols = ctx.ledger.symbols
    overlay = ctx.surface.by_id
    alias_edges = ctx.surface.alias_edges

    for sid in claim.cited_symbol_ids:
        if sid not in known_symbols:
            rejected.append(
                RejectedClaim(
                    claim_id=claim.claim_id,
                    page_id=page_id,
                    gate="S1",
                    reason=f"cited symbol id not in ledger.symbols: {sid}",
                    text_sample=claim.text[:200],
                )
            )
            continue
        if not known_symbols[sid].is_fresh:
            rejected.append(
                RejectedClaim(
                    claim_id=claim.claim_id,
                    page_id=page_id,
                    gate="S2",
                    reason=f"cited symbol is not fresh: {sid}",
                    text_sample=claim.text[:200],
                )
            )
    for sid in claim.cited_surface_ids:
        if sid not in overlay:
            rejected.append(
                RejectedClaim(
                    claim_id=claim.claim_id,
                    page_id=page_id,
                    gate="S1",
                    reason=f"cited surface id not in overlay: {sid}",
                    text_sample=claim.text[:200],
                )
            )

    if not claim.citation_set:
        rejected.append(
            RejectedClaim(
                claim_id=claim.claim_id,
                page_id=page_id,
                gate="S3",
                reason="claim has empty cited_symbol_ids and cited_surface_ids",
                text_sample=claim.text[:200],
            )
        )

    cited = claim.citation_set
    for ident in _IDENT.findall(claim.text):
        if ident in _SKIP_IDENTS:
            continue
        allowed = ctx.name_index.get(ident)
        if not allowed:
            continue
        if not (allowed & cited):
            rejected.append(
                RejectedClaim(
                    claim_id=claim.claim_id,
                    page_id=page_id,
                    gate="S4",
                    reason=f"name {ident!r} hits ledger/overlay but is not in this claim's citation set",
                    text_sample=claim.text[:200],
                )
            )

    if claim.claim_kind is SynthesisClaimKind.FLOW_STEP:
        if claim.graph_edge is None:
            rejected.append(
                RejectedClaim(
                    claim_id=claim.claim_id,
                    page_id=page_id,
                    gate="S5",
                    reason="flow_step claim is missing graph_edge",
                    text_sample=claim.text[:200],
                )
            )
        else:
            src, dst = claim.graph_edge
            in_ir = (src, dst) in ctx.ir_edges
            in_alias = (src, dst) in alias_edges
            if not in_ir and not in_alias:
                rejected.append(
                    RejectedClaim(
                        claim_id=claim.claim_id,
                        page_id=page_id,
                        gate="S5",
                        reason=f"graph_edge not in IR or overlay alias edges: {src!r} -> {dst!r}",
                        text_sample=claim.text[:200],
                    )
                )
            if src not in cited or dst not in cited:
                rejected.append(
                    RejectedClaim(
                        claim_id=claim.claim_id,
                        page_id=page_id,
                        gate="S5",
                        reason="graph_edge endpoints must both be in the claim citation set",
                        text_sample=claim.text[:200],
                    )
                )
    return rejected


def check_page_hash(page: SynthesisPage, ctx: GateContext) -> list[RejectedClaim]:
    expected = compute_page_hash(
        source_revision=ctx.ledger.source_revision,
        surface=ctx.surface,
        cited_symbol_ids=page.cited_symbol_ids,
        cited_surface_ids=page.cited_surface_ids,
        ledger=ctx.ledger,
    )
    if page.explained_content_hash != expected:
        return [
            RejectedClaim(
                claim_id="",
                page_id=page.page_id,
                gate="S6",
                reason=(
                    "explained_content_hash does not match ordered "
                    "(id, content_hash) digest + source_revision + overlay file hashes"
                ),
                text_sample=page.explained_content_hash,
            )
        ]
    return []


def page_is_projectable(page: SynthesisPage, ctx: GateContext) -> bool:
    if page.stale:
        return False
    if check_page_hash(page, ctx):
        return False
    for symbol_id in page.cited_symbol_ids:
        record = ctx.ledger.symbols.get(symbol_id)
        if record is None or not record.is_fresh:
            return False
    for sid in page.cited_surface_ids:
        if sid not in ctx.surface.by_id:
            return False
    return True


def synthesis_text_outside_blocks(markdown: str, texts: tuple[str, ...]) -> list[str]:
    """S7: claim bodies must not appear in INDEX outside synthesis markers."""

    stripped: list[str] = []
    skipping = False
    for line in markdown.splitlines():
        if re.search(r"<!--\s*synthesis:", line):
            skipping = True
            continue
        if skipping and re.search(r"<!--\s*end:synthesis:", line):
            skipping = False
            continue
        if not skipping:
            stripped.append(line)
    body = "\n".join(stripped)
    return [text for text in texts if text.strip() and text.strip() in body]
