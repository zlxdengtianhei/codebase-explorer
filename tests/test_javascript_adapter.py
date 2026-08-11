from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    warnings.simplefilter("ignore", FutureWarning)
    from graph_sitter.tree_sitter_parser import parse_file

from src.ir import EntityKind, Relation, SourceUnit, SourceUnitState, Symbol, deserialize_model, deterministic_entity_id, serialize_model
from src.parser.adapters.javascript import JavaScriptSyntaxAdapter
from src.parser.backend import FailureCode, SyntaxArtifact, TypedFailure


ROOT = Path(__file__).parent
FIXTURES = ROOT / "fixtures/languages/javascript"
ORACLE = json.loads((ROOT / "oracles/contracts/javascript/expected_ir.json").read_text())
REVISION = "rev_" + "2" * 64
PROJECT_CONTEXT_FACT_IDS = frozenset({"js.call.worker.run", "js.call.dynamic"})
PROJECTION_LOSS_FACT_IDS = frozenset({
    "js.call.missing",
    "js.import.dynamic",
    "js.export.dynamic",
    "js.unsupported.commonjs",
})
DEFERRED_FACT_IDS = PROJECT_CONTEXT_FACT_IDS | PROJECTION_LOSS_FACT_IDS


def _artifact(relative_path: str, content: str | None = None) -> SyntaxArtifact:
    content = content if content is not None else (FIXTURES / relative_path).read_text(encoding="utf-8")
    unit = SourceUnit(
        id=deterministic_entity_id(REVISION, relative_path, EntityKind.SOURCE_UNIT, relative_path),
        source_revision_id=REVISION,
        path=relative_path,
        language="javascript",
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        state=SourceUnitState.DISCOVERED,
        backend_id="graph_sitter",
        backend_version="test",
    )
    return SyntaxArtifact(unit, "graph_sitter", "test", "javascript", parse_file(relative_path, content))


def _normalize(relative_path: str):
    return JavaScriptSyntaxAdapter().normalize(_artifact(relative_path))


def _fact_keys(file_ir) -> set[tuple[str, str, int, int]]:
    keys = {("symbol", item.qualified_name, item.definition.start_line, item.definition.start_column) for item in file_ir.symbols}
    keys.update((item.kind, item.locator.split("|", 1)[0], item.evidence[0].start_line, item.evidence[0].start_column) for item in file_ir.relations)
    return keys


def _span_payload(span, source: str) -> dict[str, object]:
    lines = source.encode().splitlines(keepends=True)
    start = sum(len(line) for line in lines[: span.start_line - 1]) + span.start_column
    end = sum(len(line) for line in lines[: span.end_line - 1]) + span.end_column
    raw = source.encode()[start:end]
    return {"byte_offset": start, "byte_length": end - start, "line": span.start_line, "column": span.start_column, "text": raw.decode()}


def _expected_ref_id(target: str, current_path: str) -> str:
    modules = {}
    for path in ORACLE["files"]:
        module = path
        for suffix in (".cjs", ".js"):
            if module.endswith(suffix):
                module = module[: -len(suffix)]
                break
        modules[module] = path
    if target in modules:
        target_path = modules[target]
        return deterministic_entity_id(REVISION, target_path, EntityKind.SOURCE_UNIT, target_path)
    for module in sorted(modules, key=len, reverse=True):
        if target.startswith(module + "."):
            return deterministic_entity_id(REVISION, modules[module], EntityKind.SYMBOL, target)
    return deterministic_entity_id(REVISION, current_path, EntityKind.SYMBOL, target)


def _assert_expected_fact(fact_id: str, fact: dict[str, object], file_ir) -> None:
    source = (FIXTURES / str(fact["path"])).read_text(encoding="utf-8")
    if fact["kind"] == "symbol":
        actual = next(item for item in file_ir.symbols if item.qualified_name == fact["subject"])
        span = actual.definition
        assert dict(actual.language_attributes) == fact["attributes"]
    else:
        prefix = f'{fact["kind"]}:{fact["subject"]}:{fact["span"]["line"]}:{fact["span"]["column"]}'
        actual = next(item for item in file_ir.relations if item.locator.split("|", 1)[0] == prefix)
        span = actual.evidence[0]
        assert actual.resolution_status.value == fact["resolution_status"]
        assert actual.resolution_method.value == fact["resolution_method"]
        if fact["target"] is not None:
            assert actual.target.id == _expected_ref_id(str(fact["target"]), str(fact["path"]))
        assert tuple(item.id for item in actual.candidates) == tuple(_expected_ref_id(str(target), str(fact["path"])) for target in fact["candidates"])
    assert _span_payload(span, source) == fact["span"], fact_id


def test_javascript_complete_oracle_partition_is_mechanical() -> None:
    expected_ids = frozenset(ORACLE["expected_facts"])
    produced = expected_ids - DEFERRED_FACT_IDS
    assert produced | DEFERRED_FACT_IDS == expected_ids
    assert not produced & DEFERRED_FACT_IDS
    assert len(expected_ids) == 20
    assert len(produced) == 14
    assert len(DEFERRED_FACT_IDS) == 6


def test_javascript_target_absent_relations_emit_canonical_null_without_candidates() -> None:
    emitted_fact_ids = PROJECTION_LOSS_FACT_IDS | {
        "js.call.worker.run",
        "js.call.dynamic",
    }
    for fact_id in emitted_fact_ids:
        fact = ORACLE["expected_facts"][fact_id]
        result = _normalize(fact["path"])
        assert not isinstance(result, TypedFailure)
        prefix = f'{fact["kind"]}:{fact["subject"]}:{fact["span"]["line"]}:{fact["span"]["column"]}'
        actual = next(item for item in result.relations if item.locator.split("|", 1)[0] == prefix)
        assert actual.target is None
        assert actual.candidates == ()
        if fact_id in PROJECTION_LOSS_FACT_IDS:
            assert actual.resolution_status.value == fact["resolution_status"]
            assert actual.resolution_method.value == fact["resolution_method"]
        else:
            assert actual.resolution_status.value == "ambiguous"
            assert actual.resolution_method.value == "heuristic"
        assert _span_payload(actual.evidence[0], (FIXTURES / fact["path"]).read_text()) == fact["span"]


def test_javascript_null_relation_remains_distinct_from_legitimate_self_relation_after_round_trip() -> None:
    result = _normalize("src/index.js")
    assert not isinstance(result, TypedFailure)
    null_relation = next(
        item
        for item in result.relations
        if item.resolution_status.value == "ambiguous" and item.target is None
    )
    payload = null_relation.model_dump(mode="python", round_trip=True)
    payload["target"] = null_relation.source
    self_relation = Relation.model_validate(payload)

    null_round_trip = deserialize_model(serialize_model(null_relation), Relation)
    self_round_trip = deserialize_model(serialize_model(self_relation), Relation)
    assert null_round_trip.target is None
    assert self_round_trip.target == self_round_trip.source
    assert serialize_model(null_round_trip) != serialize_model(self_round_trip)


def test_javascript_targetful_unsupported_relation_remains_targetful() -> None:
    fact = ORACLE["expected_facts"]["js.type.base.run"]
    result = _normalize(fact["path"])
    assert not isinstance(result, TypedFailure)
    prefix = f'{fact["kind"]}:{fact["subject"]}:{fact["span"]["line"]}:{fact["span"]["column"]}'
    actual = next(item for item in result.relations if item.locator.split("|", 1)[0] == prefix)
    assert actual.resolution_status.value == "unsupported"
    assert actual.target is not None
    assert actual.target.id == _expected_ref_id("dynamic", str(fact["path"]))
    assert actual.candidates == ()


def test_javascript_exact_produced_symbols_preserve_oracle_attributes() -> None:
    symbol_facts = {
        fact_id: fact
        for fact_id, fact in ORACLE["expected_facts"].items()
        if fact["kind"] == "symbol"
    }
    assert len(symbol_facts) == 4
    for fact_id, fact in symbol_facts.items():
        result = _normalize(fact["path"])
        assert not isinstance(result, TypedFailure)
        actual = next(item for item in result.symbols if item.qualified_name == fact["subject"])
        assert dict(actual.language_attributes) == fact["attributes"], fact_id


def test_javascript_fixture_manifest_hashes_match_immutable_oracle() -> None:
    actual_paths = {path.relative_to(FIXTURES).as_posix() for path in FIXTURES.rglob("*") if path.is_file()}
    assert actual_paths == set(ORACLE["files"])
    for path, spec in ORACLE["files"].items():
        content = (FIXTURES / path).read_bytes()
        assert hashlib.sha256(content).hexdigest() == spec["content_sha256"]


@pytest.mark.parametrize("path", ["src/base.js", "src/impl.js", "src/index.js", "src/dynamic.js", "src/éclair.js"])
def test_javascript_normalizes_actual_tree_sitter_boundary(path: str) -> None:
    result = _normalize(path)
    assert not isinstance(result, TypedFailure)
    assert result.source_unit.state is SourceUnitState.INDEXED
    assert tuple(item.id for item in result.symbols) == tuple(sorted(item.id for item in result.symbols))
    assert tuple(item.id for item in result.relations) == tuple(sorted(item.id for item in result.relations))


def test_javascript_expected_syntax_facts_have_exact_start_spans() -> None:
    all_keys: set[tuple[str, str, int, int]] = set()
    for path, spec in ORACLE["files"].items():
        if spec["expected_state"] in {"indexed", "unsupported"}:
            result = _normalize(path)
            assert not isinstance(result, TypedFailure)
            all_keys |= _fact_keys(result)
    for fact_id, fact in ORACLE["expected_facts"].items():
        if fact_id in DEFERRED_FACT_IDS:
            continue
        subject = fact["subject"]
        key_name = subject if fact["kind"] == "symbol" else f'{fact["kind"]}:{subject}:{fact["span"]["line"]}:{fact["span"]["column"]}'
        assert (fact["kind"], key_name, fact["span"]["line"], fact["span"]["column"]) in all_keys
        result = _normalize(fact["path"])
        assert not isinstance(result, TypedFailure)
        _assert_expected_fact(fact_id, fact, result)


def test_javascript_parse_error_and_commonjs_unsupported_are_terminal() -> None:
    broken = _normalize("src/broken.js")
    assert isinstance(broken, TypedFailure)
    assert broken.code is FailureCode.PARSE_ERROR
    commonjs = _normalize("src/legacy.cjs")
    assert not isinstance(commonjs, TypedFailure)
    assert commonjs.source_unit.state is SourceUnitState.UNSUPPORTED
    assert any(item.kind == "unsupported_construct" for item in commonjs.relations)


def test_javascript_calls_are_bounded_and_wrong_language_is_rejected() -> None:
    valid = _normalize("src/index.js")
    assert not isinstance(valid, TypedFailure)
    assert all(item.resolution_method.value != "compiler" for item in valid.relations)
    artifact = _artifact("src/index.js")
    wrong = SyntaxArtifact(artifact.source_unit, artifact.backend_id, artifact.backend_version, "typescript", artifact.syntax_tree)
    result = JavaScriptSyntaxAdapter().normalize(wrong)
    assert isinstance(result, TypedFailure)
    assert result.code is FailureCode.UNSUPPORTED_LANGUAGE
    base = _normalize("src/base.js")
    assert not isinstance(base, TypedFailure)
    error_call = next(item for item in base.relations if item.kind == "call" and item.resolution_status.value == "unresolved")
    assert error_call.source.id == deterministic_entity_id(
        REVISION, "src/base.js", EntityKind.SYMBOL, "src/base.Base.run"
    )


def test_javascript_ir_is_repeatable_and_canonical_round_trip() -> None:
    first = _normalize("src/index.js")
    second = _normalize("src/index.js")
    assert first == second
    assert not isinstance(first, TypedFailure)
    models = (first.source_unit, *first.symbols, *first.relations)
    for model in models:
        model_type = SourceUnit if isinstance(model, SourceUnit) else Symbol if isinstance(model, Symbol) else Relation
        assert deserialize_model(serialize_model(model), model_type) == model


def test_javascript_mutation_oracle_is_replayed_without_stale_fact_reuse() -> None:
    mutations = json.loads((ROOT / "oracles/contracts/javascript/mutations.json").read_text())["mutations"]
    assert set(mutations) == {"js.replace_call", "js.corrupt_span", "js.remove_backend"}
    mutation = mutations["js.replace_call"]
    original = (FIXTURES / mutation["path"]).read_text(encoding="utf-8")
    changed = original.replace(mutation["old_text"], mutation["new_text"])
    result = JavaScriptSyntaxAdapter().normalize(_artifact(mutation["path"], changed))
    assert not isinstance(result, TypedFailure)
    dynamic = [item for item in result.relations if item.source.id == deterministic_entity_id(REVISION, "src/index.js", EntityKind.SYMBOL, "src/index.dynamic") and item.kind == "call"]
    assert len(dynamic) == 1
    assert dynamic[0].resolution_status.value == "resolved"
    assert dynamic[0].resolution_method.value == "exact"
    assert _span_payload(dynamic[0].evidence[0], changed)["text"] == mutation["new_text"]
    corrupt = mutations["js.corrupt_span"]
    valid = _normalize(corrupt["path"])
    assert not isinstance(valid, TypedFailure)
    missing = next(item for item in valid.relations if item.kind == "call" and item.resolution_status.value == "unresolved")
    valid_span = _span_payload(missing.evidence[0], original)
    corrupted_span = next(iter(corrupt["created_facts"].values()))["span"]
    removed_span = next(iter(corrupt["removed_facts"].values()))["span"]
    assert valid_span == removed_span
    assert valid_span != corrupted_span
    assert corrupt["expected_verdict"] == "fail"
    assert mutations["js.remove_backend"]["expected_verdict"] == "unavailable"
