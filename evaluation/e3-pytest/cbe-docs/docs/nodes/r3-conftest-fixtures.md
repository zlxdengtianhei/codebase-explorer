# Testing conftest Fixtures

**Capability.** Repo-wide test fixtures: color env cleanup and ColorMapping helper, fixed column width, trace-function restoration, mocked timing, a mocked terminal writer, YAML-collection scaffolding, plugin-autoload-disabled pytester, and fastest-first item reordering.

Use this subtree to see the guarantees every pytest self-test runs under. The autouse fixtures neutralize host color/terminal/tracing state; the named fixtures supply pytester, tw_mock, color_mapping, mock_timing, and dummy YAML collection.

**Depends on.**

- [Terminal Writer](r3-terminal-writer.md) · model-inferred · 0 edge(s)

Parent: [Test-Suite Infrastructure](r3-test-infra.md)

## Units (9)

<a id="u-393935c1e454"></a>
### `reset_colors`

`def reset_colors(monkeypatch: pytest.MonkeyPatch) -> None:` · [testing/conftest.py:L39-L47][f1]

Autouse fixture deleting the PY_COLORS, NO_COLOR and FORCE_COLOR environment variables (each with raising=False, so absence is fine) so host color settings cannot affect tests asserting on pytest's own colored output.

<a id="u-8e2e43893603"></a>
### `set_column_width`

`def set_column_width(monkeypatch: pytest.MonkeyPatch) -> None:` · [testing/conftest.py:L30-L36][f1]

Autouse fixture forcing terminal width to 80 for every test by setting the COLUMNS environment variable through MonkeyPatch, keeping --help formatting checks deterministic regardless of the host terminal.

<a id="u-29083da5644a"></a>
### `restore_tracing`

`def restore_tracing():` · [testing/conftest.py:L18-L27][f1]

Autouse fixture, defined only when sys.gettrace() is truthy at import (e.g. under Coverage.py), that restores the process trace function after each test.

It saves the trace function before yield; after the test, if it differs, it reinstates the original via sys.settrace, working around CPython bug 37011.

**Uncertainties.**

- Only the import-time condition is visible; which tracer changes the function mid-test is outside this file.

<a id="u-b12557a1005c"></a>
### `testing/conftest.py:pytest_collection_modifyitems`

`def pytest_collection_modifyitems(items) -> Generator[None]:` · [testing/conftest.py:L50-L91][f1]

Tryfirst hook wrapper that reorders collected items fastest-first so options like --ff still operate on the reordered list.

Items without a fixturenames attribute (AttributeError, e.g. doctests) are neutral. Items using the pytester fixture get a slow marker: those whose function code references spawn_pytest or spawn also get an uses_pexpect marker and join the slowest bucket, those referencing runpytest_subprocess join slowest, the rest join slow. Non-pytester items go to slowest if they carry a slow marker, otherwise fast. items is rewritten in place as fast + neutral + slow + slowest, then the wrapper yields, propagating the wrapped hook's result.

**Notes.**

- side_effect: Mutates items in place and adds slow and uses_pexpect markers to pytester-based items.

uses: [testing/conftest.py:pytester](r3-conftest-fixtures.md#u-29ff30038046)

<a id="u-dcc000042fd4"></a>
### `tw_mock`

`def tw_mock():` · [testing/conftest.py:L94-L98][f1]

Fixture returning a mock terminal writer recording all output in self.lines.

sep appends (sep, line) tuples; write appends (TWMock.WRITE, msg) tuples; line appends raw strings; markup returns text unchanged; _write_source zips per-line indents (defaulting to empty strings) with lines and delegates each to line; get_write_msg asserts the entry at idx is a WRITE record before returning its message. __init__ starts lines empty and is_writing False; fullwidth is 80.

**Uncertainties.**

- sep/write/line/markup accept **kw and ignore it; which kwargs the real TerminalWriter passes are not visible here.

<a id="u-660d53cc0d41"></a>
### `color_mapping`

`def color_mapping():` · [testing/conftest.py:L166-L177][f1]

Session-scoped fixture returning the ColorMapping utility class, which replaces {NAME} placeholders in strings with ANSI escape codes for tests checking pytest's colored output.

At fixture setup it reads the installed pygments version via importlib.metadata and Version comparison: for pygments >= 2.19 the 'kwspace' code is the pygments keyword-highlight sequence, otherwise a plain space. ColorMapping defines COLORS (name to escape code), RE_COLORS (re.escape of each code) and NO_COLORS (every name mapped to ''). format substitutes color codes per line; format_for_fnmatch substitutes then escapes '[' as '[[]' for fnmatch_lines; format_for_rematch substitutes RE_COLORS for re_match_lines; strip_colors substitutes '' for every name. All four are classmethods taking and returning list[str].

**Uncertainties.**

- importlib.metadata.version can raise PackageNotFoundError if pygments is absent; behavior in that case is not visible here.

<a id="u-402d47b4296d"></a>
### `dummy_yaml_custom_test`

`def dummy_yaml_custom_test(pytester: Pytester) -> None:` · [testing/conftest.py:L133-L157][f1]

Fixture writing a conftest that collects and runs dummy YAML tests: pytester.makeconftest installs a pytest_collect_file hook converting test*.yaml files into a YamlFile whose collect yields a YamlItem with a no-op runtest, then makefile creates test1.yaml.

Use it when tests need custom collected items.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

<a id="u-4ff5ebeb683a"></a>
### `mock_timing`

`def mock_timing(monkeypatch: MonkeyPatch):` · [testing/conftest.py:L222-L239][f1]

Fixture patching _pytest.timing with a deterministic MockTiming object: it lazily imports MockTiming from _pytest.timing, instantiates it, applies its patch through the given MonkeyPatch, and returns it.

Time is static and advances only through sleep calls, so tests can sleep large amounts instantly while time() stays accurate.

<a id="u-29ff30038046"></a>
### `testing/conftest.py:pytester`

`def pytester(pytester: Pytester, monkeypatch: MonkeyPatch) -> Pytester:` · [testing/conftest.py:L160-L163][f1]

Fixture wrapping the built-in pytester fixture: it sets PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 through MonkeyPatch before returning the Pytester, so tests using it do not autoload installed plugins.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/conftest.py
