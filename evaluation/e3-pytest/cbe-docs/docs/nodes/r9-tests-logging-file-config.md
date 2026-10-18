# Log File and Format Tests

**Capability.** Covers --log-file/--log-file-* options, ini equivalents, date/format settings, ANSI-colored logs, --log-disable, emit-error handling, set_log_path and root-logger level defaults, plus collection-phase logging.

Use this for file-logging and formatting regressions and for level-configuration guarantees. The module_residual unit is only imports/setup.

**Depends on.**

- [Logging Configuration](r9-logging-config-options.md) · model-inferred · 0 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 40 edge(s)

Parent: [Logging Reporting Test Suite](r9-tests-logging-reporting.md)

## Units (12)

<a id="u-c5df41cc648b"></a>
### `test_reporting-collection-logging`

`def test_collection_live_logging(pytester: Pytester) -> None:` · [testing/logging/test_reporting.py:L974-L986][f1]

Covers logging during collection.

test_collection_live_logging expects a '--- live log collection ---' section with the root-logger INFO message when --log-cli-level=INFO is passed, with 0 items collected. test_collection_collect_only_live_logging parametrizes verbosity '', '-q', '-qq': at normal verbosity 'collected 1 item', the Module line, and '1 test collected' appear; with -q the 'collected 1 item*' line is absent and the node id plus a timed '1 test collected in X.YYs' line are required; with -qq only a compact 'file: 1' line. test_collection_logging_to_file sets log_file in the INI and asserts the collection-phase message and the test-call INFO record reach the file, the debug record does not (file level INFO), and no live collection section is printed.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- The '-q' timing regex '1 test collected in [0-9].[0-9][0-9]s' assumes a two-digit fractional second format.

<a id="u-9acddad8ad78"></a>
### `test_reporting-colored-log`

`def test_colored_captured_log(pytester: Pytester) -> None:` · [testing/logging/test_reporting.py:L1233-L1254][f1]

Tests ANSI coloring of logs under --color=yes.

test_colored_captured_log expects the failing test's captured log section to color the level name, matching the literal escape sequence '\x1b[32mINFO    \x1b[0m' before the message. test_colored_ansi_esc_caplogtext asserts the complementary invariant: caplog.text inside a test never contains the ESC character even when output is colored, via an in-test assertion (suite passes with ret 0).

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-e33365213bc7"></a>
### `test_reporting-date-format`

`def test_without_date_format_log(pytester: Pytester) -> None:` · [testing/logging/test_reporting.py:L1395-L1412][f1]

Covers log format/date-format configuration.

test_without_date_format_log shows the default format 'LEVEL  logger:file:line message' with no timestamp. test_date_format_log sets log_format='%(asctime)s; %(levelname)s; %(message)s' and log_date_format='%Y-%m-%d %H:%M:%S' via INI and regex-matches 'YYYY-MM-DD HH:MM:SS; WARNING; text'. test_date_format_percentf_log uses %f and requires exactly six microsecond digits. test_date_format_percentf_tz_log combines %f with %z and matches microseconds followed by a signed numeric offset, verifying timestamp and timezone directives compose correctly. All generated tests fail (assert False) so the captured log is reported.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- The timezone regex [+-][0-9\.]+ is loose and does not pin the exact %z rendering.

<a id="u-f6f4e587b3f0"></a>
### `test_reporting-disable-loggers`

`def test_disable_loggers(pytester: Pytester) -> None:` · [testing/logging/test_reporting.py:L1326-L1342][f1]

Tests the --log-disable option.

test_disable_loggers disables the 'disabled' logger; inside caplog.at_level(DEBUG) only the 'test' logger's debug record appears in caplog.record_tuples, and stderr stays empty. test_disable_loggers_does_not_propagate disables 'parent.child'; the parent's warning is captured but the child's is not, asserting exactly one record from 'parent', which shows disabling does not propagate upward to ancestors. test_log_disabling_works_with_log_cli combines --log-cli-level=DEBUG with --log-disable=disabled: the visible INFO record is printed live with its exact formatted line, the disabled logger's WARNING is absent, and stderr stays empty.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-b7d7af83f354"></a>
### `test_reporting-emit-error`

`def test_logging_emit_error(pytester: Pytester) -> None:` · [testing/logging/test_reporting.py:L1274-L1297][f1]

Tests pytest's override of logging's emit-error handling.

test_logging_emit_error passes wrong extra args to logging.warning, causing 'not all arguments converted during string formatting' inside emit(); pytest propagates it, so the test fails with a FAILURES section containing that message. test_logging_emit_error_supressed monkeypatches logging.raiseExceptions to False; the logging module then silently swallows the error and pytest also propagates nothing, so the test passes.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- The propagation override itself lives in _pytest.logging, not shown here; this file only observes its effects.

<a id="u-5179893e2c48"></a>
### `test_reporting-log-file-cli`

`def test_log_file_cli(pytester: Pytester) -> None: # Default log file level` · [testing/logging/test_reporting.py:L633-L663][f1]

Covers --log-file options.

test_log_file_cli runs with --log-file and --log-file-level=WARNING, asserts the file handler level, and that only warning records land in the file. test_log_file_mode_cli pre-writes a custom header and uses --log-file-mode=a, asserting the header survives and records are appended. test_log_file_mode_cli_invalid passes --log-file-mode=b and expects exit code ExitCode.USAGE_ERROR. test_log_file_cli_level repeats the file-content check at INFO level. test_log_file_cli_subdirectories_are_successfully_created passes --log-file=foo/bar/logf.log and asserts the foo/bar directory is created containing logf.log with exit code OK.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-f27743400cc3"></a>
### `test_reporting-log-file-ini`

`def test_log_file_ini(pytester: Pytester) -> None:` · [testing/logging/test_reporting.py:L776-L810][f1]

Covers log_file settings in the INI.

test_log_file_ini sets log_file/log_file_level=WARNING and checks only warning records are written. test_log_file_mode_ini adds log_file_mode=a with a pre-written header, asserting append behavior (ExitCode.OK). test_log_file_ini_level repeats at INFO. test_log_file_unicode logs ASCII and the box-drawing character '├' at INFO level and asserts all three messages, including the non-ASCII one, appear in the file read back as UTF-8.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-e17903f01bcf"></a>
### `test_reporting-log-set-path`

`def test_log_set_path(pytester: Pytester) -> None:` · [testing/logging/test_reporting.py:L1127-L1170][f1]

Tests per-test log redirection via logging_plugin.set_log_path.

Both tests install a wrapper hookimpl for pytest_runtest_setup that, before yielding, sets the logging plugin's report file to <pytester path>/<item name> with log_file_level=DEBUG and log_cli=true. test_log_set_path asserts each test's messages land in the file named after the test. test_log_set_path_with_log_file_mode adds log_file_mode=a, pre-writes custom headers into both files, and asserts headers are preserved alongside the appended messages with ExitCode.OK.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- set_log_path's semantics are exercised only through this public effect; the plugin's internal handling is outside this file.

<a id="u-ac3762a0d32f"></a>
### `test_log_file_cli_fallback_options`

`def test_log_file_cli_fallback_options(pytester: Pytester) -> None:` · [testing/logging/test_reporting.py:L1492-L1548][f1]

Verifies that --log-format/--log-date-format CLI values apply to the log file even when only --log-level is set for filtering.

Two runs with --log-level=ERROR, --log-file, and different format/date-format combinations each produce a file whose first line must regex-match the timestamp and message exactly ('HH:MM error text...' then 'HH:MM:SS : error text...'), with info and warning records absent in both, proving the level filter and CLI-provided formats both take effect.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- re.match anchors at file start, so a preceding header would break the match; the file is assumed fresh per run.

<a id="u-1a27dbf98647"></a>
### `test_log_level_not_changed_by_default`

`def test_log_level_not_changed_by_default(pytester: Pytester) -> None:` · [testing/logging/test_reporting.py:L764-L773][f1]

A passing in-line test asserts logging.getLogger().level == logging.WARNING when no logging options are given, verifying pytest leaves the root logger's level at the library default.

The outer test only checks '1 passed in'.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-95cb2c1d02a0"></a>
### `test_root_logger_affected`

`def test_root_logger_affected(pytester: Pytester) -> None:` · [testing/logging/test_reporting.py:L58-L91][f1]

Sets the root logger's effective level via --log-level=ERROR and asserts both the captured-stdout report and the --log-file output contain only error-level records.

The generated test logs info, warning, and error on the root logger and fails. The test asserts info/warning text is absent from both stdout and the log file while the error text is present, proving the level applies to the root logger rather than only named loggers.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-8221c5a7280f"></a>
### `test_reporting.py module code (L1–L16)`

`module_region` · [testing/logging/test_reporting.py:L1-L16][f1]

Imports and module setup for the logging-reporting test suite.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/logging/test_reporting.py
