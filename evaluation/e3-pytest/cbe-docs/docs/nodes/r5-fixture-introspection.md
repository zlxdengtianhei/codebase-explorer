# Fixture listing from the command line

**Capability.** The --fixtures and --fixtures-per-test modes: command-line option registration, main-hook interception, wrap_session-based listing bodies, and terminal rendering of fixture locations and docstrings.

Use this to trace how the user-facing fixture listings are produced. Both entry points share _pretty_fixture_path and write_docstring for output.

**Depends on.**

- [Fixture registry and requirement closure](r5-fixture-registry.md) · model-inferred · 0 edge(s)

Parent: [Fixture machinery](r5-fixture-machinery.md)

## Units (8)

<a id="u-2cd4df91f8be"></a>
### `src/_pytest/fixtures.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/fixtures.py:L1440-L1463][f1]

Register this module's configuration.

Adds the 'usefixtures' ini option (args type, default empty) listing project-wide default fixtures, and to the 'general' group the --fixtures/--funcattrs flags: --fixtures (dest showfixtures) lists available fixtures sorted by plugin appearance with underscore-named ones shown only at -v, and --fixtures-per-test (dest show_fixtures_per_test) shows fixtures per test.

<a id="u-84be6968727a"></a>
### `src/_pytest/fixtures.py:pytest_cmdline_main`

`def pytest_cmdline_main(config: Config) -> int | ExitCode | None:` · [src/_pytest/fixtures.py:L1466-L1473][f1]

Intercept the main command line for the fixture-listing modes.

If config.option.showfixtures is set, run showfixtures(config) and return 0; otherwise if show_fixtures_per_test is set, run show_fixtures_per_test(config) and return 0; otherwise return None, letting normal session execution proceed.

calls: [showfixtures](r5-fixture-introspection.md#u-f837d2e4413a), [show_fixtures_per_test](r5-fixture-introspection.md#u-2486d6c01684)

<a id="u-f837d2e4413a"></a>
### `showfixtures`

`def showfixtures(config: Config) -> int | ExitCode:` · [src/_pytest/fixtures.py:L1953-L1956][f1]

Entry point for --fixtures: runs _showfixtures_main inside wrap_session and returns its result (int or ExitCode).

<a id="u-2486d6c01684"></a>
### `show_fixtures_per_test`

`def show_fixtures_per_test(config: Config) -> int | ExitCode:` · [src/_pytest/fixtures.py:L1882-L1885][f1]

Entry point for --fixtures-per-test: runs _show_fixtures_per_test inside wrap_session so a full collection is performed, returning wrap_session's result (int or ExitCode).

<a id="u-6498de62e6bf"></a>
### `_showfixtures_main`

`def _showfixtures_main(config: Config, session: Session) -> None:` · [src/_pytest/fixtures.py:L1959-L2013][f1]

Session body for --fixtures.

Performs full collection and lists all registered fixtures. Each fixturedef in fm._arg2fixturedefs is deduplicated by (argname, location), then all entries are sorted by (baseid length, module, pretty path, argname) so more locally-scoped fixtures (longer baseid) come later. When the defining module changes and is not an internal _pytest module, a section header 'fixtures defined from <module>' is printed. Fixtures whose argname starts with '_' are hidden at verbosity 0. Each entry prints the name (green), a cyan '[<scope> scope]' suffix for non-function scopes, the yellow pretty path, and the docstring — only its first paragraph at verbosity 0, else in full — or 'no docstring available' in red, followed by a blank line.

calls: [src/_pytest/main.py:Session.perform_collect (2)](r8-collection-tree.md#u-71c6b6672ba8)

**Uncertainties.**

- get_verbosity has two resolution candidates; the production Config one is presumed.

<a id="u-f25c6a8fd47d"></a>
### `_show_fixtures_per_test`

`def _show_fixtures_per_test(config: Config, session: Session) -> None:` · [src/_pytest/fixtures.py:L1900-L1908][f1]

Session body for --fixtures-per-test.

Performs full collection, then writes per-item fixture usage to a terminal writer at the configured verbosity. get_best_relpath renders a function's location relative to the invocation dir. write_fixture prints the fixture name (green), its pretty path (yellow), and its docstring — only the first paragraph when verbosity is 0, where fixtures whose argname starts with '_' are also skipped; without a docstring it prints 'no docstring available' in red. write_item skips items without _fixtureinfo or with an empty name2fixturedefs, otherwise prints a header with the item name and the relative path of the test function, then for each fixture name (sorted) writes the closest-scope fixturedef (last in the list). Finally every session item is written in order.

calls: [src/_pytest/main.py:Session.perform_collect (2)](r8-collection-tree.md#u-71c6b6672ba8)

**Uncertainties.**

- get_verbosity resolves to Config.get_verbosity at runtime; a test double also exists but is not chosen here.
- item.function is assumed present; a type ignore notes not all items are Functions.

<a id="u-d2da1420a4fc"></a>
### `_pretty_fixture_path`

`def _pretty_fixture_path(invocation_dir: Path, func) -> str:` · [src/_pytest/fixtures.py:L1891-L1897][f1]

Render a fixture's location for help output.

The location (relative to invocation_dir via getlocation) is shown as '.../_pytest/<relpath>' when it lies inside the installed _pytest package; otherwise bestrelpath renders it relative to invocation_dir.

<a id="u-899e7c307100"></a>
### `write_docstring`

`def write_docstring(tw: TerminalWriter, doc: str, indent: str = " ") -> None:` · [src/_pytest/fixtures.py:L2016-L2018][f1]

Write a docstring to the terminal writer, one line at a time, prefixing each line with the given indent (default four spaces).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/fixtures.py
