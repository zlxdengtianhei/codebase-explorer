"""Tests for deterministic candidates and explicit status residuals."""
from __future__ import annotations

import networkx as nx

from src.graph.feature_cone import PublicSurfaceEntry
from src.graph.file_cards import L1SymbolFact
from src.semantic.l2_status import (
    assemble_status,
    build_status_prompt,
    build_symbol_cards,
    compute_hops_from_surface,
    deterministic_status,
    parse_status_response,
)


def test_status_candidates_keep_entry_and_public_api_deterministic():
    graph = nx.DiGraph((("api.py", "internal.py"),))
    surface = (
        PublicSurfaceEntry(
            name="public",
            origin="reexport",
            declared_in="__init__.py",
            defining_path="api.py",
            defining_name="public",
        ),
    )
    facts = (
        L1SymbolFact("s-public", "api.py", "pkg.public", "function", "publishes a result"),
        L1SymbolFact("s-helper", "internal.py", "pkg.helper", "function", "adapts a value"),
        L1SymbolFact("internal.py::ParseError", "internal.py", "pkg.ParseError", "class", "an error"),
    )
    hops = compute_hops_from_surface(graph, ("api.py",))
    cards = build_symbol_cards(facts, graph, surface, hops=hops)
    by_id = {card.symbol_id: card for card in cards}
    assert deterministic_status(by_id["s-public"], entry_paths=frozenset({"api.py"})).status == "entry"
    assert deterministic_status(by_id["internal.py::ParseError"], entry_paths=frozenset({"api.py"})).status == "error_path"
    assert deterministic_status(by_id["s-helper"], entry_paths=frozenset({"api.py"})) is None
    prompt = build_status_prompt((by_id["s-helper"],), repo_name="fixture")
    assert "adapts a value" in prompt
    assert "cluster" not in prompt.lower()
    assert "behavior" not in prompt


def test_status_parser_rejects_labels_owned_by_deterministic_layer():
    parsed = parse_status_response(
        '{"labels": [{"symbol_id": "s1", "status": "entry", "confidence": "high"}, '
        '{"symbol_id": "s2", "status": "adapter", "confidence": "medium"}, '
        '{"symbol_id": "s3", "status": "unknown", "confidence": "high"}]}'
    )
    assert parsed == {"s2": ("adapter", "medium")}


def test_assemble_status_keeps_zero_symbol_file_and_explains_unclassified():
    graph = nx.DiGraph((("api.py", "empty.py"),))
    surface = (
        PublicSurfaceEntry(
            name="public",
            origin="reexport",
            declared_in="__init__.py",
            defining_path="api.py",
            defining_name="public",
        ),
    )
    cards = build_symbol_cards(
        (L1SymbolFact("s1", "api.py", "pkg.public", "function", "publishes"),
         L1SymbolFact("s2", "api.py", "pkg.helper", "function", "helps")),
        graph,
        surface,
        hops={"api.py": 0, "empty.py": 1},
    )
    deterministic = {
        card.symbol_id: deterministic_status(card, entry_paths=frozenset({"api.py"}))
        for card in cards
        if deterministic_status(card, entry_paths=frozenset({"api.py"})) is not None
    }
    result = assemble_status(
        cards,
        deterministic,
        {},
        {"api.py": "feature-api", "empty.py": "feature-api"},
    )
    assert len(result.unclassified) == 1
    assert result.unclassified[0].reason
    empty = next(record for record in result.files if record.path == "empty.py")
    assert empty.module_id == "feature-api"
    assert empty.symbol_count == 0
    assert empty.reason is None
