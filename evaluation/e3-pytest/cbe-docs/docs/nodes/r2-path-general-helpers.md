# General Path Helpers

**Capability.** Standalone filesystem helpers: robust recursive removal with error repair, Windows extended-length paths, relative-path computation, safe directory scanning/walking, fnmatch matching, and existence/symlink operations that degrade gracefully.

Reach for these when dealing with hostile or platform-quirky paths: rm_rf removes read-only trees, safe_exists swallows unstatable paths, bestrelpath/commonpath render relative names, fnmatch_ex matches with py.path semantics.

Parent: [Filesystem & Import Path Utilities](r2-path-utils.md)

## Units (13)

<a id="u-679a90fd83e0"></a>
### `rm_rf`

`def rm_rf(path: Path) -> None:` · [src/_pytest/pathlib.py:L162-L170][f1]

Recursively removes a path even if entries are read-only.

It converts the path to Windows extended-length form, then runs shutil.rmtree with on_rm_rf_error bound as the error handler via partial (start_path set to the extended path), using the onexc parameter on Python 3.12+ and onerror on older versions; the handler's chmod-retry path is what makes read-only entries removable.

calls: [ensure_extended_length_path](r2-path-general-helpers.md#u-83c8a6a5fd5c), [on_rm_rf_error](r2-path-general-helpers.md#u-9c7f1f8d8575)

<a id="u-9c7f1f8d8575"></a>
### `on_rm_rf_error`

`def on_rm_rf_error( func: Callable[..., Any] | None, path: str, excinfo: BaseExceptio…` · [src/_pytest/pathlib.py:L73-L113][f1]

Error handler for shutil.rmtree that suppresses or repairs known removal failures.

FileNotFoundError (another process removed the entry concurrently) returns False silently. Any non-PermissionError emits a PytestWarning naming the path and exception and returns False. A PermissionError from a function other than os.rmdir/os.remove/os.unlink, and not os.open, warns about the unknown function and returns False; a PermissionError from os.open returns False without warning. For PermissionError on rmdir/remove/unlink it chmods user read/write onto the path and, when the path is a file, onto each parent up to start_path, then retries func(path) once and returns True so rmtree continues. The nested chmod_rw preserves existing mode bits by stat-then-or; the tail segment after chmod_rw is the retry logic of this same handler.

**Notes.**

- side_effect: chmods the failing path and, for files, all ancestor directories up to start_path before retrying.

uses: [rm_rf](r2-path-general-helpers.md#u-679a90fd83e0)

<a id="u-9687ab14ccec"></a>
### `_ignore_error`

`def _ignore_error(exception: Exception) -> bool:` · [src/_pytest/pathlib.py:L62-L66][f1]

Reports whether an OS error from directory scanning can be ignored.

True when the exception's errno is ENOENT, ENOTDIR, EBADF (macOS stat guard), or ELOOP, or when its winerror is one of the ignored Windows codes (drive not ready, broken self-referential symlink); false otherwise.

<a id="u-83c8a6a5fd5c"></a>
### `ensure_extended_length_path`

`def ensure_extended_length_path(path: Path) -> Path:` · [src/_pytest/pathlib.py:L132-L147][f1]

Bypasses the Windows 260-character MAX_PATH limit: on win32 it resolves the path to an absolute path and converts it via get_extended_length_path_str; on other platforms the input is returned unchanged.

<a id="u-24380735ee33"></a>
### `get_extended_length_path_str`

`def get_extended_length_path_str(path: str) -> str:` · [src/_pytest/pathlib.py:L150-L159][f1]

Prepends the Windows extended-length prefix.

Strings already starting with \\?\ or \\?\UNC\ are returned unchanged; strings starting with \\ receive the \\?\UNC\ prefix with the two leading slashes dropped; anything else receives \\?\.

<a id="u-924aae5fe744"></a>
### `bestrelpath`

`def bestrelpath(directory: Path, dest: Path) -> str:` · [src/_pytest/pathlib.py:L1019-L1045][f1]

Returns a relative path from directory to dest such that directory/bestrelpath equals dest; both paths must be both absolute or both relative (asserted to be Path instances).

If dest equals directory, returns os.curdir. If there is no common base (commonpath returns None or empty — different drives, disjoint relative paths, or mixed relative/absolute), returns str(dest). Otherwise it walks up from directory to the common base with one os.pardir per leftover directory part, then appends dest's remaining parts.

calls: [commonpath](r2-path-general-helpers.md#u-ae4ed12bd941)

<a id="u-ae4ed12bd941"></a>
### `commonpath`

`def commonpath(path1: Path, path2: Path) -> Path | None:` · [src/_pytest/pathlib.py:L1007-L1016][f1]

Returns the longest common path of two paths via os.path.commonpath, or None when they share none — including when one is relative and the other absolute, or on Windows for paths on different drives — since those make commonpath raise ValueError, which is caught.

<a id="u-a07dfdf2d39c"></a>
### `scandir`

`def scandir( path: str | os.PathLike[str], sort_key: Callable[[os.DirEntry[str]], obj…` · [src/_pytest/pathlib.py:L950-L979][f1]

Scans one directory breadth-first and returns its entries sorted by the given key (entry name by default).

A missing directory yields an empty list via FileNotFoundError. For each entry, is_file() is probed: OSError with an ignorable errno/winerror per _ignore_error skips the entry, while any other OSError is re-raised rather than hidden. The scandir iterator is closed via context manager.

calls: [_ignore_error](r2-path-general-helpers.md#u-9687ab14ccec)

<a id="u-a0eceeead17e"></a>
### `visit`

`def visit( path: str | os.PathLike[str], recurse: Callable[[os.DirEntry[str]], bool] …` · [src/_pytest/pathlib.py:L982-L995][f1]

Recursively walks a directory breadth-first, yielding entries level by level, each level sorted via scandir.

An entry's directory is recursed only when entry.is_dir() is true and the supplied recurse predicate accepts the entry.

calls: [scandir](r2-path-general-helpers.md#u-a07dfdf2d39c); uses: [function::visit::35149][f1]

<a id="u-110156d88ac3"></a>
### `fnmatch_ex`

`def fnmatch_ex(pattern: str, path: str | os.PathLike[str]) -> bool:` · [src/_pytest/pathlib.py:L419-L452][f1]

Matches a path against an fnmatch pattern with py.path-compatible whole-path semantics, unlike PurePath.match.

On Windows, when the pattern contains no native separators but does contain posix separators, posix separators are replaced with the native one. If the pattern contains no separator only the path's name is matched; otherwise the whole path string is matched, and for an absolute path with a relative pattern the pattern is prefixed with '*<os.sep>'. Final decision is fnmatch.fnmatch.

<a id="u-682fd12ea3a8"></a>
### `safe_exists`

`def safe_exists(p: Path) -> bool:` · [src/_pytest/pathlib.py:L1048-L1055][f1]

Like Path.exists() but returns False instead of raising on paths that cannot even be stat'ed: ValueError (path too long on Windows) or OSError (e.g. WinError 123 invalid filename syntax).

<a id="u-f173209cb095"></a>
### `resolve_from_str`

`def resolve_from_str(input: str, rootpath: Path) -> Path:` · [src/_pytest/pathlib.py:L410-L416][f1]

Turns a user-supplied path string into a Path anchored at rootpath: expands ~ (expanduser) and environment variables (expandvars); returns Path(input) when the result is absolute, otherwise rootpath joined with the input.

<a id="u-b29f54221f67"></a>
### `symlink_or_skip`

`def symlink_or_skip( src: os.PathLike[str] | str, dst: os.PathLike[str] | str, **kwar…` · [src/_pytest/pathlib.py:L460-L469][f1]

Creates a symlink from src to dst with os.symlink (passing through kwargs); if that raises OSError the test is skipped with a message naming the error, using pytest's skip outcome.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/pathlib.py
