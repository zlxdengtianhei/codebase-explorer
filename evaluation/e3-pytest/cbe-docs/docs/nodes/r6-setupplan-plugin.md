# Setup Plan Dry Run

**Capability.** Implements --setupplan by reusing setup-only machinery: it flips setuponly/setupshow, and short-circuits fixture setup with a dummy cached result so fixtures never execute.

Use it to see how pytest reports what would run without executing anything. All hookimpls are tryfirst and defer to normal behavior when the flag is absent.

Parent: [Built-in Plugins and CLI Facets](r6-builtin-plugins.md)

## Units (3)

<a id="u-dfa5e87bab0c"></a>
### `src/_pytest/setupplan.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/setupplan.py:L11-L19][f1]

Adds the --setupplan/--setup-plan store_true flag to the 'debugconfig' group, advertised as showing which fixtures and tests would execute without executing anything.

<a id="u-f723c785d8d4"></a>
### `src/_pytest/setupplan.py:pytest_cmdline_main`

`def pytest_cmdline_main(config: Config) -> int | ExitCode | None:` · [src/_pytest/setupplan.py:L34-L39][f1]

Hookimpl with tryfirst=True: when --setupplan is given, turns on config.option.setuponly and setupshow so the dry run reuses the setup-only machinery with show; always returns None, deferring to the normal cmdline main.

<a id="u-6f04ff50c033"></a>
### `src/_pytest/setupplan.py:pytest_fixture_setup`

`def pytest_fixture_setup( fixturedef: FixtureDef[object], request: SubRequest ) -> ob…` · [src/_pytest/setupplan.py:L22-L31][f1]

Hookimpl with tryfirst=True: when the request's config has --setupplan, computes the fixture's cache key via fixturedef.cache_key(request), stores a dummy cached result (None, key, None) on fixturedef.cached_result, and returns it so the fixture body never runs; otherwise returns None, letting later hook implementations perform real setup.

**Notes.**

- side_effect: Mutates fixturedef.cached_result, so downstream fixture finalization sees a completed (dummy) result.

calls: [FixtureDef](r5-fixture-lifecycle.md#u-9674c75d4866)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/setupplan.py
