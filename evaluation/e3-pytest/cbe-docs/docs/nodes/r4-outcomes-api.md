# Test outcome signals

**Capability.** Defines and raises the sentinel outcome exceptions behind pytest.skip/fail/xfail/exit and importorskip, deriving from BaseException so ordinary except-Exception handlers cannot swallow them.

Consult this subtree to see how outcome exceptions are represented and raised. Callable classes (_Skip, _Fail, _XFail, _Exit) are instantiated as the module-level public callables; residual regions are constants and bindings.

Parent: [Runtime library](r4-runtime-library.md)

## Units (24)

<a id="u-58f8b4f3406b"></a>
### `outcomes.py module code (L1–L13)`

`module_region` · [src/_pytest/outcomes.py:L1-L13][f1]

Module docstring and imports; no behavior.

<a id="u-a47395565d6d"></a>
### `OutcomeException`

`class OutcomeException(BaseException):` · [src/_pytest/outcomes.py:L14-L18][f1]

BaseException subclass whose instances indicate and carry information about test/collection outcomes; deliberately derives from BaseException so unrelated `except Exception` handlers do not swallow outcome exceptions.

Constructor and repr documented separately. Class-level data: TEST_OUTCOME is defined at module level as (OutcomeException, Exception).

<a id="u-d75fb9b8abb7"></a>
### `OutcomeException.__init__`

`def __init__(self, msg: str | None = None, pytrace: bool = True) -> None:` · [src/_pytest/outcomes.py:L18-L27][f1]

Stores the message and pytrace flag.

If msg is provided but is not a string, raises TypeError with a message naming the exception class and the offending value's type, hinting that a mark may have been used accidentally instead of a message.

**Notes.**

- failure: The TypeError is raised before calling super().__init__, so the exception instance is never constructed with a non-string msg.

<a id="u-51ab7f4fd960"></a>
### `OutcomeException.__repr__`

`def __repr__(self) -> str:` · [src/_pytest/outcomes.py:L29-L32][f1]

Returns the stored msg when set, otherwise a generic '<ClassName instance>' string; __str__ is bound to the same function.

<a id="u-d91334136c25"></a>
### `outcomes.py module code (L34–L39)`

`module_region` · [src/_pytest/outcomes.py:L34-L39][f1]

Defines TEST_OUTCOME = (OutcomeException, Exception), a constant used elsewhere to catch test-outcome errors; no behavior of its own.

<a id="u-8d9a08d00d92"></a>
### `Skipped`

`class Skipped(OutcomeException): # XXX hackish: on 3k we fake to live in the builtins…` · [src/_pytest/outcomes.py:L40-L45][f1]

OutcomeException for skips.

Fakes its __module__ as 'builtins' for shorter, nicer skip messages. The constructor adds allow_module_level (permit raising at module import time, stopping collection of the whole module) and the keyword-only _use_item_location, which when True reports the skip at the test item's location rather than the raise site.

<a id="u-27665288495a"></a>
### `Skipped.__init__`

`def __init__( self, msg: str | None = None, pytrace: bool = True, allow_module_level:…` · [src/_pytest/outcomes.py:L45-L57][f1]

Delegates msg/pytrace to OutcomeException.__init__ (so a non-string msg raises TypeError) and stores allow_module_level and _use_item_location on the instance.

<a id="u-14424057b703"></a>
### `src/_pytest/outcomes.py:Failed`

`class Failed(OutcomeException):` · [src/_pytest/outcomes.py:L60-L63][f1]

OutcomeException raised by an explicit pytest.fail() call; also fakes __module__ as 'builtins'.

No additional behavior beyond the base class.

<a id="u-9456420f5284"></a>
### `XFailed`

`class XFailed(Failed):` · [src/_pytest/outcomes.py:L77-L78][f1]

Failed subclass raised by an explicit pytest.xfail() call; adds no behavior.

<a id="u-bde7b7262dd0"></a>
### `Exit`

`class Exit(Exception):` · [src/_pytest/outcomes.py:L66-L69][f1]

Ordinary Exception raised for immediate program exits without tracebacks or summaries.

Constructor stores msg (default 'unknown reason') and returncode (None meaning like sys.exit's 0) before calling super().__init__(msg).

<a id="u-cc20abfa5fb4"></a>
### `Exit.__init__`

`def __init__( self, msg: str = "unknown reason", returncode: int | None = None ) -> N…` · [src/_pytest/outcomes.py:L69-L74][f1]

Sets self.msg and self.returncode from the arguments, then initializes the Exception with the message.

Unlike OutcomeException, no type validation of msg is performed.

<a id="u-d9944f5f7522"></a>
### `_Skip`

`class _Skip:` · [src/_pytest/outcomes.py:L106-L137][f1]

Callable implementing pytest.skip().

Its Exception attribute is Skipped. Calling it with __tracebackhide__ set raises Skipped(msg=reason, allow_module_level=allow_module_level); allow_module_level=True permits module-level use that halts collection of the entire module. The docstring recommends skipif markers or doctest SKIP directives for static cases.

<a id="u-1415bef5ab0b"></a>
### `outcomes.py module code (L139–L144)`

`module_region` · [src/_pytest/outcomes.py:L139-L144][f1]

Instantiates module-level `skip` as _Skip(); re-exported constant, no behavior.

<a id="u-4ae4f0fb6df6"></a>
### `_Skip.__call__`

`def __call__(self, reason: str = "", allow_module_level: bool = False) -> NoReturn:` · [src/_pytest/outcomes.py:L137-L139][f1]

Raises Skipped with the reason and allow_module_level flag; never returns.

<a id="u-172d32b1aad7"></a>
### `_Fail`

`class _Fail:` · [src/_pytest/outcomes.py:L145-L161][f1]

Callable implementing pytest.fail().

Its Exception attribute is Failed. Calling it with __tracebackhide__ set raises Failed(msg=reason, pytrace=pytrace); pytrace=False means the message is the full failure info and no Python traceback is reported.

<a id="u-26e63d2be709"></a>
### `outcomes.py module code (L163–L168)`

`module_region` · [src/_pytest/outcomes.py:L163-L168][f1]

Instantiates module-level `fail` as _Fail(); re-exported constant, no behavior.

<a id="u-08f2ffe3ad3d"></a>
### `_Fail.__call__`

`def __call__(self, reason: str = "", pytrace: bool = True) -> NoReturn:` · [src/_pytest/outcomes.py:L161-L163][f1]

Raises Failed with the given reason and pytrace flag; never returns.

<a id="u-ec398fd255d2"></a>
### `_XFail`

`class _XFail:` · [src/_pytest/outcomes.py:L169-L191][f1]

Callable implementing pytest.xfail().

Its Exception attribute is XFailed. Calling it with __tracebackhide__ set raises XFailed(msg=reason); no code runs after an xfail() call since it is implemented by raising. Docstring recommends the xfail marker for declarative use.

<a id="u-21f6636341b6"></a>
### `outcomes.py module code (L193–L198)`

`module_region` · [src/_pytest/outcomes.py:L193-L198][f1]

Instantiates module-level `xfail` as _XFail(); re-exported constant, no behavior.

<a id="u-0587140210df"></a>
### `_XFail.__call__`

`def __call__(self, reason: str = "") -> NoReturn:` · [src/_pytest/outcomes.py:L191-L193][f1]

Raises XFailed with the given reason; never returns.

<a id="u-96da642804cf"></a>
### `_Exit`

`class _Exit:` · [src/_pytest/outcomes.py:L81-L98][f1]

Callable implementing pytest.exit().

Its class attribute Exception is Exit, letting users reference the raised type as exit.Exception. Calling it (with __tracebackhide__ set so the frame is hidden from tracebacks) raises Exit(msg=reason, returncode=returncode); unlike the other callables it accepts an empty default reason.

<a id="u-fbeabee6dbb4"></a>
### `outcomes.py module code (L100–L105)`

`module_region` · [src/_pytest/outcomes.py:L100-L105][f1]

Instantiates the module-level `exit` callable as _Exit(); a re-exported constant with no behavior.

<a id="u-1a54ffe02b7e"></a>
### `_Exit.__call__`

`def __call__(self, reason: str = "", returncode: int | None = None) -> NoReturn:` · [src/_pytest/outcomes.py:L98-L100][f1]

Raises Exit with the given reason and returncode; never returns (NoReturn).

<a id="u-b6b96116e0b8"></a>
### `importorskip`

`def importorskip( modname: str, minversion: str | None = None, reason: str | None = N…` · [src/_pytest/outcomes.py:L199-L308][f1]

Imports and returns the module `modname`, skipping the current test if the import fails.

Hides its own traceback and compiles modname first to catch syntax errors in the name. Unless exc_type is given, exc_type defaults to ImportError and warn_on_import_error is True; an explicit exc_type disables the warning. Inside a catch_warnings block with simplefilter('ignore') (to suppress ImportWarnings from shadowing directories), it imports the module; on a matching exception it builds the skip reason (using the provided reason or 'could not import ...' with the exception) as a module-level Skipped, and, if warning on import errors and the caught exception is not a ModuleNotFoundError, prepares a PytestDeprecationWarning explaining that in pytest 9.1 this becomes an error and how to silence it with exc_type=ImportError. Outside the warnings block, it issues the warning (stacklevel 2) then raises the Skipped. On success, retrieves the module from sys.modules; if minversion is given, lazily imports packaging.version.Version and skips with a version-mismatch message when the module lacks __version__ or its version is below the minimum; otherwise returns the module.

**Notes.**

- side_effect: Defers raising and warning until after the catch_warnings block so the deprecation warning is not swallowed by the ignore filter.
- failure: Non-ImportError failures from __import__ propagate uncaught, since only exc_type is caught.

**Uncertainties.**

- The redundant `if minversion is not None` re-check after the earlier None test suggests possible refactoring residue; behavior is unaffected.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/outcomes.py
