# Platform-specific & import suites

**Capability.** Covers behavior that varies by platform or import mechanism: sysfind/sysexec and numbered dirs (win32-skipped), Windows-only sysfind .bat preference and win32-only path tests, POSIX-only tests, and pyimport via both classic and importlib-forced paths.

Use this suite when touching platform-sensitive or import-related py.path code. Markers restrict classes to their intended platforms, so tests skipped locally are expected. The import suites duplicate coverage under an explicit importlib option set.

**Depends on.**

- [py.path test infrastructure](r1-local-test-support.md) · model-inferred · 0 edge(s)

Parent: [Legacy py.path compatibility](r1-legacy-py-path.md)

## Units (6)

<a id="u-5bac36691956"></a>
### `test-local.py-testexecution`

`class TestExecution:` · [testing/_py/test_local.py:L900-L903][f1]

Tests for sysfind, sysexec and make_numbered_dir, skipped on win32 via pytestmark.

Pinned behaviors: sysfind ignores PATH entries lacking read permission (a chmod-0 directory yields None for any name, restored in finally); sysfind accepts an absolute name string and resolves to the same path as a bare name; with two PATH entries both containing 'a', sysfind('a', checker=...) selects the candidate passing the checker and returns None when the checker rejects all (lambda returning None); sysexec captures stdout so 'ls -a' output contains every basename of the cwd; a failing command raises ExecutionFailed (imported from py._process.cmdexec, falling back to RuntimeError when that import fails); make_numbered_dir with keep=2 numbers sequentially from 0 and prunes older entries so only the previous two remain; numbering is case-insensitive-safe on the filesystem (prefixes 'CAse.' and 'caSE.' produce distinct lowercased paths, the second ending '.1'); when os.symlink is monkeypatched to raise NotImplementedError, make_numbered_dir still succeeds (lock creation degrades gracefully); the default locked variant produces the same sequential numbering across ten rounds; and mtime()/read() on a non-existent path raise EnvironmentError, preserving OS errors.

uses: [test-local.py-testlocalpath](r1-local-commonfs-suite.md#u-2f8275a2f0ee)

**Uncertainties.**

- test_sysexec assumes an 'ls' and 'false' executable exist in PATH; environment outside this file

<a id="u-4a2bec852984"></a>
### `test-local.py-testexecutiononwindows`

`class TestExecutionOnWindows:` · [testing/_py/test_local.py:L889-L892][f1]

Windows-only test class (pytestmark applies the win32only skipif marker) verifying that local.sysfind prefers the '.bat' extension result over the extension-less file: with tmpdir prepended to PATH containing both 'hello' and 'hello.bat', sysfind('hello') returns the .bat file.

**Uncertainties.**

- Behavior is only asserted under the win32only marker; result on other platforms is unknown from this file

<a id="u-0b5a240e864d"></a>
### `test-local.py-testwinlocalpath`

`class TestWINLocalPath:` · [testing/_py/test_local.py:L1241-L1244][f1]

Windows-only tests (win32only marker).

stat().owner and stat().group raise NotImplementedError on Windows; chmod accepts an int mode and actually changes then restores the stat mode (with a guard choosing a differing mode when the current mode is 0); path comparison and relto are case-insensitive ('a_path' equals 'A_path', relto returns 'fiLe'); join accepts Unix-style separators and slashes and converts them to backslash form; sysfind('cmd') locates the executable and, viewed from the drive root via as_cwd, still finds it by its relative name; and fnmatch patterns written with posix separators ('/') match absolute paths on Windows.

<a id="u-9651fe1bf8cf"></a>
### `test-local.py-testposixlocalpath`

`class TestPOSIXLocalPath:` · [testing/_py/test_local.py:L1299-L1302][f1]

POSIX-only tests (skiponwin32 marker).

Pinned behaviors: mklinkto creates a hard link, incrementing the target's nlink count; mksymlinkto creates symlinks whose readlink() equals the target string (or the bare name when absolute=False); checks follow links — a symlink to a file satisfies check(file=1) and islink(), a symlink to a dir satisfies dir=1, while check(link=0, ...) excludes links; a non-existent path is not a link; relto the root '/' strips the leading slash; visit with a rec filter excluding links does not follow a symlink pointing back at tmpdir (yielding only the link itself); a self-referencing symlink can be removed; realpath() resolves a file symlink to its target basename; stat exposes owner/group matching pwd.getpwuid/grp.getgrgid, and stat(raising=False) returns None instead of raising error.ENOENT for missing paths; atime increases after reads within a duration bound using the ATIME_RESOLUTION sleep; common() of two siblings is the parent, and of unrelated absolute paths is '/'; joining to the root part gives '/a' and joining '/' onto a path is identity; chmod changes and restores modes, and chmod(rec=filter) applies mode 0o772 to every visited non-dot non-link entry, restoring old modes in finally; copy(mode=True) preserves the file mode, copy(stat=True) preserves mode plus atime/mtime within ATIME_RESOLUTION for files and per-file inside directories; and chown(owner, group) with the current identity succeeds, including recursively over a tree containing a dangling symlink (cleaned up in finally). test_chmod_rec_int is self-labeled fragile; its nested recfilter excludes dotfiles and links.

**Uncertainties.**

- test_atime assumes the filesystem updates atime on read; many modern systems mount noatime, which would falsify the assertion independent of this code
- stat attribute access (atime/mtime/mode vs atime()/mtime()) differs between tests; the exact stat object API is defined outside this file

<a id="u-bddb2b5dc7dc"></a>
### `test-local.py-testimport`

`class TestImport:` · [testing/_py/test_local.py:L1009-L1010][f1]

Tests for py.path's pyimport.

An autouse fixture preserve_sys snapshots sys.modules (mock.patch.dict) and sys.path so each test runs isolated. Pinned behaviors: execfile.py imports to a module named 'execfile' with x==42; importing a module whose containing directory was renamed raises tmpdir.ImportMismatchError, which is suppressed when env PY_IGNORE_IMPORTMISMATCH='1' but raised again when it is '0' (set via monkeypatch.setenv); a filename like 'foo__init__.py' imports despite its messy name; a directory with __init__.py imports both from the directory path and from the __init__.py path, yielding module name 'hello_123'; the modname argument overrides the derived name ('0x.y.z'); package-relative imports inside otherdir give a.py result 'got it' with name 'otherdir.a', b.py stuff 'got it', and c.py/d.py their value attributes; a file inside an ensured package imports as 'xxxpackage.module1' and is identical to the sys.modules entry after a normal 'from xxxpackage import module1'; the filepath-consistency check accepts cached variants ('.pyc', '$py.class', '.pyo' — the pre-registered module object is returned as-is inside monkeypatch.context) but a mismatched '.py' pseudo-path raises ImportMismatchError whose args are (modname, modfile, original path), and ImportMismatchError subclasses ImportError; importing two different __init__.py files named proja can yield the same namespace module (issue 131); and ensuresyspath='append' appends exactly the root directory to sys.path once, at the end.

uses: [path1](r1-local-test-support.md#u-45acc6187683)

**Uncertainties.**

- ImportMismatchError is accessed as tmpdir.<...> / pseudopath.<...>, i.e. an attribute of the path object; its definition is outside this file

<a id="u-93fa9475b279"></a>
### `test-local.py-testimportlibimport`

`class TestImportlibImport:` · [testing/_py/test_local.py:L1128-L1131][f1]

Tests pyimport with OPTS = {'ensuresyspath': 'importlib'}, i.e. forcing the importlib-based import path.

Pinned behaviors: execfile.py imports normally with name 'execfile' and x==42; importing a package directory raises ImportError under this mode; modname can still be overridden ('0x.y.z'); a module relying on package-relative imports (otherdir/a.py) raises ImportError because no package context is set up; and the import bypasses sys.modules — a freshly imported file's name does not appear there.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/_py/test_local.py
