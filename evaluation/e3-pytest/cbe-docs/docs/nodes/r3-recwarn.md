# Warning Assertion Helpers

**Capability.** The recwarn fixture and warns/deprecated_call context managers: record warnings within a scope and assert on their classes, with WarningsChecker adding exit-time assertion behavior on top of WarningsRecorder.

Use this subtree to see how tests assert that code warns. The recorder is the list-like base; WarningsChecker.__exit__ enforces expectations; deprecated_call delegates to warns with deprecation classes.

**Depends on.**

- [Warning Capture Hooks](r3-warning-capture.md) · model-inferred · 0 edge(s)
- [Warning Categories](r3-warning-types.md) · model-inferred · 0 edge(s)

Parent: [Pytest Framework Codebase](r3-pytest.md)

## Units (8)

<a id="u-15834f1dbb94"></a>
### `recwarn.py module code (L1–L32)`

`module_region` · [src/_pytest/recwarn.py:L1-L32][f1]

Module imports and the TypeVar alias for recwarn.

<a id="u-80504c936d9f"></a>
### `WarningsRecorder`

`class WarningsRecorder(warnings.catch_warnings):` · [src/_pytest/recwarn.py:L170-L183][f1]

Reusable context manager (subclass of warnings.catch_warnings(record=True)) that records every warning emitted inside it as warnings.WarningMessage objects, accessible via `list`, indexing, iteration, and len.

`__init__` requires internal construction via check_ispytest. `__enter__` rejects double entry with RuntimeError, binds the internal recorded list from catch_warnings, and sets the filter to 'always'; `__exit__` rejects exit without entry with RuntimeError, restores the prior warnings state via super().__exit__, and resets `_entered` so the recorder can be reused. `clear` empties the recorded list in place. Trivial accessors delegate to `_list`.

<a id="u-10692f5a6904"></a>
### `WarningsRecorder.pop`

`def pop(self, cls: type[Warning] = Warning) -> warnings.WarningMessage:` · [src/_pytest/recwarn.py:L206-L223][f1]

Removes and returns the best matching recorded warning of class `cls`.

An exact category equality returns immediately. Otherwise it tracks the first warning that is a subclass of `cls` but not a subclass of a previously found match (i.e., the most specific match); if any, that one is popped. No match raises AssertionError (hidden from tracebacks).

<a id="u-25758f949086"></a>
### `WarningsChecker`

`class WarningsChecker(WarningsRecorder):` · [src/_pytest/recwarn.py:L259-L261][f1]

WarningsRecorder subclass adding assertion behavior.

`__init__` validates `expected_warning`: a tuple must contain only Warning subclasses, a single class must be a Warning subclass, anything else raises TypeError ('exceptions must be derived from Warning'); stores the normalized tuple and the optional match regex. `matches` reports whether a recorded warning's category is a subclass of the expected tuple and, when match_expr is set, whether re.search finds the pattern in str(message).

<a id="u-0f2a71f41aa4"></a>
### `WarningsChecker.__exit__`

`def __exit__( self, exc_type: type[BaseException] | None, exc_val: BaseException | No…` · [src/_pytest/recwarn.py:L293-L314][f1]

On context exit, first restores the warnings state via the recorder's __exit__.

If the body raised, control-flow exceptions propagate unchanged: any non-Exception BaseException (pytest.skip/fail/xfail/exit-adjacent, KeyboardInterrupt) — plus `Exit`, which is an Exception — returns without any warning check or re-emission. Only when the body succeeded (or raised an ordinary Exception other than Exit) does it verify expectations: no warning of the expected types at all fails with 'DID NOT WARN ... No warnings of type ... were emitted'; warnings of the right type but none matching the regex fail with the regex shown. Both failure messages embed a pretty-printed list of emitted warning messages. In a finally block, every non-matching recorded warning is re-emitted with warnings.warn_explicit (original category, location, source), and a guard raises TypeError when a UserWarning's first message argument is not a str — treated as a Warning constructed with an invalid non-str/non-Warning argument, since an explicitly-built UserWarning with non-str first arg is indistinguishable from the invalid case.

**Uncertainties.**

- The TypeError guard can false-positive when a UserWarning was deliberately constructed with a non-str first argument, as the code comment acknowledges.
- Re-emitted unmatched warnings may themselves be caught by an enclosing checker, changing outer results.

<a id="u-50e45f1c6a15"></a>
### `recwarn`

`def recwarn() -> Generator[WarningsRecorder]:` · [src/_pytest/recwarn.py:L33-L42][f1]

Fixture that yields a WarningsRecorder active for the test: it enters the recorder, sets the warnings filter to 'default', and yields; exiting the with block on fixture teardown restores the prior warnings state.

<a id="u-1fa0642b3db3"></a>
### `src/_pytest/recwarn.py:warns (2)`

`def warns( expected_warning: type[Warning] | tuple[type[Warning], ...] = Warning, *ar…` · [src/_pytest/recwarn.py:L106-L167][f1]

Asserts that code raises a warning of the expected class(es).

With no positional args it must be a context manager: any keyword arguments other than `match` raise TypeError with a hint to use the context-manager form; otherwise returns a WarningsChecker (default expected_warning Warning, with optional match regex). With a callable first argument it validates the argument is callable (TypeError otherwise), enters a WarningsChecker, calls func with the remaining args/kwargs, and returns the function's return value; the checker's __exit__ enforces the warning and re-emits unmatched warnings.

<a id="u-2bc149591007"></a>
### `src/_pytest/recwarn.py:deprecated_call (2)`

`def deprecated_call( func: Callable[..., Any] | None = None, *args: Any, **kwargs: An…` · [src/_pytest/recwarn.py:L55-L86][f1]

Asserts that code emits DeprecationWarning, PendingDeprecationWarning, or FutureWarning.

With no positional function argument it delegates to warns with those classes and passes `match` through as a context manager; with a callable first argument it prepends it to args so warns runs the function and returns its return value. Sets __tracebackhide__ to hide internals from tracebacks.

calls: [src/_pytest/recwarn.py:warns (2)](r3-recwarn.md#u-1fa0642b3db3)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/recwarn.py
