"""Tests for the source-free FileCard boundary."""
from __future__ import annotations

import json

import networkx as nx

from src.graph.feature_cone import PublicSurfaceEntry
from src.graph.file_cards import (
    L1SymbolFact,
    build_file_cards,
    clustering_payload,
    derive_one_liner,
    load_l1_facts,
)


def test_file_cards_keep_zero_symbol_files_and_rank_exported_symbols():
    facts = (
        L1SymbolFact("api::helper", "api.py", "pkg.helper", "function", "helper text", mess_score=2.0),
        L1SymbolFact("api::public", "api.py", "pkg.public", "function", "public text", mess_score=4.0),
    )
    graph = nx.DiGraph(
        (
            ("api.py", "core.py"),
            ("consumer.py", "api.py"),
        )
    )
    surface = (
        PublicSurfaceEntry(
            name="public",
            origin="reexport",
            declared_in="__init__.py",
            defining_path="api.py",
            defining_name="public",
        ),
    )
    cards, diagnostics = build_file_cards(
        facts,
        graph,
        surface,
        ("__init__.py", "api.py", "core.py", "consumer.py"),
        symbol_in_degree={"api::helper": 1, "api::public": 3},
    )
    by_path = {card.path: card for card in cards}
    assert set(by_path) == {"__init__.py", "api.py", "core.py", "consumer.py"}
    assert by_path["core.py"].symbol_count == 0
    assert by_path["api.py"].top_symbols[0].symbol_id == "api::public"
    assert by_path["api.py"].mess_p50 == 3.0
    assert "zero_symbol_file:core.py" in diagnostics

    payload = clustering_payload(cards)
    assert all("behavior" not in item for item in payload)
    assert all(set(item) == {
        "path", "language", "exported_names", "symbol_count", "symbol_kinds",
        "top_symbols", "effects_histogram", "out_files", "in_files", "mess_p50",
    } for item in payload)


def test_l1_ledger_loader_preserves_missing_explanations(tmp_path):
    ledger = tmp_path / "ledger.json"
    ledger.write_text(
        json.dumps({
            "symbols": {
                "s1": {"path": "a.py", "qualified_name": "pkg.a", "kind": "function", "explanation": {"text": "Does a thing. More detail."}},
                "s2": {"path": "b.py", "qualified_name": "pkg.b", "kind": "class"},
            },
            "files": ["a.py", "b.py"],
        }),
        encoding="utf-8",
    )
    facts, diagnostics = load_l1_facts(ledger)
    assert [fact.symbol_id for fact in facts] == ["s1", "s2"]
    assert facts[0].one_liner == "Does a thing."
    assert facts[1].one_liner == ""
    assert diagnostics == ("missing_one_liner:s2",)


def test_one_liner_is_bounded_to_the_l2_input_budget():
    result = derive_one_liner("x" * 500)
    assert len(result) == 160
