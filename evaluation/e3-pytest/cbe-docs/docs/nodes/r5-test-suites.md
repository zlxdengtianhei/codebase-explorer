# pytest's own test suites

**Capability.** The testing/ tree exercising pytest's plugins and testing utilities: pytester itself, junitxml reporting, cache provider, conftest loading, argcomplete, and unittest integration. Each child covers one suite; helper fixtures live beside the tests that use them.

Use this subtree to find behavioral coverage and executable examples for each plugin area. Tests run through the pytester fixture, largely inprocess or via subprocess.

**Children.**

- [Pytester self-tests](r5-pytester-selftests.md) `r5-pytester-selftests` · 27 unit(s)
- [JUnit XML reporting tests](r5-junitxml-tests.md) `r5-junitxml-tests` · 12 unit(s)
- [Argcomplete tests](r5-argcomplete-tests.md) `r5-argcomplete-tests` · 4 unit(s)
- [Cache provider tests](r5-cacheprovider-tests.md) `r5-cacheprovider-tests` · 7 unit(s)
- [Conftest loading tests](r5-conftest-tests.md) `r5-conftest-tests` · 11 unit(s)
- [unittest integration tests](r5-unittest-integration-tests.md) `r5-unittest-integration-tests` · 38 unit(s)

**Depended on by.**

- [Cache provider tests](r5-cacheprovider-tests.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r5-cacheprovider-tests ` → ` r5-test-suites `)

Parent: [pytest codebase](r5-pytest-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
