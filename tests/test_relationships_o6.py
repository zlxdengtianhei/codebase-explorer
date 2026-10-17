"""O6 public behavior: evidence, bounded traversal, retry, pages and query."""
import json
from pathlib import Path

import pytest

from cbe import aggregation, checks, docs, host_run, prompts
from cbe.token_budget import count_text_tokens
from test_host_run import _repo, _good, _answer_task, _graph_for


def graph():
    return {"schema": "cbe-graph/1", "nodes": [{"id": "n"}], "edges": []}


def tree():
    return {"nodes": [dict(id="root", parent=None, title='Root ["<&`', unit_ids=["a", "b"]),
                       dict(id="child", parent="root", title="Child", unit_ids=["c"]),
                       dict(id="other", parent="root", title="Other", unit_ids=["d"])],
            "depends_on": [{"from": "root", "to": "child", "basis": "Uses it."},
                           {"from": "child", "to": "other", "basis": "Assumed."}]}


def edge(a, b, kind="call", count=1):
    return {"from": a, "to": b, "kind": kind, "count": count}


def test_rollup_containment_is_not_dependency_and_omission():
    edges = [edge("a", "b", count=100), edge("a", "c", count=2),
             edge("b", "c", "import", 3), edge("c", "d", "relation", 80),
             edge("d", "a", count=4), edge("d", "c", count=9)]
    result = aggregation.relationship_view(tree(), edges, graph(), graph_only_limit=1)
    rows = result["dependencies"]
    assert [(r["from"], r["to"], r["source"], r["count"]) for r in rows] == [
        ("child", "other", "model_inferred", 0), ("root", "child", "model_inferred", None),
        ("other", "child", "graph_only", 9)]
    assert rows[1]["containment"] and rows[1]["kinds"] == {}
    assert result["graph_only_omitted"] == 0
    assert result["counts"] == dict(graph_confirmed=0, model_inferred=1, graph_only=1)


@pytest.mark.parametrize("evidence", [None, {"schema": "cbe-graph/1", "nodes": [], "edges": [],
                                          "diagnostics": [{"code": "no_backend_completed"}]}])
def test_without_usable_graph_only_model_dependencies(evidence):
    result = aggregation.relationship_view(tree(), [edge("a", "c")], evidence)
    assert {r["source"] for r in result["dependencies"]} == {"model_inferred"}
    assert result["candidate_flows"] == []
    assert result["graph_reason"]


def test_candidates_stable_ranked_bounded_and_cycle_safe():
    edges = [edge("start", "b", count=3), edge("start", "a", count=8), edge("a", "b"),
             edge("b", "a"), edge("b", "end"), edge("second", "end")]
    result = aggregation.candidate_flows(edges, max_depth=3, max_flows=3)
    assert result == [["start", "a", "b"], ["start", "b", "a"], ["start", "b", "end"]]
    assert aggregation.candidate_flows(list(reversed(edges)), max_depth=3, max_flows=3) == result
    assert aggregation.candidate_flows([edge("a", "b"), edge("b", "a")]) == []
    assert aggregation.candidate_flows([edge("a", "b", "import")]) == []


def test_prompt_limits_graph_context_and_exposes_omission():
    view = {"dependencies": [{"from": str(i), "to": "other", "basis": "word " * 500}
                             for i in range(100)],
            "candidate_flows": [["a" * 1000, "b" * 1000] for _ in range(24)]}
    prompt = prompts.system_prompt([], 2000, view)
    context = json.loads(prompt.split("RELATIONSHIPS: ")[1].split("\nNODE SUMMARIES:")[0])
    assert count_text_tokens(json.dumps(context, ensure_ascii=False)) < 12100
    assert context["prompt_omitted"]["dependencies"] > 20
    assert context["candidate_flows"] == []


def answer():
    return dict(overview="Overview.", maintenance_navigation="Open root.",
                dependency_descriptions=[dict(**{"from": "root", "to": "child"}, description="Uses child.")],
                key_flows=[dict(name=f"Flow {i}", description="Connects parts.", steps=["a", "c"])
                           for i in range(3)])


@pytest.mark.parametrize("bad", ["missing", "unknown_unit", "unknown_dependency", "count"])
def test_system_validation_and_last_answer_empty_sections(bad):
    value = answer()
    if bad == "missing":
        del value["key_flows"]
    elif bad == "unknown_unit":
        value["key_flows"][0]["steps"] = ["a", "missing"]
    elif bad == "unknown_dependency":
        value["dependency_descriptions"][0]["to"] = "missing"
    else:
        value["key_flows"] = value["key_flows"][:2]
    options = dict(unit_ids={"a", "c"}, dependencies=[{"from": "root", "to": "child"}], has_candidates=True)
    with pytest.raises(ValueError):
        checks.check_system(value, **options)
    flags = checks.normalize_system(value, 2000, **options)
    assert flags
    if bad in {"unknown_unit", "count"}:
        assert len(value["key_flows"]) == 2
    else:
        assert value["dependency_descriptions" if bad == "unknown_dependency" else "key_flows"] == []


def test_missing_new_fields_reasked_then_normalized_via_host(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    while True:
        item = host_run.next_tasks(run, limit=1)["tasks"][0]
        if item["kind"] == "system":
            break
        assert _answer_task(run, item, _good(item, run))["accepted"]
    old = {"overview": "Overview.", "maintenance_navigation": "Open root."}
    first = _answer_task(run, item, old)
    assert not first["accepted"] and first["task_status"] == "pending"
    item = host_run.next_tasks(run, limit=1)["tasks"][0]
    assert _answer_task(run, item, old)["accepted"]
    accepted = json.loads((run / "host/accepted/system.json").read_text())
    assert accepted["key_flows"] == accepted["dependency_descriptions"] == []
    state = json.loads((run / "host/state.json").read_text())
    assert any("key_flows" in flag for flag in state["tasks"]["system"]["flags"])
    assert "system 未提供关键流程" in (run / "docs/INDEX.md").read_text()
    assert host_run.verify(run)["ok"]


def test_render_query_and_links_with_inferred_flow(tmp_path):
    # Drive a real planned frozen context, assigning each source unit to a node.
    repo = _repo(tmp_path)
    gp = tmp_path / "graph.json"
    gp.write_text(json.dumps(_graph_for(repo, ["src/pkg/jobs.py", "src/pkg/cli.py"])))
    run = Path(host_run.plan(repo, tmp_path / "run", graph_path=gp, review="none")["run_dir"])
    while True:
        item = host_run.next_tasks(run, limit=1)["tasks"][0]
        if item["kind"] == "tree":
            value = _good(item, run)
            ids = value["nodes"][0]["unit_ids"]
            value["nodes"][0]["unit_ids"] = ids[:1]
            value["nodes"][0]["title"] = 'Root ["<&`'
            value["nodes"].append(dict(id="child", parent="root", title="Child", capability="Calls.",
                                       summary="Helpers.", unit_ids=ids[1:]))
            value["depends_on"] = [{"from": "root", "to": "child", "basis": "Uses helper."}]
            assert _answer_task(run, item, value)["accepted"]
        elif item["kind"] == "system":
            # This fixture has no call evidence, so flows are supplied to the
            # renderer directly below to exercise inferred transition display.
            assert _answer_task(run, item, _good(item, run))["accepted"]
            break
        else:
            assert _answer_task(run, item, _good(item, run))["accepted"]
    catalog = json.loads((run / "catalog.json").read_text())
    dep = catalog["node_dependencies"][0]
    assert dep["source"] == "model_inferred" and dep["description"] == "Uses its service."
    assert dep["containment"] and dep["count"] is None
    assert docs.query(run, "root")["dependencies"] == [dep]
    assert docs.query(run, "child")["depended_on_by"] == [dep]
    assert "Depended on by" in (run / "docs/nodes/child.md").read_text()
    index = (run / "docs/INDEX.md").read_text()
    assert '```mermaid' not in index  # containment is never drawn as dependency
    assert "包含关系，不比对" in index and "Uses its service." in index
    assert host_run.verify(run)["ok"]
    view = aggregation.relationship_view(value, [], graph())
    system = dict(key_flows=[dict(name="Flow", description="Uses helpers.", steps=ids[:2])])
    enriched = aggregation.annotate_relationships(view, system, [])
    assert enriched["key_flows"][0]["inferred_steps"] == [1]
