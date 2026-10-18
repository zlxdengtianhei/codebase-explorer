# OS error facade (py.error)

**Capability.** Lazily generated EnvironmentError subclasses per POSIX errno: ErrorMaker creates and caches one Error class per errno, a Windows errno map translates winerror codes, and PEP 562 module __getattr__ forwards py.error.ENOENT-style access to the singleton.

Use this subtree when code raises or matches py.error.<ERRNO> exceptions; the residual regions are the import block, the winerrnomap table, and the singleton creation tail.

Parent: [Runtime library](r4-runtime-library.md)

## Units (6)

<a id="u-5f5431c00590"></a>
### `error.py module code (L1–L20)`

`module_region` · [src/_pytest/_py/error.py:L1-L20][f1]

Import block and P/R typing aliases of error.py; no behavior.

<a id="u-dbb5fdb15669"></a>
### `Error`

`class Error(EnvironmentError):` · [src/_pytest/_py/error.py:L21-L22][f1]

EnvironmentError subclass whose string forms lead with the class docstring, which for generated errno classes is the OS error description.

__repr__ formats module, class name, docstring and the space-joined str of args as 'module.Class docstring: args '; __str__ formats '[docstring]: joined-args'. Both map every arg through str, so non-string args are stringified; if the class has no __doc__ the literal 'None' appears.

<a id="u-baaec187caad"></a>
### `error.py module code (L36–L51)`

`module_region` · [src/_pytest/_py/error.py:L36-L51][f1]

Module-level _winerrnomap translating Windows error codes (2, 3→ENOENT; 17→EEXIST; 18→EXDEV; 13→EBUSY; 22, 20, 267→ENOTDIR; 5→EACCES) to errno constants; a constant table with no behavior.

<a id="u-8ca33451364a"></a>
### `ErrorMaker`

`class ErrorMaker:` · [src/_pytest/_py/error.py:L52-L60][f1]

Lazily creates and caches one Error subclass per POSIX errno so attribute access like ErrorMaker.ENOENT yields a class.

__getattr__ raises AttributeError for names starting with underscore, otherwise reads the name from the errno module, builds/caches the class via _geterrnoclass, caches it on the instance with setattr so later lookups skip __getattr__, and returns it. _geterrnoclass consults the _errno2class dict; on a miss it derives the class name from errno.errorcode (falling back to 'UnknownErrno{eno}'), creates the type with __module__='py.error' and __doc__=os.strerror(eno), caches, and returns it. checked_call runs func(*args, **kwargs) with __tracebackhide__=True; an Error propagates unchanged; an OSError without an errno attribute re-raises as-is; on win32 the errno is mapped through _winerrnomap with a KeyError fallback that re-raises the original OSError; elsewhere a None errno produces an 'UnknownErrnoNone' Error subclass and a real errno goes through _geterrnoclass. In all converted cases it raises the mapped class with the message '<funcname><args-repr>'.

**Notes.**

- side_effect: Attribute access caches the generated class on the ErrorMaker instance and in _errno2class, so class identity is stable per process.
- failure: checked_call raises the original OSError unchanged when win32 mapping misses (KeyError) or when the exception lacks .errno.
- contract: __getattr__ raising AttributeError for underscore names lets private attribute lookups fail normally instead of being misread as errno names.

inherits: [Error](r4-os-error-facade.md#u-dbb5fdb15669)

**Uncertainties.**

- In checked_call, the cls construction call could bind to an unrelated .cls property per the graph; the intended target is the locally built type() result, and OSError.errno being non-int on win32 would raise before the mapping.

<a id="u-1bb434798cfd"></a>
### `error.py module code (L111–L117)`

`module_region` · [src/_pytest/_py/error.py:L111-L117][f1]

Module tail: creates the singleton _error_maker = ErrorMaker(), binds module-level checked_call to its bound method, and defines the module __getattr__ below; no additional logic.

<a id="u-904753d19568"></a>
### `__getattr__`

`def __getattr__(attr: str) -> type[Error]:` · [src/_pytest/_py/error.py:L118-L119][f1]

Module-level __getattr__ (PEP 562): any unknown attribute of the py.error module is forwarded to the _error_maker singleton, so e.g. py.error.ENOENT returns the lazily generated Error subclass for that errno; underscore names raise AttributeError via ErrorMaker.__getattr__.

uses: [ErrorMaker](r4-os-error-facade.md#u-8ca33451364a)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_py/error.py
