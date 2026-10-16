"""Observable O5 contracts: graph input, bounded tasks, composition and diagnostics."""
import json
from pathlib import Path

import pytest

from cbe import aggregation, checks, host_run, principles, prompts, source_context
from cbe.symbols import inventory_from_context
from cbe.token_budget import count_text_tokens
from test_host_run import _answer, _drive, _repo


def test_tree_receives_summaries_and_counted_resolved_edges(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("def a():\n    b()\n    b()\n\ndef b():\n    return 3\n")
    (repo / "c.py").write_text("def c():\n    return 4\n")
    context = source_context.build_context(repo)
    inventory = inventory_from_context(context)
    syms = [symbol for row in inventory.values() for symbol in row["symbols"]]
    a = next(s["id"] for s in syms if s["name"] == "a")
    b = next(s["id"] for s in syms if s["name"] == "b")
    units = {s["id"]: {"id": s["id"], "kind": s["kind"],
              "explain": "First sentence. SECRET complete explanation.", "summary": "Owns a capability."} for s in syms}
    dispositions = {uid: {"how": "unit", "unit": uid} for uid in units}
    context["graph"] = {"nodes": [
        {"id": "ga", "kind": "method", "path": "a.py", "start_line": 1},
        {"id": "gb", "kind": "method", "path": "a.py", "start_line": 5},
        {"id": "fa", "kind": "file", "path": "a.py"},
        {"id": "fc", "kind": "file", "path": "c.py"}],
        "edges": [{"id": "file-import", "source": "fa", "target": "fc", "kind": "import", "status": "resolved"}]
        + [{"id": str(i), "source": "ga", "target": "gb", "kind": "call",
                   "path": "a.py", "line": line, "status": status}
                  for i, (line, status) in enumerate([(2, "resolved"), (3, "resolved"), (2, "ambiguous")])]}
    units[a]["relations"] = [{"target": b, "kind": "use", "basis": "dynamic dispatch"}]
    records, edges = aggregation.inputs(units, dispositions, inventory, context)
    assert edges == [{"from": a, "to": b, "kind": "call", "count": 2},
                     {"from": a, "to": b, "kind": "relation", "count": 1, "provenance": "model_inferred"}]
    prompt = prompts.tree_prompt(records, ["a.py"], edges)
    assert "SECRET" not in prompt and "Owns a capability." in prompt
    assert '"count": 2' in prompt and '"kind": "call"' in prompt
    assert '"path": "a.py"' in prompt


@pytest.mark.parametrize("review,decision", [("none", "accepted"), ("all", "needs_repair")])
def test_partitioned_host_keeps_unique_homes_and_subtree_content(tmp_path, monkeypatch, review, decision):
    monkeypatch.setenv("CBE_TREE_MAX_UNITS", "2")
    repo = _repo(tmp_path)
    run = Path(host_run.plan(repo, tmp_path / "run", review=review, jobs=8)["run_dir"])
    handed = _drive(run, decision=decision)
    regions = [tid for tid in handed if tid.startswith("tree_region-")]
    assert len(regions) >= 2 and handed.index("tree") > max(handed.index(tid) for tid in regions)
    if review == "all":
        assert max(handed.index(tid) for tid in handed if tid.startswith("repair_")) < min(handed.index(tid) for tid in regions)
    state = json.loads((run / "host/state.json").read_text())
    for region in state["aggregation"]["regions"]:
        assert region["unit_ids"]
        prompt = host_run.completion_prompt(run, "tree_" + region["id"])
        assert count_text_tokens(prompt) <= state["aggregation"]["limits"]["max_tokens"]
        assert count_text_tokens(prompt) == region["input_tokens"]
    upper_prompt = host_run.completion_prompt(run, "tree")
    assert "MERGE:" in upper_prompt and '"top_nodes"' in upper_prompt
    catalog = json.loads((run / "catalog.json").read_text())
    assert set(catalog["units"]) == {uid for r in state["aggregation"]["regions"] for uid in r["unit_ids"]}
    assert all(row.get("node", "").startswith("r") for row in catalog["units"].values())
    assert host_run.verify(run)["ok"]
    assert (run / "docs/INDEX.md").is_file() and list((run / "docs/nodes").glob("r*-*.md"))
    host_run.render(run)
    summary = json.loads((run / "summary.json").read_text())
    assert summary["aggregation_principles"]["checks"][-1]["status"] == "re-render identical"
    assert summary["aggregation_principles"]["checks"][-1]["ok"] is None
    index = (run / "docs/INDEX.md").read_text()
    assert "## Aggregation principle checks" in index
    assert all(f'"principle": "P{i}"' in index for i in range(1, 8))


def test_small_host_keeps_one_tree(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    handed = _drive(run)
    assert [t for t in handed if t.startswith("tree")] == ["tree"]
    report = json.loads((run / "summary.json").read_text())["aggregation_principles"]
    assert len(report["checks"]) == 7


def test_principles_report_counterexamples_and_replay_identity(monkeypatch):
    units = {"a": {"explain": "Detail " * 100, "ranges": [{"path": "a.py"}]},
             "b": {"explain": "Detail " * 100, "ranges": [{"path": "b.js"}]},
             "shared": {"explain": "Detail " * 100, "ranges": [{"path": "util.py"}]}}
    def node(nid, ids, capability):
        return {"id": nid, "parent": None if nid == "root" else "root", "title": nid,
                "unit_ids": ids, "capability": capability, "summary": "Use this capability."}
    tree = {"nodes": [node("root", [], "Contains the shared capabilities."),
                       node("one", ["a"], "First capability."), node("two", ["b"], "Second capability."),
                       node("infra", ["shared"], "Shared infrastructure.")]}
    edges = [{"from": uid, "to": "shared", "kind": "call", "count": 4} for uid in ("a", "b")]
    langs = {"a.py": "python", "b.js": "javascript", "util.py": "python"}
    first = principles.report(tree, units, edges, langs)
    rows = {r["principle"]: r for r in first["checks"]}
    assert rows["P1"]["ok"] and rows["P4"]["ok"]
    assert rows["P2"]["modules"]["one"] == {"internal": 0, "external": 4, "internal_external_ratio": 0.0}
    assert rows["P3"]["out_of_bounds"] == {"one": 1, "two": 1, "infra": 1}
    assert rows["P5"]["shared_units"] == {"shared": {"one": 4, "two": 4}}
    assert rows["P6"]["modules"]["two"] == {"javascript": 1}
    assert rows["P7"]["ok"] is None
    assert principles.report(tree, units, edges, langs, first)["checks"][-1]["ok"]
    changed_graph = principles.report(tree, units, [], langs, first)
    assert changed_graph["checks"][-1]["status"] == "not_checked"
    tree["nodes"][1]["title"] = "Changed"
    tree["nodes"][1]["capability"] = "Second capability."
    tree["nodes"][1]["unit_ids"].append("b")
    bad = principles.report(tree, units, edges, langs, first)
    assert not bad["checks"][0]["ok"] and not bad["checks"][3]["ok"] and not bad["checks"][-1]["ok"]
    assert bad["hierarchy"]["ok"]
    monkeypatch.setenv("CBE_TREE_MIN_GRAIN", "1")
    assert "Aim for 1–30 units" in prompts.tree_prompt({}, [])
    assert principles.report({"nodes": tree["nodes"][:1]}, {}, [], {})["introduction_length"]["overlong"]


def test_file_imports_guide_regions_without_inventing_unit_edges():
    units = {uid: {"id": uid, "summary": "A responsibility.", "ranges": [{"path": f"pkg/{uid}.py"}]}
             for uid in ("a", "b", "c")}
    context = {"graph": {"nodes": [{"id": uid, "path": f"pkg/{uid}.py"} for uid in units],
                         "edges": [{"source": "b", "target": "c", "kind": "import", "status": "resolved"}]}}
    render = lambda rows, edges: prompts.tree_prompt(rows, [], edges)
    regions = aggregation.partition(units, [], aggregation.Limits(max_units=2), render, context=context)
    assert [r["unit_ids"] for r in regions] == [["a"], ["b", "c"]]


def test_hierarchy_and_introduction_checks_detect_flat_overlong_tree():
    units = {f"u{i}": {"explain": "Detail " * 30} for i in range(31)}
    root = {"id": "root", "parent": None, "title": "Root", "unit_ids": [],
            "capability": "Repository capability.", "summary": "Start here."}
    leaf = {"id": "leaf", "parent": "root", "title": "Leaf", "unit_ids": list(units),
            "capability": "Leaf capability.", "summary": "Summary " * 1000}
    bad = principles.report({"nodes": [root, leaf]}, units, [], {})
    assert not bad["hierarchy"]["ok"] and not bad["introduction_length"]["ok"]
    leaf["summary"] = "Open units."
    leaf["parent"] = "middle"
    middle = {**root, "id": "middle", "parent": "root", "title": "Middle"}
    good = principles.report({"nodes": [root, middle, leaf]}, units, [], {})
    assert good["hierarchy"]["ok"] and good["introduction_length"]["ok"]


def test_merge_rejects_id_collision_instead_of_losing_subtree_units():
    sub = {"nodes": [{"id": "root", "parent": None, "unit_ids": ["u"]}], "depends_on": []}
    upper = {"nodes": [{"id": "r1-root", "parent": None, "unit_ids": ["region-0001"]}]}
    with pytest.raises(ValueError, match="collides"):
        aggregation.compose(upper, {"region-0001": sub})


def test_summary_budget_splits_and_oversize_single_unit_fails():
    import pytest
    units = {f"u{i}": {"id": f"u{i}", "summary": "Describe capability " * 20,
                       "ranges": [{"path": f"pkg/{i}.py"}]} for i in range(8)}
    render = lambda rows, edges: prompts.tree_prompt(rows, [], edges)
    one = count_text_tokens(render({"u0": units["u0"]}, []))
    regions = aggregation.partition(units, [], aggregation.Limits(max_units=100, max_tokens=one + 10), render)
    assert len(regions) == 8
    assert all(r["input_tokens"] <= one + 10 for r in regions)
    with pytest.raises(ValueError, match="token budget"):
        aggregation.partition(units, [], aggregation.Limits(max_tokens=1), render)
