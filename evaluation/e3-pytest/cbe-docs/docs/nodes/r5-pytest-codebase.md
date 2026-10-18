# pytest codebase

**Capability.** Recursive semantic decomposition of the pytest codebase into responsibility-owned subtrees: runtime fixture machinery, marker data model, configuration bootstrapping, process-level diagnostics, the unittest compatibility bridge, and pytest's own test suites.

Start at the root to navigate by responsibility. Each child owns one capability area spanning source modules and their dedicated test modules; edges below record observed unit-level evidence.

**Children.**

- [Fixture machinery](r5-fixture-machinery.md) `r5-fixture-machinery` · 0 unit(s)
- [Mark data model](r5-mark-model.md) `r5-mark-model` · 8 unit(s)
- [Configuration bootstrapping](r5-config-bootstrapping.md) `r5-config-bootstrapping` · 0 unit(s)
- [Runtime diagnostics and shared primitives](r5-runtime-diagnostics.md) `r5-runtime-diagnostics` · 0 unit(s)
- [unittest integration bridge](r5-unittest-bridge.md) `r5-unittest-bridge` · 0 unit(s)
- [pytest's own test suites](r5-test-suites.md) `r5-test-suites` · 0 unit(s)

**Depended on by.**

- [Faulthandler plugin](r5-faulthandler-plugin.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r5-faulthandler-plugin ` → ` r5-pytest-codebase `)
- [JUnit XML reporting tests](r5-junitxml-tests.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r5-junitxml-tests ` → ` r5-pytest-codebase `)

Parent: [Fixtures, Marks and Bootstrap Primitives](fixtures-marks-bootstrap.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
