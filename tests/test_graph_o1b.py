"""O1b inventory and merge-boundary regressions."""
from cbe.graph import discover_sources, _prefer_resolved_imports
from cbe.graph_backends.identity import repository_files, file_id
from cbe.graph_backends._imports import ImportResolver
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
