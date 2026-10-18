# Stepwise tests

**Capability.** Verifies the --stepwise/--sw-skip/--sw-reset cache workflow: stopping at first failure, resuming across runs, cache preservation under xdist and disabled runs, corrupted-cache recovery, and interaction with xfail and collection errors.

Fixtures build the reusable failing suites; the tests assert exact user-facing messages and cache-file side effects.

**Children.**

- [Stepwise fixtures and helpers](r4-stepwise-fixtures.md) `r4-stepwise-fixtures` · 5 unit(s)
- [Stepwise behavior tests](r4-stepwise-behavior-tests.md) `r4-stepwise-behavior-tests` · 16 unit(s)

Parent: [Test suites](r4-test-suites.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
