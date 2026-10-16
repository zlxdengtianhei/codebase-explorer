"""O1b inventory and merge-boundary regressions."""
from cbe.graph import discover_sources, _prefer_resolved_imports
from cbe.graph_backends.identity import repository_files, file_id
from cbe.graph_backends.resolution import ImportResolver
from cbe.graph_backends._calls import CallResolver


def test_inventory_excludes_environment_and_includes_headers(tmp_path):
    for name in ("src/ext.c", "include/cJSON.h", ".venv/include/Python.h", "node_modules/lib/x.js"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    files = repository_files(tmp_path)
    assert files == {"src/ext.c", "include/cJSON.h"}
    assert {x["path"] for x in discover_sources(tmp_path)} == files
    assert file_id("invented.c", files) is None
    assert ImportResolver(tmp_path).resolve("src/ext.c", '#include "Python.h"') == [("unresolved", None)]
    resolver = CallResolver([], files)
    assert resolver.resolve(dict(methodFullName="include/cJSON.h:cJSON_String:ANY(0)",
                                 callees=[dict(fullName="include/cJSON.h:cJSON_String:ANY(0)", external=True)]))[0] == "unresolved"


def test_merge_collapses_repeated_resolved_evidence():
    edges = [dict(id=str(i), source="file:a.py", target="file:b.py", kind="import",
                  status="resolved", backend="joern", expression=f"from b import name{i}") for i in range(28)]
    merged = _prefer_resolved_imports(edges)
    assert len(merged) == 1
    assert len(merged[0]["expressions"]) == 28


def test_merge_boundary_degrades_invalid_files_and_repairs_external_suffix():
    from cbe.graph_backends.identity import validate_identities
    nodes = [dict(id="file:invented.js", path="invented.js"),
             dict(id="ext:curl/curl.h", name="curl/curl.h")]
    edges = [dict(id="bad", source=None, target="file:invented.js", kind="import", status="resolved"),
             dict(id="curl", source=None, target="ext:curl/curl.h", kind="import", status="external")]
    nodes, edges, diagnostics = validate_identities(nodes, edges, {"include/curl/curl.h"})
    assert {n["id"] for n in nodes} == {"file:include/curl/curl.h"}
    assert edges[0]["target"] is None and edges[0]["status"] == "unresolved"
    assert edges[1]["target"] == "file:include/curl/curl.h" and edges[1]["status"] == "resolved"
    assert len(diagnostics) == 2
    ambiguous = [dict(id="ext:common.h", name="common.h")]
    nodes, edges, diagnostics = validate_identities(ambiguous, [dict(kind="import", status="external", target="ext:common.h")], {"a/common.h", "b/common.h"})
    assert nodes[0]["id"] == "ext:common.h"
    assert edges[0]["status"] == "external"
    nodes, edges, _ = validate_identities(
        [dict(id="file:missing.c", path="missing.c"), dict(id="file:ok.h", path="ok.h")],
        [dict(kind="import", status="resolved", source="file:missing.c", target="file:ok.h")], {"ok.h"})
    assert edges[0]["source"] is None and edges[0]["status"] == "unresolved"


def test_src_layout_absolute_import_and_js_extension_index(tmp_path):
    for name in ("src/pkg/a.py", "src/pkg/__init__.py", "src/main.ts", "src/util.ts", "src/lib/index.mts", "src/plain.js"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    resolver = ImportResolver(tmp_path)
    assert resolver.resolve("src/pkg/a.py", "from pkg import a") == [("resolved", "src/pkg/a.py")]
    assert resolver.resolve("src/main.ts", 'import x from "./util.js"') == [("resolved", "src/util.ts")]
    assert resolver.resolve("src/main.ts", 'import x from "./lib"') == [("resolved", "src/lib/index.mts")]
    assert resolver.resolve("src/main.ts", 'import x from "./plain"') == [("resolved", "src/plain.js")]


def test_repository_class_guesses_and_exact_inheritance():
    methods = [dict(nodeId=1, file="app.py", fullName="app.py:<module>.Base.run"),
               dict(nodeId=2, file="app.py", fullName="app.py:<module>.Child.call")]
    types = [dict(name="Base", fullName="app.py:<module>.Base", file="app.py", inherits=[]),
             dict(name="Child", fullName="app.py:<module>.Child", file="app.py", inherits=["app.py:<module>.Base"])]
    resolver = CallResolver(methods, {"app.py"}, types)
    def call(full):
        return dict(callerId="2", methodFullName=full, callees=[dict(fullName=full, external=True)])
    assert resolver.resolve(call("Child.run")) == ("resolved", [1], [])
    assert resolver.resolve(call("te.Self.run")) == ("resolved", [1], [])
    assert resolver.resolve(call("Child.missing"))[0] == "unresolved"
    assert resolver.resolve(call("Child.<member>(session).open"))[0] == "unresolved"
    assert resolver.resolve(call("te.Self.run.<returnValue>.loads"))[0] == "unresolved"
    assert resolver.resolve(call("Self.missing"))[0] == "unresolved"
    assert resolver.resolve(call("werkzeug.Response"))[0] == "external"
    # Captured C# method signatures contain System.*; those names are not
    # repository class declarations (real csharpsrc output).
    csharp = CallResolver([dict(nodeId="107374182400", file="Helper.cs",
                                fullName="Probe.Helper.Compute:System.Int32(System.Int32)"),
                           dict(nodeId="107374182401", file="Program.cs",
                                fullName="Probe.Program.Main:System.Void()")], {"Helper.cs", "Program.cs"})
    assert csharp.resolve(call("System.Console.WriteLine:System.Void(System.Int32)"))[0] == "external"


def test_depcruise_unresolvable_dependency_never_invents_file(tmp_path, monkeypatch):
    import json
    import subprocess
    from cbe.graph_backends.imports import build_with_depcruise
    (tmp_path / "main.js").touch()
    (tmp_path / "existing.js").touch()
    # This shape is emitted for polyglot ./helper.js and c1-jsrepo packages.
    payload = dict(modules=[dict(source="main.js", dependencies=[
        dict(module="./helper.js", resolved="./helper.js", couldNotResolve=True),
        dict(module="react", resolved="react", couldNotResolve=True),
        dict(module="./existing.js", resolved="./existing.js", couldNotResolve=True)])])
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0, json.dumps(payload), ""))
    result = build_with_depcruise(tmp_path, tmp_path / "run", "depcruise", 10, ["javascript"])
    assert all(e["status"] == "unresolved" and e["target"] is None for e in result["edges"])
    assert {n["id"] for n in result["nodes"]} == {"file:main.js"}


def test_frontend_diagnostic_retry_inherits_heap(tmp_path, monkeypatch):
    import subprocess
    from cbe.graph_backends import joern
    seen = []
    def run(argv, timeout, cwd, *, env=None):
        seen.append(env)
        return subprocess.CompletedProcess(argv, 1, "", "OutOfMemoryError: Java heap space")
    monkeypatch.setattr(joern, "_run", run)
    env = {"JAVA_TOOL_OPTIONS": "-Xmx64m"}
    assert "OutOfMemoryError" in joern._frontend_error_from_direct_run("invoke the frontend: /tool/c2cpg input", tmp_path, 10, [], env=env)
    assert seen == [env]


def test_python_script_siblings_src_package_and_namespace_child(tmp_path):
    for name in ("tests/helpers.py", "tests/main.py", "src/__init__.py", "src/a.py", "src/x.py", "src/nsdir/util.py"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    resolver = ImportResolver(tmp_path)
    assert resolver.resolve("tests/main.py", "from helpers import make") == [("resolved", "tests/helpers.py")]
    assert resolver.resolve("src/a.py", "from . import x") == [("resolved", "src/x.py")]
    assert resolver.resolve("src/a.py", "from . import nsdir") == [("unresolved", None)]
