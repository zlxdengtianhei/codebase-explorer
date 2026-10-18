# Fixture declaration API

**Capability.** The @pytest.fixture decorator surface: turning decorated functions into fixture definitions carrying scope/params/autouse/ids/name, plus the deprecated yield_fixture alias and the marker accessor used by other subsystems.

Read this to understand how a Python function becomes a fixture definition object. Other code detects fixtures via getfixturemarker and consumes the resulting FixtureFunctionDefinition.

**Depends on.**

- [Fixture machinery](r5-fixture-machinery.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r5-fixture-declaration ` → ` r5-fixture-machinery `)

**Depended on by.**

- [Fixture setup, execution and teardown](r5-fixture-lifecycle.md) · model-inferred · 0 edge(s)
- [Fixture registry and requirement closure](r5-fixture-registry.md) · model-inferred · 0 edge(s)

Parent: [Fixture machinery](r5-fixture-machinery.md)

## Units (5)

<a id="u-dea499384199"></a>
### `src/_pytest/fixtures.py:fixture (2)`

`def fixture( fixture_function: FixtureFunction | None = None, *, scope: _ScopeName | …` · [src/_pytest/fixtures.py:L1324-L1396][f1]

Implementation of the @pytest.fixture decorator, usable bare or with keyword arguments.

Builds a FixtureFunctionMarker from scope (a scope name or a (fixture_name, config) callable), params (converted to a tuple), autouse, ids (None, kept as-is when callable, else tuple) and name. When a positional fixture_function is supplied the marker is applied immediately, returning a FixtureFunctionDefinition; otherwise the marker is returned for later use as a decorator factory. The overloads cover the two call shapes.

<a id="u-e64689959414"></a>
### `yield_fixture`

`def yield_fixture( fixture_function=None, *args, scope="function", params=None, autou…` · [src/_pytest/fixtures.py:L1399-L1422][f1]

Deprecated alias of @pytest.fixture for yield-based factories.

Emits the YIELD_FIXTURE deprecation warning at stacklevel 2, then forwards all arguments (positional function and args included) to fixture() and returns its result.

calls: [src/_pytest/fixtures.py:fixture (2)](r5-fixture-declaration.md#u-dea499384199)

<a id="u-1909e1363a5b"></a>
### `FixtureFunctionMarker`

`class FixtureFunctionMarker:` · [src/_pytest/fixtures.py:L1210-L1221][f1]

Frozen dataclass holding @pytest.fixture arguments (scope, params, autouse, ids, name); its __call__ applies the marker to a function and produces the FixtureFunctionDefinition.

__post_init__ enforces internal creation via check_ispytest. Applying it: a class raises ValueError ('class fixtures not supported'); re-decorating a FixtureFunctionDefinition raises ValueError about double application; a function carrying pytestmark triggers a MARKED_FIXTURE deprecation warning. After building the definition, a fixture named 'request' fails via fail() with the function location, since the name is reserved. Otherwise the definition is returned.

calls: [FixtureFunctionDefinition](r5-fixture-declaration.md#u-b64081ca680c)

<a id="u-b64081ca680c"></a>
### `FixtureFunctionDefinition`

`class FixtureFunctionDefinition:` · [src/_pytest/fixtures.py:L1252-L1253][f1]

The object produced by @pytest.fixture: it wraps the fixture function, carries its marker, and replaces the function in its namespace.

The constructor stores the name (explicit marker name or function name, mirrored to __name__), binds the function to an instance if given (so fixtures on classes work), and copies function metadata via functools.update_wrapper. Calling the object directly fails with fail(): fixtures must be requested by tests, not invoked (message references the pytest docs and deprecation page). __get__ makes the object behave like a method descriptor: accessing it on an instance returns a new FixtureFunctionDefinition bound to that instance with the same marker. _get_wrapped_function returns the underlying callable; __repr__ shows '<pytest_fixture(function)>'.

<a id="u-69d0b19e6ce4"></a>
### `getfixturemarker`

`def getfixturemarker(obj: object) -> FixtureFunctionMarker | None:` · [src/_pytest/fixtures.py:L161-L165][f1]

Return the fixture marker attached to an object, or None.

For a FixtureFunctionDefinition it returns its _fixture_function_marker; any other object (including a plain function) yields None. The comment notes intent to migrate to using FixtureFunctionDefinition directly.

uses: [FixtureFunctionDefinition](r5-fixture-declaration.md#u-b64081ca680c)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/fixtures.py
