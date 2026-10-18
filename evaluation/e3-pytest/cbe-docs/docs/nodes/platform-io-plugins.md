# Platform, I/O and Reporting Plugins

**Capability.** Owns pytest's user-facing runtime capabilities that surround the run loop: terminal rendering and pretty-printing, output capture, marking and selection, warning capture/filtering, report data models, and the warning-assertion helpers, together with their self-test suites. They cohere as presentation and annotation layers consumed by the core pipeline.

Enter here for anything the user sees or annotates: terminal text, captured output, marks and selection, warnings, and report objects. Each subtree groups one module-level responsibility with its verifying tests.

**Children.**

- [Pytest Framework Codebase](r3-pytest.md) `r3-pytest` · 1 unit(s)

**Depends on.**

- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 9 edge(s)
- [Fixtures, Marks and Bootstrap Primitives](fixtures-marks-bootstrap.md) · graph-confirmed · 1 edge(s)
- [Framework Overview](framework-overview.md) · graph-confirmed · 1 edge(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 13 edge(s)
- [Runtime Helper Library](runtime-helper-library.md) · graph-confirmed · 5 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · graph-confirmed · 334 edge(s)

**Depended on by.**

- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 4 edge(s) · Config setup interacts with terminal, capture and warning plugins during invocation building.
- [Fixtures, Marks and Bootstrap Primitives](fixtures-marks-bootstrap.md) · graph-confirmed · 2 edge(s)
- [Framework Overview](framework-overview.md) · graph-confirmed · 1 edge(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 1 edge(s)
- [Logging, Runner and Terminal Loop](logging-runner-terminal.md) · graph-confirmed · 10 edge(s) · Terminal reporting and warning handling interplay with the platform plugin capabilities.
- [Runtime Helper Library](runtime-helper-library.md) · graph-confirmed · 24 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · graph-confirmed · 36 edge(s)

Parent: [pytest Codebase](pytest.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
