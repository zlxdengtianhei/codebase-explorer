# Marking & Test Selection

**Capability.** The marker plugin (pytest.mark, -k, -m, --markers, parametrize helpers) and its functional test suite covering selection semantics, marker registration, and parametrization edge cases.

Use this subtree for anything about attaching marks to items or selecting tests by keyword/mark expressions. The implementation node owns matching and configuration; the test nodes verify the public behavior end-to-end.

**Children.**

- [Marker Plugin Core](r3-mark-implementation.md) `r3-mark-implementation` · 8 unit(s)
- [-k / -m Selection Tests](r3-mark-selection-tests.md) `r3-mark-selection-tests` · 11 unit(s)
- [Marker Registry & Decorator Tests](r3-mark-registry-tests.md) `r3-mark-registry-tests` · 16 unit(s)
- [Parametrize & Parameter-Set Tests](r3-mark-parametrize-tests.md) `r3-mark-parametrize-tests` · 11 unit(s)

Parent: [Pytest Framework Codebase](r3-pytest.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
