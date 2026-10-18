# Deprecation tests

**Capability.** Verifies each deprecation path emits exactly the expected warnings: legacy hookimpl/hookspec function attributes, py.path.local hook signatures, removed external plugins, deprecated fspath constructor argument, private-constructor checks, and marks-on-fixtures plus yield_fixture removals.

Hook-related deprecations are in deprecation-hook-tests; fixture-mark and yield_fixture deprecations in deprecation-fixture-tests.

**Children.**

- [Hook and plugin deprecation tests](r4-deprecation-hook-tests.md) `r4-deprecation-hook-tests` · 7 unit(s)
- [Fixture-mark deprecation tests](r4-deprecation-fixture-tests.md) `r4-deprecation-fixture-tests` · 4 unit(s)

Parent: [Test suites](r4-test-suites.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
