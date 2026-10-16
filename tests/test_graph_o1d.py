"""Regressions for Python call identities and truncated dataflow exports."""
import os
from pathlib import Path

import pytest

from cbe.graph import analyze_graph
from cbe.graph_backends._calls import CallResolver
from cbe.graph_backends.joern import _normalize, _capabilities_for


def external_call(full, caller="pkg/app.py"):
    return {"nodeId": 10, "callerFile": caller, "methodFullName": full,
            "name": "invoke", "code": "invoke()", "line": 7,
            "callees": [{"external": True, "fullName": full}]}


def assert_resolution(resolver, call, expected, *, unverified=False):
    """Check the public result together with diagnostics from this call."""
    start = len(resolver.diagnostics)
    assert resolver.resolve(call) == expected
    codes = [item["code"] for item in resolver.diagnostics[start:]]
    assert codes == (["python_external_name_unverified"] if unverified else [])


def test_python_guessed_names_are_unresolved_but_library_paths_survive():
    resolver = CallResolver([], {"celery/beat.py", "celery/backends/redis.py", "pkg/app.py"})
    for full in ["result.results.<returnValue>.<member>(results).__iter__.<returnValue>.__next__",
                 "decorator.<returnValue>.view_class"]:
        # Return/member guesswork remains unresolved regardless of caller.
        assert_resolution(resolver, external_call(full, ""), ("unresolved", [], []))
    assert_resolution(resolver, external_call("beat.Service.start"), ("unresolved", [], []))
    assert_resolution(resolver, external_call("copy.py:<module>.copy"),
                      ("external", [], ["copy.py:<module>.copy"]))
    full = "redis.py:<module>.StrictRedis.__init__"
    assert_resolution(resolver, external_call(full), ("external", [], [full]))


def test_python_module_names_do_not_reclassify_javascript_external_calls():
    resolver = CallResolver([], {"tools/console.py", "web/main.js", "pkg/app.py"})
    call = external_call("console.log", "web/main.js")
    call.update(name="log", code="console.log('hello')")
    assert_resolution(resolver, call, ("external", [], ["console.log"]))
    # The repository Python module inference still applies to Python callers,
    # and library-qualified Python identities still survive unchanged.
    assert_resolution(resolver, external_call("console.log"), ("unresolved", [], []))
    assert_resolution(resolver, external_call("console.py:<module>.log"),
                      ("external", [], ["console.py:<module>.log"]))


def test_python_external_exit_guard_and_diagnostic():
    payload = {"calls": [external_call("future_receiver.invoke")], "methods": []}
    diagnostics = []
    _, edges = _normalize(payload, "1", diagnostics=diagnostics)
    assert edges[0]["status"] == "unresolved"
    assert edges[0]["target"] is None
    assert diagnostics[0]["code"] == "python_external_name_unverified"
    assert diagnostics[0]["analyzer_id"] == 10
    resolver = CallResolver([])
    for full in ["__builtin.print", "__builtin.dict<meta>.<returnValue>.setdefault"]:
        assert_resolution(resolver, external_call(full), ("external", [], [full]))
    assert_resolution(resolver, external_call("java.util.List.add", "Main.java"),
                      ("external", [], ["java.util.List.add"]))
    # The exit must also validate a newly introduced resolution branch.
    resolver._resolve = lambda call: ("external", [], ["future_guess"])
    assert_resolution(resolver, external_call("anything"), ("unresolved", [], []), unverified=True)


def test_lost_relative_package_requires_unique_file_and_method():
    full = "//logging.py:<module>.create_logger"
    method = {"nodeId": 1, "file": "flask/logging.py",
              "fullName": "flask/logging.py:<module>.create_logger"}
    call = external_call(full, "flask/sansio/app.py")
    files = {"flask/logging.py", "flask/sansio/app.py", "unrelated/logging.py"}
    assert_resolution(CallResolver([method], files), call, ("resolved", [1], []))
    assert_resolution(CallResolver([method], files | {"flask/sansio/logging.py"}),
                      call, ("unresolved", [], []))
    assert_resolution(CallResolver([], files), call, ("unresolved", [], []))
    duplicate = dict(method, nodeId=2)
    assert_resolution(CallResolver([method, duplicate], files), call, ("unresolved", [], []))
    assert_resolution(CallResolver([method], {"unrelated/logging.py"}), call, ("unresolved", [], []))
    nested = {"nodeId": 3, "file": "celery/utils/quorum_queues.py",
              "fullName": "celery/utils/quorum_queues.py:<module>.detect_quorum_queues"}
    assert_resolution(CallResolver([nested]), external_call(
        "//utils/quorum_queues.py:<module>.detect_quorum_queues", "celery/app/base.py"),
        ("resolved", [3], []))


def test_truncated_dataflow_is_partial_with_omitted_count():
    payload = {"methods": [{"nodeId": 1}], "reachingDefs": [{}],
               "reachingDefsTruncated": True, "reachingDefsOmitted": 17}
    cap = next(c for c in _capabilities_for("python", payload, "1") if c["graph"] == "dataflow")
    assert cap["status"] == "partial"
    assert cap["edges_omitted"] == 17
    assert "17 edges omitted" in cap["limitations"]
    payload["reachingDefs"] = []  # cap zero remains partial
    assert next(c for c in _capabilities_for("python", payload, "1") if c["graph"] == "dataflow")["status"] == "partial"
    payload.pop("reachingDefsOmitted")  # old exports cannot provide an exact count
    cap = next(c for c in _capabilities_for("python", payload, "1") if c["graph"] == "dataflow")
    assert cap["edges_omitted"] is None
    assert "unknown" in cap["limitations"]
    payload["reachingDefsTruncated"] = False
    assert next(c for c in _capabilities_for("python", payload, "1") if c["graph"] == "dataflow")["status"] == "empty"


@pytest.mark.skipif(not os.environ.get("CBE_JOERN_HOME"), reason="Joern is not configured")
def test_real_truncated_dataflow_reports_partial(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def compute(x):\n    y = x + 1\n    z = y * x\n    return z\n\ncompute(3)\n")
    graph = analyze_graph(repo, tmp_path / "graph.json", backend="joern", languages=["python"],
                          joern_home=Path(os.environ["CBE_JOERN_HOME"]), max_reaching_defs=1)
    cap = next(c for c in graph["capabilities"] if c["graph"] == "dataflow" and c["language"] == "python")
    assert cap["status"] == "partial"
    assert cap["reaching_def_edges"] == 1
    assert cap["edges_omitted"] > 0
    diag = next(d for d in graph["diagnostics"] if d["code"] == "reaching_defs_truncated")
    assert diag["edges_omitted"] == cap["edges_omitted"]
