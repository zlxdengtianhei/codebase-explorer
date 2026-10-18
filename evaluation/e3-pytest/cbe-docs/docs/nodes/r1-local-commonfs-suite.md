# Common py.path API suite

**Capability.** Pins the py.path filesystem API shared across implementations against the path1 tree: the CommonFSTests mixin, local-specific LocalPath behavior subclassing it, fspath-protocol objects, explicit binary/text I/O, unicode handling, and module-level function tests.

Use this suite as the reference contract for py.path operations. LocalPath inherits the mixin's tests and adds local-only cases; fake fspath objects check protocol acceptance. Encoding defaults and unicode round-trips are asserted explicitly, using ignore_encoding_warning where needed.

**Depends on.**

- [py.path test infrastructure](r1-local-test-support.md) · graph-confirmed · 4 edge(s)

Parent: [Legacy py.path compatibility](r1-legacy-py-path.md)

## Units (6)

<a id="u-ef4bd72abf8e"></a>
### `test-local.py-commonfs`

`class CommonFSTests:` · [testing/_py/test_local.py:L26-L27][f1]

Mixin class of tests pinning the common py.path filesystem API against a prepared tree supplied by the path1 fixture.

Its assertions document: construction and equality (a path equals a re-constructed path and a new() copy); join normalizes leading and doubled separators, accepts no arguments (yielding an equal path), and matches the '/' operator; parts() lists ancestors forward and reversed and common() returns the shared prefix; basename/dirname/dirpath/new(ext|basename)/ext/purebasename and _getbyspec expose path components; check() accepts keyword predicates (exists, dir, file, basename, notbasename, relto, notrelto, fnmatch, endswith, dotfile, link, notfile, notdir, notexists) that are false on non-existent paths for positive predicates; exists/isfile/isdir distinguish files from directories; relto returns the relative suffix, raises TypeError for a non-path argument (42), and bestrelpath returns '.', '../'-style results for relatives, and the raw string for a plain string argument; listdir accepts a fnmatch string, a callable filter, and sort=True, and raises error.ENOTDIR when called on a file; visit() accepts a string/callable filter, a rec filter, ignore (an exception class such as error.ENOENT, which makes visiting a non-existing path yield []), bf for breadth-first, and sort for ordering; comparison orders like the basename strings; read/read_text/readlines (with cr=0 stripping newlines) return file contents; load() unpickles the sample pickle ({'answer': 42}); size() and mtime() expose stat data; copy() copies files and recursively directories, remove() recurses by default, mkdir raises error.EEXIST on an existing directory, ensure/ensure_dir create missing paths; move() relocates files and directories (with a revert fallback in one test); and __fspath__ equals strpath so os.fspath and open work on the object. test_visit_filterfunc_is_string contains 'assert len(lst), 2', which in this syntax only asserts non-emptiness, not a length of 2.

uses: [setuptestfs](r1-local-test-support.md#u-07b0aa2ee739)

**Uncertainties.**

- This class is a mixin; the concrete path class under test is determined by the fixture each subclass binds, which is outside this file's source

<a id="u-2f8275a2f0ee"></a>
### `test-local.py-testlocalpath`

`class TestLocalPath(CommonFSTests):` · [testing/_py/test_local.py:L565-L566][f1]

Tests for local-specific behavior, subclassing CommonFSTests (whose tests run via the tmpdir fixture).

Pinned behaviors: join collapses '.', '..' segments and trailing separators to equal tmpdir; dirpath('/bar') keeps the path relative unless abs=True, which yields local('/bar'); computehash('md5'|'sha1') matches hashlib digests of the file bytes and raises ValueError for an unknown algorithm; remove() succeeds on read-only files and read-only directories (chmod 0 / 0o500 beforehand) and routes ignore_errors through to shutil.rmtree (verified by monkeypatching rmtree and inspecting kwargs); local() equals os.getcwd() and chdir() returns the previous cwd, but when the current directory is deleted, constructing local() raises error.ENOENT while path.chdir() still works and returns None; as_cwd() yields the original path and restores the working directory on normal exit, on a raised exception, and even when the target directory was removed (yielding None as old); local('samplefile') resolves relative to the cwd established by as_cwd; local('~', expanduser=True) matches os.path.expanduser of $HOME; on Windows, equality and hash are case-insensitive and set/dict membership reflects that; equality works with plain strings and None compares unequal, non-ASCII names remain distinct; ordering compares against strings and sorts consistently; open('w', ensure=1) and write_text(ensure=1) create missing parent directories; dump() writes a pickle readable with pickle.load in both binary and text modes; setmtime(mtime) sets an exact mtime and setmtime() resets it to now (using tempfile.mkstemp with a mktemp fallback if unavailable); normpath makes join('/otherdir') equal join('otherdir'); mkdtemp() creates a directory under local.get_temproot(); chdir() returns the previous location; ensure() on a file with or without a missing parent dir creates the file (and parents) idempotently, and ensure(dir=1) creates directories including non-ASCII names; visit is depth-first with files visited in order and rec patterns like '???'/'[!.]*' filter traversal; fnmatch works against absolute patterns containing os.sep; sysfind finds an existing executable, returns None for a nonsense name or an empty paths list, and accepts an explicit paths list; constructing local from an fspath object produces an absolute path whose join matches os.path.join semantics; and make_numbered_dir across a 20-process pool produces unique directories whose counter files read back correctly (marked xfail for EEXIST/ENOENT races, issue #11603).

calls: [batch_make_numbered_dirs](r1-local-test-support.md#u-a3d6c19ed48a); uses: [test-local.py-fake-fspath-obj](r1-local-commonfs-suite.md#u-014153a8c837); inherits: [test-local.py-commonfs](r1-local-commonfs-suite.md#u-ef4bd72abf8e)

**Uncertainties.**

- test_dump's finally closes 'f' which is only bound inside try; if path.dump raises, UnboundLocalError would shadow the original error
- test_chdir_gone asserts pytest.raises(error.ENOENT, local) then path1.chdir() returns None; the None-vs-exception conditions of chdir on a removed cwd are only evidenced by this test

<a id="u-014153a8c837"></a>
### `test-local.py-fake-fspath-obj`

`def fake_fspath_obj(request):` · [testing/_py/test_local.py:L540-L542][f1]

Function-scoped fixture returning an instance of a locally defined FakeFSPathClass whose __init__ stores the given path and whose __fspath__ returns it unchanged; the fixture instantiates it with os.path.join('this','is','a','fake','path'), i.e. a relative fake path object implementing the fspath protocol.

It supports test_fspath_protocol_other_class, which constructs a py.path local from the fake object and asserts that the resulting absolute path ends with the fake string and that joining the fake object appends exactly its fspath string.

**Uncertainties.**

- The test comment says py.path is always absolute, but this file does not show the conversion applied to the relative fake path

<a id="u-b83bc90dbb0b"></a>
### `test-local.py-free-functions`

`def test_pypkgdir(tmpdir):` · [testing/_py/test_local.py:L1159-L1164][f1]

Module-level tests.

test_pypkgdir: a directory containing __init__.py is its own pypkgpath, and files under subpackages resolve to the top package. test_pypkgdir_unimportable: when the directory name is unimportable ('pkg1-1'), pypkgpath stops at the subdirectory containing the nearest importable __init__.py and the unimportable package itself returns falsy. test_isimportable: py.path.isimportable (imported from py.path, falling back to py._path.local) accepts '', rejects it; accepts identifiers like 'x', 'x1', 'x_1', '_', '_1' and rejects 'x-1', 'x:1'. test_homedir_from_HOME: with HOME monkeypatched to the cwd, local._gethomedir() equals local(HOME). test_homedir_not_exists: with HOME and HOMEDRIVE both deleted, _gethomedir() returns None. test_samefile: samefile is true for a path with itself, for a file relative to its own basename under as_cwd, and on Windows for differently-cased spellings. test_samefile_symlink (skipped without os.symlink; skipped if os.symlink raises OSError/NotImplementedError, e.g. Windows permissions or pypy3): a symlink and its target are samefile. test_listdir_single_arg: listdir('hello') matches the exact name. test_mkdtemp_rootdir: local.mkdtemp(rootdir=tmpdir) creates the sole entry in tmpdir.

**Uncertainties.**

- test_samefile's p.basename case relies on as_cwd semantics proven elsewhere; the Windows branch's case-insensitivity source is not in this file

<a id="u-34e86f8cee90"></a>
### `test-local.py-testbinaryandtextmethods`

`class TestBinaryAndTextMethods:` · [testing/_py/test_local.py:L1558-L1559][f1]

Tests the explicit binary/text API: write_binary followed by read_binary round-trips the utf-8 bytes, and read_text(encoding='utf8') decodes them to the original str; write_text(encoding='utf8') produces the same bytes readable as binary and decodes back to the str; and using the explicit default-ish encoding 'ascii' for write_text/read_text returns a value whose type matches the written str, demonstrating that the default (ascii) encoding governs when none is passed.

<a id="u-eba4f8a3a001"></a>
### `test-local.py-testunicode`

`class TestUnicode:` · [testing/_py/test_local.py:L1530-L1531][f1]

Tests Unicode handling.

test_join_ensure and test_listdir skip unless LANG is set in the environment, then create a 'hällo' entry via ensure and verify join and listdir-by-name round-trip it. test_read_write, marked xfail with the reason that changing read/write might break existing usages, writes a str then reads it back, then writes and reads bytes encoded with sys.getdefaultencoding, wrapping the default-encoding reads in ignore_encoding_warning.

calls: [ignore_encoding_warning](r1-local-test-support.md#u-d93d9534c9ed)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/_py/test_local.py
