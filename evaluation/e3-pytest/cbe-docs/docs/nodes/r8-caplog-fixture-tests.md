# caplog Fixture Tests

**Capability.** testing/logging/test_fixture.py verifies the caplog fixture: basic capture and accessors (text/messages), per-stage record tracking across setup/call/teardown, set_level undo semantics, at_level filtering via handler-level filters, and interactions with global logging.disable and ini log_level; an autouse fixture resets logging.disable state.

Use this to check expected caplog behavior under level changes, disabled global logging, and multi-stage tests. All scenarios run via plain tests or pytester inline runs.

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Units (10)

<a id="u-1e5e309cd863"></a>
### `test_fixture-py-config-level-tests`

`def test_ini_controls_global_log_level(pytester: Pytester) -> None:` · [testing/logging/test_fixture.py:L348-L372][f1]

Pytester-based tests of how the ini log_level interacts with caplog overrides and failure reporting.

test_ini_controls_global_log_level writes a test asserting the logging plugin's log_level is ERROR per ini, that WARNING is filtered and ERROR captured, and checks result.ret == 0. test_can_override_global_log_level sets ini log_level=WARNING; the embedded test asserts the plugin level is WARNING, then uses caplog.set_level(INFO) and caplog.at_level(DEBUG/CRITICAL) blocks, asserting every message claimed to be filtered is absent from caplog.text while the final INFO is shown — proving caplog overrides the ini level locally and restores it. test_captures_despite_exception raises inside an at_level(DEBUG) block after logging ERROR and DEBUG; output shows the ERROR line present, the DEBUG line absent, and ret == 1, so captured logs survive the exception and at_level filtering applied up to it. test_log_report_captures_according_to_config_option_upon_failure runs with --log-level=INFO on a failing test that captures DEBUG inside at_level(DEBUG); it asserts no 'caplog failed to capture DEBUG' exception, no DEBUG line in the report, but print/INFO/WARNING lines appear, and ret == 1 — caplog captures below the configured level during the test while the report honors the config level.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-efac0956e393"></a>
### `test_fixture-py-simple-caplog-tests`

`def test_fixture_help(pytester: Pytester) -> None:` · [testing/logging/test_fixture.py:L30-L32][f1]

Small tests exercising basic caplog capture and accessors.

test_fixture_help runs pytester.runpytest("--fixtures") and matches '*caplog*' in stdout. test_change_level uses caplog.set_level to raise the handler level to INFO globally and to CRITICAL for the sublogger, then asserts DEBUG and WARNING messages are absent from caplog.text while INFO and CRITICAL appear. test_with_statement_at_level does the same scoping with nested caplog.at_level context managers instead of set_level. test_log_access asserts records[0] keeps the raw msg ('boo %s') and levelname while caplog.text contains the interpolated 'boo arg'. test_record_tuples checks caplog.record_tuples equals [(__name__, logging.INFO, 'boo arg')]. test_unicode confirms non-ASCII ('bū') is preserved in record msg and text. test_clear asserts records and text are non-empty after a log call and empty after caplog.clear(). test_captures_for_all_stages is documented with the stage-records group but its assertions are also plain capture checks.

<a id="u-70a79ee5cc5d"></a>
### `test_fixture-py-stage-records-tests`

`def logging_during_setup_and_teardown( caplog: pytest.LogCaptureFixture, ) -> Iterato…` · [testing/logging/test_fixture.py:L296-L304][f1]

Verifies per-stage record tracking of caplog across setup/call/teardown.

The logging_during_setup_and_teardown fixture enables INFO, logs 'a_setup_log' during setup, and after yield logs 'a_teardown_log' and asserts caplog.get_records("teardown") equals ['a_teardown_log']. private_assert_caplog_records_is_setup_call reaches into private API (caplog._item.stash[caplog_records_key]) and asserts the stash holds exactly the keys {'setup','call'}. test_captures_for_all_stages asserts records are empty before logging, that a call-stage log appears in get_records("call") and the setup log in get_records("setup"), then checks the stash keys. test_clear_for_call_stage logs 'a_call_log', verifies setup records survive caplog.clear() while call records become [], then that a new log re-fills only the call stage, re-checking the stash each time. Together these pin down that clear() empties the current-stage records but leaves other stages and the stash untouched.

calls: [test_fixture-py-stage-records-tests](r8-caplog-fixture-tests.md#u-70a79ee5cc5d)

**Uncertainties.**

- Exact semantics of caplog_records_key stash updates live in _pytest.logging, not in this file.

<a id="u-53e4485e963f"></a>
### `test_fixture-py-undo-tests`

`def test_change_level_undo(pytester: Pytester) -> None:` · [testing/logging/test_fixture.py:L67-L90][f1]

Pytester-based end-to-end tests that set_level's changes are undone after each test.

test_change_level_undo writes test1 setting caplog level INFO then failing, and test2 logging the same message; it asserts 'log from test1' appears in stdout while 'log from test2' does not and both tests failed, proving the INFO level did not leak. test_change_disabled_level_undo targets _force_enable_logging undo: test1 disables logging at CRITICAL then set_level(INFO) and logs; test2 logs at WARNING, which would only be visible if logging.disable were not restored to CRITICAL; absence of the test2 message proves restoration. test_change_level_undoes_handler_level (issue #7569) asserts caplog.handler.level is 0 in fresh tests, becomes the last set value (41, then 43) within a test, and returns to 0 in subsequent tests; all three inner tests pass. Messages in the embedded sources use string concatenation so fnmatch_lines cannot accidentally match the test code itself.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-6b98300da8c8"></a>
### `test_fixture-py-with-statement-filtering`

`def test_with_statement_filtering(caplog: pytest.LogCaptureFixture) -> None:` · [testing/logging/test_fixture.py:L193-L194][f1]

Verifies caplog.filtering temporarily installs a handler-level logging.Filter.

The test defines TestFilter whose filter(record) mutates record.msg to 'filtered handler call' and always returns True, so records pass but are rewritten. Inside at_level(INFO), the first logger.info call runs within caplog.filtering(TestFilter()) and its record tuple becomes ('test_fixture', 20, 'filtered handler call'); the second call outside that context yields the unmodified ('test_fixture', 20, 'handler call'). This shows filtering applies only to records emitted while the context manager is active and only mutates records it sees, leaving later records untouched.

uses: [test_fixture-py-with-statement-filtering](r8-caplog-fixture-tests.md#u-6b98300da8c8)

<a id="u-76ba5081e80d"></a>
### `cleanup_disabled_logging`

`def cleanup_disabled_logging() -> Iterator[None]:` · [testing/logging/test_fixture.py:L17-L27][f1]

An autouse fixture that resets the process-global logging.disable state after each test in this module.

It yields to run the test, then unconditionally calls logging.disable(logging.NOTSET) in teardown; because this runs after yield, the reset happens even when the test fails or raises, preventing a test that disabled logging from leaking that global state into subsequent tests.

<a id="u-b6dfe44adf6d"></a>
### `test_change_level_logging_disabled`

`def test_change_level_logging_disabled(caplog: pytest.LogCaptureFixture) -> None:` · [testing/logging/test_fixture.py:L50-L64][f1]

Verifies caplog.set_level still works when global logging is disabled via logging.disable(CRITICAL).

It first asserts logging.root.manager.disable equals CRITICAL, then calls caplog.set_level(WARNING) for the root logger and CRITICAL for the sublogger, implying set_level internally force-enables logging below the requested level. INFO from the root logger is then excluded while WARNING is captured; for the sublogger, WARNING is excluded and CRITICAL captured, showing per-logger level scoping still applies under the forced-enable.

**Uncertainties.**

- Whether set_level restores the original disable level is not observable in this file; it is covered by test_change_disabled_level_undo.

<a id="u-425b5cc4cda9"></a>
### `test_force_enable_logging_level_string`

`def test_force_enable_logging_level_string( caplog: pytest.LogCaptureFixture, level_s…` · [testing/logging/test_fixture.py:L209-L239][f1]

Parametrized test of the private caplog._force_enable_logging when given a level name string.

It disables all logging with logging.disable(CRITICAL), asserts a test logger is not enabled even for CRITICAL, then calls caplog._force_enable_logging(level_str, test_logger) and asserts test_logger.manager.disable equals the parametrized expected value: one standard level below the requested level (CRITICAL→ERROR, ERROR→WARNING, WARNING→INFO, INFO→DEBUG, DEBUG→NOTSET); 'NOTSET' and an invalid name 'NOTVALIDLEVEL' both leave disable at NOTSET. It deliberately checks manager.disable rather than isEnabledFor, since the latter also consults logger levels set by setLevel.

**Uncertainties.**

- The mapping from an invalid/NOTSET string to NOTSET is asserted, but the implementation of _force_enable_logging lives outside this file.

<a id="u-1bd4ed59593b"></a>
### `test_messages`

`def test_messages(caplog: pytest.LogCaptureFixture) -> None:` · [testing/logging/test_fixture.py:L250-L268][f1]

Verifies caplog.messages returns fully interpolated message strings while caplog.text includes formatted output.

Two INFO calls with %s placeholders produce caplog.messages entries 'boo arg' and 'bar arg1\nbaz arg2'; it asserts text has more newlines and splitlines than messages, showing text carries per-record log-line formatting beyond the bare messages. It then logs via logger.exception in an except block and asserts 'oops' appears both in text and in the last message, but 'Exception' (the traceback) appears only in caplog.text, not in caplog.messages — evidence that tracebacks are attached to the record and rendered only by the formatter/handler.

<a id="u-959e1b02888b"></a>
### `test_with_statement_at_level_logging_disabled`

`def test_with_statement_at_level_logging_disabled( caplog: pytest.LogCaptureFixture, …` · [testing/logging/test_fixture.py:L165-L190][f1]

Checks caplog.at_level under global logging.disable(CRITICAL).

Inside the outer at_level(WARNING) block it asserts logging.root.manager.disable becomes INFO — one level below the requested capture level — and captures WARNING, ERROR, and CRITICAL while excluding DEBUG and INFO. A nested at_level(CRITICAL, logger=sublogger.name) scope excludes the sublogger's WARNING but captures its CRITICAL. After the with blocks, the final assertion pins that logging.root.manager.disable is back to CRITICAL, i.e. at_level restored the prior global disable level.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/logging/test_fixture.py
