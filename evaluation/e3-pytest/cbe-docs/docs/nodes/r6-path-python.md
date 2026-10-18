# Path Python Integration

**Capability.** Bridges paths and the Python runtime: importing a file as a module, package-root discovery, sys.path manipulation, subprocess execution, PATH lookup, home-dir resolution, plus module glue (importability test, mapping helper, sentinel exception, header/tail bindings).

Use it when a path must become a module or executable or interact with sys.path/HOME. pyimport composes structure, query and read primitives, making this the integration layer of LocalPath.

**Depends on.**

- [Path Construction and Decomposition](r6-path-structure.md) · graph-confirmed · 3 edge(s)

Parent: [Legacy LocalPath Library](r6-legacy-path.md)

## Units (11)

<a id="u-48914e451d3e"></a>
### `LocalPath.pyimport`

`def pyimport(self, modname=None, ensuresyspath=True):` · [src/_pytest/_py/path.py:L1070-L1157][f1]

Import the file at this path as a Python module and return the module.

Raises error.ENOENT if the path does not exist. With ensuresyspath=='importlib', modname defaults to purebasename, the module is loaded via importlib.util.spec_from_file_location and exec_module (ImportError if a spec or loader cannot be built) and sys.path is untouched. Otherwise: when modname is None, pypkgpath determines a package root and dotted module name (a trailing '__init__' name component is dropped, and __init__.py returns the package module without further verification); the package root is ensured on sys.path per ensuresyspath ('append' appends, other truthy values prepend, False leaves it alone) via _ensuresyspath, then __import__ runs and the module is taken from sys.modules. mod.__file__ is normalized (.pyc/.pyo strip the last char, $py.class maps to .py, __init__.py suffix handling), and if the resolved file differs from self, ImportMismatchError is raised unless the environment variable PY_IGNORE_IMPORTMISMATCH is '1'; a samefile ENOENT counts as not-same. With an explicit modname, an already-imported module is returned; otherwise a fresh empty ModuleType is registered in sys.modules, the file is exec'd into it, and on any BaseException the sys.modules entry is removed before re-raising.

**Notes.**

- failure: ImportMismatchError is the nested class LocalPath.ImportMismatchError (an ImportError).

calls: [LocalPath.pypkgpath](r6-path-python.md#u-a33835d532e2), [LocalPath._ensuresyspath](r6-path-python.md#u-362af356b7ee)

<a id="u-a33835d532e2"></a>
### `LocalPath.pypkgpath`

`def pypkgpath(self):` · [src/_pytest/_py/path.py:L1045-L1058][f1]

Find the enclosing Python package root by scanning ancestors from self upward for the last directory containing an __init__.py whose basename is importable per isimportable; scanning stops at the first non-directory, missing __init__.py, or unimportable basename, and None is returned when no package directory is found.

**Uncertainties.**

- The loop never breaks on the path itself before checking parents, so a file named like a package component inside a package yields the parent directory as pkgpath.

<a id="u-362af356b7ee"></a>
### `LocalPath._ensuresyspath`

`def _ensuresyspath(self, ensuremode, path):` · [src/_pytest/_py/path.py:L1060-L1068][f1]

Conditionally modify sys.path for imports.

A falsy ensuremode does nothing; 'append' appends str(path) only when not already present in sys.path; any other truthy mode inserts str(path) at sys.path[0] unless it is already the first entry.

<a id="u-5dfff8c9e5a2"></a>
### `LocalPath.sysexec`

`def sysexec(self, *argv: os.PathLike[str], **popen_opts: Any) -> str:` · [src/_pytest/_py/path.py:L1159-L1190][f1]

Execute this path as a subprocess and return decoded stdout.

stdout/stderr keys are popped from popen_opts and both pipes are forced, so callers cannot redirect them. Output bytes are decoded with sys.getdefaultencoding(). A non-zero exit status raises RuntimeError carrying (ret, ret, str(self), stdout, stderr) including decoded stderr; zero status returns the stdout text.

**Notes.**

- failure: Non-zero exit raises RuntimeError rather than a subprocess exception; the tuple duplicates ret as its first two fields.

<a id="u-1d370f8c296f"></a>
### `LocalPath.sysfind`

`def sysfind(cls, name, checker=None, paths=None):` · [src/_pytest/_py/path.py:L1192-L1237][f1]

Class method locating an executable by name via PATH.

An absolute name is checked directly (file=1) and returned or None. Otherwise paths come from the argument, or from PATH (':'-split) on posix; on win32 from Path (';'-split), appending '.' when neither '' nor '.' present, and substituting SYSTEMROOT for '%SystemRoot%' entries, with PATHEXT suffixes tried (plus the empty suffix). Each candidate local(x).join(name, abs=True)+addext is checked as a file; the optional checker callable filters matches (falsy result skips); error.EACCES on check is ignored. Returns None when nothing matches.

**Uncertainties.**

- On win32 the docstring warns plain win32 may not work; the code's '%SystemRoot%' substitution is the only special handling visible.

<a id="u-e5d4127e8dac"></a>
### `LocalPath._gethomedir`

`def _gethomedir(cls):` · [src/_pytest/_py/path.py:L1239-L1248][f1]

Class method returning a LocalPath of the user home: HOME if set, else HOMEDRIVE+HOMEPATH, else None.

<a id="u-428635ffecaf"></a>
### `isimportable`

`def isimportable(name):` · [src/_pytest/_py/path.py:L1469-L1472][f1]

Return True when name is a plausible Python identifier: it must be non-empty and start with a letter or underscore; underscores are stripped and the remainder must be empty or alphanumeric.

<a id="u-08629dffeaa5"></a>
### `map_as_list`

`def map_as_list(func, iter):` · [src/_pytest/_py/path.py:L199-L200][f1]

Apply func over iter with map and return the result as a list.

<a id="u-823223c01671"></a>
### `NeverRaised`

`class NeverRaised(Exception):` · [src/_pytest/_py/path.py:L134-L135][f1]

Exception subclass that is never raised, used as the default ignore filter for visit so that no listdir exception is swallowed.

<a id="u-7e6e387992af"></a>
### `path.py module code (L1–L40)`

`module_region` · [src/_pytest/_py/path.py:L1-L40][f1]

Module header: imports and the iswin32 flag (sys.platform == 'win32' or os._name == 'nt') used throughout for Windows-specific behavior.

<a id="u-f8edbc94ebf5"></a>
### `path.py module code (L1472–L1475)`

`module_region` · [src/_pytest/_py/path.py:L1472-L1475][f1]

Module tail binding the name local to LocalPath, the alias used throughout the module's own code.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_py/path.py
