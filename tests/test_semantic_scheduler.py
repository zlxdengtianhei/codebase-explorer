"""Qualified graph, SCC frontier, budget packet, and lease recovery tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import networkx as nx

from src.graph.ordering import dependency_first_scc_layers
from src.ir import (
    CallOutcome,
    CallResolution,
    EntityKind,
    EntityRef,
    EvidenceSpan,
    Provenance,
    ProvenanceBasis,
    ReceiverShape,
    Relation,
    RepositoryEntityIdentity,
    ResolutionMethod,
    ResolutionStatus,
    TargetEvidence,
    deterministic_entity_id,
)
from src.semantic.coverage import apply_runtime_coverage, load_runtime_coverage
from src.semantic.inventory import (
    SemanticInventory,
    enumerate_semantic_inventory,
    reconcile_semantic_ledger,
)
from src.semantic.models import SemanticExplanation
from src.semantic.scheduler import SemanticScheduler, build_semantic_graph
from src.semantic.store import SemanticLedgerStore


FIXTURE = Path(__file__).parent / "fixtures/semantic_disclosure"


def test_dependency_first_scc_helper_is_callee_first_and_exposes_cycles() -> None:
    graph = nx.DiGraph()
    graph.add_edges_from(
        (
            ("caller", "middle"),
            ("middle", "leaf"),
            ("cycle_a", "cycle_b"),
            ("cycle_b", "cycle_a"),
        )
    )

    plan = dependency_first_scc_layers(graph)
    layer_by_member = {
        member: index
        for index, layer in enumerate(plan.layers)
        for component in layer
        for member in component.members
    }

    assert layer_by_member["leaf"] < layer_by_member["middle"] < layer_by_member["caller"]
    cycle = next(component for component in plan.components if len(component.members) == 2)
    assert cycle.members == ("cycle_a", "cycle_b")
    assert cycle.is_cycle
    assert set(plan.component_by_node) == set(graph.nodes)


def test_inventory_graph_keeps_duplicate_names_qualified_and_tracks_probe_edges() -> None:
    repo = FIXTURE / "cycle_repo"
    inventory = enumerate_semantic_inventory(repo)
    graph = build_semantic_graph(inventory)

    assert "a.py::duplicate" in graph
    assert "b.py::duplicate" in graph
    assert ("a.py::hot_leaf", "a.py::duplicate") in graph.edges
    assert ("b.py::cold_only", "b.py::duplicate") in graph.edges
    assert ("a.py::Outer", "a.py::Outer.method") in graph.edges
    assert ("a.py::Outer.nested_parent", "a.py::Outer.nested_parent.inner") in graph.edges
    assert ("a.py::cycle_a", "a.py::cycle_b") in graph.edges
    assert ("a.py::cycle_b", "a.py::cycle_a") in graph.edges


def test_resolved_ir_relation_adds_a_qualified_cross_file_edge() -> None:
    repo = FIXTURE / "cycle_repo"
    base = enumerate_semantic_inventory(repo)
    revision = "rev_" + "3" * 64
    caller_ir = deterministic_entity_id(
        revision, "a.py", EntityKind.SYMBOL, "test:hot_caller"
    )
    callee_ir = deterministic_entity_id(
        revision, "b.py", EntityKind.SYMBOL, "test:duplicate"
    )
    symbols = dict(base.symbols)
    symbols["a.py::hot_caller"] = symbols["a.py::hot_caller"].model_copy(
        update={"ir_symbol_id": caller_ir}
    )
    symbols["b.py::duplicate"] = symbols["b.py::duplicate"].model_copy(
        update={"ir_symbol_id": callee_ir}
    )
    inventory = SemanticInventory(
        repo_root=base.repo_root,
        source_revision=base.source_revision,
        files=base.files,
        symbols=symbols,
        diagnostics=base.diagnostics,
    )
    caller = "a.py::hot_caller"
    call_span = EvidenceSpan(
        source_unit_id=deterministic_entity_id(
            revision, "a.py", EntityKind.SOURCE_UNIT, "a.py"
        ),
        path="a.py",
        start_line=13,
        start_column=0,
        end_line=13,
        end_column=20,
    )
    target_identity = RepositoryEntityIdentity(
        ref=EntityRef(kind=EntityKind.SYMBOL, id=callee_ir),
        source_revision_id=revision,
        path="b.py",
        definition_locator="test:duplicate",
    )
    target_evidence = TargetEvidence(
        target=target_identity,
        provenance=(
            Provenance(
                basis=ProvenanceBasis.DIRECT_LOCAL_BINDING,
                evidence=(
                    EvidenceSpan(
                        source_unit_id=deterministic_entity_id(
                            revision, "b.py", EntityKind.SOURCE_UNIT, "b.py"
                        ),
                        path="b.py",
                        start_line=1,
                        start_column=0,
                        end_line=1,
                        end_column=20,
                    ),
                ),
                source_revision_id=revision,
                source_entity=target_identity,
            ),
        ),
    )
    locator = (
        f"python:call:{call_span.start_line}:{call_span.start_column}:"
        f"{call_span.end_line}:{call_span.end_column}:{caller}"
    )
    relation = Relation(
        id=deterministic_entity_id(revision, "a.py", EntityKind.RELATION, locator),
        source_revision_id=revision,
        path="a.py",
        kind="call",
        locator=locator,
        source=EntityRef(kind=EntityKind.SYMBOL, id=caller_ir),
        target=None,
        evidence=(call_span,),
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_method=ResolutionMethod.EXACT,
        confidence=1.0,
        reason="typed runtime exact test relation",
        candidates=(),
        call_resolution=CallResolution(
            outcome=CallOutcome.RUNTIME_EXACT,
            receiver_shape=ReceiverShape.BARE_NAME,
            runtime_exact_target=target_evidence,
        ),
    )

    graph = build_semantic_graph(inventory, relations=(relation,))
    assert ("a.py::hot_caller", "b.py::duplicate") in graph.edges
    assert graph.edges["a.py::hot_caller", "b.py::duplicate"]["sources"] == (
        "ir_relation",
    )

    virtual_relation = Relation(
        id=relation.id,
        source_revision_id=revision,
        path="a.py",
        kind="call",
        locator=locator,
        source=EntityRef(kind=EntityKind.SYMBOL, id=caller_ir),
        target=None,
        evidence=(call_span,),
        resolution_status=ResolutionStatus.AMBIGUOUS,
        resolution_method=ResolutionMethod.DATAFLOW,
        confidence=0.5,
        reason="typed virtual dispatch test relation",
        candidates=(),
        call_resolution=CallResolution(
            outcome=CallOutcome.VIRTUAL_DISPATCH,
            receiver_shape=ReceiverShape.ANNOTATED_NAME,
            lexical_base_target=target_evidence,
        ),
    )
    virtual_graph = build_semantic_graph(inventory, relations=(virtual_relation,))
    assert ("a.py::hot_caller", "b.py::duplicate") not in virtual_graph.edges


def test_full_order_covers_every_symbol_and_is_callee_first_for_acyclic_probe_edges(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "app.py").write_text(
        "def leaf():\n"
        "    return 1\n\n"
        "def middle():\n"
        "    return leaf()\n\n"
        "class Outer:\n"
        "    def caller(self):\n"
        "        return middle()\n",
        encoding="utf-8",
    )
    inventory = enumerate_semantic_inventory(tmp_path)
    scheduler = SemanticScheduler.from_inventory(inventory)
    order = scheduler.full_order()
    positions = {symbol_id: index for index, symbol_id in enumerate(order)}

    assert set(order) == set(inventory.symbols)
    assert positions["app.py::leaf"] < positions["app.py::middle"]
    assert positions["app.py::middle"] < positions["app.py::Outer.caller"]
    assert positions["app.py::Outer.caller"] < positions["app.py::Outer"]
    assert scheduler.ready_frontier()


def test_runtime_heat_changes_only_same_layer_priority() -> None:
    repo = FIXTURE / "cycle_repo"
    inventory = enumerate_semantic_inventory(repo)
    plain = SemanticScheduler.from_inventory(inventory)
    runtime = load_runtime_coverage(FIXTURE / "coverage.json", repo_root=repo)
    heated_ledger = apply_runtime_coverage(plain.ledger, runtime)
    heated = SemanticScheduler.from_inventory(inventory, ledger=heated_ledger)

    assert set(plain.full_order()) == set(heated.full_order()) == set(inventory.symbols)
    assert plain.scc_plan == heated.scc_plan
    heated_ready = heated.ready_frontier()
    assert {item.scc_id for item in plain.ready_frontier()} == {
        item.scc_id for item in heated_ready
    }
    hot = next(item for item in heated_ready if "a.py::duplicate" in item.members)
    cold = next(item for item in heated_ready if "a.py::cold_path" in item.members)
    assert heated_ready.index(hot) < heated_ready.index(cold)


def test_claim_persists_packet_and_exclusive_lease_for_process_recovery(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "app.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    store = SemanticLedgerStore(tmp_path)
    store.create()
    now = datetime(2026, 8, 13, 1, 0, tzinfo=UTC)

    first_scheduler = SemanticScheduler.from_store(store)
    packet = first_scheduler.claim_semantic_batch(
        lease_owner="codex-a",
        max_context_tokens=8_000,
        lease_seconds=60,
        now=now,
    )
    assert packet is not None
    assert packet.symbols[0].source_body.startswith("def value")
    assert packet.lease_expires_at == now + timedelta(seconds=60)

    recovered_scheduler = SemanticScheduler.from_store(store)
    assert recovered_scheduler.recover_batch(packet.batch_id, now=now) == packet
    assert recovered_scheduler.claim_semantic_batch(
        lease_owner="codex-b",
        max_context_tokens=8_000,
        now=now,
    ) is None

    reclaimed = recovered_scheduler.claim_semantic_batch(
        lease_owner="codex-b",
        max_context_tokens=8_000,
        now=now + timedelta(seconds=61),
    )
    assert reclaimed is not None
    assert reclaimed.lease_owner == "codex-b"


def test_fresh_callee_unlocks_its_caller_from_reopened_store(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "app.py").write_text(
        "def leaf():\n    return 1\n\ndef caller():\n    return leaf()\n",
        encoding="utf-8",
    )
    store = SemanticLedgerStore(tmp_path)
    ledger = store.create()
    leaf = ledger.symbols["app.py::leaf"]
    explanation = SemanticExplanation(
        text="Returns the stable leaf value without reading or mutating external state.",
        explained_content_hash=leaf.content_hash,
        producer="codex-test",
        created_at=datetime(2026, 8, 13, tzinfo=UTC),
    )
    authored = reconcile_semantic_ledger(
        enumerate_semantic_inventory(tmp_path),
        ledger,
        explanation_overrides={"app.py::leaf": explanation},
        order_override=("app.py::leaf",),
    )
    store.commit(authored)

    scheduler = SemanticScheduler.from_store(store)
    assert tuple(item.members for item in scheduler.ready_frontier()) == (
        ("app.py::caller",),
    )


def test_single_symbol_packet_compresses_dependency_text_before_source(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = "def leaf():\n    return 1\n\ndef caller():\n    return leaf()\n"
    (tmp_path / "app.py").write_text(source, encoding="utf-8")
    store = SemanticLedgerStore(tmp_path)
    ledger = store.create()
    leaf = ledger.symbols["app.py::leaf"]
    long_text = "Explains the leaf dependency and its stable return value. " * 120
    explanation = SemanticExplanation(
        text=long_text,
        explained_content_hash=leaf.content_hash,
        producer="codex-test",
        created_at=datetime(2026, 8, 13, tzinfo=UTC),
    )
    authored = reconcile_semantic_ledger(
        enumerate_semantic_inventory(tmp_path),
        ledger,
        explanation_overrides={"app.py::leaf": explanation},
        order_override=("app.py::leaf",),
    )
    store.commit(authored)

    scheduler = SemanticScheduler.from_store(store)
    packet = scheduler.claim_semantic_batch(
        lease_owner="codex-a",
        max_context_tokens=3_300,
        now=datetime(2026, 8, 13, 3, 0, tzinfo=UTC),
    )
    assert packet is not None
    symbol = packet.symbols[0]
    assert symbol.source_body == "def caller():\n    return leaf()"
    assert symbol.callee_ids == ("app.py::leaf",)
    assert 0 < len(symbol.callee_explanations[0][1]) < len(long_text)
    assert not packet.oversize


def test_large_cycle_is_paged_without_unlocking_its_caller(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "app.py").write_text(
        "def cycle_a():\n"
        "    return cycle_b()\n\n"
        "def cycle_b():\n"
        "    return cycle_a()\n\n"
        "def caller():\n"
        "    return cycle_a()\n",
        encoding="utf-8",
    )
    store = SemanticLedgerStore(tmp_path)
    store.create()
    scheduler = SemanticScheduler.from_store(store)
    now = datetime(2026, 8, 13, 2, 0, tzinfo=UTC)

    first = scheduler.claim_semantic_batch(
        lease_owner="codex-a",
        max_context_tokens=2_510,
        now=now,
    )
    second = scheduler.claim_semantic_batch(
        lease_owner="codex-b",
        max_context_tokens=2_510,
        now=now,
    )

    assert first is not None and second is not None
    assert first.scc_id == second.scc_id
    assert first.cycle_members == second.cycle_members == (
        "app.py::cycle_a",
        "app.py::cycle_b",
    )
    assert len(first.symbols) == len(second.symbols) == 1
    assert first.symbols[0].symbol_id != second.symbols[0].symbol_id
    assert all("app.py::caller" not in item.members for item in scheduler.ready_frontier())
