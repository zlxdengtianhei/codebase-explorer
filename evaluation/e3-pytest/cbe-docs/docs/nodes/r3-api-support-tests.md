# Stash, Legacy Path & Typing Tests

**Capability.** Tests pytest's supporting APIs: Stash's typed mapping protocol, the legacy path shims (LEGACY_PATH, fspath, Testdir, TempdirFactory), and mypy-only check functions asserting public API static typing.

Use this subtree for tests of infrastructure APIs rather than plugin behavior. typing_checks.py is never executed, only mypy-checked, so its units pin type contracts, not runtime behavior.

Parent: [Test-Suite Infrastructure](r3-test-infra.md)

## Units (3)

<a id="u-5eee6bc86353"></a>
### `test_stash`

`def test_stash() -> None:` · [testing/test_stash.py:L8-L69][f1]

Exercises Stash's full mapping protocol with typed StashKey instances.

len/bool reflect stored entries; __contains__, __getitem__, __setitem__, __getitem__ reassignment, and get with default behave per-key: distinct keys never see each other's values, and missing keys raise KeyError on read and delete, including after deletion. Values keep their static types (str + str, int + int compile cleanly). setdefault returns the existing value when present, otherwise stores and returns the default. Assigning an undeclared attribute on the Stash object itself raises AttributeError. Two Stash instances are independent: writes through one do not appear in the other for the same key, and a key unique to the second stash is absent from the first.

<a id="u-cd09f5c65901"></a>
### `test-legacypath-legacy-path-integration`

`def test_item_fspath(pytester: pytest.Pytester) -> None:` · [testing/test_legacypath.py:L13-L22][f2]

Tests the legacy path shims (LEGACY_PATH, fspath, Testdir, TempdirFactory) provided by _pytest.legacypath.

test_item_fspath checks that re-collecting an item by nodeid yields identical name, fspath and path. Testdir tests: testdir.test_tmproot behaves as a py.path directory; makefile treats its extension argument specially — a dotted 'foo.bar' silently becomes a file named '.foo.bar', None raises TypeError, and an empty string creates a file named after the test (test_testdir_makefile...). attempt_symlink_to skips the test with pytest.skip on OSError, which commonly happens on Windows without symlink privileges. TempdirFactory and TempPathFactory share the same base temp directory (str comparison) and mktemp creates existing directories. tmpdir equals tmp_path as a Path. test_tmpdir_always_is_realpath symlinks a temp dir and asserts that inside a run with --basetemp pointing at the symlink, os.path.realpath(tmpdir) == str(tmpdir), i.e. tmpdir is always the real path. cache.makedir creates a directory that can be removed. TopRequest on a function item exposes path/fspath matching the module collector; a session-scoped request raises AttributeError with 'path not available in session-scoped context' when fspath is accessed. test_addini_paths verifies pathlist ini values resolve relative to the ini file's parent in both .ini and pyproject.toml forms, unknown ini names raise ValueError, and --override-ini replaces pathlist values (output shows bar1.py/bar2.py). test_inifile_from_cmdline_main_hook confirms config.inifile is populated during pytest_cmdline_main in a subprocess run.

imports: [_pytest.legacypath](../../catalog.json); calls: [test-legacypath-legacy-path-integration](r3-api-support-tests.md#u-cd09f5c65901)

**Uncertainties.**

- Whether test_tmproot.check(dir=1) semantics differ across py.path versions is external to this file.
- The exact attribute set unavailable on session-scoped requests beyond fspath is not shown here.

<a id="u-f0ea91886e63"></a>
### `typing_checks.py-mypy-checks`

`def check_mark_xfail_raises() -> None:` · [testing/typing_checks.py:L22-L24][f3]

Type-only check functions: this file is never executed, only mypy-checked, so each function verifies that a public pytest API has the intended static typing.

check_mark_xfail_raises confirms @pytest.mark.xfail(raises=RuntimeError) type-checks (issue #7488). check_fixture_ids_callable confirms a fixture accepts callable ids (issue #7494). check_parametrize_ids_callable confirms parametrize accepts callable ids (issue #7494). check_monkeypatch_typeddict (issue #10999) uses a local TypedDict Foo and verifies monkeypatch.setitem/delitem accept TypedDict mappings. check_raises_is_a_context_manager verifies pytest.raises can be used as a context manager in a conditional expression, with excinfo typed Optional[pytest.ExceptionInfo[RuntimeError]]. check_testreport_attributes (issue #12941) pins TestReport.when to Literal['setup','call','teardown'] and location to tuple[str, Optional[int], str]. All bodies are no-ops or assert_type calls; no runtime behavior is asserted.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_stash.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/test_legacypath.py
[f3]: ../../../../../../eval/pytest-5989efe/testing/typing_checks.py
