# Summary Sections

**Capability.** End-of-session summary sections (ERRORS, FAILURES/XFAILURES, PASSES/XPASSES, warnings in two passes, short summary, final stats line) and their formatting helpers.

Read this to see how failures, warnings and the stats line are composed and ordered. Skips are folded for the short summary; duration and pluralization helpers keep the stats line compact.

**Depends on.**

- [Terminal Options and Status Hook](r9-terminal-config.md) · model-inferred · 0 edge(s)
- [Per-Test Progress Output](r9-terminal-progress.md) · graph-confirmed · 4 edge(s)
- [Reporter Lifecycle and Collection Output](r9-terminal-reporter-core.md) · graph-only · 32 edge(s)

Parent: [Terminal Reporting](r9-terminal-reporting.md)

## Units (19)

<a id="u-c31ec4abdfa2"></a>
### `TerminalReporter.pytest_terminal_summary`

> **ID corrected by CBE.** CBE changed the unit ID from ` src/_pytest/terminal.py::method::TerminalReporter.pytest_terminal_summary::959 ` to the inventory ID ` src/_pytest/terminal.py::method::TerminalReporter.pytest_terminal_summary::34128 `. The model wrote this body under the wrong ID; it may be inaccurate.

`def pytest_terminal_summary(self) -> Generator[None]:` · [src/_pytest/terminal.py:L959-L972][f1]

Wrapper hook ordering the summary sections: errors, failures, xfailures, warnings, passes, xpasses, then yielding to other plugins, and in a finally block printing the short test summary and a second summary_warnings pass that shows only warnings recorded after the first pass (teardown warnings).

<a id="u-d44fe467a851"></a>
### `TerminalReporter.summary_errors`

> **ID corrected by CBE.** CBE changed the unit ID from ` src/_pytest/terminal.py::method::TerminalReporter.summary_errors::1176 ` to the inventory ID ` src/_pytest/terminal.py::method::TerminalReporter.summary_errors::42461 `. The model wrote this body under the wrong ID; it may be inaccurate.

`def summary_errors(self) -> None:` · [src/_pytest/terminal.py:L1176-L1189][f1]

Prints the ERRORS section when tbstyle is not 'no' and 'error' stats exist.

For each error report the headline is 'ERROR collecting <headline>' for collection reports or 'ERROR at <when> of <headline>' otherwise, written as a red bold '_' section followed by the report body via _outrep_summary. Note it iterates self.stats["error"] directly (bypassing getreports' _pdbshown filter) after fetching reports only for the emptiness check.

calls: [TerminalReporter._outrep_summary](r9-terminal-summaries.md#u-4335da017d23)

<a id="u-6f8d4c30b59f"></a>
### `TerminalReporter.summary_failures_combined`

`def summary_failures_combined( self, which_reports: str, sep_title: str, *, style: st…` · [src/_pytest/terminal.py:L1151-L1174][f1]

Shared implementation of FAILURES and XFAILURES sections.

Skips everything when the style is 'no' (for xfailures, summary_xfailures passes 'no' unless --xfail-tb is set); otherwise requires needed_opt ('f'/'x' etc.) to pass hasopt unless None. With no reports it returns after the '=' section title is written? No — the early return precedes the separator, so nothing is printed without reports. Style 'line' prints only each report's crash line; other styles print a red bold '_' section per report headed by _getfailureheadline, the full report via _outrep_summary, then teardown sections.

calls: [TerminalReporter._outrep_summary](r9-terminal-summaries.md#u-4335da017d23)

<a id="u-a28e36e28e79"></a>
### `TerminalReporter.summary_passes_combined`

`def summary_passes_combined( self, which_reports: str, sep_title: str, needed_opt: st…` · [src/_pytest/terminal.py:L1101-L1115][f1]

Shared implementation for the PASSES and XPASSES sections.

Only acts when tbstyle is not 'no' and the report char ('P' or 'X') is enabled in reportchars; returns early with no reports. Writes a '=' section titled 'PASSES'/'XPASSES', then for each report with sections prints a green bold '_' section headed by _getfailureheadline and the report body via _outrep_summary, always followed by teardown-section handling for the nodeid.

calls: [TerminalReporter._outrep_summary](r9-terminal-summaries.md#u-4335da017d23)

<a id="u-4335da017d23"></a>
### `TerminalReporter._outrep_summary`

`def _outrep_summary(self, rep: BaseReport) -> None:` · [src/_pytest/terminal.py:L1191-L1202][f1]

Prints a report body and its captured-output sections.

Calls rep.toterminal(self._tw), then unless showcapture is 'no', prints each section as a '-' separator with the content (one trailing newline stripped); sections are skipped when showcapture is not 'all' and the configured stream name does not appear in the section name.

<a id="u-f9b848ab2829"></a>
### `TerminalReporter.print_teardown_sections`

`def print_teardown_sections(self, rep: TestReport) -> None:` · [src/_pytest/terminal.py:L1129-L1140][f1]

Prints the teardown sections of one report: returns immediately when showcapture is 'no'; for each section whose name contains 'teardown' and passes the showcapture filter (all, or the configured stream appears in the section name), writes a '-' separator with the section name and its content, stripping one trailing newline.

<a id="u-97188cbc273d"></a>
### `TerminalReporter.summary_warnings`

`def summary_warnings(self) -> None:` · [src/_pytest/terminal.py:L1041-L1060][f1]

Prints the warnings summary, in two passes.

Returns early if 'w' is not in reportchars or there are no warnings. On the second invocation (detected via _already_displayed_warnings) it shows only the tail of the list and titles the section 'warnings summary (final)'. Warning reports are grouped by message; the nested collapsed_location_report collects each report's location (via WarningReport.get_location), joins locations directly when fewer than 10, otherwise folds them into per-file counts 'file: N warning(s)'. Each group prints the locations (indented message) or the bare message, followed by a blank line and the docs URL.

uses: [WarningReport](r9-terminal-summaries.md#u-ad80b66bdb1c)

**Uncertainties.**

- _already_displayed_warnings records the length of the displayed slice, not the full list; correctness of the second-pass slicing relies on all_warnings being the same list object appended between passes.

<a id="u-ad80b66bdb1c"></a>
### `WarningReport`

`class WarningReport:` · [src/_pytest/terminal.py:L340-L358][f1]

Dataclass holding one captured warning for the summary: message, optional nodeid, optional (filename, lineno) fslocation.

Class flag count_towards_summary is True, so these reports are counted by _get_reports_to_display. get_location prefers the nodeid; otherwise renders fslocation as a path relative to the invocation directory plus ':linenum'; returns None when neither is set.

<a id="u-6ed076f0a445"></a>
### `TerminalReporter.short_test_summary`

`def short_test_summary(self) -> None:` · [src/_pytest/terminal.py:L1241-L1245][f1]

Prints the 'short test summary info' section driven by reportchars; returns when reportchars is empty.

Nested helpers append lines: show_simple prints each report of a stat ('failed', 'passed', 'error') colored via _color_for_type with the reprcrash message line; show_xfailed/show_xpassed print the colored verbose word and nodeid, appending the wasxfail reason when present; show_skipped delegates to folded or unfolded variants based on foldskipped — folded groups via _folded_skips and prints '[count] fspath:lineno: reason' (stripping a 'Skipped: ' prefix), unfolded asserts each longrepr is a 3-tuple and prints nodeid plus reason. The REPORTCHAR_ACTIONS map dispatches each char; unknown chars like 'P' are skipped silently. Any produced lines are written under a cyan bold '=' separator.

calls: [_folded_skips](r9-terminal-summaries.md#u-dd30743287a5), [_get_line_with_reprcrash_message](r9-terminal-summaries.md#u-0b239257ea5b)

**Uncertainties.**

- show_skipped_folded indexes skipped[0] for the verbose word, so the word of the first skip is reused for all folded lines.

<a id="u-dd30743287a5"></a>
### `_folded_skips`

`def _folded_skips( startpath: Path, skipped: Sequence[CollectReport], ) -> list[tuple…` · [src/_pytest/terminal.py:L1526-L1554][f1]

Groups skipped collection reports for the folded summary.

Asserts each longrepr is a 3-tuple (fspath, lineno, reason); fspaths are converted to paths relative to startpath. Setup-phase skips carrying a 'skip' keyword but not 'pytestmark' are folded by (fspath, None, reason) — an acknowledged workaround for unknown marker scope — others by (fspath, lineno, reason). Returns one (count, fspath, lineno, reason) tuple per group.

<a id="u-0b239257ea5b"></a>
### `_get_line_with_reprcrash_message`

`def _get_line_with_reprcrash_message( config: Config, rep: BaseReport, tw: TerminalWr…` · [src/_pytest/terminal.py:L1494-L1523][f1]

Builds a short-summary line '<word> <nodeid>' and tries to append the crash message from rep.longrepr.reprcrash; an AttributeError there leaves the line as-is.

On CI or at verbose >= 2, and unless --force-short-summary, the full message is appended as ' - <msg>'; otherwise _format_trimmed trims it to the remaining terminal width, and a trimmed-out message (None) is omitted.

calls: [_format_trimmed](r9-terminal-progress.md#u-70bf49560342)

<a id="u-c712f3550b7f"></a>
### `_get_node_id_with_markup`

`def _get_node_id_with_markup(tw: TerminalWriter, config: Config, rep: BaseReport):` · [src/_pytest/terminal.py:L1459-L1466][f1]

Renders a report's nodeid with the path part plain and the '::'-separated remainder in bold.

Returns just the path when the nodeid has no '::' parts.

<a id="u-2269f032c341"></a>
### `TerminalReporter.summary_stats`

> **ID corrected by CBE.** CBE changed the unit ID from ` src/_pytest/terminal.py::method::TerminalReporter.summary_stats::1204 ` to the inventory ID ` src/_pytest/terminal.py::method::TerminalReporter.summary_stats::43562 `. The model wrote this body under the wrong ID; it may be inaccurate.

`def summary_stats(self) -> None:` · [src/_pytest/terminal.py:L1204-L1239][f1]

Prints the final '= N passed, ...' line.

Returns immediately at verbosity < -1. Builds the parts line via build_summary_stats_line and renders each part through _tw.markup; at verbosity >= 0 it tracks escape-sequence width overhead so the separator spans the true full width, appending the ' in <duration>' segment (colored with the main color, format_session_duration) and a trailing markup reset trimmed of its final reset code; at lower verbosity it writes a plain line instead.

calls: [TerminalReporter.build_summary_stats_line](r9-terminal-summaries.md#u-376c25c98b91); uses: [format_session_duration](r9-terminal-summaries.md#u-a1d8da9adfb7)

**Uncertainties.**

- _session_start is set in pytest_sessionstart; summary_stats before that hook would raise AttributeError, though normal hook ordering prevents it.

<a id="u-376c25c98b91"></a>
### `TerminalReporter.build_summary_stats_line`

`def build_summary_stats_line(self) -> tuple[list[tuple[str, dict[str, bool]]], str]:` · [src/_pytest/terminal.py:L1377-L1400][f1]

Builds the final stats line parts and overall color, documented as e.g. [('12 passed', {'green': True}), ('2 errors', {'red': True})].

Dispatches to _build_collect_only_summary_stats_line when the collectonly option is set, otherwise to _build_normal_summary_stats_line, returning their (parts, main_color) tuple unchanged.

<a id="u-220ed4c66902"></a>
### `TerminalReporter._build_normal_summary_stats_line`

`def _build_normal_summary_stats_line( self, ) -> tuple[list[tuple[str, dict[str, bool…` · [src/_pytest/terminal.py:L1407-L1424][f1]

Builds the normal run's stats parts.

Uses _get_main_color, then for each known type with displayable reports appends '<count> <pluralized key>' colored via _color_for_type (default yellow), bold when it equals the main color. When no parts exist it emits ('no tests ran', yellow). Returns parts plus the main color.

<a id="u-a43b898f1a04"></a>
### `TerminalReporter._build_collect_only_summary_stats_line`

`def _build_collect_only_summary_stats_line( self, ) -> tuple[list[tuple[str, dict[str…` · [src/_pytest/terminal.py:L1426-L1456][f1]

Builds stats parts for collect-only runs.

With zero collected items: ('no tests collected', yellow). Else when nothing deselected: 'N test(s) collected' in green. Otherwise either 'no tests collected (N deselected)' in yellow when everything was deselected, or 'selected/total tests collected (N deselected)' in green. If errors exist, an '<n> errors' red part is appended and the main color switches to red regardless of the earlier choice.

<a id="u-c0ac6f303da5"></a>
### `pluralize`

`def pluralize(count: int, noun: str) -> tuple[int, str]: # No need to pluralize words…` · [src/_pytest/terminal.py:L1566-L1576][f1]

Returns (count, noun) pluralizing only 'error', 'warnings' and 'test': 'warnings' is first singularized for API stability, then 's' is appended when count != 1; other nouns (passed, failed, skipped) are already past-tense words and returned unchanged.

<a id="u-a1d8da9adfb7"></a>
### `format_session_duration`

`def format_session_duration(seconds: float) -> str:` · [src/_pytest/terminal.py:L1593-L1599][f1]

Formats seconds for the final summary: under 60 seconds as '12.34s'; otherwise as 'S.SSs (H:MM:SS or longer timedelta)' using an integer-second timedelta in parentheses.

<a id="u-9113cf07fb29"></a>
### `format_node_duration`

`def format_node_duration(seconds: float) -> str:` · [src/_pytest/terminal.py:L1602-L1622][f1]

Formats a single-test duration compactly (leading space, at most 7 characters below 100 hours) via a threshold ladder: microseconds with 3/2/1 decimals under 1ms, milliseconds with 3/2/1 decimals under 1s, seconds with 3 decimals under 60, minutes+seconds under an hour, hours+minutes above.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/terminal.py
