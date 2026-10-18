# Configuration test suite

**Capability.** Pins pytest configuration behavior end to end: ini/config-file discovery and parsing, rootdir determination, command-line and fromdictargs loading, override-ini/addopts/PYTEST_ADDOPTS handling, the Config API around options, verbosity ini options, --debug, plugin-loading module-level behavior, rejection of pytest_plugins in non-top-level conftests, and unsupported setup.cfg [pytest] sections.

Use this suite as the executable specification for how pytest resolves configuration. Parse-ini and rootdir groups anchor discovery semantics; the remaining groups cover overrides and the Config API built on top. Several groups interact (parse-ini and module-functions are model-inferred as related), so treat failing discovery tests together.

**Depends on.**

- [Test Run Invocation](r6-pytester-run.md) · graph-only · 104 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 102 edge(s)

Parent: [pytest codebase](r1-pytest-codebase.md)

## Units (11)

<a id="u-c1524ecf1eba"></a>
### `test-config-parse-ini`

`class TestParseIni:` · [testing/test_config.py:L35-L36][f1]

Verifies pytest's ini/config-file discovery, parsing, and early-option behavior.

test_getcfg_and_config checks locate_config finds 'name = value' under [pytest] (pytest.ini) or [tool:pytest] (setup.cfg) in an ancestor of the cwd, and that parseconfigure exposes it via inicfg. test_setupcfg_uses_toolpytest_with_pytest asserts [tool:pytest] wins over [pytest] inside setup.cfg. test_append_parse_args confirms PYTEST_ADDOPTS env var and ini 'addopts' are both applied (color no, -rs, tb short, verbose). test_tox_ini_wrong_version expects a nonzero exit and stderr message when minversion exceeds the running pytest. test_ini_names parametrizes minversion parsing across setup.cfg/tox.ini/pytest.ini/.pytest.ini sections. pyproject.toml cases: it is used as config when containing [tool.pytest.ini_options] or even empty (test_empty_pyproject_toml); with several empty pyproject.toml files the closest to the starting directory wins; pytest.ini takes precedence over pyproject.toml. test_toxini_before_lower_pytestini shows the nearest config (sub/tox.ini) beats a parent pytest.ini. test_ini_parse_error and test_toml_parse_error expect nonzero exit and an 'ERROR:' stderr line on malformed ini/toml. The two confcutdir-default tests assert _confcutdir defaults to rootpath without a configfile and to the configfile's directory with one; test_confcutdir is xfail. test_invalid_config_options parametrizes unknown ini keys: they are reported via _get_unknown_ini_keys, emitted as PytestConfigWarning in the warnings summary, keys under other headers or known keys produce nothing, and --strict-config turns them into a USAGE_ERROR; test_silence_unknown_key_warning shows filterwarnings can silence the warning, and disabling the warnings plugin suppresses issue_config_time_warning output. test_missing_required_plugins monkeypatches importlib.metadata.distributions with a fake 'myplugin' dist and asserts UsageError listing missing plugins, accepting exact/loose pins and prereleases when versions satisfy. test_early_config_cmdline is a regression for options registered by plugins loaded via PYTEST_PLUGINS during early config. The three args_source tests assert Config.ArgsSource is ARGS with positional args, INVOCATION_DIR with none, and TESTPATHS when only testpaths apply.

**Notes.**

- contract: The class body contains no attributes; all behavior lives in its test methods.

uses: [test-config-module-functions](r1-config-test-suite.md#u-33448891ade6)

<a id="u-acf574879ed0"></a>
### `test-config-rootdir`

`class TestRootdir:` · [testing/test_config.py:L1605-L1606][f1]

Pins determine_setup and get_common_ancestor semantics for rootdir/inifile discovery.

test_simple_noini shows get_common_ancestor returns the single arg's directory, the common ancestor of nested dirs, cwd when args are empty, and tmp_path even for nonexistent path arguments. test_with_ini, parametrized over pytest.ini/pyproject.toml/tox.ini/setup.cfg with their matching sections, asserts rootdir is the ini's directory and the same ini is found whether args are the root, a child, a grandchild, or multiple args; the returned ini_config is the parsed dict {'x': '10'}. test_pytestini_overrides_empty_other shows an empty setup.cfg/tox.ini in a subdirectory does not beat an existing (even empty) pytest.ini above it. test_setuppy_fallback shows with only a setup.cfg in a subdir and setup.py at root, rootdir falls back to the setup.py directory and inipath is None with empty inicfg. test_nothing: no config anywhere yields rootdir == args dir, inipath None, inicfg {}. test_with_specific_inifile (only pyproject.toml param active; others commented out) shows an explicit inifile fixes both rootdir and inipath and its parsed config. test_explicit_config_file_sets_rootdir contrasts no explicit config (rootdir is cwd's ancestor, no inipath) with an explicit pytest.ini (rootdir/inipath from the ini's directory). test_with_arg_outside_cwd_without_inifile uses the common ancestor of args; with a pytest.ini in one arg dir, that dir becomes rootdir. test_with_non_dir_arg (empty, nonexistent, nested-nonexistent args) yields rootdir == cwd and no inipath; test_with_existing_file_in_subdir with prefix-matching 'a/exist' likewise. test_with_config_also_in_parent_directory (regression #7807) asserts running from myproject with args 'tests/' picks myproject/setup.cfg and myproject as rootdir, not the parent's setup.cfg.

<a id="u-5ca859c00f67"></a>
### `test-config-cmdline-parsing`

`class TestConfigCmdlineParsing:` · [testing/test_config.py:L556-L557][f1]

Checks command-line-driven config loading.

test_parsing_again_fails asserts that calling Config.parse a second time raises AssertionError, i.e. a parsed config refuses re-parsing. test_explicitly_specified_config_file_is_loaded registers a 'custom' ini option in conftest, then verifies for each of -c and --config-file that an explicitly named custom.ini, a .cfg with [tool:pytest], and a .toml with [tool.pytest.ini_options] are all loaded and their value 'custom = 1' wins over the pytest.ini value 'custom = 0'; the toml file deliberately contains a non-ini list to show toml-only syntax is accepted. test_absolute_win32_path runs pytest.main twice in-process with a normalized absolute Windows-style path to a custom ini containing 'addopts = --version', asserting ExitCode.OK for both -c and --config-file forms.

<a id="u-b9c3d2475f19"></a>
### `test-config-fromdictargs`

`class TestConfigFromdictargs:` · [testing/test_config.py:L1095-L1096][f1]

Tests Config.fromdictargs.

test_basic_behavior shows options come from the dict verbatim (verbose 444, foo 'bar', capture 'no'), args are the given list, and a second parse attempt raises AssertionError. test_invocation_params_args shows raw args like '-vvvv -s a b' are split: config.args keeps only the path arguments ['a','b'] while invocation_params.args retains the full tuple; -vvvv maps to verbose 4 and -s to capture 'no'. test_inifilename sets option_dict['inifilename'] to a relative '../../foo/bar.ini', chdir into a/b (which has its own pytest.ini with conflicting values), and asserts the option is stored, args default to [str(cwd)], inipath points at the referenced bar.ini (resolved via absolutepath relative to cwd), and inicfg values come from bar.ini ('name' == 'value') rather than the cwd pytest.ini ('should_not_be_set' absent).

<a id="u-7aedf6ccd3e6"></a>
### `test-config-override-ini-args`

`class TestOverrideIniArgs:` · [testing/test_config.py:L1840-L1841][f1]

Tests --override-ini (-o), PYTEST_ADDOPTS, and ini 'addopts' handling.

test_override_ini_names, parametrized over setup.cfg/tox.ini/pytest.ini with the right section, shows a single -o custom=2.0 overrides the ini value (printed via a test using pytestconfig), and a repeated -o for the same key wins with the last value (3.0). test_override_ini_paths shows overriding a 'paths' ini with a space-separated string yields bar1.py/bar2.py path objects. test_override_multiple_and_default confirms multiple -o/-o options override different keys including bool conversion ('True'/'no') and values containing '=', '?', '&'. test_override_ini_usage_error_bad_style asserts 'xdist_strict True' (no '=') gives the stderr error '-o/--override-ini expects option=value style'. test_override_ini_handled_asap shows -o python_files=unittest_*.py takes effect regardless of whether an ini file exists, so a test in unittest_ini_handle.py passes. test_addopts_before_initini proves PYTEST_ADDOPTS content is routed into _override_ini during _preparse (cache_dir=.custom_cache appears there). The two not-concatenated tests (#4265) verify a '-o' value is never taken from subsequent normal args: an env-var '-o' followed by 'cache_dir=ignored' raises UsageError mentioning '(via PYTEST_ADDOPTS)', and ini 'addopts=-o' produces the error '(via addopts config)' with USAGE_ERROR exit. test_override_ini_does_not_contain_paths shows -o no longer swallows following path args (#3103); test_multiple_override_ini_options extends that with a file path after -o options collecting and passing exactly one test. test_override_ini_without_config_file shows -o pythonpath=src works with no config file, importing a module from src/ so one test passes.

group: [test-config-override-ini-args](r1-config-test-suite.md#u-7aedf6ccd3e6)

<a id="u-fcd8b82f9062"></a>
### `test-config-api`

`class TestConfigAPI:` · [testing/test_config.py:L631-L632][f1]

Exercises Config's public and private API around options, ini values, and cleanup.

test_config_trace shows config.trace writes through a root writer as 'hello [config]\n'. The getoption tests: declared options resolve by dest, long, and short name; unknown names raise ValueError; without a value getoption returns the parser default None, and with default=1 it still returns None because the option exists, while skip=True yields the supplied default; undeclared names behave analogously. getvalueorskip raises pytest.skip.Exception for an unknown option and otherwise mirrors config.option values (including None-valued declared options, as the None-suffixed test shows). test_getconftest_pathlist confirms _getconftest_pathlist returns None for a missing variable and resolves relative entries against the given path. The addini family: default value depends on type (linelist/paths/pathlist/args default to [], bool to False, string/None type to ""), explicit default=None is honored regardless of type (test_addini_default_values), get_ini_default_for_type is checked directly per type, and unknown ini names raise ValueError. Typed parsing: paths resolve relative to the ini file's parent in both ini and pyproject forms; args and linelist parse from both formats with helper methods make_conftest_for_args/check_config_args and make_conftest_for_linelist/check_config_linelist; bool converts 'True'/'no'; int and float convert strings but a list value in pyproject.toml raises TypeError ('Expected an int/float string...'). addinivalue_line appends entries to an existing or newly created linelist ini value in order. test_confcutdir_check_isdir raises UsageError when --confcutdir is a file or nonexistent and accepts a real directory. test_iter_rewritable_modules pins the module-name rewriting rules for dist-info vs egg layouts and editable finder modules. test_add_cleanup builds a Config via fromdictargs and registers cleanups; _ensure_unconfigure runs them LIFO ('cleanup_first', 'raise_1', 'raise_2', 'cleanup_last'), propagates the last raised exception (MyError from raise_2 matches) after running all cleanups.

uses: [test-config-module-functions](r1-config-test-suite.md#u-33448891ade6)

**Uncertainties.**

- test_add_cleanup expects only the final exception (raise_2) to propagate; whether intermediate exceptions are chained or logged is not visible here.

<a id="u-50b8e97cc372"></a>
### `test-config-verbosity`

`class TestVerbosity:` · [testing/test_config.py:L2470-L2474][f1]

Tests Config.get_verbosity for verbosity ini options registered via Config._add_verbosity_ini.

The nested VerbosityIni plugin registers an option for VERBOSITY_ASSERTIONS through pytest_addoption. test_level_matches_verbose_when_not_specified shows that with only --verbose (via ini addopts) get_verbosity falls back to config.option.verbose; test_level_matches_verbose_when_not_known_type shows the same fallback for an unregistered fake type string; test_level_matches_specified_override shows an explicit verbosity_assertions = 5 ini value takes precedence over --verbose.

**Uncertainties.**

- Whether get_verbosity fallback or the explicit ini value wins is inferred from the asserted outcomes; the resolution order code is not in this file.

<a id="u-2df345de71b1"></a>
### `test-config-debug-options`

`class TestDebugOptions:` · [testing/test_config.py:L2418-L2419][f1]

Covers the --debug option.

test_without_debug_does_not_write_log asserts no 'writing/wrote pytest debug information' stderr lines and no *.log files anywhere under the pytester root. test_with_only_debug_writes_pytestdebug_log shows bare --debug writes pytestdebug.log with matching stderr messages. test_multiple_custom_debug_logs shows '--debug bar.log' then '--debug foo.log' each write their named log (the file is truncated per run) and both files exist afterwards. test_debug_help checks the --help text mentions internal tracing, that the file is opened with 'w' and truncated, and the default name pytestdebug.log.

<a id="u-33448891ade6"></a>
### `test-config-module-functions`

`def test_options_on_small_file_do_not_blow_up(pytester: Pytester) -> None:` · [testing/test_config.py:L1166-L1167][f1]

Module-level tests of plugin loading, reporting, and rootdir/arg behavior.

test_options_on_small_file_do_not_blow_up runs a two-failing-test file through inline_run under many option sets (-l, -s, --tb variants, --fulltrace, --traceconfig, -v) expecting exactly 2 failed each time via the nested runfiletest helper. Plugin-loading tests monkeypatch importlib.metadata.distributions with fake distributions: test_preparse_ordering_with_setuptools checks a setuptools entry-point plugin referenced by both conftest pytest_plugins and PYTEST_PLUGINS is loaded once with its attribute visible; test_setuptools_importerror_issue1479 asserts an ImportError raised by an entry point's load propagates (not hidden); test_importlib_metadata_broken_distribution accepts a distribution with files=None; test_plugin_preparse_prevents_setuptools_loading verifies '-p no:mytestplugin' blocks registration and module import while unblocked parsing registers the placeholder object. test_disable_plugin_autoload is a 9-way matrix over enabling (PYTEST_PLUGINS env, -p flag, none) and disabling (env var, --disable-plugin-autoload flag, none), asserting the plugin loads exactly when enabled or autoload is not disabled, and checking __loader__/__spec__ attribute accesses on a PseudoPlugin with commented caveats (the __spec__ branch is skipped on non-PyPy due to CI/local discrepancy noted in comments). test_plugin_loading_order verifies a -p plugin is registered before the terminal plugin by configure time but not before sessionstart ordering assumptions... concretely it asserts myplugin observes terminalreporter absent at pytest_configure and present at pytest_sessionstart. Reporting/rootdir tests: test_invalid_options_show_extra_information expects inifile and rootdir lines on unrecognized-argument errors; test_consider_args_after_options_for_rootdir shows args after options still influence rootdir discovery; test_toolongargs_issue224 expects NO_TESTS_COLLECTED for a huge -m expression; test_config_in_subdirectory_colon_command_line_issue2148 checks a node-id argument in a subdirectory picks the subdirectory's ini ('foo' == 'subdir'). test_notify_exception asserts config.notify_exception prints the exception to stderr unless a registered plugin's pytest_internalerror returns True, and that with '-p no:terminal' the ValueError still appears. test_no_terminal_discovery_error expects INTERRUPTED when collection errors with the terminal plugin disabled. test_load_initial_conftest_last_ordering pins exact hookimpl ordering for pytest_load_initial_conftests across _pytest.config, a locally registered plugin, legacypath, and the capture/warnings wrappers. test_get_plugin_specs_as_list checks _get_plugin_specs_as_list accepts None, '' , comma strings, and sequences, and raises UsageError for dicts with a specific message (built by exp_match). test_collect_pytest_prefix_bug_integration copies an example and expects 1 passed; test_collect_pytest_prefix_bug asserts parse_hookimpl_opts ignores a nested class named pytest_something. test_help_via_addopts and test_help_and_version_after_argument_error verify --help/--version still work when addopts contain bad options, with minimal help plus UsageError and nonzero exit; test_help_formatter_uses_py_get_terminal_width pins DropShorterLongHelpFormatter width from COLUMNS, _pytest._io.get_terminal_width, or an explicit width. test_config_does_not_load_blocked_plugin_from_args shows '-pno:capture' removes the capfd fixture and makes '-s' unrecognized. test_invocation_args asserts invocation_params.args/dir/plugins on a real run's config (second plugin is PytesterHelperPlugin) and that InvocationParams rejects args=None with TypeError. test_config_blocked_default_plugins, parametrized over every non-essential default plugin, asserts '-pno:<plugin>' keeps passing/failing runs working, with special cases: 'python' yields USAGE_ERROR with a not-found message and 'terminal' yields empty stdout on failure. Final small units: test_conftest_import_error_repr pins ConftestImportFailure's '<Exc>: msg (from <path>)' repr; test_strtobool checks _strtobool accepts YES/NO and rejects unknown; test_parse_warning_filter and its failure variant pin parse_warning_filter's 5-tuple parsing, escaping behavior, and UsageError on too many parts, bad action, unimportable or non-Warning class, and bad line numbers.

uses: [test-config-parse-ini](r1-config-test-suite.md#u-c1524ecf1eba)

**Uncertainties.**

- test_disable_plugin_autoload's __loader__/__spec__ assertions are acknowledged in source comments as partially unexplained; only the assert expressions are documented, not the underlying mechanism.

<a id="u-edf5698aed5b"></a>
### `test-config-pytest-plugins-variable`

`class TestPytestPluginsVariable:` · [testing/test_config.py:L2248-L2249][f1]

Verifies that defining 'pytest_plugins' in a non-top-level conftest.py is rejected.

test_pytest_plugins_in_non_top_level_conftest_unsupported puts pytest_plugins=['capture'] in subdirectory/conftest.py and expects exit code 2 with the message 'Defining pytest_plugins in a non-top-level conftest is no longer supported' and the offending path in stdout. The _pyargs variant builds a src/pkg package tree with the variable only in pkg/sub/conftest.py: with --pyargs the run succeeds (ret 0) and the message is absent; without it the run fails (ret 2) with the message. The _no_top_level_conftest variant moves the top-level conftest into the subdirectory and uses runpytest_subprocess, again expecting ret 2 and the message. The _no_false_positives variant keeps pytest_plugins in the genuine top-level conftest (which also sets warnings.filterwarnings) and an inert subdirectory conftest, asserting ret 0 and the message absent.

<a id="u-af2ecfebb052"></a>
### `test-config-setupcfg`

`class TestSetupCfg:` · [testing/test_config.py:L2221-L2222][f1]

Asserts that a [pytest] section inside setup.cfg, or any other .cfg file given via -c/--config-file, is unsupported: pytester.runpytest raises pytest.fail.Exception in both tests, i.e. the run fails at the pytester level rather than producing a result.

This documents that ini options are not read from these .cfg forms.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_config.py
