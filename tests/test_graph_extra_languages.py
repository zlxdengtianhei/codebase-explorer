"""Real Joern coverage for the six additional source languages.

The priority-language contract lives in ``tests/test_graph.py``.  This module
covers the languages a user explicitly asked us to expose beyond that set:
ruby, rust, php, c_sharp, kotlin and swift.  Each integration test copies its
fixture to a neutral temp path (the Ruby frontend silently skips paths whose
component is ``test``/``tests``/``spec``) and runs the real Joern frontend.

The deterministic tests never need a JVM; the integration tests are skipped
unless ``CBE_JOERN_HOME`` points at an installed Joern 4.x.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from cbe.graph import analyze_graph, graph_suffixes
from cbe.graph_backends.joern import (
    JOERN_LANGUAGE_FLAGS,
    _capabilities_for,
    _first_error_line,
)

FIXTURES = Path(__file__).parent / "fixtures" / "graphs" / "extra"
_JOERN = os.environ.get("CBE_JOERN_HOME")
_JOERN_HOME = Path(_JOERN) if _JOERN else None


def _copy_case(tmp_path: Path, name: str) -> Path:
    destination = tmp_path / "case" / name
    shutil.copytree(FIXTURES / name, destination)
    return destination


def _resolved_calls(graph: dict) -> list[dict]:
    nodes = {node["id"]: node for node in graph["nodes"]}
    result = []
    for edge in graph["edges"]:
        if edge["kind"] != "call" or edge["status"] != "resolved":
            continue
        source, target = nodes.get(edge["source"]), nodes.get(edge["target"])
        if source and target:
            result.append({"source": source, "target": target, "expression": edge.get("expression", "")})
    return result


def _capability(graph: dict, language: str, kind: str) -> dict:
    return next(c for c in graph["capabilities"]
                if c["language"] == language and c["graph"] == kind)


# ---------------------------------------------------------------------------
# deterministic
# ---------------------------------------------------------------------------


def test_first_error_line_prefers_actionable_cause() -> None:
    text = (
        "2026-10-13 16:00:47.815 ERROR ExternalCommand$          Process exited with code 1.\n"
        "Error: failed to load the Rust project at `/Users/secret/repo`. "
        "Are `cargo` and `rustc` on your PATH?\n"
        "java.lang.RuntimeException: [rust_ast_gen::cargo] loading workspace\n"
    )
    line = _first_error_line(text, ["/Users/secret/repo"])
    assert "failed to load the Rust project" in line
    assert "PATH" in line
    assert "/Users/secret/repo" not in line
    assert line.count("<path>") == 1


def test_first_error_line_returns_none_without_markers() -> None:
    assert _first_error_line("all good\nno problems here\n", []) is None


def test_language_flags_cover_registry_languages() -> None:
    registry = set(graph_suffixes().values())
    missing = registry - set(JOERN_LANGUAGE_FLAGS)
    assert not missing, f"registry languages without a Joern frontend route: {sorted(missing)}"
    assert JOERN_LANGUAGE_FLAGS["c_sharp"] == "csharpsrc"
    assert JOERN_LANGUAGE_FLAGS["rust"] == "rust"


def test_capabilities_failed_when_frontend_errored() -> None:
    caps = {c["graph"]: c for c in _capabilities_for("rust", {}, "1", frontend_error="boom")}
    assert set(caps) == {"call", "cfg", "dataflow", "import"}
    assert all(c["status"] == "failed" for c in caps.values())
    assert "boom" in caps["call"]["limitations"]


def test_ruby_capability_documents_test_path_exclusion() -> None:
    caps = {c["graph"]: c for c in _capabilities_for("ruby", {}, "1")}
    assert "test" in (caps["call"]["condition"] or "")


# ---------------------------------------------------------------------------
# real integration
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _JOERN_HOME, reason="CBE_JOERN_HOME is not set")
def test_ruby_extra_language(tmp_path: Path) -> None:
    repo = _copy_case(tmp_path, "ruby")
    graph = analyze_graph(repo, tmp_path / "ruby.json", backend="joern", languages=["ruby"],
                          joern_home=_JOERN_HOME, timeout=600)
    calls = _resolved_calls(graph)
    assert any(call["target"]["path"].endswith("helper.rb")
               and "compute" in call["expression"] for call in calls)
    assert _capability(graph, "ruby", "call")["status"] == "resolved"
    assert _capability(graph, "ruby", "cfg")["status"] == "resolved"


@pytest.mark.skipif(not _JOERN_HOME, reason="CBE_JOERN_HOME is not set")
def test_rust_extra_language(tmp_path: Path) -> None:
    repo = _copy_case(tmp_path, "rust")
    graph = analyze_graph(repo, tmp_path / "rust.json", backend="joern", languages=["rust"],
                          joern_home=_JOERN_HOME, timeout=600)
    calls = _resolved_calls(graph)
    assert any(call["target"]["path"].endswith("helper.rs")
               and "helper::compute" in call["expression"] for call in calls)
    assert _capability(graph, "rust", "call")["status"] == "resolved"


@pytest.mark.skipif(not _JOERN_HOME, reason="CBE_JOERN_HOME is not set")
def test_rust_without_cargo_is_failed_not_empty(tmp_path: Path) -> None:
    repo = tmp_path / "flat_rust"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "main.rs").write_text("fn main() { println!(\"hi\"); }\n", encoding="utf-8")
    graph = analyze_graph(repo, tmp_path / "flat.json", backend="joern", languages=["rust"],
                          joern_home=_JOERN_HOME, timeout=600)
    assert _capability(graph, "rust", "call")["status"] == "failed"
    assert any(d["code"] == "frontend_error" for d in graph["diagnostics"])
    assert not any(c["status"] == "empty" for c in graph["capabilities"] if c["language"] == "rust")


@pytest.mark.skipif(not _JOERN_HOME, reason="CBE_JOERN_HOME is not set")
def test_c_sharp_extra_language(tmp_path: Path) -> None:
    repo = _copy_case(tmp_path, "csharp")
    graph = analyze_graph(repo, tmp_path / "cs.json", backend="joern", languages=["c_sharp"],
                          joern_home=_JOERN_HOME, timeout=600)
    calls = _resolved_calls(graph)
    assert any("Helper.Compute" in call["expression"] for call in calls)
    assert _capability(graph, "c_sharp", "call")["status"] == "resolved"


@pytest.mark.skipif(not _JOERN_HOME, reason="CBE_JOERN_HOME is not set")
def test_kotlin_extra_language(tmp_path: Path) -> None:
    repo = _copy_case(tmp_path, "kotlin")
    graph = analyze_graph(repo, tmp_path / "kt.json", backend="joern", languages=["kotlin"],
                          joern_home=_JOERN_HOME, timeout=600)
    calls = _resolved_calls(graph)
    assert any("Helper.compute" in call["expression"] for call in calls)
    assert _capability(graph, "kotlin", "call")["status"] == "resolved"


@pytest.mark.skipif(not _JOERN_HOME, reason="CBE_JOERN_HOME is not set")
def test_swift_extra_language_parses_but_cross_file_is_partial(tmp_path: Path) -> None:
    repo = _copy_case(tmp_path, "swift")
    graph = analyze_graph(repo, tmp_path / "swift.json", backend="joern", languages=["swift"],
                          joern_home=_JOERN_HOME, timeout=600)
    method_names = {node["name"] for node in graph["nodes"] if node["kind"] in ("function", "method")}
    assert any("compute" in (name or "") for name in method_names)
    assert _capability(graph, "swift", "call")["status"] == "partial"
    assert _capability(graph, "swift", "cfg")["status"] == "resolved"


@pytest.mark.skipif(shutil.which("php") is not None, reason="php is installed; the failure path is unreachable")
@pytest.mark.skipif(not _JOERN_HOME, reason="CBE_JOERN_HOME is not set")
def test_php_without_runtime_is_failed_with_cause(tmp_path: Path) -> None:
    repo = _copy_case(tmp_path, "php")
    graph = analyze_graph(repo, tmp_path / "php.json", backend="joern", languages=["php"],
                          joern_home=_JOERN_HOME, timeout=600)
    assert _capability(graph, "php", "call")["status"] == "failed"
    assert any(d["code"] == "backend_error" and "php" in d["message"].lower()
               for d in graph["diagnostics"])


@pytest.mark.skipif(not _JOERN_HOME, reason="CBE_JOERN_HOME is not set")
def test_extra_language_context_build_ruby(tmp_path: Path) -> None:
    pytest.importorskip("tree_sitter_ruby")
    from cbe.source_context import build_context

    repo = _copy_case(tmp_path, "ruby")
    out = tmp_path / "ruby.json"
    analyze_graph(repo, out, backend="joern", languages=["ruby"],
                  joern_home=_JOERN_HOME, timeout=600)
    context = build_context(repo, graph_path=out)
    assert context["schema"] == "cbe-context/1"
    assert context["chunks"]
    assert context["graph"] is not None
