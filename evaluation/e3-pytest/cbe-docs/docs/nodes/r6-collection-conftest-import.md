# Conftest, Packages and Import Modes

**Capability.** Tests conftest-driven collection (ignore lists, initial conftests, fixture scoping across sibling conftests), __init__.py/package collection rules, importlib mode, namespace packages, deferred annotations, and sys.path non-pollution.

Use it when changing conftest loading, package detection or import modes. Many tests run pytest in subprocesses to observe sys.path and import side effects.

**Depends on.**

- [Test Run Invocation](r6-pytester-run.md) · graph-confirmed · 38 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 42 edge(s)

Parent: [Collection Suite](r6-test-collection.md)

## Units (15)

<a id="u-90468f73c3ba"></a>
### `TestCustomConftests`

`class TestCustomConftests:` · [testing/test_collection.py:L367-L368][f1]

Conftest-provided collection hooks.

test_ignore_collect_path uses pytest_ignore_collect returning True for names starting with 'x' and for test_one.py, so syntax-error files in ignored paths leave a clean 1-passed --fulltrace run. test_ignore_collect_not_called_on_argument shows a blanket pytest_ignore_collect returning True does not veto a path given explicitly on the command line (1 passed) but yields NO_TESTS_COLLECTED argument-less. test_collectignore_exclude_on_option and test_collectignoreglob_exclude_on_option define conftest collect_ignore / collect_ignore_glob lists (including a custom __fspath__ object) clearable from pytest_configure when a --XX flag is passed: without --XX nothing is collected, with it all tests pass. test_pytest_fs_collect_hooks_are_seen shows a conftest pytest_collect_file returning MyModule surfaces in --co output. test_pytest_collect_file_from_sister_dir places distinct conftests in sub1/sub2 and asserts both MyModule1 and MyModule2 collectors are used for copied test files.

<a id="u-7328dfb1a3ad"></a>
### `TestImportModeImportlib`

`class TestImportModeImportlib:` · [testing/test_collection.py:L1625-L1626][f1]

--import-mode=importlib semantics.

test_collect_duplicate_names shows identically named test_foo.py files in tests_a and tests_b both import and pass under importlib. test_conftest shows directories containing conftest modules are not added to sys.path as an import side effect. setup_conftest_and_foo creates tests/ with conftest.py, foo.py (returning 42), and a test importing foo. test_modules_importable_as_side_effect shows --import-mode=prepend makes foo importable (1 passed), while test_modules_not_importable_as_side_effect shows importlib does not, with ModuleNotFoundError for 'foo' and 1 failed. test_using_python_path configures pythonpath=. with importlib and asserts a real package import (tests.subpath.helper) works, i.e. dummy modules created by insert_missing_modules do not shadow importable modules (#9645).

<a id="u-e16d5603ce44"></a>
### `ensure_file`

`def ensure_file(file_path: Path) -> Path:` · [testing/test_collection.py:L26-L30][f1]

Creates the file at the given path including missing parent directories and returns the path.

Uses mkdir(parents=True, exist_ok=True) and touch(exist_ok=True), so repeated calls are idempotent and existing content is untouched; OS errors propagate.

<a id="u-d891c6dc2714"></a>
### `test_collectignore_via_conftest`

`def test_collectignore_via_conftest(pytester: Pytester) -> None:` · [testing/test_collection.py:L1457-L1472][f1]

collect_ignore in a package's conftest skips importing the ignored subpackage (#4592): tests/ignore_me contains a conftest that would assert-fail on import, but the run yields NO_TESTS_COLLECTED, proving the child conftest was never imported.

<a id="u-030d58283481"></a>
### `test_does_not_eagerly_collect_packages`

`def test_does_not_eagerly_collect_packages(pytester: Pytester) -> None:` · [testing/test_collection.py:L1568-L1573][f1]

Packages are not collected eagerly: a foopkg whose __init__.py contains 'assert False' does not break a rootdir run; the run exits OK because the package is only imported when its directory is actually collected.

<a id="u-a9a156c82cdc"></a>
### `test_does_not_put_src_on_path`

`def test_does_not_put_src_on_path(pytester: Pytester) -> None: # src is not on sys.…` · [testing/test_collection.py:L1576-L1586][f1]

A src/nope package exists in the rootdir but is not added to sys.path, so a test asserting 'import nope' raises ImportError passes, exit OK.

<a id="u-2968491abc87"></a>
### `test_namespace_packages`

`def test_namespace_packages(pytester: Pytester, import_mode: str):` · [testing/test_collection.py:L1940-L1998][f1]

Parametrized over prepend, importlib, and append with consider_namespace_packages=true, pythonpath=., and python_files=*.py.

A pkg tree holds module1.py, namespace subpkg (no __init__.py) with module2.py, and regular subpkg with __init__.py and module3. --pyargs on 'pkg' collects 3 items with the expected tree (namespace dirs shown as <Dir>, regular as <Package>); targeting pkg.subpkg_namespace or pkg.subpkg_regular collects exactly that subpackage's 1 item each, showing namespace-package collection works at any specificity.

<a id="u-6465b4368e81"></a>
### `test_annotations_deferred_314`

`def test_annotations_deferred_314(pytester: Pytester):` · [testing/test_collection.py:L1919-L1937][f1]

On Python 3.14+ (skipped below), annotation evaluation is deferred natively, so a fixture annotated with undefined X collects fine and the run passes with exit 0.

<a id="u-a6e830320940"></a>
### `test_annotations_deferred_future`

`def test_annotations_deferred_future(pytester: Pytester):` · [testing/test_collection.py:L1900-L1916][f1]

A fixture annotated with undefined return type X under 'from __future__ import annotations' must not error: stringified annotations are never evaluated eagerly, so the run passes test_func with exit 0.

<a id="u-46e25776d24f"></a>
### `test_fixture_scope_sibling_conftests`

`def test_fixture_scope_sibling_conftests(pytester: Pytester) -> None:` · [testing/test_collection.py:L1133-L1166][f1]

Tests in package 'food' must not see a fixture defined in sibling non-package directory 'foo': the food test errors at setup with "fixture 'fix' not found" while the foo test passes, yielding exit code 1 and '1 passed, 1 error' (regression #2836).

<a id="u-ad7e883e1ef1"></a>
### `test_initial_conftests_with_testpaths`

`def test_initial_conftests_with_testpaths(pytester: Pytester) -> None:` · [testing/test_collection.py:L1354-L1382][f1]

testpaths entries are loaded as initial conftests when no command-line args are given: the conftest's sessionstart hook raises, producing INTERNALERROR and exit code INTERNAL_ERROR.

With an explicit '.' argument, testpaths is not used, the conftest is not loaded, and the run yields NO_TESTS_COLLECTED (#10987).

<a id="u-1666df22ccbe"></a>
### `test_large_option_breaks_initial_conftests`

`def test_large_option_breaks_initial_conftests(pytester: Pytester) -> None:` · [testing/test_collection.py:L1385-L1401][f1]

A ~1 MB command-line option value (--xx=xxx...) must not break initial conftest handling: the conftest registers the option and the test asserts the received value equals the long string, with exit code 0 (#10169).

<a id="u-f460bc270d18"></a>
### `test_collect_init_tests`

`def test_collect_init_tests(pytester: Pytester) -> None:` · [testing/test_collection.py:L1169-L1241][f1]

Collection from __init__.py when it matches python_files.

After copying the example, --collect-only on the path, './tests', './tests .', and '. ./tests' all report the same 2 items (Package tests containing Module __init__.py with test_init and Module test_foo.py with test_foo), showing duplicate args are not double-collected. Passing only ./tests/test_foo.py excludes test_init; passing only ./tests/__init__.py excludes test_foo.

<a id="u-db44385815e3"></a>
### `test_collect_pkg_init_and_file_in_args`

`def test_collect_pkg_init_and_file_in_args(pytester: Pytester) -> None:` · [testing/test_collection.py:L1475-L1509][f1]

For a sub package with a test inside __init__.py and one in test_file.py: passing the package directory filters out __init__.py (1 passed); passing both file paths explicitly includes the init test (2 passed); passing the directory with -o python_files=*.py also includes it (2 passed).

<a id="u-69ed28e4971f"></a>
### `test_collect_pkg_init_only`

`def test_collect_pkg_init_only(pytester: Pytester) -> None:` · [testing/test_collection.py:L1512-L1524][f1]

A package directory whose only test is in __init__.py collects nothing by default ('no tests ran'); passing __init__.py explicitly runs its test, and so does the directory with -o python_files=*.py.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_collection.py
