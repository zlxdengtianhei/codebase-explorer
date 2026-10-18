# Module Import by Path

**Capability.** Imports a file or package as a module under three modes, deriving dotted module names from package roots via importlib specs without touching sys.path, and detecting mismatches between requested path and module __file__.

Use import_path for test/conftest imports; resolve_pkg_root_and_module_name computes the package root and dotted name; insert_missing_modules makes synthetic names importable. ImportPathMismatchError signals duplicate-basename conflicts.

Parent: [Filesystem & Import Path Utilities](r2-path-utils.md)

## Units (12)

<a id="u-d7adbe2f03f9"></a>
### `ImportPathMismatchError`

`class ImportPathMismatchError(ImportError):` · [src/_pytest/pathlib.py:L480-L486][f1]

ImportError subclass raised by import_path when the imported module's __file__ differs from the requested path — e.g. two different files with the same basename in packages, such as /tests1/test_foo.py versus /tests2/test_foo.py.

<a id="u-71e06937ccc3"></a>
### `import_path`

`def import_path( path: str | os.PathLike[str], *, mode: str | ImportMode = ImportMode…` · [src/_pytest/pathlib.py:L489-L612][f1]

Imports and returns the module for a file or package path under one of three modes.

The path must exist (ImportError otherwise). In importlib mode it first resolves pkg root and module name; on success it returns an existing sys.modules entry or imports via _import_module_using_spec without inserting modules; if resolution or import fails it falls back to a root-anchored synthetic name via module_name_from_path, returning a cached sys.modules entry, then importing with insert_modules=True, raising ImportError if that also fails. In prepend/append modes it resolves the pkg root (falling back to path.parent/path.stem when unresolvable), then permanently mutates sys.path — append adds pkg_root at the end if absent, prepend inserts it at position 0 if not already first; the mutation is deliberately not restored because delayed imports need it. It then calls importlib.import_module; for __init__.py paths the module is returned without further checks. Otherwise, unless the PY_IGNORE_IMPORTMISMATCH env var is '1', it verifies the module's __file__ matches the path — stripping a trailing 'c'/'o' from .pyc/.pyo and a trailing __init__.py component — treating FileNotFoundError during comparison as a mismatch, and raising ImportPathMismatchError on any difference; module_file None also raises the mismatch error.

calls: [resolve_pkg_root_and_module_name](r2-path-import-machinery.md#u-63d1ed07edab), [_import_module_using_spec](r2-path-import-machinery.md#u-c016134a3d1a), [module_name_from_path](r2-path-import-machinery.md#u-930786165f13); uses: [_is_same](r2-path-import-machinery.md#u-420d2bcbe7ec); raises: [ImportPathMismatchError](r2-path-import-machinery.md#u-d7adbe2f03f9)

**Uncertainties.**

- Which _is_same definition executes depends on sys.platform at module import time; both definitions are in this file.

<a id="u-c016134a3d1a"></a>
### `_import_module_using_spec`

`def _import_module_using_spec( module_name: str, module_path: Path, module_location: …` · [src/_pytest/pathlib.py:L615-L735][f1]

Imports a module by canonical name, file path, and parent location using importlib specs, without touching sys.path.

It first ensures the parent module exists: for a dotted name, it reuses sys.modules' parent unless that parent lacks __path__ (needing re-import), otherwise recursively imports the parent — deriving the parent path from the module path (grandparent directory for __init__.py, parent directory otherwise, plus __init__.py when the parent is a regular package). It then searches sys.meta_path finders for a spec matching the module path; for the pytest assertion-rewrite hook with a real file, it passes both location and path as search locations. If no finder matches, it builds a spec with spec_from_file_location, supplying a NamespaceLoader when the path is a directory (namespace package). When the resulting spec matches the module path (spec_matches_module_path), it creates the module, stores it in sys.modules under the canonical name, execs it, sets it as an attribute of the parent module, optionally runs insert_missing_modules to fabricate empty ancestors, and returns it; otherwise returns None so callers can fall back.

calls: [spec_matches_module_path](r2-path-import-machinery.md#u-2afaba008d63), [insert_missing_modules](r2-path-import-machinery.md#u-c69c206a362b), [_import_module_using_spec](r2-path-import-machinery.md#u-c016134a3d1a)

<a id="u-c69c206a362b"></a>
### `insert_missing_modules`

`def insert_missing_modules(modules: dict[str, ModuleType], module_name: str) -> None:` · [src/_pytest/pathlib.py:L801-L836][f1]

Creates intermediate parent modules so a synthetically named module like src.tests.test_foo is importable via __import__.

Walking from the full name upward, for each missing parent it first tries importlib.import_module — explicitly raising ModuleNotFoundError when sys.meta_path is empty to avoid the interpreter's warning — and on ModuleNotFoundError substitutes an empty ModuleType marked as created by pytest's importmode=importlib. The missing parent is stored in the modules dict and the child module is set as an attribute on it if not already present. The loop strips one name part per iteration until no parent remains.

**Uncertainties.**

- The fabricated ModuleType is constructed with module_name (the child's full name at that iteration) as its name argument, which looks off by one relative to parent_module_name; documented as observed in source.

<a id="u-2afaba008d63"></a>
### `spec_matches_module_path`

`def spec_matches_module_path(module_spec: ModuleSpec | None, module_path: Path) -> bool:` · [src/_pytest/pathlib.py:L738-L754][f1]

Tests whether a ModuleSpec corresponds to a given module file path.

None spec returns False. If the spec has an origin, it matches only when Path(origin) equals the path. Otherwise, for namespace packages, it matches when any entry of submodule_search_locations equals the path; all other cases return False.

<a id="u-5bd537925bc1"></a>
### `is_importable`

`def is_importable(module_name: str, module_path: Path) -> bool:` · [src/_pytest/pathlib.py:L900-L923][f1]

Checks whether a module name would resolve to the given file if imported normally, as in the REPL.

It calls importlib.util.find_spec(module_name); ImportError, ValueError, or ImportWarning mean not importable (False). Otherwise it returns spec_matches_module_path(spec, module_path), i.e. True only when the found spec's origin or namespace search locations equal the given path.

calls: [spec_matches_module_path](r2-path-import-machinery.md#u-2afaba008d63)

<a id="u-930786165f13"></a>
### `module_name_from_path`

`def module_name_from_path(path: Path, root: Path) -> str:` · [src/_pytest/pathlib.py:L770-L798][f1]

Derives a dotted module name from a file path anchored at root, e.g. root=/projects, path=projects/src/tests/test_foo.py gives src.tests.test_foo.

The suffix is removed; if the path is not relative to root the full path minus its first component is used. A trailing __init__ part is dropped when at least two parts remain (package name without the init file, unless at root). Dots inside any part are replaced with underscores so directory names like .env.310 cannot create spurious intermediate modules or relative-import-looking names.

<a id="u-542079ec72f0"></a>
### `compute_module_name`

`def compute_module_name(root: Path, module_path: Path) -> str | None:` · [src/_pytest/pathlib.py:L926-L943][f1]

Computes a dotted module name for module_path relative to a root anchor, or None when it cannot.

Stripping the suffix fails on empty paths such as Path.cwd() (returns None); a path not relative to root returns None (marked no-cover); an empty relative part returns None; a trailing __init__ part is dropped; otherwise the joined relative parts are returned.

<a id="u-91980a208e0e"></a>
### `resolve_package_path`

`def resolve_package_path(path: Path) -> Path | None:` · [src/_pytest/pathlib.py:L839-L853][f1]

Finds the deepest-or-highest regular package root containing the given path by walking the path and its parents: while each directory contains an __init__.py and its name is a valid identifier, it is recorded as the result; the first directory failing either check stops the walk.

Returns the last qualifying directory, or None if none qualify.

<a id="u-63d1ed07edab"></a>
### `resolve_pkg_root_and_module_name`

`def resolve_pkg_root_and_module_name( path: Path, *, consider_namespace_packages: boo…` · [src/_pytest/pathlib.py:L856-L897][f1]

Returns the root-package directory for a Python file plus its dotted module name, e.g. models.py under src/app/core yields src and app.core.models.

It starts from resolve_package_path, taking the parent of the package path as pkg_root. When consider_namespace_packages is true it additionally scans the (pkg_root or path.parent) and all its ancestors, computing a candidate module name and accepting the first ancestor for which the name is non-empty and importable via is_importable, extending pkg_root to that namespace root. Finally, if a pkg_root was determined, it returns it together with compute_module_name's result; if no root could be determined or the computed name is empty, it raises CouldNotResolvePathError.

calls: [resolve_package_path](r2-path-import-machinery.md#u-91980a208e0e), [compute_module_name](r2-path-import-machinery.md#u-542079ec72f0), [is_importable](r2-path-import-machinery.md#u-5bd537925bc1); raises: [CouldNotResolvePathError][f1]

<a id="u-420d2bcbe7ec"></a>
### `_is_same`

`def _is_same(f1: str, f2: str) -> bool:` · [src/_pytest/pathlib.py:L761-L762][f1]

Windows variant of the file-identity check (the first of two platform-conditional definitions): returns True when the two path strings are Path-equal or when os.path.samefile considers them the same file, working around samefile returning False for UNC mounts.

**Uncertainties.**

- Which definition is active depends on sys.platform at module import time.

<a id="u-2f9d50ab6ca1"></a>
### `src/_pytest/pathlib.py:_is_same`

`def _is_same(f1: str, f2: str) -> bool:` · [src/_pytest/pathlib.py:L766-L767][f1]

Non-Windows variant of the file-identity check (the else branch of the two platform-conditional definitions): returns os.path.samefile(f1, f2).

**Uncertainties.**

- Which definition is active depends on sys.platform at module import time.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/pathlib.py
