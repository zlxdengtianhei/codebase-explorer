# Logging Plugin

**Capability.** Integrates Python's logging module into pytest sessions: option parsing, per-phase capture, formatter construction, live-CLI output and file logging all belong together because they share one handler/formatter lifecycle installed and removed around session and test phases.

Use this subtree to understand how log records flow from the root logger into caplog, live terminal output and log files. The plugin core wires config into handlers; formatters and handlers are supporting capabilities. Tests live under the logging test-suite subtree.

**Children.**

- [Plugin Lifecycle and Phase Capture](r9-logging-plugin-core.md) `r9-logging-plugin-core` · 10 unit(s)
- [Log Formatters](r9-logging-formatters.md) `r9-logging-formatters` · 8 unit(s)
- [caplog Capture Fixture](r9-logging-capture-fixtures.md) `r9-logging-capture-fixtures` · 8 unit(s)
- [Live and File Handlers](r9-logging-live-file-handlers.md) `r9-logging-live-file-handlers` · 4 unit(s)
- [Logging Configuration](r9-logging-config-options.md) `r9-logging-config-options` · 3 unit(s)

Parent: [pytest Core](r9-pytest-core.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
