# Test Runner

**Capability.** Executes the runtest protocol for each item (setup/call/teardown), wraps invocations in CallInfo, manages the shared SetupState stack, and produces TestReport/CollectReport objects plus the --durations summary.

Use this subtree to trace how one item moves through phases into reports, how setup/teardown state is stacked and torn down, and how reports are created. The reporting of results is delegated to the terminal reporter; the runner only emits report objects and hook calls.

**Children.**

- [Runtest Protocol](r9-runner-protocol.md) `r9-runner-protocol` · 10 unit(s)
- [CallInfo and Collection](r9-runner-callinfo-collect.md) `r9-runner-callinfo-collect` · 4 unit(s)
- [Session SetupState](r9-runner-setupstate.md) `r9-runner-setupstate` · 5 unit(s)
- [Runner Options and Status Defaults](r9-runner-config-durations.md) `r9-runner-config-durations` · 3 unit(s)

**Depended on by.**

- [Plugin Lifecycle and Phase Capture](r9-logging-plugin-core.md) · model-inferred · 0 edge(s)

Parent: [pytest Core](r9-pytest-core.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
