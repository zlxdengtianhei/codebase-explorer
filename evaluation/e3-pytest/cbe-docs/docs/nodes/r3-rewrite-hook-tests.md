# Import Hook & Cache Tests

**Capability.** Covers the assertion-rewrite import hook end to end: rewriting on import, filesystem/pyc interactions, cache-directory computation, mtime edge cases, early bailout via PathFinder.find_spec, and internal hook helpers.

Use this subtree for import-machinery behavior, all exercised through pytester sessions or direct helper calls. Regression classes pin docstring misdetection, subdirectory patterns, and infinite recursion on pyc writing.

**Depends on.**

- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 45 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-only · 29 edge(s)

**Depended on by.**

- [Rewriting & Explanations](r3-rewrite-core-tests.md) · model-inferred · 0 edge(s)

Parent: [Assertion Rewrite Test Suite](r3-assertrewrite-tests.md)

## Units (9)

<a id="u-84058861b183"></a>
### `test_assertrewrite.py-test-rewrite-on-import`

`class TestRewriteOnImport:` · [testing/test_assertrewrite.py:L996-L997][f1]

TestRewriteOnImport covers the assertion-rewrite import hook's interaction with the filesystem and import machinery, all through pytester sessions.

Verified behaviors: rewriting succeeds when __pycache__ is a plain file or read-only, and when the source directory is read-only (test_pycache_is_a_file, test_pycache_is_readonly, test_readonly, each restoring modes in finally where applicable); modules inside zip files are collected but yield NO_TESTS_COLLECTED (test_zipfile); importlib.resources file iteration works for a rewritten plugin package (test_load_resource_via_files_with_rewrite expects exactly __init__.py and the example dir); with PYTHONDONTWRITEBYTECODE set, __cached__ points to a nonexistent file and no cache dir exists (test_dont_write_bytecode, subprocess); an orphaned top-level .pyc without source is importable and rewritten (test_orphaned_pyc_file, which moves the __pycache__ pyc next to source when needed); cached pyc filenames embed the running pytest version (test_cached_pyc_includes_pytest_version, subprocess); with PYTHONOPTIMIZE=2 a .pyo-tagged cache is produced and a later run reuses/rebuilds producing ret 1 in the second phase (test_pyc_vs_pyo, skipped on pypy, uses make_numbered_dir basetemp); a package without __init__.py still imports (test_package, test_package_without__init__py); CRLF source files are rewritten (test_translate_newlines); registering an already-imported module warns 'Module already imported so cannot be rewritten' in a subprocess, and -W ignore suppresses it without errors (test_rewrite_warning, test_rewrite_warning_ignore); a module imported from conftest is still rewritten (test_rewrite_module_imported_from_conftest, subprocess); AssertionRewritingHook remembers rewritten modules so mark_rewrite on them emits no warnings (test_remember_rewritten_modules, monkeypatching _warn_already_imported and driving find_spec/exec_module directly); pytest_plugins chains and the PYTEST_PLUGINS env var produce no pytest-warning summary (test_rewrite_warning_using_pytest_plugins, ..._env_var, both subprocess after pytester.chdir).

**Uncertainties.**

- The hook internals these tests exercise live in _pytest.assertion.rewrite.

<a id="u-18aeb6420449"></a>
### `test_assertrewrite.py-early-rewrite-bailout`

`class TestEarlyRewriteBailout:` · [testing/test_assertrewrite.py:L1891-L1892][f1]

TestEarlyRewriteBailout verifies the hook skips PathFinder.find_spec for modules that cannot be rewritten.

Its hook fixture builds an AssertionRewritingHook with default fnpats ['test_*.py', '*_test.py'], monkeypatches _find_spec with a spy recording module names and delegating to importlib.machinery.PathFinder.find_spec, attaches a StubSession whose isinitpath checks a set of initial paths, and inserts the pytester dir on sys.path. test_basic shows conftest is always rewritten, files matching python_files are rewritten, 'bar' gets an early bail (find_spec returns None with no spy call), and a file added to initial paths is rewritten despite not matching patterns. test_pattern_contains_subdirectories shows that with a pattern containing 'tests/**.py' no early bailout happens: 'file' is found and the spy is called, since full-path matching requires find_spec. test_cwd_changed (skipped on Windows and Solaris) removes pathlib from sys.modules, prepends '' to sys.path, and runs a session where one test module changes the process cwd into a temporary directory before another test runs; the run passes, exercising path resolution after cwd changes.

**Uncertainties.**

- The bailout condition itself is implemented in AssertionRewritingHook.

<a id="u-752b69872bcb"></a>
### `test_assertrewrite.py-hook-details`

`class TestAssertionRewriteHookDetails:` · [testing/test_assertrewrite.py:L1288-L1289][f1]

TestAssertionRewriteHookDetails tests internal hook helpers directly or through pytester.

Behaviors verified: a test file can blank sys.meta_path and still run (test_sys_meta_path_munged); _write_pyc returns True on success and False when os.replace raises OSError, mocked via unittest.mock (test_write_pyc, building AssertionState from pytester.parseconfig and compiling a 'single' code object); when the AssertionRewritingHook loads a module, pkg_resources.resource_string still resolves package data (test_resources_provider_for_loader, subprocess, skipped without pkg_resources); _read_pyc on a truncated pyc returns None without raising (test_read_pyc, truncating 20 bytes off a py_compile output); a pyc written by _rewrite_test plus _write_pyc round-trips through _read_pyc (test_read_pyc_success); _read_pyc validates header fields one by one — good header passes, too-short data, bad magic, unsupported flags, mismatched mtime and mismatched size each return None (test_read_pyc_more_invalid, hand-building magic/flags/mtime/size plus marshal.dumps code and pinning source mtime via os.utime); reloading a module whose source changed on disk returns the same module object with updated code (test_reload_is_same_and_reloads, using python_files = *.py and rewrite_self overwriting __file__); and pkgutil.get_data works for a hook-loaded module (test_get_data_support, PEP 302 get_data).

**Uncertainties.**

- _read_pyc/_write_pyc/_rewrite_test internals are defined in _pytest.assertion.rewrite.

<a id="u-eadd1b8194da"></a>
### `test_assertrewrite.py-pycache-dir`

`class TestPyCacheDir:` · [testing/test_assertrewrite.py:L2250-L2251][f1]

TestPyCacheDir covers cache-directory computation.

test_get_cache_dir is parametrized over prefix/source pairs: with sys.pycache_prefix set (and PYTHONPYCACHEPREFIX removed), a Windows-style prefix 'c:/tmp/pycs' maps 'd:/projects/src/foo.py' to 'c:/tmp/pycs/projects/src', a POSIX prefix maps '/home/projects/src/foo.py' to '/tmp/pycs/home/projects/src', and with prefix None the source directory gains a '__pycache__' component; the result is compared as Path. test_sys_pycache_prefix_integration (skipped on Python 3.9 Windows per #9298) sets pycache_prefix and dont_write_bytecode False, runs a session with a rewritten test file and a normal imported package module, then asserts the test file's pyc exists under the pytest cache tag (PYC_TAIL) while bar/__init__.py's pyc uses the interpreter's implementation.cache_tag and standard '.pyc' suffix, both resolved via get_cache_dir.

<a id="u-0db2c3032d18"></a>
### `test_assertrewrite.py-issue11140`

`class TestIssue11140:` · [testing/test_assertrewrite.py:L2358-L2359][f1]

TestIssue11140 ensures a leading constant expression (0) in a test module is not mistaken for the module docstring during rewriting.

The test writes a module whose first statement is 0 followed by a passing test, runs pytest, and asserts ret == 0.

<a id="u-8f2bc3a71205"></a>
### `test_assertrewrite.py-test-issue2121`

`class TestIssue2121:` · [testing/test_assertrewrite.py:L1535-L1536][f1]

TestIssue2121 verifies that a python_files pattern containing subdirectories ('tests/**.py') still causes assertion rewriting of files in subdirectories.

The test writes tests/file.py with a failing assert, sets the ini pattern, runs pytest, and expects the rewritten explanation 'assert (1 + 1) == 3'.

<a id="u-3e9279362252"></a>
### `test_rewrite_infinite_recursion`

`def test_rewrite_infinite_recursion( pytester: Pytester, pytestconfig, monkeypatch ) …` · [testing/test_assertrewrite.py:L1857-L1873][f1]

Regression test guarding against infinite recursion when pyc writing triggers an import (#3506).

It inserts the pytester dir on sys.path, creates test_foo and test_bar, then monkeypatches the rewrite module's _write_pyc with spy_write_pyc, which records the call and, while writing, asserts that hook.find_spec('test_bar') is None — i.e. a nested import during pyc writing does not re-enter rewriting. It forces dont_write_bytecode False, drives AssertionRewritingHook.find_spec/exec_module for test_foo directly, and asserts exactly one pyc write occurred.

**Notes.**

- side_effect: Spy delegates to the original _write_pyc after the nested-import check.

**Uncertainties.**

- The s1 fragment merely defines the nested spy and final assertions; behavior is as described here.

<a id="u-308530935ee2"></a>
### `test_source_mtime_long_long`

`def test_source_mtime_long_long(pytester: Pytester, offset) -> None:` · [testing/test_assertrewrite.py:L1831-L1854][f1]

Parametrized regression test for source mtimes beyond 2038, skipped on 32-bit systems where the old struct.pack('<ll') overflowed.

For offset in [-1, +1] it writes a test file, sets its mtime to 2**32 + offset via os.utime (the +1 case also masks 0xFFFFFFFF), runs pytest and asserts ret == 0.

**Notes.**

- condition: Skipped via sys.maxsize <= 2**31 - 1 because 32-bit systems raise OverflowError.

<a id="u-f85e9dc0c892"></a>
### `test_try_makedirs`

`def test_try_makedirs(monkeypatch, tmp_path: Path) -> None:` · [testing/test_assertrewrite.py:L2205-L2218][f1]

Unit test for try_makedirs.

It first asserts creating a new directory succeeds and that a repeated call on an existing directory also returns True. It then monkeypatches os.makedirs with fake_mkdir, which asserts its first argument is a Path and raises a supplied exception. FileNotFoundError, NotADirectoryError, PermissionError, OSError(EROFS) and OSError(ENOSYS) each make try_makedirs return False, while an OSError with an unhandled errno (ECHILD) propagates and is caught with pytest.raises, asserting the errno is preserved.

**Uncertainties.**

- Which errnos try_makedirs swallows is inferred from this test's expectations; the implementation is in _pytest.assertion.rewrite.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_assertrewrite.py
