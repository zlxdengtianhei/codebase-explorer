"""Independent-denominator tests for Python semantic inventory."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from src.ir import EntityKind, SourceUnit, SourceUnitState, deterministic_entity_id
from src.parser.adapters.base import FileIR
from src.parser.adapters.python import PythonLanguageAdapter
from src.parser.backend import PythonAstBackend, SyntaxArtifact
from src.semantic.inventory import (
    PROBE_EXCLUDE_DIRS,
    enumerate_python_files,
    enumerate_semantic_inventory,
    reconcile_semantic_ledger,
)


REVISION = "rev_" + "9" * 64
NESTED_FIXTURE = Path(__file__).parent / "fixtures" / "semantic" / "nested"


def _write(root, path: str, text: str) -> None:  # type: ignore[no-untyped-def]
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def test_inventory_matches_probe_file_and_nested_symbol_rules(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = (
        "if True:\n"
        "    def guarded():\n"
        "        def nested():\n"
        "            return 1\n"
        "        return nested()\n"
        "class Box:\n"
        "    def method(self):\n"
        "        return 2\n"
        "def duplicate():\n"
        "    return 'first'\n"
        "def duplicate():\n"
        "    return 'second'\n"
    )
    _write(tmp_path, "pkg/app.py", source)
    _write(tmp_path, "empty.py", "VALUE = 1\n")
    _write(tmp_path, "broken.py", "def broken(:\n")
    _write(tmp_path, "build_tools/kept.py", "def kept():\n    return 1\n")
    _write(tmp_path, "stub.pyi", "def ignored() -> None: ...\n")
    for dirname in PROBE_EXCLUDE_DIRS:
        _write(tmp_path, f"{dirname}/ignored.py", "def ignored():\n    return 0\n")

    files = {path.relative_to(tmp_path).as_posix() for path in enumerate_python_files(tmp_path)}
    assert files == {"broken.py", "build_tools/kept.py", "empty.py", "pkg/app.py"}

    inventory = enumerate_semantic_inventory(tmp_path)
    assert set(inventory.files) == files
    assert set(inventory.symbols) == {
        "build_tools/kept.py::kept",
        "pkg/app.py::Box",
        "pkg/app.py::Box.method",
        "pkg/app.py::duplicate",
        "pkg/app.py::guarded",
        "pkg/app.py::guarded.nested",
    }
    assert inventory.symbols["pkg/app.py::guarded"].kind.value == "function"
    assert inventory.symbols["pkg/app.py::guarded.nested"].kind.value == "method"
    assert inventory.symbols["pkg/app.py::Box.method"].kind.value == "method"
    assert inventory.symbols["pkg/app.py::duplicate"].span == (11, 12)
    assert inventory.files["empty.py"].status.value == "no_symbols"
    assert inventory.files["broken.py"].status.value == "residual"
    assert "parse failed" in inventory.files["broken.py"].reason
    assert any("later definition" in item for item in inventory.diagnostics)

    start, end = inventory.symbols["pkg/app.py::guarded"].span
    body = "\n".join(source.splitlines()[start - 1 : end])
    assert inventory.symbols["pkg/app.py::guarded"].content_hash == (
        "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()
    )


def test_source_revision_changes_for_uncommitted_content(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _write(tmp_path, "app.py", "def f():\n    return 1\n")
    first = enumerate_semantic_inventory(tmp_path)
    _write(tmp_path, "app.py", "def f():\n    return 2\n")
    second = enumerate_semantic_inventory(tmp_path)
    assert first.source_revision != second.source_revision
    assert first.symbols["app.py::f"].content_hash != second.symbols["app.py::f"].content_hash


def test_decorators_are_part_of_semantic_span_and_content_hash(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = "@property\ndef value():\n    return 1\n"
    _write(tmp_path, "app.py", source)

    inventory = enumerate_semantic_inventory(tmp_path)
    symbol = inventory.symbols["app.py::value"]

    assert symbol.span == (1, 3)
    assert symbol.content_hash == (
        "sha256:" + hashlib.sha256(source.rstrip("\n").encode("utf-8")).hexdigest()
    )


def test_multiline_decorator_fixture_starts_span_at_decorator() -> None:
    source = (NESTED_FIXTURE / "a.py").read_text(encoding="utf-8")
    inventory = enumerate_semantic_inventory(NESTED_FIXTURE)
    symbol = inventory.symbols["a.py::multiline_decorated"]
    first_line = source.splitlines().index("@lru_cache(") + 1

    assert symbol.span == (first_line, first_line + 4)
    expected_body = "\n".join(source.splitlines()[symbol.span[0] - 1 : symbol.span[1]])
    assert expected_body.startswith("@lru_cache(\n")
    assert symbol.content_hash == (
        "sha256:" + hashlib.sha256(expected_body.encode("utf-8")).hexdigest()
    )


def test_inventory_bridges_ir_only_by_path_lexical_name_and_full_span(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = "def outer():\n    def inner():\n        return 1\n    return inner()\n"
    _write(tmp_path, "pkg/app.py", source)
    unit = SourceUnit(
        id=deterministic_entity_id(REVISION, "pkg/app.py", EntityKind.SOURCE_UNIT, "pkg/app.py"),
        source_revision_id=REVISION,
        path="pkg/app.py",
        language="python",
        content_hash=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        state=SourceUnitState.DISCOVERED,
        backend_id="python_ast",
        backend_version="test",
    )
    artifact = PythonAstBackend(root=tmp_path).parse(unit)
    assert isinstance(artifact, SyntaxArtifact)
    file_ir = PythonLanguageAdapter(tmp_path).normalize(artifact)
    assert isinstance(file_ir, FileIR)

    inventory = enumerate_semantic_inventory(tmp_path, ir_symbols=file_ir.symbols)
    by_lexical = {
        symbol.language_attributes["lexical_qualified_name"]: symbol.id
        for symbol in file_ir.symbols
    }
    assert inventory.symbols["pkg/app.py::outer"].ir_symbol_id == by_lexical["outer"]
    assert inventory.symbols["pkg/app.py::outer.inner"].ir_symbol_id == by_lexical["outer.inner"]
    assert inventory.symbols["pkg/app.py::outer.inner"].kind.value == "method"

    bridged_ledger = reconcile_semantic_ledger(inventory)
    reopened_without_adapter = reconcile_semantic_ledger(
        enumerate_semantic_inventory(tmp_path),
        bridged_ledger,
    )
    assert reopened_without_adapter.symbols["pkg/app.py::outer"].ir_symbol_id == by_lexical["outer"]
