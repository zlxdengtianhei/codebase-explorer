# Plugin and Utility Unit Tests

**Capability.** Smaller suites with distinct subsystems: parseopt argument parsing and help formatting, the pythonpath plugin's path injection and cleanup, the Scope enum API, and xunit setup/teardown ordering tests.

Jump here for behavior contracts of individual utilities rather than the collection pipeline. Each grouped suite is self-contained around one framework component.

**Depends on.**

- [JUnit XML Reporting](r7-junit-xml-reporting.md) · graph-confirmed · 2 edge(s)

Parent: [pytest's Own Test Suites](r7-internal-test-suites.md)

## Units (16)

<a id="u-3e4dcda29d96"></a>
### `test_parseopt-Parser-argument-and-group`

`class TestParser:` · [testing/test_parseopt.py:L24-L25][f1]

Covers parseopt.Argument and OptionGroup/Parser group registration.

test_argument: Argument() without any option raises ArgumentError; '-t' yields _short_opts ['-t'], empty long opts, dest 't'; '-t --test' sets both lists and dest 'test'; an explicit dest wins ('abc'), and str(argument) renders the given format. test_argument_type asserts the type kwarg is stored as-is for int, str, float, and that adding choices keeps type str. test_argument_processopt: attrs() reflects default 42 and dest 'abc' after setting them. Group tests: getgroup('hello', description='desc') returns a group with that name and description, and a second getgroup('hello') returns the identical object; group_ordering shows getgroup('3', after='1') places '3' after '1', ordering as 1,3,2 in parser._groups. test_group_addoption: OptionGroup.addoption stores an Argument in group.options. test_group_addoption_conflict: adding '--option1' then re-adding it with a different second alias raises ValueError whose message contains the {'--option1'} set repr. test_group_shortopt_lowercase: group.addoption('-x', ...) raises ValueError (lowercase shorts rejected via the public path) and leaves options empty, while the internal _addoption accepts it (one option). test_parser_addoption: parser.getgroup('custom options') starts with zero options and gains one after addoption.

<a id="u-252e097d1468"></a>
### `test_parseopt-Parser-parsing`

`def test_no_help_by_default(self) -> None:` · [testing/test_parseopt.py:L25-L27][f1]

Covers Parser.parse, parse_known_args, parse_known_and_unknown_args, parse_setoption, and argparse construction.

test_no_help_by_default: parsing ['-h'] with usage='xyz' and no help option raises UsageError. test_custom_prog: _getparser().prog initially equals argparse's default prog, and setting parser.prog changes the built parser's prog. test_parse: parse(['--hello','world']) stores 'world' on dest hello and leaves the FILE_OR_DIR attribute unset. test_parse2: parse([Path('.')]) places '.' in the FILE_OR_DIR list. test_parse_from_file: parse of an '@file' argument reads newline-separated test node ids from the file, matching the original list. test_parse_known_args: after registering --hello, parsing ['x','--y','--hello','this'] sets hello truthy and keeps file_or_dir ['x'], ignoring --y. test_parse_known_and_unknown_args returns (namespace, unknown) where unknown is ['--y','this'] and file_or_dir ['x']. test_parse_will_set_default: parse([]) fills default 'x'; after deleting the attribute, parse_setoption([], option) re-fills it. test_parse_setoption: parsing ['--hello','world'] into a bare argparse.Namespace sets hello='world', world=42 (default), and returns an empty remaining-args list. test_parse_special_destination: '--ultimate-answer 42' maps to args.ultimate_answer==42 (dashes to underscores). test_parse_split_positional_arguments: flags and positionals interleave so FILE_OR_DIR always collects ['4','2'] while -R/-S booleans are set regardless of position. test_parse_defaultgetter: the nested defaultget callback sets default 42 for int-typed options, 'world' for str-typed, and returns early when the option lacks 'type'; parsing [] yields hello 'world', this 42, no False.

<a id="u-981d2dfebc34"></a>
### `test_parseopt-DropShort-help-formatting`

`def test_drop_short_helper(self) -> None:` · [testing/test_parseopt.py:L212-L247][f1]

Covers DropShorterLongHelpFormatter behavior for aliased long options and help output.

test_drop_short_helper builds a raw argparse parser with the formatter: options with several long aliases ('--twoword','--duo','--two-word','--two') can be set via any alias and the value lands on the canonical dest (args.twoword); '--deux-mots' normalizes to args.deuxmots while args.deux_mots does not exist (AttributeError); positional nargs='*' preserves order. test_drop_short_0: parsing ['--funcarg','--k'] raises UsageError (abbreviated '--k' not allowed with allow_abbrev=False behavior). test_drop_short_2: '--doit' sets args.func_arg True for the alias pair '--func-arg','--doit'. test_drop_short_3: with no flags, func_arg is False and 'abcd' goes to file_or_dir. test_drop_short_help0: format_help renders '--func-args, --doit  foo' (hyphens dropped on the short-form long option). test_drop_short_help1: with an explicit -h/--help option added via _addoption, parsing ['-h'] succeeds and help contains '-doit, --func-args  foo'. test_multiple_metavar_help (#2004): an option with metavar tuple ('value1','value2','value3') and nargs=3 renders in help as '--preferences=value1 value2 value3'.

<a id="u-0a6f2ff0c01a"></a>
### `parser`

`def parser() -> parseopt.Parser:` · [testing/test_parseopt.py:L19-L21][f1]

Session-independent fixture returning a parseopt.Parser constructed with _ispytest=True, giving tests a parser instance without usage/help arguments.

<a id="u-d1c70e1a279f"></a>
### `test_argcomplete`

`def test_argcomplete(pytester: Pytester, monkeypatch: MonkeyPatch) -> None:` · [testing/test_parseopt.py:L303-L358][f1]

Integration test for bash argcomplete against pytest's command line.

It picks a locale encoding (locale.getencoding on 3.11+, else getpreferredencoding(False)), runs 'bash --version' and skips if bash is missing or output lacks 'GNU bash' (#7518). It writes a bash script into pytester.path that runs 'python -m pytest' with fd redirections 8>&1 9>&2, then monkeypatch sets _ARGCOMPLETE=1, _ARGCOMPLETE_IFS, COMP_WORDBREAKS, COMP_LINE and COMP_POINT for '--fu': pytester.run('bash', script, arg) must produce --funcargs and --fulltrace; exit 255 skips (argcomplete not found) and empty stdout skips with the stderr quoted. It then creates a 'test_argcomplete.d' directory in the current working directory, sets COMP_LINE for 'test_argc', and expects completions 'test_argcomplete' and 'test_argcomplete.d/'.

**Notes.**

- side_effect: os.mkdir('test_argcomplete.d') is created in the process current directory and not cleaned up here.

**Uncertainties.**

- Whether pytester.run restores the cwd changed implicitly is not shown here; the mkdir target depends on it.

<a id="u-52148cfe486a"></a>
### `test-python-path-py-module-head`

`module_region` · [testing/test_python_path.py:L1-L10][f2]

Module imports and header; no behavioral symbols in this region.

<a id="u-72ca60e66236"></a>
### `file_structure`

`def file_structure(pytester: Pytester) -> None:` · [testing/test_python_path.py:L11-L47][f2]

Fixture creating two test modules importing foo and bar, plus sub/foo.py returning 1 and sub2/bar.py returning 2; the directories are not on sys.path unless an ini sets pythonpath.

**Notes.**

- side_effect: writes files under the pytester tmp directory

<a id="u-425ea1a9cadf"></a>
### `test_one_dir`

`def test_one_dir(pytester: Pytester, file_structure) -> None:` · [testing/test_python_path.py:L50-L54][f2]

With pythonpath=sub, test_foo.py imports foo and passes (1 passed, ret 0).

<a id="u-786fe0b0e488"></a>
### `test_two_dirs`

`def test_two_dirs(pytester: Pytester, file_structure) -> None:` · [testing/test_python_path.py:L57-L61][f2]

With pythonpath='sub sub2', both test files import their modules and pass.

<a id="u-1709bd9b2839"></a>
### `test_local_plugin`

`def test_local_plugin(pytester: Pytester, file_structure) -> None:` · [testing/test_python_path.py:L64-L82][f2]

pythonpath is applied early enough that -plocalplugin can load a plugin from sub; the plugin's load and unconfigure prints appear in stdout and the test run passes (issue 11118).

<a id="u-c9233b8db0c0"></a>
### `test_module_not_found`

`def test_module_not_found(pytester: Pytester, file_structure) -> None:` · [testing/test_python_path.py:L85-L92][f2]

Without pythonpath, importing foo fails: run exits with ExitCode.INTERRUPTED, one collection error, and 'ModuleNotFoundError: No module named foo' in stdout.

<a id="u-c1d262b9c36a"></a>
### `test_no_ini`

`def test_no_ini(pytester: Pytester, file_structure) -> None:` · [testing/test_python_path.py:L95-L101][f2]

With no ini file at all, the same import failure occurs: interrupted exit, one error, ModuleNotFoundError for foo.

<a id="u-4e422db7b307"></a>
### `test_clean_up`

`def test_clean_up(pytester: Pytester) -> None:` · [testing/test_python_path.py:L104-L117][f2]

Verifies the pythonpath plugin removes its entries at shutdown.

The test states implementation assumptions: cleanup happens in a non-wrapper pytest_unconfigure hook, so it registers a Plugin with a tryfirst pytest_unconfigure capturing sys.path before cleanup, runs in-process, and compares against sys.path afterward: 'I_SHALL_BE_REMOVED' is present before and absent after. Nested Plugin and the post-run body are part of this unit.

**Uncertainties.**

- assertion depends on runpytest_inprocess ordering; cleanup timing outside this flow is unverified

<a id="u-15f48430bf5c"></a>
### `test_scope-py-scope-api-tests`

`def test_ordering() -> None:` · [testing/test_scope.py:L9-L13][f3]

Tests the Scope enum API from _pytest.scope.

test_ordering verifies the total ordering Session > Package > Module > Class > Function via comparisons. test_next_lower and test_next_higher verify each scope's adjacent-lower/adjacent-higher transitions, and that Function.next_lower() and Session.next_higher() raise ValueError mentioning the lower-most/upper-most scope. test_from_user checks Scope.from_user maps the string 'module' to Scope.Module, and that an unknown value raises pytest.fail.Exception with a message combining the usage string, the node id, and the bad value.

<a id="u-a57d1ce31ad4"></a>
### `test_scope.py module code (L1–L8)`

`module_region` · [testing/test_scope.py:L1-L8][f3]

Module header: __future__ annotations and imports (re, Scope, pytest).

<a id="u-7fdeeea0a75e"></a>
### `test_runner_xunit-tests`

`def test_module_and_function_setup(pytester: Pytester) -> None:` · [testing/test_runner_xunit.py:L10-L40][f4]

Tests of xunit-style setup/teardown ordering and failure behavior, mostly via pytester.inline_runsource with report verification through reprec.

test_module_and_function_setup checks setup_module/setup_function attributes and teardown on a passing module- and function-level test plus a class test seeing module state but no function attributes. The failure tests establish that when a setup raises (0/0 or ValueError) at module, function, class, or method level, the corresponding teardown never runs: test_module_setup_failure_no_teardown asserts outcome failed=1 and inspects pytest_runtest_setup calls to confirm setup_module ran (values == [1]) before failing; test_setup_function_failure_no_teardown and test_class_setup_failure_no_teardown and test_method_setup_failure_no_teardown each pair the failing test with a cleanup test asserting the mutated state shows setup ran but teardown did not. test_class_setup verifies setup_class/teardown_class balance across a class, a subclass inheriting it, and a cleanup test seeing emptied class lists (passed=4). test_method_setup checks setup_method receives the exact test method per test. test_method_setup_uses_fresh_instances verifies each test gets a new instance by appending self in one test and asserting inequality in the next (passed=2, failed=0). test_setup_that_skips_calledagain and test_setup_fails_again_on_all_tests (makepyfile + inline_run) show a skipping or failing setup_module is re-executed per test, yielding skipped=2 and failed=2 respectively. test_setup_funcarg_setup_when_outer_scope_fails runs runpytest on a module whose setup_module raises ValueError(42) and whose fixture raises ValueError('xyz43'): stdout must show both tests failing with the ValueError 42, '*2 errors*', and must NOT contain xyz43 — the fixture error is suppressed because outer-scope setup failure prevents fixture instantiation. test_setup_teardown_function_level_with_optional_argument, parametrized with arg '' or 'arg' (issue 1728), monkeypatches a trace list onto sys (raising=False) and asserts a fixed ordering of setup_module/setup_function/setup_method/teardown traces across two functions and two methods with all four tests passing.

calls: [pytester-collection-helpers](r6-pytester-run.md#u-0183c0c437e7), [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d), [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- The trace list is injected onto sys with raising=False and read from sys.trace_setups_teardowns inside the generated module; the injection mechanics rely on namespace propagation not proven here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_parseopt.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/test_python_path.py
[f3]: ../../../../../../eval/pytest-5989efe/testing/test_scope.py
[f4]: ../../../../../../eval/pytest-5989efe/testing/test_runner_xunit.py
