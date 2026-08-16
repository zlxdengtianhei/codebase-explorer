"""Threshold depth: only qualifying symbols get a block; the rest is a table row.

Coverage stays a ledger property. Compact rows must stay visible (name +
anchor + line range) and keep ``<!-- symbol:ID -->`` so hops do not jump.
"""

from __future__ import annotations

from src.synthesis.variant_a.depth import (
    BLOCK_STATUSES,
    ContentDepth,
    LEDGER_POINTER_PREFIX,
    body_mode,
    compute_threshold_signals,
    parse_depth,
    qualifies_for_block,
)
from src.synthesis.variant_a.fold_audit import audit_fold, run_fold_negative_control
from src.synthesis.variant_a.models import SynthesisLedger
from src.synthesis.variant_a.page_tree import plan_page_tree
from src.synthesis.variant_a.render import render_documents
from src.synthesis.variant_a.pointing import evaluate_docs
from src.synthesis.variant_a.symbol_hops import measure_symbol_hops
from src.synthesis.variant_a.tests.test_depth import _mini


def test_parse_threshold() -> None:
    assert parse_depth("threshold") is ContentDepth.THRESHOLD
    assert BLOCK_STATUSES == frozenset({"entry", "public_api", "core"})


def test_qualifies_or_of_four_signals() -> None:
    assert qualifies_for_block("a", None, exported={"a"}, in_degree={}, hops={})
    assert qualifies_for_block("b", None, exported=set(), in_degree={"b": 2}, hops={})
    assert not qualifies_for_block("b", None, exported=set(), in_degree={"b": 1}, hops={})
    assert qualifies_for_block("c", None, exported=set(), in_degree={}, hops={"c": 0})
    assert qualifies_for_block("c", None, exported=set(), in_degree={}, hops={"c": 1})
    assert not qualifies_for_block("c", None, exported=set(), in_degree={}, hops={"c": 2})
    assert not qualifies_for_block("c", None, exported=set(), in_degree={}, hops={})
    assert qualifies_for_block("d", "entry", exported=set(), in_degree={}, hops={})
    assert qualifies_for_block("d", "public_api", exported=set(), in_degree={}, hops={})
    assert qualifies_for_block("d", "core", exported=set(), in_degree={}, hops={})
    assert not qualifies_for_block("d", "glue", exported=set(), in_degree={}, hops={})
    assert not qualifies_for_block("d", "adapter", exported=set(), in_degree={}, hops={})


def test_body_mode_threshold() -> None:
    signals = compute_threshold_signals(
        exported={"app.py::Flask"},
        ir_edges=frozenset({("app.py::Flask", "app.py::dispatch")}),
        symbol_ids=["app.py::Flask", "app.py::dispatch", "app.py::teardown"],
    )
    assert body_mode("entry", ContentDepth.THRESHOLD, symbol_id="app.py::Flask", signals=signals) == "full"
    assert body_mode("glue", ContentDepth.THRESHOLD, symbol_id="app.py::teardown", signals=signals) == "compact"
    # hops=1 from exported Flask → dispatch still a block even if status is glue
    assert body_mode("glue", ContentDepth.THRESHOLD, symbol_id="app.py::dispatch", signals=signals) == "full"


def test_compute_signals_in_degree_and_hops() -> None:
    signals = compute_threshold_signals(
        exported={"A"},
        ir_edges=frozenset({("A", "B"), ("C", "B"), ("B", "D")}),
        symbol_ids=["A", "B", "C", "D", "E"],
    )
    assert signals.exported == frozenset({"A"})
    assert signals.in_degree["B"] == 2
    assert signals.hops_from_surface["A"] == 0
    assert signals.hops_from_surface["B"] == 1
    assert signals.hops_from_surface["D"] == 2
    assert "E" not in signals.hops_from_surface
    assert "C" not in signals.hops_from_surface


def test_threshold_render_blocks_vs_compact_table(tmp_path) -> None:
    ledger, surface, clusters, pages, ctx, status, entry, core, glue, adapter = _mini(tmp_path)
    docs = render_documents(
        repo_name="demo",
        ledger=ledger,
        surface=surface,
        synthesis=SynthesisLedger(
            schema="cbe-synthesis-ledger-1",
            repo_root=ledger.repo_root,
            source_revision=ledger.source_revision,
        ),
        pages=pages,
        clusters=clusters,
        ctx=ctx,
        depth=ContentDepth.THRESHOLD,
        status_by_symbol=status,
    )
    joined = "\n".join(docs.values())
    for sid in ledger.symbols:
        assert f"<!-- symbol:{sid} -->" in joined
    # entry is exported + status; core is status — both get heading blocks
    assert f"### `{entry.qualified_name}`" in joined
    assert f"### `{core.qualified_name}`" in joined
    # glue / adapter: compact table only, no heading, no explanation
    assert f"### `{glue.qualified_name}`" not in joined
    assert f"### `{adapter.qualified_name}`" not in joined
    glue_block = joined.split(f"<!-- symbol:{glue.symbol_id} -->", 1)[1].split(
        f"<!-- end:symbol:{glue.symbol_id} -->", 1
    )[0]
    assert "监听器" not in glue_block
    assert LEDGER_POINTER_PREFIX not in glue_block
    assert f"{glue.path}:{glue.span[0]}-{glue.span[1]}" in glue_block
    assert glue.qualified_name in glue_block or glue.qualified_name.rsplit(".", 1)[-1] in glue_block
    assert "<!-- compact:" in glue_block or "<!-- compact:" in joined
    # hops: every ledger symbol still on a reachable page
    hops = measure_symbol_hops(docs, list(ledger.symbols))
    assert hops["n_rendered"] == 4
    assert hops["unreachable"] == []
    assert hops["rate_le_3"] == 1.0
    pointing = evaluate_docs(docs)
    assert pointing["rate_hit"] == 1.0
    assert pointing["misses"] == 0
    audit = audit_fold(docs, list(ledger.symbols), status, ContentDepth.THRESHOLD, ir_edges=ctx.ir_edges, surface=surface)
    assert audit["n_ledger"] == 4
    assert audit["n_rendered"] == 4
    assert audit["missing_markers"] == []
    assert audit["silent_folds"] == []
    assert audit["n_compact"] == 2
    assert audit["n_block"] == 2
    assert audit["ok"]


def test_threshold_negative_control_flags_missing_row(tmp_path) -> None:
    ledger, surface, clusters, pages, ctx, status, *_ = _mini(tmp_path)
    docs = render_documents(
        repo_name="demo",
        ledger=ledger,
        surface=surface,
        synthesis=SynthesisLedger(
            schema="cbe-synthesis-ledger-1",
            repo_root=ledger.repo_root,
            source_revision=ledger.source_revision,
        ),
        pages=pages,
        clusters=clusters,
        ctx=ctx,
        depth=ContentDepth.THRESHOLD,
        status_by_symbol=status,
    )
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    for rel, text in docs.items():
        dest = docs_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
    control = run_fold_negative_control(
        docs_root,
        tmp_path / "neg",
        list(ledger.symbols),
        status,
        ContentDepth.THRESHOLD,
        ir_edges=ctx.ir_edges,
        surface=surface,
    )
    assert control["ran"] is True
    assert control["ok_flagged_red"] is True
