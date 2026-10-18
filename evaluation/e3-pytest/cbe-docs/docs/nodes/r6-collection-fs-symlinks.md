# Filesystem Traversal and Symlinks

**Capability.** Tests directory recursion, ignore rules, and symlink handling: working/broken/recursive/out-of-tree symlinks, samefile siblings, chdir during import, --pyargs with testpaths, and Windows reproducers.

Use it when changing how the collector walks the filesystem or resolves paths. Expect chdir/setenv patching and subprocess runs for path-sensitive cases.

**Depends on.**

- [Patch Engine and Undo Journal](r6-monkeypatch-engine.md) · graph-confirmed · 5 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-confirmed · 17 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-confirmed · 25 edge(s)

Parent: [Collection Suite](r6-test-collection.md)

## Units (11)

<a id="u-46a7beba9d67"></a>
### `TestCollectFS`

`class TestCollectFS:` · [testing/test_collection.py:L137-L138][f1]

Filesystem recursion and ignore rules.

test_ignored_certain_directories plants test files under build, dist, _darcs, CVS, {arch} and dot-directories and asserts --collect-only skips them while a 'normal' directory is collected. test_ignored_virtualenvs (parametrized by the class attribute known_environment_types over pyvenv.cfg and conda-meta/history) shows venv tests are skipped by default but collected with --collect-in-virtualenv or when the venv directory is given explicitly. test_ignored_virtualenvs_norecursedirs_precedence shows norecursedirs beats --collect-in-virtualenv unless the venv path is also on the command line. test__in_venv calls _in_venv directly: False without an env marker file, True after creating one. test_custom_norecursedirs applies 'norecursedirs = mydir xyz*': inline run collects only xy's test; an explicit xyz123/test_2.py argument runs and fails. test_testpaths_ini with testpaths=*/tests collects only b and c at the rootdir; explicit directory args collect each directory's test; after chdir into a subdirectory, argument-less runs collect that directory. test_missing_permissions_on_unselected_directory_doesnt_crash chmods a directory to 0 (restored to 750 and removed in a finally) and asserts selecting another file still exits OK with 1 passed.

calls: [_pytest.main._in_venv](../../catalog.json)

**Uncertainties.**

- chmod(0) may be ineffective when running as root; the source has no guard

<a id="u-6dc9c295491c"></a>
### `test_collect_sub_with_symlinks`

`def test_collect_sub_with_symlinks(use_pkg: bool, pytester: Pytester) -> None:` · [testing/test_collection.py:L1527-L1548][f1]

Parametrized over presence of __init__.py: collection of sub works with a working symlink to test_file.py (collected as test_symlink.py) and tolerates a broken symlink pointing at a nonexistent file; both real and symlinked tests pass, 2 passed.

<a id="u-1c998027322c"></a>
### `test_collect_symlink_dir`

`def test_collect_symlink_dir(pytester: Pytester) -> None:` · [testing/test_collection.py:L1448-L1454][f1]

A symlinked directory is collected: creating symlink_dir pointing to a dir containing test_it.py results in 2 passed (the original and the symlink both collected).

<a id="u-f43da076a97e"></a>
### `test_collect_symlink_file_arg`

`def test_collect_symlink_file_arg(pytester: Pytester) -> None:` · [testing/test_collection.py:L1404-L1416][f1]

A symlink to a test file is collected even though the symlink name does not match python_files (#4325): running -v on symlink.py reports 'symlink.py::test_nodeid PASSED' and 1 passed, with the nodeid based on the symlink name.

<a id="u-bd5dbef05658"></a>
### `test_collect_symlink_out_of_tree`

`def test_collect_symlink_out_of_tree(pytester: Pytester) -> None:` · [testing/test_collection.py:L1419-L1445][f1]

With an out-of-tree rootdir, a symlink to sub/ placed in out_of_tree is collected without a 'sub/' prefix in nodeids: after chdir into sub and passing --rootdir=sub plus the symlink path, -vs reports 'test_real.py::test_nodeid PASSED' and exit 0.

<a id="u-011d46c613cd"></a>
### `test_does_not_crash_on_recursive_symlink`

`def test_does_not_crash_on_recursive_symlink(pytester: Pytester) -> None:` · [testing/test_collection.py:L1743-L1754][f1]

A symlink 'recursive' pointing at itself in the rootdir must not break collection (#7951): the run exits OK with exactly 1 passed.

<a id="u-49d7ec45da11"></a>
### `test_do_not_collect_symlink_siblings`

`def test_do_not_collect_symlink_siblings( pytester: Pytester, tmp_path: Path, request…` · [testing/test_collection.py:L1828-L1850][f1]

Regression for #12039: directories that are samefile-equivalent siblings are not collected twice.

tmp_path creates a 'current' symlink next to itself; a test file in tmp_path is collected exactly once whether pytest is pointed at tmp_path or at the symlinked 'current' directory (1 passed each run).

**Uncertainties.**

- Relies on tmp_path fixtures creating the 'current' sibling symlink; derived from the tmpdir naming in the test

<a id="u-aa200c441e75"></a>
### `test_collect_with_chdir_during_import`

`def test_collect_with_chdir_during_import(pytester: Pytester) -> None:` · [testing/test_collection.py:L1291-L1321][f1]

A rootdir conftest that chdirs into 'sub' at import time must not corrupt collection: the run passes a test asserting the cwd equals sub.

Adding testpaths=. then works too: --collect-only collects 1 item despite the changed working directory.

<a id="u-62a9e56cba69"></a>
### `test_collect_pyargs_with_testpaths`

`def test_collect_pyargs_with_testpaths( pytester: Pytester, monkeypatch: MonkeyPatch …` · [testing/test_collection.py:L1324-L1351][f1]

With addopts=--pyargs and testpaths=testmod in a root pytest.ini, PYTHONPATH prepended to the pytester path, and cwd changed to the root, a subprocess run collects the package's test_file.py (its __init__.py with a test function is not collected since it does not match python_files), reporting 1 passed.

<a id="u-18266b31beeb"></a>
### `test_pyargs_collection_tree`

`def test_pyargs_collection_tree(pytester: Pytester, monkeypatch: MonkeyPatch) -> None:` · [testing/test_collection.py:L1783-L1825][f1]

With --pyargs, the collection tree includes only parents within the import path, not up to confcutdir (#11904).

A site-packages directory is prepended to sys.path, a pkg/sub/test_it.py package tree is created, and --pyargs --collect-only pkg.sub.test_it prints Package pkg -> Package sub -> Module test_it.py -> Function test, consecutively. Repeating after chdir to an unrelated temp rootdir yields the same tree with a globbed pkg root, exit OK both times.

<a id="u-811ed67c3eac"></a>
### `test_collect_short_file_windows`

`def test_collect_short_file_windows(pytester: Pytester) -> None:` · [testing/test_collection.py:L1757-L1780][f1]

Windows-only reproducer for #11895.

It creates a temp dir via tempfile.mkdtemp; if the path lacks '~' it fails on CI (expecting short paths there) or skips locally, since short-path generation is environment-dependent. Otherwise it writes a test file into the short path and asserts running pytest on it collects 1 passed.

**Uncertainties.**

- Behavior depends on the filesystem producing 8.3 short names; guarded by skip/fail branches

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_collection.py
