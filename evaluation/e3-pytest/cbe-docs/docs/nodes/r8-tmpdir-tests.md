# tmpdir and pathlib Helper Tests

**Capability.** testing/test_tmpdir.py verifies the tmpdir subsystem end to end (fixtures, basetemp handling, retention policy) and the numbered-dir/rm_rf helpers it relies on, using FakeConfig to build TempPathFactory. The example script tmp_path_fixture.py checks the fixture against hostile directory names.

Read this to see expected behavior of numbered directories, cleanup, permissions, and mktemp basename validation. These tests call directly into TempPathFactory.getbasetemp/mktemp.

**Depends on.**

- [Temporary Directory Management](r8-tmp-path-management.md) · containment · → 1 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r8-tmpdir-tests ` → ` r8-tmp-path-management `)

Parent: [Temporary Directory Management](r8-tmp-path-management.md)

## Units (10)

<a id="u-e0615c2e893f"></a>
### `test_tmpdir-py-fixture-and-user-tests`

`def test_tmp_path_fixture(pytester: Pytester) -> None:` · [testing/test_tmpdir.py:L29-L32][f1]

Module-level tests of the tmp_path fixture and user resolution.

test_tmp_path_fixture runs an example file via copy_example and expects one pass. test_mktemp is parametrized over basenames: 'safe' relative names succeed (directory created under --basetemp), while absolute, '..', or parent-traversing names fail with exit code 1 and a ValueError in output. test_tmp_path_always_is_realpath creates a real dir plus a symlink to it, points PYTEST_DEBUG_TEMPROOT at the symlink, and asserts tmp_path.resolve() equals tmp_path inside a test. test_tmp_path_too_long_on_parametrization and test_tmp_path_factory assert a 1000-char parametrize id and a session-scoped mktemp both pass. test_tmp_path_fallback_tox_env deletes USER/USERNAME and expects tmp_path to still work (getpass fallback, #1010). break_getuser is a fixture patching os.getuid to -1 and deleting LOGNAME/USER/LNAME/USERNAME; test_tmp_path_fallback_uid_not_found and test_get_user_uid_not_found (unix-only) use it to assert tmp_path works and get_user() returns None when the uid is unknown; test_get_user (windows-only) asserts get_user() is None without USER/USERNAME env vars.

calls: [MonkeyPatch.delenv](r6-monkeypatch-engine.md#u-7e894007c213), [MonkeyPatch.setenv](r6-monkeypatch-engine.md#u-3bcdaba77d61), [Pytester.copy_example](r6-pytester-core.md#u-c15c0894e320), [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d); uses: [method::get_user::unknown][f2]

**Uncertainties.**

- The inventory does not provide an id for _pytest.tmpdir.get_user, so the exact target of the get_user() calls is stated from the import line only.

<a id="u-4f0fd2e6e574"></a>
### `test_tmpdir-py-removal-and-permissions`

`def attempt_symlink_to(path, to_path):` · [testing/test_tmpdir.py:L542-L548][f1]

Symlink helper plus integration tests for basetemp cleanup and permissions.

attempt_symlink_to creates a symlink and pytest.skips on OSError (unsupported platforms or missing privileges on Windows). test_basetemp_with_read_only_files (#5524) runs a test twice with --basetemp=tmp where the test strips read permission bits from a file; both runs exit 0, proving basetemp reuse does not crash on read-only leftovers. test_tmp_path_factory_handles_invalid_dir_characters patches getpass.getuser to a name full of invalid path characters ('os/<:*?;>agnostic'), resets the factory's cached _basetemp/_given_basetemp, and asserts getbasetemp() falls back to a 'pytest-of-unknown' directory. test_tmp_path_factory_create_directory_with_safe_permissions (unix-only) points PYTEST_DEBUG_TEMPROOT at the test's tmp_path, builds a TempPathFactory, and asserts both basetemp and its pytest-of- parent have no group/other permission bits. test_tmp_path_factory_fixes_up_world_readable_permissions chmods the pytest-of- parent to 0o777, then constructs a fresh factory and asserts the permissions were tightened back to private.

calls: [MonkeyPatch.setenv](r6-monkeypatch-engine.md#u-3bcdaba77d61), [src/_pytest/monkeypatch.py:MonkeyPatch.setattr (2)](r6-monkeypatch-engine.md#u-7e3e8acd6062), [TempPathFactory.getbasetemp](r8-tmp-path-management.md#u-9bff6cf31e64), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-1c4b0ab522b6"></a>
### `testing/test_tmpdir.py:FakeConfig`

`class FakeConfig:` · [testing/test_tmpdir.py:L35-L39][f1]

A dataclass stub standing in for Config when constructing TempPathFactory.from_config in tests.

It holds basetemp; trace and option are self-returning properties; get(key) returns a function absorbing any arguments and returning None; getini returns 3 for 'tmp_path_retention_count', 'all' for 'tmp_path_retention_policy', and asserts False for any other name. It exists only so cast(Config, FakeConfig(...)) satisfies the factory constructor with deterministic ini values.

<a id="u-4a3442ec2def"></a>
### `TestConfigTmpPath`

`class TestConfigTmpPath:` · [testing/test_tmpdir.py:L81-L82][f1]

Integration tests for tmp_path basetemp handling and the tmp_path_retention_policy ini option, run via pytester inline runs.

test_getbasetemp_custom_removes_old runs a test twice with --basetemp pointing at a prepared directory and asserts the second run wipes pre-existing content (a touched 'hello' file) while keeping the directory. The 'failed'-policy tests: with policy=failed, test_policy_failed_removes_only_passed_dir asserts only the failing test's directory (test_20) survives per root child; test_policy_failed_removes_basedir_when_all_passed asserts the whole base directory is removed when every test passes (ignoring atexit-deleted symlinks); test_policy_failed_removes_dir_when_skipped_from_fixture (issue #10502) asserts a skip raised inside the tmp_path fixture still removes the directory under the failed policy. test_policy_all_keeps_dir_when_skipped_from_fixture asserts the same skip scenario keeps the directory under the 'all' policy. All retention tests inspect pytester._test_tmproot children, filtering to real (non-symlink) directories.

**Uncertainties.**

- The tests rely on pytester._test_tmproot, an attribute whose setup is not visible in this file.

<a id="u-3ee1b904486c"></a>
### `TestNumberedDir`

`class TestNumberedDir:` · [testing/test_tmpdir.py:L370-L373][f1]

Tests numbered-directory helpers from _pytest.pathlib using the 'fun-' prefix.

test_make shows make_numbered_dir assigns sequentially suffixed names (fun-0..fun-9) and, on unix, maintains a 'fun-current' symlink resolving to the newest dir. test_cleanup_lock_create shows a second create_cleanup_lock in the same directory raises OSError ('cannot create lockfile'). test_lock_register_cleanup_removal registers the lock-removal callback into a list and verifies: with a different original_pid argument the lock survives; a no-arg call removes it; a repeat call is harmless. _do_cleanup runs test_make then cleanup_numbered_dir with a given keep count. test_cleanup_keep asserts two non-symlink dirs remain with keep=2; test_cleanup_keep_0 asserts nothing remains with keep=0. test_cleanup_locked verifies ensure_deletable is false when the lock is newer than the dead-lock threshold and true when older. test_cleanup_ignores_symlink verifies the 'current' symlink is not treated as deletable content. test_removal_accepts_lock shows maybe_delete_a_numbered_dir leaves a locked folder in place.

imports: [src/_pytest/pathlib](../../catalog.json)

<a id="u-349d070adf53"></a>
### `TestRmRf`

`class TestRmRf:` · [testing/test_tmpdir.py:L459-L460][f1]

Tests the rm_rf helper and the on_rm_rf_error error handler.

test_rm_rf removes an empty then a file-containing directory. chmod_r clears the owner-write bit on a path. test_rm_rf_with_read_only_file and test_rm_rf_with_read_only_directory (#5524) verify rm_rf succeeds on a read-only file and on a directory made read-only via chmod_r. test_on_rm_rf_error exercises the handler's branch behavior directly: an unknown exception type (RuntimeError) triggers a PytestWarning and leaves the file; FileNotFoundError yields a falsy return (ignored); an unknown function (None) with PermissionError warns with the specific '(rm_rf) unknown function None when removing' message and leaves the file; os.open with PermissionError is silently ignored (no warning recorded); os.unlink with PermissionError performs the retry and deletes the file.

**Uncertainties.**

- Exact semantics of on_rm_rf_error's ignore list are inferred from the asserted outcomes, not from its source.

<a id="u-71f9f69f3362"></a>
### `TestTmpPathHandler`

`class TestTmpPathHandler:` · [testing/test_tmpdir.py:L59-L60][f1]

Tests TempPathFactory built from FakeConfig.

test_mktemp creates a factory over a tmp_path basetemp and verifies mktemp('world') yields 'world0' relative to basetemp, repeated mktemp('this') calls yield distinct directories whose relative paths start with 'this'. test_tmppath_relative_basetemp_absolute (issue #4425) chdirs to tmp_path, passes the relative string 'hello' as basetemp, and asserts getbasetemp() resolves to tmp_path/hello, i.e. relative basetemp paths are interpreted against the current working directory.

calls: [MonkeyPatch.chdir](r6-monkeypatch-engine.md#u-50a6dcd4ac47)

<a id="u-ed4471fb272c"></a>
### `test_tmpdir.py module code (L1–L28)`

`module_region` · [testing/test_tmpdir.py:L1-L28][f1]

Module header: mypy pragma, __future__ annotations, and imports (dataclasses, os, pathlib, stat, sys, typing.cast, warnings, _pytest modules, pytest).

<a id="u-f828a6336db5"></a>
### `test_tmpdir.py module code (L226–L240)`

`module_region` · [testing/test_tmpdir.py:L226-L240][f1]

Module-level testdata constant: a parametrization list of (basename, is_ok) pairs used by test_mktemp to classify safe versus path-traversing/absolute mktemp basenames.

<a id="u-182f7d14659d"></a>
### `tmp_path_fixture-py`

`def test_fixture(tmp_path, a):` · [testing/example_scripts/tmpdir/tmp_path_fixture.py:L7-L10][f3]

Verifies the tmp_path fixture against a parametrized name containing a backslash and slash (r"qwe/\abc").

test_fixture asserts tmp_path is a directory and that its listing is empty. The parametrization checks that such a name does not leak into the temporary directory contents.

**Uncertainties.**

- Whether the parametrized id string containing path separators is legal for all pytest id handling is the boundary this example probes; not decidable here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_tmpdir.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/tmpdir.py
[f3]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/tmpdir/tmp_path_fixture.py
