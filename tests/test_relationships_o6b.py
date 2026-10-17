"""D-50 reader-visible contracts and the eleven C6 surviving mutations."""
import hashlib
import json
import re
from pathlib import Path

import pytest

from cbe import aggregation, checks, docs, host_run, prompts
from test_relationships_o6 import edge, graph, answer
from test_host_run import _repo, _good, _answer_task, _graph_for


def test_sibling_containers_use_subtrees_but_graph_only_uses_primary_owners():
    tree = {"nodes": [dict(id="top", parent=None, unit_ids=[]),
                      dict(id="left", parent="top", unit_ids=[]),
                      dict(id="right", parent="top", unit_ids=[]),
                      dict(id="leaf-a", parent="left", unit_ids=["a"]),
                      dict(id="leaf-b", parent="right", unit_ids=["b"])],
            "depends_on": [dict(**{"from": "left", "to": "right"}),
                           dict(**{"from": "top", "to": "right"})]}
    view = aggregation.relationship_view(tree, [edge("a", "b", count=37)], graph())
    rows = {(r["from"], r["to"]): r for r in view["dependencies"]}
    assert (rows["left", "right"]["source"], rows["left", "right"]["count"]) == ("graph_confirmed", 37)
    assert rows["top", "right"]["containment"] and rows["top", "right"]["count"] == 0
    assert [(r["from"], r["to"]) for r in rows.values() if r["source"] == "graph_only"] == [("leaf-a", "leaf-b")]


def test_graph_only_order_uses_edge_count_before_ids():
    tree = {"nodes": [dict(id=n, parent=None, unit_ids=[n]) for n in "abcd"], "depends_on": []}
    view = aggregation.relationship_view(tree, [edge("a", "b"), edge("c", "d", count=9)], graph(), graph_only_limit=1)
    assert [(r["from"], r["to"], r["count"]) for r in view["dependencies"]] == [("c", "d", 9)]
    assert view["graph_only_omitted"] == 1


def test_candidate_paths_never_repeat_units_even_before_depth_limit():
    paths = aggregation.candidate_flows([edge("entry", "a"), edge("a", "b"), edge("b", "a")])
    assert paths == [["entry", "a", "b"]]


def test_final_answer_keeps_five_good_flows_and_names_bad_ids():
    value = answer()
    value["key_flows"] = [dict(name=f"Flow {i}", description="Uses helper.", steps=["a", "c"]) for i in range(7)]
    for i in (2, 6):
        value["key_flows"][i]["steps"] = ["root", "child"]
    options = dict(unit_ids={"a", "c"}, dependencies=[{"from": "root", "to": "child"}], has_candidates=True)
    with pytest.raises(ValueError, match="Flow 2.*root.*child.*not node ids") as error:
        checks.check_system(value, **options)
    assert "Flow 6" in str(error.value)
    flags = checks.normalize_system(value, 2000, **options)
    assert [f["name"] for f in value["key_flows"]] == ["Flow 0", "Flow 1", "Flow 3", "Flow 4", "Flow 5"]
    assert sum("removed" in flag for flag in flags) == 2
    checks.check_system(value, normalized=True, **options)


@pytest.mark.parametrize("text", ["Uses graph-confirmed calls.", "It is model-inferred.", "Uses graph-only edges.",
                                  "Uses resolved calls.", "Uses 37 static call edges.", "Uses 3 calls."])
def test_evidence_words_reasked_and_only_bad_description_removed(text):
    value = answer()
    value["dependency_descriptions"].append(dict(**{"from": "child", "to": "root"}, description=text))
    options = dict(unit_ids={"a", "c"}, dependencies=[{"from": "root", "to": "child"}, {"from": "child", "to": "root"}], has_candidates=True)
    with pytest.raises(ValueError, match="omit evidence/source words"):
        checks.check_system(value, **options)
    flags = checks.normalize_system(value, 2000, **options)
    assert len(value["dependency_descriptions"]) == 1
    assert value["dependency_descriptions"][0]["description"] == "Uses child."
    assert any("dependency_descriptions[1] removed" in f for f in flags)


def test_all_invalid_flows_normalize_to_empty_with_a_flag():
    value = answer()
    for flow in value["key_flows"]:
        flow["steps"] = ["root", "child"]
    flags = checks.normalize_system(value, 2000, unit_ids={"a", "c"},
                                    dependencies=[{"from": "root", "to": "child"}], has_candidates=True)
    assert value["key_flows"] == []
    assert any("retained 0" in flag for flag in flags)


def test_one_good_final_flow_is_retained_and_flagged():
    value = answer()
    value["key_flows"] = value["key_flows"][:1]
    flags = checks.normalize_system(value, 2000, unit_ids={"a", "c"},
                                    dependencies=[{"from": "root", "to": "child"}], has_candidates=True)
    assert len(value["key_flows"]) == 1
    assert any("retained 1" in flag for flag in flags)


def test_no_candidates_rejects_model_flows():
    with pytest.raises(ValueError, match="otherwise"):
        checks.check_system(answer(), has_candidates=False)


def test_nonempty_dependency_table_requires_an_explanation():
    value = answer()
    value.update(dependency_descriptions=[], key_flows=[])
    with pytest.raises(ValueError, match="at least one"):
        checks.check_system(value, dependencies=[{"from": "root", "to": "child"}])


def render_example(tmp_path, *, evidence=True, flows=True, many=False):
    from test_semantic import SRC, _inventory, _good_payload
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg/jobs.py").write_text(SRC)
    inventory = _inventory()
    payload = _good_payload(inventory)
    units = {u["id"]: u for u in payload["units"]}
    a, b = "pkg/jobs.py::Pool.submit", "pkg/jobs.py::reserve@5"
    nodes = [dict(id="top", parent=None, title="Top", unit_ids=[]),
             dict(id="a", parent="top", title='Submit ["<&`', unit_ids=[a]),
             dict(id="b", parent="top", title="Reserve", unit_ids=sorted(set(units) - {a}))]
    nodes += [dict(id=f"empty{i}", parent="top", title=f"Empty {i}", unit_ids=[]) for i in range(20 if many else 1)]
    tree = {"nodes": nodes, "depends_on": [{"from": "a", "to": "b"}] +
            [{"from": "a", "to": n["id"]} for n in nodes[3:]]}
    gp = {"schema": "cbe-graph/1", "nodes": [
        dict(id="submit", path="pkg/jobs.py", start_line=11, kind="method"),
        dict(id="reserve", path="pkg/jobs.py", start_line=5, kind="method")],
        "edges": [dict(id=str(i), kind="call", status="resolved", source=s, target=t,
                       path="pkg/jobs.py", line=12 if i == 0 else 6, column=16)
                  for i, (s, t) in enumerate([("submit", "reserve"), ("reserve", "submit")])]}
    # Add an entry outside the cycle for a real program-candidate fallback.
    if not flows:
        gp["edges"] = gp["edges"][:1]
    system = dict(overview="Submission overview.", maintenance_navigation="Open Submit.",
                  dependency_descriptions=[], key_flows=[dict(name="Transfer", description="Uses helpers.", steps=[a, b, a])] if flows else [])
    context = {"files": [{"path": "pkg/jobs.py", "source": SRC, "sha256": hashlib.sha256(SRC.encode()).hexdigest()}],
               "chunks": [{"id": a, "path": "pkg/jobs.py", "start_byte": SRC.index("    def submit"),
                           "end_byte": len(SRC.encode())},
                          {"id": b, "path": "pkg/jobs.py", "start_byte": SRC.index("def reserve(value):"),
                           "end_byte": SRC.index("class Pool:")}]}
    run = tmp_path / "run"
    result = docs.render(run_dir=run, source_root=repo, inventory=inventory, units=units,
                        dispositions=payload["dispositions"], tree=tree, languages={"pkg/jobs.py": "python"},
                        graph=gp if evidence else None, system=system, context=context)
    return run, (run / "docs/INDEX.md").read_text(), result


def test_three_mermaid_line_styles_and_full_legend(tmp_path):
    _, index, _ = render_example(tmp_path)
    diagram = index.split("```mermaid\n", 1)[1].split("```", 1)[0]
    assert all(arrow in diagram for arrow in (" --> ", " -.-> ", " ==> "))
    legend = index.split("图例：", 1)[1].splitlines()[0]
    assert all(label in legend for label in ("图确认", "模型推断", "图有未描述"))
    assert "#34;" in diagram and "#91;" in diagram


def test_dependency_list_keeps_all_source_labels_and_separates_footnotes(tmp_path):
    _, index, _ = render_example(tmp_path)
    listing = index.split("## Dependency list\n", 1)[1].split("## Key flows", 1)[0]
    assert all(f"· {label} ·" in listing for label in ("图确认", "模型推断", "图有未描述"))
    assert "\n\n图有未描述按边数降序保留" in listing
    assert "\n\nsystem 未提供关键依赖说明。" in listing


def test_mermaid_at_most_fifteen_nodes(tmp_path):
    _, index, _ = render_example(tmp_path, many=True)
    diagram = index.split("```mermaid\n", 1)[1].split("```", 1)[0]
    assert len(re.findall(r'^  n\d+\[', diagram, re.M)) == 15


def test_index_explains_unavailable_graph(tmp_path):
    _, index, _ = render_example(tmp_path, evidence=False)
    assert "没有可用图确认；仅列模型推断：" in index


def test_index_explains_unavailable_candidates(tmp_path):
    _, index, _ = render_example(tmp_path, evidence=False, flows=False)
    assert "没有候选流程：" in index


def test_all_bad_flows_fall_back_to_linked_program_candidates(tmp_path):
    run, index, result = render_example(tmp_path, flows=False)
    assert result["key_flows"] == 0 and result["candidate_flows"] == 1
    assert "程序候选，未经模型挑选" in index
    assert "**候选 1**" in index and f"nodes/a.md#{docs.anchor('pkg/jobs.py::Pool.submit')}" in index
    assert json.loads((run / "catalog.json").read_text())["key_flows"] == []


def host_until_system(tmp_path):
    repo = _repo(tmp_path)
    gp = _graph_for(repo, ["src/pkg/jobs.py", "src/pkg/cli.py"])
    gp["nodes"][0]["start_line"] = 5
    gp["nodes"][1]["start_line"] = 3
    gp["edges"] = [dict(id="call", kind="call", status="resolved", source="n-1", target="n-0",
                        path="src/pkg/cli.py", line=4)]
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(gp))
    run = Path(host_run.plan(repo, tmp_path / "run", graph_path=path, review="none")["run_dir"])
    while True:
        item = host_run.next_tasks(run, limit=1)["tasks"][0]
        if item["kind"] == "system":
            return run, item
        assert _answer_task(run, item, _good(item, run))["accepted"]


def test_final_missing_flows_with_real_graph_is_accepted_flagged_and_counted(tmp_path):
    run, item = host_until_system(tmp_path)
    shown = json.loads(Path(item["prompt_file"]).read_text().split("RELATIONSHIPS: ")[1].split("\nNODE SUMMARIES:")[0])
    assert shown["candidate_flows"]
    value = _good(item, run)
    del value["key_flows"]
    assert not _answer_task(run, item, value)["accepted"]
    item = host_run.next_tasks(run, limit=1)["tasks"][0]
    assert _answer_task(run, item, value)["accepted"]
    state = json.loads((run / "host/state.json").read_text())
    assert state["status"] == "complete" and host_run.verify(run)["ok"]
    assert any("key_flows" in f for f in state["tasks"]["system"]["flags"])
    assert "程序候选，未经模型挑选" in (run / "docs/INDEX.md").read_text()
    summary = json.loads((run / "summary.json").read_text())
    assert summary["node_dependencies"] == dict(graph_confirmed=0, model_inferred=0, graph_only=0)
    assert summary["candidate_flows"] == 1 and summary["key_flows"] == 0


def test_host_checks_candidate_presence_after_prompt_truncation(tmp_path, monkeypatch):
    run, item = host_until_system(tmp_path)
    original = host_run._system_inputs
    def large_inputs(*args):
        nodes, limit, view, units = original(*args)
        view = {**view, "dependencies": [{"from": "root", "to": "root", "basis": "word " * 60000}],
                "candidate_flows": view["candidate_flows"]}
        return nodes, limit, view, units
    monkeypatch.setattr(host_run, "_system_inputs", large_inputs)
    prompt = host_run.completion_prompt(run, "system")
    context = json.loads(prompt.split("RELATIONSHIPS: ")[1].split("\nNODE SUMMARIES:")[0])
    assert context["candidate_flows"] == []
    value = dict(overview="Overview.", maintenance_navigation="Open root.", dependency_descriptions=[], key_flows=[])
    assert _answer_task(run, item, value)["accepted"]
