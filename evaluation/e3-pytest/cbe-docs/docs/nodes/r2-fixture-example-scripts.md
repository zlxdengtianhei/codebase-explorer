# Fixture Example Scripts

**Capability.** Standalone example files used as pytester fixtures: conftest-visibility rules, fixture extension/overriding, class-level lookup, dynamic getfixturevalue ordering, and mock+fixture integration.

These files are inputs to TestFillFixtures-style end-to-end runs; each demonstrates one resolution rule of the fixture machinery.

**Depended on by.**

- [Fixture Semantics Suite](r2-fixture-tests.md) · model-inferred · 0 edge(s)

Parent: [Test Corpus](r2-test-suite.md)

## Units (1)

<a id="u-f667c5867ec1"></a>
### `arg1`

`def arg1(request):` · [testing/example_scripts/fixtures/fill_fixtures/test_conftest_funcargs_only_available_in_subdir/sub1/conftest.py:L7-L10][f1]

Fixture arg1 proves that a sibling-directory fixture is not visible.

It calls request.getfixturevalue("arg2") inside pytest.raises(pytest.FixtureLookupError); since arg2 is defined only in sub2's conftest, the lookup raises and the with-block swallows it, so arg1 completes normally with an implicit None result for test_1.

calls: [FixtureRequest](r5-fixture-request-context.md#u-e8edbc928469)

**Uncertainties.**

- That sub2's conftest is never in scope for sub1 depends on conftest visibility rules not present in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/fixtures/fill_fixtures/test_conftest_funcargs_only_available_in_subdir/sub1/conftest.py
