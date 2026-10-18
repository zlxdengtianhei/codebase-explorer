# Summary Sections and Reporting

**Capability.** End-to-end checks of report sections: fixture setup/teardown errors, traceback styles and crash lines, --show-capture filtering, header/trailer suppression, --no-summary, locals, verbosity and folding of skip summaries, plus xfail/xpass sections and --xfail-tb.

Use it for anything printed in or suppressed from the summary areas of a real run. TestGenericReporting methods are written to be reusable for distributed runs.

**Depends on.**

- [Test Run Invocation](r6-pytester-run.md) · graph-confirmed · 29 edge(s)

Parent: [Terminal Reporting Suite](r6-test-terminal.md)

## Units (23)

<a id="u-158a9c921846"></a>
### `TestFixtureReporting`

`class TestFixtureReporting:` · [testing/test_terminal.py:L652-L653][f1]

Verifies error reporting for failing setup/teardown functions: header text, captured output sections, and pass/fail/error count combinations in the summary.

<a id="u-7ab8317ab657"></a>
### `TestFixtureReporting.test_setup_fixture_error`

`def test_setup_fixture_error(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L653-L673][f1]

A setup_function assert produces 'ERROR at setup of test_nada', the captured 'setup func' output, the assert traceback, and '1 error'; result.ret is nonzero.

<a id="u-8fd9a75405d3"></a>
### `TestFixtureReporting.test_teardown_fixture_error`

`def test_teardown_fixture_error(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L675-L695][f1]

A failing teardown_function after a passing test reports 'ERROR at teardown', captured teardown stdout, and a '1 passed*1 error' summary.

<a id="u-b5dcc76f61b3"></a>
### `TestFixtureReporting.test_teardown_fixture_error_and_test_failure`

`def test_teardown_fixture_error_and_test_failure(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L697-L721][f1]

When the test body asserts 0 and teardown also fails, output contains both 'ERROR at teardown of test_fail' and the test's own failure traceback, summarized as '1 failed*1 error'.

<a id="u-a4edb039a652"></a>
### `TestFixtureReporting.test_setup_teardown_output_and_test_failure`

`def test_setup_teardown_output_and_test_failure(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L723-L749][f1]

Issue #442: with a failing test plus printing setup and teardown, output shows separate 'Captured stdout setup' and 'Captured stdout teardown' sections alongside the failure traceback and '1 failed'.

<a id="u-ed2d21abdc96"></a>
### `TestGenericReporting`

`class TestGenericReporting:` · [testing/test_terminal.py:L1508-L1512][f1]

Verbosity-parametrized reporting tests intended to be reusable for distributed runs; covers collection errors, maxfailures stopping, tbstyle variants, crash-line summaries, report headers from hooks, and --show-capture filtering.

<a id="u-2cf08c077afb"></a>
### `TestGenericReporting.test_collect_fail`

`def test_collect_fail(self, pytester: Pytester, option) -> None:` · [testing/test_terminal.py:L1512-L1517][f1]

Importing a nonexistent module reports 'ImportError while importing', 'No module named *xyz', and '1 error' at any verbosity.

<a id="u-4d828a7d1587"></a>
### `TestGenericReporting.test_maxfailures`

`def test_maxfailures(self, pytester: Pytester, option) -> None:` · [testing/test_terminal.py:L1519-L1538][f1]

--maxfail=2 with three failing tests shows both failure tracebacks, the '!

stopping after 2 failures !' banner, and '2 failed'.

<a id="u-f4ad3832b41a"></a>
### `TestGenericReporting.test_maxfailures_with_interrupted`

`def test_maxfailures_with_interrupted(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L1540-L1557][f1]

A test setting request.session.shouldstop with --maxfail=1 -ra shows the short summary, the stopping banner, an additional '!

session_interrupted !' banner, and '1 failed'.

<a id="u-d3db0552a106"></a>
### `TestGenericReporting.test_tb_option`

`def test_tb_option(self, pytester: Pytester, option) -> None:` · [testing/test_terminal.py:L1559-L1584][f1]

For --tb=long the printed source line (print(6*7)) appears; for short/no it does not.

For any tbopt except 'no', '--calling--' and 'IndexError' appear; with 'no' there is no FAILURES section at all.

<a id="u-cc40ff250694"></a>
### `TestGenericReporting.test_tb_crashline`

`def test_tb_crashline(self, pytester: Pytester, option) -> None:` · [testing/test_terminal.py:L1586-L1605][f1]

With --tb=line, one 'file:line: ExceptionType: message' line per failure is expected (IndexError at :3, AssertionError 'hello' at :8) and no source lines like 'def test_func2' appear.

<a id="u-bd1840e55952"></a>
### `TestGenericReporting.test_tb_crashline_pytrace_false`

`def test_tb_crashline_pytrace_false(self, pytester: Pytester, option) -> None:` · [testing/test_terminal.py:L1607-L1618][f1]

pytest.fail(..., pytrace=False) under --tb=line still yields a single crash line 'file:3: Failed: test_func1'.

<a id="u-9fa5754ebeec"></a>
### `TestGenericReporting.test_pytest_report_header`

`def test_pytest_report_header(self, pytester: Pytester, option) -> None:` · [testing/test_terminal.py:L1620-L1637][f1]

A conftest hook returning a string using a value set in sessionstart ('hello: 42') and a hook in a subdirectory conftest returning a list ['line1', start_path] are both rendered, with the path being the pytester root path.

<a id="u-772c9f03d417"></a>
### `TestGenericReporting.test_show_capture`

`def test_show_capture(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L1639-L1688][f1]

A test writing to stdout, stderr, and a logging warning: default and --show-capture=all show all three; 'stdout' shows only stdout, 'stderr' only stderr, 'log' only the warning, and 'no' none.

<a id="u-e6b623bfdde9"></a>
### `TestGenericReporting.test_show_capture_with_teardown_logs`

`def test_show_capture_with_teardown_logs(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L1690-L1728][f1]

Same filtering applied to output produced during fixture teardown after yield: --show-capture selects exactly the stdout, stderr, or log content, or none with 'no'.

<a id="u-c32323685467"></a>
### `test_summary_xfail_reason`

`def test_summary_xfail_reason(pytester: Pytester) -> None:` · [testing/test_terminal.py:L3125-L3144][f1]

-rx summary lists XFAIL lines; an unmarked-reason xfail has no suffix, an xfail with reason='foo' shows ' - foo'; each line appears exactly once.

<a id="u-2d6c77910f92"></a>
### `test_summary_xpass_reason`

`def test_summary_xpass_reason(pytester: Pytester) -> None:` · [testing/test_terminal.py:L3222-L3241][f1]

-rX lists XPASS summary lines; without reason no suffix, with reason='foo' shows ' - foo', each once.

<a id="u-b34d28a7def5"></a>
### `xfail_testfile`

`def xfail_testfile(pytester: Pytester) -> Path:` · [testing/test_terminal.py:L3147-L3162][f1]

Fixture creating a module with a plain failing test and an xfail-marked failing test, shared by --xfail-tb tests.

<a id="u-db011523fef9"></a>
### `test_xfail_tb_default`

`def test_xfail_tb_default(xfail_testfile, pytester: Pytester) -> None:` · [testing/test_terminal.py:L3165-L3181][f1]

Without --xfail-tb, the plain failure shows a FAILURES traceback but no XFAILURES section appears for the xfailed test.

<a id="u-d8a8a1621b69"></a>
### `test_xfail_tb_true`

`def test_xfail_tb_true(xfail_testfile, pytester: Pytester) -> None:` · [testing/test_terminal.py:L3184-L3204][f1]

With --xfail-tb, an additional XFAILURES section shows the xfailed test's traceback (assert 3 == 4), followed by the short summary.

<a id="u-603f2e9b5e63"></a>
### `test_xfail_tb_line`

`def test_xfail_tb_line(xfail_testfile, pytester: Pytester) -> None:` · [testing/test_terminal.py:L3207-L3219][f1]

--xfail-tb --tb=line yields one crash line per section: 'file:5: assert 1 == 2' under FAILURES and 'file:10: assert 3 == 4' under XFAILURES.

<a id="u-0e37ddf30a2d"></a>
### `test_xpass_output`

`def test_xpass_output(pytester: Pytester) -> None:` · [testing/test_terminal.py:L3244-L3264][f1]

With -rX, an xpassing test gets an '= XPASSES =' section including 'Captured stdout call' and an XPASS short-summary line with '1 xpassed' trailer.

<a id="u-a6cfdabb249d"></a>
### `test_tbstyle_short`

`def test_tbstyle_short(pytester: Pytester) -> None:` · [testing/test_terminal.py:L1478-L1499][f1]

With --tb=short, locals ('arg = 42', 'x = 0') are absent and the traceback shows file:line plus the assert line; with default tbstyle, locals and the assert line appear.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_terminal.py
