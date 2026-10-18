# Fixture setup display plugin

**Capability.** The --setuponly/--setupshow plugin: registers flags, forces setupshow from setuponly, and wraps fixture setup and finalizer hooks to print SETUP/TEARDOWN action lines using the Scope enum for readable scope names.

Consult this to see how fixture activity is surfaced on the terminal without executing tests or while they run.

**Depends on.**

- [Fixture setup, execution and teardown](r5-fixture-lifecycle.md) · model-inferred · 0 edge(s)
- [Timing and scope primitives](r5-time-scope-primitives.md) · model-inferred · 0 edge(s)

Parent: [Runtime diagnostics and shared primitives](r5-runtime-diagnostics.md)

## Units (5)

<a id="u-16258c8e75e1"></a>
### `src/_pytest/setuponly.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/setuponly.py:L15-L28][f1]

Registers two boolean flags in the 'debugconfig' parser group: --setuponly/--setup-only (store_true, 'Only setup fixtures, do not execute tests') and --setupshow/--setup-show (store_true, 'Show setup of fixtures while executing tests').

Registration only; parsing is handled by the parser.

calls: [Parser.getgroup](r4-argparsing-parser-api.md#u-e2ffc00b5f80)

<a id="u-864d54f69d16"></a>
### `src/_pytest/setuponly.py:pytest_cmdline_main`

`def pytest_cmdline_main(config: Config) -> int | ExitCode | None:` · [src/_pytest/setuponly.py:L94-L98][f1]

Tryfirst main hook: when --setuponly was given, it forces config.option.setupshow to True so fixture setup/teardown actions are displayed, then returns None to let normal main processing continue (the actual 'only setup, do not run tests' enforcement lives elsewhere).

**Uncertainties.**

- How --setuponly skips test execution is not implemented in this file; only the setupshow flag propagation is visible.

<a id="u-543e25a5b340"></a>
### `src/_pytest/setuponly.py:pytest_fixture_setup`

`def pytest_fixture_setup( fixturedef: FixtureDef[object], request: SubRequest ) -> Ge…` · [src/_pytest/setuponly.py:L31-L50][f1]

Wrapper hook around fixture setup: the fixture's normal setup result is yielded through unchanged; in the finally clause, when config.option.setupshow is set, it displays the SETUP action.

If the request has a 'param' attribute, it first resolves a displayable param — calling fixturedef.ids(param) when ids is callable, indexing fixturedef.ids[request.param_index] when ids is a sequence, otherwise using request.param directly — and stores it on fixturedef.cached_param so both the SETUP display here and the later TEARDOWN display can show it.

calls: [_show_fixture_action](r5-setuponly-display.md#u-47930f60bc2e)

**Uncertainties.**

- Behavior of indexing fixturedef.ids with request.param_index when ids is a non-callable of mismatched length is not visible here.

<a id="u-c43ba7133b4d"></a>
### `src/_pytest/setuponly.py:pytest_fixture_post_finalizer`

`def pytest_fixture_post_finalizer( fixturedef: FixtureDef[object], request: SubReques…` · [src/_pytest/setuponly.py:L53-L61][f1]

Hook running after each fixture finalizer: only when fixturedef.cached_result is not None and config.option.setupshow is set, it shows the TEARDOWN action and then deletes fixturedef.cached_param if present, keeping the display from repeating for already-torn-down fixtures.

calls: [_show_fixture_action](r5-setuponly-display.md#u-47930f60bc2e)

<a id="u-47930f60bc2e"></a>
### `_show_fixture_action`

`def _show_fixture_action( fixturedef: FixtureDef[object], config: Config, msg: str ) …` · [src/_pytest/setuponly.py:L64-L91][f1]

Prints one fixture action line for --setupshow.

It first suspends global capture (and resumes it at the end) whenever the capturemanager plugin is present, so the output is actually visible. Using the terminal writer, it writes a blank line, then indentation of 2 spaces per reversed-Scope index of the fixture's _scope (higher scope means less indentation: Session 0, Package 1, etc.), then '<msg padded to 8> <first letter of scope uppercased> <argname>'. For msg 'SETUP' it additionally appends '(fixtures used: ...)' listing sorted argnames excluding 'request' when any exist. If fixturedef has cached_param, it appends '[<saferepr(cached_param, maxsize=42)>]' before flushing.

uses: [Scope](r5-time-scope-primitives.md#u-046837a5b5a3), [src/_pytest/_io/saferepr.py][f2]

**Uncertainties.**

- Graph evidence lists two candidates for config.get_terminal_writer(); the production Config method is assumed but not provable from this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/setuponly.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/_io/saferepr.py
