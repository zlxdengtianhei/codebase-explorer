# Report serialization tests

**Capability.** Round-trip verification of TestReport/CollectReport through _to_json/_from_json and the pytest_report_to/from_serializable hooks, covering chained exceptions, reprentry styles, path-like attributes, timestamps, and failure paths.

The hooks child verifies hook registration and $report_type validation; serialization covers historical xdist regressions and payload fidelity.

**Children.**

- [Report hook tests](r4-report-hooks-tests.md) `r4-report-hooks-tests` · 4 unit(s)
- [Report serialization regressions](r4-report-serialization-tests.md) `r4-report-serialization-tests` · 18 unit(s)

Parent: [Test suites](r4-test-suites.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
