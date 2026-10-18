# Warning Handling

**Capability.** pytest's warning infrastructure: the PytestWarning category hierarchy users filter on, deferred warning messages, and the capture/filtering machinery wrapping collection and test execution.

Use this subtree to understand how pytest emits, filters, and renders warnings. warning_types defines the categories; warnings.py scopes capture around config/collection/runtest phases and formats captured warnings for the report.

**Children.**

- [Warning Categories](r3-warning-types.md) `r3-warning-types` · 3 unit(s)
- [Warning Capture Hooks](r3-warning-capture.md) `r3-warning-capture` · 4 unit(s)

Parent: [Pytest Framework Codebase](r3-pytest.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
