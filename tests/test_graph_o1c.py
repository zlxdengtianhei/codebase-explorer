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
