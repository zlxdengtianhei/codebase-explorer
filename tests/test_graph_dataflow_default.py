"""Dataflow is exported only on request; a user-named Joern location must be valid."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import pytest

from cbe import cli, docs, source_context, catalog_query
from cbe.graph import NO_DATAFLOW_MESSAGE, built_without_dataflow, graph_quality, query_graph
from cbe.graph_backends import joern
from cbe.graph_backends.joern import _normalize
from cbe.symbols import inventory_from_context

CASES = Path(__file__).parent / "fixtures" / "graphs" / "cases"
LANGUAGES = ["c", "cpp", "go", "java", "python", "ruby", "typescript"]


def _raw(language: str) -> dict:
    return json.loads((CASES / language / "raw.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("language", LANGUAGES)
def test_normalization_is_right_with_and_without_dataflow_input(language):
    with_flow = _raw(language)
    without = copy.deepcopy(with_flow)
    without.update(reachingDefs=[], dataflowPaths=[], dataflowRequested=False)
    _, edges_with = _normalize(with_flow, "t", diagnostics=[])
    _, edges_without = _normalize(without, "t", diagnostics=[])
    assert not [e for e in edges_without if e["kind"] == "dataflow"]
    # Nothing else changes when dataflow is left out.
    assert [e for e in edges_with if e["kind"] != "dataflow"] == edges_without
    caps = {c["graph"]: c for c in joern._capabilities_for(language, without, "t")}
    assert caps["dataflow"]["status"] == "not_requested"
    assert "--with-dataflow" in caps["dataflow"]["limitations"]
    assert caps["call"]["status"] == {c["graph"]: c for c in joern._capabilities_for(language, with_flow, "t")}["call"]["status"]
    # A recorded export that predates the flag still reads as requested.
    assert {c["graph"]: c for c in joern._capabilities_for(language, with_flow, "t")}["dataflow"]["status"] != "not_requested"


def _fake_joern(tmp_path, monkeypatch):
    home = tmp_path / "joern"
    home.mkdir()
    for name in ("joern", "joern-parse"):
        (home / name).touch()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("def run(): pass\n")
    exports = []

    def run(argv, timeout, cwd, *, env=None):
        if "--version" in argv:
            return subprocess.CompletedProcess(argv, 0, "Version: 1", "")
        if "--language" in argv:
            Path(argv[argv.index("-o") + 1]).touch()
        if "--script" in argv:
            params = dict(a.split("=", 1) for a in argv if "=" in a)
            exports.append(params)
            payload = _raw("python")
            if params["withDataflow"] == "0":
                payload.update(reachingDefs=[], dataflowPaths=[], dataflowRequested=False)
            Path(params["outFile"]).write_text(json.dumps(payload))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(joern, "_run", run)
    from cbe import graph_backends
    monkeypatch.setattr(graph_backends, "find_java", lambda *a, **k: None)
    return home, repo, exports


@pytest.mark.parametrize("extra,expected", [
    ([], "0"), (["--with-dataflow"], "1"), (["--max-reaching-defs", "7"], "1"),
    (["--dataflow-path-method", "run"], "1")])
def test_dataflow_is_exported_only_when_asked(tmp_path, monkeypatch, capsys, extra, expected):
    home, repo, exports = _fake_joern(tmp_path, monkeypatch)
    output = tmp_path / "g.json"
    code = cli.main(["graph", "build", str(repo), "--backend", "joern", "--language", "python",
                     "--joern-home", str(home), "--output", str(output)] + extra)
    assert code == 0
    assert exports[0]["withDataflow"] == expected
    graph = json.loads(output.read_text())
    status = next(c["status"] for c in graph["capabilities"] if c["graph"] == "dataflow")
    has_edges = any(e["kind"] == "dataflow" for e in graph["edges"])
    if expected == "0":
        assert status == "not_requested" and not has_edges and built_without_dataflow(graph)
        assert not any(row["kind"] == "dataflow" for row in graph["quality"]["edge_counts"])
        assert not any(c["graph"] == "dataflow" for c in graph["quality"]["incomplete_capabilities"])
        assert graph["quality"]["backend_completed"] is True
    else:
        assert status != "not_requested" and has_edges and not built_without_dataflow(graph)
        assert any(row["kind"] == "dataflow" for row in graph["quality"]["edge_counts"])
    capsys.readouterr()


def test_graph_query_for_dataflow_says_how_to_rebuild(tmp_path, monkeypatch, capsys):
    home, repo, _ = _fake_joern(tmp_path, monkeypatch)
    plain, flow = tmp_path / "plain.json", tmp_path / "flow.json"
    base = ["graph", "build", str(repo), "--backend", "joern", "--language", "python", "--joern-home", str(home)]
    assert cli.main(base + ["--output", str(plain)]) == 0
    assert cli.main(base + ["--output", str(flow), "--with-dataflow"]) == 0
    capsys.readouterr()
    assert cli.main(["graph", "query", "--graph", str(plain), "--kind", "dataflow"]) == 2
    assert NO_DATAFLOW_MESSAGE in capsys.readouterr().err
    assert "rebuild with `cbe graph build --with-dataflow`" in NO_DATAFLOW_MESSAGE
    assert cli.main(["graph", "query", "--graph", str(flow), "--kind", "dataflow"]) == 0
    assert json.loads(capsys.readouterr().out)["edges"]
    # Other kinds still work on the graph without dataflow.
    assert query_graph(json.loads(plain.read_text()), kind="cfg")["edges"]


def test_query_edges_and_edge_counts_without_dataflow(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "views.py").write_text("def one():\n    return 1\n\ndef two():\n    return 2\n")
    context = source_context.build_context(repo)
    inventory = inventory_from_context(context)
    symbols = inventory["views.py"]["symbols"]
    units = {s["id"]: {"id": s["id"], "kind": s["kind"], "explain": "First. Complete explanation."} for s in symbols}
    nodes = [{"id": s["id"], "path": "views.py", "start_line": s["lines"][0][0]} for s in symbols]

    def build(graph, name):
        graph["quality"] = graph_quality(graph)
        context["graph"] = graph
        run = tmp_path / name
        run.mkdir()
        (run / "context.json").write_text(json.dumps(context))
        docs.render(run_dir=run, source_root=repo, inventory=inventory, units=units,
                    dispositions={uid: {"how": "unit", "unit": uid} for uid in units},
                    tree={"nodes": [{"id": "root", "unit_ids": list(units)}]},
                    languages={"views.py": "python"}, context=context, graph=graph)
        return run

    edges = [{"id": f"{s['id']}-cfg", "kind": "cfg", "source": s["id"], "target": s["id"]} for s in symbols]
    plain = build({"nodes": nodes, "edges": edges,
                   "capabilities": [{"language": "python", "graph": "dataflow", "status": "not_requested"}]}, "plain")
    flow = build({"nodes": nodes, "edges": edges + [{"id": "d", "kind": "dataflow", "source": symbols[0]["id"],
                                                     "target": symbols[0]["id"]}]}, "flow")
    uid = symbols[0]["id"]
    assert catalog_query.query(plain, uid)["internal_edge_counts"] == {"cfg": 1}  # no "dataflow: 0"
    assert catalog_query.query(flow, uid)["internal_edge_counts"] == {"cfg": 1, "dataflow": 1}
    with pytest.raises(docs.SemanticError, match="built without dataflow"):
        catalog_query.query(plain, uid, edges="dataflow")
    assert cli.main(["query", "--run-dir", str(plain), "--id", uid, "--edges", "dataflow"]) == 2
    assert "cbe graph build --with-dataflow" in capsys.readouterr().err
    mixed = catalog_query.query(plain, uid, edges="cfg,dataflow")
    assert [e["kind"] for e in mixed["raw_edges"]] == ["cfg"] and NO_DATAFLOW_MESSAGE in mixed["notice"]
    assert "notice" not in catalog_query.query(flow, uid, edges="cfg,dataflow")
    assert "notice: " + NO_DATAFLOW_MESSAGE in catalog_query.query_text(mixed)
