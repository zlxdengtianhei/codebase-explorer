"""_scan_modules must walk the repo once per adapter, not once per file.

This is the negative control for the django 15-minute IR wall: if the walk
count grows with file count, the green of "IR finished" is fake.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from src.ir import EntityKind, SourceUnit, SourceUnitState, deterministic_entity_id
from src.parser.adapters.base import FileIR
from src.parser.adapters.python import PythonLanguageAdapter
from src.parser.backend import PythonAstBackend, SyntaxArtifact


REVISION = "rev_" + "c" * 64


def _write(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _artifact(root: Path, relative: str) -> SyntaxArtifact:
    source = (root / relative).read_text(encoding="utf-8")
    unit = SourceUnit(
        id=deterministic_entity_id(REVISION, relative, EntityKind.SOURCE_UNIT, relative),
        source_revision_id=REVISION,
        path=relative,
        language="python",
        content_hash=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        state=SourceUnitState.DISCOVERED,
        backend_id="python_ast",
        backend_version="test",
    )
    return SyntaxArtifact(
        source_unit=unit,
        backend_id="python_ast",
        backend_version="test",
        language="python",
        syntax_tree=ast.parse(source, filename=relative),
    )


def test_scan_modules_walks_repo_once_across_many_normalize_calls(tmp_path: Path) -> None:
    for index in range(12):
        _write(tmp_path, f"pkg/mod_{index:02d}.py", f"def f{index}():\n    return {index}\n")
    _write(tmp_path, "pkg/__init__.py", "from .mod_00 import f0\n")
    adapter = PythonLanguageAdapter(tmp_path)
    backend = PythonAstBackend(root=tmp_path)
    results: list[FileIR] = []
    for relative in ["pkg/__init__.py"] + [f"pkg/mod_{index:02d}.py" for index in range(12)]:
        artifact = backend.parse(
            _artifact(tmp_path, relative).source_unit
        )
        assert isinstance(artifact, SyntaxArtifact)
        normalized = adapter.normalize(artifact)
        assert isinstance(normalized, FileIR)
        results.append(normalized)
    assert adapter._path_walks == 1
    assert len(results) == 13
    init_ir = results[0]
    import_relations = [relation for relation in init_ir.relations if relation.kind == "import"]
    assert import_relations, "cached scan must still emit the __init__ import edge"


def test_new_file_after_first_walk_rescans_once(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "def a():\n    return 1\n")
    adapter = PythonLanguageAdapter(tmp_path)
    first = adapter.normalize(_artifact(tmp_path, "a.py"))
    assert isinstance(first, FileIR)
    assert adapter._path_walks == 1
    _write(tmp_path, "b.py", "def b():\n    return 2\n")
    second = adapter.normalize(_artifact(tmp_path, "b.py"))
    assert isinstance(second, FileIR)
    assert adapter._path_walks == 2
    third = adapter.normalize(_artifact(tmp_path, "a.py"))
    assert isinstance(third, FileIR)
    assert adapter._path_walks == 2
