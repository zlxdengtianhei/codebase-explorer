# Path Inspection and Predicates

**Capability.** Owns non-mutating views of a path: keyword check predicates, stat wrappers, uid/gid lookup, glob matching, directory walking and listing; read-only vocabulary consumed by fs ops and import logic.

Use it to answer questions about a path (existence, mode, listing, pattern match) without modification. Checkers and the stat wrapper back LocalPath.check and query methods.

**Depends on.**

- [Path Construction and Decomposition](r6-path-structure.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Path Filesystem Operations](r6-path-fs.md) · graph-confirmed · 17 edge(s)
- [Path Construction and Decomposition](r6-path-structure.md) · graph-confirmed · 2 edge(s)

Parent: [Legacy LocalPath Library](r6-legacy-path.md)

## Units (7)

<a id="u-6dfe3d34fb22"></a>
### `path-checkers`

`class Checkers:` · [src/_pytest/_py/path.py:L41-L44][f1]

Predicate checkers evaluating keyword checks against a path for LocalPath.check.

Each public method implements one check (dotfile, ext, basename, basestarts, relto, fnmatch, endswith); ext adds a leading dot to the argument when missing. _evaluate resolves each keyword to a method: a 'not'-prefixed name with no direct method inverts the unprefixed check; unknown names raise TypeError. If the resolved method takes an argument (co_argcount>1 via getrawcode) it is called as meth(value), otherwise as meth() compared against the truthiness of value, XOR the invert flag; any false result fails the whole evaluation. If a check raises ENOENT, ENOTDIR, or EBUSY, evaluation falls back to the existence-dependent keywords in _depend_on_existence (exists, link, dir, file): if such a keyword is present and its value contradicts non-existence, the evaluation fails. _stat caches a Stat on the instance (first call guarded by AttributeError) and falls back to lstat on ELOOP; dir/file test S_ISDIR/S_ISREG on that cached stat, exists returns the Stat object itself, link lstats and uses S_ISLNK.

**Notes.**

- failure: A checker name with no matching method and no 'not'-stripped method raises TypeError, not False.
- condition: The exists checker returns the Stat object (truthy) rather than a boolean.

uses: [getrawcode](r6-source-introspection.md#u-d1f459143028)

**Uncertainties.**

- Only ENOENT/ENOTDIR/EBUSY trigger the existence fallback; other OSError subclasses propagate.

<a id="u-2f5968320414"></a>
### `path-stat`

`class Stat:` · [src/_pytest/_py/path.py:L203-L206][f1]

Wrapper around an os.stat result tied to its LocalPath.

__getattr__ forwards unknown attribute names to 'st_<name>' on the wrapped osstatresult, so uid, mode, etc. resolve dynamically; size and mtime are declared as typed properties only under TYPE_CHECKING. owner and group resolve ids to names via lazily imported pwd/grp through error.checked_call, raising NotImplementedError on win32. isdir/isfile test the cached st_mode with S_ISDIR/S_ISREG. islink calls self.path.lstat() but then tests the cached osstatresult mode, so a symlink lstat result is required for it to be meaningful.

**Notes.**

- condition: Stat.islink performs an lstat for its side effect but checks the cached st_mode, so a Stat built from a plain stat() of a symlink will not report a link.

<a id="u-d8f2ac381eff"></a>
### `path-id-lookup`

`def getuserid(user):` · [src/_pytest/_py/path.py:L249-L254][f1]

Translate user/group names to numeric ids; integer inputs pass through unchanged, non-int inputs are resolved via pwd.getpwnam / grp.getgrnam (field index 2).

Modules are imported lazily, so these functions are only usable on platforms providing pwd/grp.

<a id="u-fcd704795ccf"></a>
### `path-fnmatcher`

`class FNMatcher:` · [src/_pytest/_py/path.py:L173-L174][f1]

Callable glob matcher for paths.

On Windows (iswin32) when the pattern contains posix separators but not the path's own separator, posix '/' is rewritten to the platform separator first. If the pattern contains no path separator it is matched against path.basename only; otherwise it is matched against the full string form of the path, and a non-absolute pattern is implicitly prefixed with '*<sep>' so it matches any suffix. Matching uses fnmatch.fnmatch.

<a id="u-391bc53c6eb9"></a>
### `path-visitor`

`class Visitor:` · [src/_pytest/_py/path.py:L138-L139][f1]

Directory-walk helper used by LocalPath.visit.

__init__ normalizes arguments: a string fil becomes FNMatcher(fil); a string rec becomes FNMatcher(rec); a non-callable truthy rec becomes a lambda accepting every path; otherwise rec is stored as-is (None disables descent filtering). optsort is sorted when sort is true, else identity. gen lists entries of a path, returning silently if listdir raises an exception in self.ignore; it filters subdirectories to those passing p.check(dir=1) and (if rec is set) rec(p), sorting them via optsort. Depthfirst (default) recurses into all subdirectories before yielding matching entries; breadthfirst yields the entries first, then recurses. Entries are yielded when fil is None or fil(p) matches.

<a id="u-d59616894f5d"></a>
### `path-localpath-listing`

`def listdir(self, fil=None, sort=None):` · [src/_pytest/_py/path.py:L803-L824][f1]

Directory listing.

listdir with no fil and no sort returns _fastjoin(name) for every os.listdir entry (_fastjoin builds a child LocalPath by naive string concatenation with sep). When fil is a string lacking any of * ? [ or sep, it is treated as a literal child name: the joined child is returned as a one-element list if it exists, else an empty list; otherwise the string becomes an FNMatcher. With a filter (or sort requested), entries are built by listing, matching each child, sorting via _sortlist when sort is truthy — a callable sort emits a DeprecationWarning (stacklevel 3) and calls res.sort(callable), while any other truthy sort sorts plainly. visit yields all entries below self through Visitor with fil (glob string or callable), rec (descent filter), ignore (exception class to swallow on listdir, default NeverRaised so all propagate), bf for breadthfirst, and sort.

calls: [path-visitor](r6-path-meta.md#u-391bc53c6eb9), [path-fnmatcher](r6-path-meta.md#u-fcd704795ccf)

<a id="u-742389cde1fa"></a>
### `path-localpath-query`

`def check(self, **kw):` · [src/_pytest/_py/path.py:L773-L799][f1]

Non-mutating queries on the path.

check with no keywords returns exists(strpath); with exactly one 'dir' or 'file' keyword it short-circuits on os.path.isdir/isfile (kw value XOR NOT semantics); otherwise it delegates to Checkers(self)._evaluate(kw). exists/isdir/isfile are thin wrappers over check with the corresponding keyword. islink returns os.path.islink(strpath) directly. stat wraps os.stat in a Stat; with raising=True (default) errors go through error.checked_call, with raising=False any exception except KeyboardInterrupt returns None. lstat wraps os.lstat in a Stat. size and mtime read the Stat. setmtime with mtime=None calls os.utime with None; otherwise it tries (−1, mtime) and on error.EINVAL retries with (atime(), mtime). atime reads stat().atime via __getattr__. samefile fspath-converts and absolutizes other, returns True on equality, False when os.path.samefile is unavailable, otherwise the checked os.path.samefile result. realpath returns a new path from os.path.realpath. chdir chdirs (checked) and returns the previous cwd as a LocalPath, or None if computing it raised error.ENOENT; as_cwd is a contextmanager that yields the old dir and restores it in finally when not None.

calls: [path-checkers](r6-path-meta.md#u-6dfe3d34fb22)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_py/path.py
