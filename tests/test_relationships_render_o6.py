"""Graph-derived dependencies are published outside the reading path (design 2.4)."""
from __future__ import annotations

import json

from cbe import docs


def _run(tmp_path):
    from test_semantic import SRC, _inventory, _good_payload

    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg/jobs.py").write_text(SRC)
    inventory = _inventory()
    payload = _good_payload(inventory)
    units = {u["id"]: u for u in payload["units"]}
    a = "pkg/jobs.py::Pool.submit"
    tree = {"nodes": [dict(id="top", parent=None, title="Top", unit_ids=[]),
                      dict(id="root", parent="top", title="Submit", unit_ids=[a]),
                      dict(id="helper", parent="top", title="Reserve",
                           unit_ids=sorted(set(units) - {a}))],
            "depends_on": []}
    evidence = {"schema": "cbe-graph/1", "nodes": [
        dict(id="submit", path="pkg/jobs.py", start_line=11, kind="method"),
        dict(id="reserve", path="pkg/jobs.py", start_line=5, kind="method")],
        "edges": [dict(id="call", kind="call", status="resolved", source="submit", target="reserve",
                       path="pkg/jobs.py", line=12, column=16)]}
    from cbe.graph import graph_quality
    evidence["quality"] = graph_quality(evidence)
    run = tmp_path / "run"
    meta = docs.render(run_dir=run, source_root=repo, inventory=inventory, units=units,
                       dispositions=payload["dispositions"], tree=tree,
                       languages={"pkg/jobs.py": "python"}, graph=evidence,
                       overview={"overview": "A small pool."})
    return run, meta


def test_dependencies_page_lists_the_graph_edge_and_pages_stay_prose_only(tmp_path):
    run, meta = _run(tmp_path)
    dependencies = (run / "docs" / "DEPENDENCIES.md").read_text()
    assert "Dependencies" in dependencies and "graph" in dependencies.lower()
    for page in (run / "docs" / "nodes").glob("*.md"):
        text = page.read_text()
        assert '<a id=' not in text and "[f1]:" not in text
        assert "calls:" not in text and "uses:" not in text
        assert "Look up code:" not in text
    assert "cbe find" in (run / "docs" / "INDEX.md").read_text()


def test_catalog_keeps_the_node_dependency_edges(tmp_path):
    run, _ = _run(tmp_path)
    catalog = json.loads((run / "catalog.json").read_text())
    assert "node_dependencies" in catalog and "key_flows" not in catalog
