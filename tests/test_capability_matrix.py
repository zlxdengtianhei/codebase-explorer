"""Capability matrix and legacy parser handshake tests."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.capabilities import CAPABILITY_NAMES, build_capability_handshake
from src.ir import IR_PROTOCOL_ID, Availability, SemanticTier, VerificationStatus
from src.parser.adapters.registry import BackendRegistry
from src.parser.backend import (
    BackendHealth,
    BackendStatus,
    FailureCode,
    ParserBackend,
    PythonAstBackend,
    SyntaxArtifact,
    TypedFailure,
)
from src.parser.codebase import (
    CodebaseParseError,
    CodebaseParser,
    RequestedLanguageUnavailableError,
    _USE_FALLBACK,
)


def _ast_only_registry(root: Path | None = None) -> BackendRegistry:
    registry = BackendRegistry()
    registry.register(
        "python_ast",
        lambda selected_root: PythonAstBackend(root=selected_root),
        priority=10,
    )
    return registry


def test_registry_is_single_selection_source_and_falls_back_to_ast(tmp_path) -> None:
    registry = _ast_only_registry()

    selected = registry.select("python", root=tmp_path)

    assert isinstance(selected, PythonAstBackend)
    assert registry.select("typescript", root=tmp_path) is None


def test_requested_unavailable_language_never_returns_empty_success(tmp_path) -> None:
    (tmp_path / "app.ts").write_text("export const x = 1;\n", encoding="utf-8")
    parser = CodebaseParser(registry=_ast_only_registry())

    with pytest.raises(RequestedLanguageUnavailableError) as caught:
        parser.parse(str(tmp_path), languages=["typescript"])

    failure = caught.value.failures[0]
    assert failure.language == "typescript"
    assert caught.value.handshake.requested_languages == ("typescript",)
    assert caught.value.handshake.detected_languages == ("typescript",)
    assert caught.value.handshake.successfully_parsed_languages == ()
    assert caught.value.handshake.protocol_version == IR_PROTOCOL_ID


def test_handshake_separates_requested_detected_and_parsed(tmp_path) -> None:
    (tmp_path / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    (tmp_path / "app.ts").write_text("export const x = 1;\n", encoding="utf-8")
    snapshot = CodebaseParser(registry=_ast_only_registry()).parse(
        str(tmp_path), languages=["python"]
    )

    assert snapshot.requested_languages == ("python",)
    assert snapshot.languages_detected == ("python", "typescript")
    assert snapshot.successfully_parsed_languages == ("python",)
    assert snapshot.handshake is not None
    assert snapshot.handshake.requested_languages == ("python",)
    assert snapshot.handshake.detected_languages == ("python", "typescript")
    assert snapshot.handshake.successfully_parsed_languages == ("python",)
    assert snapshot.handshake.protocol_version == IR_PROTOCOL_ID


def test_autodetect_does_not_relabel_detected_languages_as_requested(tmp_path) -> None:
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")

    snapshot = CodebaseParser(registry=_ast_only_registry()).parse(str(tmp_path))

    assert snapshot.requested_languages == ()
    assert snapshot.languages_detected == ("python",)
    assert snapshot.successfully_parsed_languages == ("python",)
    assert snapshot.handshake is not None
    assert snapshot.handshake.requested_languages == ()


def test_autodetect_keeps_unavailable_secondary_language_as_residual(tmp_path) -> None:
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "web.ts").write_text("export const x = 1;\n", encoding="utf-8")

    snapshot = CodebaseParser(registry=_ast_only_registry()).parse(str(tmp_path))

    assert snapshot.languages_detected == ("python", "typescript")
    assert snapshot.successfully_parsed_languages == ("python",)
    assert tuple(failure.language for failure in snapshot.failures) == ("typescript",)
    assert snapshot.failures[0].code is FailureCode.BACKEND_UNAVAILABLE


def test_capability_cells_keep_three_axes_independent(tmp_path) -> None:
    registry = _ast_only_registry()
    handshake = build_capability_handshake(
        registry=registry,
        root=tmp_path,
        requested_languages=("python", "typescript"),
        detected_languages=("python", "typescript"),
        successfully_parsed_languages=("python",),
        failures=(),
        receipt_id="test-receipt",
    )

    assert len(handshake.capability_cells) == 2 * len(CAPABILITY_NAMES)
    python_syntax = handshake.cell("python", "syntax")
    assert python_syntax.availability is Availability.AVAILABLE
    assert python_syntax.semantic_tier is SemanticTier.HEURISTIC
    assert python_syntax.verification_status is VerificationStatus.UNVERIFIED
    ts_syntax = handshake.cell("typescript", "syntax")
    assert ts_syntax.availability is Availability.UNAVAILABLE
    assert ts_syntax.verification_status is VerificationStatus.CANNOT_JUDGE


def test_handshake_carries_backend_toolchain_limitations_and_receipt(tmp_path) -> None:
    handshake = build_capability_handshake(
        registry=_ast_only_registry(),
        root=tmp_path,
        requested_languages=("python",),
        detected_languages=("python",),
        successfully_parsed_languages=("python",),
        failures=(),
        receipt_id="receipt-123",
    )

    cell = handshake.cell("python", "calls")
    assert cell.backend_id == "python_ast"
    assert cell.backend_version
    assert cell.toolchain_conditions
    assert cell.limitations
    assert cell.evidence_receipt_id == "receipt-123"
    assert handshake.protocol_version == IR_PROTOCOL_ID


def test_capability_handshake_source_has_no_stale_protocol_literal() -> None:
    capability_source = Path(__file__).parents[1] / "src" / "capabilities.py"

    assert '"cbe-ir/1"' not in capability_source.read_text(encoding="utf-8")


def test_registry_rejects_duplicate_backend_id() -> None:
    registry = _ast_only_registry()

    with pytest.raises(ValueError, match="already registered"):
        registry.register("python_ast", lambda root: PythonAstBackend(root=root))


class _CountingBackend(ParserBackend):
    backend_id = "counting"

    def __init__(
        self,
        *,
        fail_paths: frozenset[str] = frozenset(),
        artifact_language: str | None = None,
    ) -> None:
        self.fail_paths = fail_paths
        self.artifact_language = artifact_language
        self.parse_calls: list[str] = []

    def health(self) -> BackendHealth:
        return BackendHealth(
            backend_id=self.backend_id,
            backend_version="1",
            status=BackendStatus.HEALTHY,
            supported_languages=("python", "javascript"),
            semantic_tier="syntax_only",
            toolchain_conditions=("test backend",),
            limitations=("syntax only",),
        )

    def parse(self, source_unit):  # type: ignore[no-untyped-def]
        self.parse_calls.append(source_unit.path)
        if source_unit.path in self.fail_paths:
            return TypedFailure(
                code=FailureCode.PARSE_ERROR,
                message=f"intentional failure: {source_unit.path}",
                backend_id=self.backend_id,
                language=source_unit.language,
            )
        return SyntaxArtifact(
            source_unit=source_unit,
            backend_id=self.backend_id,
            backend_version="1",
            language=self.artifact_language or source_unit.language,
            syntax_tree=object(),
        )


def _counting_registry(backend: _CountingBackend) -> BackendRegistry:
    registry = BackendRegistry()
    registry.register("counting", lambda _root: backend, priority=100)
    return registry


def test_selected_backend_parse_failure_survives_compatibility_conversion(tmp_path) -> None:
    (tmp_path / "good.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "bad.py").write_text("value = 2\n", encoding="utf-8")
    backend = _CountingBackend(fail_paths=frozenset({"bad.py"}))

    with pytest.raises(RequestedLanguageUnavailableError) as caught:
        CodebaseParser(registry=_counting_registry(backend)).parse(
            str(tmp_path), languages=["python"]
        )

    assert backend.parse_calls == ["bad.py", "good.py"]
    assert caught.value.failures[0].backend_id == "counting"
    assert caught.value.failures[0].code is FailureCode.PARSE_ERROR
    assert caught.value.handshake.successfully_parsed_languages == ()


def test_selected_backend_success_drives_compatibility_snapshot(tmp_path) -> None:
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    backend = _CountingBackend()

    snapshot = CodebaseParser(registry=_counting_registry(backend)).parse(
        str(tmp_path), languages=["python"]
    )

    assert backend.parse_calls == ["app.py"]
    assert tuple(item.filepath for item in snapshot.files) == ("app.py",)
    assert snapshot.successfully_parsed_languages == ("python",)


def test_requested_language_without_eligible_source_is_failure(tmp_path) -> None:
    (tmp_path / "app.ts").write_text("export const x = 1;\n", encoding="utf-8")

    with pytest.raises(RequestedLanguageUnavailableError) as caught:
        CodebaseParser(registry=_ast_only_registry()).parse(
            str(tmp_path), languages=["python"]
        )

    assert caught.value.failures[0].code is FailureCode.SOURCE_UNAVAILABLE
    assert caught.value.handshake.detected_languages == ("typescript",)
    assert caught.value.handshake.successfully_parsed_languages == ()


def test_python_syntax_error_is_terminal_typed_failure(tmp_path) -> None:
    (tmp_path / "broken.py").write_text("def broken(\n", encoding="utf-8")

    with pytest.raises(RequestedLanguageUnavailableError) as caught:
        CodebaseParser(registry=_ast_only_registry()).parse(
            str(tmp_path), languages=["python"]
        )

    assert caught.value.failures[0].code is FailureCode.PARSE_ERROR
    assert caught.value.handshake.successfully_parsed_languages == ()


def test_autodetected_parse_failure_is_actionable_to_server_boundary(tmp_path) -> None:
    (tmp_path / "broken.py").write_text("def broken(\n", encoding="utf-8")

    with pytest.raises(CodebaseParseError, match="Python AST parse failed") as caught:
        CodebaseParser(registry=_ast_only_registry()).parse(str(tmp_path))

    assert caught.value.handshake.protocol_version == IR_PROTOCOL_ID


def test_real_server_caller_converts_parse_failure_to_tool_error(tmp_path) -> None:
    from mcp.server.fastmcp.exceptions import ToolError
    from src.server import analyze_codebase

    (tmp_path / "broken.py").write_text("def broken(\n", encoding="utf-8")
    parser = CodebaseParser(registry=_ast_only_registry())
    ctx = SimpleNamespace(
        request_context=SimpleNamespace(lifespan_context={"parser": parser})
    )

    with pytest.raises(ToolError, match="Python AST parse failed"):
        asyncio.run(analyze_codebase(
            path=str(tmp_path),
            languages=["python"],
            output_dir=str(tmp_path / ".analysis"),
            force_reindex=True,
            ctx=ctx,  # type: ignore[arg-type]
        ))


def test_oracle_unsupported_is_not_environment_unavailable(tmp_path) -> None:
    backend = _CountingBackend()
    handshake = build_capability_handshake(
        registry=_counting_registry(backend),
        root=tmp_path,
        requested_languages=("javascript",),
        detected_languages=("javascript",),
        successfully_parsed_languages=(),
        failures=(),
        receipt_id="test-receipt",
    )

    cell = handshake.cell("javascript", "types")
    assert cell.availability is Availability.UNSUPPORTED
    assert cell.verification_status is VerificationStatus.CANNOT_JUDGE


def test_fallback_selector_routes_malformed_python_through_registered_backend(
    tmp_path,
) -> None:
    (tmp_path / "broken.py").write_text("def broken(\n", encoding="utf-8")
    parser = CodebaseParser(registry=_ast_only_registry())

    with patch.object(parser, "_init_codebase", return_value=_USE_FALLBACK):
        with pytest.raises(RequestedLanguageUnavailableError) as caught:
            parser.parse(str(tmp_path), languages=["python"])

    assert caught.value.failures[0].code is FailureCode.PARSE_ERROR
    assert caught.value.handshake.successfully_parsed_languages == ()


def test_missing_codegen_selector_cannot_make_no_source_success(tmp_path) -> None:
    (tmp_path / "app.ts").write_text("export const x = 1;\n", encoding="utf-8")
    parser = CodebaseParser(registry=_ast_only_registry())

    with patch.dict(sys.modules, {"codegen": None}):
        with pytest.raises(RequestedLanguageUnavailableError) as caught:
            parser.parse(str(tmp_path), languages=["python"])

    assert caught.value.failures[0].code is FailureCode.SOURCE_UNAVAILABLE
    assert caught.value.handshake.successfully_parsed_languages == ()


def test_real_server_rejects_malformed_python_on_fallback_selector(tmp_path) -> None:
    from mcp.server.fastmcp.exceptions import ToolError
    from src.server import analyze_codebase

    (tmp_path / "broken.py").write_text("def broken(\n", encoding="utf-8")
    parser = CodebaseParser(registry=_ast_only_registry())
    ctx = SimpleNamespace(
        request_context=SimpleNamespace(lifespan_context={"parser": parser})
    )
    output = tmp_path / ".analysis"

    with patch.dict(sys.modules, {"codegen": None}):
        with pytest.raises(ToolError, match="Python AST parse failed"):
            asyncio.run(analyze_codebase(
                path=str(tmp_path),
                languages=["python"],
                output_dir=str(output),
                force_reindex=True,
                ctx=ctx,  # type: ignore[arg-type]
            ))
    assert not tuple(output.glob("*.json"))


def test_duplicate_requested_languages_parse_once_in_stable_order(tmp_path) -> None:
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    backend = _CountingBackend()

    snapshot = CodebaseParser(registry=_counting_registry(backend)).parse(
        str(tmp_path), languages=["python", "python"]
    )

    assert backend.parse_calls == ["app.py"]
    assert snapshot.requested_languages == ("python",)
    assert snapshot.successfully_parsed_languages == ("python",)
    assert tuple(item.filepath for item in snapshot.files) == ("app.py",)


def test_artifact_language_mismatch_is_typed_backend_failure(tmp_path) -> None:
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    backend = _CountingBackend(artifact_language="typescript")

    with pytest.raises(RequestedLanguageUnavailableError) as caught:
        CodebaseParser(registry=_counting_registry(backend)).parse(
            str(tmp_path), languages=["python"]
        )

    assert caught.value.failures[0].code is FailureCode.BACKEND_ERROR
    assert "language" in caught.value.failures[0].message


def test_throwing_health_probe_becomes_typed_degraded_failure(tmp_path) -> None:
    class ThrowingHealthBackend(ParserBackend):
        def health(self):  # type: ignore[no-untyped-def]
            raise RuntimeError("probe exploded")

        def parse(self, source_unit):  # type: ignore[no-untyped-def]
            raise AssertionError("parse must not run after a failed health probe")

    registry = BackendRegistry()
    registry.register("throwing", lambda _root: ThrowingHealthBackend())
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(RequestedLanguageUnavailableError) as caught:
        CodebaseParser(registry=registry).parse(str(tmp_path), languages=["python"])

    assert caught.value.failures[0].code is FailureCode.BACKEND_ERROR
    assert "probe exploded" in caught.value.failures[0].message
    assert registry.health(root=tmp_path)[0].status is BackendStatus.ERROR


class _StatefulHealthBackend(_CountingBackend):
    def __init__(self, transitions: list[BackendHealth | Exception]) -> None:
        super().__init__()
        self.transitions = transitions
        self.health_calls = 0

    def health(self, *, refresh: bool = False) -> BackendHealth:
        transition = self.transitions[min(self.health_calls, len(self.transitions) - 1)]
        self.health_calls += 1
        if isinstance(transition, Exception):
            raise transition
        return transition


def _health(
    status: BackendStatus,
    *,
    supported_languages: tuple[str, ...] = ("python",),
) -> BackendHealth:
    return BackendHealth(
        backend_id="counting",
        backend_version="1",
        status=status,
        supported_languages=supported_languages,
        semantic_tier="syntax_only",
        toolchain_conditions=("stateful test backend",),
        limitations=(f"state={status.value}",),
    )


def test_selected_health_snapshot_is_stable_when_later_probe_would_throw(tmp_path) -> None:
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    backend = _StatefulHealthBackend([
        _health(BackendStatus.HEALTHY),
        RuntimeError("second health exploded"),
    ])

    snapshot = CodebaseParser(registry=_counting_registry(backend)).parse(
        str(tmp_path), languages=["python"]
    )

    assert tuple(item.filepath for item in snapshot.files) == ("app.py",)
    assert snapshot.successfully_parsed_languages == ("python",)
    assert backend.health_calls == 1
    assert snapshot.handshake is not None
    assert snapshot.handshake.backend_health[0].status is BackendStatus.HEALTHY


def test_registry_health_refresh_types_throwing_to_healthy_transition(tmp_path) -> None:
    backend = _StatefulHealthBackend([
        RuntimeError("first health exploded"),
        _health(BackendStatus.HEALTHY),
    ])
    registry = _counting_registry(backend)

    first = registry.health(root=tmp_path)
    cached = registry.health(root=tmp_path)
    refreshed = registry.health(root=tmp_path, refresh=True)

    assert first[0].status is BackendStatus.ERROR
    assert cached == first
    assert refreshed[0].status is BackendStatus.HEALTHY
    assert backend.health_calls == 2


@pytest.mark.parametrize("ambient_value", [None, SimpleNamespace()])
def test_ambient_codegen_cannot_change_registry_execution_or_identity(
    tmp_path, ambient_value: object,
) -> None:
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    backend = _CountingBackend()
    ambient_executor = SimpleNamespace(Codebase=pytest.fail)

    with patch.dict(sys.modules, {"codegen": ambient_value or ambient_executor}):
        snapshot = CodebaseParser(registry=_counting_registry(backend)).parse(
            str(tmp_path), languages=["python"]
        )

    assert backend.parse_calls == ["app.py"]
    assert snapshot.handshake is not None
    assert snapshot.handshake.backend_health[0].backend_id == "counting"
    assert snapshot.handshake.cell("python", "syntax").backend_id == "counting"


def test_fresh_and_injected_module_processes_are_observationally_equal(
    tmp_path,
) -> None:
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    script = """
import json
import os
import sys
from types import SimpleNamespace
from src.parser.codebase import CodebaseParser

if os.environ["AMBIENT_CODEGEN"] == "1":
    class PoisonCodebase:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("ambient executor must be unreachable")
    sys.modules["codegen"] = SimpleNamespace(Codebase=PoisonCodebase)

snapshot = CodebaseParser().parse(os.environ["REPO_ROOT"], languages=["python"])
handshake = snapshot.handshake
assert handshake is not None
print(json.dumps({
    "files": [item.filepath for item in snapshot.files],
    "parsed": snapshot.successfully_parsed_languages,
    "failures": [failure.code for failure in snapshot.failures],
    "health": [item.backend_id for item in handshake.backend_health],
    "syntax_backend": handshake.cell("python", "syntax").backend_id,
}, sort_keys=True))
"""
    observations = []
    for injected in ("0", "1"):
        env = os.environ.copy()
        env.update({
            "AMBIENT_CODEGEN": injected,
            "CBE_PARSER_BACKEND": "python_ast",
            "REPO_ROOT": str(tmp_path),
        })
        completed = subprocess.run(
            [sys.executable, "-W", "error", "-c", script],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        observations.append(json.loads(completed.stdout))

    assert observations[0] == observations[1]
    assert observations[0]["syntax_backend"] == "python_ast"
