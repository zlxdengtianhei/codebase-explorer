"""C1b counterexamples: search evidence must precede repository identity."""
from cbe.graph_backends.resolution import ImportResolver, resolve_declarations
from cbe.graph_backends.identity import validate_identities


def test_angle_headers_require_directory_evidence(tmp_path):
    files = {"src/util.c", "test/math.h", "compat/stdint.h", "internal/assert.h",
             "adapters/poll.h", "lib/vtls/rustls.h", "lib/vtls/schannel.h",
             "include/curl/curl.h", "fake/sys/types.h", "fake/netinet/in.h",
             "fake/arpa/inet.h"}
    resolver = ImportResolver(tmp_path, files)
    for token in ("math.h", "stdint.h", "assert.h", "poll.h", "rustls.h", "schannel.h",
                  "sys/types.h", "netinet/in.h", "arpa/inet.h"):
        assert resolver.resolve("src/util.c", f"#include <{token}>") == [("external", token)]
    assert resolver.resolve("src/util.c", '#include "math.h"') == [("resolved", "test/math.h")]
    edge = dict(id="curl", kind="import", backend="joern", path="src/util.c",
                source="file:src/util.c", expression="#include <curl/curl.h>")
    nodes, edges = resolve_declarations(tmp_path, [], [edge], files=files)
    assert edges[0]["target"] == "file:include/curl/curl.h"
    assert edges[0]["resolution_basis"] == dict(kind="repository_directory_prefix", prefix="curl", include_root="include")
    from cbe.graph import _prefer_resolved_imports
    quoted = {**edges[0], "id": "quoted", "expression": '#include "curl/curl.h"'}
    quoted.pop("resolution_basis")
    merged = _prefer_resolved_imports([quoted, edges[0]])
    assert len(merged) == 1 and merged[0]["resolution_basis"] == edges[0]["resolution_basis"]
    # Validation must not reinterpret a standard header based on its basename.
    nodes, edges, _ = validate_identities([dict(id="ext:math.h", name="math.h")],
        [dict(kind="import", target="ext:math.h", status="external")], files)
    assert nodes[0]["id"] == edges[0]["target"] == "ext:math.h"


def test_ambiguous_angle_header_preserves_candidates(tmp_path):
    files = {"include/nlohmann/json.hpp", "single_include/nlohmann/json.hpp"}
    resolver = ImportResolver(tmp_path, files)
    assert resolver.resolve("test.cpp", "#include <nlohmann/json.hpp>") == [("unresolved", None)]
    assert resolver.diagnostics[0]["candidates"] == sorted(files)
    diagnostics = []
    _, edges = resolve_declarations(tmp_path, [], [dict(id="json", kind="import", backend="joern",
        path="test.cpp", expression="#include <nlohmann/json.hpp>")], files=files, diagnostics=diagnostics)
    assert edges[0]["status"] == "unresolved" and edges[0]["target"] is None
    assert diagnostics[0]["code"] == "ambiguous_include"


def test_import_boundary_rejects_self_loop_and_diagnoses_library_collision():
    nodes = [dict(id="file:lib/vtls/schannel.h", path="lib/vtls/schannel.h")]
    edges = [dict(kind="import", status="resolved", source=nodes[0]["id"], target=nodes[0]["id"],
                  expression="#include <schannel.h>"),
             dict(kind="import", status="resolved", source="file:lib/vtls/rustls.c",
                  target="file:lib/vtls/rustls.h", expressions=["#include <rustls.h>", '#include "vtls/rustls.h"'])]
    _, kept, diagnostics = validate_identities(nodes, edges, {"lib/vtls/schannel.h"})
    assert len(kept) == 1
    assert {d["code"] for d in diagnostics} == {"self_import_suppressed", "external_header_collision"}
    assert diagnostics[0]["angle_headers"] == ["rustls.h"]
    # Correct separated external and repository dependencies do not collide.
    edges[1]["expressions"] = ['#include "vtls/rustls.h"']
    _, _, diagnostics = validate_identities([], edges[1:] + [dict(kind="import", status="external",
        source="file:lib/vtls/rustls.c", target="ext:rustls.h", expression="#include <rustls.h>")], set())
    assert diagnostics == []


def test_function_types_and_nested_function_owners_are_not_classes():
    from cbe.graph_backends._calls import CallResolver
    methods = [dict(nodeId=1, file="ctx.py", fullName="ctx.py:<module>.AppContext.copy"),
               dict(nodeId=2, file="ctx.py", fullName="ctx.py:<module>.inspect"),
               dict(nodeId=3, file="ctx.py", fullName="ctx.py:<module>.inspect.wrapper")]
    types = [dict(name="copy", fullName=methods[0]["fullName"], file="ctx.py", inherits=["ANY"]),
             dict(name="inspect", fullName=methods[1]["fullName"], file="ctx.py", inherits=["ANY"]),
             dict(name="AppContext", fullName="ctx.py:<module>.AppContext", file="ctx.py", inherits=[])]
    resolver = CallResolver(methods, {"ctx.py"}, types)
    assert "copy" not in resolver.classes and "inspect" not in resolver.classes
    assert "AppContext" in resolver.classes
    for full in ("copy.py:<module>.copy", "inspect.isfunction"):
        assert resolver.resolve(dict(methodFullName=full, callees=[dict(fullName=full, external=True)]))[0] == "external"
    assert resolver.resolve(dict(methodFullName="AppContext.missing", callees=[dict(external=True)]))[0] == "unresolved"
    # Joern's guessed top-level package module is separate from class names.
    resolver = CallResolver(methods, {"celery/__init__.py", "ctx.py"}, types)
    assert "celery" not in resolver.classes
    resolver.classes.add("redis")  # A real test class shares an external module name.
    assert resolver.resolve(dict(methodFullName="redis.py:<module>.Redis.__init__",
        callees=[dict(fullName="redis.py:<module>.Redis.__init__", external=True)]))[0] == "external"
    assert resolver.resolve(dict(methodFullName="redis.missing", callees=[dict(external=True)]))[0] == "unresolved"
    assert resolver.resolve(dict(methodFullName="celery.py:<module>.chord",
                                 callees=[dict(fullName="celery.py:<module>.chord", external=True)]))[0] == "unresolved"


def test_cli_default_exports_all_cfg_methods(tmp_path, monkeypatch):
    import json
    import subprocess
    from pathlib import Path
    from cbe.cli import main
    home = tmp_path / "joern"
    home.mkdir()
    for name in ("joern", "joern-parse"):
        (home / name).touch()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("def run(): pass\n")
    exports = []
    def run(argv, **kwargs):
        if "--version" in argv:
            return subprocess.CompletedProcess(argv, 0, "Version: 1", "")
        if "--language" in argv:
            Path(argv[argv.index("-o") + 1]).touch()
        if "--script" in argv:
            params = dict(arg.split("=", 1) for arg in argv if "=" in arg)
            exports.append(params)
            Path(params["outFile"]).write_text(json.dumps(dict(
                methods=[dict(nodeId=1, file="a.py", fullName="run")], cfgMethodsOmitted=0)))
        return subprocess.CompletedProcess(argv, 0, "", "")
    monkeypatch.setattr(subprocess, "run", run)
    output = tmp_path / "graph.json"
    assert main(["graph", "build", str(repo), "--output", str(output), "--backend", "joern",
                 "--joern-home", str(home)]) == 0
    assert exports[-1]["maxMethods"] == "-1"
    cfg = next(c for c in json.loads(output.read_text())["capabilities"] if c["graph"] == "cfg")
    assert cfg["methods_omitted"] == 0


def test_suffix_registry_is_built_once_per_graph(tmp_path, monkeypatch):
    from cbe import graph, source_context
    from cbe.graph_backends import resolution
    original = source_context.suffix_languages
    calls = []
    def registry():
        calls.append(1)
        return original()
    monkeypatch.setattr(source_context, "suffix_languages", registry)
    monkeypatch.setattr(resolution, "suffix_languages", registry)
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("import os\nimport sys\n")
    graph.analyze_graph(tmp_path, tmp_path / "g.json", backend="imports")
    assert len(calls) == 1
    calls.clear()
    resolver = ImportResolver(tmp_path)
    for _ in range(10):
        resolver.resolve("main.rb", 'require "set"')
    assert len(calls) == 1


def test_python_only_build_does_not_report_unused_dependency_cruiser(tmp_path, monkeypatch):
    from cbe import graph, graph_backends
    monkeypatch.setattr(graph_backends, "find_depcruise", lambda *args: None)
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("import os\n")
    result = graph.analyze_graph(tmp_path, tmp_path / "g.json", backend="imports")
    assert not any("dependency-cruiser" in d.get("message", "") for d in result["diagnostics"])
    # A requested JS backend still reports its absence.
    (tmp_path / "main.js").write_text('import x from "missing";')
    result = graph.analyze_graph(tmp_path, tmp_path / "g.json", backend="imports")
    assert any("dependency-cruiser not found" in d.get("message", "") for d in result["diagnostics"])
