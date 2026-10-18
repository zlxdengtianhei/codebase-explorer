# Live Logging Tests

**Capability.** Verifies log_cli behavior: enable/disable, default and configured levels, per-phase sections, unknown sections, hook-timed records, newline handling and direct _LiveLoggingStreamHandler testing with a dummy terminal.

Read this when changing live-logging behavior; it pins section boundaries, level thresholds and capture suspension. The captured-log-sections group also covers separation of logs per phase alongside stdout/stderr.

**Depends on.**

- [Plugin Lifecycle and Phase Capture](r9-logging-plugin-core.md) · model-inferred · 0 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 31 edge(s)

Parent: [Logging Reporting Test Suite](r9-tests-logging-reporting.md)

## Units (10)

<a id="u-2da400d7d9a1"></a>
### `test_reporting-captured-log-sections`

`def test_nothing_logged(pytester: Pytester) -> None:` · [testing/logging/test_reporting.py:L17-L33][f1]

Verifies that pytest captures and reports logging separately per test phase, alongside stdout/stderr.

test_nothing_logged writes only to stdout/stderr and asserts a 'Captured *log call' header cannot be matched (fnmatch raises pytest.fail.Exception inside pytest.raises). test_messages_logged with --log-level=INFO shows all three captured sections. test_setup_logging and test_teardown_logging confirm logs emitted in setup/teardown hooks appear under 'Captured *log setup' and 'Captured *log teardown' headers; teardown asserts a failing teardown yields ret 1 with call and teardown sections both present.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- Exact header text is only checked via fnmatch wildcards, so precise section titles are not established from this source alone.

<a id="u-4dd861bc9de7"></a>
### `test_reporting-hooks-logging`

`def test_log_in_hooks(pytester: Pytester) -> None:` · [testing/logging/test_reporting.py:L1061-L1092][f1]

Checks that log records emitted from early/late hooks reach both live output and the log file.

test_log_in_hooks defines pytest_runtestloop, pytest_sessionstart, and pytest_sessionfinish in conftest; with log_cli=true and log_file at INFO, all three messages must appear on stdout and in the file. test_log_in_runtest_logreport logs 'logreport' from pytest_runtest_logreport for a single passing test and asserts the file contains exactly three occurrences, one per report phase (setup/call/teardown).

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- The count of 3 relies on exactly one setup, call, and teardown report for the passing test; the mapping to report phases is inferred, not stated in code.

<a id="u-1d34144d0eef"></a>
### `test_reporting-log-cli-default-level`

`def test_log_cli_default_level(pytester: Pytester) -> None: # Default log file level` · [testing/logging/test_reporting.py:L209-L240][f1]

Covers live logging at its default level.

test_log_cli_default_level asserts the logging plugin's log_cli_handler.level is NOTSET when only log_cli=true is set, that WARNING records appear live while INFO ones do not, and that the suite exits 0. test_log_cli_default_level_multiple_tests ensures the newline added by the live logger is reset between tests, matching node-id headers and 50%/100% progress for two tests. test_log_cli_default_level_sections verifies the full sequence of live sections (start/setup/call/teardown/finish) for two tests using conftest hooks pytest_runtest_logstart/logfinish and a yield fixture logging in setup and teardown.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-38083a514dca"></a>
### `test_reporting-log-cli-level-config`

`def test_log_cli_level(pytester: Pytester) -> None: # Default log file level` · [testing/logging/test_reporting.py:L500-L547][f1]

Verifies setting the live-log threshold via CLI versus INI.

test_log_cli_level asserts plugin.log_cli_handler.level equals INFO both with --log-cli-level=INFO and with --log-level=INFO, that INFO messages print live while DEBUG ones are suppressed, and that exit code stays 0. test_log_cli_ini_level obtains the same behavior from log_cli_level=INFO in the INI, run with -s only. Both use no_fnmatch_line to reject the suppressed debug text.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-d3c109b90aa6"></a>
### `testing/logging/test_reporting.py:test_live_logging_suspends_capture`

`def test_live_logging_suspends_capture( has_capture_manager: bool, request: FixtureRe…` · [testing/logging/test_reporting.py:L953-L971][f1]

Directly tests _LiveLoggingStreamHandler: with a DummyTerminal (a StringIO subclass whose section() is a no-op) cast to TerminalReporter and an optional MockCaptureManager whose global_and_fixture_disabled context manager records enter/exit, the handler is attached to a module-named logger with set_when('call') and removed via a finalizer.

Emitting a critical record must, when a capture manager exists, wrap the emit in exactly one enter/exit of that manager and write '\nsome message\n'; without one, calls stay empty yet the same text is still written, proving the handler tolerates a None capture manager.

calls: [FixtureRequest](r5-fixture-request-context.md#u-e8edbc928469)

**Uncertainties.**

- Behavior of _LiveLoggingStreamHandler itself is asserted, not read from source; the shared MockCaptureManager.calls list is not cleared between parametrized runs, though each run asserts one enter/exit pair.

<a id="u-cf2799ac8c50"></a>
### `test_live_logs_unknown_sections`

`def test_live_logs_unknown_sections( pytester: Pytester, request: FixtureRequest ) ->…` · [testing/logging/test_reporting.py:L356-L417][f1]

With log_cli=true, a conftest defines pytest_runtest_protocol that logs a warning outside any known live-log section, alongside logstart/logfinish hooks and a fixture.

The test asserts the 'Unknown Section!' warning is printed first, before the test's node-id header, and that the usual start/setup/call/teardown/finish live sections still render in order with a passing result.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-1c7ffc9edb0c"></a>
### `test_log_cli_auto_enable`

`def test_log_cli_auto_enable(pytester: Pytester, cli_args: str) -> None:` · [testing/logging/test_reporting.py:L586-L630][f1]

Parametrized over cli_args in {'', '--log-level=WARNING', '--log-file-level=WARNING', '--log-cli-level=WARNING'} with INI log_level=INFO/log_cli_level=INFO.

Only --log-cli-level=WARNING enables live logs: stdout shows the node header, live log call section, the WARNING record, and no 'INFO' string. All other cases show only the summary line, with neither INFO nor WARNING rendered live, confirming INI settings do not auto-enable live logging and log-level/log-file-level do not either.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-5c9e4a94eb5e"></a>
### `test_log_cli_enabled_disabled`

`def test_log_cli_enabled_disabled(pytester: Pytester, enabled: bool) -> None:` · [testing/logging/test_reporting.py:L178-L206][f1]

Parametrized over enabled True/False to test that log_cli=true in the INI turns on live log output during a passing test that logs a critical message.

When enabled, stdout must show the node id, '-- live log call --', the CRITICAL record, and 'PASSED*'; when disabled (no INI written), the message must not appear anywhere in stdout.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-673c24381d8a"></a>
### `test_log_cli_level_log_level_interaction`

`def test_log_cli_level_log_level_interaction(pytester: Pytester) -> None:` · [testing/logging/test_reporting.py:L94-L121][f1]

Checks that --log-cli-level and --log-level configure independent thresholds for live and captured logging.

A failing test emits debug/info/warning/error records on the root logger; run with --log-cli-level=INFO and --log-level=ERROR, the live-log section must show INFO, WARNING, and ERROR lines under '-- live log call' plus the failure summary, while any 'DEBUG' occurrence in stdout is rejected via no_re_match_line.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-8f16501c5b99"></a>
### `test_sections_single_new_line_after_test_outcome`

`def test_sections_single_new_line_after_test_outcome( pytester: Pytester, request: Fi…` · [testing/logging/test_reporting.py:L420-L497][f1]

Checks newline handling of live-log sections when a teardown and a finish hook each log two consecutive warnings.

Beyond fnmatch ordering assertions, two regex searches on the full stdout (MULTILINE) require the 'live log teardown' and 'live log finish' sections to be followed by WARNING lines separated by exactly single newlines, demonstrating no blank-line accumulation between repeated records.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- The regexes (.+)live log teardown(.+)\nWARNING(.+)\nWARNING(.+) constrain the immediate newline layout but the precise writer behavior lives outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/logging/test_reporting.py
