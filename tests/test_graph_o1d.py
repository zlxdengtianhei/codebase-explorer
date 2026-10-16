"""Regressions for Python call identities and truncated dataflow exports."""
from cbe.graph_backends._calls import CallResolver
from cbe.graph_backends.joern import _normalize, _capabilities_for


def external_call(full, caller="pkg/app.py"):
    return {"nodeId": 10, "callerFile": caller, "methodFullName": full,
            "name": "invoke", "code": "invoke()", "line": 7,
            "callees": [{"external": True, "fullName": full}]}


def test_python_guessed_names_are_unresolved_but_library_paths_survive():
    resolver = CallResolver([], {"celery/beat.py", "celery/backends/redis.py", "pkg/app.py"})
    for full in ["result.results.<returnValue>.<member>(results).__iter__.<returnValue>.__next__",
                 "beat.Service.start", "decorator.<returnValue>.view_class"]:
        # No Python caller: this exercises classification independently of the exit guard.
        assert resolver.resolve(external_call(full, "")) == ("unresolved", [], [])
    assert resolver.resolve(external_call("copy.py:<module>.copy")) == (
        "external", [], ["copy.py:<module>.copy"])
    assert resolver.resolve(external_call("redis.py:<module>.StrictRedis.__init__"))[0] == "external"


def test_python_external_exit_guard_and_diagnostic():
    payload = {"calls": [external_call("future_receiver.invoke")], "methods": []}
    diagnostics = []
    _, edges = _normalize(payload, "1", diagnostics=diagnostics)
    assert edges[0]["status"] == "unresolved"
    assert edges[0]["target"] is None
    assert diagnostics[0]["code"] == "python_external_name_unverified"
    assert diagnostics[0]["analyzer_id"] == 10
    resolver = CallResolver([])
    assert resolver.resolve(external_call("__builtin.print"))[0] == "external"
    assert resolver.resolve(external_call("__builtin.dict<meta>.<returnValue>.setdefault"))[0] == "external"
    assert resolver.resolve(external_call("java.util.List.add", "Main.java"))[0] == "external"
    # The exit must also validate a newly introduced resolution branch.
    resolver._resolve = lambda call: ("external", [], ["future_guess"])
    assert resolver.resolve(external_call("anything")) == ("unresolved", [], [])
