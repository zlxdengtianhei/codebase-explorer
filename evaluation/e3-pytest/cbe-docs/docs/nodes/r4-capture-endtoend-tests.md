# Capture end-to-end tests

**Capability.** Behavioral capture verification: the capsys/capfd/capsysbinary/capfdbinary/capteesys fixture family with mutual exclusion, per-test capturing of setup/call/teardown, logging-module interaction via runpytest_subprocess, non-ASCII and collection-time output, and remaining module-level scenarios.

Use this subtree for user-visible capture behavior; the logging-interaction tests deliberately run in subprocesses to exercise atexit/teardown paths.

**Depends on.**

- [Capture primitive tests](r4-capture-mechanism-tests.md) · model-inferred · 0 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-only · 50 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 49 edge(s)

**Depended on by.**

- [Capture primitive tests](r4-capture-mechanism-tests.md) · graph-confirmed · 6 edge(s)

Parent: [Capture tests](r4-test-capture-suite.md)

## Units (6)

<a id="u-c1c867a02c2b"></a>
### `testing-test-capture.py-testcapturefixture`

`class TestCaptureFixture:` · [testing/test_capture.py:L435-L436][f1]

Tests for the capsys/capfd/capsysbinary/capfdbinary/capteesys fixtures and their mutual exclusion and disabled() context manager.

Key behaviors asserted: capsys reads text from sys-level streams (test_std_functional); capfd reads os-level fd 1/2 writes including undecodable bytes (test_stdfd_functional, test_capfdbinary) and preserves \n, \r\n, \r line endings (test_cafd_preserves_newlines, in-process); capsysbinary returns bytes including un-decodable sequences plus later text-mode prints, with captured output still shown in the -rA report (test_capsysbinary); capteesys passes output through to the real terminal while still readable, with -rN showing each stream once and -rA duplicating on stdout under tee-sys but only stdout under --capture=sys (test_capteesys); requesting capsys+capfd (including via request.getfixturevalue) errors with 'cannot use ... at the same time' at setup, producing errors instead of test results (test_capsyscapfd, test_capturing_getfixturevalue, test_capsyscapfdbinary). Robustness cases: failed fixture setup still reports as an error (test_partial_setup_failure); KeyboardInterrupt during a test still yields ret 2 with capture disabled (test_keyboardinterrupt_disables_capturing); logging in a capsys test leaves no 'closed' errors in a subprocess run (test_capture_and_logging); captured output appears in failure reports for sys and fd methods (test_capture_is_represented_on_failure_issue128). disabled() semantics: prints inside the context reach the terminal even under capture or -s, readouterr still returns only pre/post prints, nested disabled() blocks do not re-enable at the inner exit (test_disabled_capture_fixture twice-parametrized over fixture and no_capture; test_disabled_capture_fixture_twice), and capsys/capfd are usable inside other fixtures' setup and teardown with buffers readable there (test_fixture_use_by_other_fixtures, test_fixture_use_by_other_fixtures_teardown via inline_run).

**Uncertainties.**

- Fixture implementations (CaptureFixture, disabled(), readouterr) are in src/_pytest/capture.py and not covered here; exact error-raising mechanism is inferred from the asserted messages.

<a id="u-e52fbae23cca"></a>
### `testing-test-capture.py-testpertestcapturing`

`class TestPerTestCapturing:` · [testing/test_capture.py:L154-L155][f1]

Tests that per-test capture scopes setup, call, and teardown output separately.

Each test writes a target module via pytester.makepyfile, runs pytest, and matches report sections: test_capture_and_fixtures expects setup_module/setup_function and in-test prints to appear for each failing test; test_no_carry_over asserts output of a passing test does not leak into a later failing test's report while the failing test's output does; test_teardown_capturing expects setup/call/teardown prints in the failure report when teardown_function fails; test_teardown_capturing_final expects a failing teardown_module to surface as '*1 error*' with captured stdout; test_capturing_outerr asserts separate '-- Captured stdout call' and '-- Captured stderr call' sections for a passing and a raising test. test_capture_scope_cache is marked xfail 'unimplemented feature' and expects module- and function-scoped setup prints to be attributed to their phases; since it is xfail, the assertions are not treated as current behavior.

**Uncertainties.**

- The exact phase attribution of captured output during teardown failures depends on reporting code outside this file.

<a id="u-7b8d9bcc43f3"></a>
### `testing-test-capture.py-testlogginginteraction`

`class TestLoggingInteraction:` · [testing/test_capture.py:L297-L298][f1]

Tests of interaction between pytest capture and the logging module, all using runpytest_subprocess so a real interpreter exercises atexit/teardown paths.

test_logging_stream_ownership checks that a logging handler on a closed CaptureIO does not emit 'atexit' errors on stderr. test_logging_and_immediate_setupteardown and test_logging_and_crossscope_fixtures log warnings in setup/test/teardown (function- and module-scoped respectively) across --capture=sys and --capture=fd, expecting all three warnings in the report — teardown's 'hello3' first because errors show first — and no 'closed' text on stderr. test_conftestlogging_is_shown and test_conftestlogging_and_test_logging verify conftest basicConfig logging still reaches stderr/stdout with -p no:capturelog, with NO_TESTS_COLLECTED in the former and no 'operation on closed file' in either. test_logging_after_cap_stopped combines a teardown-logging fixture with --log-cli-level info and a KeyboardInterrupt in the test, expecting both warnings in stdout and specifically no "'NoneType' object has no attribute 'resume_capturing'" on stderr.

uses: [testing-test-capture.py-testcaptureio](r4-capture-mechanism-tests.md#u-9f71f83bf35b)

**Uncertainties.**

- Ordering of log records between teardown errors and earlier phases is asserted only via fnmatch patterns, not strict ordering.

<a id="u-76fa9018b7f8"></a>
### `testing-test-capture.py-unicode-collect-tests`

`def test_capturing_unicode(pytester: Pytester, method: str) -> None:` · [testing/test_capture.py:L105-L118][f1]

Pytester-driven tests checking that non-ASCII and collection-time output is captured.

test_capturing_unicode and test_capturing_bytes_in_utf8_encoding each write a small test file printing a 'böy' literal (once as a unicode object, once as a \u00f6 escape in source), run pytest with --capture=fd and --capture=sys via parametrize, and expect '1 passed'. test_collect_capturing writes a module that prints to stdout and stderr at import time and then imports a nonexistent module; it asserts the resulting collection error report shows separate 'Captured stdout' and 'Captured stderr' sections containing the printed text.

<a id="u-04c19c0a3773"></a>
### `testing-test-capture.py-module-level-capture-tests`

`def test_capture_not_started_but_reset() -> None:` · [testing/test_capture.py:L1359-L1361][f1]

Remaining module-level tests exercising capture internals and end-to-end scenarios.

Lifecycle and plumbing: test_capture_not_started_but_reset shows stop_capturing on an unstarted StdCapture is safe; test_fdcapture_tmpfile_remains_the_same asserts cap.err.tmpfile is identical before start and after stop; test__get_multicapture maps 'no' to a MultiCapture and raises ValueError matching "unknown capturing method: 'unknown'" for bad methods. Fixture-level in-process checks: test_using_capsys_fixture_works_with_sys_stdout_encoding prints a bytes object encoded with sys.stdout.encoding and expects non-empty out; test_capsys_results_accessible_by_attribute reads .out/.err from readouterr; test_stderr_write_returns_len asserts captured sys.stderr.write returns 3; test_encodedfile_writelines wraps tmpfile in capture.EncodedFile, expects TypeError for bytes lines, None for str lines whose text lands in the file, and ValueError reading after the underlying file is closed. Interaction and resilience: test_capturing_and_logging_fundamentals (parametrized over SysCapture(2), SysCapture(2, tee=True), FDCapture(2)) runs a subprocess where logging before readouterr is captured, pop_outerr_to_orig flushes 'hello3' to the original stderr (then captured as 'WARNING:root:hello3'), 'hello2' goes to real stderr, and no 'atexit' appears; test_error_attribute_issue555 and test_dontreadfrominput_has_encoding (via inline_run) assert sys.stdout/stderr have errors=='replace' and a truthy encoding under capture. Windows-only test_windowsconsoleio_workaround_non_standard_streams defines a local DummyStream with only write and passes it (cast to TextIO) to _windowsconsoleio_workaround without error. Subprocess scenarios: test_crash_on_closing_tmpfile_py27 (with plugin autoload disabled) runs a threaded test flushing a closed stderr in a loop and expects ret 0, empty stderr, no OSError line; test_global_capture_with_live_logging and test_capture_with_live_logging use --log-cli-level=INFO and assert setup/call/teardown prints and log records still reach the teardown report's caplog/capstdout (via a conftest writing files) and that readouterr under a capture fixture contains only post-logging output; test_close_and_capture_again closes fd 1 in one test and expects capture to work in the next; test_capture_while... — rather, test_logging_while_collecting asserts a collection-time warning is NOT duplicated into the failing test's 'Captured log call' (issue #6240) and no 'Captured stderr call' section appears. test_libedit_workaround spawns an interactive pytest (spawn_pytest) whose conftest terminal_summary suspends global capture including stdin, reads input 'hi', resumes, and the test matches "value: 'hi'" in the child output, guarding against libedit/readline issues.

calls: [testing-test-capture.py-testhelpers](r4-capture-mechanism-tests.md#u-6df8405153cc), [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f)

**Uncertainties.**

- test_typeerror_encodedfile_write accepts either of two TypeError messages, so the exact text depends on the Python/impl combination actually run.
- The pop_outerr_to_orig semantics asserted in test_capturing_and_logging_fundamentals are defined in src/_pytest/capture.py, not here.

<a id="u-911abb1ef245"></a>
### `testing-test-capture.py-module-level-pytester-tests`

`def test_setup_failure_does_not_kill_capturing(pytester: Pytester) -> None:` · [testing/test_capture.py:L773-L786][f1]

Module-level pytester tests covering capture edge cases end to end.

test_setup_failure_does_not_kill_capturing installs a conftest whose pytest_runtest_setup raises ValueError(42) and expects the error plus '1 error' with --traceconfig, i.e. capturing survives setup failure. test_capture_conftest_runtest_setup asserts output printed in pytest_runtest_setup is not shown by default (no 'hello19'); test_capture_early_option_parsing asserts the same print IS shown with -vs, checking -v/-s are parsed early. test_capture_badoutput_issue412 writes raw bytes (including 0x81) to fd 1 before failing and expects the traceback and a Captured section under --capture=fd. test_capture_binary_output runs a module that subprocess-calls itself and writes b'\xc3' to fd 1, expecting both tests to pass with --assert=plain. test_error_during_readouterr monkeypatches FDCapture.snap in a plugin file to raise and asserts, under a subprocess run, the boom exception appears on stderr — establishing that readouterr errors suspend rather than silently swallow.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_capture.py
