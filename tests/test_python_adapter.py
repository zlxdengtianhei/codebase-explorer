"""Frozen-oracle tests for the Python canonical-IR adapter."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

import src.parser.adapters.python as python_adapter_module

from src.ir import (
    Availability,
    EntityKind,
    ResolutionMethod,
    ResolutionStatus,
    SemanticTier,
    SourceUnit,
    SourceUnitState,
    VerificationStatus,
    deserialize_model,
    deterministic_entity_id,
    serialize_model,
)
from src.parser.adapters.base import FileIR
from src.parser.adapters.python import PythonLanguageAdapter
from src.parser.adapters.registry import BackendRegistry
from src.parser.backend import FailureCode, PythonAstBackend, SyntaxArtifact, TypedFailure
from src.parser.codebase import CodebaseParser


ROOT = Path(__file__).parent / "fixtures" / "languages" / "python"
ORACLE_ROOT = Path(__file__).parent / "oracles" / "contracts" / "python"
REVISION = "rev_" + "7" * 64


def _json(name: str) -> dict[str, object]:
    return json.loads((ORACLE_ROOT / name).read_text(encoding="utf-8"))


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _unit(path: str, *, language: str = "python") -> SourceUnit:
    source = _source(path)
    return SourceUnit(
        id=deterministic_entity_id(REVISION, path, EntityKind.SOURCE_UNIT, path),
        source_revision_id=REVISION,
        path=path,
        language=language,
        content_hash=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        state=SourceUnitState.DISCOVERED,
        backend_id="python_ast",
        backend_version="test",
    )


def _artifact(path: str, source: str | None = None) -> SyntaxArtifact:
    text = _source(path) if source is None else source
    unit = _unit(path)
    if source is not None:
        unit = unit.model_copy(
            update={"content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest()}
        )
    return SyntaxArtifact(
        source_unit=unit,
        backend_id="python_ast",
        backend_version="test",
        language="python",
        syntax_tree=ast.parse(text, filename=path),
    )


def _inline_result(tmp_path: Path, source: str, *, path: str = "probe.py") -> FileIR:
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    unit = SourceUnit(
        id=deterministic_entity_id(REVISION, path, EntityKind.SOURCE_UNIT, path),
        source_revision_id=REVISION,
        path=path,
        language="python",
        content_hash=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        state=SourceUnitState.DISCOVERED,
        backend_id="python_ast",
        backend_version="test",
    )
    artifact = PythonAstBackend(root=tmp_path).parse(unit)
    assert isinstance(artifact, SyntaxArtifact)
    result = PythonLanguageAdapter(tmp_path).normalize(artifact)
    assert isinstance(result, FileIR)
    return result


def _span_text(root: Path, span) -> str:  # type: ignore[no-untyped-def]
    raw = (root / span.path).read_bytes()
    lines = raw.splitlines(keepends=True)
    start = sum(len(line) for line in lines[: span.start_line - 1]) + span.start_column
    end = sum(len(line) for line in lines[: span.end_line - 1]) + span.end_column
    return raw[start:end].decode("utf-8")


def _relation_for_fact(file_ir: FileIR, fact):  # type: ignore[no-untyped-def]
    matches = [
        relation
        for relation in file_ir.relations
        if relation.kind == fact["kind"]
        and relation.resolution_status.value == fact["resolution_status"]
        and relation.resolution_method.value == fact["resolution_method"]
        and relation.evidence[0].start_line == fact["span"]["line"]
        and relation.evidence[0].start_column == fact["span"]["column"]
    ]
    if len(matches) > 1 and fact["target"] is not None:
        matches = [
            relation
            for relation in matches
            if relation.target.id
            == _expected_reference_id(file_ir.source_unit, fact["target"])
        ]
    assert len(matches) == 1, fact
    return matches[0]


def _expected_reference_id(source_unit: SourceUnit, qualified_name: str) -> str:
    for path in ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT).as_posix()
        module = ".".join(Path(relative).with_suffix("").parts)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        def find(body, scope=()):  # type: ignore[no-untyped-def]
            for node in body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    candidate = ".".join((module, *scope, node.name))
                    if candidate == qualified_name:
                        kind = (
                            "class"
                            if isinstance(node, ast.ClassDef)
                            else "method" if scope else "function"
                        )
                        locator = f"python:{kind}:{candidate}:{node.lineno}:{node.col_offset}"
                        return deterministic_entity_id(
                            source_unit.source_revision_id,
                            relative,
                            EntityKind.SYMBOL,
                            locator,
                        )
                    found = find(node.body, (*scope, node.name))
                    if found is not None:
                        return found
            return None

        found = find(tree.body)
        if found is not None:
            return found
    return deterministic_entity_id(
        source_unit.source_revision_id,
        source_unit.path,
        EntityKind.SYMBOL,
        f"reference:{qualified_name}",
    )


def _span_bytes(path: str, span) -> tuple[int, int, str]:  # type: ignore[no-untyped-def]
    raw = _source(path).encode("utf-8")
    lines = raw.splitlines(keepends=True)
    offset = sum(len(line) for line in lines[: span.start_line - 1]) + span.start_column
    end = sum(len(line) for line in lines[: span.end_line - 1]) + span.end_column
    return offset, end - offset, raw[offset:end].decode("utf-8")


def test_frozen_fixture_bytes_match_oracle_before_adapter_execution() -> None:
    oracle = _json("expected_ir.json")
    for path, spec in oracle["files"].items():  # type: ignore[union-attr]
        raw = (ROOT / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == spec["content_sha256"]
        assert raw.decode("utf-8") == "\n".join(spec["content_lines"]) + "\n"


def test_python_adapter_replays_representable_frozen_facts_and_exact_bytes() -> None:
    adapter = PythonLanguageAdapter(ROOT)
    oracle = _json("expected_ir.json")
    results = {
        path: adapter.normalize(_artifact(path))
        for path, spec in oracle["files"].items()  # type: ignore[union-attr]
        if spec["expected_state"] == "indexed"
    }
    assert all(isinstance(result, FileIR) for result in results.values())

    expected = oracle["expected_facts"]  # type: ignore[assignment]
    for key, fact in expected.items():  # type: ignore[union-attr]
        if oracle["files"][fact["path"]]["expected_state"] != "indexed":
            continue
        if fact["kind"] == "symbol":
            symbol = next(
                item
                for item in results[fact["path"]].symbols
                if item.qualified_name == fact["subject"]
            )
            span = symbol.definition
        else:
            relation = _relation_for_fact(results[fact["path"]], fact)
            assert relation.kind == fact["kind"]
            assert relation.resolution_status.value == fact["resolution_status"]
            assert relation.resolution_method.value == fact["resolution_method"]
            if fact["target"] is None:
                assert relation.target is None
            else:
                assert relation.target is not None
                assert relation.target.id == _expected_reference_id(
                    results[fact["path"]].source_unit, fact["target"]
                )
            assert tuple(candidate.id for candidate in relation.candidates) == tuple(
                _expected_reference_id(results[fact["path"]].source_unit, candidate)
                for candidate in fact["candidates"]
            )
            assert relation.id == deterministic_entity_id(
                relation.source_revision_id,
                relation.path,
                EntityKind.RELATION,
                relation.locator,
            )
            assert ":occurrence:" not in relation.locator
            span = relation.evidence[0]
        assert span.start_line == fact["span"]["line"]
        assert span.start_column == fact["span"]["column"]
        offset, length, text = _span_bytes(fact["path"], span)
        assert (offset, length, text) == (
            fact["span"]["byte_offset"],
            fact["span"]["byte_length"],
            fact["span"]["text"],
        ), key

    native = expected["py.unsupported.native"]
    native_raw = _source(native["path"]).encode("utf-8")
    native_span = native["span"]
    assert native_raw[
        native_span["byte_offset"] : native_span["byte_offset"] + native_span["byte_length"]
    ].decode("utf-8") == native_span["text"]


def test_same_qualified_names_get_distinct_deterministic_ids_and_order() -> None:
    adapter = PythonLanguageAdapter(ROOT)
    first = [adapter.normalize(_artifact(path)) for path in ("pkg/base.py", "pkg/impl.py", "pkg/api.py")]
    second = [adapter.normalize(_artifact(path)) for path in ("pkg/api.py", "pkg/base.py", "pkg/impl.py")]
    first_symbols = {symbol.qualified_name: symbol.id for item in first for symbol in item.symbols}
    second_symbols = {symbol.qualified_name: symbol.id for item in second for symbol in item.symbols}
    same_ids = {first_symbols[name] for name in ("pkg.base.same", "pkg.impl.same", "pkg.api.same")}
    assert len(same_ids) == 3
    assert first_symbols == second_symbols
    for result in first + second:
        assert result.symbols == tuple(sorted(result.symbols, key=lambda item: item.id))
        assert result.relations == tuple(sorted(result.relations, key=lambda item: item.id))


def test_absent_targets_remain_null_and_unresolved_candidates_remain_empty() -> None:
    adapter = PythonLanguageAdapter(ROOT)
    results = [adapter.normalize(_artifact(path)) for path in ("pkg/api.py", "pkg/dynamic.py")]
    assert all(isinstance(result, FileIR) for result in results)
    relations = [relation for result in results for relation in result.relations]  # type: ignore[union-attr]
    absent = [relation for relation in relations if relation.target is None]
    assert absent
    assert all(
        relation.resolution_status
        in {ResolutionStatus.UNRESOLVED, ResolutionStatus.AMBIGUOUS, ResolutionStatus.UNSUPPORTED}
        for relation in absent
    )
    unresolved = [
        relation
        for relation in relations
        if relation.resolution_status is ResolutionStatus.UNRESOLVED
    ]
    assert unresolved
    assert all(relation.target is None and relation.candidates == () for relation in unresolved)


def test_duplicate_call_occurrences_have_distinct_deterministic_locators_and_ids(tmp_path: Path) -> None:
    source = "def f():\n    return 1\ndef g():\n    return f() + f()\n"
    first = _inline_result(tmp_path, source)
    second = _inline_result(tmp_path, source)
    calls = [relation for relation in first.relations if relation.kind == "call"]
    assert len(calls) == 2
    assert len({relation.locator for relation in calls}) == 2
    assert len({relation.id for relation in calls}) == 2
    assert first == second


def test_multiline_call_evidence_contains_the_claimed_callee(tmp_path: Path) -> None:
    source = "def f():\n    return 1\ndef g():\n    return (\n        f()\n    )\n"
    result = _inline_result(tmp_path, source)
    call = next(relation for relation in result.relations if relation.kind == "call")
    witness = _span_text(tmp_path, call.evidence[0])
    assert "f(" in witness


def test_nested_functions_remain_functions_while_class_members_are_methods(tmp_path: Path) -> None:
    source = (
        "def outer():\n"
        "    def inner():\n"
        "        return 1\n"
        "    return inner()\n"
        "class Box:\n"
        "    def member(self):\n"
        "        return 2\n"
    )
    result = _inline_result(tmp_path, source)
    kinds = {symbol.qualified_name: symbol.kind for symbol in result.symbols}
    assert kinds == {
        "probe.outer": "function",
        "probe.outer.inner": "function",
        "probe.Box": "class",
        "probe.Box.member": "method",
    }


def test_probe_compatible_lexical_identity_and_full_ast_span_are_additive(
    tmp_path: Path,
) -> None:
    source = (
        "if True:\n"
        "    def guarded():\n"
        "        def nested():\n"
        "            return 1\n"
        "        return nested()\n"
        "class Box:\n"
        "    if True:\n"
        "        async def member(self):\n"
        "            return 2\n"
    )
    result = _inline_result(tmp_path, source, path="pkg/probe.py")
    by_lexical = {
        symbol.language_attributes["lexical_qualified_name"]: symbol
        for symbol in result.symbols
    }
    assert set(by_lexical) == {"guarded", "guarded.nested", "Box", "Box.member"}
    assert by_lexical["guarded"].qualified_name == "pkg.probe.guarded"
    assert by_lexical["guarded.nested"].kind == "function"  # legacy IR remains compatible
    assert by_lexical["guarded.nested"].language_attributes["lexical_kind"] == "method"
    assert by_lexical["Box.member"].kind == "method"
    assert by_lexical["Box.member"].language_attributes["async"] is True
    assert by_lexical["guarded"].language_attributes["definition_start_line"] == 2
    assert by_lexical["guarded"].language_attributes["definition_end_line"] == 5
    # The legacy evidence span remains the declaration line; the additive
    # attributes carry the complete AST range consumed by semantic inventory.
    assert by_lexical["guarded"].definition.start_line == 2
    assert by_lexical["guarded"].definition.end_line == 2


def test_semantic_definition_start_line_includes_first_decorator(tmp_path: Path) -> None:
    source = "@property\ndef value():\n    return 1\n"
    result = _inline_result(tmp_path, source)
    symbol = next(item for item in result.symbols if item.qualified_name == "probe.value")

    assert symbol.language_attributes["definition_start_line"] == 1
    assert symbol.language_attributes["definition_end_line"] == 3
    # The legacy IR declaration-line evidence remains unchanged.
    assert symbol.definition.start_line == 2


def test_active_python_adapter_documentation_advertises_cbe_ir_v2() -> None:
    assert "cbe-ir/2" in (python_adapter_module.__doc__ or "")
    assert "cbe-ir/1" not in (python_adapter_module.__doc__ or "")


def test_dynamic_and_unsupported_constructs_are_never_promoted() -> None:
    result = PythonLanguageAdapter(ROOT).normalize(_artifact("pkg/dynamic.py"))
    assert isinstance(result, FileIR)
    expected = _json("expected_ir.json")["expected_facts"]  # type: ignore[index]
    wildcard = _relation_for_fact(result, expected["py.import.wildcard"])
    dynamic_import = _relation_for_fact(result, expected["py.import.dynamic"])
    dynamic_export = _relation_for_fact(result, expected["py.export.dynamic"])
    unsupported_exec = _relation_for_fact(result, expected["py.unsupported.exec"])
    assert wildcard.resolution_status is ResolutionStatus.AMBIGUOUS
    assert dynamic_import.resolution_status is ResolutionStatus.UNSUPPORTED
    assert dynamic_export.resolution_status is ResolutionStatus.AMBIGUOUS
    assert unsupported_exec.resolution_status is ResolutionStatus.UNSUPPORTED
    assert all(
        relation.resolution_method is ResolutionMethod.HEURISTIC
        for relation in (wildcard, dynamic_import, dynamic_export, unsupported_exec)
    )


def test_replace_call_mutation_removes_old_edge_and_shifts_later_span() -> None:
    mutation = _json("mutations.json")["mutations"]["py.replace_call"]  # type: ignore[index]
    source = _source(mutation["path"])
    mutated = source.replace(mutation["old_text"], mutation["new_text"])
    result = PythonLanguageAdapter(ROOT, source_overrides={mutation["path"]: mutated}).normalize(
        _artifact(mutation["path"], mutated)
    )
    assert isinstance(result, FileIR)
    removed = mutation["removed_facts"]["py.call.impl_same"]
    created = mutation["created_facts"]["py.call.local_same"]
    assert not [
        relation for relation in result.relations
        if relation.kind == "call"
        and relation.evidence[0].start_line == removed["span"]["line"]
        and relation.target.id == _expected_reference_id(result.source_unit, removed["target"])
    ]
    assert _relation_for_fact(result, created)
    dynamic = _relation_for_fact(result, mutation["unchanged_facts"]["py.call.dynamic"])
    raw = mutated.encode("utf-8")
    lines = raw.splitlines(keepends=True)
    offset = sum(len(line) for line in lines[: dynamic.evidence[0].start_line - 1])
    assert offset == mutation["unchanged_facts"]["py.call.dynamic"]["span"]["byte_offset"]


def test_corrupt_span_control_is_rejected_by_external_byte_replay() -> None:
    mutation = _json("mutations.json")["mutations"]["py.corrupt_span"]  # type: ignore[index]
    corrupted = mutation["created_facts"]["py.call.missing.corrupted"]["span"]
    raw = _source(mutation["path"]).encode("utf-8")
    witness = raw[corrupted["byte_offset"] : corrupted["byte_offset"] + corrupted["byte_length"]]
    assert witness.decode("utf-8") != corrupted["text"]
    result = PythonLanguageAdapter(ROOT).normalize(_artifact(mutation["path"]))
    valid = _relation_for_fact(result, mutation["removed_facts"]["py.call.missing"])
    assert _span_bytes(mutation["path"], valid.evidence[0]) == (
        mutation["removed_facts"]["py.call.missing"]["span"]["byte_offset"],
        mutation["removed_facts"]["py.call.missing"]["span"]["byte_length"],
        mutation["removed_facts"]["py.call.missing"]["span"]["text"],
    )


def test_backend_removal_and_invalid_artifacts_are_typed_terminal_failures(tmp_path) -> None:
    registry = BackendRegistry()
    assert registry.select("python", root=ROOT) is None
    wrong_language = PythonLanguageAdapter(ROOT).normalize(
        SyntaxArtifact(
            source_unit=_unit("pkg/api.py", language="typescript"),
            backend_id="test",
            backend_version="1",
            language="typescript",
            syntax_tree=ast.parse("value = 1"),
        )
    )
    invalid_tree = PythonLanguageAdapter(ROOT).normalize(
        SyntaxArtifact(
            source_unit=_unit("pkg/api.py"),
            backend_id="test",
            backend_version="1",
            language="python",
            syntax_tree=object(),
        )
    )
    assert isinstance(wrong_language, TypedFailure)
    assert wrong_language.code is FailureCode.UNSUPPORTED_LANGUAGE
    assert isinstance(invalid_tree, TypedFailure)
    assert invalid_tree.code is FailureCode.INVALID_INPUT

    non_utf = tmp_path / "non_utf.py"
    non_utf.write_bytes(b"value = \xff\n")
    unit = SourceUnit(
        id=deterministic_entity_id(REVISION, "non_utf.py", EntityKind.SOURCE_UNIT, "non_utf.py"),
        source_revision_id=REVISION,
        path="non_utf.py",
        language="python",
        content_hash=hashlib.sha256(non_utf.read_bytes()).hexdigest(),
        state=SourceUnitState.DISCOVERED,
        backend_id="python_ast",
        backend_version="test",
    )
    assert PythonAstBackend(root=tmp_path).parse(unit).code is FailureCode.SOURCE_UNAVAILABLE  # type: ignore[union-attr]


def test_registry_selected_backend_artifact_is_consumed_by_adapter() -> None:
    registry = BackendRegistry()
    registry.register("python_ast", lambda root: PythonAstBackend(root=root))
    backend = registry.select("python", root=ROOT)
    assert backend is not None
    artifact = backend.parse(_unit("pkg/api.py"))
    assert isinstance(artifact, SyntaxArtifact)
    result = PythonLanguageAdapter(ROOT).normalize(artifact)
    assert isinstance(result, FileIR)
    assert result.source_unit.path == "pkg/api.py"


def test_syntax_error_is_a_backend_failure_not_empty_file_ir() -> None:
    result = PythonAstBackend(root=ROOT).parse(_unit("pkg/broken.py"))
    assert isinstance(result, TypedFailure)
    assert result.code is FailureCode.PARSE_ERROR


def test_frozen_negative_facts_remain_observably_false() -> None:
    oracle = _json("expected_ir.json")
    assert len(oracle["forbidden_facts"]) == 6  # type: ignore[arg-type]
    adapter = PythonLanguageAdapter(ROOT)
    api = adapter.normalize(_artifact("pkg/api.py"))
    assert isinstance(api, FileIR)
    expected = oracle["expected_facts"]  # type: ignore[assignment]
    dynamic = _relation_for_fact(api, expected["py.call.dynamic"])
    missing = _relation_for_fact(api, expected["py.call.missing"])
    builtin = _relation_for_fact(api, expected["py.call.print"])
    assert dynamic.resolution_status is ResolutionStatus.AMBIGUOUS
    assert missing.resolution_status is ResolutionStatus.UNRESOLVED
    assert builtin.resolution_status is ResolutionStatus.EXTERNAL

    eligible = {
        path.relative_to(ROOT).as_posix()
        for path in CodebaseParser()._eligible_source_paths(ROOT, "python")
    }
    assert "pkg/broken.py" in eligible
    # P2 currently discovers these paths; P5 owns their excluded terminal state.
    assert {"vendor/ignored.py", "generated/output.py"} <= eligible
    assert oracle["files"]["vendor/ignored.py"]["expected_state"] == "excluded"
    assert oracle["files"]["generated/output.py"]["expected_state"] == "excluded"
    assert "pkg/native.pyx" not in eligible


def test_capability_axes_match_frozen_oracle_without_verification_promotion() -> None:
    expected = _json("expected_capabilities.json")["cells"]  # type: ignore[index]
    cells = PythonLanguageAdapter(ROOT).capability_cells(
        backend_id="python_ast",
        backend_version="test",
        toolchain_conditions=("stdlib ast",),
        evidence_receipt_id="p3-producer-unverified",
    )
    assert {cell.capability for cell in cells} == set(expected)
    for cell in cells:
        oracle = expected[cell.capability]
        assert cell.availability.value == oracle["availability"]
        assert cell.semantic_tier.value == oracle["semantic_tier"]
        assert cell.verification_status.value == oracle["verification_status"]
    assert next(cell for cell in cells if cell.capability == "calls").semantic_tier is SemanticTier.HEURISTIC
    assert all(cell.verification_status is not VerificationStatus.VERIFIED for cell in cells)
    assert next(cell for cell in cells if cell.capability == "syntax").availability is Availability.AVAILABLE


def test_file_ir_models_round_trip_through_canonical_envelopes() -> None:
    result = PythonLanguageAdapter(ROOT).normalize(_artifact("pkg/api.py"))
    assert isinstance(result, FileIR)
    models = (result.source_unit, *result.symbols, *result.relations)
    for model in models:
        assert deserialize_model(serialize_model(model), type(model)) == model


@pytest.mark.parametrize("path", ["pkg/base.py", "pkg/impl.py", "pkg/api.py", "pkg/dynamic.py", "pkg/über.py"])
def test_normalization_is_repeatable(path: str) -> None:
    adapter = PythonLanguageAdapter(ROOT)
    assert adapter.normalize(_artifact(path)) == adapter.normalize(_artifact(path))
