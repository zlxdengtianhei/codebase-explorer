# Conftest loading tests

**Capability.** Tests of PytestPluginManager conftest handling: initial conftest collection and import order, value access across directory trees, visibility rules (#616), confcutdir/ini-boundary behavior, CLI-driven end-to-end loading, and edge/error cases — built on the conftest_setinitial helper.

Consult this for the expected semantics of conftest discovery, confcutdir, and import ordering; the shared helper fixes deterministic options for _set_initial_conftests.

**Depends on.**

- [Configuration bootstrapping](r5-config-bootstrapping.md) · model-inferred · 0 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 36 edge(s)

Parent: [pytest's own test suites](r5-test-suites.md)

## Units (11)

<a id="u-a6ce7c20145f"></a>
### `test_conftest.py module code (L1–L19)`

`module_region` · [testing/test_conftest.py:L1-L19][f1]

Module header: imports (os, pathlib, textwrap, typing.cast, collections.abc, ExitCode, PytestPluginManager, MonkeyPatch, symlink_or_skip, Pytester, TempPathFactory, pytest) and the mypy pragma; no behavior of its own.

<a id="u-c363f51a86dd"></a>
### `conftest_setinitial`

`def conftest_setinitial( conftest: PytestPluginManager, args: Sequence[str | Path], c…` · [testing/test_conftest.py:L26-L40][f1]

Wraps PytestPluginManager._set_initial_conftests with fixed options: pyargs=False, noconftest=False, importmode='prepend', consider_namespace_packages=False, invocation_dir set to Path.cwd(), rootpath derived from args[0], and confcutdir passed through (may be None).

args accepts strings or Paths; args[0] is dereferenced unconditionally so an empty sequence fails. The actual collection behavior lives in _set_initial_conftests, external to this file.

**Notes.**

- contract: rootpath is Path(args[0]), so args must be non-empty.

**Uncertainties.**

- Error and fallback behavior of _set_initial_conftests is defined outside this file.

<a id="u-dc4cce9e6282"></a>
### `ConftestWithSetinitial`

`def ConftestWithSetinitial(path) -> PytestPluginManager:` · [testing/test_conftest.py:L20-L23][f1]

Creates a PytestPluginManager primed with a single initial conftest path and returns it.

It delegates priming to conftest_setinitial, so all fixed initialization options come from that helper; the manager is returned for callers to load or query conftest values.

calls: [conftest_setinitial](r5-conftest-tests.md#u-c363f51a86dd)

<a id="u-b1661a41ad83"></a>
### `test_conftest-TestConftestValueAccessGlobal`

`class TestConftestValueAccessGlobal:` · [testing/test_conftest.py:L43-L45][f1]

Verifies PytestPluginManager conftest loading and attribute lookup on a parametrized directory tree.

The module-scoped basedir fixture builds adir/conftest.py ('a=1 ; Directory = 3') and adir/b/conftest.py ('b=2 ; a = 1.5'); for the 'inpackage' param it adds __init__.py files to adir and adir/b. test_basic_init loads conftests for adir via _loadconftestmodules and asserts _rget_with_confmod('a', adir) returns value 1. test_immediate_initialization_and_incremental_are_the_same asserts _dirpath2confmods starts empty and grows by exactly one entry per newly loaded path (basedir, adir, then basedir/'b'). test_value_access_not_existing builds a manager only via ConftestWithSetinitial (no explicit load of adir) and expects KeyError from _rget_with_confmod('a', basedir). test_value_access_by_path shows lookup is path-dependent: 'a' resolves to 1 at adir, but after also loading adir/b it resolves to 1.5 there. test_value_access_with_confmod starts at adir/b/xx, asserting value 1.5 and that the returned module's __file__ has parent adir/b and stem 'conftest'. test_conftest_in_nonpkg_with_init constructs an equivalent tree with __init__.py files and only instantiates via ConftestWithSetinitial, exercising loading without assertions.

**Uncertainties.**

- Caching and search semantics of _loadconftestmodules/_rget_with_confmod are implemented outside this file.
- Whether the KeyError path searches upward from basedir and finds nothing, or fails earlier, is not visible here.

<a id="u-3cd50452d915"></a>
### `test_conftest-initial-conftest-collection`

`def test_doubledash_considered(pytester: Pytester) -> None:` · [testing/test_conftest.py:L145-L151][f1]

Tests which conftest.py files initial collection considers.

test_doubledash_considered creates a directory literally named '--option' containing a conftest.py and asserts _getconftestmodules finds exactly one module for it even when the name is passed twice to conftest_setinitial, guarding against the name being treated as a flag. test_issue151_load_all_conftests creates sibling dirs 'code', 'proj', 'src', each with a conftest.py, primes a manager with all three names, and asserts the plugin set minus the manager itself has three plugins. test_conftestcutdir: with confcutdir set to pytester.path/'x', conftests at the pytester root are neither loaded nor registered (has_plugin False, module lists empty), yet a direct _importconftest call still imports the root conftest; afterwards subdirectory lookups return that module whose __file__ starts with the conftest path. test_conftestcutdir_inplace_considered shows that when confcutdir equals the conftest's own directory, the conftest is loaded (one module, __file__ under the conf path). test_setinitial_conftest_subdirs is parametrized over subdir names 'test', 'tests', 'whatever', '.dotdir': for the first two, a conftest in the subdir is registered (one plugin besides the manager); for 'whatever' and '.dotdir' it is not (zero extra plugins), showing initial conftest collection skips those directory names.

<a id="u-7a78c4dae4ed"></a>
### `test_conftest-cli-loading-behavior`

`def test_conftest_global_import(pytester: Pytester) -> None:` · [testing/test_conftest.py:L165-L199][f1]

End-to-end tests of conftest loading driven through pytester subprocess/inprocess runs.

test_conftest_global_import runs a Python script that uses _importconftest directly and asserts the imported module matches the sys.modules 'conftest' entry after each import — first the root conftest (x==3), then a subdir conftest (y==4, a different module object) — exit code must be 0. test_conftest_confcutdir puts 'assert 0' in the root conftest and a valid pytest_addoption in x/conftest.py; running '-h --confcutdir=x x' shows the --xyz option and no 'could not load initial' warning, proving confcutdir prevented loading the failing root conftest. test_installed_conftest_is_picked_up simulates site-packages in tmp_path with a foo package containing conftest.py and a test using its fixture; running with '--pyargs foo' must exit 0 (regression #9767). test_conftest_symlink builds /real with a fixture-providing conftest and symlinks symlinktests->real/app/tests and symlink->real: running via the file-level symlink fails with "fixture 'fixture' not found" and ExitCode.TESTS_FAILED, while running via the directory symlink succeeds and does not raise 'Plugin already registered' (#4174). test_conftest_symlink_files symlinks individual files (not directories) into a build dir, chdirs there, and expects 'conftest_loaded' plus PASSED and ExitCode.OK. test_conftest_badcase (skipped on case-sensitive filesystems) creates JenkinsRoot/test files, chdirs to lowercase 'jenkinsroot/test', and expects ExitCode.NO_TESTS_COLLECTED, i.e. the conftest is still found (#5792). test_conftest_uppercase exercises a conftest whose qualified name contains uppercase (Foo/conftest.py) and expects NO_TESTS_COLLECTED rather than an import failure (#5819). test_no_conftest: root conftest 'assert 0'; running with --noconftest collects nothing (NO_TESTS_COLLECTED); running without it yields USAGE_ERROR. test_conftest_existing_junitxml shows a pre-existing junit.xml does not block conftest option registration: '-h --junitxml junit.xml' still lists --xyz.

<a id="u-e496fbac762c"></a>
### `test_conftest_import_order`

`def test_conftest_import_order(pytester: Pytester, monkeypatch: MonkeyPatch) -> None:` · [testing/test_conftest.py:L443-L449][f1]

Verifies that _loadconftestmodules loads conftest files in root-first order.

A root conftest is made via makeconftest and a second one in 'sub'. The helper impct simply returns its path argument, and monkeypatch replaces _importconftest with it, so _getconftestmodules returns paths rather than modules (cast to list[Path]). _confcutdir is set directly to pytester.path. After loading for 'sub', the assertion requires [root conftest, sub conftest] in that order.

<a id="u-d47ad97eb74f"></a>
### `test_conftest-fixture-and-nodeid`

`def test_fixture_dependency(pytester: Pytester) -> None:` · [testing/test_conftest.py:L466-L510][f1]

Tests fixture resolution and conftest lookup by node id.

test_fixture_dependency builds a package tree where sub/conftest.py defines bar(foo) (both would fail if instantiated) and sub/subsub/test_bar.py overrides bar locally; running pytest on 'sub' must report '1 passed', showing the test uses only the local bar and never invokes the conftest fixtures. test_conftest_found_with_double_dash defines --hello-world in sub/conftest.py and runs help for 'sub/test_hello.py::test_hello' as a string argument plus '-h'; the help output must include --hello-world, proving conftest lookup works for node-id arguments containing '::'.

<a id="u-ee1f9fd06d39"></a>
### `test_conftest-TestConftestVisibility`

`class TestConftestVisibility:` · [testing/test_conftest.py:L534-L535][f1]

Checks conftest visibility for relative node ids across a fixed directory tree (issue #616).

_setup_tree creates: empty/ (runner dir), package/ with a conftest defining fixture fxtr='from-package' and test_pkgroot.py, package/swc (a package with its own conftest returning 'from-swc' and test_with_conftest.py), and package/snc (a package without local conftest whose test asserts it gets 'from-package'); it returns a dict mapping these role names to Paths. test_parsefactories_relative_node_ids is parametrized with 16 (chdir, testarg, expected-passes) combinations covering four effective targets: from anywhere resolving to package/.. three tests pass; targeting package three pass; targeting package/swc exactly one passes (the swc test, using the local fixture); targeting package/snc one passes. Each run chdirs into the given directory, then pytester.inline_run runs the relative argument with -q --traceconfig --confcutdir pytester.path, and reprec.assertoutcome checks the expected pass count.

<a id="u-ae73cfbc1eac"></a>
### `test_search_conftest_up_to_inifile`

`def test_search_conftest_up_to_inifile( pytester: Pytester, confcutdir: str, passed: …` · [testing/test_conftest.py:L651-L705][f1]

Verifies conftest collection stops at an ini file unless --confcutdir is explicit.

The tree has src/pytest.ini, src/conftest.py defining fix1, src/test_foo.py using fix1 and out_of_reach, and a root conftest.py defining out_of_reach. Parametrized: confcutdir='.' expects 2 passed, 0 errors (root conftest loaded, both tests run); confcutdir='src' expects 1 passed, 1 error (out_of_reach missing); confcutdir=None expects 1 passed, 1 error (search stops at src/pytest.ini, so root conftest is not loaded). The expected stdout patterns are built from the parametrization.

<a id="u-9e16d2b62934"></a>
### `test_conftest-conftest-error-and-hook-tests`

`def test_issue1073_conftest_special_objects(pytester: Pytester) -> None:` · [testing/test_conftest.py:L708-L725][f1]

Tests edge behaviors of conftest loading.

test_issue1073_conftest_special_objects defines a conftest global whose class raises on any __getattr__; a plain test run must exit 0, i.e. plugin registration must not probe arbitrary attributes of conftest objects. test_conftest_exception_handling raises ValueError at conftest import time: the run must return exit code 4 and stderr must contain the 'raise ValueError()' source line, so the original source context is preserved in the reported error. test_hook_proxy (regression #2016) creates root/demo-a with a conftest whose pytest_ignore_collect returns True alongside sibling dirs; a full run must collect test_foo1, test_foo3, test_foo4 (3 passed), proving session hook proxies do not cache conftests incorrectly. test_required_option_help: root conftest 'assert 0', but x/conftest.py adds required option --xyz; running '-h x' must not print 'argument --xyz is required' and output must contain a 'general:' section, i.e. help rendering succeeds with confcutdir handling skipping the failing root conftest.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_conftest.py
