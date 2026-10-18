# Terminal End-to-End Reporting

**Capability.** End-to-end reporting checks over real runs: deselection counts, header content and --no-header, --no-summary, locals display, verbosity and quietness levels, summary aliases and folding, collectionfinish hook lines, and interrupt/count edge cases.

Use it to verify full-run output shape for common flag combinations. verbose_testfile and related fixtures set up mixed pass/fail/skip modules.

**Depends on.**

- [Test Run Invocation](r6-pytester-run.md) · graph-confirmed · 29 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 29 edge(s)

Parent: [Terminal Reporting Suite](r6-test-terminal.md)

## Units (27)

<a id="u-480b76805b19"></a>
### `TestTerminalFunctional`

`class TestTerminalFunctional:` · [testing/test_terminal.py:L752-L753][f1]

End-to-end checks of terminal reporting through real pytest runs: deselection counts, header content and suppression flags, --no-summary, locals display, verbosity levels, summary alias folding, and hook-extended collection lines.

<a id="u-54c0742543f6"></a>
### `TestTerminalFunctional.verbose_testfile`

`def verbose_testfile(self, pytester: Pytester) -> Path:` · [testing/test_terminal.py:L1069-L1082][f1]

Fixture creating a module with a failing, a passing, and a skipping test, shared by the verbose-reporting tests.

<a id="u-bf872694e294"></a>
### `TestTerminalFunctional.test_passes`

`def test_passes(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L874-L891][f1]

From the test file's directory, a two-test run shows 'test_passes.py ..' and '2 pass' with exit 0; directory is restored in a finally block.

<a id="u-92633194cf19"></a>
### `TestTerminalFunctional.test_header`

`def test_header(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L935-L962][f1]

Header content varies by configuration: without ini only 'rootdir:' appears; with a tox.ini, 'configfile: tox.ini' is added; with testpaths and no args, 'testpaths: tests, gui' is added; passing a directory on the command line suppresses the testpaths line.

<a id="u-f021fcb45228"></a>
### `TestTerminalFunctional.test_header_trailer_info`

`def test_header_trailer_info( self, monkeypatch: MonkeyPatch, pytester: Pytester, req…` · [testing/test_terminal.py:L893-L915][f1]

Deletes PYTEST_DISABLE_PLUGIN_AUTOLOAD and PYTEST_PLUGINS, then checks the header shows session-start banner, platform/Python/pytest/pluggy version line, progress line, and '1 passed' trailer; conditionally checks 'plugins:' only when distinfos are registered.

<a id="u-4fdcdffd8af1"></a>
### `TestTerminalFunctional.test_no_header_trailer_info`

`def test_no_header_trailer_info( self, monkeypatch: MonkeyPatch, pytester: Pytester, …` · [testing/test_terminal.py:L917-L933][f1]

With --no-header, neither the platform/version line nor the plugins line appears.

<a id="u-0f15ac39a289"></a>
### `TestTerminalFunctional.test_no_header`

`def test_no_header(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L985-L1003][f1]

With --no-header the rootdir/inifile/testpaths header line is absent, both when args are defaulted and when a directory is passed.

<a id="u-31b0e3f7d52e"></a>
### `TestTerminalFunctional.test_header_absolute_testpath`

`def test_header_absolute_testpath( self, pytester: Pytester, monkeypatch: MonkeyPatch…` · [testing/test_terminal.py:L964-L983][f1]

Regression #7814: with pyproject.toml testpaths given as absolute paths, the header shows rootdir, configfile, and the absolute testpaths value.

<a id="u-a4868a810bbd"></a>
### `TestTerminalFunctional.test_no_skip_summary_if_failure`

`def test_no_skip_summary_if_failure(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L858-L872][f1]

A run with a pass, a fail, and a skip produces no skip summary section; exit 1.

<a id="u-3c5eb69c551c"></a>
### `TestTerminalFunctional.test_no_summary`

`def test_no_summary(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L1005-L1013][f1]

--no-summary suppresses the '= FAILURES =' section even for a failing (typo'd name, NameError) test.

<a id="u-5882ad479352"></a>
### `TestTerminalFunctional.test_deselected`

`def test_deselected(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L753-L768][f1]

-k test_t on three tests reports 'collected 3 items / 1 deselected / 2 selected', two progress dots, and exit 0.

<a id="u-17e694dd9543"></a>
### `TestTerminalFunctional.test_deselected_with_hook_wrapper`

`def test_deselected_with_hook_wrapper(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L770-L799][f1]

A wrapper hookimpl for pytest_collection_modifyitems pops an item and reports it via pytest_deselected; the count line and '2 passed, 1 deselected' summary still render correctly, exit 0.

<a id="u-ab5f333747d3"></a>
### `TestTerminalFunctional.test_show_deselected_items_using_markexpr_before_test_execution`

`def test_show_deselected_items_using_markexpr_before_test_execution( self, pytester: …` · [testing/test_terminal.py:L801-L829][f1]

With -m 'not foo', deselection info appears in the collection line and final summary '2 passed, 1 deselected', and no separate '= 1 deselected =' summary section is emitted.

<a id="u-47731d2d35fa"></a>
### `TestTerminalFunctional.test_selected_count_with_error`

`def test_selected_count_with_error(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L831-L856][f1]

A module whose module body divides by zero during collection combines error into the count line ('collected 3 items / 1 error / 1 deselected / 2 selected') and interrupts with exit code ExitCode.INTERRUPTED.

<a id="u-e355eb3422e8"></a>
### `TestTerminalFunctional.test_showlocals`

`def test_showlocals(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L1015-L1031][f1]

With -l, failing-test locals appear as 'x = 3' and long string values truncated ('xxxxxx...').

<a id="u-ddca8a08b563"></a>
### `TestTerminalFunctional.test_showlocals_short`

`def test_showlocals_short(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L1049-L1067][f1]

With -l --tb=short, locals render aligned inside the short traceback ('x = 3', "y = 'xxxx'").

<a id="u-8e414e361404"></a>
### `TestTerminalFunctional.test_noshowlocals_addopts_override`

`def test_noshowlocals_addopts_override(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L1033-L1047][f1]

An ini addopts=--showlocals can be overridden on the command line by --no-showlocals, so no local-variable lines appear.

<a id="u-4aa194e987ac"></a>
### `TestTerminalFunctional.test_quiet_reporting`

`def test_quiet_reporting(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L1116-L1123][f1]

With -q the output omits the session banner, file name, and '===' separators but keeps 'passed'.

<a id="u-ae745eb5785f"></a>
### `TestTerminalFunctional.test_more_quiet_reporting`

`def test_more_quiet_reporting(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L1125-L1132][f1]

With -qq even 'passed' disappears from output.

<a id="u-93f08344e0fa"></a>
### `TestTerminalFunctional.test_report_collectionfinish_hook`

`def test_report_collectionfinish_hook(self, pytester: Pytester, params) -> None:` · [testing/test_terminal.py:L1134-L1153][f1]

A conftest pytest_report_collectionfinish returning a line is printed after 'collected 3 items' both in a normal run and with --collect-only.

<a id="u-03a0e93eacf0"></a>
### `TestTerminalFunctional.test_verbose_reporting`

`def test_verbose_reporting(self, verbose_testfile, pytester: Pytester) -> None:` · [testing/test_terminal.py:L1084-L1095][f1]

-v with -Walways::pytest.PytestWarning shows per-test node IDs with PASS/FAIL/SKIP words; exit 1 due to the failure.

<a id="u-3b2164ba9d26"></a>
### `TestTerminalFunctional.test_verbose_reporting_xdist`

`def test_verbose_reporting_xdist( self, verbose_testfile, monkeypatch: MonkeyPatch, p…` · [testing/test_terminal.py:L1097-L1114][f1]

Skips when xdist is not installed; otherwise -v -n 1 still prints FAIL lines carrying the node ID, exit 1.

<a id="u-f06a17ddd095"></a>
### `TestTerminalFunctional.test_summary_f_alias`

`def test_summary_f_alias(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L1155-L1166][f1]

-rfF produces exactly one FAILED summary line, proving 'f' and 'F' chars are aliases not duplicated in the summary.

<a id="u-e470ba68e6c7"></a>
### `TestTerminalFunctional.test_summary_s_alias`

`def test_summary_s_alias(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L1168-L1182][f1]

-rsS produces exactly one SKIPPED summary line for an unconditionally skipped test, proving 's'/'S' aliasing.

<a id="u-5e852c06a2eb"></a>
### `TestTerminalFunctional.test_summary_s_folded`

`def test_summary_s_folded(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L1184-L1199][f1]

Two parametrized skips with the same reason fold into one summary line 'SKIPPED [2] file:3: Some reason'.

<a id="u-587b9fc88bb7"></a>
### `TestTerminalFunctional.test_summary_s_unfolded`

`def test_summary_s_unfolded(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L1201-L1220][f1]

With --no-fold-skipped the two skips are listed individually with node IDs and '- Skipped: Some reason' messages.

<a id="u-bc997c7d412c"></a>
### `test_tbstyle_native_setup_error`

`def test_tbstyle_native_setup_error(pytester: Pytester) -> None:` · [testing/test_terminal.py:L1750-L1765][f1]

With --tb=native, a fixture-raised exception reports a Python-style traceback line naming the fixture function.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_terminal.py
