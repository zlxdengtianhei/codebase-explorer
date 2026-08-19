"""Executable proof for the frozen inbound protocol fixture.

The fixture files and oracle are read-only inputs.  The parser's serialized
typed IR is compared site-for-site with the frozen oracle before the v3
reverse projection is checked.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.ir import (
    CallOutcome,
    CallResolution,
    CallSiteAnchor,
    CallSiteInventory,
    EntityRef,
    EntityKind,
    EvidenceSpan,
    Provenance,
    ProvenanceBasis,
    Relation,
    RepositoryEntityIdentity,
    ResolutionMethod,
    ResolutionStatus,
    ReceiverShape,
    SourceUnit,
    SourceUnitState,
    Symbol,
    TargetEvidence,
    deterministic_entity_id,
    deserialize_model,
    serialize_model,
)
from src.parser.adapters.base import FileIR
from src.parser.adapters.python import PythonLanguageAdapter
from src.parser.backend import PythonAstBackend, SyntaxArtifact
from src.semantic.models import SemanticSymbolKind, SemanticSymbolRecord
from src.semantic.render import (
    inbound_view_from_payload,
    inbound_view_from_reverse_index,
    render_inbound_section,
)
from src.server import _python_semantic_ir_cached
import src.graph.reverse_edges as reverse_edges


FIXTURE = Path(__file__).parent / "fixtures" / "inbound_protocol"
ORACLE = json.loads((FIXTURE / "oracle.json").read_text(encoding="utf-8"))
FIXTURE_REVISION = str(ORACLE["source_revision_id"])


def _fixture_ir() -> tuple[tuple[object, ...], tuple[object, ...], tuple[object, ...]]:
    backend = PythonAstBackend(root=FIXTURE)
    adapter = PythonLanguageAdapter(FIXTURE)
    symbols: list[object] = []
    relations: list[object] = []
    inventories: list[object] = []
    for relative in ("base.py", "calls.py", "zero_calls.py"):
        source = (FIXTURE / relative).read_text(encoding="utf-8")
        unit = SourceUnit(
            id=deterministic_entity_id(
                FIXTURE_REVISION, relative, EntityKind.SOURCE_UNIT, relative
            ),
            source_revision_id=FIXTURE_REVISION,
            path=relative,
            language="python",
            content_hash=hashlib.sha256(source.encode("utf-8")).hexdigest(),
            state=SourceUnitState.DISCOVERED,
            backend_id=backend.backend_id,
            backend_version=backend.backend_version,
        )
        artifact = backend.parse(unit)
        assert isinstance(artifact, SyntaxArtifact)
        result = adapter.normalize(artifact)
        assert isinstance(result, FileIR)
        assert result.call_site_inventory is not None
        symbols.extend(result.symbols)
        relations.extend(result.relations)
        inventories.append(result.call_site_inventory)
    return tuple(symbols), tuple(relations), tuple(inventories)


def _serialized_fixture_ir() -> tuple[
    tuple[object, ...], tuple[object, ...], tuple[object, ...]
]:
    """Replay the parser output through the canonical JSON model boundary."""

    symbols, relations, inventories = _fixture_ir()
    round_tripped = tuple(
        deserialize_model(serialize_model(model), type(model))
        for model in (*symbols, *relations, *inventories)
    )
    symbol_count = len(symbols)
    relation_count = len(relations)
    assert round_tripped[:symbol_count] == symbols
    assert round_tripped[symbol_count : symbol_count + relation_count] == relations
    assert round_tripped[symbol_count + relation_count :] == inventories
    return (
        round_tripped[:symbol_count],
        round_tripped[symbol_count : symbol_count + relation_count],
        round_tripped[symbol_count + relation_count :],
    )


def _site_key(span: object) -> str:
    return (
        f"{span.path}:{span.start_line}:{span.start_column}:"
        f"{span.end_line}:{span.end_column}"
    )


def _target_id(target_evidence: object | None) -> str | None:
    if target_evidence is None:
        return None
    return target_evidence.target.ref.id


def _assert_fixture_oracle(
    symbols: tuple[object, ...],
    relations: tuple[object, ...],
    inventories: tuple[object, ...],
    index: reverse_edges.ReverseIndex,
) -> dict[str, float]:
    """Require exact parser, inventory, and reverse-payload agreement.

    The oracle is deliberately checked against the real parser models and the
    builder's emitted payload independently.  This keeps a hand-written
    sidecar or a readings-only assertion from masking a site-level mutation.
    """

    oracle_by_site = {row["site_key"]: row for row in ORACLE["call_sites"]}
    assert len(oracle_by_site) == 45
    typed_relations = {
        relation.id: relation
        for relation in relations
        if relation.kind == "call" and relation.path.endswith((".py", ".pyi"))
    }
    anchors = {
        _site_key(anchor.span): anchor
        for inventory in inventories
        for anchor in inventory.call_sites
    }
    assert len(typed_relations) == 45
    assert len(anchors) == 45
    assert set(anchors) == set(oracle_by_site)
    assert set(typed_relations) == {anchor.call_site_id for anchor in anchors.values()}

    relation_by_site = {
        _site_key(relation.evidence[0]): relation
        for relation in typed_relations.values()
    }
    assert set(relation_by_site) == set(oracle_by_site)
    for site, expected in oracle_by_site.items():
        anchor = anchors[site]
        relation = relation_by_site[site]
        resolution = relation.call_resolution
        assert resolution is not None
        assert relation.source_revision_id == FIXTURE_REVISION
        assert relation.path == expected["path"]
        assert relation.evidence == (anchor.span,)
        assert anchor.caller_canonical_id == expected["caller_id"]
        assert resolution.receiver_shape.value == expected["receiver_shape"]
        assert resolution.outcome.value == expected["outcome"]
        assert _target_id(resolution.runtime_exact_target) == expected["runtime_exact_target_id"]
        assert _target_id(resolution.lexical_base_target) == expected["lexical_base_target_id"]
        assert [
            item.target.ref.id for item in resolution.override_candidates
        ] == expected["override_candidate_ids"]
        assert (
            None
            if resolution.external_target is None
            else resolution.external_target.external_id
        ) == expected["external_identity"]
        assert (
            None
            if resolution.unresolved_or_deep_receiver is None
            else resolution.unresolved_or_deep_receiver.reason.value
        ) == expected["gap_reason"]

    payload = index.to_payload()
    reverse_edges.validate_reverse_payload(payload)
    readings = payload["readings"]
    expected_readings = {
        "n_all_ast_calls": 45,
        "n_call_relations": 45,
        "n_runtime_exact": 17,
        "n_virtual_dispatch": 11,
        "n_external": 2,
        "n_unresolved_or_deep": 15,
        "reconciled": True,
        "edges_runtime_exact": 17,
        "edges_lexical_base": 11,
        "edges_override_candidate": 7,
    }
    assert {key: readings[key] for key in expected_readings} == expected_readings

    ir_to_canonical = {
        ir_id: canonical_id
        for canonical_id, symbol in payload["symbols"].items()
        for ir_id in symbol["ir_symbol_ids"]
    }
    edges_by_site: dict[str, list[dict[str, object]]] = {}
    for rows in payload["by_callee_symbol"].values():
        for edge in rows:
            edges_by_site.setdefault(edge["call_site_id"], []).append(edge)
    external_by_site = {row["call_site_id"]: row for row in payload["external_sites"]}
    unresolved_by_site = {row["call_site_id"]: row for row in payload["unresolved_sites"]}
    assert set(edges_by_site) | set(external_by_site) | set(unresolved_by_site) == set(
        typed_relations
    )
    assert not (set(edges_by_site) & set(external_by_site))
    assert not (set(edges_by_site) & set(unresolved_by_site))
    assert not (set(external_by_site) & set(unresolved_by_site))

    expected_runtime_sites: set[str] = set()
    actual_runtime_sites: set[str] = set()
    expected_candidates: set[tuple[str, str]] = set()
    actual_candidates: set[tuple[str, str]] = set()
    for site, expected in oracle_by_site.items():
        relation = relation_by_site[site]
        call_site_id = relation.id
        outcome = expected["outcome"]
        if outcome == "runtime_exact":
            expected_runtime_sites.add(call_site_id)
            rows = edges_by_site.get(call_site_id, [])
            assert len(rows) == 1
            edge = rows[0]
            assert edge["resolution"] == "runtime_exact"
            assert edge["callee_id"] == ir_to_canonical[expected["runtime_exact_target_id"]]
            assert edge["caller_id"] == expected["caller_id"]
            assert edge["line"] == expected["span"]["start_line"]
            assert edge["candidate_target_ids"] == []
            actual_runtime_sites.add(call_site_id)
        elif outcome == "virtual_dispatch":
            rows = edges_by_site.get(call_site_id, [])
            expected_ids = [
                expected["lexical_base_target_id"],
                *expected["override_candidate_ids"],
            ]
            expected_canonical = {
                ir_to_canonical[target_id] for target_id in expected_ids
            }
            assert len(rows) == len(expected_canonical)
            for target_id in expected_ids:
                expected_candidates.add((call_site_id, ir_to_canonical[target_id]))
            for edge in rows:
                assert edge["caller_id"] == expected["caller_id"]
                assert edge["line"] == expected["span"]["start_line"]
                assert set(edge["candidate_target_ids"]) == expected_canonical
                assert edge["callee_id"] in expected_canonical
                actual_candidates.add((call_site_id, edge["callee_id"]))
            assert sum(edge["resolution"] == "lexical_base" for edge in rows) == 1
            assert sum(edge["resolution"] == "override_candidate" for edge in rows) == len(
                expected["override_candidate_ids"]
            )
            lexical_id = expected["lexical_base_target_id"]
            assert any(
                edge["resolution"] == "lexical_base"
                and edge["callee_id"] == ir_to_canonical[lexical_id]
                for edge in rows
            )
        elif outcome == "external":
            assert call_site_id not in edges_by_site
            assert call_site_id not in unresolved_by_site
            row = external_by_site[call_site_id]
            assert row["caller_id"] == expected["caller_id"]
            assert row["line"] == expected["span"]["start_line"]
            assert row["receiver_shape"] == expected["receiver_shape"]
            assert row["external_id"] == expected["external_identity"]
        else:
            assert outcome == "unresolved_or_deep"
            assert call_site_id not in edges_by_site
            assert call_site_id not in external_by_site
            row = unresolved_by_site[call_site_id]
            assert row["caller_id"] == expected["caller_id"]
            assert row["line"] == expected["span"]["start_line"]
            assert row["receiver_shape"] == expected["receiver_shape"]
            assert row["reason"] == expected["gap_reason"]
            assert row["receiver_text"]

    assert actual_runtime_sites == expected_runtime_sites
    assert actual_candidates == expected_candidates

    class _NoDuplicateLabels:
        @staticmethod
        def symbol_labels(_symbol_id: str, _path: str) -> list[str]:
            return []

    inbound = inbound_view_from_reverse_index(index)
    for canonical_id, body in payload["symbols"].items():
        record = SemanticSymbolRecord(
            path=body["path"],
            qualified_name=canonical_id.split("::", 1)[1],
            kind=SemanticSymbolKind(body["kind"]),
            span=tuple(body["span"]),
            content_hash="sha256:" + ("0" * 64),
        )
        rendered = "\n".join(
            render_inbound_section(
                canonical_id,
                record,
                inbound,
                _NoDuplicateLabels(),
                repo_root=FIXTURE,
            )
        )
        exact_at = rendered.index("**精确**")
        lexical_at = rendered.index("**词法基类（非精确答案）**")
        override_at = rendered.index("**歧义候选（非答案）**")
        blind_at = rendered.index("**静态盲区**")
        assert exact_at < lexical_at < override_at < blind_at
        assert "~" not in rendered[exact_at:lexical_at]
        assert f"runtime exact **{len(inbound.runtime_exact_of(canonical_id))}**" in rendered
        assert f"lexical base **{len(inbound.lexical_base_of(canonical_id))}**" in rendered
        assert (
            f"override candidates **{len(inbound.override_of(canonical_id))}**"
            in rendered
        )
    exact_precision = len(actual_runtime_sites & expected_runtime_sites) / len(actual_runtime_sites)
    candidate_recall = len(actual_candidates & expected_candidates) / len(expected_candidates)
    assert exact_precision == 1.0
    assert candidate_recall == 1.0
    return {
        "exact_precision": exact_precision,
        "candidate_recall": candidate_recall,
        "site_matches": float(len(oracle_by_site)),
    }


def test_fixture_parser_ir_round_trip_reverse_and_renderer_v3() -> None:
    symbols, relations, inventories = _serialized_fixture_ir()

    index = reverse_edges.build_reverse_index_from_ir(
        symbols,
        relations,
        inventories,
        repo="inbound_protocol",
    )
    payload = index.to_payload()
    reverse_edges.validate_reverse_payload(payload)
    assert payload["schema"] == "cbe-reverse-edges/3"
    assert payload["source"] == "cbe-ir/3 Relation(kind=call)+CallSiteInventory"
    assert payload["readings"]["n_all_ast_calls"] == len(ORACLE["call_sites"])
    assert payload["readings"]["n_call_relations"] == len(ORACLE["call_sites"])
    assert "by_name" not in json.dumps(payload, sort_keys=True)
    metrics = _assert_fixture_oracle(symbols, relations, inventories, index)
    assert metrics == {
        "exact_precision": 1.0,
        "candidate_recall": 1.0,
        "site_matches": 45.0,
    }

    # The real parser output is the only input to reverse; no sidecar is
    # allowed to provide outcomes or caller rows.
    assert all(relation.call_resolution is not None for relation in relations if relation.kind == "call")
    assert all(inventory.call_sites is not None for inventory in inventories)
    answer = index.callers_of("base.py::Base.save")
    assert not answer.runtime_exact
    assert answer.lexical_base
    override_answer = index.callers_of("base.py::Child.save")
    assert override_answer.override_candidates


def _json_fixture_payload() -> dict[str, object]:
    symbols, relations, inventories = _serialized_fixture_ir()
    index = reverse_edges.build_reverse_index_from_ir(
        symbols,
        relations,
        inventories,
        repo="inbound_protocol",
    )
    # Exercise the exact JSON-decoded shape used by sidecars and renderer
    # ingress: tuple fields arrive as lists, while their scalar members retain
    # their JSON scalar types.
    return json.loads(json.dumps(index.to_payload()))


def _set_path(payload: dict[str, object], path: tuple[object, ...], value: object) -> None:
    current: object = payload
    for key in path[:-1]:
        current = current[key]  # type: ignore[index]
    current[path[-1]] = value  # type: ignore[index]


def _strict_integer_mutations(payload: dict[str, object]):
    readings = payload["readings"]
    for field in (
        "n_all_ast_calls",
        "n_call_relations",
        "n_runtime_exact",
        "n_virtual_dispatch",
        "n_external",
        "n_unresolved_or_deep",
        "edges_runtime_exact",
        "edges_lexical_base",
        "edges_override_candidate",
    ):
        yield f"readings.{field}=string", ("readings", field), str(readings[field])

    for field in ("receiver_shape_histogram", "gap_reason_histogram"):
        for key, value in readings[field].items():
            yield f"readings.{field}.{key}=string", ("readings", field, key), str(value)

    first_symbol = next(iter(payload["symbols"].values()))
    for index, value in enumerate(first_symbol["span"]):
        yield f"symbols.*.span[{index}]=string", ("symbols", next(iter(payload["symbols"])), "span", index), str(value)
        yield f"symbols.*.span[{index}]=float", ("symbols", next(iter(payload["symbols"])), "span", index), float(value)

    first_edge = next(
        row
        for rows in payload["by_callee_symbol"].values()
        for row in rows
    )
    yield "edge.line=string", ("by_callee_symbol", next(iter(payload["by_callee_symbol"])), 0, "line"), "1"
    yield "edge.line=float", ("by_callee_symbol", next(iter(payload["by_callee_symbol"])), 0, "line"), 1.0
    assert first_edge["line"] >= 1

    first_unresolved = payload["unresolved_sites"][0]
    yield "unresolved.line=string", ("unresolved_sites", 0, "line"), "1"
    yield "unresolved.line=float", ("unresolved_sites", 0, "line"), 1.0
    assert first_unresolved["line"] >= 1

    first_external = payload["external_sites"][0]
    yield "external.line=string", ("external_sites", 0, "line"), "1"
    yield "external.line=float", ("external_sites", 0, "line"), 1.0
    assert first_external["line"] >= 1

    # bool is a subclass of int in Python but is not a legal protocol integer.
    yield "edge.line=bool", ("by_callee_symbol", next(iter(payload["by_callee_symbol"])), 0, "line"), True


def test_v3_json_integer_fields_are_strict_at_reverse_and_renderer_boundaries() -> None:
    payload = _json_fixture_payload()
    for label, path, value in _strict_integer_mutations(payload):
        mutated = json.loads(json.dumps(payload))
        _set_path(mutated, path, value)
        with pytest.raises(reverse_edges.ReverseEdgeError):
            reverse_edges.validate_reverse_payload(mutated)
        with pytest.raises(reverse_edges.ReverseEdgeError):
            inbound_view_from_payload(mutated)


def test_v3_json_decoded_lists_remain_accepted_at_both_boundaries() -> None:
    payload = _json_fixture_payload()
    assert reverse_edges.validate_reverse_payload(payload).schema == "cbe-reverse-edges/3"
    assert inbound_view_from_payload(payload).known_ids


def test_server_bridge_preserves_independent_inventory_carrier() -> None:
    symbols, relations, inventories = _python_semantic_ir_cached(
        FIXTURE.as_posix(),
        "sha256:3e211438ba32720bd4ba40daed54e9cef3bf92395a497f2686211e339aac4e4f",
    )
    assert len(inventories) == 3
    assert sum(len(item.call_sites) for item in inventories) == 45
    assert len([item for item in relations if item.kind == "call"]) == 45
    assert symbols and relations


def _call_relation(relations: tuple[object, ...], caller: str, line: int) -> object:
    for relation in relations:
        if relation.kind != "call" or relation.evidence[0].start_line != line:
            continue
        fields = relation.locator.split(":", 6)
        if len(fields) == 7 and fields[-1] == caller:
            return relation
    raise AssertionError(f"fixture call relation not found: {caller} line {line}")


def _replace_relation(
    relations: tuple[object, ...], original: object, replacement: object
) -> tuple[object, ...]:
    return tuple(replacement if relation.id == original.id else relation for relation in relations)


def _index(
    symbols: tuple[object, ...], relations: tuple[object, ...], inventories: tuple[object, ...]
) -> reverse_edges.ReverseIndex:
    return reverse_edges.build_reverse_index_from_ir(
        symbols, relations, inventories, repo="inbound_protocol"
    )


def _promote_relation(relation: object, target: object) -> object:
    resolution = relation.call_resolution
    assert resolution is not None
    promoted = resolution.model_copy(
        update={
            "outcome": CallOutcome.RUNTIME_EXACT,
            "runtime_exact_target": target,
            "lexical_base_target": None,
            "override_candidates": (),
            "external_target": None,
            "unresolved_or_deep_receiver": None,
        }
    )
    return relation.model_copy(update={"call_resolution": promoted})


def test_inbound_mutation_promotion_lexical_base_cannot_be_runtime_exact() -> None:
    symbols, relations, inventories = _fixture_ir()
    baseline = _index(symbols, relations, inventories)
    source = _call_relation(relations, "calls.py::use_annotated", 40)
    assert source.call_resolution is not None
    lexical_target = source.call_resolution.lexical_base_target
    assert lexical_target is not None
    mutated = _replace_relation(relations, source, _promote_relation(source, lexical_target))
    mutated_index = _index(symbols, mutated, inventories)
    with pytest.raises(AssertionError):
        _assert_fixture_oracle(symbols, mutated, inventories, mutated_index)
    _assert_fixture_oracle(symbols, relations, inventories, baseline)


def test_inbound_mutation_name_guess_cannot_add_unrelated_same_name_override() -> None:
    symbols, relations, inventories = _fixture_ir()
    baseline = _index(symbols, relations, inventories)
    source = _call_relation(relations, "calls.py::use_unrelated", 64)
    known_virtual = _call_relation(relations, "calls.py::use_annotated", 40)
    assert source.call_resolution is not None
    assert known_virtual.call_resolution is not None
    child_target = known_virtual.call_resolution.override_candidates[0]
    guessed = source.call_resolution.model_copy(update={"override_candidates": (child_target,)})
    mutated = _replace_relation(relations, source, source.model_copy(update={"call_resolution": guessed}))
    mutated_index = _index(symbols, mutated, inventories)
    with pytest.raises(AssertionError):
        _assert_fixture_oracle(symbols, mutated, inventories, mutated_index)
    _assert_fixture_oracle(symbols, relations, inventories, baseline)


def test_inbound_mutation_silent_relation_drop_cannot_change_inventory_denominator() -> None:
    symbols, relations, inventories = _fixture_ir()
    dropped = _call_relation(relations, "calls.py::<module>", 20)
    remaining = tuple(relation for relation in relations if relation.id != dropped.id)
    with pytest.raises(reverse_edges.ReverseEdgeError, match="ID set mismatch"):
        _index(symbols, remaining, inventories)


def test_inbound_mutation_decorator_or_incomplete_mro_promotion_stays_visible_as_gap() -> None:
    symbols, relations, inventories = _fixture_ir()
    baseline = _index(symbols, relations, inventories)
    source = _call_relation(relations, "base.py::UnknownChild.call", 78)
    known_virtual = _call_relation(relations, "calls.py::use_annotated", 40)
    assert known_virtual.call_resolution is not None
    lexical_target = known_virtual.call_resolution.lexical_base_target
    assert lexical_target is not None
    mutated = _replace_relation(relations, source, _promote_relation(source, lexical_target))
    mutated_index = _index(symbols, mutated, inventories)
    with pytest.raises(AssertionError):
        _assert_fixture_oracle(symbols, mutated, inventories, mutated_index)
    _assert_fixture_oracle(symbols, relations, inventories, baseline)


def test_inbound_mutation_serialized_override_removal_breaks_reverse_projection() -> None:
    symbols, relations, inventories = _fixture_ir()
    baseline = _index(symbols, relations, inventories)
    source = _call_relation(relations, "base.py::Diamond.call", 68)
    encoded = json.loads(serialize_model(source))
    assert encoded["payload"]["call_resolution"]["override_candidates"]
    del encoded["payload"]["call_resolution"]["override_candidates"]
    restored = deserialize_model(json.dumps(encoded), type(source))
    mutated = _replace_relation(relations, source, restored)
    mutated_index = _index(symbols, mutated, inventories)
    with pytest.raises(AssertionError):
        _assert_fixture_oracle(symbols, mutated, inventories, mutated_index)
    _assert_fixture_oracle(symbols, relations, inventories, baseline)


def _duplicate_symbol_inputs(
    family: str,
) -> tuple[tuple[Symbol, ...], tuple[Relation, ...], tuple[CallSiteInventory, ...], str, Symbol, Symbol]:
    """Build one exact call into a duplicate-display Symbol family.

    These are the two source shapes that exposed the reverse projection bug:
    overload declarations share a function display name, while a property
    getter and setter share a method display name.  The source-unit and
    definition locators remain distinct so the target identity checks are
    exercised rather than replaced with a name lookup.
    """

    if family == "flask-overload":
        path = "src/flask/cli.py"
        qualified_name = "src.flask.cli.locate_app"
        local_name = "locate_app"
        kind = "function"
        definitions = (
            ("python:function:src.flask.cli.locate_app:230:0", 230, ("typing.overload",)),
            ("python:function:src.flask.cli.locate_app:236:0", 236, ("typing.overload",)),
            ("python:function:src.flask.cli.locate_app:241:0", 241, ()),
        )
        owner: Symbol | None = None
    elif family == "celery-property":
        path = "celery/app/amqp.py"
        qualified_name = "celery.app.amqp.AMQP.queues"
        local_name = "queues"
        kind = "method"
        definitions = (
            ("python:method:celery.app.amqp.AMQP.queues:607:4", 607, ("cached_property",)),
            ("python:method:celery.app.amqp.AMQP.queues:612:4", 612, ("queues.setter",)),
        )
        owner_locator = "python:class:celery.app.amqp.AMQP:219:0"
        owner_span = EvidenceSpan(
            source_unit_id=deterministic_entity_id(
                FIXTURE_REVISION, path, EntityKind.SOURCE_UNIT, path
            ),
            path=path,
            start_line=219,
            start_column=0,
            end_line=219,
            end_column=4,
        )
        owner = Symbol(
            id=deterministic_entity_id(
                FIXTURE_REVISION, path, EntityKind.SYMBOL, owner_locator
            ),
            source_revision_id=FIXTURE_REVISION,
            source_unit_id=owner_span.source_unit_id,
            path=path,
            kind="class",
            qualified_name="celery.app.amqp.AMQP",
            local_name="AMQP",
            definition_locator=owner_locator,
            definition=owner_span,
            language="python",
            decorators=(),
        )
    else:  # pragma: no cover - callers use the two named product families.
        raise AssertionError(f"unknown duplicate symbol family: {family}")

    source_unit_id = deterministic_entity_id(
        FIXTURE_REVISION, path, EntityKind.SOURCE_UNIT, path
    )
    duplicate_symbols = tuple(
        Symbol(
            id=deterministic_entity_id(
                FIXTURE_REVISION, path, EntityKind.SYMBOL, locator
            ),
            source_revision_id=FIXTURE_REVISION,
            source_unit_id=source_unit_id,
            path=path,
            kind=kind,
            qualified_name=qualified_name,
            local_name=local_name,
            definition_locator=locator,
            definition=EvidenceSpan(
                source_unit_id=source_unit_id,
                path=path,
                start_line=line,
                start_column=0,
                end_line=line,
                end_column=1,
            ),
            language="python",
            decorators=decorators,
        )
        for locator, line, decorators in definitions
    )
    symbols = ((owner,) if owner is not None else ()) + duplicate_symbols

    call_path = "calls.py"
    caller_id = f"{call_path}::caller"
    call_source_unit_id = deterministic_entity_id(
        FIXTURE_REVISION, call_path, EntityKind.SOURCE_UNIT, call_path
    )
    call_span = EvidenceSpan(
        source_unit_id=call_source_unit_id,
        path=call_path,
        start_line=10,
        start_column=4,
        end_line=10,
        end_column=20,
    )
    call_locator = (
        f"python:call:{call_span.start_line}:{call_span.start_column}:"
        f"{call_span.end_line}:{call_span.end_column}:{caller_id}"
    )
    call_id = deterministic_entity_id(
        FIXTURE_REVISION, call_path, EntityKind.RELATION, call_locator
    )

    selected, other = duplicate_symbols[0], duplicate_symbols[-1]

    def _target(symbol: Symbol) -> TargetEvidence:
        identity = RepositoryEntityIdentity(
            ref=EntityRef(kind=EntityKind.SYMBOL, id=symbol.id),
            source_revision_id=FIXTURE_REVISION,
            path=symbol.path,
            definition_locator=symbol.definition_locator,
        )
        return TargetEvidence(
            target=identity,
            provenance=(
                Provenance(
                    basis=ProvenanceBasis.DIRECT_LOCAL_BINDING,
                    evidence=(symbol.definition,),
                    source_revision_id=FIXTURE_REVISION,
                    source_entity=identity,
                ),
            ),
        )

    target = _target(selected)
    resolution = CallResolution(
        outcome=CallOutcome.RUNTIME_EXACT,
        receiver_shape=ReceiverShape.BARE_NAME,
        runtime_exact_target=target,
    )
    relation = Relation(
        id=call_id,
        source_revision_id=FIXTURE_REVISION,
        path=call_path,
        kind="call",
        locator=call_locator,
        source=EntityRef(kind=EntityKind.SYMBOL, id=selected.id),
        target=None,
        evidence=(call_span,),
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_method=ResolutionMethod.EXACT,
        confidence=1.0,
        reason="duplicate target regression",
        candidates=(),
        call_resolution=resolution,
    )
    inventory = CallSiteInventory(
        source_revision_id=FIXTURE_REVISION,
        source_unit_id=call_source_unit_id,
        path=call_path,
        language="python",
        ast_backend_id="duplicate-regression",
        ast_backend_version="1",
        call_sites=(
            CallSiteAnchor(
                call_site_id=call_id,
                caller_canonical_id=caller_id,
                span=call_span,
            ),
        ),
    )
    canonical_id = (
        f"{path}::{qualified_name.removeprefix(path[:-3].replace('/', '.') + '.') }"
        if path.endswith(".py")
        else f"{path}::{qualified_name}"
    )
    return symbols, (relation,), (inventory,), canonical_id, selected, other


def _assert_duplicate_family_projects_exact_target(family: str) -> None:
    symbols, relations, inventories, canonical_id, selected, other = _duplicate_symbol_inputs(family)
    index = _index(symbols, relations, inventories)
    payload = index.to_payload()
    reverse_edges.validate_reverse_payload(payload)

    symbol_body = payload["symbols"][canonical_id]
    assert set(symbol_body["ir_symbol_ids"]) == {item.id for item in symbols if item.kind != "class"}
    edge = payload["by_callee_symbol"][canonical_id][0]
    assert edge["resolution"] == "runtime_exact"
    assert edge["callee_id"] == canonical_id
    via = json.loads(edge["via"])
    assert via["provenance"][0]["source_entity_id"] == selected.id
    assert via["provenance"][0]["source_revision_id"] == FIXTURE_REVISION
    assert via["provenance"][0]["evidence"][0]["path"] == selected.path
    assert selected.definition_locator != other.definition_locator

    # The accepted IR identity, not the public display name, selects the
    # target.  A same-display ref carrying the other definition locator must
    # fail closed instead of being promoted to the selected Symbol.
    target = relations[0].call_resolution.runtime_exact_target
    assert target is not None
    forged_identity = target.target.model_copy(
        update={"definition_locator": other.definition_locator}
    )
    forged_target = target.model_copy(update={"target": forged_identity})
    forged_resolution = relations[0].call_resolution.model_copy(
        update={"runtime_exact_target": forged_target}
    )
    forged_relation = relations[0].model_copy(update={"call_resolution": forged_resolution})
    with pytest.raises(reverse_edges.ReverseEdgeError, match="identity does not match"):
        _index(symbols, (forged_relation,), inventories)


def test_flask_overload_symbols_survive_duplicate_display_projection() -> None:
    _assert_duplicate_family_projects_exact_target("flask-overload")


def test_celery_getter_setter_symbols_survive_duplicate_display_projection() -> None:
    _assert_duplicate_family_projects_exact_target("celery-property")
