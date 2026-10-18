# Frozen Binary Support

**Capability.** Computes the module names freezing tools must bundle so a frozen pytest can find its own plugins.

Use freeze_includes when packaging pytest with cx_freeze-like tools; it walks all modules under pytest packages via _iter_all_modules.

Parent: [Built-in Plugins and CLI Facets](r6-builtin-plugins.md)

## Units (2)

<a id="u-f047cdea906e"></a>
### `freeze_includes`

`def freeze_includes() -> list[str]:` · [src/_pytest/freeze_support.py:L10-L16][f1]

Return module names used by pytest that freezing tools like cx_freeze should include.

Imports the _pytest package locally, feeds the package object to _iter_all_modules, and returns its full traversal as a plain list. The only input-dependent condition is the size of _pytest's package tree; there is no error handling, so any failure importing or walking the package propagates.

calls: [_iter_all_modules](r6-freeze-support.md#u-d6d7c377b090)

**Uncertainties.**

- Whether _pytest resolves to the installed package versus a namespace package is determined at runtime; behavior if __path__ is absent is untested here

<a id="u-d6d7c377b090"></a>
### `_iter_all_modules`

`def _iter_all_modules( package: str | types.ModuleType, prefix: str = "", ) -> Iterat…` · [src/_pytest/freeze_support.py:L19-L45][f1]

Recursively yield the dotted names of every module found under a package.

Accepts either a filesystem path string (used as the search path with the caller-supplied prefix) or a module object, in which case the first entry of its __path__ becomes the path and the prefix becomes '<package.__name__>.'. For each entry from pkgutil.iter_modules: a subpackage causes a recursive call on path/name with prefix '<subname>.', each yielded child name being re-prefixed with the parent prefix; a plain module is yielded as prefix + name. Local imports of os and pkgutil keep them out of the frozen module list. No error handling: a module without __path__ raises AttributeError, and filesystem errors propagate.

**Notes.**

- condition: Passing a plain (non-package) module has no __path__, so behavior is undefined and would raise at package_path access
- contract: When a string path is given, the default empty prefix is used, so yielded names lack a package prefix

uses: [pkgutil.iter_modules](../../catalog.json)

**Uncertainties.**

- The docstring example implies sorted-ish output order, but pkgutil.iter_modules ordering is what actually determines it; no sorting is applied here

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/freeze_support.py
