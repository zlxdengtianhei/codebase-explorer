# pytest codebase

**Capability.** Owns the overall pytest testing framework: core introspection and exception reporting, public API surface, plugin hooks for leaked exceptions and doctests, approximate comparison assertions, legacy py.path compatibility, and the test suites covering all of these.

Use this root to orient between the product code under src/_pytest (and src/pytest, src/py) and the testing tree. Each child is a capability that can be read independently. Cross-cutting dependencies flow downward into introspection and compatibility utilities.

**Children.**

- [Python code inspection & exception rendering](r1-code-inspection.md) `r1-code-inspection` · 1 unit(s)
- [Compatibility & introspection utilities](r1-pytest-compat.md) `r1-pytest-compat` · 9 unit(s)
- [Doctest plugin](r1-doctest-plugin.md) `r1-doctest-plugin` · 1 unit(s)
- [Approximate comparison \(pytest.approx\)](r1-python-approx.md) `r1-python-approx` · 0 unit(s)
- [RaisesGroup test suite](r1-raises-group-tests.md) `r1-raises-group-tests` · 4 unit(s)
- [Leaked exception reporting](r1-leaked-exception-reporting.md) `r1-leaked-exception-reporting` · 1 unit(s)
- [Legacy py.path compatibility](r1-legacy-py-path.md) `r1-legacy-py-path` · 1 unit(s)
- [Configuration test suite](r1-config-test-suite.md) `r1-config-test-suite` · 11 unit(s)
- [Plugin manager test suite](r1-pluginmanager-tests.md) `r1-pluginmanager-tests` · 4 unit(s)
- [Acceptance test suite](r1-acceptance-tests.md) `r1-acceptance-tests` · 6 unit(s)
- [Main & wrap\_session tests](r1-main-session-tests.md) `r1-main-session-tests` · 6 unit(s)
- [Environment & integration tests](r1-integration-environment-tests.md) `r1-integration-environment-tests` · 0 unit(s)
- [Public pytest API surface](r1-public-api-surface.md) `r1-public-api-surface` · 1 unit(s)

**Depended on by.**

- [Public pytest API surface](r1-public-api-surface.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-public-api-surface ` → ` r1-pytest-codebase `)

Parent: [Framework Overview](framework-overview.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
