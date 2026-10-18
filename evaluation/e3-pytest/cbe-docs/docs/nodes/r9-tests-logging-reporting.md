# Logging Reporting Test Suite

**Capability.** End-to-end tests of the logging plugin's user-visible behavior: live CLI output, file logs, formats, levels and capture reporting.

Use this to find behavioral coverage of logging features; it is split into live-log tests and file/format/config tests. These tests exercise the plugin through runpytest rather than unit-testing handlers directly.

**Children.**

- [Live Logging Tests](r9-tests-logging-live-cli.md) `r9-tests-logging-live-cli` · 10 unit(s)
- [Log File and Format Tests](r9-tests-logging-file-config.md) `r9-tests-logging-file-config` · 12 unit(s)

Parent: [pytest Core](r9-pytest-core.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
