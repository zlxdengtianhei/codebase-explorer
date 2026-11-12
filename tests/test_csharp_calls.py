"""C# calls whose full name spells repository types without their namespace."""
from cbe.graph_backends._calls import CallResolver, csharp_signature_key


def _call(full, caller="src/Use.cs"):
    return {"nodeId": 50, "callerFile": caller, "methodFullName": full, "name": "call", "code": "call()",
            "line": 3, "callees": [{"external": True, "nodeId": 99, "fullName": full}]}


def _method(node, full, file="src/Guard.cs"):
    return {"nodeId": node, "fullName": full, "name": full.split(":")[0].rsplit(".", 1)[-1], "file": file}


def test_key_drops_namespaces_inside_the_signature_only():
    own = "N.GuardExtensions.NotNull:T(N.IGuardClause,T,System.String)"
    call = "N.GuardExtensions.NotNull:T(IGuardClause,T,String)"
    assert csharp_signature_key(own) == csharp_signature_key(call) == "N.GuardExtensions.NotNull:T(IGuardClause,T,String)"
    assert csharp_signature_key("N.C.M:System.Collections.Generic.List<N.Foo>(N.Bar)") == "N.C.M:List<Foo>(Bar)"
    assert csharp_signature_key("N.C.M:List<A.Foo>(X)") != csharp_signature_key("N.C.M:Dictionary<B.Foo>(X)")
    assert csharp_signature_key("N.C.M") == "N.C.M"


def test_csharp_call_resolves_by_key_and_lists_ties():
    resolver = CallResolver([
        _method(1, "N.GuardExtensions.NotNull:T(N.IGuardClause,T)"),
        _method(2, "N.Guard.get_Against:N.IGuardClause()"),
        _method(3, "N.C.M:void(A.X)"),
        _method(4, "N.C.M:void(B.X)"),
    ])
    assert resolver.resolve(_call("N.GuardExtensions.NotNull:T(IGuardClause,T)")) == ("resolved", [1], [])
    assert resolver.resolve(_call("N.Guard.get_Against:IGuardClause()")) == ("resolved", [2], [])
    status, targets, _ = resolver.resolve(_call("N.C.M:void(X)"))
    assert status == "ambiguous" and sorted(targets) == [3, 4]


def test_an_overloaded_csharp_method_is_a_candidate_set():
    # Joern types the call Zero(0.0) as Zero:Int32(IGuardClause,Int32); the key would pick the
    # Int32 overload, so every overload of the name is returned and the call is ambiguous.
    resolver = CallResolver([
        _method(1, "N.GuardExtensions.Zero:System.Int32(N.IGuardClause,System.Int32)"),
        _method(2, "N.GuardExtensions.Zero:System.Double(N.IGuardClause,System.Double)"),
    ])
    status, targets, _ = resolver.resolve(_call("N.GuardExtensions.Zero:Int32(IGuardClause,Int32)"))
    assert status == "ambiguous" and targets == [1, 2]
    # A different method name never matches through the key.
    assert resolver.resolve(_call("N.GuardExtensions.Other:T(IGuardClause,T)"))[0] != "resolved"


def test_only_csharp_callers_use_the_key():
    resolver = CallResolver([_method(1, "N.GuardExtensions.NotNull:T(N.IGuardClause,T)")])
    assert resolver.resolve(_call("N.GuardExtensions.NotNull:T(IGuardClause,T)", caller="src/Use.java"))[0] != "resolved"
