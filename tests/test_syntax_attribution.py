from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from cbe.syntax_attribution import syntax_attribution


def _ledger(tmp_path: Path, source: str, kind: str = "module_residual") -> dict:
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    (repo / "sample.py").write_text(source)
    return {
        "repo_root": str(repo), "source_revision": "frozen-r1",
        "inventory": {
            "files": {"sample.py": {"content_hash": hashlib.sha256(source.encode()).hexdigest()}},
            "symbols": {"sample": {"path": "sample.py", "kind": kind,
                                   "span": {"start": 0, "end": len(source)},
                                   "exclusive_spans": [{"start": 0, "end": len(source)}]}},
        },
    }


def test_declaration_only_module_is_program_syntax_not_model_review(tmp_path: Path) -> None:
    source = '"""Docs."""\nimport os\nfrom math import floor\nEXPORTS = ["a", "b"]\n'
    record = syntax_attribution(_ledger(tmp_path, source), "sample")
    assert record is not None
    assert "import statements" in record["behavior"]
    assert "imports may execute code" in record["behavior"]
    assert record["provenance"]["evidence_kind"] == "program_syntax"
    assert record["provenance"]["source_revision"] == "frozen-r1"


def test_bare_base_exception_class_reports_syntax_only(tmp_path: Path) -> None:
    source = 'class LocalError(Exception):\n    """An error."""\n'
    record = syntax_attribution(_ledger(tmp_path, source, "class"), "sample")
    assert record is not None
    assert "bare base names (Exception)" in record["behavior"]
    assert "does not assert base identity" in record["behavior"]


@pytest.mark.parametrize("source,kind", [
    ('from .cli import main\nraise SystemExit(main())\n', "module_residual"),
    ('x = run_side_effect()\n', "module_residual"),
    ('@decorate\nclass C:\n    pass\n', "class"),
    ('class C(metaclass=Meta):\n    pass\n', "class"),
    ('class C(make_base()):\n    pass\n', "class"),
    ('class C(UnknownBase):\n    pass\n', "class"),
])
def test_executable_or_dynamic_declaration_stays_for_model(
    tmp_path: Path, source: str, kind: str,
) -> None:
    assert syntax_attribution(_ledger(tmp_path, source, kind), "sample") is None


def test_shadowed_builtin_exception_base_stays_for_model(tmp_path: Path) -> None:
    source = 'Exception = CustomBase\nclass C(Exception):\n    pass\n'
    ledger = _ledger(tmp_path, source, "class")
    start = source.index("class C")
    ledger["inventory"]["symbols"]["sample"]["span"] = {"start": start, "end": len(source)}
    ledger["inventory"]["symbols"]["sample"]["exclusive_spans"] = [{"start": start, "end": len(source)}]
    assert syntax_attribution(ledger, "sample") is None
