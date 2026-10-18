# Symlink & subst path resolution tests

**Capability.** Verifies issue 5965: running pytest on a path behind a Linux symlink or a Windows subst drive reports errors using the given path rather than the resolved one, with per-platform context managers exposing the aliased path.

Use these tests when changing path canonicalization or error reporting locations. Each context manager yields the aliased path form; the single test asserts message paths stay as given. Only one of the two context managers applies per platform.

Parent: [Environment & integration tests](r1-integration-environment-tests.md)

## Units (3)

<a id="u-279517dcd234"></a>
### `subst_path_linux`

`def subst_path_linux(filepath: Path):` · [testing/test_link_resolve.py:L39-L51][f1]

Context manager exposing a Linux file path through a symlink: it creates directory/../sub2 as a symlink to the file's parent directory and yields target/basename.

The finally block does nothing because everything lives in the tempdir; os.symlink raises if the target already exists. On cleanup the symlink is intentionally left in place.

**Notes.**

- side_effect: Leaves the sub2 symlink behind; cleanup is deliberately skipped.

<a id="u-846f84be9574"></a>
### `subst_path_windows`

`def subst_path_windows(filepath: Path):` · [testing/test_link_resolve.py:L15-L36][f1]

Context manager exposing a Windows file path under a subst drive.

It scans drive letters H through Z for the first nonexistent one; if none is free it raises AssertionError('Unable to find suitable drive letter for subst.'). It then runs 'subst <drive> <parent-dir>', asserts the drive exists, and yields a filename assembled as Path(drive, os.sep, basename) — preserving the original basename. In a finally block it always runs 'subst /D <drive>' to delete the mapping, even if the yielded block raised. The subprocess calls run via subprocess.check_call, so a subst failure raises CalledProcessError before the yield.

**Uncertainties.**

- No branch handles 'subst' being absent from PATH beyond the resulting CalledProcessError propagating.

<a id="u-a6c31d908d30"></a>
### `test_link_resolve`

`def test_link_resolve(pytester: Pytester) -> None:` · [testing/test_link_resolve.py:L54-L84][f1]

Verifies issue 5965: running pytest on a path behind a subst drive or symlink reports errors using the given path, not the resolved one.

It creates mkpydir sub1 with a failing test_foo.py, selects subst_path_windows on win32 or subst_path_linux otherwise, and runs pytest on the substituted path. It asserts the substring 'sub1/test_foo.py' never appears in stdout, then that stdout fnmatch-matches the drive-prefixed path on Windows or '*sub2/test_foo.py*' on Linux.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_link_resolve.py
