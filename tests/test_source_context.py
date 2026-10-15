"""Tests for the multi-language source-context contract.

These tests check real behaviour, not JSON shape: byte-exact reconstruction,
grammar-derived boundaries, Unicode/CRLF coordinates, distinguishable
failures, graph drift rejection and local graph pruning.  Each of them can go
red on a wrong partition or a wrong graph decision.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cbe.source_context import (
    ContextError,
    GRAMMARS,
    GrammarSpec,
    GraphSourceMismatch,
    _collect_named_boundaries,
    _grammar_for_suffix,
    _load_graph,
    _make_parser,
    available_languages,
    build_context,
    context_for_paths,
    language_for_path,
    register_language,
)

FIXTURES = Path(__file__).parent / "fixtures" / "source_context"

ALL_SUPPORTED = [
    "sample.c",
    "sample.cpp",
    "sample.py",
    "sample.js",
    "sample.ts",
    "Sample.java",
    "sample.go",
]

# (kind, name) pairs that a correct grammar-driven partition must contain.
EXPECTED_DECLARATIONS = {
    "sample.c": [("function", "add"), ("function", "main"), ("struct", "Point")],
    "sample.cpp": [
        ("function", "maximum"),
        ("class", "Box"),
        ("method", "get"),
        ("namespace", "demo"),
    ],
    "sample.py": [
        ("function", "top"),
        ("function", "inner"),
        ("class", "Greeter"),
        ("method", "greet"),
    ],
    "sample.js": [
        ("function", "compute"),
        ("function", "double"),
        ("function", "asyncArrow"),
        ("class", "Widget"),
        ("method", "render"),
    ],
    "sample.ts": [
        ("interface", "Shape"),
        ("type_alias", "Alias"),
        ("enum", "Color"),
        ("function", "apply"),
        ("class", "Circle"),
        ("method", "area"),
    ],
    "Sample.java": [
        ("class", "Main"),
        ("constructor", "Main"),
        ("method", "add"),
        ("method", "run"),
        ("interface", "Greeter"),
        ("enum", "Color"),
    ],
    "sample.go": [("type", "Point"), ("method", "Sum"), ("function", "outer")],
}

# Joern extra native frontends wired with mature tree-sitter grammars.
EXTRA_LANGUAGES = {
    "sample.rb": [
        ("function", "top"),
        ("class", "Greeter"),
        ("method", "greet"),
        ("module", "Util"),
        ("method", "helper"),
    ],
    "sample.rs": [
        ("function", "top"),
        ("function", "main"),
        ("struct", "Point"),
        ("impl", "Point"),
        ("method", "sum"),
        ("module", "util"),
        ("function", "helper"),
    ],
    "sample.php": [
        ("function", "top"),
        ("class", "Greeter"),
        ("method", "greet"),
        ("interface", "Shape"),
        ("method", "area"),
    ],
    "Sample.cs": [
        ("class", "Greeter"),
        ("constructor", "Greeter"),
        ("method", "Greet"),
        ("method", "Add"),
        ("interface", "IShape"),
        ("class", "Program"),
        ("method", "Main"),
    ],
    "sample.kt": [
        ("function", "top"),
        ("class", "Greeter"),
        ("method", "greet"),
        ("object", "Util"),
    ],
    "sample.swift": [
        ("class", "Point"),
        ("function", "top"),
        ("class", "Greeter"),
        ("constructor", "init"),
        ("method", "greet"),
        ("protocol", "Shape"),
        ("method", "area"),
    ],
}


def _chunks_of(context, path):
    return sorted(
        (chunk for chunk in context["chunks"] if chunk["path"] == path),
        key=lambda item: item["start_byte"],
    )


def test_discovery_finds_supported_files_without_python_only_scan(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "m.py").write_text("def f():\n    return 1\n")
    (tmp_path / "GoFile.go").write_text("package main\n\nfunc main() {}\n")
    (tmp_path / "notes.txt").write_text("not source\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.js").write_text("module.exports = 1;\n")
    context = build_context(tmp_path)
    paths = {f["path"] for f in context["files"]}
    assert paths == {"sub/m.py", "GoFile.go"}
    assert all(c["path"] in paths for c in context["chunks"])


def test_full_source_reconstruction_is_byte_exact():
    context = build_context(FIXTURES, paths=ALL_SUPPORTED)
    assert context["schema"] == "cbe-context/1"
    for entry in context["files"]:
        raw = (FIXTURES / entry["path"]).read_bytes()
        chunks = _chunks_of(context, entry["path"])
        assert "".join(chunk["text"] for chunk in chunks) == raw.decode("utf-8")
        # Byte ranges are a contiguous, non-overlapping partition.
        cursor = 0
        for chunk in chunks:
            assert chunk["start_byte"] == cursor
            assert raw[chunk["start_byte"]:chunk["end_byte"]].decode("utf-8") == chunk["text"]
            assert chunk["sha256"] == _sha256(chunk["text"])
            cursor = chunk["end_byte"]
        assert cursor == len(raw)
    assert context["diagnostics"] == []


def _sha256(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.mark.parametrize("path", ALL_SUPPORTED)
def test_declarations_are_recognised(path):
    context = build_context(FIXTURES, paths=[path])
    found = {(chunk["kind"], chunk["name"]) for chunk in context["chunks"]}
    for expected in EXPECTED_DECLARATIONS[path]:
        assert expected in found, f"{path} missing {expected}; got {sorted(found)}"


@pytest.mark.parametrize("path", list(EXTRA_LANGUAGES))
def test_joern_frontend_fixture_is_chunked_when_grammar_available(path):
    languages = {entry["name"]: entry for entry in available_languages()["languages"]}
    language = language_for_path(path)
    if not languages[language]["available"]:
        pytest.skip(f"grammar for {language} not installed: {languages[language]['error']}")
    context = build_context(FIXTURES, paths=[path])
    assert not any(d["code"] in {"grammar_unavailable", "syntax_error"} for d in context["diagnostics"])
    _partition(context, path, FIXTURES)
    found = {(chunk["kind"], chunk["name"]) for chunk in context["chunks"]}
    for expected in EXTRA_LANGUAGES[path]:
        assert expected in found, f"{path} missing {expected}; got {sorted(found)}"


def test_nested_methods_do_not_duplicate_source():
    context = build_context(FIXTURES, paths=["sample.py"])
    chunks = _chunks_of(context, "sample.py")
    class_chunks = [c for c in chunks if c["kind"] == "class" and c["name"] == "Greeter"]
    assert class_chunks, "class Greeter must be a chunk"
    class_text = "".join(chunk["text"] for chunk in class_chunks)
    assert "def greet" not in class_text, "method body must not be repeated in the class chunk"
    method = next(c for c in chunks if c["kind"] == "method" and c["name"] == "greet")
    assert "def greet" in method["text"]
    assert method["parent_id"] in {chunk["symbol_id"] for chunk in class_chunks}
    assert method["ancestors"] == ["Greeter"]


def test_unicode_bytes_and_crlf_line_numbers():
    context = build_context(FIXTURES, paths=["unicode.py", "crlf.py"])
    unicode_chunks = _chunks_of(context, "unicode.py")
    names = {chunk["name"] for chunk in unicode_chunks}
    assert {"café", "Ünïcode", "emoji"} <= names
    raw = (FIXTURES / "unicode.py").read_bytes()
    for chunk in unicode_chunks:
        assert raw[chunk["start_byte"]:chunk["end_byte"]].decode("utf-8") == chunk["text"]

    crlf_chunks = _chunks_of(context, "crlf.py")
    first = next(c for c in crlf_chunks if c["name"] == "first")
    assert first["start_line"] == 2
    assert first["end_line"] == 3
    assert "\r\n" in first["text"]
    one = next(c for c in crlf_chunks if c["name"] == "one")
    assert one["start_line"] == 6
    assert one["end_line"] == 7


def test_cpp_template_and_arrow_functions_keep_their_prefix():
    context = build_context(FIXTURES, paths=["sample.cpp", "sample.ts", "sample.js"])
    maximum = next(
        c for c in _chunks_of(context, "sample.cpp") if c["name"] == "maximum" and c["kind"] == "function"
    )
    assert maximum["text"].startswith("template <typename T>")
    assert "return b;" in maximum["text"]

    apply = next(c for c in _chunks_of(context, "sample.ts") if c["name"] == "apply")
    assert apply["kind"] == "function"
    assert apply["text"].startswith("export const apply")

    double = next(c for c in _chunks_of(context, "sample.js") if c["name"] == "double")
    assert double["text"].startswith("export const double")


def test_oversized_function_splits_on_grammar_boundaries():
    context = build_context(FIXTURES, paths=["sample.go"], max_segment_bytes=30)
    outer = [c for c in _chunks_of(context, "sample.go") if c["name"] == "outer"]
    assert len(outer) > 1, "small budget must produce multiple segments"
    assert [c["segment_index"] for c in outer] == list(range(len(outer)))
    assert {c["segment_count"] for c in outer} == {len(outer)}
    assert {c["symbol_id"] for c in outer} == {outer[0]["symbol_id"]}
    assert "".join(c["text"] for c in outer).startswith("func outer()")

    raw = (FIXTURES / "sample.go").read_bytes()
    boundaries = set(_collect_named_boundaries(_parse_go(raw))[0])
    for chunk in outer:
        assert chunk["start_byte"] in boundaries
        assert chunk["end_byte"] in boundaries
    assert chunk_full_range(outer, raw) == (outer[0]["full_start_byte"], outer[-1]["full_end_byte"])


def chunk_full_range(chunks, raw):
    assert len({c["full_start_byte"] for c in chunks}) == 1
    assert len({c["full_end_byte"] for c in chunks}) == 1
    return chunks[0]["full_start_byte"], chunks[0]["full_end_byte"]


def _parse_go(raw: bytes):
    spec = _grammar_for_suffix(".go")
    return _make_parser(spec).parse(raw).root_node


def test_unknown_language_is_distinguishable_from_empty_success(tmp_path):
    (tmp_path / "empty.py").write_bytes(b"")
    (tmp_path / "mystery.xyz").write_text("hello\n")
    context = build_context(tmp_path, paths=["empty.py", "mystery.xyz"])
    codes = {(d["path"], d["code"]) for d in context["diagnostics"]}
    assert ("mystery.xyz", "unsupported_language") in codes
    assert ("empty.py", "unsupported_language") not in codes
    assert any(f["path"] == "empty.py" for f in context["files"])
    # A failed file has no chunks; a successful empty file has no chunks either.
    # The diagnostic is the only thing that distinguishes them.
    assert not [c for c in context["chunks"] if c["path"] == "mystery.xyz"]


def test_missing_grammar_package_is_a_diagnostic(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("def f():\n    return 1\n")
    import cbe.source_context as sc

    def boom(spec):
        raise ImportError("simulated missing grammar")

    monkeypatch.setattr(sc, "_make_parser", boom)
    context = build_context(tmp_path, paths=["a.py"])
    assert any(d["code"] == "grammar_unavailable" for d in context["diagnostics"])
    assert not [c for c in context["chunks"] if c["path"] == "a.py"]


def test_syntax_error_keeps_coverage_and_reports():
    context = build_context(FIXTURES, paths=["broken.c"])
    assert any(d["code"] == "syntax_error" for d in context["diagnostics"])
    raw = (FIXTURES / "broken.c").read_bytes()
    assert "".join(c["text"] for c in _chunks_of(context, "broken.c")) == raw.decode("utf-8")


def test_path_escape_and_symlink_are_rejected(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ok.py").write_text("x = 1\n")
    outside = tmp_path / "outside.py"
    outside.write_text("secret = 1\n")
    os.symlink(outside, repo / "link.py")

    for bad in ["../outside.py", "/etc/passwd", "a/../../b.py"]:
        with pytest.raises(ContextError) as excinfo:
            build_context(repo, paths=[bad])
        assert excinfo.value.code == "invalid_path"

    with pytest.raises(ContextError) as excinfo:
        build_context(repo, paths=["link.py"])
    assert excinfo.value.code == "invalid_path"


def _graph_for(context, edges):
    manifest = [
        {"path": f["path"], "language": f["language"], "sha256": f["sha256"]} for f in context["files"]
    ]
    return {
        "schema": "cbe-graph/1",
        "backend": {"name": "test", "version": "0"},
        "capabilities": {"python": {"call": "supported"}},
        "source_manifest": manifest,
        "nodes": [
            {"id": "n1", "kind": "function", "path": "sample.py", "start_line": 9, "end_line": 11, "name": "top"},
            {"id": "n2", "kind": "function", "path": "sample.py", "start_line": 4, "end_line": 5, "name": "decorate"},
            {"id": "n3", "kind": "function", "path": "sample.c", "start_line": 9, "end_line": 11, "name": "add"},
            {"id": "ext", "kind": "external", "path": None, "start_line": None, "end_line": None, "name": "lib"},
        ],
        "edges": edges,
        "diagnostics": [],
    }


EDGES = [
    {"id": "e1", "source": "n1", "target": "n2", "kind": "call", "status": "resolved"},
    {"id": "e2", "source": "n1", "target": "ext", "kind": "call", "status": "external"},
    {"id": "e3", "source": "n3", "target": "n2", "kind": "import", "status": "ambiguous"},
]


def test_graph_is_included_when_manifest_matches(tmp_path):
    base = build_context(FIXTURES, paths=["sample.py", "sample.c"])
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(_graph_for(base, EDGES)))
    context = build_context(FIXTURES, paths=["sample.py", "sample.c"], graph_path=graph_path)
    assert context["graph_status"] == "provided"
    assert context["graph"]["backend"]["name"] == "test"


def test_graph_source_drift_is_rejected(tmp_path):
    base = build_context(FIXTURES, paths=["sample.py"])
    graph = _graph_for(base, EDGES)
    graph["source_manifest"] = [
        {**entry, "sha256": "0" * 64} if entry["path"] == "sample.py" else entry
        for entry in graph["source_manifest"]
    ]
    graph_path = tmp_path / "drift.json"
    graph_path.write_text(json.dumps(graph))
    with pytest.raises(GraphSourceMismatch) as excinfo:
        build_context(FIXTURES, paths=["sample.py"], graph_path=graph_path)
    assert excinfo.value.details["path"] == "sample.py"
    assert excinfo.value.details["actual"] != excinfo.value.details["expected"]


def test_graph_drift_in_unselected_boundary_dependency_is_rejected(tmp_path):
    # The graph manifest may cover files that this particular build did not
    # select.  A drifted boundary dependency must still be rejected.
    base = build_context(FIXTURES, paths=["sample.py", "sample.c"])
    graph = _graph_for(base, EDGES)
    graph["source_manifest"] = [
        {**entry, "sha256": "1" * 64} if entry["path"] == "sample.c" else entry
        for entry in graph["source_manifest"]
    ]
    graph_path = tmp_path / "boundary-drift.json"
    graph_path.write_text(json.dumps(graph))
    with pytest.raises(GraphSourceMismatch) as excinfo:
        build_context(FIXTURES, paths=["sample.py"], graph_path=graph_path)
    assert excinfo.value.details["path"] == "sample.c"


def test_graph_manifest_without_source_manifest_is_rejected(tmp_path):
    graph_path = tmp_path / "no-manifest.json"
    graph_path.write_text(json.dumps({"schema": "cbe-graph/1", "nodes": [], "edges": []}))
    with pytest.raises(ContextError) as excinfo:
        build_context(FIXTURES, paths=["sample.py"], graph_path=graph_path)
    assert excinfo.value.code == "graph_manifest_missing"


def test_context_for_paths_prunes_graph_but_keeps_boundary_nodes(tmp_path):
    base = build_context(FIXTURES, paths=["sample.py", "sample.c"])
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(_graph_for(base, EDGES)))
    context = build_context(FIXTURES, paths=["sample.py", "sample.c"], graph_path=graph_path)

    local = context_for_paths(context, ["sample.py"])
    assert {f["path"] for f in local["files"]} == {"sample.py"}
    assert {c["path"] for c in local["chunks"]} == {"sample.py"}
    node_ids = {n["id"] for n in local["graph"]["nodes"]}
    # n1/n2 are local; ext and n3 are boundary endpoints of kept edges.
    assert {"n1", "n2", "ext", "n3"} <= node_ids
    assert {e["id"] for e in local["graph"]["edges"]} == {"e1", "e2", "e3"}
    assert local["graph"]["scope"]["partial"] is True
    assert local["graph"]["capabilities"] == {"python": {"call": "supported"}}

    only_c = context_for_paths(context, ["sample.c"])
    assert {n["id"] for n in only_c["graph"]["nodes"]} == {"n3", "n2"}


def test_context_for_paths_rejects_escape():
    base = build_context(FIXTURES, paths=["sample.py"])
    with pytest.raises(ContextError):
        context_for_paths(base, ["../sample.py"])


def test_graph_manifest_path_escape_is_rejected(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ok.py").write_text("x = 1\n")
    outside = tmp_path / "outside.py"
    outside.write_text("secret = 1\n")
    for bad in ["../outside.py", "/etc/passwd", "sub/../../outside.py"]:
        graph_path = tmp_path / "graph.json"
        graph_path.write_text(
            json.dumps({"schema": "cbe-graph/1", "source_manifest": [{"path": bad, "sha256": "0" * 64}]})
        )
        with pytest.raises(ContextError) as excinfo:
            build_context(repo, paths=["ok.py"], graph_path=graph_path)
        assert excinfo.value.code == "graph_source_mismatch"
        assert excinfo.value.details["reason"] == "invalid_path"


def test_graph_manifest_external_symlink_is_rejected(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ok.py").write_text("x = 1\n")
    outside = tmp_path / "outside.py"
    outside.write_text("secret = 1\n")
    os.symlink(outside, repo / "link.py")
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(
        json.dumps(
            {"schema": "cbe-graph/1", "source_manifest": [{"path": "link.py", "sha256": "0" * 64}]}
        )
    )
    with pytest.raises(ContextError) as excinfo:
        build_context(repo, paths=["ok.py"], graph_path=graph_path)
    assert excinfo.value.details["reason"] == "invalid_path"


def test_graph_compares_against_the_frozen_chunk_hash(tmp_path):
    """A file changed after the chunks were frozen must not pass a second read."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("changed after freeze\n")
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(
        json.dumps({"schema": "cbe-graph/1", "source_manifest": [{"path": "a.py", "sha256": "a" * 64}]})
    )
    # Frozen hash (what the chunks were built from) matches the graph: accepted
    # even though the on-disk bytes are different.
    assert _load_graph(graph_path, repo, {"a.py": "a" * 64})["schema"] == "cbe-graph/1"
    # Frozen hash differs from the graph: rejected, and the disk content is
    # irrelevant because it is not the chunk source.
    with pytest.raises(GraphSourceMismatch) as excinfo:
        _load_graph(graph_path, repo, {"a.py": "b" * 64})
    assert excinfo.value.details["actual"] == "b" * 64
    # A boundary dependency not in the frozen set is read once from disk; the
    # on-disk bytes do not match the graph, so it is rejected.
    with pytest.raises(GraphSourceMismatch):
        _load_graph(graph_path, repo, {})


def test_context_for_paths_keeps_the_full_manifest(tmp_path):
    base = build_context(FIXTURES, paths=["sample.py", "sample.c"])
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(_graph_for(base, EDGES)))
    context = build_context(FIXTURES, paths=["sample.py", "sample.c"], graph_path=graph_path)
    full_manifest = context["graph"]["source_manifest"]
    assert {entry["path"] for entry in full_manifest} == {"sample.py", "sample.c"}
    local = context_for_paths(context, ["sample.py"])
    # The local graph may reference sample.c boundary nodes, so its provenance
    # manifest must stay complete rather than pretend to be a one-file graph.
    assert local["graph"]["source_manifest"] == full_manifest
    assert local["graph"]["scope"]["partial"] is True


def test_register_language_adds_a_suffix_through_one_path(tmp_path):
    custom = GrammarSpec(
        name="c-custom",
        suffixes=(".cst",),
        module="tree_sitter_c",
        attr="language",
        function_kinds={"function_definition": "function"},
        class_kinds={"struct_specifier": "struct"},
        wrappers=frozenset(),
        value_function_kinds=frozenset(),
    )
    register_language(custom)
    try:
        (tmp_path / "a.cst").write_text("int f(void) { return 1; }\n")
        context = build_context(tmp_path, paths=["a.cst"])
        assert any(c["kind"] == "function" and c["name"] == "f" for c in context["chunks"])
        assert language_for_path("a.cst") == "c-custom"
        assert any(entry["name"] == "c-custom" for entry in available_languages()["languages"])
    finally:
        import cbe.source_context as sc

        sc._EXTRA_SPECS.pop("c-custom", None)


def test_c_header_reports_its_language_ambiguity(tmp_path):
    (tmp_path / "api.h").write_text("int add(int a, int b);\n")
    context = build_context(tmp_path, paths=["api.h"])
    assert any(d["code"] == "ambiguous_language" for d in context["diagnostics"])
    # Still chunked, not silently dropped.
    assert any(c["path"] == "api.h" for c in context["chunks"])


def test_registered_overrides_resolve_ambiguous_suffix(tmp_path):
    cpp_spec = next(s for s in GRAMMARS if s.name == "cpp")
    hpp_override = GrammarSpec(
        name="cpp-h",
        suffixes=(".h",),
        module=cpp_spec.module,
        attr=cpp_spec.attr,
        function_kinds=cpp_spec.function_kinds,
        class_kinds=cpp_spec.class_kinds,
        wrappers=cpp_spec.wrappers,
        value_function_kinds=cpp_spec.value_function_kinds,
    )
    register_language(hpp_override)
    try:
        assert language_for_path("api.h") == "cpp-h"
        (tmp_path / "api.h").write_text("template <typename T>\nT maxv(T a, T b) { return a > b ? a : b; }\n")
        context = build_context(tmp_path, paths=["api.h"])
        assert not any(d["code"] == "ambiguous_language" for d in context["diagnostics"])
        assert any(c["kind"] == "function" and c["name"] == "maxv" for c in context["chunks"])
    finally:
        import cbe.source_context as sc

        sc._EXTRA_SPECS.pop("cpp-h", None)


def test_language_discovery_covers_priority_and_extra_languages():
    languages = {entry["name"]: entry for entry in available_languages()["languages"]}
    # Priority list plus the extra representative language.
    for name in ["c", "cpp", "python", "javascript", "typescript", "java", "go"]:
        assert name in languages
        assert languages[name]["available"] is True, f"{name} grammar unavailable: {languages[name]['error']}"
    assert language_for_path("x.tsx") == "tsx"
    assert language_for_path("x.unknown") is None
    # The registry is the single discovery path: an extra language is visible
    # without touching the priority list.
    assert "go" in languages
    # Joern extra native frontends: the spec is always registered (implemented),
    # while availability and fixture verification depend on the installed
    # grammar.  This distinguishes implemented / installed / verified.
    for name in ["ruby", "rust", "php", "c_sharp", "kotlin", "swift"]:
        assert name in languages, f"{name} spec is not registered"
    assert languages["ruby"]["joern_frontends"] == ["rubysrc2cpg"]
    assert languages["kotlin"]["provenance"] == "community"
    assert languages["go"]["joern_frontends"] == ["gosrc2cpg"]


def _partition(context, path, repo):
    raw = (repo / path).read_bytes()
    chunks = _chunks_of(context, path)
    assert "".join(c["text"] for c in chunks) == raw.decode("utf-8")
    cursor = 0
    for chunk in chunks:
        assert chunk["start_byte"] == cursor, (path, chunk["start_byte"], cursor)
        assert raw[chunk["start_byte"]:chunk["end_byte"]].decode("utf-8") == chunk["text"]
        assert chunk["sha256"] == _sha256(chunk["text"])
        cursor = chunk["end_byte"]
    assert cursor == len(raw)
    return raw, chunks


def _named_boundaries(repo, path):
    raw = (repo / path).read_bytes()
    spec = _grammar_for_suffix(Path(path).suffix)
    root = _make_parser(spec).parse(raw).root_node
    return set(_collect_named_boundaries(root)[0])


def test_unicode_crlf_and_small_budget_share_real_byte_boundaries(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "uni.py").write_bytes(
        "# \u4e2d\u6587\U0001f600\ndef f():\n    x = \"\u4e2d\u6587\u5185\u5bb9\"\n    y = 12345\n    return x + str(y)\n".encode("utf-8")
    )
    (repo / "crlf.py").write_bytes("# \u6ce8\u91ca\r\ndef g(a):\r\n    return a + 1\r\n".encode("utf-8"))
    max_bytes = 16
    context = build_context(repo, paths=["uni.py", "crlf.py"], max_segment_bytes=max_bytes)
    for path in ("uni.py", "crlf.py"):
        raw, chunks = _partition(context, path, repo)
        boundaries = _named_boundaries(repo, path)
        for chunk in chunks:
            # Every endpoint is a real tree-sitter named-node byte boundary.
            assert chunk["start_byte"] in boundaries
            assert chunk["end_byte"] in boundaries
        # A chunk above the byte target is only allowed with an explicit
        # oversized-token diagnostic for an indivisible lexeme.
        oversized = [c for c in chunks if c["end_byte"] - c["start_byte"] > max_bytes]
        flags = [d for d in context["diagnostics"] if d["code"] == "oversized_token" and d["path"] == path]
        assert len(flags) == len(oversized), (path, oversized, flags)
        line_count = len(raw.decode("utf-8").splitlines())
        for chunk in chunks:
            assert 1 <= chunk["start_line"] <= chunk["end_line"] <= line_count + 1


def test_sibling_bindings_reconstruct_once_and_stay_addressable(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "siblings.js").write_bytes(b"export const a = () => 1, b = () => 2;\n")
    context = build_context(repo, paths=["siblings.js"])
    _partition(context, "siblings.js", repo)
    chunks = _chunks_of(context, "siblings.js")
    a = next(c for c in chunks if c["name"] == "a")
    b = next(c for c in chunks if c["name"] == "b")
    assert a["end_byte"] <= b["start_byte"], "sibling declarations must not overlap"
    assert a["text"].startswith("export const a")
    assert b["text"].startswith("b = () => 2")
    assert a["symbol_id"] != b["symbol_id"]
    assert context["diagnostics"] == []


def test_discovery_rejects_external_symlink_but_keeps_in_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "real.py").write_text("def real():\n    return 1\n")
    outside = tmp_path / "outside.py"
    outside.write_text("outside_marker = True\n")
    os.symlink(outside, repo / "linked.py")
    context = build_context(repo)  # discovery path, not explicit paths
    paths = {f["path"] for f in context["files"]}
    assert "real.py" in paths
    assert "linked.py" not in paths
    assert not any("outside_marker" in c["text"] for c in context["chunks"])
    assert any(d["path"] == "linked.py" and d["code"] == "invalid_path" for d in context["diagnostics"])


def test_graph_rejects_unmanifested_repo_source(tmp_path):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(
        json.dumps(
            {
                "schema": "cbe-graph/1",
                "source_manifest": [],
                "nodes": [{"id": "n", "path": "sample.py"}],
                "edges": [],
            }
        )
    )
    with pytest.raises(ContextError) as excinfo:
        build_context(FIXTURES, paths=["sample.py"], graph_path=graph_path)
    assert excinfo.value.code == "graph_unmanifested_source"
    assert excinfo.value.details["paths"] == ["sample.py"]

    # A valid empty graph is still accepted.
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"schema": "cbe-graph/1", "source_manifest": [], "nodes": [], "edges": []}))
    assert build_context(FIXTURES, paths=["sample.py"], graph_path=empty)["graph_status"] == "provided"

    # External nodes without a repo path stay explicitly external/unknown.
    external = tmp_path / "external.json"
    external.write_text(
        json.dumps(
            {
                "schema": "cbe-graph/1",
                "source_manifest": [],
                "nodes": [{"id": "ext", "kind": "external", "path": None, "name": "os"}],
                "edges": [],
            }
        )
    )
    assert build_context(FIXTURES, paths=["sample.py"], graph_path=external)["graph_status"] == "provided"


def test_grammar_override_after_cache_is_effective(tmp_path):
    from dataclasses import replace

    import cbe.source_context as sc

    (tmp_path / "m.py").write_text("def f():\n    return 1\n")
    first = build_context(tmp_path, paths=["m.py"])
    assert any(c["name"] == "f" for c in first["chunks"])
    python_spec = next(s for s in GRAMMARS if s.name == "python")
    register_language(replace(python_spec, module="cbe_nonexistent_grammar"))
    try:
        after = build_context(tmp_path, paths=["m.py"])
        assert any(d["code"] == "grammar_unavailable" for d in after["diagnostics"])
        assert not [c for c in after["chunks"] if c["name"] == "f"]
    finally:
        sc._EXTRA_SPECS.pop("python", None)


def test_plugin_load_errors_surface_in_discovery(monkeypatch):
    import importlib.metadata

    import cbe.source_context as sc

    class BrokenEntry:
        name = "broken-pack"

        def load(self):
            raise ImportError("no such grammar pack")

    monkeypatch.setattr(importlib.metadata, "entry_points", lambda group=None: [BrokenEntry()])
    monkeypatch.setattr(sc, "_PLUGINS_LOADED", False)
    monkeypatch.setattr(sc, "_PLUGIN_ERRORS", [])
    result = sc.available_languages()
    assert any(e["entry_point"] == "broken-pack" for e in result["plugin_errors"])


def test_unavailable_registered_grammar_is_listed_not_silently_unsupported():
    registered = GrammarSpec(
        name="klingon",
        suffixes=(".tlh",),
        module="cbe_nonexistent_grammar",
        attr="language",
        function_kinds={"function_definition": "function"},
        class_kinds={},
        wrappers=frozenset(),
        value_function_kinds=frozenset(),
    )
    register_language(registered)
    try:
        entry = next(e for e in available_languages()["languages"] if e["name"] == "klingon")
        assert entry["available"] is False
        assert entry["error"]
        assert language_for_path("x.tlh") == "klingon"
    finally:
        import cbe.source_context as sc

        sc._EXTRA_SPECS.pop("klingon", None)
