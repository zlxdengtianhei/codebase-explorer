# TerminalReporter Unit Tests

**Capability.** Unit tests of TerminalReporter behavior over fake writers/configs: per-verbosity result lines, internal errors, rewrite/erase sequences, logstart hooks, keyboard interrupts, isatty, summary stat lines and colors, skip folding/counting, and reprcrash message lines.

Use it when changing TerminalReporter internals directly; these avoid full runs and assert on writer contents. The tr fixture builds a real reporter over a fake config.

**Depends on.**

- [Output Capture and Line Matching](r6-pytester-output-matching.md) · graph-confirmed · 2 edge(s)

Parent: [Terminal Reporting Suite](r6-test-terminal.md)

## Units (28)

<a id="u-37810e827263"></a>
### `TestTerminal`

`class TestTerminal:` · [testing/test_terminal.py:L85-L86][f1]

Hosts unit tests of TerminalReporter behavior: per-verbosity result lines, internal errors, line writing, logstart hooks, rewrite/erase, keyboard-interrupt handling, colored status markup, skip/xfail reasons at -v/-vv, and the isatty boolean-compatibility quirk.

<a id="u-5a2378f83392"></a>
### `TestTerminal.test_pass_skip_fail`

`def test_pass_skip_fail(self, pytester: Pytester, option) -> None:` · [testing/test_terminal.py:L86-L113][f1]

Runs one passing, one skipping, and one failing test at each verbosity from the option fixture.

Verbose output shows per-test PASS/SKIP/FAIL lines, default shows '.sF' per file, quiet shows just '.sF'; the failure traceback lines are asserted at every verbosity.

<a id="u-042363acbc51"></a>
### `TestTerminal.test_console_output_style_times_with_skipped_and_passed`

`def test_console_output_style_times_with_skipped_and_passed( self, pytester: Pytester…` · [testing/test_terminal.py:L115-L138][f1]

Runs a passing test and an importorskip-skipped module with console_output_style=times, asserting the '1 passed, 1 skipped' summary and no INTERNALERROR in combined stdout/stderr.

<a id="u-8fbc88fe31d6"></a>
### `TestTerminal.test_internalerror`

`def test_internalerror(self, pytester: Pytester, linecomp) -> None:` · [testing/test_terminal.py:L140-L146][f1]

Constructs a TerminalReporter over a line-comparison StringIO, raises and catches a ValueError, feeds its repr to rep.pytest_internalerror, and asserts 'INTERNALERROR> *ValueError*hello*' was written.

<a id="u-9cf927078a22"></a>
### `TestTerminal.test_writeline`

`def test_writeline(self, pytester: Pytester, linecomp) -> None:` · [testing/test_terminal.py:L148-L156][f1]

Uses TerminalReporter.write_fspath_result then write_line against a StringIO; asserts an empty first line, the second line ending with the module name plus ' .', and the third line exactly 'hello world'.

<a id="u-284c80d78c57"></a>
### `TestTerminal.test_show_runtest_logstart`

`def test_show_runtest_logstart(self, pytester: Pytester, linecomp) -> None:` · [testing/test_terminal.py:L158-L166][f1]

Registers a TerminalReporter on the config plugin manager and fires pytest_runtest_logstart directly with the item's reportinfo location, asserting the file name appears in the captured output.

<a id="u-a29d325703bf"></a>
### `TestTerminal.test_runtest_location_shown_before_test_starts`

`def test_runtest_location_shown_before_test_starts( self, pytester: Pytester ) -> None:` · [testing/test_terminal.py:L168-L181][f1]

Spawns pytest in a pty running a test that sleeps 20 seconds and expects the test's location line to appear before completion, proving the location is printed at test start rather than at its end; then EOFs and kills the child.

<a id="u-f70ab60def6d"></a>
### `TestTerminal.test_report_collect_after_half_a_second`

`def test_report_collect_after_half_a_second( self, pytester: Pytester, monkeypatch: M…` · [testing/test_terminal.py:L183-L209][f1]

Sets REPORT_COLLECTING_RESOLUTION to 0 inside the test module so the 'collecting' progress line updates immediately, forces colored output via PY_COLORS=1, and expects the pty sequence 'collecting ...', 'collecting 1 item', 'collecting 2 items', then a green bold '2 passed' summary.

<a id="u-b70472a0432a"></a>
### `TestTerminal.test_keyboard_interrupt`

`def test_keyboard_interrupt(self, pytester: Pytester, fulltrace) -> None:` · [testing/test_terminal.py:L283-L313][f1]

Parametrized over '' and '--fulltrace' with no_reraise_ctrlc=True; a KeyboardInterrupt in the third test is reported with the traceback pointing at the raise line.

With fulltrace the raise statement itself is shown; otherwise the hint '(to show a full traceback on KeyboardInterrupt use --full-trace)' is expected.

<a id="u-5823e737acd0"></a>
### `TestTerminal.test_keyboard_in_sessionstart`

`def test_keyboard_in_sessionstart(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L315-L331][f1]

A conftest raising KeyboardInterrupt in pytest_sessionstart, run with no_reraise_ctrlc=True, yields exit code 2 and a KeyboardInterrupt line, verifying interruption is handled before any test runs.

<a id="u-43a53fbe6b99"></a>
### `TestTerminal.test_itemreport_subclasses_show_subclassed_file`

`def test_itemreport_subclasses_show_subclassed_file( self, pytester: Pytester ) -> None:` · [testing/test_terminal.py:L211-L262][f1]

Defines a BaseTests class in tests/test_p1 and subclasses in test_p2/test_p3.

Verbose reports annotate '<- test_p1.py' as the defining file, and setting BaseTests.fail=True from test_p3 makes that run fail with the traceback pointing at tests/test_p1.py:5; non-verbose runs attribute results to the invoking file only.

<a id="u-f6712b34f1a3"></a>
### `TestTerminal.test_itemreport_directclasses_not_shown_as_subclasses`

`def test_itemreport_directclasses_not_shown_as_subclasses( self, pytester: Pytester )…` · [testing/test_terminal.py:L264-L281][f1]

Runs -vv on a class defined in its own package module and asserts PASS output without the '<- ' subclass-origin annotation, confirming the annotation is reserved for tests whose class is inherited from another file.

<a id="u-e18f3b8ca8a4"></a>
### `TestTerminal.test_rewrite`

`def test_rewrite(self, pytester: Pytester, monkeypatch) -> None:` · [testing/test_terminal.py:L344-L352][f1]

Forces isatty on a StringIO, sets terminal width to 10, writes 'hello', then calls rewrite('hey', erase=True); expects 'hello' + carriage return + 'hey' padded with six spaces, documenting the erase-and-rewrite byte sequence on TTYs.

<a id="u-a7d781bc8e6f"></a>
### `TestTerminal.test_report_teststatus_explicit_markup`

`def test_report_teststatus_explicit_markup( self, monkeypatch: MonkeyPatch, pytester:…` · [testing/test_terminal.py:L354-L378][f1]

With PY_COLORS=1 a conftest hook pytest_report_teststatus returns an arbitrary category ('foo' or a known one) with markup ('FOO', red).

The -v output must render FOO in red regardless of category, proving TerminalReporter honors hook-supplied markup explicitly.

<a id="u-1a610e4cbf34"></a>
### `TestTerminal.test_verbose_skip_reason`

`def test_verbose_skip_reason(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L380-L468][f1]

With twelve skip/xfail variants, -v output shows the status word plus reason in parentheses; missing reasons render as empty parentheses for unconditional marks, while the two long reasons are truncated with '...'.

Under -vv the long reasons wrap across lines in full instead of truncating. The emoji-containing reason (test_10) is preserved.

<a id="u-fca90346e32c"></a>
### `TestTerminal.test_isatty`

`def test_isatty(self, pytester: Pytester, monkeypatch, isatty: bool) -> None:` · [testing/test_terminal.py:L470-L478][f1]

Parametrized over isatty True/False; constructs TerminalReporter over a StringIO whose isatty is patched and asserts tr.isatty() equals it.

Also asserts bool(tr.isatty) equals it, documenting that the method remains truthy-compatible because it was once implemented as a plain boolean attribute.

<a id="u-313bd8c033ac"></a>
### `TestTerminal.test_collect_single_item`

`def test_collect_single_item(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L333-L342][f1]

Asserts singular phrasing 'collected 1 item' for a single test file.

<a id="u-0750b8fdf66f"></a>
### `tr`

`def tr() -> TerminalReporter:` · [testing/test_terminal.py:L1865-L1868][f1]

Session-scoped fixture building a real TerminalReporter over a prepared empty config, shared by build_summary_stats_line tests.

<a id="u-dd87de445838"></a>
### `test_getreportopt`

`def test_getreportopt() -> None:` · [testing/test_terminal.py:L1400-L1403][f1]

Tests getreportopt against a FakeConfig by asserting the effective report-chars string for each reportchars/disable_warnings combination.

<a id="u-1acd474b63ed"></a>
### `testing/test_terminal.py:test_getreportopt`

`def test_getreportopt() -> None:` · [testing/test_terminal.py:L1408-L1456][f1]

Exercises getreportopt with a FakeConfig providing reportchars and disable_warnings.

Expected transformations: default 'fE' becomes 'wfE'; 'w' is deduplicated when already present; 'a' expands to 'wsxXEf'; 'N' resets chars to empty before any additions and swallows a trailing 'w' unless other chars follow it; 'A' expands to 'PpsxXEf'; 'AN' yields empty; with disable_warnings, 'w' is never added or is removed.

**Uncertainties.**

- The exact 'N'/'A' reset semantics are inferred from the expected strings, not from getreportopt's implementation.

<a id="u-0445b1fdd638"></a>
### `test_summary_stats`

`def test_summary_stats( tr: TerminalReporter, exp_line: list[tuple[str, dict[str, boo…` · [testing/test_terminal.py:L1871-L2010][f1]

Parametrized over stats dicts, asserting the exact summary line (word plus markup dict per category) and main color produced by build_summary_stats_line: failed/error force red, unknown/warnings-only/deselected/xfail/skipped/no-tests force yellow unless a passing count coexists (then green), xpassed keeps yellow, and empty-string keys are ignored in counting.

<a id="u-20b9f1c8bd0e"></a>
### `testing/test_terminal.py:test_summary_stats`

`def test_summary_stats( tr: TerminalReporter, exp_line: list[tuple[str, dict[str, boo…` · [testing/test_terminal.py:L2011-L2024][f1]

Body replaces tr.stats with the parametrized dict, installs a fake session with testscollected=0 so tr._is_last_item is truthy, resets the cached _main_color to None, then asserts build_summary_stats_line's (line, color) equals expectations.

<a id="u-d58dd398220b"></a>
### `test_skip_counting_towards_summary`

`def test_skip_counting_towards_summary(tr):` · [testing/test_terminal.py:L2027-L2028][f1]

Checks that reports with count_towards_summary True are counted in the summary line and those with it False are excluded (2 failed vs 1 failed), with _main_color reset between calls.

<a id="u-d17d8701ad4b"></a>
### `testing/test_terminal.py:test_skip_counting_towards_summary`

`def test_skip_counting_towards_summary(tr):` · [testing/test_terminal.py:L2029-L2042][f1]

Defines DummyReport(BaseReport) with count_towards_summary=True, stores two instances under stats['failed'], and asserts the summary counts reflect the flag toggling on r1.

<a id="u-0bd2b43616a1"></a>
### `test_skip_reasons_folding`

`def test_skip_reasons_folding() -> None:` · [testing/test_terminal.py:L2504-L2510][f1]

Checks _folded_skips collapses three same-location skip reports (execute/execute/collect) into one (count, fspath, lineno, reason) tuple.

<a id="u-951e02a1b1dd"></a>
### `testing/test_terminal.py:test_skip_reasons_folding`

`def test_skip_reasons_folding() -> None:` · [testing/test_terminal.py:L2511-L2535][f1]

Builds three duck-typed objects cast to CollectReport sharing longrepr ('xyz', 3, 'justso') and skipped=True (one with when='collect'), calls _folded_skips(Path.cwd(), ...), and asserts a single folded entry with num 3 and the original location fields.

<a id="u-ea4841264aa3"></a>
### `test_line_with_reprcrash`

`def test_line_with_reprcrash(monkeypatch: MonkeyPatch) -> None:` · [testing/test_terminal.py:L2538-L2543][f1]

Nested helper for test_line_with_reprcrash; its inner check function drives _get_line_with_reprcrash_message against fakes and is explained in the test unit.

<a id="u-dd86fd2803c8"></a>
### `testing/test_terminal.py:test_line_with_reprcrash`

`def test_line_with_reprcrash(monkeypatch: MonkeyPatch) -> None:` · [testing/test_terminal.py:L2544-L2548][f1]

Patches _get_node_id_with_markup to return a fixed nodeid and defines local fakes (Namespace, config, rep with _get_verbose_word_with_markup returning ('FAILED', {}) and a reprcrash.message slot, DummyTerminalWriter whose markup is identity).

check() sets the crash message, calls _get_line_with_reprcrash_message, asserts the exact expected line, and — unless the message was omitted — asserts display width and wcswidth fit the given terminal width. Cases cover missing message, fitting/truncating messages with '...' at boundary widths, first-line-only extraction from multiline messages, and CJK-wide-character unicode truncation, including a unicode nodeid noted as constructed rather than known-supported.

**Uncertainties.**

- Whether unicode nodeids with '🉐' are supported in production is uncertain; the source itself marks this case 'NOTE: constructed, not sure if this is supported'.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_terminal.py
