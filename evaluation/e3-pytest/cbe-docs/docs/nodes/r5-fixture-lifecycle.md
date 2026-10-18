# Fixture setup, execution and teardown

**Capability.** Runtime lifecycle of a single fixture value: hook-driven setup, factory invocation (including generator/yield fixtures), result caching, dynamic scope evaluation, teardown chaining, and finalization order.

Consult this for what happens when a fixture value is produced and later finalized. pytest_fixture_setup drives resolve_fixture_function and call_fixture_func; FixtureDef.execute manages caching and teardown linkage.

**Depends on.**

- [Fixture declaration API](r5-fixture-declaration.md) · model-inferred · 0 edge(s)
- [Request objects and scoping context](r5-fixture-request-context.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Fixture setup display plugin](r5-setuponly-display.md) · model-inferred · 0 edge(s)

Parent: [Fixture machinery](r5-fixture-machinery.md)

## Units (7)

<a id="u-9674c75d4866"></a>
### `FixtureDef`

`class FixtureDef(Generic[FixtureValue]):` · [src/_pytest/fixtures.py:L975-L983][f1]

Container for one fixture definition: its factory function, visibility, scope, parametrization, cached result, and finalizers.

The constructor (check_ispytest-guarded) stores baseid (empty string when None, so no-location fixtures match everywhere) and has_location (baseid is not None). The scope argument is normalized: None becomes Scope.Function, a callable is resolved via _eval_scope_callable, and a string is converted via Scope.from_user with a descriptive error mentioning the fixture name and location. Also stores params and ids for direct parametrization, computes argnames from the function signature via getfuncargnames, initializes cached_result to None and an empty finalizer list, and keeps _autouse only for a pytest-9 deprecation warning. The scope property exposes the scope's string value; addfinalizer appends to the finalizer list; cache_key is request.param (or None when unset); __repr__ summarizes argname, scope and baseid. finish(request) runs teardown: finalizers are popped and called one by one, collecting BaseExceptions instead of propagating; then the pytest_fixture_post_finalizer hook fires on the node, and cached_result is invalidated and finalizers cleared even if calls failed (bound-method finalizers could otherwise keep objects alive). A single collected exception is re-raised; multiple are wrapped in a BaseExceptionGroup (reversed order) titled with the fixture name and node.

calls: [_eval_scope_callable](r5-fixture-lifecycle.md#u-3cc0cfd5b322)

<a id="u-a9d8d7ad2f88"></a>
### `FixtureDef.execute`

`def execute(self, request: SubRequest) -> FixtureValue:` · [src/_pytest/fixtures.py:L1074-L1134][f1]

Return the fixture's value, executing the factory if needed, and manage caching and teardown linkage.

First every argname the fixture requests is resolved via request._get_active_fixturedef — before the cache check, so an invalidated dependency (e.g. re-parametrization) has already cleared this fixture's cache; non-pseudo dependency defs are saved so this fixture's finish can later be attached to them. If cached_result exists, the request's cache key is compared to the stored key with ==, falling back to identity when comparison raises ValueError/RuntimeError (e.g. numpy arrays). On a hit, a stored exception is re-raised with its original traceback; otherwise the cached value is returned. On a key mismatch the previous instance is torn down via finish before proceeding. The finalizer (partial finish bound to the request) is then added to each saved dependency fixture, after the cache check to avoid duplicates. Finally the pytest_fixture_setup hook runs the setup and populates cached_result, and the finalizer is added to the request node in a finally block so teardown is scheduled even if setup raised.

calls: [FixtureRequest](r5-fixture-request-context.md#u-e8edbc928469)

**Uncertainties.**

- Which of the several addfinalizer overloads (Request/TopRequest/SubRequest) runs at request.node / parent_fixture is not resolvable from this file alone.
- exact hook behavior of pytest_fixture_setup is defined in the hook impl, partly in this file's own pytest_fixture_setup.

<a id="u-3cc0cfd5b322"></a>
### `_eval_scope_callable`

`def _eval_scope_callable( scope_callable: Callable[[str, Config], _ScopeName], fixtur…` · [src/_pytest/fixtures.py:L952-L972][f1]

Evaluate a dynamic scope callable for a fixture.

Calls it with keyword arguments fixture_name and config. Any Exception during the call is re-raised as a TypeError explaining the expected (*, fixture_name, config) signature, chained to the original. A non-str return value triggers fail() with the actual returned object; the validated string is returned.

<a id="u-a5f00eff11db"></a>
### `pytest_fixture_setup`

`def pytest_fixture_setup( fixturedef: FixtureDef[FixtureValue], request: SubRequest )…` · [src/_pytest/fixtures.py:L1167-L1207][f1]

Hook implementation that sets up a fixture.

Collects kwargs by resolving each of fixturedef.argnames through request.getfixturevalue, resolves the bound callable, and computes the cache key from request.param. Async generator or coroutine functions produce a PytestRemovedIn9Warning (becoming an error in pytest 9) noting no plugin handled the async fixture. call_fixture_func runs the factory; on TEST_OUTCOME exceptions the cached_result is set to (None, key, (exc, traceback)) so later requests re-raise the same error, with skip exceptions flagged _use_item_location=True so the skip points at the test rather than the fixture; the exception then propagates. On success cached_result becomes (result, key, None) and the result is returned.

calls: [call_fixture_func](r5-fixture-lifecycle.md#u-74e05a97a08f), [resolve_fixture_function](r5-fixture-lifecycle.md#u-9ee7ba8a51de)

**Uncertainties.**

- TEST_OUTCOME's exact exception set lives in _pytest.outcomes and is not shown here.

<a id="u-74e05a97a08f"></a>
### `call_fixture_func`

`def call_fixture_func( fixturefunc: _FixtureFunc[FixtureValue], request: FixtureReque…` · [src/_pytest/fixtures.py:L916-L931][f1]

Invoke a fixture factory and obtain its value, handling generator fixtures.

For a generator function, the first next() result is the fixture value; StopIteration means the fixture yielded nothing and is converted to a ValueError naming the fixture. A finalizer partial (_teardown_yield_fixture with the generator) is registered on the request so the code after the yield runs at teardown. Non-generator functions are called directly with kwargs and their return value is the fixture value.

calls: [_teardown_yield_fixture](r5-fixture-lifecycle.md#u-749c4d15ce85)

<a id="u-749c4d15ce85"></a>
### `_teardown_yield_fixture`

`def _teardown_yield_fixture(fixturefunc, it) -> None:` · [src/_pytest/fixtures.py:L934-L949][f1]

Advance a yield-fixture's generator to run its teardown code.

StopIteration is the normal single-yield case; if another value is produced the fixture yielded more than once and fail() reports 'fixture function has more than one yield' with the indented source and file:line, pytrace=False. Exceptions raised by the teardown code itself propagate uncaught.

<a id="u-9ee7ba8a51de"></a>
### `resolve_fixture_function`

`def resolve_fixture_function( fixturedef: FixtureDef[FixtureValue], request: FixtureR…` · [src/_pytest/fixtures.py:L1143-L1164][f1]

Return the callable to invoke for a fixture, binding to the requesting instance when appropriate.

If request.instance is None the raw fixturedef.func is used. Otherwise, if the function is already bound (has __self__) to a class the instance does not belong to (e.g. a fixture defined on a plugin class), the function is returned unbound. Otherwise getimfunc extracts the underlying function, and if it differs from the original it is bound to the instance via __get__ so class-defined fixtures see self.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/fixtures.py
