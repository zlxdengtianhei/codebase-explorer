"""Frozen-oracle tests for the Python canonical-IR adapter."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import src.parser.adapters.python as python_adapter_module

from src.ir import (
    Availability,
    CallOutcome,
    EntityKind,
    ProvenanceBasis,
    ReceiverGapReason,
    ReceiverShape,
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
INBOUND_ROOT = Path(__file__).parent / "fixtures" / "inbound_protocol"
INBOUND_ORACLE = json.loads((INBOUND_ROOT / "oracle.json").read_text(encoding="utf-8"))
INBOUND_REVISION = str(INBOUND_ORACLE["source_revision_id"])


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


def _inbound_result(path: str) -> FileIR:
    source = (INBOUND_ROOT / path).read_text(encoding="utf-8")
    backend = PythonAstBackend(root=INBOUND_ROOT)
    unit = SourceUnit(
        id=deterministic_entity_id(
            INBOUND_REVISION, path, EntityKind.SOURCE_UNIT, path
        ),
        source_revision_id=INBOUND_REVISION,
        path=path,
        language="python",
        content_hash=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        state=SourceUnitState.DISCOVERED,
        backend_id=backend.backend_id,
        backend_version=backend.backend_version,
    )
    artifact = backend.parse(unit)
    assert isinstance(artifact, SyntaxArtifact)
    result = PythonLanguageAdapter(INBOUND_ROOT).normalize(artifact)
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
            if fact["kind"] == "call" or fact.get("attributes", {}).get("dynamic"):
                # Python calls are target-independent in cbe-ir/3; the
                # legacy oracle records v2 statement locators and target rows.
                continue
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
    absent = [relation for relation in relations if relation.target is None and relation.kind == "call"]
    assert absent
    typed_calls = [relation for relation in relations if relation.kind == "call"]
    assert typed_calls
    assert all(relation.call_resolution is not None for relation in typed_calls)
    assert all(relation.target is None and relation.candidates == () for relation in typed_calls)
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


def test_decorator_carrier_normalizes_callable_heads_and_preserves_gap_identity(
    tmp_path: Path,
) -> None:
    source = (
        "from typing import final as sealed\n"
        "import typing as t\n"
        "\n"
        "def wrapper(fn):\n"
        "    return fn\n"
        "\n"
        "def factory(label):\n"
        "    def decorate(fn):\n"
        "        return fn\n"
        "    return decorate\n"
        "\n"
        "@staticmethod\n"
        "def static_fn():\n"
        "    return 1\n"
        "\n"
        "@classmethod\n"
        "def class_fn(cls):\n"
        "    return 2\n"
        "\n"
        "@sealed\n"
        "def direct_final():\n"
        "    return 3\n"
        "\n"
        "@sealed()\n"
        "def call_final():\n"
        "    return 4\n"
        "\n"
        "@t.final\n"
        "def module_final():\n"
        "    return 5\n"
        "\n"
        "@wrapper\n"
        "def wrapped():\n"
        "    return 6\n"
        "\n"
        "@factory('x')\n"
        "def factory_wrapped():\n"
        "    return 7\n"
        "\n"
        "@wrapper\n"
        "@staticmethod\n"
        "def layered():\n"
        "    return 8\n"
        "\n"
        "def caller():\n"
        "    return direct_final(), call_final(), wrapped(), factory_wrapped()\n"
    )
    result = _inline_result(tmp_path, source)
    symbols = {item.local_name: item for item in result.symbols}

    assert symbols["static_fn"].decorators == ("staticmethod",)
    assert symbols["class_fn"].decorators == ("classmethod",)
    assert symbols["direct_final"].decorators == ("typing.final",)
    assert symbols["call_final"].decorators == ("typing.final",)
    assert symbols["module_final"].decorators == ("typing.final",)
    assert symbols["wrapped"].decorators == ("wrapper",)
    assert symbols["factory_wrapped"].decorators == ("factory",)
    assert symbols["layered"].decorators == ("staticmethod", "wrapper")

    caller_calls = sorted(
        (
            relation
            for relation in result.relations
            if relation.kind == "call" and relation.evidence[0].start_line == 46
        ),
        key=lambda relation: relation.evidence[0].start_column,
    )
    assert len(caller_calls) == 4
    assert [
        relation.call_resolution.outcome for relation in caller_calls[:2]
    ] == [CallOutcome.RUNTIME_EXACT, CallOutcome.RUNTIME_EXACT]
    assert all(
        relation.call_resolution.unresolved_or_deep_receiver.reason
        is ReceiverGapReason.DECORATED_CALLABLE
        for relation in caller_calls[2:]
    )


def test_decorator_carrier_rejects_non_name_callable_head_without_ast_dump_identity(
    tmp_path: Path,
) -> None:
    source = (
        "def factory():\n"
        "    return lambda fn: fn\n"
        "\n"
        "@factory()[\"key\"]\n"
        "def decorated():\n"
        "    return 1\n"
    )

    with pytest.raises(ValidationError, match="decorators"):
        _inline_result(tmp_path, source)


def test_active_python_adapter_documentation_advertises_cbe_ir_v3() -> None:
    assert "cbe-ir/3" in (python_adapter_module.__doc__ or "")
    assert "cbe-ir/1" not in (python_adapter_module.__doc__ or "")


def test_dynamic_and_unsupported_constructs_are_never_promoted() -> None:
    result = PythonLanguageAdapter(ROOT).normalize(_artifact("pkg/dynamic.py"))
    assert isinstance(result, FileIR)
    expected = _json("expected_ir.json")["expected_facts"]  # type: ignore[index]
    wildcard = _relation_for_fact(result, expected["py.import.wildcard"])
    dynamic_import = next(
        relation
        for relation in result.relations
        if relation.kind == "call"
        and relation.evidence[0].start_line == expected["py.import.dynamic"]["span"]["line"]
    )
    dynamic_export = _relation_for_fact(result, expected["py.export.dynamic"])
    unsupported_exec = next(
        relation
        for relation in result.relations
        if relation.kind == "call"
        and relation.evidence[0].start_line == expected["py.unsupported.exec"]["span"]["line"]
    )
    assert wildcard.resolution_status is ResolutionStatus.AMBIGUOUS
    assert dynamic_import.resolution_status is ResolutionStatus.UNRESOLVED
    assert dynamic_export.resolution_status is ResolutionStatus.AMBIGUOUS
    assert unsupported_exec.resolution_status is ResolutionStatus.UNRESOLVED
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
    removed_calls = [
        relation for relation in result.relations
        if relation.kind == "call"
        and relation.evidence[0].start_line == removed["span"]["line"]
    ]
    assert removed_calls
    assert all(
        relation.call_resolution is None
        or relation.call_resolution.runtime_exact_target is None
        or relation.call_resolution.runtime_exact_target.target.path != removed["target"].rsplit(".", 2)[0].replace(".", "/") + ".py"
        for relation in removed_calls
    )
    created_calls = [
        relation for relation in result.relations
        if relation.kind == "call"
        and relation.evidence[0].start_line == created["span"]["line"]
    ]
    assert created_calls
    dynamic = next(
        relation
        for relation in result.relations
        if relation.kind == "call"
        and relation.evidence[0].start_line
        == mutation["unchanged_facts"]["py.call.dynamic"]["span"]["line"]
    )
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
    valid = next(
        relation
        for relation in result.relations
        if relation.kind == "call"
        and relation.evidence[0].start_line
        == mutation["removed_facts"]["py.call.missing"]["span"]["line"]
    )
    assert "missing" in _span_text(ROOT, valid.evidence[0])


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
    dynamic = next(
        relation
        for relation in api.relations
        if relation.kind == "call"
        and relation.evidence[0].start_line == expected["py.call.dynamic"]["span"]["line"]
    )
    missing = next(
        relation
        for relation in api.relations
        if relation.kind == "call"
        and relation.evidence[0].start_line == expected["py.call.missing"]["span"]["line"]
    )
    builtin = next(
        relation
        for relation in api.relations
        if relation.kind == "call"
        and relation.evidence[0].start_line == expected["py.call.print"]["span"]["line"]
    )
    assert dynamic.resolution_status is ResolutionStatus.UNRESOLVED
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
    assert result.call_site_inventory is not None
    models = (result.source_unit, *result.symbols, *result.relations, result.call_site_inventory)
    for model in models:
        assert deserialize_model(serialize_model(model), type(model)) == model


def test_call_inventory_and_relation_ids_have_golden_module_and_nested_callers(
    tmp_path: Path,
) -> None:
    source = (
        "def leaf():\n"
        "    return 1\n"
        "\n"
        "leaf()\n"
        "\n"
        "def outer():\n"
        "    return leaf()\n"
    )
    result = _inline_result(tmp_path, source)
    assert result.call_site_inventory is not None
    inventory = result.call_site_inventory
    call_relations = [relation for relation in result.relations if relation.kind == "call"]
    assert len(inventory.call_sites) == 2
    assert len(call_relations) == 2
    assert {
        anchor.caller_canonical_id for anchor in inventory.call_sites
    } == {"probe.py::<module>", "probe.py::outer"}
    relation_by_id = {relation.id: relation for relation in call_relations}
    assert set(relation_by_id) == {
        anchor.call_site_id for anchor in inventory.call_sites
    }
    for anchor in inventory.call_sites:
        expected_locator = (
            f"python:call:{anchor.span.start_line}:{anchor.span.start_column}:"
            f"{anchor.span.end_line}:{anchor.span.end_column}:"
            f"{anchor.caller_canonical_id}"
        )
        relation = relation_by_id[anchor.call_site_id]
        assert relation.locator == expected_locator
        assert relation.id == deterministic_entity_id(
            REVISION, "probe.py", EntityKind.RELATION, expected_locator
        )
    module_anchor = next(
        anchor
        for anchor in inventory.call_sites
        if anchor.caller_canonical_id.endswith("::<module>")
    )
    assert module_anchor.span.start_line == 4


def test_nested_call_inventory_caller_namespace_is_target_independent(
    tmp_path: Path,
) -> None:
    source = (
        "def leaf():\n"
        "    return 1\n"
        "\n"
        "def outer():\n"
        "    def inner():\n"
        "        return leaf()\n"
        "    return inner()\n"
    )
    result = _inline_result(tmp_path, source)
    assert result.call_site_inventory is not None
    assert [
        anchor.caller_canonical_id for anchor in result.call_site_inventory.call_sites
    ] == ["probe.py::outer.inner", "probe.py::outer"]
    assert all(
        relation.locator.endswith(
            ("probe.py::outer.inner" if relation.evidence[0].start_line == 6 else "probe.py::outer")
        )
        for relation in result.relations
        if relation.kind == "call"
    )


def test_simple_forward_annotation_resolves_without_runtime_evaluation(
    tmp_path: Path,
) -> None:
    source = (
        "class Base:\n"
        "    def save(self):\n"
        "        return 1\n"
        "\n"
        "def use(value: 'Base'):\n"
        "    return value.save()\n"
    )
    result = _inline_result(tmp_path, source)
    call = next(relation for relation in result.relations if relation.kind == "call")
    assert call.call_resolution.outcome is CallOutcome.VIRTUAL_DISPATCH
    assert call.call_resolution.receiver_shape is ReceiverShape.ANNOTATED_NAME


def test_local_binding_shadowing_nested_identity_and_quoted_optional_forms(
    tmp_path: Path,
) -> None:
    source = (
        "def helper():\n"
        "    return 1\n"
        "\n"
        "class Base:\n"
        "    def save(self):\n"
        "        return 1\n"
        "\n"
        "class Child(Base):\n"
        "    def save(self):\n"
        "        return 2\n"
        "\n"
        "def outer():\n"
        "    def inner():\n"
        "        return 3\n"
        "    return inner()\n"
        "\n"
        "def shadow(helper):\n"
        "    return helper()\n"
        "\n"
        "def closure():\n"
        "    helper = lambda: 4\n"
        "    def nested():\n"
        "        return helper()\n"
        "    return nested()\n"
        "\n"
        "def use(value: \"Base | None\", other: \"Optional[Base]\"):\n"
        "    value.save()\n"
        "    other.save()\n"
    )
    result = _inline_result(tmp_path, source)
    calls = [relation for relation in result.relations if relation.kind == "call"]

    def caller_call(caller: str, line: int):
        matches = [
            relation
            for relation in calls
            if relation.locator.endswith(f"probe.py::{caller}")
            and relation.evidence[0].start_line == line
        ]
        assert len(matches) == 1, (caller, line, matches)
        return matches[0]

    nested = caller_call("outer", 15)
    assert nested.call_resolution.outcome is CallOutcome.RUNTIME_EXACT
    assert nested.call_resolution.runtime_exact_target is not None
    assert "python:function:probe.outer.inner:13:4" in (
        nested.call_resolution.runtime_exact_target.target.definition_locator
    )

    shadowed = caller_call("shadow", 18)
    assert shadowed.call_resolution.outcome is CallOutcome.UNRESOLVED_OR_DEEP
    assert (
        shadowed.call_resolution.unresolved_or_deep_receiver.reason
        is ReceiverGapReason.UNKNOWN_NAME
    )

    closure_call = caller_call("closure.nested", 23)
    assert closure_call.call_resolution.outcome is CallOutcome.UNRESOLVED_OR_DEEP
    assert (
        closure_call.call_resolution.unresolved_or_deep_receiver.reason
        is ReceiverGapReason.UNKNOWN_NAME
    )

    optional_calls = [
        relation
        for relation in calls
        if relation.evidence[0].start_line in {27, 28}
    ]
    assert len(optional_calls) == 2
    for relation in optional_calls:
        resolution = relation.call_resolution
        assert resolution.outcome is CallOutcome.VIRTUAL_DISPATCH
        assert resolution.lexical_base_target is not None
        assert resolution.lexical_base_target.target.definition_locator.endswith(
            "python:method:probe.Base.save:5:4"
        )
        assert any(
            candidate.target.definition_locator.endswith("python:method:probe.Child.save:9:4")
            for candidate in resolution.override_candidates
        )
        assert all(
            "Audit" not in candidate.target.definition_locator
            for candidate in resolution.override_candidates
        )


def test_python_call_outcomes_cover_deep_receivers_and_keep_unrelated_names_non_exact(
    tmp_path: Path,
) -> None:
    source = (
        "from typing import final as is_final\n"
        "\n"
        "class Base:\n"
        "    def save(self):\n"
        "        return 1\n"
        "    def run(self):\n"
        "        return self.save()\n"
        "\n"
        "class Child(Base):\n"
        "    def save(self):\n"
        "        return 2\n"
        "    def run(self):\n"
        "        return self.save()\n"
        "\n"
        "class Audit:\n"
        "    def save(self):\n"
        "        return 3\n"
        "\n"
        "@is_final\n"
        "class Final:\n"
        "    def save(self):\n"
        "        return 4\n"
        "    def run(self):\n"
        "        return self.save()\n"
        "\n"
        "class Unknown(MissingBase):\n"
        "    def save(self):\n"
        "        return 5\n"
        "\n"
        "def factory():\n"
        "    return Base()\n"
        "\n"
        "def wrapper(fn):\n"
        "    return fn\n"
        "\n"
        "@wrapper\n"
        "def wrapped():\n"
        "    return 6\n"
        "\n"
        "def use(backend: Base, optional: Base | None, union: Base | Audit, items):\n"
        "    backend.save()\n"
        "    optional.save()\n"
        "    union.save()\n"
        "    backend.missing()\n"
        "    backend.child.save()\n"
        "    factory().save()\n"
        "    items[0].save()\n"
        "    getattr(backend, 'save')()\n"
        "    exec('pass')\n"
        "    wrapped()\n"
        "    len(items)\n"
        "\n"
        "Unknown().save()\n"
        "\n"
        "def use_unknown(value: Unknown):\n"
        "    return value.save()\n"
    )
    result = _inline_result(tmp_path, source)
    assert result.call_site_inventory is not None
    calls = [relation for relation in result.relations if relation.kind == "call"]
    assert len(calls) == len(
        [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)]
    )
    assert len(calls) == len(result.call_site_inventory.call_sites)
    assert {relation.call_resolution.outcome for relation in calls} == {
        CallOutcome.RUNTIME_EXACT,
        CallOutcome.VIRTUAL_DISPATCH,
        CallOutcome.EXTERNAL,
        CallOutcome.UNRESOLVED_OR_DEEP,
    }

    def call_at(
        line: int,
        *,
        reason: ReceiverGapReason | None = None,
        receiver_text: str | None = None,
    ):
        matches = [
            relation
            for relation in calls
            if relation.evidence[0].start_line == line
            and (
                reason is None
                or (
                    relation.call_resolution.unresolved_or_deep_receiver is not None
                    and relation.call_resolution.unresolved_or_deep_receiver.reason is reason
                )
            )
            and (
                receiver_text is None
                or (
                    relation.call_resolution.unresolved_or_deep_receiver is not None
                    and relation.call_resolution.unresolved_or_deep_receiver.receiver_text
                    == receiver_text
                )
            )
        ]
        assert len(matches) == 1, (line, reason, matches)
        return matches[0]

    base_virtual = call_at(41)
    assert base_virtual.call_resolution.outcome is CallOutcome.VIRTUAL_DISPATCH
    assert base_virtual.call_resolution.lexical_base_target is not None
    assert base_virtual.call_resolution.lexical_base_target.target.path == "probe.py"
    assert base_virtual.call_resolution.lexical_base_target.provenance[0].basis is ProvenanceBasis.RECEIVER_ANNOTATION
    assert any(
        "Child.save" in candidate.target.definition_locator
        for candidate in base_virtual.call_resolution.override_candidates
    )
    assert all(
        "Audit" not in candidate.target.definition_locator
        for candidate in base_virtual.call_resolution.override_candidates
    )
    optional_virtual = call_at(42)
    assert optional_virtual.call_resolution.outcome is CallOutcome.VIRTUAL_DISPATCH
    assert optional_virtual.call_resolution.receiver_shape is ReceiverShape.ANNOTATED_NAME
    assert call_at(43).call_resolution.unresolved_or_deep_receiver.reason is ReceiverGapReason.UNSUPPORTED_UNION_RECEIVER
    assert call_at(44).call_resolution.unresolved_or_deep_receiver.reason is ReceiverGapReason.MISSING_LEXICAL_MEMBER
    assert call_at(45).call_resolution.unresolved_or_deep_receiver.reason is ReceiverGapReason.ATTRIBUTE_CHAIN
    assert call_at(46, reason=ReceiverGapReason.FACTORY_RESULT).call_resolution.receiver_shape is ReceiverShape.CALL_RESULT
    assert call_at(47).call_resolution.unresolved_or_deep_receiver.reason is ReceiverGapReason.SUBSCRIPT_RECEIVER
    assert call_at(48, reason=ReceiverGapReason.DYNAMIC_ATTRIBUTE, receiver_text="getattr(backend, 'save')").call_resolution.receiver_shape is ReceiverShape.DYNAMIC_ATTRIBUTE
    assert call_at(49).call_resolution.unresolved_or_deep_receiver.reason is ReceiverGapReason.EXEC
    assert call_at(50).call_resolution.unresolved_or_deep_receiver.reason is ReceiverGapReason.DECORATED_CALLABLE
    assert call_at(7).call_resolution.outcome is CallOutcome.VIRTUAL_DISPATCH
    assert call_at(51).call_resolution.outcome is CallOutcome.EXTERNAL
    final_call = call_at(24)
    assert final_call.call_resolution.outcome is CallOutcome.RUNTIME_EXACT
    assert final_call.call_resolution.runtime_exact_target is not None
    assert final_call.call_resolution.runtime_exact_target.provenance[0].basis is ProvenanceBasis.FINAL_CLASS_OR_METHOD
    unknown_call = call_at(56)
    assert unknown_call.call_resolution.unresolved_or_deep_receiver.reason is ReceiverGapReason.AMBIGUOUS_MRO


@pytest.mark.parametrize("path", ["pkg/base.py", "pkg/impl.py", "pkg/api.py", "pkg/dynamic.py", "pkg/über.py"])
def test_normalization_is_repeatable(path: str) -> None:
    adapter = PythonLanguageAdapter(ROOT)
    assert adapter.normalize(_artifact(path)) == adapter.normalize(_artifact(path))


def test_decorator_factory_call_uses_enclosing_scope_caller_and_locator() -> None:
    result = _inbound_result("base.py")
    relation = next(
        item
        for item in result.relations
        if item.kind == "call"
        and item.evidence[0].start_line == 143
        and item.evidence[0].start_column == 1
    )

    assert relation.locator == (
        "python:call:143:1:143:30:base.py::<module>"
    )
    assert relation.id == (
        "ir_59e11dc41577d1cd82fccbd2371eb158ceb6ff4a8e4b16bd1e2af12c86f6e981"
    )


def test_imported_class_attribute_calls_resolve_identity_preserving_members_exactly() -> None:
    result = _inbound_result("calls.py")
    calls = {
        relation.evidence[0].start_line: relation
        for relation in result.relations
        if relation.kind == "call"
        and relation.evidence[0].start_line in {104, 108}
    }

    assert set(calls) == {104, 108}
    assert all(
        relation.call_resolution.outcome is CallOutcome.RUNTIME_EXACT
        and relation.call_resolution.receiver_shape is ReceiverShape.MODULE_ATTRIBUTE
        for relation in calls.values()
    )
    assert calls[104].call_resolution.runtime_exact_target.target.ref.id == (
        "ir_9f0bcacbfaad82409ecbf79e427a2fd8013448bc8ec5e8e2c6942719f8b637ca"
    )
    assert calls[108].call_resolution.runtime_exact_target.target.ref.id == (
        "ir_33eb984e49e2ee41374d31f41a39a94f4e5d76d5b97f8f88535ab691300411ae"
    )


def test_imported_qualified_annotation_resolves_virtual_base_and_overrides() -> None:
    result = _inbound_result("calls.py")
    relation = next(
        item
        for item in result.relations
        if item.kind == "call" and item.evidence[0].start_line == 48
    )
    resolution = relation.call_resolution

    assert resolution.outcome is CallOutcome.VIRTUAL_DISPATCH
    assert resolution.receiver_shape is ReceiverShape.ANNOTATED_NAME
    assert resolution.lexical_base_target.target.ref.id == (
        "ir_7bd6ffc99115ef545ca542476d7298a8102180b25c2f6bd3c65191ec11b31d14"
    )
    assert tuple(
        candidate.target.ref.id for candidate in resolution.override_candidates
    ) == (
        "ir_beb8c525bd76d2cced8db9b1cf6d94a2c927dd6004acb699f2bdb0006757254a",
    )


def test_nested_getattr_keeps_inner_builtin_external_and_outer_dynamic_gap() -> None:
    result = _inbound_result("calls.py")
    calls = {
        (relation.evidence[0].start_column, relation.evidence[0].end_column): relation
        for relation in result.relations
        if relation.kind == "call" and relation.evidence[0].start_line == 80
    }
    inner = calls[(11, 32)]
    outer = calls[(11, 34)]

    assert inner.call_resolution.outcome is CallOutcome.EXTERNAL
    assert inner.call_resolution.receiver_shape is ReceiverShape.BARE_NAME
    assert inner.call_resolution.external_target.external_id == (
        "ext_22a6192b71a0b3c3180ccc5ab21f8d626e2f774ee807880eb820432279801921"
    )
    assert outer.call_resolution.outcome is CallOutcome.UNRESOLVED_OR_DEEP
    assert outer.call_resolution.receiver_shape is ReceiverShape.DYNAMIC_ATTRIBUTE
    assert (
        outer.call_resolution.unresolved_or_deep_receiver.reason
        is ReceiverGapReason.DYNAMIC_ATTRIBUTE
    )


def test_builtin_external_identity_uses_frozen_bare_qualified_name() -> None:
    result = _inbound_result("calls.py")
    relation = next(
        item
        for item in result.relations
        if item.kind == "call" and item.evidence[0].start_line == 92
    )
    external = relation.call_resolution.external_target

    assert relation.call_resolution.outcome is CallOutcome.EXTERNAL
    assert external.ecosystem.value == "python_builtin"
    assert external.qualified_name == "len"
    assert external.distribution is None
    assert external.external_id == (
        "ext_0e3cf4e3a1175c6ad4ac9f716bad0126bb6f4f642a3be06aa9dd1243398d6c7c"
    )


def test_adapter_to_frozen_oracle_matches_all_45_call_sites_exactly() -> None:
    results = {
        path: _inbound_result(path)
        for path in ("base.py", "calls.py", "zero_calls.py")
    }
    expected_rows = {
        row["site_key"]: row for row in INBOUND_ORACLE["call_sites"]
    }
    actual_rows: dict[str, dict[str, object]] = {}

    for path, file_ir in results.items():
        assert file_ir.call_site_inventory is not None
        anchors = file_ir.call_site_inventory.call_sites
        relations = {
            relation.id: relation
            for relation in file_ir.relations
            if relation.kind == "call"
        }
        assert {anchor.call_site_id for anchor in anchors} == set(relations)
        for anchor in anchors:
            relation = relations[anchor.call_site_id]
            resolution = relation.call_resolution
            assert resolution is not None
            span = anchor.span
            assert relation.path == path
            assert relation.source_revision_id == INBOUND_REVISION
            assert span.path == path
            assert span.source_unit_id == file_ir.source_unit.id
            site_key = (
                f"{span.path}:{span.start_line}:{span.start_column}:"
                f"{span.end_line}:{span.end_column}"
            )
            actual_rows[site_key] = {
                "site_key": site_key,
                "path": relation.path,
                "span": {
                    "path": span.path,
                    "start_line": span.start_line,
                    "start_column": span.start_column,
                    "end_line": span.end_line,
                    "end_column": span.end_column,
                },
                "caller_id": anchor.caller_canonical_id,
                "receiver_shape": resolution.receiver_shape.value,
                "outcome": resolution.outcome.value,
                "runtime_exact_target_id": (
                    resolution.runtime_exact_target.target.ref.id
                    if resolution.runtime_exact_target is not None
                    else None
                ),
                "lexical_base_target_id": (
                    resolution.lexical_base_target.target.ref.id
                    if resolution.lexical_base_target is not None
                    else None
                ),
                "override_candidate_ids": [
                    candidate.target.ref.id
                    for candidate in resolution.override_candidates
                ],
                "external_identity": (
                    resolution.external_target.external_id
                    if resolution.external_target is not None
                    else None
                ),
                "gap_reason": (
                    resolution.unresolved_or_deep_receiver.reason.value
                    if resolution.unresolved_or_deep_receiver is not None
                    else None
                ),
            }

    assert len(actual_rows) == 45
    assert len(expected_rows) == 45
    assert set(actual_rows) == set(expected_rows)
    assert actual_rows == expected_rows
