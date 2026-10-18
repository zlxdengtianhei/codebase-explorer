# Per-Test Progress Output

**Capability.** Rendering of individual test result lines and in-place progress updates: location prefixes, result letters/words, width-aware progress writes, and keyboard-interrupt reporting.

Use this to understand exactly what is printed as tests run, in both normal and verbose modes. TestShortLogReport defines the category/letter/word triple consumed from pytest_report_teststatus.

**Depends on.**

- [Terminal Options and Status Hook](r9-terminal-config.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Summary Sections](r9-terminal-summaries.md) · graph-confirmed · 4 edge(s)

Parent: [Terminal Reporting](r9-terminal-reporting.md)

## Units (14)

<a id="u-6c9c7f77cb50"></a>
### `TerminalReporter.pytest_runtest_logstart`

`def pytest_runtest_logstart( self, nodeid: str, location: tuple[str, int | None, str]…` · [src/_pytest/terminal.py:L591-L603][f1]

Hook called before a test runs, ensuring the location is printed first.

When showlongtestinfo, it builds the location line via _locationline and writes it through write_ensure_prefix with empty extra, then flushes. Otherwise, when showfspath, it emits an empty result for the nodeid via write_fspath_result (which prints the file path) and flushes.

calls: [TerminalReporter._locationline](r9-terminal-progress.md#u-f3922305a46b), [TerminalReporter.write_ensure_prefix](r9-terminal-progress.md#u-485445f66ec3), [TerminalReporter.write_fspath_result](r9-terminal-progress.md#u-1dcfa1204f5d)

<a id="u-1f75ba95ab24"></a>
### `TerminalReporter.pytest_runtest_logreport`

`def pytest_runtest_logreport(self, report: TestReport) -> None:` · [src/_pytest/terminal.py:L605-L679][f1]

Core per-report hook; sets _tests_ran, obtains the (category, letter, word) triple from the pytest_report_teststatus hook wrapped into TestShortLogReport, and files the report under the category.

If both letter and word are empty (typically passed setup/teardown) it returns after the stats update. When word is not a tuple it derives markup itself: green for passed without wasxfail, yellow for passed xfail/xskip, red for failed; otherwise word and markup come from the tuple. At test-cases verbosity <= 0 it writes only the letter, and with progress info enabled prints past-edge progress here rather than at logfinish — the source comments this avoids xdist interleaving overflow — except for the last item. Above that verbosity, it builds the location line; locally it writes prefix+word with markup, appends a trimmed skip reason for skipped or wasxfail reports (full reason at verbosity >= 2, width-trimmed otherwise, via _get_raw_skip_reason and _format_trimmed), and refreshes progress filling space; under xdist (report has a node attribute) it writes a [gateway-id] bracket, cyan progress message, word and location, setting currentfspath to -2. Flushes at the end.

uses: [TestShortLogReport](r9-terminal-progress.md#u-42395b912891); calls: [TerminalReporter._locationline](r9-terminal-progress.md#u-f3922305a46b), [_get_raw_skip_reason](r9-terminal-progress.md#u-08be377904c8), [_format_trimmed](r9-terminal-progress.md#u-70bf49560342)

**Uncertainties.**

- _tests_ran is assigned but never read in this file, so its effect on other components is unproven.

<a id="u-42395b912891"></a>
### `TestShortLogReport`

`class TestShortLogReport(NamedTuple):` · [src/_pytest/terminal.py:L114-L131][f1]

NamedTuple carrying the per-report display triple: the stats category (e.g. 'passed', '' for setup/teardown), the progress letter (e.g. '.', 's', 'R'), and the verbose word which may be a plain string or a (word, markup-mapping) tuple used for colored verbose output.

<a id="u-f3922305a46b"></a>
### `TerminalReporter._locationline`

`def _locationline( self, nodeid: str, fspath: str, lineno: int | None, domain: str ) …` · [src/_pytest/terminal.py:L997-L1000][f1]

Builds the '<location> ' prefix for a test line.

The nested mkrel asks the config for the cwd-relative nodeid, then when the result ends with the domain, rewrites dots in the domain's first segment to '::' (leaving parameter brackets intact, hence the split on '['). With a non-empty fspath the line is mkrel(nodeid), plus ' <- <relative fspath>' at verbosity >= 2 when the nodeid's file part differs from the fspath; without an fspath it is the literal '[location]'. A trailing space is always appended.

uses: [Config.cwd_relative_nodeid](r2-config-lifecycle.md#u-a226606b0680)

<a id="u-485445f66ec3"></a>
### `TerminalReporter.write_ensure_prefix`

`def write_ensure_prefix(self, prefix: str, extra: str = "", **kwargs) -> None:` · [src/_pytest/terminal.py:L472-L479][f1]

Writes text under a location prefix, keeping column alignment.

When currentfspath differs from the given prefix it starts a new line, stores the prefix as currentfspath, and writes the prefix. If extra is non-empty it is written with the kwargs and currentfspath is set to -2, so subsequent lines force a newline (truthy) while never matching a real prefix again.

<a id="u-1dcfa1204f5d"></a>
### `TerminalReporter.write_fspath_result`

`def write_fspath_result(self, nodeid: str, res: str, **markup: bool) -> None:` · [src/_pytest/terminal.py:L461-L470][f1]

Writes a per-file progress result character after the file's relative path.

Resolves fspath from the nodeid path segment; when it differs from currentfspath, flushes pending progress (filling space) if _show_progress_info, switches currentfspath, and writes the best-relative path plus a space on a new line. The result char itself is written with flush=True and any markup kwargs.

<a id="u-adf48d81a0f6"></a>
### `TerminalReporter.wrap_write`

`def wrap_write( self, content: str, *, flush: bool = False, margin: int = 8, line_sep…` · [src/_pytest/terminal.py:L486-L506][f1]

Writes content wrapped so it does not collide with progress info at the right margin.

It prefixes the content with padding matching the current line's width, wraps with textwrap at width _screen_width - margin (dropping whitespace, keeping original whitespace), strips the padding prefix from each resulting line, and writes the joined text with flush and markup kwargs. Default margin is 8, line separator newline.

<a id="u-52343aa4eaa7"></a>
### `TerminalReporter.write_line`

`def write_line(self, line: str | bytes, **markup: bool) -> None:` · [src/_pytest/terminal.py:L514-L518][f1]

Writes one full line.

Non-str input (e.g. bytes) is decoded with errors='replace'; then ensure_newline closes any partial line before _tw.line emits the line with markup kwargs.

<a id="u-d3dd32e586da"></a>
### `TerminalReporter._write_progress_information_filling_space`

`def _write_progress_information_filling_space(self) -> None:` · [src/_pytest/terminal.py:L761-L766][f1]

Writes the progress message right-justified to fill the remaining screen width: fill equals fullwidth minus current line width minus one; the message is padded and written with flush and the main color as markup.

<a id="u-2f4d1fae5fb5"></a>
### `TerminalReporter._write_progress_information_if_past_edge`

`def _write_progress_information_if_past_edge(self) -> None:` · [src/_pytest/terminal.py:L745-L759][f1]

Writes a progress update only when the next update would hit the screen edge.

Computes the width the coming message would occupy (count uses len ' [n/n]' with the collected total, times uses len ' 99h 59m', otherwise ' [100%]'); when current line width plus that plus one reaches _screen_width it writes the message followed by a newline colored with the main color.

<a id="u-d6449bde5e4a"></a>
### `TerminalReporter._get_progress_information_message`

`def _get_progress_information_message(self) -> str:` · [src/_pytest/terminal.py:L700-L743][f1]

Builds the progress string for the current state, branching on _show_progress_info.

For 'count': a zero-padded [done/collected] counter, or '[ 0 / 0 ]' when nothing was collected. For 'times': empty when nothing collected; otherwise it concatenates displayable reports of passed, xpassed, failed, xfailed, skipped, error and the empty category, takes the last report's file as current location, counts reports in that file not yet in _timing_nodeids_reported, and — when showlongtestinfo or the module's last test finished — marks those nodeids reported and returns the summed node duration via format_node_duration; else returns ''. For 'progress': a right-aligned percentage of reported nodeids over collected, or ' [100%]' when nothing collected.

calls: [format_node_duration](r9-terminal-summaries.md#u-9113cf07fb29)

**Uncertainties.**

- The 'times' branch sums duration only for TestReport instances (isinstance filter), so other report types contribute 0 duration but still count as tests in the module.

<a id="u-70bf49560342"></a>
### `_format_trimmed`

`def _format_trimmed(format: str, msg: str, available_width: int) -> str | None:` · [src/_pytest/terminal.py:L1469-L1491][f1]

Formats msg into a template, ellipsizing to fit available_width.

Only the first line of msg is considered. Returns None when even the '...' cannot fit (format width plus 3 exceeds available_width). When the message is too wide, it truncates and trims characters until the width fits, then appends the ellipsis.

**Uncertainties.**

- Width checks mix wcswidth for measured strings with len(ellipsis) for the literal '...', so wide-character ellipsis accounting is approximate.

<a id="u-08be377904c8"></a>
### `_get_raw_skip_reason`

`def _get_raw_skip_reason(report: TestReport) -> str:` · [src/_pytest/terminal.py:L1625-L1643][f1]

Extracts the user-provided reason string from a skip/xfail report.

For wasxfail reports the stored string has a 'reason: ' prefix stripped. For skipped reports it asserts skipped and a 3-tuple longrepr and takes the third element, stripping a 'Skipped: ' prefix or collapsing the bare 'Skipped' to an empty string.

<a id="u-aa1caadf2ddf"></a>
### `TerminalReporter._report_keyboardinterrupt`

> **ID corrected by CBE.** CBE changed the unit ID from ` src/_pytest/terminal.py::method::TerminalReporter._report_keyboardinterrupt::981 ` to the inventory ID ` src/_pytest/terminal.py::method::TerminalReporter._report_keyboardinterrupt::34904 `. The model wrote this body under the wrong ID; it may be inaccurate.

`def _report_keyboardinterrupt(self) -> None:` · [src/_pytest/terminal.py:L981-L995][f1]

Prints the stored KeyboardInterrupt repr.

Asserts the memo and its reprcrash exist, writes a '!' separator with the crash message, and only when the message contains 'KeyboardInterrupt' prints the traceback: the full exception repr with --fulltrace, otherwise just the crash location plus a yellow hint line pointing to --full-trace.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/terminal.py
