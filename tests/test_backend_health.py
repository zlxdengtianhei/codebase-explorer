"""Contract tests for parser backend health and typed failures."""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from src.ir import SourceUnit, SourceUnitState, deterministic_entity_id
from src.ir.models import EntityKind
from src.parser.backend import (
    BackendStatus,
    FailureCode,
    GraphSitterBackend,
    ParserBackend,
    PythonAstBackend,
    SyntaxArtifact,
    TypedFailure,
)


def _source_unit(source: str, *, path: str = "sample.py") -> SourceUnit:
    revision = "rev_" + "a" * 64
    return SourceUnit(
        id=deterministic_entity_id(revision, path, EntityKind.SOURCE_UNIT, path),
        source_revision_id=revision,
        path=path,
        language="python",
        content_hash=hashlib.sha256(source.encode()).hexdigest(),
        state=SourceUnitState.DISCOVERED,
        backend_id="pending",
        backend_version="pending",
    )


def test_parser_backend_contract_is_explicit() -> None:
    assert ParserBackend.__abstractmethods__ == frozenset({"health", "parse"})


def test_graph_sitter_missing_module_is_typed_unavailable() -> None:
    def missing(_name: str) -> object:
        raise ModuleNotFoundError("graph_sitter")

    health = GraphSitterBackend(importer=missing).health()

    assert health.status is BackendStatus.UNAVAILABLE
    assert health.backend_id == "graph_sitter"
    assert health.supported_languages == ()
    assert "not importable" in health.limitations[0]


def test_graph_sitter_incompatible_api_is_not_healthy() -> None:
    module = SimpleNamespace(version="9.9.9")

    health = GraphSitterBackend(importer=lambda _name: module).health()

    assert health.status is BackendStatus.INCOMPATIBLE
    assert health.backend_version == "9.9.9"
    assert any("Codebase" in item for item in health.limitations)


def test_graph_sitter_health_refresh_reprobes_changed_environment() -> None:
    state = {"available": False}

    class Codebase:
        def __init__(self, repo_path: str, language: str) -> None:
            pass

    graph_module = SimpleNamespace(version="9.9.9", Codebase=Codebase)
    parser_module = SimpleNamespace(parse_file=lambda _path, _source: object())

    def changing_importer(name: str) -> object:
        if not state["available"]:
            raise ModuleNotFoundError(name)
        if name == "graph_sitter":
            return graph_module
        if name == "graph_sitter.tree_sitter_parser":
            return parser_module
        return SimpleNamespace()

    backend = GraphSitterBackend(importer=changing_importer)
    assert backend.health().status is BackendStatus.UNAVAILABLE

    state["available"] = True
    assert backend.health().status is BackendStatus.UNAVAILABLE
    assert backend.health(refresh=True).status is BackendStatus.HEALTHY


def test_python_ast_backend_is_explicitly_heuristic(tmp_path) -> None:
    source = "def answer():\n    return 42\n"
    (tmp_path / "sample.py").write_text(source, encoding="utf-8")
    backend = PythonAstBackend(root=tmp_path)

    health = backend.health()
    result = backend.parse(_source_unit(source))

    assert health.status is BackendStatus.HEALTHY
    assert health.semantic_tier == "heuristic"
    assert isinstance(result, SyntaxArtifact)
    assert result.backend_id == "python_ast"


def test_backend_parse_hash_mismatch_is_typed_failure(tmp_path) -> None:
    (tmp_path / "sample.py").write_text("different\n", encoding="utf-8")

    result = PythonAstBackend(root=tmp_path).parse(_source_unit("expected\n"))

    assert isinstance(result, TypedFailure)
    assert result.code is FailureCode.CONTENT_HASH_MISMATCH
    assert result.language == "python"


def test_backend_parse_syntax_error_is_typed_failure(tmp_path) -> None:
    source = "def broken(\n"
    (tmp_path / "sample.py").write_text(source, encoding="utf-8")

    result = PythonAstBackend(root=tmp_path).parse(_source_unit(source))

    assert isinstance(result, TypedFailure)
    assert result.code is FailureCode.PARSE_ERROR
    assert result.retryable is False
