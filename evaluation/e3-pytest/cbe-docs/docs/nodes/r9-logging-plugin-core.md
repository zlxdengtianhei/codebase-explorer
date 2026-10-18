# Plugin Lifecycle and Phase Capture

**Capability.** Builds and installs the handler set (caplog, report, file, live) and brackets session phases and each test phase with capture via _runtest_for and wrapper hooks.

Read this to see when logging handlers are attached and detached and which capture is active per phase. _runtest_for is the shared per-phase engine; the group units enumerate the hook surface. Formatter and handler construction is delegated to sibling capabilities.

**Depends on.**

- [caplog Capture Fixture](r9-logging-capture-fixtures.md) · graph-confirmed · 2 edge(s)
- [Logging Configuration](r9-logging-config-options.md) · graph-confirmed · 13 edge(s)
- [Log Formatters](r9-logging-formatters.md) · graph-confirmed · 2 edge(s)
- [Live and File Handlers](r9-logging-live-file-handlers.md) · model-inferred · 0 edge(s)
- [Test Runner](r9-test-runner.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Live Logging Tests](r9-tests-logging-live-cli.md) · model-inferred · 0 edge(s)

Parent: [Logging Plugin](r9-logging-plugin.md)

## Units (10)

<a id="u-a9c07f26da5f"></a>
### `LoggingPlugin`

`class LoggingPlugin:` · [src/_pytest/logging.py:L641-L644][f1]

Plugin that wires pytest into the logging module: it builds a shared report formatter, in-memory caplog/report handlers, an optional file handler, and a live-logging handler, and installs/removes them around session phases and each test phase.

The constructor resolves log_level, creates the shared formatter via _create_formatter, two LogCaptureHandlers, file logging (creating the target directory if missing and defaulting to os.devnull, opening with the configured mode and UTF-8), a DatetimeFormatter for the file, log_cli_level, and — when _log_cli_enabled() — a _LiveLoggingStreamHandler over the terminal reporter and capture manager, otherwise a _LiveLoggingNullHandler; a distinct log_cli formatter is applied. Finally it disables any loggers named by --log-disable (setting logger.disabled = True; empty list returns early).

**Notes.**

- side_effect: Constructor may create directories (os.makedirs) and open the log file via _FileHandler.

calls: [LoggingPlugin._create_formatter](r9-logging-plugin-core.md#u-16167d77fe42), [get_option_ini](r9-logging-config-options.md#u-f7c75fa6744f), [get_log_level_for_setting](r9-logging-config-options.md#u-ac848bb6cc00), [LoggingPlugin._log_cli_enabled](r9-logging-plugin-core.md#u-fd16719ef713), [_FileHandler](r9-logging-live-file-handlers.md#u-ee6819f6cc32)

**Uncertainties.**

- Whether the log_file directory creation happens only when log_file differs from os.devnull is clear from the if, but error handling of os.makedirs failures is not shown.

<a id="u-ae4f754f757a"></a>
### `src/_pytest/logging.py:pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/logging.py:L636-L638][f1]

Registers the LoggingPlugin under the name 'logging-plugin' on the plugin manager.

It runs trylast so it executes after the terminal reporter and capture manager are configured, which the plugin's live-logging assumptions depend on.

calls: [LoggingPlugin](r9-logging-plugin-core.md#u-a9c07f26da5f)

<a id="u-16167d77fe42"></a>
### `LoggingPlugin._create_formatter`

`def _create_formatter(self, log_format, log_date_format, auto_indent): # Color option…` · [src/_pytest/logging.py:L719-L735][f1]

Builds the formatter used by report and live-CLI handlers.

Color is read as config.option.color with fallback 'no' (present only when the terminal plugin is loaded). If color is not 'no' and the format contains a %(levelname)..s pattern, it creates a ColoredLevelFormatter over a fresh terminal writer; otherwise a plain DatetimeFormatter. In both cases the formatter's _style is replaced with a PercentStyleMultiline carrying the same format and the auto_indent setting, enabling multiline reindentation for all output through this plugin.

calls: [ColoredLevelFormatter](r9-logging-formatters.md#u-ffc6c97076c3), [DatetimeFormatter](r9-logging-formatters.md#u-c47be60e560d), [PercentStyleMultiline](r9-logging-formatters.md#u-44f224c8760d)

<a id="u-fd16719ef713"></a>
### `LoggingPlugin._log_cli_enabled`

`def _log_cli_enabled(self) -> bool:` · [src/_pytest/logging.py:L759-L772][f1]

Decides whether live logging is active: enabled is true when the --log-cli-level option is set or the log_cli ini is truthy; if not enabled it returns False.

Even when enabled, a missing 'terminalreporter' plugin (e.g. under pytest-xdist) makes it return False; otherwise True.

<a id="u-ace1a5759def"></a>
### `LoggingPlugin._runtest_for`

`def _runtest_for(self, item: nodes.Item, when: str) -> Generator[None]:` · [src/_pytest/logging.py:L812-L834][f1]

Core per-phase capture shared by the pytest_runtest_setup/call/teardown hooks.

It attaches the shared caplog_handler and report_handler to the root logger at the configured level, resets both handlers (fresh records and streams), publishes the phase's record list and handler on the item stash (caplog_records_key[when] and caplog_handler_key), then yields. In a finally block it strips the report handler's captured text and records it as a report section via item.add_report_section(when, "log", log), so the section is emitted even when the phase fails.

**Notes.**

- side_effect: Writes item.stash entries consumed by the caplog fixture's handler/get_records accessors.

uses: [LogCaptureHandler](r9-logging-capture-fixtures.md#u-83fec58eea9a), [catching_logs](r9-logging-capture-fixtures.md#u-aa1f02003ef5)

**Uncertainties.**

- reset() on the handlers is graph-ambiguous between LogCaptureHandler.reset and the live-logging reset methods; for these shared LogCaptureHandler instances the records/stream reset applies.

<a id="u-82da37be5eb2"></a>
### `LoggingPlugin.pytest_runtestloop`

`def pytest_runtestloop(self, session: Session) -> Generator[None, object, object]:` · [src/_pytest/logging.py:L790-L801][f1]

Wraps the whole test-running loop in live and file log capture.

When collectonly is set it yields straight through with no handlers attached. Otherwise, if live logging is enabled and verbosity is below 1 it forces config.option.verbose to 1 to keep progress output coherent, then nests catching_logs around the log_cli_handler and log_file_handler (with their resolved levels) and yields the inner loop's result.

**Notes.**

- side_effect: Mutates self._config.option.verbose to 1 for the remainder of the run when live logging is on at low verbosity.

calls: [LoggingPlugin._log_cli_enabled](r9-logging-plugin-core.md#u-fd16719ef713); uses: [catching_logs](r9-logging-capture-fixtures.md#u-aa1f02003ef5)

<a id="u-214e4ce98b18"></a>
### `LoggingPlugin.pytest_unconfigure`

`def pytest_unconfigure(self) -> None: # Close the FileHandler explicitly. # (logging.…` · [src/_pytest/logging.py:L875-L879][f1]

Closes the file-log handler explicitly at unconfigure, on the assumption that logging.shutdown may have dropped its weak reference.

No other cleanup is performed here.

uses: [_FileHandler](r9-logging-live-file-handlers.md#u-ee6819f6cc32)

<a id="u-c9d1e8569f99"></a>
### `LoggingPlugin.set_log_path`

`def set_log_path(self, fname: str) -> None:` · [src/_pytest/logging.py:L737-L757][f1]

Redirects file logging to a new path (experimental API).

Relative paths are resolved against config.rootpath. If the parent directory does not exist it is created with parents. It opens the file with the stored log_file_mode and UTF-8 encoding, passes the stream to log_file_handler.setStream, and closes the previous stream if one is returned.

**Notes.**

- side_effect: Creates directories and files; the old log stream is closed only if setStream reports one.

<a id="u-5eaf4cdad2e4"></a>
### `logging-plugin-per-test-hooks`

`def pytest_runtest_logstart(self) -> None:` · [src/_pytest/logging.py:L803-L806][f1]

Per-test hooks coordinating the live handler's phase marker and the per-phase caplog capture.

pytest_runtest_logstart resets the live handler and sets when to 'start'; logreport sets 'logreport'; logfinish sets 'finish'. setup/call/teardown set the when marker, publish a fresh empty per-phase records dict on the item stash during setup (empty: dict assigned to caplog_records_key), and run their phase inside _runtest_for(item, phase). Teardown wraps that in try/finally deleting both caplog stash keys, so the fixture state is removed after teardown even if it raised.

calls: [LoggingPlugin._runtest_for](r9-logging-plugin-core.md#u-ace1a5759def); uses: [_LiveLoggingStreamHandler](r9-logging-live-file-handlers.md#u-f39c2e7e81cb)

<a id="u-1c5f6a27631d"></a>
### `logging-plugin-session-phase-hooks`

`def pytest_sessionstart(self) -> Generator[None]:` · [src/_pytest/logging.py:L774-L780][f1]

Wrapper hooks that bracket session-level phases (sessionstart, collection, sessionfinish) with live and file log capture.

Each first sets log_cli_handler.set_when to its phase name, then nests catching_logs around the log_cli_handler and log_file_handler at their configured levels and yields the inner hook result through the wrapper. The when marker drives _LiveLoggingStreamHandler's section headers.

uses: [catching_logs](r9-logging-capture-fixtures.md#u-aa1f02003ef5); calls: [_LiveLoggingStreamHandler](r9-logging-live-file-handlers.md#u-f39c2e7e81cb)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/logging.py
