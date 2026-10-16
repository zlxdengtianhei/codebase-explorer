"""Unit graph evidence: identity, priorities, accounting and token bounds."""
from __future__ import annotations

from cbe import projection as graph_projection, prompts
from cbe.token_budget import count_text_tokens


def _node(nid, path, line=1, **extra):
    return {"id": nid, "kind": "function", "name": nid, "path": path,
            "start_line": line, "end_line": line, **extra}


def _edge(eid, source, target, kind="call", status="resolved", **extra):
    return {"id": eid, "source": source, "target": target, "kind": kind,
            "status": status, **extra}


def _graph(nodes, edges, **extra):
    return {"schema": "cbe-graph/1", "nodes": nodes, "edges": edges,
            "capabilities": [], **extra}


def _inputs():
    chunks = [{"id": uid, "path": path, "start_line": start, "end_line": end}
              for uid, path, start, end in [("A", "a.py", 1, 20),
                  ("B", "b.py", 1, 20), ("C", "a.py", 21, 30)]]
    inventory = {p: {"symbols": [{"id": c["id"], "kind": "function"} for c in chunks if c["path"] == p]}
                 for p in ("a.py", "b.py")}
    graph = _graph([_node("a", "a.py"), _node("b", "b.py"), _node("c", "a.py", 21)],
                   [_edge("out", "a", "b", path="a.py", line=7),
                    _edge("in", "b", "a", path="b.py", line=8),
                    _edge("internal", "a", "c", path="a.py", line=9)])
    return graph, inventory, chunks


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


def test_graph_prompt_no_local_nodes_is_not_an_empty_graph_claim() -> None:
    graph = _graph([_node("other", "other.c")], [])
    prompt = "\n".join(graph_projection.graph_prompt_lines(graph, ["a.c"], embed=True))
    assert "no graph node anchors the listed file(s)" in prompt
    assert "not an empty graph and not a missing graph" in prompt
    assert "successfully empty" not in prompt


def test_callsite_maps_only_to_inventory_chunks_and_reports_missing_mapping():
    graph, inventory, chunks = _inputs()
    chunks.append({"id": "class-residue", "path": "a.py", "start_line": 6, "end_line": 8})
    graph["edges"].append(_edge("missing", "a", "b", path="a.py", line=50))
    # The Joern source method starts at line 1, but this call site is in C.
    graph["edges"].append(_edge("later-chunk", "a", "b", path="a.py", line=23))
    evidence = graph_projection.unit_graph(graph, ["a.py"], inventory, chunks)
    text = graph_projection.graph_text(evidence)
    assert "A → B (b.py:1)" in text and "A ← B (b.py:8)" in text
    assert "C → B (b.py:1)" in text
    assert "class-residue" not in text
    assert evidence.internal_calls == 1 and evidence.unmapped_calls == 1
    assert "A → C" not in text
    assert "unmapped resolved calls: 1" in text


def test_import_flood_cannot_displace_cross_batch_resolved_calls():
    graph, inventory, chunks = _inputs()
    for i in range(400):
        graph["nodes"].append({"id": f"ext{i}", "name": f"external_module_{i}"})
        graph["edges"].append(_edge(str(i), "a", f"ext{i}", "import", "external", path="a.py"))
    evidence = graph_projection.unit_graph(graph, ["a.py"], inventory, chunks)
    text = graph_projection.graph_text(evidence, budget=170)
    assert "A → B" in text and "A ← B" in text
    assert "dependencies=1" in text and "packages=1" in text
    assert "out=" not in text and "in=" not in text
    assert count_text_tokens(text) <= 170


def test_budget_and_exact_omissions_when_cross_calls_alone_overflow():
    graph, inventory, chunks = _inputs()
    graph["edges"] = []
    for i in range(10):
        graph["nodes"].append(_node(f"other{i}", "b.py", i + 1))
        graph["edges"].append(_edge(str(i), "a", f"other{i}", path="a.py", line=i + 1))
    evidence = graph_projection.unit_graph(graph, ["a.py"], inventory, chunks)
    text = graph_projection.graph_text(evidence, budget=130)
    selected = text.count("→")
    assert 0 < selected < 10
    assert f"out={10 - selected}" in text
    assert count_text_tokens(text) <= 130
    assert len([r for r in evidence.rows if r.category == "out"]) == 10


def test_cfg_counts_are_from_nodes_and_do_not_export_dataflow():
    graph, inventory, chunks = _inputs()
    for i, (label, line) in enumerate([("CONTROL_STRUCTURE", 3), ("RETURN", 5),
                                     ("CALL", 9), ("RETURN", 10), ("THROW", 8)]):
        graph["nodes"].append(_node(str(i), "a.py", line, kind="cfg_node", label=label, owner="a"))
    graph["nodes"].append(_node("secret-flow", "a.py", kind="dataflow_node", owner="a"))
    text = graph_projection.graph_text(graph_projection.unit_graph(graph, ["a.py"], inventory, chunks))
    assert "CFG A: control_structures=1, returns=2, early_returns_by_line=1, explicit_throw_exits=1" in text
    assert "other exception exits unknown" in text
    assert "secret-flow" not in text and "cfg_node" not in text
    graph["nodes"].extend([_node("synthetic", "a.py"),
        _node("second-return", "a.py", 6, kind="cfg_node", label="RETURN", owner="synthetic")])
    merged = graph_projection.graph_text(graph_projection.unit_graph(graph, ["a.py"], inventory, chunks))
    assert merged.count("CFG A:") == 1
    assert "returns=3" in merged
    graph["nodes"].extend([_node("adapter", "a.py", name="f<metaClassAdapter>"),
        _node("adapter-return", "a.py", 1, kind="cfg_node", label="RETURN", owner="adapter")])
    filtered = graph_projection.graph_text(graph_projection.unit_graph(graph, ["a.py"], inventory, chunks))
    assert filtered == merged


def test_ambiguity_three_candidates_and_unresolved_per_file_counts():
    graph, inventory, chunks = _inputs()
    graph["edges"] += [_edge("amb", "a", None, status="ambiguous", path="a.py", line=4,
                            candidates=["a", "b", "c", "missing"], expression="choose()")]
    graph["edges"] += [_edge(f"u{i}", "a", None, status="unresolved", path="a.py", line=4,
                             expression=f"unknown{i}()") for i in range(8)]
    text = graph_projection.graph_text(graph_projection.unit_graph(graph, ["a.py"], inventory, chunks))
    assert "A; B; C (4 candidates)" in text and "missing" not in text
    assert "Unresolved calls a.py: 8;" in text
    assert "unknown4" in text and "unknown5" not in text


def test_default_and_configurable_source_token_caps():
    graph, inventory, chunks = _inputs()
    for source_tokens, cap in [(100, 3000), (5000, 120), (5000, 3000), (0, 3000), (1, 3000)]:
        lines = graph_projection.graph_prompt_lines(graph, ["a.py"], embed=True,
            inventory=inventory, chunks=chunks, source_tokens=source_tokens, max_tokens=cap)
        payload = graph_projection.graph_text(
            graph_projection.unit_graph(graph, ["a.py"], inventory, chunks),
            budget=min(source_tokens, cap))
        assert count_text_tokens(payload) <= min(source_tokens, cap)
        if payload:
            assert "\n".join(lines).strip() == payload
        else:
            assert lines[0].startswith("GRAPH STATUS (outside payload cap):")


def test_tiny_budget_has_one_explicit_status_notice_with_all_omissions():
    graph, inventory, chunks = _inputs()
    options = dict(inventory=inventory, chunks=chunks, source_tokens=1,
                   graph_file="/run/tasks/module_1.graph.txt")
    script = graph_projection.graph_prompt_lines(graph, ["a.py"], embed=True, **options)
    host = graph_projection.graph_prompt_lines(graph, ["a.py"], embed=False, **options)
    for lines in (script, host):
        assert len([line for line in lines if line]) == 1
        assert "budget=1 tokens" in lines[0]
        assert "omitted dependencies=1,in=1,out=1,packages=1" in lines[0]
        assert "internal=1; unmapped=0" in lines[0]
        assert "→" not in lines[0] and "←" not in lines[0]
        assert count_text_tokens(lines[0]) > 1  # explicitly outside the payload cap
    assert ".graph.txt" not in script[0]
    assert "Read full evidence: /run/tasks/module_1.graph.txt" in host[0]
