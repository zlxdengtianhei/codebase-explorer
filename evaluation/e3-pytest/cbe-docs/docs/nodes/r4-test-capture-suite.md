# Capture tests

**Capability.** Verifies pytest's output capture: fd- and sys-level capture primitives, CaptureManager lifecycle, the capsys/capfd fixture family, per-test scoping, and end-to-end behaviors including logging interaction and invalid-fd edge cases.

Mechanism-tests cover the primitives and their factories; end-to-end-tests cover fixtures, per-test scoping, and subprocess-driven scenarios.

**Children.**

- [Capture primitive tests](r4-capture-mechanism-tests.md) `r4-capture-mechanism-tests` · 8 unit(s)
- [Capture end-to-end tests](r4-capture-endtoend-tests.md) `r4-capture-endtoend-tests` · 6 unit(s)

Parent: [Test suites](r4-test-suites.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
