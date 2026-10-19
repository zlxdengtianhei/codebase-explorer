"""Availability agrees at the prompt/INDEX boundary, including a failed build."""
import copy
import json
from pathlib import Path

import pytest

from cbe import docs, graph, projection


FAILED = json.loads((Path(__file__).parent / "fixtures/graphs/c2-tiny-failed.json").read_text())
EMPTY = {"schema": "cbe-graph/1", "nodes": [], "edges": [],
         "capabilities": [{"language": "python", "graph": "import", "status": "empty"}]}
EMPTY_PARTIAL_FAILURE = copy.deepcopy(EMPTY)
EMPTY_PARTIAL_FAILURE["capabilities"].append(
    {"language": "ruby", "graph": "call", "status": "failed"})


@pytest.mark.parametrize("value,state,prompt_text,index_text", [
    (FAILED, "failed", "analysis failed or was unavailable", "No graph backend succeeded"),
    (EMPTY, "empty", "provided and successfully empty", "The graph is empty. No relations are graph-confirmed"),
    (EMPTY_PARTIAL_FAILURE, "empty", "provided and successfully empty", "The graph is empty. No relations are graph-confirmed"),
    (None, "absent", "not provided", "No graph was provided"),
    ({"schema": "cbe-graph/1", "nodes": [], "edges": [], "capabilities": [
        {"language": "ruby", "graph": "call", "status": "unsupported"}]},
     "unsupported", "unsupported for this run", "The graph does not support this analysis"),
])
def test_prompt_and_index_share_availability(tmp_path, value, state, prompt_text, index_text):
    assert graph.graph_state(value)[0] == state
    assert projection.graph_state(value) == graph.graph_state(value)
    line = projection.graph_prompt_lines(value, ["main.py"], embed=True)[0]
    assert line.startswith("GRAPH:") and prompt_text in line
    docs.render(run_dir=tmp_path, source_root=tmp_path, inventory={}, units={}, dispositions={},
                tree={"nodes": []}, languages={}, graph=value)
    index = (tmp_path / "docs/INDEX.md").read_text()
    opening = index.split("## Graph coverage\n\n", 1)[1].splitlines()[0]
    assert opening.startswith(index_text)


def test_components_with_only_failed_capabilities_are_failed():
    value = {"schema": "cbe-graph/1", "nodes": [], "edges": [],
             "backend": {"name": "test", "components": [{"name": "joern"}]},
             "capabilities": [{"language": "go", "graph": "call", "status": "failed"}]}
    assert graph.graph_state(value)[0] == "failed"


@pytest.mark.parametrize("status", ["resolved", "partial", "empty"])
def test_one_successful_capability_keeps_empty_result(status):
    value = {"schema": "cbe-graph/1", "nodes": [], "edges": [],
             "backend": {"name": "test", "components": [{"name": "joern"}]},
             "capabilities": [{"language": "go", "graph": "call", "status": "failed"},
                              {"language": "go", "graph": "cfg", "status": status}]}
    assert graph.graph_state(value)[0] == "empty"


def test_explicit_successful_component_is_completion_evidence():
    value = {"schema": "cbe-graph/1", "nodes": [], "edges": [],
             "backend": {"name": "test", "components": [{"name": "joern", "status": "empty"}]},
             "capabilities": [{"language": "go", "graph": "call", "status": "failed"}]}
    assert graph.graph_state(value)[0] == "empty"


def test_read_quality_keeps_snapshot_and_refreshes_explicit_files(tmp_path):
    value = copy.deepcopy(EMPTY)
    value["source_manifest"] = [{"path": "main.py", "language": "python"}]
    value["nodes"] = [{"id": "a", "path": "main.py"}]
    legacy = graph.read_graph_quality(value, repo=tmp_path)
    assert legacy["nodes_missing_files"]["count"] == 1
    value["quality"] = legacy
    (tmp_path / "main.py").write_text("pass\n")
    assert graph.read_graph_quality(value, repo=tmp_path) is legacy
    assert graph.read_graph_quality(value, existing_paths={"main.py"})["nodes_missing_files"]["count"] == 0
    assert graph.read_graph_quality(value) is legacy
