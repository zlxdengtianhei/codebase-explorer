# pathlib and Import Mechanism Tests

**Capability.** testing/test_pathlib.py verifies pytest's path utilities (fnmatch_ex, scandir-tolerant helpers) and the import_path machinery across import modes, namespace packages, sys.modules parent registration, and samefile false negatives; an autouse pytester fixture keeps sys.path mutations isolated.

Read this for the contract of import_path and --import-mode=importlib. The import-path group exercises TempPathFactory.mktemp for sandbox fixtures.

**Depends on.**

- [Temporary Directory Management](r8-tmp-path-management.md) · graph-confirmed · 1 edge(s)

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Units (11)

<a id="u-7301bee28452"></a>
### `test_pathlib.py-fnmatcher`

`class TestFNMatcherPort:` · [testing/test_pathlib.py:L65-L75][f1]

Tests the pytest port of py.common.FNMatcher (fnmatch_ex).

Drive prefixes are platform-dependent class attributes: 'c:'/'d:' on win32, '/c'/'/d' elsewhere. test_matching asserts positives across plain globs, directory prefixes, drive-prefixed patterns, and recursive '**' patterns; test_not_matching asserts the mirror negatives, including drive mismatch and cases where '**' still requires a directory component. test_matching_abspath asserts a relative pattern 'tests/foo.py' matches the absolute path of that same location.

imports: [test_pathlib.py module code (L1–L50)][f1]

<a id="u-79ed4c4a78a0"></a>
### `test_pathlib.py-import-path`

`class TestImportPath:` · [testing/test_pathlib.py:L123-L131][f1]

Tests import_path, pytest's pyimport-like function, mostly ported from the py lib.

Fixture infrastructure: session-scoped path1 builds a temp tree via setuptestfs (execfile.py with x=42, a pickled dict, sampledir without __init__.py, and package otherdir containing a.py importing .b, b.py, c.py doing 'import otherdir.a', d.py doing 'from otherdir import a'); teardown asserts samplefile still exists. preserve_sys snapshots sys.modules and sys.path around every test, and ns_param runs each test with consider_namespace_packages True and False. Asserted behavior: importing execfile.py yields x==42 with __name__ 'execfile'; importing a directory lacking __init__.py (sampledir) raises ImportPathMismatchError; foo__init__.py imports under the plain name 'foo__init__'; a directory with __init__.py imports as the package name via both the directory and the __init__.py path; relative imports in otherdir resolve (result/stuff/value/value2 == 'got it') with names 'otherdir.a'/'otherdir.b'; after importing xxxpackage/module1.py the object is identical to the one from a normal 'from xxxpackage import module1'; mode='append' places the file's root exactly once at sys.path's end; a nonexistent path raises ImportError. test_renamed_dir_creates_mismatch: after importing a/test_x123.py, renaming a to b makes re-import raise ImportPathMismatchError; env PY_IGNORE_IMPORTMISMATCH=1 suppresses the error so the import succeeds, while PY_IGNORE_IMPORTMISMATCH=0 re-raises. test_check_filepath_consistency: a cached sys.modules entry whose __file__ ends in .pyc/.pyo re-imports and compares equal; when __file__ points at a different .py file, import_path raises ImportPathMismatchError with args (module name, cached file string, original path), and the error subclasses ImportError. importlib-mode tests: a nested _src/tests module imports without touching sys.path, registering synthetic parents '_src' and '_src.tests' in sys.modules; a second call returns the identical cached module; with sys.meta_path emptied the import still works, but after deleting the module from sys.modules and patching importlib.util.spec_from_file_location to return None, import_path raises ImportError. simple_module writes 'def foo(x): return 40 + x' under _src/tests and pops the generated module name from sys.modules on teardown.

uses: [ns_param](r8-pathlib-tests.md#u-e50cbd44dff8), [test_pathlib.py-import-path](r8-pathlib-tests.md#u-79ed4c4a78a0)

**Uncertainties.**

- Whether c.py and d.py's 'import pluggy' requires pluggy installed at runtime is not verifiable from this file.

<a id="u-285a02a59b39"></a>
### `test_pathlib.py-importlib-mode`

`class TestImportLibMode:` · [testing/test_pathlib.py:L596-L597][f1]

Exercises --import-mode=importlib semantics end to end.

ns_param makes most tests run with consider_namespace_packages True and False. Dataclass/pickle tests: a module defining a @dataclass imports and instantiates with correct __module__ '_src.tests.test_dataclass'; a module pickling its own function round-trips; two similarly named modules in _src/m1 and _src/m2 keep distinct Data classes whose pickles round-trip to their own class, with __module__ '_src.m1.tests.test' vs '_src.m2.tests.test'; in all cases a second import_path returns the identical module. test_module_name_from_path: 'src/tests/test_foo.py' under root gives 'src.tests.test_foo'; a path not under root uses the full path ('home.foo.test_foo'); __init__.py maps to the package name unless at the root, where it stays '__init__'; leading-dot components become '_' ('.env' -> '_env') and dots inside a directory name are replaced ('.env.310' -> '_env_310'). test_resolve_pkg_root_and_module_name: with no __init__.py files resolution raises CouldNotResolvePathError; after adding app and core __init__.py files, (tmp_path/src, 'app.core.models') is returned; once tmp_path is on sys.path the namespace resolution yields (tmp_path, 'src.app.core.models') with consider_namespace_packages=True, while False still returns (tmp_path/src, 'app.core.models'); validate_namespace_package confirms Python itself imports src.app.core.models. insert_missing_modules fills missing parent packages into a modules dict ('xxx', 'xxx.tests' for 'xxx.tests.foo'), leaves an existing entry alone, and handles an empty module name by inserting nothing; parents get attributes pointing at children (test_parent_contains_child_module_attribute). test_import_module_using_spec: _import_module_using_spec imports 'a.b.c.demo' from its file, registering namespace modules 'a' and 'a.b.c'; when a/b is a package its __init__.py executes (my_name='b.__init__', not a namespace), otherwise a.b is a namespace and accessing mod_b.my_name raises AttributeError; parents link to children. test_importlib_package: importing a package __init__.py twice returns the same module, and Singleton.__init__ raising on a second instance proves the init ran once. test_importlib_root_is_package: an __init__.py at the root imports fine under importlib mode (pytest run passes 1 test). test_importlib_same_name_as_stl: for names code/time/math, the stdlib module is imported first, then a namespace package of the same name is imported via import_path, and an end-to-end pytest run passes. create_installed_doctests_and_tests_dir builds src/app with a doctested core.py, copies it into a fake site-packages prepended to sys.path, and creates .tests/a and .tests/b conftest+test_core.py files with same names; returns (installed core.py, test_path1, test_path2). test_import_using_normal_mechanism_first: core_py reachable from sys.path imports as 'app.core' with __file__ equal to the installed path and is cached on re-import; tests unreachable from sys.path import as '_tests.a.test_core'/'_tests.b.test_core' (leading '.' replaced by '_' to avoid local-import semantics), each cached. test_import_using_normal_mechanism_first_integration reruns the same layout through pytester.runpytest with --import-mode=importlib, --doctest-modules and --pyargs, expecting each of the three files to pass (3 passed). test_import_path_imports_correct_file: a sys.path-reachable x.py that raises AssertionError is not imported when importing a/b/x.py (which imports as itself and is cached); importing the root x.py does raise the AssertionError.

uses: [ns_param](r8-pathlib-tests.md#u-e50cbd44dff8); calls: [test_pathlib.py-ns-misc](r8-pathlib-tests.md#u-ebee4f44e1da)

<a id="u-776129d8debc"></a>
### `test_pathlib.py-module-as-attribute`

`def test_import_sets_module_as_attribute(pytester: Pytester) -> None:` · [testing/test_pathlib.py:L1243-L1275][f1]

Regression tests for #12194: import_path must register parent modules in sys.modules and set attributes pointing at children.

test_import_sets_module_as_attribute: with foo/bar/baz packages each having __init__.py, importing foo/bar/baz/__init__.py yields module 'foo.bar.baz', sys.modules gains 'foo', 'foo.bar', 'foo.bar.baz', bar.baz is baz and foo.bar is bar; re-importing foo/bar/__init__.py returns the cached bar module. test_import_sets_module_as_attribute_without_init_files: the same holds for foo/bar/baz.py with no __init__.py files anywhere. test_import_sets_module_as_attribute_regression runs a user script doing 'import foo; from foo.bar import baz' via runpython (exit 0), then a full pytest run with --import-mode=importlib --doctest-modules also exiting 0. test_import_submodule_not_namespace: with package foo containing bar.py and a top-level sys.path directory named 'bar', importing foo then foo.bar binds both to the exact given file paths, proving the submodule is not shadowed into a namespace package by the same-named directory.

<a id="u-0b9db5e4b34e"></a>
### `test_pathlib.py-namespace-packages`

`class TestNamespacePackages:` · [testing/test_pathlib.py:L1376-L1379][f1]

Tests import_path support for true namespace packages.

Autouse fixture setup_imports_tracking sets sys.pytest_namespace_packages_test to a list; setup_directories writes each module with a guard snippet asserting its __name__ was not imported before (detecting double imports), then builds two distributions: src/dist1 with com.company.app (package __init__ files with the guard, core/models.py) and src/dist2 with com.company.calc (calc/__init__, algo/__init__, algo/algorithms.py); it validates via validate_namespace_package (ret 0) and, if monkeypatch is given, prepends both dist roots to sys.path, returning (models_py, algorithms_py). test_resolve_pkg_root_and_module_name_ns_multiple_levels across modes prepend/append/importlib: models_py resolves to (src/dist1, 'com.company.app.core.models') and imports with that name and __file__, re-import returning the same module; algorithms_py analogously to (src/dist2, 'com.company.calc.algo.algorithms'). test_ns_multiple_levels_import_rewrite_assertions: a failing test inside the namespace package under importlib mode produces properly rewritten assertion output ('four lights' vs 'five lights'). test_ns_multiple_levels_import_error: a package dir 'moo' containing both moo.py and test_moo.py (trigger conditions: same-named ns and file; tests inside ns) still runs the whole session with ExitCode.OK under importlib mode. test_incorrect_namespace_package across all three modes: adding src/dist1/com/__init__.py turns 'com' into a regular package; validate_namespace_package then fails with ret 1 and stderr matching "No module named 'com.company.calc", while models_py still resolves to (src/dist1, 'com.company.app.core.models') and algorithms_py now resolves to (src/dist2/com/company, 'calc.algo.algorithms'). test_detect_meta_path (regression #12112): without sys.path configuration resolution falls back to (src/dist1/com/company, 'app.core.models'); after inserting CustomImporter, a MetaPathFinder whose find_spec returns a namespace ModuleSpec 'com' with submodule_search_locations covering both dist com roots, resolution yields the full namespace answer (src/dist1, 'com.company.app.core.models'). test_full_ns_packages_without_init_files with insert True/False: an __init__.py deep inside (ns/b/app) does not break namespace detection; both dist modules validate (ret 0) and resolve to their dist roots with dotted names ns.b.app.bar.m and ns.a.core.foo.m.

calls: [test_pathlib.py-ns-misc](r8-pathlib-tests.md#u-ebee4f44e1da)

<a id="u-ebee4f44e1da"></a>
### `test_pathlib.py-ns-misc`

`def test_ns_import_same_name_directory_12592( tmp_path: Path, pytester: Pytester ) ->…` · [testing/test_pathlib.py:L1687-L1697][f1]

Standalone namespace/import helpers.

test_ns_import_same_name_directory_12592: with x/y/y created and x/y/test_y.py present, a pytest run with --import-mode=importlib exits OK despite parent and child directories sharing the name 'y'. test_is_importable: with pytester.path on sys.path, is_importable('bar.foo', path) is True when the module imports and points at the given path; False when an existing 'bar.foo' resolves to a different path; False for module names containing '.' in a component ('bar.x'); False for names starting with '.' (relative imports cannot be checked). test_compute_module_name: returns None when path equals root (including empty root); a direct child 'mod.py' becomes 'mod'; nested 'src/app/bar' and 'src/app/bar.py' become 'src.app.bar', and the package __init__.py yields the package name 'src.app.bar'. validate_namespace_package(pytester, paths, modules) builds a small script that imports sys, appends each path to sys.path via sys.path.append(r'<path>'), and imports each module name, then runs it via pytester.runpython_c and returns the RunResult used as a sanity check that the files form a valid namespace package from Python's perspective.

<a id="u-0472045f3fd8"></a>
### `test_pathlib.py-path-helpers`

`def test_resolve_package_path(tmp_path: Path) -> None:` · [testing/test_pathlib.py:L434-L441][f1]

Focused tests for small pathlib helpers.

resolve_package_path: with pkg1 containing __init__.py and subdir/__init__.py, both the package dir and its __init__.py resolve to pkg1; a directory having its own __init__.py (subdir) resolves to itself, its child xyz.py resolves to subdir, and a package dir itself yields a falsy result. Cleanup resilience: test_access_denied_during_cleanup patches Path.rename to raise OSError('access denied') via renamed_failed and asserts maybe_delete_a_numbered_dir still completes and the lock file is gone. test_long_path_during_cleanup creates a >260-character path (with the \\?\ extended-length prefix on Windows) and asserts maybe_delete_a_numbered_dir deletes it. get_extended_length_path_str maps drive paths to \\?\c:\..., UNC shares to \\?\UNC\..., and returns already-extended strings unchanged. test_suppress_error_removing_lock: with Path.unlink patched to raise OSError, ensure_deletable returns False after exactly one unlink call and keeps the lock file; with Path.is_file patched to raise OSError it also returns False after one call; unpatched it returns True and removes the lock. bestrelpath: same path gives '.', descendants give os.sep-joined relative paths, parents give '..' (per level), and an unrelated relative path is returned as-is. commonpath returns the shared ancestor in both argument orders, the parent when one path extends the other only by a suffix, and the shorter path when one contains the other. test_visit_ignores_errors walks a temp dir (symlink created via symlink_or_skip) with recurse returning False and expects sorted entries ['bar', 'foo'], i.e. recursion is not followed and errors are tolerated.

<a id="u-3f75dfccda0d"></a>
### `test_pathlib.py-scandir-safe-exists`

`def test_safe_exists(tmp_path: Path) -> None:` · [testing/test_pathlib.py:L1214-L1240][f1]

Tests tolerant directory inspection helpers.

scandir of a nonexistent directory returns an empty list rather than raising. When an entry's is_file raises OSError, scandir itself propagates the OSError (mocked to 'some permission error') after calling is_file exactly once, established with a patched os.scandir returning a MagicMock entry. safe_exists returns True for an existing dir and file; when Path.exists raises OSError (errno.ENAMETOOLONG) or ValueError it returns False instead of propagating, using narrowly scoped patches on a very long filename.

<a id="u-cd7bb3497607"></a>
### `test_pathlib.py-test-samefile-false-negatives`

`def test_samefile_false_negatives(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:` · [testing/test_pathlib.py:L551-L570][f1]

Windows-only test (skipif otherwise) verifying import_path does not raise ImportPathMismatchError when os.path.samefile is unreliable.

A module my_module.py is written into tmp_path, which is prepended to sys.path; inside a narrowed monkeypatch context os.path.samefile is forced to return False, import_path(consider_namespace_packages=False) still succeeds by comparing paths too, and calling the imported foo returns 42.

<a id="u-c2582df88d1d"></a>
### `autouse_pytester`

`def autouse_pytester(pytester: Pytester) -> None:` · [testing/test_pathlib.py:L51-L62][f1]

Makes the pytester fixture autouse for the whole module so sys.path is restored around every test; many tests here import modules and mutate sys.path, which would otherwise leak names like 'test' or 'test.conftest' into other test modules.

<a id="u-e50cbd44dff8"></a>
### `ns_param`

`def ns_param(request: pytest.FixtureRequest) -> bool:` · [testing/test_pathlib.py:L114-L120][f1]

Parametrized fixture (params True/False) returning bool(request.param).

Tests consuming it run twice, once with consider_namespace_packages True and once False, exercising import_path under both namespace-package settings.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_pathlib.py
