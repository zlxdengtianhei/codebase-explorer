# Fixture-mark deprecation tests

**Capability.** Order-independence of the 'Marks applied to fixtures have no effect' PytestRemovedIn9Warning (marks below, above, or on both sides of @pytest.fixture) and the yield_fixture deprecation warning.

The three fixture tests together pin that the warning fires once per mark decorator regardless of decorator order.

**Depended on by.**

- [Hook and plugin deprecation tests](r4-deprecation-hook-tests.md) · model-inferred · 0 edge(s)

Parent: [Deprecation tests](r4-deprecated-tests.md)

## Units (4)

<a id="u-73f11390441d"></a>
### `test_yield_fixture_is_deprecated`

`def test_yield_fixture_is_deprecated() -> None:` · [testing/deprecated_test.py:L73-L76][f1]

Decorates a nested function with pytest.yield_fixture inside pytest.warns(DeprecationWarning, match 'yield_fixture is deprecated'), asserting the decorator itself emits that deprecation.

The decorated body is never called.

<a id="u-c6a6e623560d"></a>
### `test_fixture_disallow_on_marked_functions`

`def test_fixture_disallow_on_marked_functions():` · [testing/deprecated_test.py:L171-L178][f1]

Applies @pytest.fixture on top of parametrize and usefixtures marks and expects exactly one PytestRemovedIn9Warning matching 'Marks applied to fixtures have no effect'.

Exactly one is expected because applying @fixture twice is already prevented elsewhere, so the mark-application order cannot multiply the warning.

<a id="u-231f7c306386"></a>
### `test_fixture_disallow_marks_on_fixtures`

`def test_fixture_disallow_marks_on_fixtures():` · [testing/deprecated_test.py:L190-L197][f1]

Applies parametrize and usefixtures marks below @pytest.fixture (marks applied to an already-fixture function) and expects exactly two PytestRemovedIn9Warning 'Marks applied to fixtures have no effect' records, one per mark decorator, all pointing at this file.

<a id="u-060fb502eaeb"></a>
### `test_fixture_disallowed_between_marks`

`def test_fixture_disallowed_between_marks():` · [testing/deprecated_test.py:L208-L215][f1]

Applies usefixtures below @pytest.fixture and parametrize above it (marks on both sides of the fixture decorator) and expects exactly two PytestRemovedIn9Warning 'Marks applied to fixtures have no effect' records, one per mark decorator, confirming the warning is order-independent.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/deprecated_test.py
