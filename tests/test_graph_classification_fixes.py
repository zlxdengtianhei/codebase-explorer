"""Recorded-Joern regressions for call/import classification (no JVM needed)."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from cbe import cli
from cbe.graph import GraphError, analyze_graph
from cbe.graph_backends import imports as import_backend
from cbe.graph_backends._calls import CallResolver
from cbe.graph_backends.imports import build_with_depcruise, build_with_grimp
from cbe.graph_backends.joern import (
    _c_macro_names, _capabilities_for, _non_call_reason, _normalize, build_with_joern,
)
from cbe.graph_backends.resolution import ImportResolver, resolve_declarations

CASES = Path(__file__).parent / "fixtures" / "graphs" / "cases"


def payload(language: str) -> dict:
    return json.loads((CASES / language / "raw.json").read_text(encoding="utf-8"))


def normalized(language: str):
    value = payload(language)
    diagnostics = []
    nodes, edges = _normalize(value, "test", diagnostics=diagnostics)
    return value, nodes, edges, diagnostics


@pytest.mark.parametrize("language,non_calls,statuses", [
    ("c", {"macro": 2}, {"resolved": 2}),
    ("cpp", {"macro": 1}, {"resolved": 2, "unresolved": 1}),
    ("python", {"synthetic": 8}, {"resolved": 2, "external": 1, "unresolved": 1}),
    ("typescript", {"import_statement": 1, "synthetic": 1}, {"resolved": 1}),
    ("java", {}, {"resolved": 1, "external": 1, "unresolved": 1}),
    ("go", {"literal": 1, "type_conversion": 2},
     {"resolved": 1, "external": 1, "unresolved": 1}),
    ("ruby", {"synthetic": 2}, {"resolved": 2, "external": 1}),
])
def test_recorded_non_calls_counts_and_cross_file_calls(language, non_calls, statuses):
    value, _, edges, _ = normalized(language)
    calls = [edge for edge in edges if edge["kind"] == "call"]
    assert value["_non_call_sites"] == non_calls
    assert Counter(edge["status"] for edge in calls) == Counter(statuses)
    capability = next(c for c in _capabilities_for(language, value, "test") if c["graph"] == "call")
    assert capability["non_call_sites"] == non_calls
    assert all(capability[status] == count for status, count in statuses.items())
    assert ("excluded non-call sites" in capability["limitations"]) == bool(non_calls)


@pytest.mark.parametrize("language,forbidden", [
    ("c", ["FALSE", "BUFFER_AT_OFFSET(p)"]),
    ("cpp", ["LOCAL_ASSERT(ok)"]),
    ("python", ["<fakeNew>", "__newInstance.__init__", "tmp0.__next__", "method(self)"]),
    ("typescript", ["require(\"./util.js\")", "_iterator_0.next()"]),
    ("go", ["[]byte(\"x\")", "string(data)", "Server{Value: helper.Helper(1)}"]),
])
def test_non_call_expressions_never_become_edges(language, forbidden):
    _, _, edges, _ = normalized(language)
    expressions = {edge.get("expression") for edge in edges if edge["kind"] == "call"}
    assert not any(token in expression for token in forbidden for expression in expressions)


def test_static_cpp_macro_uses_tree_sitter_name_inventory():
    cpp = payload("cpp")
    assert "LOCAL_ASSERT" in _c_macro_names(CASES / "cpp", cpp["_files"])
    macro = {"callerFile": "src/os.cc", "name": "FMT_COMPILE_STRING",
             "code": "FMT_COMPILE_STRING()", "dispatchType": "STATIC_DISPATCH"}
    assert _non_call_reason(macro, macro_names={"FMT_COMPILE_STRING"}) == "macro"
    real = dict(macro, name="format_to", code="fmt::format_to(it, FMT_COMPILE_STRING())")
    assert _non_call_reason(real, macro_names={"FMT_COMPILE_STRING"}) is None
    operator = dict(macro, name="<operators>.assignmentOr", methodFullName="<operators>.assignmentOr")
    assert _non_call_reason(operator) == "operator"  # filtered, but not counted as a non-call site
    declaration = dict(macro, name="ANY.ANY", methodFullName="ANY.ANY:void()")
    assert _non_call_reason(declaration) == "synthetic"
    conversion = dict(macro, name="char", methodFullName="char.char:void()")
    assert _non_call_reason(conversion) == "type_conversion"
    aggregate = dict(macro, name="struct", code="Parse{begin}", methodFullName="struct.struct:void(ANY)")
    assert _non_call_reason(aggregate) == "literal"
    constructor = {"callerFile": "main.cpp", "methodFullName": "detail.buffer.buffer:void()",
                   "callees": [{"fullName": "detail.buffer.buffer:void()", "external": True}]}
    assert CallResolver([]).resolve(constructor)[0] == "unresolved"
    bare = {"callerFile": "main.cpp", "methodFullName": "parse_format_string:ANY()",
            "callees": [{"fullName": "parse_format_string:ANY()", "external": True}]}
    methods = [{"nodeId": 1, "file": "format.h", "name": "parse_format_string", "fullName": "fmt.v12.parse"}]
    assert CallResolver(methods).resolve(bare)[0] == "unresolved"
    any_receiver = dict(bare, methodFullName="ANY.run:bool()",
                        callees=[{"fullName": "ANY.run:bool()", "external": True}])
    assert CallResolver([]).resolve(any_receiver)[0] == "unresolved"
    go_any = dict(any_receiver, callerFile="main.go", methodFullName="ANY.wrap.Discard",
                  callees=[{"fullName": "ANY.wrap.Discard", "external": True}])
    assert CallResolver([]).resolve(go_any)[0] == "unresolved"


def test_unresolved_identities_and_repository_namespaces_are_not_external():
    java = [e for e in normalized("java")[2] if e["kind"] == "call"]
    assert next(e for e in java if e["expression"] == 'getField("x")')["status"] == "unresolved"
    go = [e for e in normalized("go")[2] if e["kind"] == "call"]
    assert next(e for e in go if e["expression"] == "runner.Run()")["status"] == "unresolved"
    cpp = payload("cpp")
    resolver = CallResolver(cpp["methods"], cpp["_files"], cpp["types"])
    miss = dict(cpp["calls"][0], methodFullName="demo.v1.later:void()",
                callees=[{"fullName": "demo.v1.later:void()", "external": True}])
    assert resolver.resolve(miss) == ("unresolved", [], [])
    unknown = dict(miss, methodFullName="<unresolvedName>.later:<unresolvedSignature>(1)")
    assert resolver.resolve(unknown)[0] == "unresolved"
    empty = {"callerFile": "main.rb", "methodFullName": "<empty>.call",
             "callees": [{"fullName": "<empty>.call", "external": True}]}
    assert CallResolver([]).resolve(empty)[0] == "unresolved"
    python_methods = [{"nodeId": 1, "file": "src/pkg/mod.py", "fullName": "src/pkg/mod.py:<module>.run"}]
    python_files = {"src/pkg/__init__.py", "src/pkg/mod.py", "tests/test_pkg.py"}
    python_call = {"callerFile": "tests/test_pkg.py", "methodFullName": "pkg/mod.py:<module>.run",
                   "callees": [{"fullName": "pkg/mod.py:<module>.run", "external": True}]}
    assert CallResolver(python_methods, python_files).resolve(python_call)[0] == "unresolved"
    package_call = {"callerFile": "test-d/main.ts", "methodFullName": "ky:ky",
                    "callees": [{"fullName": "ky:ky", "external": True}]}
    assert CallResolver([], javascript_packages={"ky"}).resolve(package_call)[0] == "unresolved"
    go_methods = [{"nodeId": 1, "file": "github.com/go-chi/chi/v5",
                   "fullName": "github.com/go-chi/chi/v5<clinit>"}]
    go_resolver = CallResolver(go_methods, go_modules={"github.com/go-chi/chi/v5": ""})
    render = {"callerFile": "main.go", "methodFullName": "github.com/go-chi/render.Render",
              "callees": [{"fullName": "github.com/go-chi/render.Render", "external": True}]}
    assert go_resolver.resolve(render)[0] == "external"


@pytest.mark.parametrize("suffix", [".c", ".cpp", ".py", ".ts", ".java", ".go", ".rb"])
def test_unknown_receiver_with_internal_candidate_is_ambiguous(suffix):
    methods = [{"nodeId": 1, "file": "a" + suffix, "fullName": "a"}]
    call = {"callerFile": "b" + suffix, "methodFullName": "<unknownFullName>",
            "callees": [{"nodeId": 1, "fullName": "a", "external": False}]}
    assert CallResolver(methods).resolve(call) == ("ambiguous", [1], [])


def test_ruby_keyword_and_array_literals_are_not_calls():
    keyword = {"callerFile": "main.rb", "code": "defined?(value)",
               "methodFullName": "<unknownFullName>"}
    assert _non_call_reason(keyword) == "synthetic"
    literal = {"callerFile": "main.rb", "code": "%w[GET HEAD]",
               "methodFullName": "__core.Array.initialize"}
    assert _non_call_reason(literal) == "literal"
    assert _non_call_reason(dict(literal, code="[]")) == "literal"
    assert _non_call_reason(dict(literal, code="[message]")) == "literal"
    assert _non_call_reason(dict(literal, code="Array.new")) is None


def test_go_user_defined_type_conversion_uses_exact_type_identity():
    types = [{"name": "Middlewares", "fullName": "example.com/mod.Middlewares"}]
    call = {"callerFile": "chain.go", "name": "Middlewares", "code": "Middlewares(items)",
            "methodFullName": "example.com/mod.Middlewares"}
    assert _non_call_reason(call, types=types) == "type_conversion"
    function = dict(call, methodFullName="example.com/other.Middlewares")
    assert _non_call_reason(function, types=types) is None
    literal_types = [{"name": "contextKey", "fullName": "example.com/mod.contextKey", "file": "context.go"}]
    literal = {"callerFile": "example.com/mod", "name": "contextKey",
               "code": 'contextKey{"RouteContext"}', "methodFullName": "example.com/mod.contextKey.<init>"}
    assert _non_call_reason(literal, types=literal_types) == "literal"
    conversion = {"callerFile": "example.com/mod", "name": "", "code": '[]byte("x")',
                  "methodFullName": "example.com/mod."}
    assert _non_call_reason(conversion) == "type_conversion"


def test_typescript_emitted_js_name_resolves_to_unique_ts_member():
    _, nodes, edges, _ = normalized("typescript")
    edge = next(e for e in edges if e["kind"] == "call")
    assert edge["expression"] == "helper(item)" and edge["status"] == "resolved"
    assert nodes[[n["id"] for n in nodes].index(edge["target"])]["path"] == "util.ts"


def test_go_root_and_nested_module_imports_expand_to_real_files():
    repo = CASES / "go"
    resolver = ImportResolver(repo)
    assert resolver.resolve("main.go", "import helper example.com/fixture/helper") == [
        ("resolved", "helper/helper.go")]
    assert resolver.resolve("main.go", 'import "example.com/nested"') == [
        ("resolved", "nested/nested.go")]
    assert resolver.resolve("main.go", 'import "example.com/fixture/missing"') == [("unresolved", None)]
    _, _, edges, _ = normalized("go")
    _, resolved = resolve_declarations(repo, [], [e for e in edges if e["kind"] == "import"])
    local = next(e for e in resolved if "example.com/fixture/helper" in e["expression"])
    assert local["status"] == "resolved" and local["target"] == "file:helper/helper.go"


def test_grimp_discovers_src_layout_and_uses_its_source_root(monkeypatch):
    repo = CASES / "python"
    seen = []

    class FakeGraph:
        modules = {"pkg", "pkg.helper"}
        def find_modules_directly_imported_by(self, module):
            return {"pkg.helper"} if module == "pkg" else set()

    def build(name):
        seen.append((name, list(sys.path)))
        return FakeGraph()

    monkeypatch.setitem(sys.modules, "grimp", SimpleNamespace(build_graph=build))
    result = build_with_grimp(repo, ["python"])
    assert seen[0][0] == "pkg" and str(repo / "src") in seen[0][1]
    assert not any(d["code"] == "no_python_packages" for d in result["diagnostics"])
    assert any(e["target"] == "file:src/pkg/helper.py" and e["status"] == "resolved"
               for e in result["edges"])


def test_depcruise_zero_typescript_modules_is_diagnostic_not_component(tmp_path, monkeypatch):
    repo = CASES / "typescript"
    completed = subprocess.CompletedProcess(["depcruise"], 0, '{"modules": []}', "")
    monkeypatch.setattr(import_backend.subprocess, "run", lambda *a, **kw: completed)
    result = build_with_depcruise(repo, tmp_path, "depcruise", 2, ["typescript"])
    assert result["capabilities"][0]["status"] == "failed"
    assert result["diagnostics"][0]["code"] == "depcruise_no_modules"
    assert ">=2 <6" in result["diagnostics"][0]["message"]
    from cbe import graph_backends
    monkeypatch.setattr(graph_backends, "find_depcruise", lambda *a: "depcruise")
    with pytest.raises(GraphError):
        analyze_graph(repo, tmp_path / "empty.json", backend="imports", languages=["typescript"])
    value = json.loads((tmp_path / "empty.json").read_text())
    assert value["backend"] == {"name": "none", "version": None, "components": []}


def test_ruby_require_relative_recovers_file_expression_and_target():
    _, _, edges, _ = normalized("ruby")
    declarations = [e for e in edges if e["kind"] == "import"]
    assert {(e["path"], e["expression"]) for e in declarations} == {
        ("main.rb", 'require_relative "helper"')}
    _, resolved = resolve_declarations(CASES / "ruby", [], declarations)
    assert all(e["status"] == "resolved" and e["target"] == "file:helper.rb" for e in resolved)


def test_absent_files_have_diagnostic_and_ruby_tests_are_present():
    value, _, _, diagnostics = normalized("c")
    absent = next(d for d in diagnostics if d["code"] == "files_absent_from_graph")
    assert absent["examples"] == ["helper.h"] and absent["count"] == 1
    cap = next(c for c in _capabilities_for("c", value, "test") if c["graph"] == "call")
    assert "1 manifest files" in cap["limitations"]
    _, _, _, ruby_diagnostics = normalized("ruby")
    absent = next(d for d in ruby_diagnostics if d["code"] == "files_absent_from_graph")
    assert absent["examples"] == ["tests/helper_test.rb"]


def test_ruby_parser_passes_no_default_exclude(tmp_path, monkeypatch):
    import cbe.graph_backends.joern as joern
    home = tmp_path / "home"
    home.mkdir()
    (home / "joern").touch()
    (home / "joern-parse").touch()
    argv_seen = []

    def run(argv, timeout, cwd, *, env=None):
        argv_seen.append(argv)
        if argv[0].endswith("joern") and "--version" in argv:
            return subprocess.CompletedProcess(argv, 0, "Version: test", "")
        if "--language" in argv:
            Path(argv[argv.index("-o") + 1]).touch()
            return subprocess.CompletedProcess(argv, 0, "", "")
        params = dict(arg.split("=", 1) for arg in argv if "=" in arg)
        Path(params["outFile"]).write_text(json.dumps({"methods": [
            {"nodeId": 1, "file": "main.rb", "fullName": "run", "line": 1}]}))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(joern, "_run", run)
    result = build_with_joern(CASES / "ruby", tmp_path / "run", ["ruby"], home, 2)
    parse = next(argv for argv in argv_seen if "--language" in argv)
    assert parse[-2:] == ["--frontend-args", "--no-default-exclude"]
    assert result["raw"]


def test_graph_json_scrubs_repo_absolute_prefix_everywhere(tmp_path, monkeypatch):
    from cbe import graph_backends
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.c").write_text("int main(void) { return 0; }\n")
    monkeypatch.setattr(graph_backends, "find_joern", lambda *a: tmp_path)
    expression = f'assert_fail("{repo}/main.c", 1)'
    fragment = {"backend": {"name": "joern", "version": "test"},
        "nodes": [{"id": "m", "kind": "function", "path": "main.c", "name": "main"}],
        "edges": [{"id": "c", "source": "m", "target": None, "kind": "call",
                   "status": "unresolved", "path": "main.c", "expression": expression}],
        "capabilities": [{"language": "c", "graph": "call", "status": "partial", "backend": "joern"}],
        "diagnostics": [{"code": "example", "message": expression}], "raw": [{}],
        "non_call_sites": {"macro": 2}}
    monkeypatch.setattr(graph_backends, "build_with_joern", lambda *a, **kw: fragment)
    output = tmp_path / "graph.json"
    value = analyze_graph(repo, output, backend="joern", languages=["c"])
    assert str(repo) not in output.read_text()
    assert value["edges"][0]["expression"] == 'assert_fail("main.c", 1)'
    assert value["quality"]["non_call_sites"] == {"macro": 2}


@pytest.mark.parametrize("backend", ["joern", "auto"])
@pytest.mark.parametrize("suffix", [".c", ".py", ".ts", ".java", ".go", ".rb"])
def test_missing_joern_has_one_written_failure_contract(tmp_path, monkeypatch, capsys, suffix, backend):
    from cbe import graph_backends
    repo = tmp_path / suffix[1:]
    repo.mkdir()
    (repo / ("main" + suffix)).write_text("\n")
    monkeypatch.setattr(graph_backends, "find_joern", lambda *a: None)
    output = tmp_path / (suffix[1:] + ".json")
    code = cli.main(["graph", "build", str(repo), "--backend", backend, "--output", str(output)])
    assert code == 2 and output.is_file()
    value = json.loads(output.read_text())
    assert value["backend"]["name"] == "none"
    messages = [d["message"] for d in value["diagnostics"] if d["code"] == "backend_unavailable"]
    assert len(messages) == 1
    assert messages[0].startswith("Joern CLI not found; call/cfg/dataflow/import graph skipped; "
                                  "run `cbe graph setup` (downloads about ")
    assert not any(d["code"] == "no_python_packages" for d in value["diagnostics"])
    capsys.readouterr()


def test_typescript_array_literal_push_is_synthetic():
    call = {"callerFile": "main.ts", "name": "push", "code": "_tmp_3.push(101)",
            "methodFullName": "__ecma.Array:"}
    assert _non_call_reason(call) == "synthetic"
    export = {"callerFile": "main.ts", "name": "require", "code": 'require("./types.js")',
              "sourceCode": "export type {Item} from './types.js';"}
    assert _non_call_reason(export) == "import_statement"
    multiline = dict(export, sourceCode="export {\n  Item\n} from './types.js';")
    assert _non_call_reason(multiline) == "import_statement"
    runtime = dict(export, sourceCode="const types = require('./types.js');")
    assert _non_call_reason(runtime) is None
