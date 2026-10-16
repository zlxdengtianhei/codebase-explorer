"""Quality contract: deterministic audit, persisted build, legacy readers, INDEX."""
import copy
import json
from pathlib import Path

import pytest

from cbe import cli, docs, graph
from cbe.source_context import build_context
from test_host_run import _repo, _drive, _graph_for
from cbe import host_run


def bad_graph():
    return {"schema": "cbe-graph/1", "backend": {"name": "test", "components": [{"name": "test"}]},
            "source_manifest": [{"path": "main.py", "language": "python"},
                                {"path": "gone.py", "language": "python"}],
            "nodes": [{"id": "a", "path": "main.py"}, {"id": "b", "path": "gone.py"},
                      {"id": "c", "path": "../outside.py"}, {"id": "ext", "path": None}],
            "edges": [{"id": "e1", "source": "a", "target": "b", "path": "main.py",
                       "kind": "import", "status": "resolved"},
                      {"id": "e2", "source": "a", "target": "missing", "path": "main.py",
                       "kind": "call", "status": "unresolved"},
                      {"id": "e3", "source": "a", "target": None, "path": "main.py",
                       "kind": "call", "status": "external"}],
            "capabilities": [{"language": "python", "graph": "call", "status": "partial"},
                             {"language": "ruby", "graph": "cfg", "status": "failed"}],
            "diagnostics": [{"code": "frontend_error", "language": "ruby", "message": "ruby failed"}]}


def test_quality_bad_graph_and_purity():
    value = bad_graph()
    original = copy.deepcopy(value)
    quality = graph.graph_quality(value, existing_paths={"main.py"})
    assert value == original
    assert quality["dangling_edges"] == {"count": 1, "examples": [{"id": "e2", "missing_endpoints": ["missing"]}]}
    assert quality["nodes_outside_manifest"] == {"count": 1, "examples": ["c"]}
    assert quality["nodes_missing_files"] == {"count": 2, "examples": ["b", "c"]}
    rows = {(r["language"], r["kind"]): r for r in quality["edge_counts"]}
    assert rows["python", "import"]["statuses"]["resolved"] == 1
    assert rows["python", "call"]["statuses"] == dict(resolved=0, ambiguous=0, unresolved=1, external=1, unsupported=0)
    assert rows["ruby", "cfg"]["total"] == 0
    assert quality["incomplete_capabilities"] == value["capabilities"]
    assert quality["backend_completed"] and not quality["empty_graph"]
    assert graph.graph_quality(value)["nodes_missing_files"]["count"] is None


def test_distribution_preserves_every_status_and_source_language():
    value = bad_graph()
    value["source_manifest"].append({"path": "target.rb", "language": "ruby"})
    value["nodes"].append({"id": "ruby_target", "path": "target.rb"})
    statuses = ("resolved", "ambiguous", "unresolved", "external", "unsupported")
    value["edges"] = [dict(id=f"e{i}", source="a", target="ruby_target", kind="call", status=status)
                      for i, status in enumerate(statuses)]
    rows = {(r["language"], r["kind"]): r for r in graph.graph_quality(value)["edge_counts"]}
    assert rows["python", "call"]["statuses"] == dict.fromkeys(statuses, 1)
    assert rows["python", "call"]["total"] == 5
    assert rows["ruby", "call"]["total"] == 0


def test_empty_success_differs_from_failed():
    value = {"nodes": [], "edges": [], "capabilities": [{"language": "python", "graph": "import", "status": "empty"}]}
    assert graph.graph_quality(value)["empty_graph"]
    assert graph.graph_quality(value)["backend_completed"] is True
    value["diagnostics"] = [{"code": "no_backend_completed"}]
    assert graph.graph_quality(value)["backend_completed"] is False


def test_cli_build_warns_and_emits_quality(tmp_path, monkeypatch, capsys):
    value = bad_graph()
    monkeypatch.setattr(graph, "analyze_graph", lambda *a, **kw: value)
    assert cli.main(["graph", "build", str(tmp_path), "--output", str(tmp_path / "graph.json")]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out)["quality"]["dangling_edges"]["count"] == 1
    assert "dangling edges: 1" in output.err and "ruby failed" in output.err


def test_build_persists_quality(tmp_path, monkeypatch):
    from cbe import graph_backends
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("pass\n")
    monkeypatch.setattr(graph_backends, "build_with_grimp", lambda *a: {
        "backend": {"name": "grimp"}, "nodes": [{"id": "a", "path": "main.py"}],
        "edges": [], "diagnostics": [], "capabilities": [
            {"language": "python", "graph": "import", "status": "empty"}]})
    output = tmp_path / "graph.json"
    result = graph.analyze_graph(repo, output, backend="imports")
    assert json.loads(output.read_text())["quality"] == result["quality"]
    assert result["quality"]["file_existence_checked"]
    assert result["quality"]["nodes_missing_files"]["count"] == 0


def test_failed_build_keeps_auditable_quality_and_nonzero_exit(tmp_path, monkeypatch, capsys):
    from cbe import graph_backends
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("pass\n")
    monkeypatch.setattr(graph_backends, "build_with_grimp", lambda *a: {
        "nodes": [], "edges": [],
        "diagnostics": [{"code": "frontend_error", "message": "frontend failed"}],
        "capabilities": [{"language": "python", "graph": "import", "status": "failed"}]})
    path = tmp_path / "graph.json"
    assert cli.main(["graph", "build", str(repo), "--backend", "imports", "--output", str(path)]) == 2
    output = capsys.readouterr()
    quality = json.loads(output.out)["quality"]
    assert quality == json.loads(path.read_text())["quality"]
    assert quality["empty_graph"] and quality["backend_completed"] is False
    assert "frontend failed" in output.err and "no graph backend completed" in output.err


def test_legacy_graph_readers(tmp_path, capsys):
    value = bad_graph()
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(value))
    assert cli.main(["graph", "capabilities", "--graph", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["quality"] == graph.graph_quality(value)
    assert graph.query_graph(value)["quality"] == graph.graph_quality(value)
    (tmp_path / "main.py").write_text("pass\n")
    assert cli.main(["graph", "capabilities", "--graph", str(path), "--repo", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["quality"]["nodes_missing_files"]["count"] == 2
    repo = _repo(tmp_path)
    path.write_text(json.dumps(_graph_for(repo, ["src/pkg/jobs.py"])))
    original = json.loads(path.read_text())
    context = build_context(repo, graph_path=path)
    assert context["graph"] == original and "quality" not in context["graph"]
    run = Path(host_run.plan(repo, tmp_path / "run", graph_path=path, review="none")["run_dir"])
    frozen = json.loads((run / "host/state.json").read_text())["context"]
    assert frozen["graph_digest"] == host_run.context_digest(original)
    host_run.resume(run, graph_path=path)
    _drive(run)
    index = (run / "docs/INDEX.md").read_text()
    assert "## 图覆盖" in index and "python" in index and "resolved" in index
    assert "仅靠模型阅读源码" in index


@pytest.mark.parametrize("mode", ["missing", "failed", "partial"])
def test_index_coverage_without_successful_graph(tmp_path, mode):
    value = None if mode == "missing" else bad_graph()
    if mode == "failed":
        value["diagnostics"].append({"code": "no_backend_completed"})
    docs.render(run_dir=tmp_path, source_root=tmp_path, inventory={}, units={}, dispositions={},
                tree={"nodes": []}, languages={}, graph=value)
    index = (tmp_path / "docs/INDEX.md").read_text()
    assert "## 图覆盖" in index and "仅靠模型阅读源码" in index
    if mode == "missing":
        assert "未提供图" in index
    elif mode == "failed":
        assert "没有后端跑成" in index
    else:
        assert "python import: resolved 1/1 (100%)" in index and "ruby/cfg failed" in index
        assert "悬空边 1" in index
