"""Graph provenance must be checked at its actual source and host consumers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbe import host_run
from cbe.graph import discover_config, discover_sources
from cbe.source_context import ContextError, build_context


def _planned_graph(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "core.py").write_text("def answer(value):\n    return value + 1\n")
    (repo / "pyproject.toml").write_text('[project]\nname="sample"\nversion="0.1"\n')
    graph = {
        "schema": "cbe-graph/1",
        "source_manifest": discover_sources(repo),
        "provenance": {
            "source_stable": True, "config_stable": True,
            "source_manifest_scope": "registered_sources",
            "config_manifest": discover_config(repo),
        },
        "nodes": [], "edges": [], "capabilities": [], "diagnostics": [],
    }
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(graph))
    build_context(repo, graph_path=path)
    run = tmp_path / "run"
    host_run.plan(repo, run_dir=run, graph_path=path, review="none")
    return repo, path, run, graph


@pytest.mark.parametrize("change", ["edit", "add", "remove"])
@pytest.mark.parametrize("kind", ["source", "configuration"])
def test_input_drift_rejected_before_context_and_dispatch(tmp_path, change, kind):
    repo, graph, run, _ = _planned_graph(tmp_path)
    filename = "core.py" if kind == "source" else "pyproject.toml"
    if change == "add":
        filename = "new.py" if kind == "source" else "tsconfig.json"
        (repo / filename).write_text("{}\n")
    elif change == "edit":
        with (repo / filename).open("a") as handle:
            handle.write("\n# changed after graph construction\n")
    else:
        (repo / filename).unlink()
    with pytest.raises(ContextError, match="drift"):
        build_context(repo, graph_path=graph)
    state_before = (run / "host/state.json").read_bytes()
    with pytest.raises(host_run.HostRunError):
        host_run.next_tasks(run)
    # No work may be leased from the stale input.
    assert (run / "host/state.json").read_bytes() == state_before


@pytest.mark.parametrize("flag", ["source_stable", "config_stable"])
def test_unstable_analysis_is_rejected_even_when_current_hashes_match(tmp_path, flag):
    repo, path, _, graph = _planned_graph(tmp_path)
    graph["provenance"][flag] = False
    path.write_text(json.dumps(graph))
    with pytest.raises(ContextError, match="unstable"):
        build_context(repo, graph_path=path)


def test_sliced_graph_preserves_provenance_validation(tmp_path):
    from cbe.graph import query_graph

    repo, path, _, graph = _planned_graph(tmp_path)
    path.write_text(json.dumps(query_graph(graph, paths=["absent.py"])))
    (repo / "pyproject.toml").write_text("# changed\n")
    with pytest.raises(ContextError, match="configuration drift"):
        build_context(repo, graph_path=path)
