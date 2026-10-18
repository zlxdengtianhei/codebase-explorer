# Single-exception matcher

**Capability.** The pytest.raises entry point and its RaisesExc context manager: constructing a matcher for one expected type (or None with only match/check), __exit__ pass/fail semantics, standalone matches(), and repr rendering.

Use this subtree for the everyday pytest.raises(exc, match=..., check=...) contract. The public raises() function delegates construction to RaisesExc.__init__; __exit__ implements the decision.

**Depends on.**

- [Shared matcher core](r4-raises-shared-matching.md) · graph-confirmed · 7 edge(s)

**Depended on by.**

- [ExceptionGroup matcher](r4-raises-group.md) · model-inferred · 0 edge(s)

Parent: [Exception assertion helpers](r4-raises-module.md)

## Units (6)

<a id="u-94d30f76e4a0"></a>
### `src/_pytest/raises.py:raises (4)`

`def raises( expected_exception: type[E] | tuple[type[E], ...] | None = None, *args: A…` · [src/_pytest/raises.py:L104-L300][f1]

Implements `pytest.raises`, asserting that a code block raises an exception; it returns either a context-manager `RaisesExc` or, in the legacy callable form, a filled `ExceptionInfo`.

With no positional args it rejects unexpected keyword arguments with a TypeError listing them and suggesting the context-manager form, then returns `RaisesExc(**kwargs)` or `RaisesExc(expected_exception, **kwargs)`. In the legacy form with a callable, an empty or falsy expected_exception raises ValueError explaining that raising already fails the test; a non-callable first arg raises TypeError. It then runs the callable inside `RaisesExc(expected_exception)` and returns the populated excinfo, deleting the local reference in a finally block to aid garbage collection of the reference cycle. `__tracebackhide__` is set so tracebacks hide this frame.

calls: [RaisesExc](r4-raises-exc.md#u-3ca686c673f1); uses: [raises.py module code (L300–L313)][f1]

**Uncertainties.**

- ExceptionInfo population semantics live in ExceptionInfo, outside this file.
- Which of the four overloads type checkers select is not determinable from the implementation.

<a id="u-3ca686c673f1"></a>
### `RaisesExc`

`class RaisesExc(AbstractRaises[BaseExcT_co_default]):` · [src/_pytest/raises.py:L542-L589][f1]

The matcher object constructed by `pytest.raises` for a single expected exception type (or None when only match/check are used), also reusable inside RaisesGroup for sub-exception requirements.

It stores expected exceptions, match, and check via AbstractRaises, and acts as a context manager that fills an `ExceptionInfo` on success. Small accessors `_check_type` (sets `_fail_reason` from `_check_raw_type` and returns whether it is None) and `__enter__` (creates `ExceptionInfo.for_later()` and returns it) have no separate behavior beyond what `matches` and `__exit__` show.

<a id="u-dca7c560f621"></a>
### `src/_pytest/raises.py:RaisesExc.__init__ (3)`

`def __init__( self, expected_exception: ( type[BaseExcT_co_default] | tuple[type[Base…` · [src/_pytest/raises.py:L614-L640][f1]

Builds a RaisesExc from a positional expected exception (a type, tuple of types, or None) plus optional match/check.

It first initializes shared state via the AbstractRaises constructor, then normalizes the expectation to a tuple (None becomes empty). If the tuple is empty and both match and check are None it raises ValueError requiring at least one parameter. Each element is validated through `_parse_exc` and stored in `expected_exceptions`; `_just_propagate` is initialized to False. The three overloads exist only for typing: a positional type/tuple with keywords, match-only (self typed as RaisesExc[BaseException]), and check-only forms.

calls: [AbstractRaises._parse_exc](r4-raises-shared-matching.md#u-d509d34fa11b), [AbstractRaises.__init__](r4-raises-shared-matching.md#u-6e670e7645b6)

<a id="u-b767cb06d7bd"></a>
### `RaisesExc.__exit__`

`def __exit__( self, exc_type: type[BaseException] | None, exc_val: BaseException | No…` · [src/_pytest/raises.py:L699-L730][f1]

Context-manager exit implementing pytest.raises semantics, with tracebacks hidden.

If no exception was raised it fails with `fail(...)`, choosing between 'DID NOT RAISE any exception' (when no expected types were given), a repr of all expected types when several were expected, or the single expected type repr. When an exception arrived but `self.excinfo` is missing it asserts an internal error. If `matches(exc_val)` fails with `_just_propagate` set — a pure type mismatch — it returns False so the original exception propagates unchanged; other match failures raise AssertionError carrying `_fail_reason`. On success it fills the previously unfilled ExceptionInfo with the narrowed (type, value, traceback) tuple and returns True, suppressing the exception.

**Notes.**

- failure: Type-only mismatches re-raise the original exception by returning False instead of AssertionError.

calls: [RaisesExc.matches](r4-raises-exc.md#u-7ff7ba34a27f), [function::fail][f2]; uses: [AbstractRaises](r4-raises-shared-matching.md#u-2a4cdf055c84)

**Uncertainties.**

- The graph lists three candidate `matches` targets; on RaisesExc instances it is RaisesExc.matches, but dispatch is dynamic.

<a id="u-7ff7ba34a27f"></a>
### `RaisesExc.matches`

`def matches( self, exception: BaseException | None, ) -> TypeGuard[BaseExcT_co_default]:` · [src/_pytest/raises.py:L642-L675][f1]

Standalone check of one exception against type, match regex, and check predicate in that order, recording the first failure reason.

Resets `_just_propagate` to False on entry. A None exception sets reason 'exception is None' and fails. Failing `_check_type` sets `_just_propagate` to True before returning False — a flag `__exit__` uses to distinguish a pure type mismatch (which should propagate the original exception rather than assert) — then `_check_match` and `_check_check` failures simply return False with their recorded reasons.

calls: [AbstractRaises._check_check](r4-raises-shared-matching.md#u-82b6e36216ab), [AbstractRaises._check_match](r4-raises-shared-matching.md#u-0fcba48753df), [RaisesExc](r4-raises-exc.md#u-3ca686c673f1); uses: [RaisesExc.__exit__](r4-raises-exc.md#u-b767cb06d7bd)

<a id="u-b10ce9ef1d21"></a>
### `RaisesExc.__repr__`

`def __repr__(self) -> str:` · [src/_pytest/raises.py:L677-L688][f1]

Renders the matcher as `RaisesExc(...)` from optional parts: the exception type name(s) via `_exception_type_name`, `match=<pattern repr>` using `_match_pattern` to drop a redundant `re.compile` when no flags were set, and `check=<repr>` via `repr_callable`.

Each part appears only when set.

uses: [raises.py-regex-helpers](r4-raises-shared-matching.md#u-a954012eb21c)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/raises.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/outcomes.py
