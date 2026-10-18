"""O4c public behavior: locate, follow a source link, and read source coordinates."""
import json
import re
from pathlib import Path

from cbe import cli, docs
from test_layers_o4 import _run


def test_find_is_a_bounded_locator_in_text_and_json(tmp_path, capsys):
    run, ids, _, _, _ = _run(tmp_path)
    catalog_path = run / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    uid = ids[0]
    full = "Locator needle " + "word " * 60 + ". Extra body must stay behind query."
    catalog["units"][uid].update(explain=full, summary="")
    catalog_path.write_text(json.dumps(catalog))
    assert cli.main(["find", "--run-dir", str(run), "--term", "needle", "--limit", "1"]) == 0
    text = capsys.readouterr().out
    assert len(text.splitlines()) == 1 and uid in text and "pkg/jobs.py:L" in text
    assert full not in text and "Extra body" not in text and "match: explain" in text
    assert cli.main(["find", "--run-dir", str(run), "--term", "needle", "--json", "--limit", "1"]) == 0
    results = json.loads(capsys.readouterr().out)
    assert len(results) == 1
    assert set(results[0]) == {"id", "name", "kind", "location", "summary", "matched_fields"}
    assert len(results[0]["summary"].split()) <= 25
    assert results[0]["matched_fields"] == ["explain"]
    assert full in docs.query(run, uid)["explain"]
    assert docs.find(run, "needle", limit=0) == []
    assert docs.find(run, "no such match") == []


def test_legacy_catalog_find_has_the_same_locator_contract(tmp_path):
    run, ids, _, _, _ = _run(tmp_path)
    path = run / "catalog.json"
    catalog = json.loads(path.read_text())
    uid = ids[0]
    # Simulate a legacy compatibility entry without ranges or kind.
    catalog["symbols"][uid] = {"file": "pkg/jobs.py", "name": uid}
    path.write_text(json.dumps(catalog))
    row = next(r for r in docs.find(run, uid) if r["id"] == uid)
    assert row["kind"] != "symbol" and row["location"].startswith("pkg/jobs.py:L")
    assert "::" not in row["name"]
    assert not {"explain", "incoming", "outgoing", "signatures"} & row.keys()


def test_each_unit_source_link_resolves_and_file_target_is_shared(tmp_path):
    run, ids, units, inventory, _ = _run(tmp_path)
    page = run / "docs/nodes/root.md"
    text = page.read_text()
    definitions = dict(re.findall(r"^\[([^\]]+)\]: (.+)$", text, re.MULTILINE))
    assert len(definitions) == 1
    locations = re.findall(r"^`[^\n]+` · \[(pkg/jobs.py:L\d+-L\d+)\]\[([^\]]+)\]$", text, re.MULTILINE)
    assert len(locations) == len(ids)
    for location, ref in locations:
        assert ref in definitions and "#" not in definitions[ref]
        assert (page.parent / definitions[ref]).resolve() == (tmp_path / "repo/pkg/jobs.py").resolve()
        assert (page.parent / definitions[ref]).is_file()
    catalog = json.loads((run / "catalog.json").read_text())
    tree = {"nodes": [{"id": nid, **node} for nid, node in catalog["nodes"].items()]}
    def check():
        return next(c for c in docs.verify(run, inventory, units, catalog["dispositions"], tree)
                    if c["check"] == "relative_links_resolve")
    assert check()["ok"]
    literal = "\nself.error_handler_spec[name][c] and table[None][code][exc_class].\n" \
              "`handlers[x][f999]`\n\n```py\nvalue[a][f998]\n[f997]: missing-example.py\n```\n"
    page.write_text(text + literal)
    assert check()["ok"]
    page.write_text(text.replace("][f1]", "][f999]"))
    assert not check()["ok"]
    page.write_text(text.replace(definitions["f1"], "missing-source.py"))
    assert not check()["ok"]


def test_query_text_formats_multiple_ranges_while_json_keeps_structured_ranges(tmp_path, capsys):
    run, ids, _, _, _ = _run(tmp_path)
    path = run / "catalog.json"
    catalog = json.loads(path.read_text())
    ranges = [{"path": "pkg/jobs.py", "lines": [[1, 2], [4, 5]]}]
    catalog["units"][ids[0]]["ranges"] = ranges
    path.write_text(json.dumps(catalog))
    assert cli.main(["query", "--run-dir", str(run), "--id", ids[0]]) == 0
    text = capsys.readouterr().out
    assert "ranges: pkg/jobs.py:L1-L2, pkg/jobs.py:L4-L5" in text
    assert 'ranges: {"path"' not in text
    assert cli.main(["query", "--run-dir", str(run), "--id", ids[0], "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ranges"] == ranges
    assert cli.main(["query", "--run-dir", str(run), "--id", "pkg/jobs.py"]) == 0
    text = capsys.readouterr().out
    assert "units:" in text and "pkg/jobs.py:L1-L2, pkg/jobs.py:L4-L5" in text
    assert '"lines"' not in text
