# Path Construction and Decomposition

**Capability.** Owns how LocalPath instances are created, compared, stringified, decomposed into parts, and re-derived as modified copies; these operations are mutually recursive and define path identity.

Use it for equality/hash semantics, join/basename/dirname logic, and relative-path computation. Filesystem ops and Python-import helpers build on these primitives.

**Depends on.**

- [Path Filesystem Operations](r6-path-fs.md) · graph-confirmed · 1 edge(s)
- [Path Inspection and Predicates](r6-path-meta.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Path Filesystem Operations](r6-path-fs.md) · graph-confirmed · 9 edge(s)
- [Path Inspection and Predicates](r6-path-meta.md) · model-inferred · 0 edge(s)
- [Path Python Integration](r6-path-python.md) · graph-confirmed · 3 edge(s)

Parent: [Legacy LocalPath Library](r6-legacy-path.md)

## Units (3)

<a id="u-ab72a8712833"></a>
### `path-localpath-init-equality`

`class LocalPath:` · [src/_pytest/_py/path.py:L265-L270][f1]

Construction, string conversion, and comparison semantics for LocalPath.

__init__ always stores an absolute strpath: None means os.getcwd; an argument not convertible via os.fspath raises ValueError; expanduser=True performs tilde expansion before abspath. __fspath__ returns strpath, enabling os.fspath. __eq__ compares fspath strings, lower-casing both sides on win32, returning False (not raising) when the other object cannot be converted. __hash__ hashes strpath, lower-cased on win32. __ne__ negates __eq__; ordering uses raw fspath string comparison. __repr__ renders 'local(...)' with repr of strpath; __str__ returns strpath directly.

**Notes.**

- side_effect: LocalPath(None) captures the working directory at construction time, so the stored absolute path does not track later chdir calls.

<a id="u-e881d9e2a764"></a>
### `path-localpath-new`

`def new(self, **kw):` · [src/_pytest/_py/path.py:L640-L678][f1]

Building modified path copies.

new creates a fresh instance via object.__new__ and, with no keywords, returns a straight copy of strpath. Otherwise it decomposes the path into drive/dirname/basename/purebasename/ext via _getbyspec: 'basename' conflicts with 'purebasename'/'ext' (ValueError); ext is normalized with a leading dot; a falsy 'dirname' falls back to drive; sep defaults to self.sep; the result is normpath of '{dirname}{sep}{basename}'. fnmatch delegates to FNMatcher(pattern)(self).

calls: [path-localpath-parts-rel](r6-path-structure.md#u-c3dc19239c83), [path-fnmatcher](r6-path-meta.md#u-fcd704795ccf)

<a id="u-c3dc19239c83"></a>
### `path-localpath-parts-rel`

`def basename(self):` · [src/_pytest/_py/path.py:L342-L345][f1]

Path decomposition and relative-path computation for LocalPath.

basename, dirname, purebasename, and ext are properties delegated to _getbyspec, which splits strpath on sep: 'drive' is the first segment, 'dirname' joins all but the last, and basename parts split on the last dot (no dot means ext is ''). Unknown spec names raise ValueError. __add__ returns new(basename=basename+other); __div__/__truediv__ join. dirpath returns a new path of dirname(self.strpath), joined with any args; with kwargs it falls back to new(basename='').join(...). join appends fspath-converted args, stripping separator characters from each; when abs is true, iteration from the end restarts strpath at the last absolute arg; when strpath already ends in sep no extra separator is inserted (handles '/'); on win32, '/' in args is converted to the native sep; the result is normpath'd. relto requires a str or LocalPath argument (TypeError otherwise), appends a trailing sep to the prefix, and on win32 compares case-insensitively via normcase; it returns the suffix after the prefix or ''. bestrelpath returns os.curdir when self == dest, str(dest) when there is no common base (or an AttributeError occurs), and otherwise the relative path built from count(sep)+1 os.pardir steps plus dest's suffix relative to the common base. parts returns self plus all ancestors, root-first unless reverse; common walks parts of both in lockstep and returns the last equal pair or None. ensure_dir delegates to ensure(dir=True).

**Notes.**

- condition: join only honors abs=True restart from an absolute arg if one of the trailing args is absolute; otherwise all args are appended.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_py/path.py
