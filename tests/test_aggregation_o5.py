"""Observable contracts of the tree inputs: unit edges, the naming prompts, the tree tasks and the diagnostics."""
import json
import re
from pathlib import Path

import pytest

from cbe import aggregation, host_run, principles, source_context, treename
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
    tree = treename.Tree(treename.freeze(records, edges)["nodes"])
    block = "\n".join(treename.name_blocks(tree.leaves(), tree, records, edges))
    assert "SECRET" not in block and "Owns a capability." in block
    assert "file a.py" in block


def test_small_host_keeps_one_tree(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    handed = _drive(run)
    assert [t for t in handed if t.startswith("tree")] == ["tree_name_1"]
    report = json.loads((run / "summary.json").read_text())["aggregation_principles"]
    assert len(report["checks"]) == 6


@pytest.mark.parametrize("failed_module", [False, True], ids=["repair", "failed-module"])
def test_single_tree_waits_for_review_and_repair(tmp_path, failed_module):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="all", jobs=8)["run_dir"])

    def submit(item, answer):
        Path(item["output_file"]).write_text(json.dumps(answer))
        return host_run.submit(run, item["task"])

    first = host_run.next_tasks(run)["tasks"]
    failed_id = next(item["task"] for item in first if item["kind"] == "module") if failed_module else None
    for item in first:
        prompt = Path(item["prompt_file"]).read_text()
        result = submit(item, {} if item["task"] == failed_id else _answer(item, prompt))
        assert result["accepted"] == (item["task"] != failed_id)
    reviews = []
    for item in host_run.next_tasks(run)["tasks"]:
        assert item["kind"] in {"module", "review"}  # no tree before reviews
        if item["task"] == failed_id:
            assert submit(item, {})["task_status"] == "pending"
        else:
            reviews.append(item)
    if failed_id:
        # Exhaust the third detail answer before checking the existing failure path.
        final_retry = host_run.next_tasks(run)["tasks"]
        assert [item["task"] for item in final_retry] == [failed_id]
        assert submit(final_retry[0], {})["task_status"] == "failed"
    assert reviews
    for item in reviews:
        assert submit(item, {"decision": "needs_repair", "issues": ["Replace stale unit descriptions."]})["accepted"]
    repairs = host_run.next_tasks(run)["tasks"]
    assert repairs and all(item["kind"] == "repair" for item in repairs)
    assert host_run.next_tasks(run)["tasks"] == []  # repairs are still leased
    repaired_ids = []
    for item in repairs:
        answer = _answer(item, Path(item["prompt_file"]).read_text())
        for unit in answer["units"]:  # the first explain sentence is the published summary
            unit["explain"] = "Repaired capability ready for aggregation. " + unit["explain"]
        assert submit(item, answer)["accepted"]
        accepted = json.loads((run / "host" / "accepted" / f"{item['task']}.json").read_text())
        repaired_ids += [unit["id"] for unit in accepted["units"]]
    tree = host_run.next_tasks(run)["tasks"]
    assert [item["task"] for item in tree] == ["tree_name_1"]
    prompt = Path(tree[0]["prompt_file"]).read_text()
    assert prompt.count("Repaired capability ready for aggregation.") == len(repaired_ids)
    assert submit(tree[0], _answer(tree[0], prompt))["accepted"]
    assert _drive(run) == ["system"]
    state = json.loads((run / "host/state.json").read_text())
    assert state["status"] == ("partial" if failed_module else "complete")


def test_principles_report_counterexamples():
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
    tree["nodes"][1]["title"] = "Changed"
    tree["nodes"][1]["capability"] = "Second capability."
    tree["nodes"][1]["unit_ids"].append("b")
    bad = principles.report(tree, units, edges, langs)
    assert not bad["checks"][0]["ok"] and not bad["checks"][3]["ok"]
    assert bad["hierarchy"]["ok"]
    assert principles.report({"nodes": tree["nodes"][:1]}, {}, [], {})["introduction_length"]["overlong"]


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
