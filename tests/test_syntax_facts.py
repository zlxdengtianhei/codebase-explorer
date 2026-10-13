"""Deterministic atoms preserve local statement syntax, not narrative truth."""
import pytest
from cbe.inventory import build_inventory
from cbe.syntax_facts import atoms_for, check_atom_refs


def _ledger(repo):
    # The same ledger shape generate builds for its condition and failure tables.
    return {"repo_root": str(repo), "inventory": build_inventory(repo).to_dict()}


def test_guarded_return_raise_append_and_update_atoms(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ops.py").write_text("""def f(event_id, usage, counter, events):
    counter += 1
    if not isinstance(usage, dict):
        return
    if event_id:
        events.append(event_id)
    if counter > 5:
        raise ValueError('limit')
    return {'total': usage.get('total') or 0 + counter}
""")
    ledger = _ledger(repo)
    sid = next(s for s, row in ledger["inventory"]["symbols"].items() if row["name"] == "f")
    rows = atoms_for(ledger, sid)["atoms"]
    assert [r["kind"] for r in rows] == ["update", "return_none", "append_call", "raise_expression", "return_expression"]
    assert rows[1]["guards"] == ["not isinstance(usage, dict)"] and rows[1]["syntax"] == "return"
    assert rows[2]["guards"] == ["event_id"]
    assert rows[3]["guards"] == ["counter > 5"]
    assert "or 0 + counter" in rows[4]["syntax"]
    spans = [ledger["inventory"]["symbols"][sid]["span"]]
    check_atom_refs(ledger, sid, [r["id"] for r in rows], spans)
    with pytest.raises(ValueError, match="foreign"):
        check_atom_refs(ledger, sid, ["wrong"], spans)


def test_fragment_atom_does_not_leak_unpresented_guard(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    text = "def f(secret_condition):\n if secret_condition:\n  return\n"
    (repo / "ops.py").write_text(text)
    ledger = _ledger(repo)
    sid = next(s for s, row in ledger["inventory"]["symbols"].items() if row["name"] == "f")
    spans = [{"start": text.index("return"), "end": text.index("return") + 6}]
    rows = atoms_for(ledger, sid, spans)["atoms"]
    assert len(rows) == 1
    assert rows[0]["guards"] == ["condition outside owned view: unknown"]
    assert "secret_condition" not in repr(rows)


def test_nested_function_is_not_an_outer_statement(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ops.py").write_text("def outer():\n def inner():\n  raise KeyError('nested')\n return inner\n")
    ledger = _ledger(repo)
    sid = next(s for s, row in ledger["inventory"]["symbols"].items() if row["name"] == "outer")
    assert atoms_for(ledger, sid)["atoms"] == []
