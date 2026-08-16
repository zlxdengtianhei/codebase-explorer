from __future__ import annotations

from src.synthesis.variant_a.gates import GateContext, build_name_index, check_claim, check_page_hash, compute_page_hash
from src.synthesis.variant_a.models import SynthesisClaim, SynthesisClaimKind
from src.synthesis.variant_a.submit import submit_claims
from src.synthesis.variant_a.tests.conftest import make_ledger, make_surface, make_symbol
from src.synthesis.variant_a.models import SynthesisPageKind


def _ctx(tmp_path):
    a = make_symbol("a.py", "alpha")
    b = make_symbol("a.py", "beta")
    ledger = make_ledger(tmp_path, [a, b])
    surface = make_surface(ledger, [("__init__.py", "alpha", (a.symbol_id,))])
    return GateContext(
        ledger=ledger,
        surface=surface,
        ir_edges=frozenset({(a.symbol_id, b.symbol_id)}),
        name_index=build_name_index(ledger, surface),
    ), a, b


def test_s3_rejects_empty_citation(tmp_path) -> None:
    ctx, a, _ = _ctx(tmp_path)
    claim = SynthesisClaim(
        claim_id="empty",
        text="something vague",
        cited_symbol_ids=(),
        cited_surface_ids=(),
        claim_kind=SynthesisClaimKind.OVERVIEW,
    )
    fails = check_claim(claim, ctx)
    assert any(item.gate == "S3" for item in fails)


def test_s4_rejects_uncited_closed_name(tmp_path) -> None:
    ctx, a, b = _ctx(tmp_path)
    claim = SynthesisClaim(
        claim_id="s4",
        text="alpha talks about beta",
        cited_symbol_ids=(a.symbol_id,),
        claim_kind=SynthesisClaimKind.ROLE,
    )
    fails = check_claim(claim, ctx)
    assert any(item.gate == "S4" for item in fails)
    ok = SynthesisClaim(
        claim_id="s4ok",
        text="alpha talks about beta",
        cited_symbol_ids=(a.symbol_id, b.symbol_id),
        claim_kind=SynthesisClaimKind.ROLE,
    )
    assert check_claim(ok, ctx) == []


def test_s1_rejects_unknown_symbol(tmp_path) -> None:
    ctx, a, _ = _ctx(tmp_path)
    claim = SynthesisClaim(
        claim_id="s1",
        text="ghost",
        cited_symbol_ids=("missing.py::ghost",),
        claim_kind=SynthesisClaimKind.OVERVIEW,
    )
    fails = check_claim(claim, ctx)
    assert any(item.gate == "S1" for item in fails)


def test_s5_rejects_missing_and_fake_edge(tmp_path) -> None:
    ctx, a, b = _ctx(tmp_path)
    missing = SynthesisClaim(
        claim_id="s5a",
        text="alpha calls beta",
        cited_symbol_ids=(a.symbol_id, b.symbol_id),
        claim_kind=SynthesisClaimKind.FLOW_STEP,
    )
    assert any(item.gate == "S5" for item in check_claim(missing, ctx))
    fake = SynthesisClaim(
        claim_id="s5b",
        text="beta calls alpha",
        cited_symbol_ids=(a.symbol_id, b.symbol_id),
        claim_kind=SynthesisClaimKind.FLOW_STEP,
        graph_edge=(b.symbol_id, a.symbol_id),
    )
    assert any(item.gate == "S5" for item in check_claim(fake, ctx))
    good = SynthesisClaim(
        claim_id="s5c",
        text="alpha calls beta",
        cited_symbol_ids=(a.symbol_id, b.symbol_id),
        claim_kind=SynthesisClaimKind.FLOW_STEP,
        graph_edge=(a.symbol_id, b.symbol_id),
    )
    assert check_claim(good, ctx) == []


def test_s6_hash_mismatch(tmp_path) -> None:
    ctx, a, _ = _ctx(tmp_path)
    page, rejected = submit_claims(
        page_id="p",
        page_kind=SynthesisPageKind.LIBRARY,
        producer="t",
        drafts=[
            SynthesisClaim(
                claim_id="c",
                text="alpha is the entry.",
                cited_symbol_ids=(a.symbol_id,),
                claim_kind=SynthesisClaimKind.OVERVIEW,
            )
        ],
        ctx=ctx,
    )
    assert rejected == []
    assert page is not None
    assert check_page_hash(page, ctx) == []
    tampered = page.model_copy(update={"explained_content_hash": "sha256:" + "0" * 64})
    assert check_page_hash(tampered, ctx)
    expected = compute_page_hash(
        source_revision=ctx.ledger.source_revision,
        surface=ctx.surface,
        cited_symbol_ids=page.cited_symbol_ids,
        cited_surface_ids=page.cited_surface_ids,
        ledger=ctx.ledger,
    )
    assert page.explained_content_hash == expected
