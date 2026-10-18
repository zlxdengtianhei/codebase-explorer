# Numbered Directory Creation & Cleanup

**Capability.** Creates root/<prefix><N> directories monotonically and garbage-collects old ones safely using exclusive .lock files, symlink handling, and atexit-registered lock removal so concurrent pytest processes do not delete in-use directories.

Use make_numbered_dir_with_cleanup as the high-level entry; cleanup_numbered_dir and try_cleanup/maybe_delete_a_numbered_dir implement the guarded deletion; find_prefixed/find_suffixes/parse_num provide the numbering scan.

**Depends on.**

- [Pytest Codebase](r2-pytest-root.md) · within containment · 1 edge(s)

Parent: [Filesystem & Import Path Utilities](r2-path-utils.md)

## Units (14)

<a id="u-bbca0cd1c315"></a>
### `make_numbered_dir`

`def make_numbered_dir(root: Path, prefix: str, mode: int = 0o700) -> Path:` · [src/_pytest/pathlib.py:L225-L243][f1]

Creates root/<prefix><N> where N is one greater than the highest existing numbered suffix (parse_num over find_suffixes, default -1 for none).

It tries up to 10 times: each failed mkdir is swallowed and the maximum recomputed on the next attempt; on success it re-points the <prefix>current symlink via _force_symlink and returns the new path. After 10 failures it raises OSError naming the prefix and root.

calls: [find_suffixes](r2-path-numbered-dir-cleanup.md#u-babafcf3ee29), [src/_pytest/pathlib.py:parse_num](r2-path-numbered-dir-cleanup.md#u-54f5c35a4b52), [_force_symlink](r2-path-numbered-dir-cleanup.md#u-d14e49de856c)

<a id="u-e7e8ce8fbfa1"></a>
### `make_numbered_dir_with_cleanup`

`def make_numbered_dir_with_cleanup( root: Path, prefix: str, keep: int, lock_timeout:…` · [src/_pytest/pathlib.py:L377-L407][f1]

Creates a numbered directory with locking and exit-time cleanup, retrying up to 10 times.

Each attempt calls make_numbered_dir; on success, when keep is non-zero it locks the new directory with create_cleanup_lock and registers lock removal via register_cleanup_lock_removal. On success it also computes consider_lock_dead_if_created_before as the directory's mtime minus lock_timeout and registers cleanup_numbered_dir for program exit via atexit, then returns the path. Any exception in an attempt is stored and, if all 10 attempts fail, the last exception is raised via assert-and-raise.

calls: [make_numbered_dir](r2-path-numbered-dir-cleanup.md#u-bbca0cd1c315), [create_cleanup_lock](r2-path-numbered-dir-cleanup.md#u-672a2d936f54), [cleanup_numbered_dir](r2-path-numbered-dir-cleanup.md#u-17e0196d5808)

<a id="u-672a2d936f54"></a>
### `create_cleanup_lock`

`def create_cleanup_lock(p: Path) -> Path:` · [src/_pytest/pathlib.py:L246-L260][f1]

Creates the .lock file inside a numbered directory exclusively with os.open (O_WRONLY|O_CREAT|O_EXCL, mode 0o644).

If the lock already exists, raises OSError chained from the FileExistsError. On success it writes the current PID, closes the file, and re-checks existence — if the lock was renamed away after creation, raises OSError. Returns the lock path.

<a id="u-e8cf7b18e54f"></a>
### `ensure_deletable`

`def ensure_deletable(path: Path, consider_lock_dead_if_created_before: float) -> bool:` · [src/_pytest/pathlib.py:L310-L335][f1]

Decides whether a numbered directory may be deleted based on its lock file.

Symlinks are never deletable. If the .lock file does not exist the directory is deletable; if merely checking existence raises OSError (no access to the lock, presumed no access to the directory) it is not. If stat of the lock fails for any reason, it is not deletable. If the lock's mtime is older than consider_lock_dead_if_created_before, the lock is unlinked ignoring OSError and the directory reported deletable; a newer lock means not deletable.

<a id="u-9dc8325f1c8c"></a>
### `try_cleanup`

`def try_cleanup(path: Path, consider_lock_dead_if_created_before: float) -> None:` · [src/_pytest/pathlib.py:L338-L341][f1]

Attempts cleanup of one numbered directory: calls maybe_delete_a_numbered_dir only when ensure_deletable accepts the path's lock age; otherwise does nothing.

calls: [ensure_deletable](r2-path-numbered-dir-cleanup.md#u-e8cf7b18e54f), [maybe_delete_a_numbered_dir](r2-path-numbered-dir-cleanup.md#u-6bbbc57bc38f)

<a id="u-6bbbc57bc38f"></a>
### `maybe_delete_a_numbered_dir`

`def maybe_delete_a_numbered_dir(path: Path) -> None:` · [src/_pytest/pathlib.py:L282-L307][f1]

Deletes a numbered directory only if its cleanup lock can be created.

It converts the path to extended-length form, creates a lock inside it, renames the directory to a unique sibling garbage-<uuid4>, and rm_rf's that garbage name. Any OSError — concurrent cleanup by another process, a deletable folder found, or the process cwd inside the directory on Windows — aborts silently with a plain return. The finally block removes the lock if this function created it, suppressing unlink failures so cleanup of the lock never masks the outcome.

calls: [create_cleanup_lock](r2-path-numbered-dir-cleanup.md#u-672a2d936f54), [rm_rf](r2-path-general-helpers.md#u-679a90fd83e0)

<a id="u-4f2b89e40068"></a>
### `cleanup_candidates`

`def cleanup_candidates(root: Path, prefix: str, keep: int) -> Iterator[Path]:` · [src/_pytest/pathlib.py:L344-L353][f1]

Yields numbered-directory candidates for removal: computes the highest existing suffix, sets the deletion threshold to max_existing - keep, then walks find_prefixed entries paired with their parsed numbers and yields Path(entry) for each entry whose number is at or below the threshold.

calls: [find_suffixes](r2-path-numbered-dir-cleanup.md#u-babafcf3ee29), [src/_pytest/pathlib.py:parse_num](r2-path-numbered-dir-cleanup.md#u-54f5c35a4b52), [find_prefixed](r2-path-numbered-dir-cleanup.md#u-0eb310ff90a9), [extract_suffixes](r2-path-numbered-dir-cleanup.md#u-95915e4e789b)

<a id="u-17e0196d5808"></a>
### `cleanup_numbered_dir`

`def cleanup_numbered_dir( root: Path, prefix: str, keep: int, consider_lock_dead_if_c…` · [src/_pytest/pathlib.py:L363-L374][f1]

Lock-driven cleanup of numbered directories under root.

Returns immediately if root does not exist. Otherwise it runs try_cleanup on every cleanup candidate beyond the kept count, then on every garbage-* sibling left by interrupted deletions, and finally removes dead symlinks in root.

calls: [cleanup_candidates](r2-path-numbered-dir-cleanup.md#u-4f2b89e40068), [try_cleanup](r2-path-numbered-dir-cleanup.md#u-9dc8325f1c8c), [cleanup_dead_symlinks](r2-path-numbered-dir-cleanup.md#u-74fbb07843f6)

<a id="u-74fbb07843f6"></a>
### `cleanup_dead_symlinks`

`def cleanup_dead_symlinks(root: Path) -> None:` · [src/_pytest/pathlib.py:L356-L360][f1]

Removes stale symlinks in root: for each entry that is a symlink, if resolving it yields a target that does not exist, the symlink is unlinked.

Non-symlink entries and live symlinks are left untouched.

<a id="u-0eb310ff90a9"></a>
### `find_prefixed`

`def find_prefixed(root: Path, prefix: str) -> Iterator[os.DirEntry[str]]:` · [src/_pytest/pathlib.py:L173-L178][f1]

Lazily yields the os.DirEntry items directly inside root whose lowercase name starts with the lowercased prefix, i.e. a case-insensitive prefix scan of one directory level.

<a id="u-95915e4e789b"></a>
### `extract_suffixes`

`def extract_suffixes(iter: Iterable[os.DirEntry[str]], prefix: str) -> Iterator[str]:` · [src/_pytest/pathlib.py:L181-L189][f1]

Lazily yields each entry's name with the prefix length stripped, so callers receive only the suffix portion of prefixed names.

<a id="u-babafcf3ee29"></a>
### `find_suffixes`

`def find_suffixes(root: Path, prefix: str) -> Iterator[str]:` · [src/_pytest/pathlib.py:L192-L194][f1]

Composes find_prefixed and extract_suffixes: yields the suffix strings of names in root beginning with the given prefix.

calls: [find_prefixed](r2-path-numbered-dir-cleanup.md#u-0eb310ff90a9), [extract_suffixes](r2-path-numbered-dir-cleanup.md#u-95915e4e789b)

<a id="u-54f5c35a4b52"></a>
### `src/_pytest/pathlib.py:parse_num`

`def parse_num(maybe_num: str) -> int:` · [src/_pytest/pathlib.py:L197-L202][f1]

Converts a suffix string to int; returns -1 on ValueError so non-numeric suffixes rank below any real number when computing the maximum existing numbered-directory suffix.

<a id="u-d14e49de856c"></a>
### `_force_symlink`

`def _force_symlink(root: Path, target: str | PurePath, link_to: str | Path) -> None:` · [src/_pytest/pathlib.py:L205-L222][f1]

Best-effort creation of a symlink at root/target pointing to link_to, deliberately racy.

It first unlinks any existing entry at that location, ignoring any OSError, then creates the symlink and silently ignores any exception, so failures leave the previous or no link in place; acceptable because the link merely points at the latest test run.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/pathlib.py
