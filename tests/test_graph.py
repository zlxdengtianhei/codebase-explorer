"""Tests for the public ``cbe-graph/1`` analyzer and the backend adapters.

The deterministic tests never need a JVM: they exercise source discovery,
query filtering, path canonicalization, import supersession, capability
statuses and the Joern-payload normalizer with synthetic payloads.  The
integration tests run the real backends and are skipped unless
``CBE_JOERN_HOME`` (and ``CBE_DEPCRUISE_BIN`` for JS) are set, so CI without
the tools stays green.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from cbe.graph import (
    GraphError,
    _merge_capabilities,
    _normalize_joern_payload,
    _prefer_resolved_imports,
    analyze_graph,
    available_graph_languages,
    discover_config,
    discover_sources,
    graph_suffixes,
    query_graph,
)
from cbe.graph_backends._paths import canonical_repo_path
from cbe.graph_backends.joern import _capabilities_for

FIXTURES = Path(__file__).parent / "fixtures" / "graphs"


# ---------------------------------------------------------------------------
# path canonicalization
# ---------------------------------------------------------------------------


def test_canonical_repo_path_normalizes_and_rejects() -> None:
    assert canonical_repo_path("./a/b.py") == "a/b.py"
    assert canonical_repo_path("a/../b.py") == "b.py"
    assert canonical_repo_path(".hidden") == ".hidden"
    assert canonical_repo_path("a//b.py") == "a/b.py"
    assert canonical_repo_path("../a.py") is None
    assert canonical_repo_path("/abs/a.py") is None
    assert canonical_repo_path("C:/a.py") is None
    assert canonical_repo_path("") is None


# ---------------------------------------------------------------------------
# source discovery
# ---------------------------------------------------------------------------


def test_discover_sources_hashes_languages_and_skips_caches(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "b.c").write_text("int main(){return 0;}\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("ignore\n", encoding="utf-8")
    cache = tmp_path / ".venv"
    cache.mkdir()
    (cache / "hidden.py").write_text("y = 2\n", encoding="utf-8")

    manifest = discover_sources(tmp_path)
    by_path = {entry["path"]: entry for entry in manifest}
    assert set(by_path) == {"a.py", "b.c"}
    assert by_path["a.py"]["language"] == "python"
    assert by_path["b.c"]["language"] == "c"
    assert by_path["a.py"]["sha256"] == hashlib.sha256(b"x = 1\n").hexdigest()


def test_discover_sources_covers_registry_extensions(tmp_path: Path) -> None:
    for name, language in [("m.rs", "rust"), ("m.rb", "ruby"), ("m.php", "php"),
                           ("M.cs", "c_sharp"), ("m.kt", "kotlin"), ("m.swift", "swift"),
                           ("m.tsx", "tsx")]:
        (tmp_path / name).write_text("// x\n", encoding="utf-8")
    manifest = {entry["path"]: entry["language"] for entry in discover_sources(tmp_path)}
    assert manifest == {"m.rs": "rust", "m.rb": "ruby", "m.php": "php", "M.cs": "c_sharp",
                        "m.kt": "kotlin", "m.swift": "swift", "m.tsx": "tsx"}


def test_graph_suffixes_match_source_context_registry() -> None:
    from cbe.source_context import supported_languages

    registry = {}
    for entry in supported_languages()["languages"]:
        for suffix in entry["suffixes"]:
            registry[suffix.lower()] = entry["name"]
    assert graph_suffixes() == registry


def test_discover_config_hashes_build_files(tmp_path: Path) -> None:
    (tmp_path / "compile_commands.json").write_text("[]\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("x\n", encoding="utf-8")
    config = {entry["path"]: entry["sha256"] for entry in discover_config(tmp_path)}
    assert set(config) == {"compile_commands.json", "pyproject.toml"}
    assert config["compile_commands.json"] == hashlib.sha256(b"[]\n").hexdigest()


# ---------------------------------------------------------------------------
# query_graph
# ---------------------------------------------------------------------------


def _sample_graph() -> dict:
    return {
        "schema": "cbe-graph/1",
        "source_manifest": [{"path": "a.py", "language": "python", "sha256": "0" * 64}],
        "backend": {"name": "test", "version": "0"},
        "provenance": {"source_stable": True},
        "nodes": [
            {"id": "file:a.py", "kind": "file", "path": "a.py"},
            {"id": "file:b.py", "kind": "file", "path": "b.py"},
            {"id": "file:c.py", "kind": "file", "path": "c.py"},
        ],
        "edges": [
            {"id": "e1", "source": "file:a.py", "target": "file:b.py", "kind": "import", "status": "resolved"},
            {"id": "e2", "source": "file:b.py", "target": "file:c.py", "kind": "call", "status": "unresolved"},
        ],
        "capabilities": [],
        "diagnostics": [],
    }


def test_query_graph_filters_by_path_and_direction() -> None:
    graph = _sample_graph()
    out_only = query_graph(graph, paths=["a.py"], direction="out")
    assert {edge["id"] for edge in out_only["edges"]} == {"e1"}
    assert {node["id"] for node in out_only["nodes"]} == {"file:a.py", "file:b.py"}
    in_only = query_graph(graph, paths=["b.py"], direction="in")
    assert {edge["id"] for edge in in_only["edges"]} == {"e1"}


def test_query_graph_kind_only_returns_filtered_graph_not_empty() -> None:
    graph = _sample_graph()
    calls = query_graph(graph, kind="call")
    assert {edge["id"] for edge in calls["edges"]} == {"e2"}
    assert {node["id"] for node in calls["nodes"]} == {"file:b.py", "file:c.py"}
    assert calls["scope"]["edge_filter"] == "kind_only"
    assert calls["scope"]["partial"] is True


def test_query_graph_absent_path_is_empty_partial_with_manifest() -> None:
    graph = _sample_graph()
    result = query_graph(graph, paths=["not-present.c"])
    assert result["nodes"] == [] and result["edges"] == []
    assert result["scope"]["partial"] is True
    assert result["scope"]["unmatched_paths"] == ["not-present.c"]
    assert result["scope"]["edge_filter"] == "empty_selection"
    assert result["source_manifest"] == graph["source_manifest"]
    assert result["provenance"] == graph["provenance"]
    assert any(item["code"] == "query_paths_not_found" for item in result["diagnostics"])


def test_query_graph_normalizes_dot_and_rejects_parent() -> None:
    graph = _sample_graph()
    dotted = query_graph(graph, paths=["./a.py"])
    assert {edge["id"] for edge in dotted["edges"]} == {"e1"}

    escaping = query_graph(graph, paths=["../a.py"])
    assert escaping["nodes"] == []
    assert escaping["scope"]["invalid_paths"] == ["../a.py"]
    assert any(item["code"] == "query_paths_invalid" for item in escaping["diagnostics"])


def test_query_graph_by_node_id_and_unknown_errors() -> None:
    graph = _sample_graph()
    focused = query_graph(graph, node_id="file:b.py")
    assert {edge["id"] for edge in focused["edges"]} == {"e1", "e2"}
    with pytest.raises(GraphError):
        query_graph(graph, kind="nope")
    with pytest.raises(GraphError):
        query_graph(graph, node_id="missing")


# ---------------------------------------------------------------------------
# import supersession
# ---------------------------------------------------------------------------


def test_prefer_resolved_imports_keeps_unrelated_unresolved() -> None:
    edges = [
        {"id": "known", "path": "a.py", "kind": "import", "status": "resolved", "expression": "from good import ok"},
        {"id": "unknown", "path": "a.py", "kind": "import", "status": "unresolved", "expression": "import missing_dependency"},
    ]
    assert {edge["id"] for edge in _prefer_resolved_imports(edges)} == {"known", "unknown"}


def test_prefer_resolved_imports_supersedes_same_target() -> None:
    edges = [
        {"id": "resolved", "path": "main.js", "kind": "import", "status": "resolved", "expression": "./util"},
        {"id": "decl", "path": "main.js", "kind": "import", "status": "unresolved", "expression": "require('./util')"},
        {"id": "other", "path": "main.js", "kind": "import", "status": "unresolved", "expression": "require('./other')"},
    ]
    assert {edge["id"] for edge in _prefer_resolved_imports(edges)} == {"resolved", "other"}


# ---------------------------------------------------------------------------
# Joern payload normalization (synthetic, no JVM)
# ---------------------------------------------------------------------------


def _joern_payload() -> dict:
    return {
        "methods": [
            {"name": "helper", "fullName": "helper", "file": "a.c", "line": 1,
             "signature": "int helper(int)", "nodeId": 1},
            {"name": "helper", "fullName": "helper", "file": "b.c", "line": 1,
             "signature": "int helper(int)", "nodeId": 2},
        ],
        "calls": [
            {"caller": "helper", "callerId": 1, "callerFile": "a.c", "line": 2,
             "name": "external", "code": "external()", "methodFullName": "external",
             "callees": [{"nodeId": 9, "fullName": "external", "external": True}], "nodeId": 10},
            {"caller": "helper", "callerId": 1, "callerFile": "a.c", "line": 3,
             "name": "ambiguous", "code": "ambiguous()", "methodFullName": "ambiguous",
             "callees": [{"nodeId": 2, "fullName": "helper", "external": False},
                         {"nodeId": 1, "fullName": "helper", "external": False}], "nodeId": 11},
            {"caller": "helper", "callerId": 1, "callerFile": "a.c", "line": 4,
             "name": "unresolved", "code": "unresolved()", "methodFullName": "unresolved",
             "callees": [], "nodeId": 12},
        ],
        "cfg": [
            {"method": "helper", "methodId": 1, "file": "a.c", "line": 1, "nodeId": 1,
             "nodes": [
                 {"i": 0, "label": "BLOCK", "line": 1, "column": 1, "order": 1, "code": "{",
                  "file": "a.c", "ownerMethod": "helper", "nodeId": 20},
                 {"i": 1, "label": "RETURN", "line": 4, "column": 3, "order": 2, "code": "return acc;",
                  "file": "a.c", "ownerMethod": "helper", "nodeId": 21},
             ],
             "edges": [{"from": 0, "to": 1}]},
        ],
        "imports": [{"file": "a.c", "code": '#include "helper.h"', "nodeId": 30}],
        "reachingDefs": [
            {"source": {"label": "IDENTIFIER", "line": 2, "column": 3, "code": "acc",
                        "file": "a.c", "ownerMethod": "helper", "nodeId": 40},
             "target": {"label": "RETURN", "line": 4, "column": 3, "code": "return acc;",
                        "file": "a.c", "ownerMethod": "helper", "nodeId": 21}},
            {"source": {"label": "METHOD_PARAMETER_IN", "line": 1, "column": 13, "code": "int x",
                        "file": "a.c", "ownerMethod": "helper", "nodeId": 41},
             "target": {"label": "IDENTIFIER", "line": 5, "column": 3, "code": "x",
                        "file": "b.c", "ownerMethod": "other", "nodeId": 42}},
        ],
        "dataflowPaths": [],
        "dataflowErrors": [],
    }


def test_normalize_same_name_caller_uses_native_id() -> None:
    nodes, edges = _normalize_joern_payload(_joern_payload(), "probe")
    by_id = {node["id"]: node for node in nodes}
    call = next(edge for edge in edges if edge.get("expression") == "external()")
    assert by_id[call["source"]]["path"] == "a.c"


def test_normalize_preserves_ambiguous_callees() -> None:
    nodes, edges = _normalize_joern_payload(_joern_payload(), "probe")
    ambiguous = next(edge for edge in edges if edge.get("expression") == "ambiguous()")
    assert ambiguous["status"] == "ambiguous"
    assert ambiguous["target"] is None
    assert len(ambiguous["candidates"]) == 2
    unresolved = next(edge for edge in edges if edge.get("expression") == "unresolved()")
    assert unresolved["status"] == "unresolved"
    external = next(edge for edge in edges if edge.get("expression") == "external()")
    assert external["status"] == "external"


def test_normalize_ids_are_namespaced_and_referential() -> None:
    nodes, edges = _normalize_joern_payload(_joern_payload(), "probe", namespace="cpg:a")
    ids = {node["id"] for node in nodes}
    for edge in edges:
        assert edge["source"] is None or edge["source"] in ids
        assert edge["target"] is None or edge["target"] in ids
    assert all("/" in node["id"] or node["id"].startswith("file:") for node in nodes)
    # two same-name methods stay distinct
    method_ids = [node["id"] for node in nodes if node["kind"] in ("function", "method")]
    assert len(method_ids) == len(set(method_ids)) == 2


def test_normalize_reaching_def_scope_labels() -> None:
    nodes, edges = _normalize_joern_payload(_joern_payload(), "probe")
    scopes = {edge["scope"] for edge in edges if edge["kind"] == "dataflow"}
    assert scopes == {"reaching_def_intra", "reaching_def_inter"}
    assert all(edge["status"] == "resolved" for edge in edges if edge["kind"] == "dataflow")


def test_normalize_drops_synthetic_calls() -> None:
    payload = _joern_payload()
    payload["calls"].append({"caller": "helper", "callerId": 1, "callerFile": "a.c", "line": 9,
                             "name": "<operator>.assignment", "code": "x = 1", "methodFullName": "",
                             "callees": [], "nodeId": 99})
    _, edges = _normalize_joern_payload(payload, "probe")
    assert all(edge.get("expression") != "x = 1" for edge in edges)


# ---------------------------------------------------------------------------
# capability statuses
# ---------------------------------------------------------------------------


def test_capabilities_distinguish_empty_partial_and_resolved() -> None:
    empty_payload = {"methods": [{"name": "m", "fullName": "m", "file": "a.c", "line": 1, "nodeId": 1}],
                     "calls": [], "cfg": [], "imports": [], "reachingDefs": []}
    caps = {c["graph"]: c for c in _capabilities_for("c", empty_payload, "1")}
    assert caps["call"]["status"] == "empty"
    assert caps["cfg"]["status"] == "empty"
    assert caps["dataflow"]["status"] == "empty"
    assert caps["import"]["status"] == "empty"

    resolved_payload = _joern_payload()
    resolved_payload["cfg"][0]["edges"] = [{"from": 0, "to": 1}]
    caps = {c["graph"]: c for c in _capabilities_for("c", resolved_payload, "1")}
    assert caps["call"]["status"] == "partial"  # has ambiguous + unresolved
    assert caps["cfg"]["status"] == "resolved"
    assert caps["dataflow"]["status"] == "resolved"


def test_capabilities_carry_conditions() -> None:
    caps = {c["graph"]: c for c in _capabilities_for("cpp", _joern_payload(), "1")}
    assert "virtual" in (caps["call"]["condition"] or "")
    assert "build" in (caps["call"]["condition"] or "")


def test_merge_capabilities_prefers_best_and_keeps_unavailable() -> None:
    fragments = [
        {"capabilities": [{"language": "javascript", "graph": "import",
                           "backend": "joern", "status": "partial"}]},
        {"capabilities": [{"language": "javascript", "graph": "import",
                           "backend": "dependency-cruiser", "status": "resolved"}]},
    ]
    extra = [{"language": "javascript", "graph": "call", "backend": "joern",
              "status": "unavailable", "limitations": "joern not found"}]
    merged = {c["graph"]: c for c in _merge_capabilities(fragments, ["javascript"], extra)}
    assert merged["import"]["backend"] == "dependency-cruiser"
    assert merged["call"]["status"] == "unavailable"


# ---------------------------------------------------------------------------
# language registry
# ---------------------------------------------------------------------------


def test_available_graph_languages_covers_registry() -> None:
    languages = available_graph_languages()["languages"]
    for name in ("c", "cpp", "python", "javascript", "typescript", "tsx", "java",
                 "go", "ruby", "rust", "php", "c_sharp", "kotlin", "swift"):
        assert languages[name]["backends"].get("joern") is True
    assert languages["python"]["backends"]["grimp"] is True
    assert languages["tsx"]["backends"]["dependency-cruiser"] is True


# ---------------------------------------------------------------------------
# no-backend must not be an empty success
# ---------------------------------------------------------------------------


def test_no_backend_raises_instead_of_empty_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "a.php").write_text("<?php\n", encoding="utf-8")
    monkeypatch.delenv("CBE_JOERN_HOME", raising=False)
    monkeypatch.delenv("CBE_DEPCRUISE_BIN", raising=False)
    monkeypatch.setenv("PATH", "")
    with pytest.raises(GraphError):
        analyze_graph(tmp_path, tmp_path / "out.json", backend="imports",
                      languages=["php"], depcruise_bin=None, joern_home=None)


# ---------------------------------------------------------------------------
# real integration (skipped without installed toolchains)
# ---------------------------------------------------------------------------

_JOERN = os.environ.get("CBE_JOERN_HOME")
_DEPCRUISE = os.environ.get("CBE_DEPCRUISE_BIN")


@pytest.mark.skipif(not _JOERN, reason="CBE_JOERN_HOME is not set")
def test_joern_integration_c_relation(tmp_path: Path) -> None:
    graph = analyze_graph(FIXTURES / "c_relation", tmp_path / "c.json",
                          backend="joern", languages=["c"],
                          joern_home=Path(_JOERN), timeout=600)
    calls = [edge for edge in graph["edges"]
             if edge["kind"] == "call" and edge["status"] == "resolved"
             and edge.get("expression", "").strip().startswith("compute")]
    assert calls, "expected a resolved main->compute call"
    nodes = {node["id"]: node for node in graph["nodes"]}
    assert nodes[calls[0]["source"]]["path"] == "main.c"
    assert graph["provenance"]["source_stable"] is True
    assert graph["provenance"]["fingerprint"].startswith("gp_")
    dataflow = [edge for edge in graph["edges"] if edge["kind"] == "dataflow"]
    assert dataflow and all(edge["scope"].startswith("reaching_def") for edge in dataflow)
    capability = next(item for item in graph["capabilities"]
                      if item["language"] == "c" and item["graph"] == "call")
    assert capability["status"] == "resolved"


@pytest.mark.skipif(not (_JOERN and _DEPCRUISE), reason="CBE_JOERN_HOME / CBE_DEPCRUISE_BIN not set")
def test_integration_js_import_and_unresolved_call(tmp_path: Path) -> None:
    graph = analyze_graph(FIXTURES / "js_relation", tmp_path / "js.json",
                          backend="auto", languages=["javascript"],
                          joern_home=Path(_JOERN), depcruise_bin=Path(_DEPCRUISE), timeout=600)
    imports = {edge["source"]: edge["target"] for edge in graph["edges"]
               if edge["kind"] == "import" and edge["status"] == "resolved"}
    assert imports.get("file:main.js") == "file:util.js"
    capability = next(item for item in graph["capabilities"]
                      if item["language"] == "javascript" and item["graph"] == "import")
    assert capability["status"] == "resolved"


@pytest.mark.skipif(not _JOERN, reason="CBE_JOERN_HOME is not set")
def test_integration_tsx_extra_language(tmp_path: Path) -> None:
    graph = analyze_graph(FIXTURES / "tsx_relation", tmp_path / "tsx.json",
                          backend="joern", languages=["tsx"],
                          joern_home=Path(_JOERN), timeout=600)
    languages = {entry["language"] for entry in graph["source_manifest"]}
    assert languages == {"tsx"}
    capability = next(item for item in graph["capabilities"]
                      if item["language"] == "tsx" and item["graph"] == "call")
    assert capability["status"] in {"resolved", "partial"}
    calls = [edge for edge in graph["edges"]
             if edge["kind"] == "call" and "classify" in edge.get("expression", "")]
    assert calls, "expected a run->classify call in the TSX route"


@pytest.mark.skipif(not os.environ.get("CBE_GRIMP_TEST"), reason="set CBE_GRIMP_TEST to run grimp integration")
def test_integration_python_import(tmp_path: Path) -> None:
    graph = analyze_graph(FIXTURES / "python_relation", tmp_path / "py.json",
                          backend="imports", languages=["python"], timeout=120)
    imports = {edge["source"]: edge["target"] for edge in graph["edges"]
               if edge["kind"] == "import" and edge["status"] == "resolved"}
    assert imports.get("module:app.main") == "module:app.util"


def test_graph_output_is_json_serializable() -> None:
    graph = _sample_graph()
    text = json.dumps(graph)
    assert json.loads(text)["schema"] == "cbe-graph/1"
