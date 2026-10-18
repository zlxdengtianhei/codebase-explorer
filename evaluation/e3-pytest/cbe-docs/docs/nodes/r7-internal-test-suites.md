# pytest's Own Test Suites

**Capability.** The testing/ tree validating framework behavior: Python collection semantics, session-level run control, PDB integration, warning handling, terminal writer output, and assorted plugin unit tests. These suites consume the framework core through pytester.

Navigate here to find executable specifications of framework behavior. Each child groups suites by the framework subsystem they pin down; example-script fixtures used by these suites live in the example-scripts subtree.

**Children.**

- [Python Collection Tests](r7-collect-tests.md) `r7-collect-tests` · 7 unit(s)
- [Session Run Control Tests](r7-session-tests.md) `r7-session-tests` · 29 unit(s)
- [PDB and Breakpoint Tests](r7-pdb-tests.md) `r7-pdb-tests` · 15 unit(s)
- [Warning Handling Tests](r7-warnings-tests.md) `r7-warnings-tests` · 14 unit(s)
- [Terminal Writer Tests](r7-terminalwriter-tests.md) `r7-terminalwriter-tests` · 12 unit(s)
- [Plugin and Utility Unit Tests](r7-misc-unit-tests.md) `r7-misc-unit-tests` · 16 unit(s)

Parent: [pytest Codebase](r7-pytest-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
