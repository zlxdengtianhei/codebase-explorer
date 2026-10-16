"""The graph-to-prompt projection: referential integrity, priority, omissions.

These pin the contract that the LLM overlay relies on: a provided graph is
never presented as a prefix of itself, every included relation keeps its
endpoints (including boundary nodes outside the reading paths), import/call
edges are prioritized over CFG/dataflow samples, and absent / empty / failed /
unsupported are four different statements.
"""

from __future__ import annotations

import json
import os
import subprocess

from cbe import projection as graph_projection, prompts


def _node(nid: str, path: str, kind: str = "function", *, name: str | None = None,
          owner: str | None = None) -> dict:
    node = {"id": nid, "kind": kind, "path": path, "start_line": 1, "end_line": 1,
            "name": name or nid}
    if owner:
        node["owner"] = owner
    return node


def _edge(eid: str, source: str, target: str, kind: str, status: str = "resolved", **extra) -> dict:
    return {"id": eid, "source": source, "target": target, "kind": kind,
            "status": status, **extra}


def _graph(nodes: list[dict], edges: list[dict], **extra) -> dict:
    return {"schema": "cbe-graph/1", "nodes": nodes, "edges": edges,
            "backend": {"name": "test", "version": "1"}, "capabilities": [], **extra}


def test_graph_state_distinguishes_absent_empty_failed_and_unsupported() -> None:
    assert graph_projection.graph_state(None) == ("absent", "no graph was provided for this run")
    empty = _graph([], [], capabilities=[{"language": "c", "graph": "call", "status": "empty"}])
    assert graph_projection.graph_state(empty)[0] == "empty"
    failed = _graph([], [], capabilities=[{"language": "c", "graph": "call", "status": "failed"}])
    assert graph_projection.graph_state(failed)[0] == "failed"
    unsupported = {"schema": "cbe-graph/9", "nodes": [], "edges": []}
    assert graph_projection.graph_state(unsupported)[0] == "unsupported"

    absent_prompt = "\n".join(graph_projection.graph_prompt_lines(None, ["a.c"], embed=True))
    empty_prompt = "\n".join(graph_projection.graph_prompt_lines(empty, ["a.c"], embed=True))
    failed_prompt = "\n".join(graph_projection.graph_prompt_lines(failed, ["a.c"], embed=True))
    unsupported_prompt = "\n".join(graph_projection.graph_prompt_lines(unsupported, ["a.c"], embed=True))
    assert "not provided" in absent_prompt
    assert "successfully empty" in empty_prompt and "missing graph" in empty_prompt
    assert "failed or was unavailable" in failed_prompt and "unknown, not absent" in failed_prompt
    assert "unsupported" in unsupported_prompt


def test_graph_with_no_completed_backend_is_not_successfully_empty() -> None:
    failed = _graph([], [], analyzed_languages=["python"],
                    diagnostics=[{"code": "no_backend_completed"}])
    no_language = _graph([], [], analyzed_languages=[],
                         diagnostics=[{"code": "no_language_requested"},
                                      {"code": "no_backend_completed"}])
    assert graph_projection.graph_state(failed)[0] == "failed"
    assert graph_projection.graph_state(no_language)[0] == "unsupported"
    for graph in (failed, no_language):
        prompt = "\n".join(graph_projection.graph_prompt_lines(graph, ["a.c"], embed=True))
        assert "successfully empty" not in prompt
        assert "verified result" not in prompt


def test_projection_retains_cross_file_boundary_endpoints() -> None:
    graph = _graph([_node("main", "main.c"), _node("helper", "util.c")],
                   [_edge("e1", "main", "helper", "call", expression="helper()")])
    projection = graph_projection.project_graph(graph, ["main.c"])
    assert projection["state"] == "provided"
    ids = {node["id"] for node in projection["nodes"]}
    assert ids == {"main", "helper"}, "the util.c boundary endpoint must survive the code-file filter"
    assert [edge["id"] for edge in projection["edges"]] == ["e1"]
    assert projection["scope"]["boundary_endpoints_retained"] is True
    assert all(edge["source"] in ids and edge["target"] in ids for edge in projection["edges"])


def test_projection_prioritises_import_call_and_states_cfg_dataflow_omissions() -> None:
    nodes = [_node("m0", "a.c"), _node("m1", "b.c")]
    edges = [_edge("imp", "m0", "m1", "import", "partial"),
             _edge("call", "m0", "m1", "call", expression="helper()")]
    for index in range(400):
        nodes.append(_node(f"cfg{index}", "a.c", kind="cfg_node", owner="m0"))
        edges.append(_edge(f"cfge{index}", f"cfg{index}", "m0" if index % 2 else "cfg0", "cfg"))
    for index in range(400):
        nodes.append(_node(f"df{index}", "a.c", kind="dataflow_node", owner="m0"))
        edges.append(_edge(f"dfe{index}", f"df{index}", "m0" if index % 2 else "df0", "dataflow"))
    projection = graph_projection.project_graph(_graph(nodes, edges), ["a.c"],
                                        max_nodes=30, max_edges=25)
    kinds = [edge["kind"] for edge in projection["edges"]]
    assert "import" in kinds and "call" in kinds, "semantic relations must survive the budget"
    assert projection["counts"]["edges_selected"] <= 25
    assert projection["counts"]["edges_omitted"] > 0
    assert projection["counts"]["by_kind"]["cfg"]["omitted"] > 0
    assert "not a representative subset" in projection["sampling"]["cfg_dataflow"]
    ids = {node["id"] for node in projection["nodes"]}
    assert all(edge["source"] in ids and edge["target"] in ids for edge in projection["edges"])
    assert projection["cfg_dataflow_by_owner"]["cfg"]["m0"]["in_scope"] == 400


def test_projection_never_emits_a_dangling_edge() -> None:
    graph = _graph([_node("m0", "a.c")],
                   [_edge("good", "m0", "m0", "call"), _edge("dangling", "m0", "missing", "call")])
    projection = graph_projection.project_graph(graph, ["a.c"])
    ids = {node["id"] for node in projection["nodes"]}
    assert all(edge["source"] in ids and edge["target"] in ids for edge in projection["edges"])
    assert projection["counts"]["edges_omitted_missing_endpoint"] == 1
    assert "dangling" not in [edge["id"] for edge in projection["edges"]]


def test_graph_prompt_marks_api_bounded_and_gives_host_a_follow_up_query() -> None:
    graph = _graph([_node("m0", "a.c"), _node("m1", "b.c")],
                   [_edge("e1", "m0", "m1", "call", expression="helper()")])
    api_prompt = "\n".join(graph_projection.graph_prompt_lines(graph, ["a.c"], embed=True))
    assert "LOCAL GRAPH EVIDENCE" in api_prompt
    assert "tool-free" in api_prompt and "cannot query" in api_prompt
    assert "cbe graph query" not in api_prompt
    host_prompt = "\n".join(graph_projection.graph_prompt_lines(
        graph, ["a.c"], embed=False, expand_context_path="/run dir/context.json"))
    assert "cbe graph query --graph '/run dir/context.json'" in host_prompt
    assert "--kind call" in host_prompt
    assert "--kind with import, cfg, or dataflow" in host_prompt
    assert "boundary" in host_prompt.lower() or "Boundary" in host_prompt


def test_host_graph_query_runs_without_cbe_on_path(tmp_path) -> None:
    source_path = "source dir/a 'quoted'.c"
    graph = _graph([_node("caller", source_path), _node("callee", "b.c")],
                   [_edge("cross-file", "caller", "callee", "call")])
    frozen = tmp_path / "run with spaces" / "context.json"
    frozen.parent.mkdir()
    frozen.write_text(json.dumps({"schema": "cbe-context/1", "graph": graph}))
    lines = graph_projection.graph_prompt_lines(graph, [source_path], embed=False,
                                        expand_context_path=str(frozen))
    prefix = "To expand an omitted relation, run: "
    command = next(line.removeprefix(prefix) for line in lines if line.startswith(prefix))
    result = subprocess.run(command, shell=True, env={**os.environ, "PATH": ""},
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    queried = json.loads(result.stdout)
    assert [edge["id"] for edge in queried["edges"]] == ["cross-file"]
    assert {node["id"] for node in queried["nodes"]} == {"caller", "callee"}


def test_graph_prompt_no_local_nodes_is_not_an_empty_graph_claim() -> None:
    graph = _graph([_node("other", "other.c")], [])
    prompt = "\n".join(graph_projection.graph_prompt_lines(graph, ["a.c"], embed=True))
    assert "no graph node anchors the listed file(s)" in prompt
    assert "not an empty graph and not a missing graph" in prompt
    assert "successfully empty" not in prompt


def test_projection_keeps_unresolved_null_target_with_its_expression() -> None:
    graph = _graph([_node("file", "a.c", kind="file")],
                   [_edge("imp", "file", None, "import", "unresolved", expression='#include "b.h"')])
    projection = graph_projection.project_graph(graph, ["a.c"])
    assert projection["edges"][0]["target"] is None
    assert projection["edges"][0]["status"] == "unresolved"
    assert projection["edges"][0]["expression"] == '#include "b.h"'
    assert projection["counts"]["edges_omitted_missing_endpoint"] == 0


def test_detail_prompt_carries_the_projection_and_omission_statement() -> None:
    graph = _graph([_node("m0", "a.c"), _node("boundary", "util.c")],
                   [_edge("e1", "m0", "boundary", "call", expression="helper()")])
    inventory = {"a.c": {"tokens": 1, "sha256": "x", "nlines": 1, "symbols": []}}
    prompt = prompts.detail_prompt(["a.c"], inventory, graph=graph, embed=True)
    assert "LOCAL GRAPH EVIDENCE" in prompt and '"boundary"' in prompt
    assert "omitted" in prompt and "not a representative subset" in prompt
