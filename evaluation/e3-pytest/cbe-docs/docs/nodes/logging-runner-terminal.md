# Logging, Runner and Terminal Loop

**Capability.** Owns the execution loop and its output: Python logging integration with caplog and live/file handlers, the runtest protocol with SetupState and CallInfo producing report objects, and the TerminalReporter rendering progress and summaries, plus their test suites. Runner and terminal cohere because reports are produced here and consumed there.

Use this subtree to trace how one item moves through setup/call/teardown into reports and then screen output, and how log records flow into caplog and files. The reporting of results is delegated from runner to terminal reporter.

**Children.**

- [pytest Core](r9-pytest-core.md) `r9-pytest-core` · 0 unit(s)

**Depends on.**

- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 6 edge(s)
- [Fixtures, Marks and Bootstrap Primitives](fixtures-marks-bootstrap.md) · graph-confirmed · 1 edge(s)
- [Framework Overview](framework-overview.md) · graph-confirmed · 7 edge(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 7 edge(s)
- [Platform, I/O and Reporting Plugins](platform-io-plugins.md) · graph-confirmed · 10 edge(s) · Terminal reporting and warning handling interplay with the platform plugin capabilities.
- [Runtime Helper Library](runtime-helper-library.md) · graph-confirmed · 7 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · graph-confirmed · 394 edge(s)

**Depended on by.**

- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 3 edge(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 1 edge(s)

Parent: [Framework Core](framework-core.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
