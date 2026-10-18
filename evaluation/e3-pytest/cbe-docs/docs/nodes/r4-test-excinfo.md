# Excinfo and traceback tests

**Capability.** Tests of ExceptionInfo and Traceback: construction and convenience API, entry access/cutting/filtering over a shared f/g/h raise chain, FormattedExcinfo rendering at entry, traceback, and toterminal levels, plus ExceptionGroup reporting.

Start at excinfo-api-tests for the ExceptionInfo surface, traceback-model-tests for Traceback manipulation, repr-tests for rendering, exceptiongroup-tests for group output formats.

**Children.**

- [ExceptionInfo API tests](r4-excinfo-api-tests.md) `r4-excinfo-api-tests` · 5 unit(s)
- [Traceback manipulation tests](r4-excinfo-traceback-model-tests.md) `r4-excinfo-traceback-model-tests` · 3 unit(s)
- [Traceback rendering tests](r4-excinfo-repr-tests.md) `r4-excinfo-repr-tests` · 6 unit(s)
- [ExceptionGroup reporting tests](r4-excinfo-exceptiongroup-tests.md) `r4-excinfo-exceptiongroup-tests` · 1 unit(s)

Parent: [Test suites](r4-test-suites.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
