# pytest Core

**Capability.** The pytest testing framework: running tests, capturing and reporting logs, rendering terminal output, with its own test suite validating each subsystem.

Start here to navigate the framework. Source capabilities (logging, runner, terminal reporting) sit alongside the test suites that verify them. Each subtree owns one module-level responsibility.

**Children.**

- [Logging Plugin](r9-logging-plugin.md) `r9-logging-plugin` · 0 unit(s)
- [Test Runner](r9-test-runner.md) `r9-test-runner` · 0 unit(s)
- [Terminal Reporting](r9-terminal-reporting.md) `r9-terminal-reporting` · 0 unit(s)
- [Logging Reporting Test Suite](r9-tests-logging-reporting.md) `r9-tests-logging-reporting` · 0 unit(s)
- [Runner Test Suite](r9-tests-runner.md) `r9-tests-runner` · 0 unit(s)
- [Doctest Plugin Test Suite](r9-tests-doctest.md) `r9-tests-doctest` · 8 unit(s)
- [Warning Capture Test Suite](r9-tests-recwarn.md) `r9-tests-recwarn` · 6 unit(s)
- [Node API Test Suite](r9-tests-nodes.md) `r9-tests-nodes` · 4 unit(s)
- [Mark Expression Test Suite](r9-tests-mark-expression.md) `r9-tests-mark-expression` · 3 unit(s)
- [Pastebin Test Suite](r9-tests-pastebin.md) `r9-tests-pastebin` · 2 unit(s)

Parent: [Logging, Runner and Terminal Loop](logging-runner-terminal.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
