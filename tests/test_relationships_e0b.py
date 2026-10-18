"""Reader and operator contracts for the E0b dependency presentation fixes."""
import json
import re

import pytest

from cbe import aggregation, checks, host_run
from test_host_run import _answer_task, _good
from test_relationships_o6 import answer, edge, graph
from test_relationships_o6b import host_until_system, render_example
from test_relationships_o6c import containment_tree


def test_large_tree_gives_graph_only_and_containment_independent_rankings():
    nodes = [dict(id="root", parent=None, unit_ids=["root"])]
    nodes += [dict(id=f"child{i:02}", parent="root", unit_ids=[f"u{i}"]) for i in range(45)]
    nodes += [dict(id=x, parent="root", unit_ids=[x]) for x in ("left", "right", "third")]
    edges = [edge("root", f"u{i}", count=100+i) for i in range(45)]
    edges += [edge("left", "right", count=2), edge("right", "third", count=9)]
    view = aggregation.relationship_view(dict(nodes=nodes, depends_on=[]), edges, graph())
    ordinary = [r for r in view["dependencies"] if r["source"] == "graph_only"]
    within = [r for r in view["dependencies"] if r["source"] == "within_containment"]
    assert [(r["from"], r["to"], r["count"]) for r in ordinary] == [
        ("right", "third", 9), ("left", "right", 2)]
    assert view["counts"] == dict(graph_confirmed=0, model_inferred=0, graph_only=2)
    assert view["graph_only_omitted"] == 0
    assert len(within) == 40 and view["within_containment_count"] == 45
    assert view["within_containment_omitted"] == 5
    assert [r["count"] for r in within] == list(range(144, 104, -1))


def test_containment_row_shows_reverse_edges_without_a_reverse_tree_pair():
    tree = containment_tree()
    tree["depends_on"] = [{"from": "parent", "to": "child"}]
    view = aggregation.relationship_view(tree, [edge("a", "b", count=13), edge("c", "a", count=5),
                                               edge("b", "c", count=99)], graph())
    row = next(r for r in view["dependencies"] if r["source"] == "containment")
    assert (row["count"], row["reverse_count"]) == (13, 5)
    assert view["counts"]["graph_only"] == 0
    assert view["within_containment_count"] == 2


@pytest.mark.parametrize("name_length", [10, 290])
def test_host_retry_preserves_all_seven_bad_flows_and_their_ids(tmp_path, name_length):
    run, item = host_until_system(tmp_path)
    value = _good(item, run)
    value["dependency_descriptions"] = [dict(**{"from": "bad", "to": "missing"}, description="Uses it.")]*2
    value["key_flows"] = [dict(name=f"Bad {i} " + "x"*name_length, description="Uses helper.",
                               steps=[f"wrong_node_{i}", f"other_node_{i}"]) for i in range(1, 8)]
    result = _answer_task(run, item, value)
    assert not result["accepted"]
    retry = host_run.next_tasks(run, limit=1)["tasks"][0]
    # The actual file sent back to the model, after the host's 2,000-char cut.
    prompt = open(retry["prompt_file"]).read()
    feedback = prompt.split("Original error: ", 1)[1].split("\n", 1)[0]
    for i in range(1, 8):
        assert f"key flow {i}" in feedback
        assert f"wrong_node_{i}" in feedback and f"other_node_{i}" in feedback
    assert feedback.count("steps are unit ids from candidates, not node ids") == 1
    assert feedback.count("existing pair") == 2
    if name_length == 10:
        assert all(f"Bad {i}" in feedback for i in range(1, 8))


def test_description_normalization_numbers_start_at_one():
    value = answer()
    value["dependency_descriptions"] *= 2
    for row in value["dependency_descriptions"]:
        row["description"] = "Uses graph-confirmed calls."
    flags = checks.normalize_system(value, 2000, unit_ids={"a", "c"}, has_candidates=True)
    assert any("dependency_descriptions[1] removed" in flag for flag in flags)
    assert any("dependency_descriptions[2] removed" in flag for flag in flags)
    assert not any("dependency_descriptions[0]" in flag for flag in flags)


@pytest.mark.parametrize("label", ["graph-confirmed", "model-inferred", "graph-only", "containment",
                                    "within containment", "图确认", "模型推断", "图有未描述", "包含关系", "包含内"])
def test_source_labels_in_both_languages_are_rejected(label):
    value = answer()
    value["dependency_descriptions"][0]["description"] = f"Uses {label}."
    with pytest.raises(ValueError, match="omit evidence/source words"):
        checks.check_system(value, unit_ids={"a", "c"}, has_candidates=True)


def test_english_artifact_navigation_and_catalog_interface_fields(tmp_path):
    run, index, _ = render_example(tmp_path, flows=False)
    assert "### Within containment" in index
    assert "Program candidates, not selected by the model" in index
    assert "Graph-only pairs are ranked by edge count; 0 omitted." in index
    for page in (run / "docs").rglob("*.md"):
        assert not re.search(r"[\u4e00-\u9fff]", page.read_text()), page
    catalog = json.loads((run / "catalog.json").read_text())
    for key in ("short_names", "relationships", "node_dependencies"):
        assert not re.search(r"[\u4e00-\u9fff]", json.dumps(catalog[key], ensure_ascii=False))
