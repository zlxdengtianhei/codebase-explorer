# Path Filesystem Operations

**Capability.** Owns all mutating filesystem work: read/write/open, chunked copying, mode/stat copying, move/remove-style mutations, and temp/numbered directory helpers; they share the pattern of delegating to os/shutil while relying on query and structure primitives.

Use it when code must create, copy, write or clean up files and directories. copymode/copystat/copychunked are module-level helpers used by fs-ops methods.

**Depends on.**

- [Path Inspection and Predicates](r6-path-meta.md) · graph-confirmed · 17 edge(s)
- [Path Construction and Decomposition](r6-path-structure.md) · graph-confirmed · 9 edge(s)

**Depended on by.**

- [Path Construction and Decomposition](r6-path-structure.md) · graph-confirmed · 1 edge(s)

Parent: [Legacy LocalPath Library](r6-legacy-path.md)

## Units (6)

<a id="u-4e0de7f2e479"></a>
### `path-localpath-readwrite`

`def read_binary(self):` · [src/_pytest/_py/path.py:L362-L365][f1]

Reading, writing, pickling, hashing, and file-open operations.

open delegates to io.open when an encoding is given (via error.checked_call) or plain open otherwise; ensure=True first creates the parent directory. read_binary/read_text/read return file contents under the requested mode/encoding. readlines splits text on '\n' when cr is False (yielding a trailing empty element for a final newline), else uses f.readlines() with close in finally. load unpickles with pickle.load (deprecated). dump pickles with pickle.dump, closing in finally. write_binary/write_text create parents when ensure=True and write; write requires bytes for binary modes (ValueError otherwise) and coerces non-str text data via str() or decode with the default encoding. computehash resolves the hashlib constructor, mapping 'sha1' to 'sha' when hashlib is unavailable, raising ValueError for unknown types, then reads in chunks and returns the hexdigest.

**Notes.**

- failure: computehash raises ValueError (not OSError) when the hashtype names no known hash constructor.

<a id="u-7a1651f068dd"></a>
### `path-localpath-fs-ops`

`def move(self, target):` · [src/_pytest/_py/path.py:L402-L410][f1]

Filesystem mutation operations.

move refuses to move a path into its own subdirectory (error.EINVAL); it tries rename first, and on error.EXDEV falls back to copy then remove. copy of a file copies chunked content to the target (joining self.basename if the target is a dir), asserting self != target, optionally copying mode or full stat; copying a directory walks it skipping symlinks (rec filter link=0), recreating links with mksymlinkto(readlink()), files with copychunked, dirs with ensure(dir=1), applying mode/stat per entry. rename delegates to os.rename after fspath conversion; mkdir creates the joined directory and returns it. remove on a directory (link=0) uses shutil.rmtree when rec=1 (with ignore_errors passed through) or os.rmdir otherwise; on non-directories it uses os.remove; on win32 it chmods 0o700 first (recursively for dirs) to clear readonly bits. chmod requires an int mode (TypeError otherwise) and applies recursively via visit when rec=1, always also applying to self. chown (posix-only) resolves user/group via getuserid/getgroupid and chowns, recursively skipping symlinks when rec=1, and chowns self at the end. readlink returns os.readlink; mklinkto hard-links; mksymlinkto creates an absolute symlink or, with absolute=0, a relative one computed from the common base with '..' segments. _ensuredirs walks up creating missing parents; if mkdir hits error.EEXIST it rechecks dir=0 and re-raises only if the path is still not a directory (race tolerance). ensure joins args; with dir=True it ensures directories, otherwise it ensures the parent dir and creates an empty file if missing.

**Notes.**

- side_effect: chmod(rec=1) applies to self as well as every visited child, because the recursive os.chmod call precedes the final one.

<a id="u-560c27bd721e"></a>
### `path-localpath-tempdirs`

`def get_temproot(cls):` · [src/_pytest/_py/path.py:L1253-L1260][f1]

Class-level helpers for temporary and numbered directories.

get_temproot returns a LocalPath around tempfile.gettempdir(). mkdtemp creates a fresh temp dir under rootdir (default temproot) via checked tempfile.mkdtemp and returns it wrapped. make_numbered_dir creates rootdir/prefix<N> with N one greater than the highest existing number parsed from basenames starting (case-insensitively) with prefix; parse_num returns None for non-matching or non-numeric basenames. Creation runs in a retry loop: when lock_timeout is non-zero a '.lock' is created exclusively (mksymlinkto the pid when available, else O_EXCL open writing the pid), and atexit_remove_lockfile registers an exit hook that removes the lock only in the original (non-forked) pid, swallowing error.Error. If mkdir or lock creation hits EEXIST/ENOENT/EBUSY (races), the loop retries, raising only when maxnum stopped advancing (lastmax == maxnum). Old directories numbered <= maxnum-keep are pruned when keep is truthy and the new dir's mtime is readable: pruning first tries to take a lock on the victim; if that fails, victims younger than lock_timeout (by |mtime delta|) are kept. Victims are renamed to prefix+'garbage-'+uuid then recursively removed, with all non-KeyboardInterrupt exceptions during rename/remove swallowed; pre-existing garbage-named dirs are also removed the same way. Finally a symlink '<prefix-without-trailing>-<username>' to the new dir is attempted (USER, then USERNAME, else 'current'), with unlink and symlink failures ignored, and the new numbered dir is returned.

**Notes.**

- side_effect: Registers an atexit hook per created lockfile and creates a username symlink next to the numbered dir.
- failure: get_mtime swallows any error.Error and returns None, which disables pruning for that run.

**Uncertainties.**

- create_lockfile writes the pid via symlink when mksymlinkto exists; on a plain LocalPath the path has that method, so the O_EXCL branch appears to target other path implementations only.

<a id="u-c6c697cd1eb8"></a>
### `copychunked`

`def copychunked(src, dest):` · [src/_pytest/_py/path.py:L1452-L1466][f1]

Copy file contents in 512 KiB chunks: opens src for reading and dest for writing, loops reading until empty, and closes both files in nested finally blocks so the destination is closed even if a read or write fails mid-copy.

<a id="u-0655bea5d8d5"></a>
### `copymode`

`def copymode(src, dest):` · [src/_pytest/_py/path.py:L1437-L1441][f1]

Copy permission bits from src to dest via lazily imported shutil.copymode.

<a id="u-37e4a98e5089"></a>
### `copystat`

`def copystat(src, dest):` · [src/_pytest/_py/path.py:L1444-L1449][f1]

Copy permission, mtime, atime, and flags from src to dest via lazily imported shutil.copystat, stringifying both arguments.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_py/path.py
