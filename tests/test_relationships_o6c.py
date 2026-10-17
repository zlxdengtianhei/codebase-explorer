"""O6c contracts: complete feedback, visible containment calls and final repair."""
import json
import re

import pytest

from cbe import aggregation, checks, docs, prompts
from test_relationships_o6 import answer, edge, graph
from test_relationships_o6b import render_example


@pytest.mark.parametrize("flow_count", [2, 3])
def test_one_rejection_reports_descriptions_counts_and_every_bad_flow(flow_count):
    value = answer()
    value["dependency_descriptions"][0]["description"] = "Uses 3 resolved calls."
    value["dependency_descriptions"].append({"from": "unknown", "to": "child", "description": "Uses it."})
    value["key_flows"] = [dict(name=f"Bad {i}", description="Uses helper.", steps=["root", "child"])
                          for i in range(flow_count)]
    with pytest.raises(ValueError) as error:
        checks.check_system(value, unit_ids={"a", "c"}, dependencies=[{"from": "root", "to": "child"}],
                            has_candidates=True)
    message = str(error.value)
    assert "omit evidence/source words" in message and "existing pair" in message
    assert all(f"key flow {i + 1} 'Bad {i}'" in message for i in range(flow_count))
    assert "root" in message and "not node ids" in message
    if flow_count == 2:
        assert "3-7 flows" in message


def test_final_answer_keeps_first_seven_valid_flows_and_records_trim():
    value = answer()
    value["key_flows"] = [dict(name=f"Flow {i}", description="Calls helper.", steps=["a", "c"])
                          for i in range(9)]
    flags = checks.normalize_system(value, 2000, unit_ids={"a", "c"},
                                    dependencies=[{"from": "root", "to": "child"}], has_candidates=True)
    assert [f["name"] for f in value["key_flows"]] == [f"Flow {i}" for i in range(7)]
    assert any("key_flows" in flag and "9" in flag and "7" in flag for flag in flags)
    checks.check_system(value, unit_ids={"a", "c"}, has_candidates=True, normalized=True)


def test_system_prompt_tells_model_to_omit_source_labels_and_counts():
    prompt = prompts.system_prompt([], 2000, {"dependencies": [], "candidate_flows": []})
    assert "Do not write evidence/source words" in prompt
    assert "or call/edge counts" in prompt
    assert "who uses whom for what" in prompt


def test_normalization_flow_numbers_are_one_based_in_both_places():
    value = answer()
    value["key_flows"][1]["steps"] = ["root", "child"]
    flags = checks.normalize_system(value, 2000, unit_ids={"a", "c"}, has_candidates=True)
    removed = [f for f in flags if "removed" in f]
    assert len(removed) == 1
    assert "key_flows[2] removed: key flow 2 'Flow 1'" in removed[0]


@pytest.mark.parametrize("text", ["Retrieves state through _AppCtxGlobals-resolved lookups.",
                                  "Uses resolved dispatch."])
def test_ordinary_resolved_word_is_accepted(text):
    value = answer()
    value["dependency_descriptions"][0]["description"] = text
    checks.check_system(value, unit_ids={"a", "c"}, has_candidates=True)


@pytest.mark.parametrize("text", ["Uses resolved calls.", "Uses resolved import edges.", "Uses 3 edges.",
                                  "Uses 3 resolved calls.", "Uses graph-confirmed calls.",
                                  "Uses model-inferred edges.", "Uses graph-only imports."])
def test_evidence_phrases_still_rejected(text):
    value = answer()
    value["dependency_descriptions"][0]["description"] = text
    with pytest.raises(ValueError, match="omit evidence/source words"):
        checks.check_system(value, unit_ids={"a", "c"}, has_candidates=True)


def containment_tree():
    return {"nodes": [dict(id="parent", parent=None, unit_ids=["a"]),
                      dict(id="child", parent="parent", unit_ids=["b"]),
                      dict(id="grandchild", parent="child", unit_ids=["c"])],
            "depends_on": [{"from": "parent", "to": "child"}, {"from": "child", "to": "parent"}]}


def test_containment_counts_ancestor_direct_units_against_descendant_subtree_in_each_direction():
    view = aggregation.relationship_view(containment_tree(),
        [edge("a", "b", count=13), edge("a", "c"), edge("c", "a", count=2), edge("b", "c", count=99)], graph())
    rows = {(r["from"], r["to"]): r for r in view["dependencies"]}
    assert rows["parent", "child"]["count"] == 14
    assert rows["child", "parent"]["count"] == 2
    assert rows["parent", "child"]["source"] == rows["child", "parent"]["source"] == "containment"
    assert view["counts"] == dict(graph_confirmed=0, model_inferred=0, graph_only=0)
    assert view["within_containment_count"] == 3
    assert rows["parent", "grandchild"]["source"] == "within_containment"
    assert rows["parent", "grandchild"]["count"] == 1
    assert rows["parent", "grandchild"]["containment"] is True


def test_unmentioned_containment_preserves_direct_owner_pairs():
    tree = containment_tree()
    tree["depends_on"] = []
    rows = aggregation.relationship_view(tree, [edge("a", "b", count=13), edge("a", "c")], graph())
    assert [(r["from"], r["to"], r["count"], r["source"], r["containment"]) for r in rows["dependencies"]] == [
        ("parent", "child", 13, "within_containment", True), ("parent", "grandchild", 1, "within_containment", True)]


def test_pages_and_catalog_show_containment_counts_but_mermaid_excludes_both_kinds(tmp_path):
    run, _, _ = render_example(tmp_path)
    catalog = json.loads((run / "catalog.json").read_text())
    # Both endpoints also have a non-containment edge, so both receive aliases.
    tree = {"nodes": [{"id": nid, **node} for nid, node in catalog["nodes"].items()]}
    tree["nodes"] = [{**n, "parent": "a" if n["id"] == "b" else n.get("parent")} for n in tree["nodes"]]
    # Use the accepted fixture inputs, and the real host renderer to rebuild.
    from test_semantic import SRC, _inventory, _good_payload
    import hashlib
    inventory = _inventory()
    payload = _good_payload(inventory)
    gp = {"schema": "cbe-graph/1", "nodes": [
        dict(id="submit", path="pkg/jobs.py", start_line=11, kind="method"),
        dict(id="reserve", path="pkg/jobs.py", start_line=5, kind="method")],
        "edges": [dict(id="call", kind="call", status="resolved", source="submit", target="reserve",
                       path="pkg/jobs.py", line=12, column=16),
                  dict(id="reverse", kind="call", status="resolved", source="reserve", target="submit",
                       path="pkg/jobs.py", line=6, column=16)]}
    tree["depends_on"] = [{"from": "a", "to": "b"}, {"from": "a", "to": "empty0"},
                          {"from": "b", "to": "empty0"}]
    docs.render(run_dir=run, source_root=tmp_path / "repo", inventory=inventory,
        units={u["id"]: u for u in payload["units"]}, dispositions=payload["dispositions"], tree=tree,
        languages={"pkg/jobs.py": "python"}, graph=gp,
        context={"files": [{"path": "pkg/jobs.py", "source": SRC,
                           "sha256": hashlib.sha256(SRC.encode()).hexdigest()}],
                 "chunks": [{"id": "pkg/jobs.py::Pool.submit", "path": "pkg/jobs.py",
                             "start_byte": SRC.index("    def submit"), "end_byte": len(SRC.encode())},
                            {"id": "pkg/jobs.py::reserve@5", "path": "pkg/jobs.py",
                             "start_byte": SRC.index("def reserve(value):"), "end_byte": SRC.index("class Pool:")}]})
    index = (run / "docs/INDEX.md").read_text()
    assert "Graph-confirmed and model-inferred pairs count edges between two subtrees." in index
    assert "Graph-only pairs count edges between direct node owners." in index
    assert "containment · → 1 / ← 1 edge(s)" in index
    assert "within containment · 1 edge(s)" in index
    assert "containment · → 1 / ← 1 edge(s)" in (run / "docs/nodes/a.md").read_text()
    diagram = index.split("```mermaid\n", 1)[1].split("```", 1)[0]
    # There are exactly two sibling/container-disjoint tree edges to Empty.
    assert len(re.findall(r'^  n\d+ (?:-->|-\.->|==>) n\d+$', diagram, re.M)) == 2
    deps = json.loads((run / "catalog.json").read_text())["node_dependencies"]
    assert next(d for d in deps if (d["from"], d["to"]) == ("a", "b"))["source"] == "containment"
