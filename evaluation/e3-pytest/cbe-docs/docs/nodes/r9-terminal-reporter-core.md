# Reporter Lifecycle and Collection Output

**Capability.** Construction and registration of the TerminalReporter, session start/finish orchestration, and collection reporting (collecting/collected lines, listing collected items).

Read this to see how the reporter is created, when the header prints, and how collection results accumulate. Session finish gates the summary hooks on exit status and --no-summary.

**Depends on.**

- [Runner Options and Status Defaults](r9-runner-config-durations.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Live and File Handlers](r9-logging-live-file-handlers.md) · model-inferred · 0 edge(s)
- [Runtest Protocol](r9-runner-protocol.md) · model-inferred · 0 edge(s)
- [Summary Sections](r9-terminal-summaries.md) · graph-only · 32 edge(s)

Parent: [Terminal Reporting](r9-terminal-reporting.md)

## Units (14)

<a id="u-8d4b8f445ae8"></a>
### `TerminalReporter`

`class TerminalReporter:` · [src/_pytest/terminal.py:L369-L371][f1]

Final plugin class owning all terminal output of a pytest session: header, per-test progress, collection reporting and end-of-session summaries.

It stores self.stats mapping outcome category to report lists and wraps a config-created TerminalWriter. Trivial members folded here: verbosity returns option.verbose; showheader is verbosity >= 0; no_header/no_summary mirror their flags; showfspath returns the stored override when set, else test-cases verbosity >= 0, and its setter stores that override; showlongtestinfo is test-cases verbosity > 0; hasopt maps 'xfailed'->'x' and 'skipped'->'s' then checks reportchars; write, flush, section, line and _width_of_current_line delegate to the writer; ensure_newline closes a partial line when currentfspath is truthy and resets it; write_sep calls ensure_newline then _tw.sep; _add_stats extends the category list and calls _set_main_color the first time a category appears; pytest_internalerror writes each repr line prefixed 'INTERNALERROR> ' and returns True; pytest_warning_recorded converts the WarningMessage via locally imported warning_record_to_str into a WarningReport filed under 'warnings'; pytest_plugin_registered logs only with --traceconfig (the source notes this may garble output during setup/teardown); pytest_deselected files items under 'deselected'; _is_last_item asserts a session and compares len(_progress_nodeids_reported) to session.testscollected; _getfailureheadline returns rep.head_line or 'test session'; _getcrashline tries str(rep.longrepr.reprcrash), falls back to str(rep.longrepr)[:50] on AttributeError, then ''; getreports filters out reports having _pdbshown; _get_reports_to_display keeps reports lacking count_towards_summary unless the attribute is falsy; pytest_keyboard_interrupt stores excinfo.getrepr(funcargs=True) as the memo; pytest_unconfigure re-reports a pending KeyboardInterrupt memo; pytest_collection writes 'collecting ... ' bold when isatty and verbose >= 0, or when not a tty but verbose >= 1.

calls: [getreportopt](r9-terminal-config.md#u-19e5bdd30a79), [TerminalReporter._determine_show_progress_info](r9-terminal-reporter-core.md#u-73d635b530b1)

**Uncertainties.**

- compat.CallableBool semantics are defined outside this file; the in-code comment says file.isatty may be a bool or a method and the wrapper supports both.

<a id="u-3074cf4f26e1"></a>
### `TerminalReporter.__init__`

`def __init__(self, config: Config, file: TextIO | None = None) -> None:` · [src/_pytest/terminal.py:L371-L399][f1]

Initializes reporter state: empty stats dict, zero collected count, startpath from config.invocation_params.dir; output defaults to sys.stdout when no file is given.

The TerminalWriter comes from create_terminal_writer(config, file); its fullwidth is cached as _screen_width and its hasmarkup copied. reportchars is computed by getreportopt, fold_skipped read from options, and file.isatty wrapped in compat.CallableBool to support both a boolean and a method. Seeds the progress and timing nodeid sets, eagerly resolves _show_progress_info, starts a timing Instant used to throttle collection reports, and clears the displayed-warnings counter and keyboard-interrupt memo.

<a id="u-73d635b530b1"></a>
### `TerminalReporter._determine_show_progress_info`

`def _determine_show_progress_info( self, ) -> Literal["progress", "count", "times", F…` · [src/_pytest/terminal.py:L401-L424][f1]

Decides the progress mode from configuration, evaluated once at construction.

Returns False when capture is 'no' unless the ini style is 'progress-even-when-capture-no', and False when setupshow is enabled. Otherwise console_output_style is read again: 'progress' or 'progress-even-when-capture-no' yield 'progress', 'count' yields 'count', 'times' yields 'times', anything else False. The ini is read twice, so an unrecognized style reaches the final False branch.

<a id="u-d163a8944a10"></a>
### `src/_pytest/terminal.py:pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/terminal.py:L287-L292][f1]

Creates a TerminalReporter writing to sys.stdout and registers it in the plugin manager under 'terminalreporter'.

When --debug or --traceconfig is set, installs the nested mywriter as processor for the 'pytest:config' trace path; mywriter joins its args into a space-separated string and prints it via reporter.write_line prefixed '[traceconfig] '.

uses: [TerminalReporter](r9-terminal-reporter-core.md#u-8d4b8f445ae8)

<a id="u-900b4bf5db46"></a>
### `TerminalReporter.pytest_sessionstart`

`def pytest_sessionstart(self, session: Session) -> None:` · [src/_pytest/terminal.py:L826-L851][f1]

trylast wrapper-free hook: stores the session, starts the session timer, and prints the session header unless showheader is false (returns early).

With --no-header it stops after the 'test session starts' separator. Otherwise it writes 'platform <sys.platform> -- Python <ver>', switching to a pypy version string when sys.pypy_version_info exists, appending pytest and pluggy versions, plus the executable path when verbose > 0, --debug, or pastebin is set. It then writes header lines from the pytest_report_header hook.

uses: [TerminalReporter.pytest_report_header](r9-terminal-reporter-core.md#u-d1dd04669dba)

<a id="u-f33e1c4b4b7c"></a>
### `TerminalReporter.pytest_sessionfinish`

> **ID corrected by CBE.** CBE changed the unit ID from ` src/_pytest/terminal.py::method::TerminalReporter.pytest_sessionfinish::932 ` to the inventory ID ` src/_pytest/terminal.py::method::TerminalReporter.pytest_sessionfinish::33118 `. The model wrote this body under the wrong ID; it may be inaccurate.

`def pytest_sessionfinish( self, session: Session, exitstatus: int | ExitCode ) -> Gen…` · [src/_pytest/terminal.py:L932-L957][f1]

Wrapper hook: yields the inner result, writes an empty line, and when the exit status is one of OK, TESTS_FAILED, INTERRUPTED, USAGE_ERROR or NO_TESTS_COLLECTED and --no-summary is off, triggers the pytest_terminal_summary hook.

Then: session.shouldfail is written as a red '!' section; for INTERRUPTED it reports the keyboard interrupt via the memo and clears it; otherwise session.shouldstop is written as a red '!' section. Finally prints summary_stats and returns the inner result.

<a id="u-7ff87a1fa1f3"></a>
### `TerminalReporter.pytest_runtestloop`

`def pytest_runtestloop(self) -> Generator[None, object, object]:` · [src/_pytest/terminal.py:L686-L698][f1]

Wrapper hook around the test loop: yields to the inner loop, then after it completes writes the final 100% progress by calling _write_progress_information_filling_space — but only when test-cases verbosity <= 0, progress info is enabled and at least one progress nodeid was reported.

Returns the inner result unchanged.

<a id="u-976fbe74b4e6"></a>
### `TerminalReporter.pytest_collectreport`

`def pytest_collectreport(self, report: CollectReport) -> None:` · [src/_pytest/terminal.py:L780-L788][f1]

Accumulates collection results.

Failed collection reports are filed under 'error', skipped ones under 'skipped'; Items among report.result are counted into _numcollected. When isatty, it immediately calls report_collect for a throttled in-progress line.

<a id="u-1174b17a88fb"></a>
### `TerminalReporter.pytest_collection_finish`

`def pytest_collection_finish(self, session: Session) -> None:` · [src/_pytest/terminal.py:L880-L900][f1]

Finishes collection: writes the final report_collect line, then the lines from pytest_report_collectionfinish hooks.

In collectonly mode it prints an empty line first (when items exist and verbose > -1) and the collected items; afterwards, if 'failed' stats exist it prints a '! collection failures' separator and each failed report's toterminal output.

<a id="u-29542490bc9b"></a>
### `TerminalReporter.report_collect`

`def report_collect(self, final: bool = False) -> None:` · [src/_pytest/terminal.py:L790-L824][f1]

Writes the collecting/collected status line.

Returns immediately at verbosity < 0; intermediate calls are throttled to one write per REPORT_COLLECTING_RESOLUTION (0.5s) seconds via the stored Instant, while final=True is never throttled. Builds 'collected/collecting N item(s)' plus '/ k errors', '/ k deselected', '/ k skipped' and '/ selected selected' segments as their counts are nonzero. On a tty it rewrites the line in place (bold, erase) and appends a newline only when final; otherwise it writes a plain line.

**Uncertainties.**

- self.isatty is invoked as a call, enabled by compat.CallableBool; the graph shows other isatty implementations exist elsewhere.

<a id="u-5ad6073d2531"></a>
### `TerminalReporter._printcollecteditems`

`def _printcollecteditems(self, items: Sequence[Item]) -> None:` · [src/_pytest/terminal.py:L902-L930][f1]

Lists collected items per collectonly verbosity.

At test-cases verbosity < -1 it prints per-file counts ('name: count', sorted); at exactly -1 one nodeid per line. At >= 0 it maintains a collector stack: for each item it pops stack entries that no longer prefix the item's listchain, then prints each new collector indented by nesting depth; at verbosity >= 1 it additionally prints each collector object's docstring lines indented further.

<a id="u-308a0e4b66fe"></a>
### `TerminalReporter.rewrite`

`def rewrite(self, line: str, **markup: bool) -> None:` · [src/_pytest/terminal.py:L520-L536][f1]

Rewinds the current terminal line with a carriage return and rewrites it.

With the erase markup kwarg set, it pads with spaces to fullwidth minus the line length minus one, so the previous longer content is overwritten; otherwise no fill. The line is coerced to str and written with remaining markup kwargs.

<a id="u-d1dd04669dba"></a>
### `TerminalReporter.pytest_report_header`

`def pytest_report_header(self, config: Config) -> list[str]:` · [src/_pytest/terminal.py:L863-L878][f1]

Produces the baseline header lines: 'rootdir: <rootpath>'; 'configfile: <relative inipath>' when config.inipath is set; 'testpaths: ...' joined from the testpaths ini when args came from TESTPATHS; and 'plugins: ...' names/versions when the plugin manager has distinfo entries.

<a id="u-1b91a187d440"></a>
### `_plugin_nameversions`

`def _plugin_nameversions(plugininfo) -> list[str]:` · [src/_pytest/terminal.py:L1579-L1590][f1]

Turns plugin distinfo pairs into short 'name-version' strings for the header: each entry becomes '<project_name>-<version>', a leading 'pytest-' prefix is stripped to keep names short, and duplicates are dropped preserving first-seen order.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/terminal.py
