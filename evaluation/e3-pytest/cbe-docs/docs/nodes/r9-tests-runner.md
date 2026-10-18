# Runner Test Suite

**Capability.** Functional and unit tests of the runner: runtest protocol outcomes, SetupState semantics, outcome/skip/exit exceptions, and report object contents.

Use this subtree to locate regressions and contracts for runner behavior. It splits into setup-state, protocol, exception/skip handling, and report-shape groups.

**Children.**

- [SetupState Tests](r9-tests-runner-setupstate.md) `r9-tests-runner-setupstate` · 10 unit(s)
- [Runtest Protocol Functional Tests](r9-tests-runner-protocol.md) `r9-tests-runner-protocol` · 20 unit(s)
- [Outcome, Exit and Skip Tests](r9-tests-runner-outcome-skip.md) `r9-tests-runner-outcome-skip` · 29 unit(s)
- [Report and CallInfo Tests](r9-tests-runner-reports.md) `r9-tests-runner-reports` · 14 unit(s)

Parent: [pytest Core](r9-pytest-core.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
