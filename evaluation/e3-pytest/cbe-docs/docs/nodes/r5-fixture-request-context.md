# Request objects and scoping context

**Capability.** The ``request`` fixture API: the abstract FixtureRequest base, its TopRequest (test-level) and SubRequest (nested) variants, and scope resolution helpers that map a Scope to the owning collection node.

Use this to understand how fixtures discover their requesting context, request other fixtures, and locate the node that owns a given scope (get_scope_node, get_scope_package).

**Depends on.**

- [Fixture lookup error reporting](r5-fixture-lookup-errors.md) · graph-confirmed · 4 edge(s)

**Depended on by.**

- [Fixture setup, execution and teardown](r5-fixture-lifecycle.md) · model-inferred · 0 edge(s)
- [Pytester self-tests](r5-pytester-selftests.md) · graph-confirmed · 1 edge(s)

Parent: [Fixture machinery](r5-fixture-machinery.md)

## Units (5)

<a id="u-e8edbc928469"></a>
### `FixtureRequest`

`class FixtureRequest(abc.ABC):` · [src/_pytest/fixtures.py:L372-L379][f1]

Abstract base of the ``request`` fixture, giving fixtures and tests access to the requesting context and dynamic fixture resolution.

The constructor (guarded by check_ispytest) stores the fixture name, pyfuncitem, candidate fixturedefs per name (_arg2fixturedefs) and already-resolved defs (_fixture_defs), and declares self.param as Any — it only exists on parametrized SubRequests, otherwise attribute access fails. Context accessors are scope-gated: function raises AttributeError outside function scope; cls is available in class/function scope and may be None; instance returns None outside function scope; module requires function/class/module scope; path additionally allows package scope. Other accessors: _fixturemanager and session come from the pyfuncitem's session, config from the item, fixturenames is the item's static names plus any dynamically resolved ones, keywords delegates to the node, node is abstract. addfinalizer is abstract (subclasses attach teardowns differently); applymarker adds a marker to the node; raiseerror raises FixtureLookupError with an optional message. getfixturevalue resolves a fixture by name through _get_active_fixturedef and returns cached_result[0], asserting the value exists (failing if the fixture was already torn down). _iter_chain yields SubRequests from self up to but excluding the TopRequest. _get_active_fixturedef is the core resolver: 'request' yields a Function-scoped PseudoFixtureDef wrapping the request itself; an already-resolved def is returned after a scope re-check; otherwise fixturedefs are looked up (dynamically registered into _arg2fixturedefs on a dynamic getfixturevalue call) and a missing or empty list raises FixtureLookupError. Override depth is computed by counting how deep in the request chain the same fixture name is requested and indexing fixturedefs negatively; exhausting the levels raises FixtureLookupError. When the item is parametrized for the argname, param/param_index come from the callspec and the callspec's scope becomes the SubRequest's scope (overriding caching scope only — scope enforcement still uses fixturedef._scope); otherwise param is NOTSET and _check_fixturedef_without_param validates unparametrized access. Finally a SubRequest is built, fixturedef.execute runs (or reuses) the fixture, and the def is cached in _fixture_defs. _check_fixturedef_without_param fails via fail() when a parametrized fixture is requested by an item with nofuncargs=True (e.g. unittest TestCase), and when a parametrized fixture is requested without a parameter it builds a diagnostic message using the caller's frame (inspect.stack()[3]) and the fixture's location, falling back to the absolute path if it is not under rootpath. _get_fixturestack returns the chain's fixturedefs, outermost-first.

calls: [SubRequest](r5-fixture-request-context.md#u-f98a437497c0), [FixtureDef](r5-fixture-lifecycle.md#u-9674c75d4866); raises: [FixtureLookupError](r5-fixture-lookup-errors.md#u-3dd83deedbc8)

**Uncertainties.**

- inspect.stack()[3] assumes a fixed call depth; the frame identity for other call paths is not verified from this source.
- The exact interplay between callspec-driven scope and SetupState recreation is only documented in comments here.

<a id="u-f98a437497c0"></a>
### `SubRequest`

`class SubRequest(FixtureRequest):` · [src/_pytest/fixtures.py:L726-L731][f1]

The request object inside a fixture, chained to the request that asked for it.

The constructor stores the parent request, its own scope, the fixturedef being executed, and param_index; shares _fixture_defs and _arg2fixturedefs with the parent so resolution is item-wide; sets self.param only when param is not NOTSET, so non-parametrized fixture requests raise AttributeError on request.param. _scope returns the stored scope. node resolves the collection node for the scope: Function uses the pyfuncitem, Package uses get_scope_package (matching fixturedef.baseid), other scopes use get_scope_node; a missing Class-scope node falls back to the function item itself, and no node at all trips an assertion. _check_scope enforces that a narrower-scope request does not consume a wider-scoped fixture: when self._scope > requested_scope it builds a fixture stack listing and calls fail() with a ScopeMismatch message (pytrace=False); PseudoFixtureDefs are exempt. _format_fixturedef_line renders one 'path:line: def name(sig)' entry, with the path made relative to the session path when possible. addfinalizer attaches teardowns to the fixture's own fixturedef, so finalizers in a fixture fire at that fixture's teardown, not the item's.

calls: [get_scope_package](r5-fixture-request-context.md#u-fe12613f6ae5), [get_scope_node](r5-fixture-request-context.md#u-d99c04f8c65b)

<a id="u-e83ca79a5b8f"></a>
### `TopRequest`

`class TopRequest(FixtureRequest):` · [src/_pytest/fixtures.py:L684-L688][f1]

The request object presented to a test function; always Function scope.

Its constructor copies the item's name2fixturedefs into arg2fixturedefs and starts with no resolved defs. _scope is always Scope.Function, so _check_scope is a no-op (no scope violation is possible). node is the pyfuncitem itself. _fillfixtures populates item.funcargs by calling getfixturevalue for each static fixture name not already present — this is how a test's declared fixtures get instantiated. addfinalizer forwards to the item, so finalizers registered in a test run at item teardown.

<a id="u-d99c04f8c65b"></a>
### `get_scope_node`

`def get_scope_node(node: nodes.Node, scope: Scope) -> nodes.Node | None:` · [src/_pytest/fixtures.py:L135-L157][f1]

Return the closest ancestor of a node (including itself) matching the given Scope.

Function scope maps to the closest Item, Class/Module/Package/Session to the corresponding node classes via getparent. Returns None when no node of that scope exists, e.g. class scope with no Class parent; an unhandled scope reaches assert_never.

<a id="u-fe12613f6ae5"></a>
### `get_scope_package`

`def get_scope_package( node: nodes.Item, fixturedef: FixtureDef[object], ) -> nodes.N…` · [src/_pytest/fixtures.py:L123-L132][f1]

Locate the Package node matching a fixture's visibility baseid for package-scoped lookups.

Iterates the item's parents and returns the first Package whose nodeid equals fixturedef.baseid; if none matches, returns the item's session, effectively widening the location to session level.

uses: [FixtureDef](r5-fixture-lifecycle.md#u-9674c75d4866)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/fixtures.py
