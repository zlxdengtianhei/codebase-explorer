# Formatting Helpers and Fixtures

**Capability.** Unit tests of small formatting/parsing helpers (duration formatting, trimmed lines, raw skip-reason extraction, plugin name/version formatting), plus shared input fixtures and module constants.

Use it for pure-function behavior of terminal helper functions; DistInfo/Option supply test data for the parametrized cases.

Parent: [Terminal Reporting Suite](r6-test-terminal.md)

## Units (13)

<a id="u-d4479bcf566b"></a>
### `test_terminal.py module code (L1–L36)`

`module_region` · [testing/test_terminal.py:L1-L36][f1]

Holds the file's imports and module constants.

TRANS_FNMATCH is a translation table escaping '[' and ']' as '[[]' and '[]]', used to escape bracket glob characters before translating test-ID literals into fnmatch patterns for xdist-verbose line matching.

**Notes.**

- field: TRANS_FNMATCH escapes both bracket directions so literal '[' or ']' in test IDs survive fnmatch pattern translation.

uses: [TestProgressOutputStyle.test_xdist_verbose](r6-terminal-progress.md#u-0ff42833eb38)

<a id="u-ea5e310be775"></a>
### `test_terminal.py module code (L39–L44)`

`module_region` · [testing/test_terminal.py:L39-L44][f1]

Non-behavioral region containing the TRANS_FNMATCH constant assignment only.

<a id="u-8d2af9da8b24"></a>
### `DistInfo`

`class DistInfo(NamedTuple):` · [testing/test_terminal.py:L37-L39][f1]

Named tuple with project_name (str) and version fields used purely as input data for the _plugin_nameversions test cases.

<a id="u-a7a3e24e7744"></a>
### `Option`

`class Option:` · [testing/test_terminal.py:L45-L46][f1]

Stores a verbosity integer; its args property converts that value into the single pytest CLI argument '--verbosity={n}' used by verbosity-parametrized tests.

<a id="u-997ca4b3b3a6"></a>
### `testing/test_terminal.py:option`

`def option(request):` · [testing/test_terminal.py:L56-L61][f1]

Parametrized fixture yielding Option instances with verbosity 0, 1, and -1 (ids 'default', 'verbose', 'quiet'), driving verbosity-matrix tests in TestTerminal and TestGenericReporting.

<a id="u-00e303861629"></a>
### `test_plugin_nameversion`

`def test_plugin_nameversion(input, expected):` · [testing/test_terminal.py:L64-L82][f1]

Parametrized test of _plugin_nameversions: normal names pass through as 'name-version', the 'pytest-' prefix is stripped, and duplicate DistInfos are deduplicated to a single entry.

<a id="u-999c0a8aa20b"></a>
### `test_format_node_duration`

`def test_format_node_duration(seconds: float, expected: str) -> None:` · [testing/test_terminal.py:L2719-L2737][f1]

Parametrized checks of format_node_duration: hours as ' 99h 59m', minutes/seconds ' 30m 59s', seconds with milliseconds precision, and sub-second values scaled to ms/us units.

<a id="u-9dc30d4dcee2"></a>
### `test_format_session_duration`

`def test_format_session_duration(seconds, expected):` · [testing/test_terminal.py:L2702-L2716][f1]

Parametrized checks of format_session_duration: seconds with two decimals, appending '(H:MM:SS)' once over a minute (e.g. '123.55s (0:02:03)', '3600.50s (1:00:00)').

<a id="u-9b9d564cbda2"></a>
### `test_format_trimmed`

`def test_format_trimmed() -> None:` · [testing/test_terminal.py:L2885-L2889][f1]

_format_trimmed formats ' (msg) ' when the message fits the available width, otherwise truncates to ' (unconditional ...) '.

<a id="u-543cbb1bb068"></a>
### `test_raw_skip_reason_skipped`

`def test_raw_skip_reason_skipped() -> None:` · [testing/test_terminal.py:L2868-L2874][f1]

A SimpleNamespace with skipped=True and longrepr ('xyz', 3, 'Skipped: Just so') cast to TestReport: _get_raw_skip_reason strips the 'Skipped: ' prefix, returning 'Just so'.

<a id="u-5ab143bc6e1c"></a>
### `test_raw_skip_reason_xfail`

`def test_raw_skip_reason_xfail() -> None:` · [testing/test_terminal.py:L2877-L2882][f1]

A SimpleNamespace with wasxfail='reason: To everything there is a season': _get_raw_skip_reason strips the 'reason: ' prefix.

<a id="u-4fa53389ea86"></a>
### `TestNodeIDHandling`

`class TestNodeIDHandling:` · [testing/test_terminal.py:L3267-L3268][f1]

Checks node-id rendering for Windows-style path separators inside parametrized arguments.

<a id="u-ab77ef6e90aa"></a>
### `TestNodeIDHandling.test_nodeid_handling_windows_paths`

`def test_nodeid_handling_windows_paths(self, pytester: Pytester, tmp_path) -> None:` · [testing/test_terminal.py:L3268-L3299][f1]

Runs from a subdirectory with an ini (changing rootpath vs invocation dir); parametrized args containing 'x/y', 'C:/path', backslashes, 'C:\path', and 'a::b/' must appear verbatim (regex-escaped) inside the FAILED verbose lines, proving slashes, backslashes, and '::' in parameter values do not corrupt node IDs.

**Uncertainties.**

- Whether this test passes on non-Windows platforms (it chdirs and uses backslash args) cannot be established from this file alone.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_terminal.py
