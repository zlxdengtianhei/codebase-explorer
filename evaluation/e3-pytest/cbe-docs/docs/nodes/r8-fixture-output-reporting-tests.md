# Fixture Setup Reporting Tests

**Capability.** Verifies pytest's fixture lifecycle reporting modes: --setup-only/--setup-plan/--setup-show output and their equivalence (testing/test_setuponly.py, test_setupplan.py), plus the --fixtures-per-test listing end to end (testing/python/show_fixtures_per_test.py). These modes must show SETUP/TEARDOWN without executing fixture bodies in plan mode.

Read this to see the expected textual output of each reporting flag and their scoping correctness regressions (e.g. #2049).

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Units (5)

<a id="u-44bdf4422648"></a>
### `test-setuponly-setup-reporting`

`def mode(request):` · [testing/test_setuponly.py:L11-L13][f1]

Tests --setup-only, --setup-plan and --setup-show fixture lifecycle reporting via the shared 'mode' fixture parametrized over the three flags.

Established behaviors: only fixtures actually used by a test are reported (SETUP/TEARDOWN F lines plus 'test_arg1 (fixtures used: arg1)'), and fixtures whose names start with underscore stay hidden. Scopes appear as F and S prefixes, session fixtures set up before function fixtures and torn down after them. Same-named session/function fixtures show '(fixtures used: arg_same)' nesting; autouse session fixtures are reported even when no test requests them; parametrized fixtures render their id ('arg_same?"foo"?' or custom ids like 'spam'/'FOO' from id callables); fixtures acquired via request.getfixturevalue are reported like normal ones. Under --setup-only, captured fixture stdout/stderr is shown when a later fixture fails. --setup-show executes the tests for real: a failing test gives return code 1 and its line is annotated 'F' ('test_arg (fixtures used: arg)F'). A KeyboardInterrupt raised in a test with no_reraise_ctrlc=True yields SETUP/TEARDOWN lines, a '! KeyboardInterrupt !' banner, 'no tests ran', and ExitCode.INTERRUPTED. Finally, running pytest under python -bb with a bytes parametrized value passes, showing --setup-show does not trigger BytesWarning (#7126).

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346), [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

**Uncertainties.**

- Whether --setup-plan and --setup-only differ in execution semantics beyond output is not asserted in this file beyond flags passed.

<a id="u-eb8b657ffb91"></a>
### `test_show_fixtures_and_test`

`def test_show_fixtures_and_test( pytester: Pytester, dummy_yaml_custom_test: None ) -…` · [testing/test_setupplan.py:L6-L26][f2]

--setup-plan must not execute fixtures: a fixture and test both asserting False run with exit code 0, and the plan output lists 'SETUP    F arg', 'test_arg (fixtures used: arg)', and 'TEARDOWN F arg'.

Uses the dummy_yaml_custom_test fixture for a collectible test file.

**Uncertainties.**

- Relies on the dummy_yaml_custom_test fixture defined outside this file.

<a id="u-869b4379bcba"></a>
### `test_show_multi_test_fixture_setup_and_teardown_correctly_simple`

`def test_show_multi_test_fixture_setup_and_teardown_correctly_simple( pytester: Pytes…` · [testing/test_setupplan.py:L29-L75][f2]

--setup-plan display for a class-scoped fixture used by two tests in a class: SETUP and TEARDOWN indicators for 'fix' each appear exactly once across the whole plan (regression for #2049, where they wrongly appeared per test).

Only the display was affected; execution lifetimes were always correct.

<a id="u-b6a4dfea21cf"></a>
### `test_show_multi_test_fixture_setup_and_teardown_same_as_setup_show`

`def test_show_multi_test_fixture_setup_and_teardown_same_as_setup_show( pytester: Pyt…` · [testing/test_setupplan.py:L78-L122][f2]

For session/module/class/function-scoped fixtures used by one module-level test and two class tests, the filtered SETUP/TEARDOWN lines from --setup-plan must be identical in content and order to those from --setup-show.

<a id="u-05fd46e4be5e"></a>
### `show_fixtures_per_test.py-fixtures-per-test-output`

`def test_no_items_should_not_show_output(pytester: Pytester) -> None:` · [testing/python/show_fixtures_per_test.py:L6-L9][f3]

Tests the --fixtures-per-test reporting option end to end.

test_no_items_should_not_show_output runs it with no collected items and asserts no 'fixtures used by' output and exit code 0. test_fixtures_in_module shows only the requested public fixture (arg1 with docstring, with file:line locations for test and fixture) while the private _arg0 stays hidden. test_fixtures_in_conftest shows conftest fixtures, including the full dependency closure (arg1, arg2 for arg3's test) with conftest line numbers and multiline docstring collapsed to 'arg3'. test_should_show_fixtures_used_by_test confirms a test-module fixture shadows the conftest one with its own docstring and location. test_verbose_include_private_fixtures_and_loc shows that -v additionally reveals private fixtures (_arg1) with locations. test_doctest_items verifies doctest items (module and txt via --doctest-glob) collect without fixture output issues, expecting 'collected 2 items'. test_multiline_docstring_in_module truncates multiline docstrings to the first three lines; test_verbose_include_multiline_docstring shows -v prints the full docstring including blank lines. All use Pytester makepyfile/makeconftest/maketxtfile and check result.stdout.fnmatch_lines / no_fnmatch_line and result.ret.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_setuponly.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/test_setupplan.py
[f3]: ../../../../../../eval/pytest-5989efe/testing/python/show_fixtures_per_test.py
