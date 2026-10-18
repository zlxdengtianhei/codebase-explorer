# Help, version and config discovery tests

**Capability.** Tests of --help rendering of ini options and hook validation, version/debug output, and the config-file discovery helpers in _pytest.config.findpaths.

Read here for the expected help/version text contracts and findpaths resolution rules.

Parent: [CLI, config and package integrity tests](r4-cli-package-tests.md)

## Units (4)

<a id="u-a624d7c090d7"></a>
### `test_version_verbose`

`def test_version_verbose(pytester: Pytester, pytestconfig, monkeypatch) -> None:` · [testing/test_helpconfig.py:L9-L16][f1]

Checks verbose '--version --version' output.

It removes PYTEST_DISABLE_PLUGIN_AUTOLOAD and PYTEST_PLUGINS (raising=False) from the environment so plugin listing is deterministic, runs pytest with two --version flags, asserts ret 0, and matches a stdout line naming pytest with its version and where it was imported from. Conditionally, only when pytestconfig.pluginmanager.list_plugin_distinfo() is nonempty, it also matches 'registered third-party plugins:' and an 'at <location>' line, so the third-party section is asserted only when third-party plugins are installed.

uses: [MonkeyPatch.delenv](r6-monkeypatch-engine.md#u-7e894007c213), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-53c2a6fa41c6"></a>
### `test_helpconfig-help-and-version-tests`

`def test_version_less_verbose(pytester: Pytester, pytestconfig, monkeypatch) -> None:` · [testing/test_helpconfig.py:L19-L24][f1]

Tests of the pytest CLI's version/help/debug surface and hook validation.

test_version_less_verbose removes the same two plugin env vars as the verbose test, runs '--version' once, and matches the plain 'pytest <version>' line with ret 0. test_versions is a regression check that pytest.__version__ is a str and pytest.version_tuple is a tuple. test_help runs '--help', expects ret 0, and matches a block of option text including -m MARKEXPR, the Reporting section with --durations, --version help text, and pointers to setup.cfg, minversion, --markers and --fixtures. test_traceconfig runs '--traceconfig' and matches '*using*pytest*' and '*active plugins*'. test_debug runs '--debug' via runpytest_subprocess, expects ret NO_TESTS_COLLECTED, and asserts 'pytest_sessionstart' appears in pytestdebug.log in the pytester directory. test_PYTEST_DEBUG sets PYTEST_DEBUG=1, runs in a subprocess, expects NO_TESTS_COLLECTED, and matches plugin-manager debug lines ('*pytest_plugin_registered*', '*manager*PluginManager*') on stderr.

uses: [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f), [MonkeyPatch.setenv](r6-monkeypatch-engine.md#u-3bcdaba77d61), [MonkeyPatch.delenv](r6-monkeypatch-engine.md#u-7e894007c213)

<a id="u-718d4e5b24b6"></a>
### `test_helpconfig-ini-help-and-hook-validation-tests`

`def test_none_help_param_raises_exception(pytester: Pytester) -> None:` · [testing/test_helpconfig.py:L53-L64][f1]

Tests of --help rendering of ini options and hook argument validation.

test_none_help_param_raises_exception writes a conftest registering addini('test_ini', None, ...) and, on '--help', expects a stderr TypeError line 'help argument cannot be None for test_ini' (return code not asserted). test_empty_help_param registers addini with an empty help string, expects ret 0, and matches consecutive stdout lines showing required_plugins and test_ini rendered with default type info, followed by the 'Environment variables:' section. test_hookvalidation_unknown registers a conftest hook pytest_hello(xyz) without optionalhook=True; the run fails (ret != 0) with '*unknown hook*pytest_hello*' on stdout. test_hookvalidation_optional marks the same hook @pytest.hookimpl(optionalhook=True); the run then succeeds with ExitCode.NO_TESTS_COLLECTED, since optional hooks with unknown names are tolerated.

uses: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- For test_none_help_param_raises_exception, where the TypeError is raised and whether the process exit code reflects it is not observable in this file.

<a id="u-b498afe70977"></a>
### `test-findpaths-config-discovery`

`class TestLoadConfigDictFromFile:` · [testing/test_findpaths.py:L16-L17][f2]

Tests the config-file discovery helpers in _pytest.config.findpaths.

load_config_dict_from_file behavior established by the tests: an empty pytest.ini still yields {} (pytest.ini is always considered); a [pytest] section in pytest.ini or any .ini file is parsed into a dict of strings (x -> '1'); a custom .ini without [pytest] yields None; a .cfg without [tool:pytest] yields None; a .cfg containing [pytest] raises pytest.fail.Exception to alert users that this is unsupported; malformed TOML raises UsageError; a .toml without [tool.pytest.ini_options] yields None; a valid .toml coerces scalars to strings (1 -> '1', 20.0 -> '20.0'), keeps string lists as lists, and preserves heterogeneous lists like [1, 'str'] unchanged. get_common_ancestor includes the invocation cwd in the ancestor computation: two files under tmp_path/foo in different subtrees yield tmp_path/foo, and passing either file or its parent directory gives the same result; a single dir yields itself, and a single file yields its parent directory. get_dirs_from_args returns the parent dir of each existing file and each existing directory, silently skipping nonexistent paths and option-looking strings including xdist-style rsync options like 'popen=c:/dest'. is_fs_root is true only for a bare separator or drive-letter-plus-separator path (drive case only on win32).

imports: [_pytest.config.findpaths](../../catalog.json); calls: [test-findpaths-config-discovery](r4-cli-help-config-tests.md#u-b498afe70977)

**Uncertainties.**

- Exact TOML-to-str coercion rules beyond the asserted examples (e.g. booleans, nested tables) are not derivable from this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_helpconfig.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/test_findpaths.py
