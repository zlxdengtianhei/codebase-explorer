"""C4 counterexamples exercised through published pages, queries and checks."""
import json
import re

import pytest

from cbe import cli, docs, source_context
from cbe.symbols import inventory_from_context
from test_layers_o4 import _run


def test_edges_obey_exclusive_ownership_at_shared_boundary(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    text = "class MethodView:\n    marker = 1\n\n    def __init_subclass__(cls):\n        return cls\n"
    (repo / "views.py").write_text(text)
    context = source_context.build_context(repo)
    inventory = inventory_from_context(context)
    symbols = inventory["views.py"]["symbols"]
    units = {s["id"]: {"id": s["id"], "kind": s["kind"], "explain": "First. Complete explanation."}
             for s in symbols}
    parent = next(s for s in symbols if s["name"] == "MethodView")
    child = next(s for s in symbols if s["name"] == "__init_subclass__")
    assert parent["lines"][-1][-1] == child["lines"][0][0]
    nodes = [{"id": s["id"], "path": "views.py", "start_line": s["lines"][0][0]}
             for s in (parent, child)]
    graph = {"nodes": nodes, "edges": [
        {"id": f"{i}-{kind}", "kind": kind, "source": s["id"], "target": s["id"]}
        for i, s in enumerate((parent, child)) for kind in ("cfg", "dataflow")]}
    context["graph"] = graph
    run = tmp_path / "run"
    run.mkdir()
    (run / "context.json").write_text(json.dumps(context))
    docs.render(run_dir=run, source_root=repo, inventory=inventory, units=units,
                dispositions={uid: {"how": "unit", "unit": uid} for uid in units},
                tree={"nodes": [{"id": "root", "unit_ids": list(units)}]},
                languages={"views.py": "python"}, context=context, graph=graph)
    for uid in units:
        record = docs.query(run, uid, edges="cfg,dataflow")
        for kind in ("cfg", "dataflow"):
            assert sum(e["kind"] == kind for e in record["raw_edges"]) == record["internal_edge_counts"][kind]
    assert [e["id"] for e in docs.query(run, parent["id"], edges="cfg")["raw_edges"]] == ["0-cfg"]
    assert cli.main(["query", "--run-dir", str(run), "--id", parent["id"], "--edges", "cfgg"]) == 2
    assert "--edges" in capsys.readouterr().err
