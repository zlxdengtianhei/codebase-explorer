# Report Model & Rendering

**Capability.** BaseReport's shared fields (when, location, longrepr, sections, outcome) with presentation and capture-section accessors, plus the concrete TestReport, CollectReport, and CollectErrorRepr classes and worker-info line formatting.

Use this subtree to read or render report data. toterminal writes via TerminalWriter; longreprtext/capstdout/capstderr/caplog extract text sections; TestReport.from_item_and_call builds the per-phase report from a CallInfo.

**Depends on.**

- [Terminal Writer](r3-terminal-writer.md) · graph-confirmed · 3 edge(s)

**Depended on by.**

- [Report Serialization](r3-report-serialization.md) · model-inferred · 0 edge(s)

Parent: [Test & Collection Reports](r3-reports.md)

## Units (14)

<a id="u-bb2e0a19f627"></a>
### `BaseReport`

`class BaseReport:` · [src/_pytest/reports.py:L56-L66][f1]

Base class shared by test and collection reports, carrying core fields (when, location, longrepr, sections, nodeid, outcome) plus generic presentation, capture-section, status, and JSON round-trip behavior.

`__init__` bulk-applies keyword arguments via `__dict__.update`, so reports may carry arbitrary attributes; a TYPE_CHECKING-only `__getattr__` models that for type checkers. Convenience read-only properties: passed/failed/skipped compare `outcome` to the literal; fspath returns the nodeid up to the first '::'; count_towards_summary always returns True; caplog/capstdout/capstderr join the content of sections whose names start with 'Captured log'/'Captured stdout'/'Captured stderr' respectively (empty strings/'' when absent).

<a id="u-2104b752a23a"></a>
### `CollectErrorRepr`

`class CollectErrorRepr(TerminalRepr):` · [src/_pytest/reports.py:L451-L452][f1]

TerminalRepr subclass wrapping a collection error message.

`__init__` stores the message as both self.longrepr; `toterminal` writes that message as a single line with red=True markup.

<a id="u-5719d522515d"></a>
### `CollectReport`

`class CollectReport(BaseReport):` · [src/_pytest/reports.py:L399-L408][f1]

Final collection report class with when fixed to 'collect'.

`__init__` assigns nodeid, outcome, longrepr, a list copy of sections, result (None becomes []), and merges extra kwargs into __dict__. The location property overrides the base annotation to return (fspath, None, fspath) derived from the nodeid. `__repr__` shows nodeid, result length and outcome.

<a id="u-84690a33cd57"></a>
### `TestReport`

`class TestReport(BaseReport):` · [src/_pytest/reports.py:L254-L268][f1]

Final report class for one phase (setup/call/teardown) of a test item.

`__init__` assigns nodeid, location, keywords, outcome, longrepr, when, a list copy of sections, duration, start, stop, and a list copy of user_properties (None becomes []), then merges extra keyword arguments into __dict__, so reports can carry plugin-added attributes; `wasxfail` is set externally by the skipping plugin, not here. `__repr__` shows class name, nodeid, when and outcome.

<a id="u-d1f941732e5b"></a>
### `TestReport.from_item_and_call`

`def from_item_and_call(cls, item: Item, call: CallInfo[None]) -> TestReport:` · [src/_pytest/reports.py:L333-L396][f1]

Builds a TestReport from an item and its CallInfo.

Outcome selection: no excinfo means 'passed' with longrepr None; a non-ExceptionInfo excinfo means 'failed' with that value as longrepr; a skip.Exception means 'skipped', with longrepr a (path, lineno, message) triple — using the item's reportinfo path and line+1 when the skip sets _use_item_location, otherwise the reprcrash location; otherwise 'failed', rendering via item.repr_failure for the 'call' phase and via item._repr_failure_py with the configured tbstyle for setup/teardown. Captured sections are copied from item._report_sections as 'Captured <key> <when>' entries, and the report is constructed from item.nodeid, item.location, keyword dict, timings and user_properties.

calls: [TestReport](r3-report-model.md#u-84690a33cd57), [Item](r7-item-collector-types.md#u-8388b852e250), [Node._repr_failure_py](r7-node-base-lifecycle.md#u-0eac6f0bd989)

<a id="u-a645837e63f2"></a>
### `BaseReport.toterminal`

`def toterminal(self, out: TerminalWriter) -> None:` · [src/_pytest/reports.py:L73-L91][f1]

Writes this report to a TerminalWriter.

If the report has a `node` attribute, a worker info line from getworkerinfoline is printed first (only if non-empty). Returns immediately when `longrepr` is None. If longrepr has a `toterminal` method it renders itself into the writer; otherwise the value is stringified, with UnicodeEncodeError falling back to '<unprintable longrepr>', and written as one line.

calls: [getworkerinfoline](r3-report-model.md#u-738935f011f9)

<a id="u-02f1c0e461ee"></a>
### `BaseReport.longreprtext`

`def longreprtext(self) -> str:` · [src/_pytest/reports.py:L98-L110][f1]

Returns the full failure representation as plain text.

Renders via toterminal into a StringIO-backed TerminalWriter with markup disabled, then returns the stripped text.

calls: [BaseReport.toterminal](r3-report-model.md#u-a645837e63f2)

<a id="u-de3c0769231a"></a>
### `BaseReport.get_sections`

`def get_sections(self, prefix: str) -> Iterator[tuple[str, str]]:` · [src/_pytest/reports.py:L93-L96][f1]

Yields (prefix, content) pairs for each section whose name starts with the given prefix.

The yielded first element is the normalized `prefix`, not the original full section name, so callers grouping by the yielded name merge all matching sections.

<a id="u-d73ee0252912"></a>
### `BaseReport.caplog`

`def caplog(self) -> str:` · [src/_pytest/reports.py:L112-L120][f1]

Returns captured log lines: content of all sections starting with 'Captured log', newline-joined; empty string when none exist.

<a id="u-055eeee6d936"></a>
### `BaseReport.capstdout`

`def capstdout(self) -> str:` · [src/_pytest/reports.py:L122-L130][f1]

Concatenates content of all sections starting with 'Captured stdout'; empty string when none.

<a id="u-e68ea5d7ba94"></a>
### `BaseReport.capstderr`

`def capstderr(self) -> str:` · [src/_pytest/reports.py:L132-L140][f1]

Concatenates content of all sections starting with 'Captured stderr'; empty string when none.

<a id="u-0f0c22aefd72"></a>
### `BaseReport.head_line`

`def head_line(self) -> str | None:` · [src/_pytest/reports.py:L174-L193][f1]

Returns the domain component of the report's location tuple (e.g. 'Test.foo' heading), or None when location is None; path and line number are ignored.

<a id="u-ff1c243c1af8"></a>
### `BaseReport._get_verbose_word_with_markup`

`def _get_verbose_word_with_markup( self, config: Config, default_markup: Mapping[str,…` · [src/_pytest/reports.py:L195-L214][f1]

Resolves the status word and its markup for terminal output via the pytest_report_teststatus hook.

If the hook's verbose value is a plain string, it is returned with the default markup. If it is a two-element sequence of (str, Mapping), both parts are returned. Any other shape triggers fail() with a message naming the invalid value, so no return is reached after that.

uses: [src/_pytest/runner.py:pytest_report_teststatus](r9-runner-config-durations.md#u-20814e5190cb)

<a id="u-738935f011f9"></a>
### `getworkerinfoline`

`def getworkerinfoline(node):` · [src/_pytest/reports.py:L44-L53][f1]

Formats a distributed worker's info dict into one descriptive line, cached on the node.

If `_workerinfocache` exists it is returned; otherwise the first three version components are formatted and a line '[id] sysplatform -- Python ver executable' is built from `node.workerinfo`, stored in `_workerinfocache`, and returned.

**Uncertainties.**

- Assumes workerinfo provides version_info, id, sysplatform and executable; missing-key behavior is not visible here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/reports.py
