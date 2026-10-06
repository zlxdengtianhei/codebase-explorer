from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cbe.static_literals import accepted_numeric_literals, accepted_return_keys, compact_literal


def test_scope_binding_cache_is_local_and_retains_shadow_exclusion(monkeypatch):
    from cbe import static_literals
    source = "LIMIT = 3\ndef f(x):\n return LIMIT + LIMIT + LIMIT\n"
    span = {"name": "f", "span": {"start": source.index("def f"), "end": len(source)}}
    original = static_literals._scope_binds
    calls = []
    def counted(scope, name):
        calls.append((scope, name))
        return original(scope, name)
    monkeypatch.setattr(static_literals, "_scope_binds", counted)
    refs, unsafe = static_literals._referenced_by_accepted_symbols(source, [("f", span)], {"LIMIT"})
    assert refs == {"f": {"LIMIT"}} and not unsafe
    assert len(calls) == 1
    changed = "LIMIT = 3\ndef f(x):\n LIMIT = x\n return LIMIT + LIMIT\n"
    changed_span = {"name": "f", "span": {"start": changed.index("def f"), "end": len(changed)}}
    refs, unsafe = static_literals._referenced_by_accepted_symbols(changed, [("f", changed_span)], {"LIMIT"})
    assert not refs and unsafe == {"LIMIT"}
    assert len(calls) == 2  # A fresh AST/source has its own conservative binding result.


def _ledger(tmp_path: Path, source: str, behavior: str = "Computes an estimate.") -> dict:
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    (repo / "sample.py").write_text(source)
    start = source.index("def f(")
    sid = "sample.py::function::f"
    detail = {"symbol_id": sid, "behavior": behavior}
    digest = hashlib.sha256(json.dumps(
        detail, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    return {
        "repo_root": str(repo), "source_revision": "frozen-r1",
        "inventory": {
            "files": {"sample.py": {"content_hash": hashlib.sha256(source.encode()).hexdigest()}},
            "symbols": {sid: {"path": "sample.py", "kind": "function", "name": "f",
                              "span": {"start": start, "end": len(source)}}},
        },
        "details": {sid: detail},
        "fact_reviews": {sid: {"state": "source_checked", "content_sha256": digest}},
    }


def test_name_reference_projects_arbitrary_frozen_numeric_map(tmp_path: Path) -> None:
    source = 'RATIOS = {"alpha": 1.25, "beta": 7}\n\ndef f(x):\n    return x / RATIOS["alpha"]\n'
    ledger = _ledger(tmp_path, source)
    sid = next(iter(ledger["details"]))
    row = accepted_numeric_literals(ledger)[sid][0]
    assert row == {"name": "RATIOS", "value": {"alpha": 1.25, "beta": 7},
                   "path": "sample.py", "line": 1,
                   "evidence_kind": "frozen_source_literal"}

    updated = source.replace("1.25", "2.5")
    (tmp_path / "repo" / "sample.py").write_text(updated)
    with pytest.raises(ValueError, match="hash mismatch"):
        accepted_numeric_literals(ledger)
    ledger["inventory"]["files"]["sample.py"]["content_hash"] = hashlib.sha256(updated.encode()).hexdigest()
    assert accepted_numeric_literals(ledger)[sid][0]["value"]["alpha"] == 2.5


@pytest.mark.parametrize("source", [
    'RATIOS = make_ratios()\n\ndef f(x):\n    return RATIOS["a"]\n',
    'RATIOS = {"a": 1}\nRATIOS = {"a": 2}\n\ndef f(x):\n    return RATIOS["a"]\n',
    'RATIOS = {"a": 1}\nRATIOS["a"] = 2\n\ndef f(x):\n    return RATIOS["a"]\n',
    'RATIOS = {"a": 1}\n\ndef f(x):\n    RATIOS = {"a": 2}\n    return RATIOS["a"]\n',
    'RATIOS = {"a": True}\n\ndef f(x):\n    return RATIOS["a"]\n',
])
def test_dynamic_rebound_mutated_shadowed_or_bool_value_is_not_projected(
    tmp_path: Path, source: str,
) -> None:
    assert accepted_numeric_literals(_ledger(tmp_path, source)) == {}


def test_unaccepted_prose_cannot_trigger_literal_projection(tmp_path: Path) -> None:
    source = 'CONSTANT = 9\n\ndef f(x):\n    return x\n'
    ledger = _ledger(tmp_path, source, behavior="CONSTANT is nine.")
    sid = next(iter(ledger["details"]))
    ledger["fact_reviews"][sid]["state"] = "author_fact"
    assert accepted_numeric_literals(ledger) == {}


def test_referenced_immutable_diagnostic_tuple_is_preserved_without_prose_copy(tmp_path: Path) -> None:
    source = '_FLAGS = ("opaque", "stale_packet", "unknown_format")\n\ndef f(reason):\n    return any(flag in reason for flag in _FLAGS)\n'
    ledger = _ledger(tmp_path, source, "Matches configured diagnostic substrings.")
    sid = next(iter(ledger["details"]))
    row = accepted_numeric_literals(ledger)[sid][0]
    assert row["value"] == ("opaque", "stale_packet", "unknown_format")
    reader_line = compact_literal(row)
    assert all(value in reader_line for value in row["value"])
    assert "L1 [literal]: _FLAGS=" in reader_line


@pytest.mark.parametrize("declaration", [
    '_FLAGS = ["opaque", "other"]',
    '_FLAGS = ("opaque", "opaque")',
    '_FLAGS = tuple(make_flags())',
    '_FLAGS = ("opaque", "other")\n_FLAGS = ("replacement",)',
    '_FLAGS = ("opaque", "other")\n_FLAGS += ("replacement",)',
])
def test_mutable_ambiguous_or_dynamic_diagnostic_values_are_not_projected(tmp_path: Path, declaration: str) -> None:
    source = declaration + '\n\ndef f(reason):\n    return any(flag in reason for flag in _FLAGS)\n'
    assert accepted_numeric_literals(_ledger(tmp_path, source)) == {}


def test_reader_page_exposes_arbitrary_diagnostic_enum_with_source_location(tmp_path: Path) -> None:
    from cbe.runner import analyze
    from cbe.module_first_render import render_module_plan
    repo = tmp_path / "reader-repo"
    repo.mkdir()
    source = ('VALUES = {\n' + ''.join(f'"v{i}": {i},\n' for i in range(500)) + '}\n'
              '_REASONS = ("opaque", "stale_packet", "unknown_format")\n'
              'def f(reason):\n    return any(item in reason for item in _REASONS)\n')
    (repo / "reason.py").write_text(source)
    run = tmp_path / "reader-run"
    ledger = analyze(repo, run, documentation_profile="module-first-v2")
    sid = next(sid for sid, symbol in ledger["inventory"]["symbols"].items() if symbol["name"] == "f")
    detail = {"symbol_id": sid, "behavior": "Returns true when a configured substring occurs in the reason."}
    digest = hashlib.sha256(json.dumps(detail, ensure_ascii=False, sort_keys=True,
                                       separators=(",", ":")).encode()).hexdigest()
    ledger["details"] = {sid: detail}
    ledger["fact_reviews"] = {sid: {"state": "source_checked", "content_sha256": digest}}
    plan = json.loads((run / "module_plan.json").read_text())
    reader = tmp_path / "reader"
    manifest = render_module_plan(ledger, plan, reader, run_dir=run)
    pages = [path.read_text() for path in (reader / "files").glob("*.md")]
    assert any('_REASONS=' in page and all(value in page for value in ("opaque", "stale_packet", "unknown_format"))
               for page in pages)
    assert float(manifest["token_budget"]["ratio"]) <= 0.5


def test_destructuring_cannot_assign_entire_rhs_to_each_name_but_name_chains_can(tmp_path: Path) -> None:
    source = 'FIRST, SECOND = ("opaque", "other")\n\ndef f(reason):\n    return reason == FIRST\n'
    assert accepted_numeric_literals(_ledger(tmp_path, source)) == {}
    chained = '_FLAGS = _ALIASED_FLAGS = ("opaque", "other")\n\ndef f(reason):\n    return reason in _ALIASED_FLAGS\n'
    rows = accepted_numeric_literals(_ledger(tmp_path, chained))
    assert list(rows.values())[0][0]["value"] == ("opaque", "other")
    rebound = '_FLAGS = ("opaque", "other")\n_FLAGS, SECOND = ("replacement", "another")\n\ndef f(reason):\n    return reason in _FLAGS\n'
    assert accepted_numeric_literals(_ledger(tmp_path, rebound)) == {}


def test_arbitrary_identical_direct_return_dict_keys_are_projected(tmp_path: Path) -> None:
    source = ('def f(flag):\n'
              '    if flag:\n'
              '        return {"first": 1, "second": 2}\n'
              '    return {"second": 3, "first": 4}\n')
    ledger = _ledger(tmp_path, source)
    sid = next(iter(ledger["details"]))
    assert accepted_return_keys(ledger)[sid] == {
        "path": "sample.py", "keys": ["first", "second"],
        "line": 3, "statement_count": 2,
        "evidence_kind": "frozen_return_dict_keys",
    }


@pytest.mark.parametrize("source", [
    'def f(flag):\n    if flag:\n        return {"first": 1}\n    return {"other": 2}\n',
    'def f(values):\n    return {**values, "first": 1}\n',
    'def f(flag):\n    if flag:\n        return {"first": 1}\n    return None\n',
])
def test_dynamic_or_inconsistent_return_shapes_are_not_claimed(
    tmp_path: Path, source: str,
) -> None:
    assert accepted_return_keys(_ledger(tmp_path, source)) == {}


def test_nested_return_does_not_contaminate_outer_function(tmp_path: Path) -> None:
    source = ('def f():\n'
              '    def inner():\n'
              '        return {"unrelated": 1}\n'
              '    return {"outer": 2}\n')
    ledger = _ledger(tmp_path, source)
    sid = next(iter(ledger["details"]))
    assert accepted_return_keys(ledger)[sid]["keys"] == ["outer"]
