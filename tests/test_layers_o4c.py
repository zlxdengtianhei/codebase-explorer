"""O4c public behavior: locate, follow a source link, and read source coordinates."""
import json
import re
from pathlib import Path

from cbe import cli, docs, catalog_query
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
    assert full in catalog_query.query(run, uid)["explain"]
    assert catalog_query.find(run, "needle", limit=0) == []
    assert catalog_query.find(run, "no such match") == []


def test_each_unit_locates_its_source_without_a_link_on_the_page(tmp_path):
    run, ids, units, inventory, _ = _run(tmp_path)
    page = (run / "docs/nodes/root.md").read_text()
    assert "<a id=" not in page and "[f1]:" not in page and "pkg/jobs.py:L" not in page
    catalog = json.loads((run / "catalog.json").read_text())
    tree = {"nodes": [{"id": nid, **node} for nid, node in catalog["nodes"].items()]}
    def check():
        return next(c for c in docs.verify(run, inventory, units, catalog["dispositions"], tree)
                    if c["check"] == "relative_links_resolve")
    assert check()["ok"]
    for uid in ids:
        record = catalog_query.query(run, uid)
        assert record["ranges"] and record["page"]
        assert "def reserve" in catalog_query.source(run, uid) or "class Pool" in catalog_query.source(run, uid) \
            or "def submit" in catalog_query.source(run, uid)
    page_text = page + "\n[broken generated navigation](missing-page.md)\n"
    (run / "docs/nodes/root.md").write_text(page_text)
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
