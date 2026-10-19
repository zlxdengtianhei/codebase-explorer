"""Synthetic Joern methods retain identity without invented file anchors."""
import pytest
from cbe.graph_backends.joern import _normalize


@pytest.mark.parametrize("bad_path", ["demo", "<empty>", "go.mod"])
def test_unknown_synthetic_locations_are_diagnosed(bad_path):
    payload = {"_files": {"demo.go", "go.mod"},
               "methods": [{"nodeId": 1, "file": bad_path, "name": "<clinit>", "fullName": "demo.<clinit>"},
                           {"nodeId": 2, "file": "demo.go", "name": "helper", "fullName": "demo.helper"}],
               "cfg": [{"methodId": 1, "file": bad_path, "nodes": [{"i": 0, "nodeId": 3}], "edges": []}],
               "reachingDefs": [{"source": {"nodeId": 4, "file": bad_path},
                                 "target": {"nodeId": 5, "file": "demo.go"}}]}
    diagnostics = []
    nodes, edges = _normalize(payload, "test", diagnostics=diagnostics)
    unknown = {"cpg/method/1", "cpg/cfg/1/0", "cpg/dfn/4"}
    assert {n["id"] for n in nodes if n["path"] is None} == unknown
    assert {d["node"] for d in diagnostics} == unknown
    assert all(d["code"] == "unknown_node_location" and d["analyzer_path"] == bad_path for d in diagnostics)
    assert next(n for n in nodes if n["id"] == "cpg/method/2")["path"] == "demo.go"
    assert len(nodes) == 5 and len(edges) == 1
