# Test & Collection Reports

**Capability.** The report data model for test and collection outcomes, their terminal rendering, and their JSON round-trip serialization for distributed execution.

Use this subtree for anything about report objects flowing through hooks. BaseReport carries fields and presentation; TestReport/CollectReport are the concrete per-phase and collection reports; serialization functions convert both directions for workers.

**Children.**

- [Report Model & Rendering](r3-report-model.md) `r3-report-model` · 14 unit(s)
- [Report Serialization](r3-report-serialization.md) `r3-report-serialization` · 7 unit(s)

**Depends on.**

- [Terminal Writer](r3-terminal-writer.md) · graph-confirmed · 3 edge(s)

Parent: [Pytest Framework Codebase](r3-pytest.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
