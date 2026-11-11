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
    assert [c["principle"] for c in report["checks"]] == ["P2", "P3"]


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


def test_principles_report_cohesion_and_granularity_readings():
    def node(nid, ids):
        return {"id": nid, "parent": None if nid == "root" else "root", "title": nid, "unit_ids": ids}
    tree = {"nodes": [node("root", []), node("one", ["a"]), node("two", ["b"]), node("infra", ["shared"])]}
    edges = [{"from": uid, "to": "shared", "kind": "call", "count": 4} for uid in ("a", "b")]
    rows = {r["principle"]: r for r in principles.report(tree, edges)["checks"]}
    assert set(rows) == {"P2", "P3"}
    assert rows["P2"]["modules"]["one"] == {"internal": 0, "external": 4, "internal_external_ratio": 0.0}
    assert not rows["P2"]["ok"]
    assert rows["P3"]["out_of_bounds"] == {"one": 1, "two": 1, "infra": 1}



def test_introduction_length_reads_each_module_against_the_explanations_under_it():
    nodes = [{"id": "root", "parent": None, "capability": "c" * 10, "summary": "", "unit_ids": []},
             {"id": "short", "parent": "root", "capability": "c" * 10, "summary": "s" * 10, "unit_ids": ["u1"]},
             {"id": "long", "parent": "root", "capability": "c" * 30, "summary": "s" * 30, "unit_ids": ["u2"]}]
    units = {"u1": {"explain": "e" * 40}, "u2": {"explain": "e" * 20}}
    reading = principles.report({"nodes": nodes}, [], units)["introduction_length"]
    assert reading["ok"] is False and list(reading["overlong"]) == ["long"]
    assert reading["overlong"]["long"] == {"introduction_chars": 60, "detail_chars": 20}
    assert reading["max_ratio"] == 3.0
    assert "introduction_length" not in principles.report({"nodes": nodes}, [])
