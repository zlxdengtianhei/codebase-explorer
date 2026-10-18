# Warning Capture Test Suite

**Capability.** Tests of the warning-capture API surface: WarningsRecorder/WarningsChecker protocol, pop with category hierarchies, pytest.warns, and pytest.deprecated_call in both call and context-manager modes.

Use this to find contracts for recwarn and warns behavior; the top-level group covers module-level test functions including DeprecationWarning capture.

Parent: [pytest Core](r9-pytest-core.md)

## Units (6)

<a id="u-45bafe519ab0"></a>
### `test_recwarn-py-top-level-tests`

`def test_recwarn_stacklevel(recwarn: WarningsRecorder) -> None:` · [testing/test_recwarn.py:L13-L16][f1]

Covers the module-level test functions of test_recwarn.py, which exercise recwarn, pytest.warns input validation, and DeprecationWarning capture.

test_recwarn_stacklevel warns and checks recwarn.pop() reports this file as the warning's filename (stacklevel attribution). test_recwarn_functional runs an inline pytester test using the recwarn fixture and asserts one pass. test_recwarn_captures_deprecation_warning, under an empty filterwarnings mark, asserts recwarn captures DeprecationWarning by default and pop(DeprecationWarning) returns it. test_raise_type_error_on_invalid_warning and the cpython-specific variant check that warnings.warn(1) raises TypeError (the latter via the stdlib with filtering enabled, skipped on pypy). test_no_raise_type_error_on_valid_warning parametrizes valid messages (str, UserWarning, Warning) and expects no error. test_multiple_arg_custom_warning defines CustomWarning with a two-arg __init__ and verifies a non-matching match argument fails with DID NOT WARN even for custom warning classes.

calls: [WarningsRecorder.pop](r3-recwarn.md#u-10692f5a6904), [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

**Uncertainties.**

- Whether pytest.warns(None) raising TypeError is asserted anywhere in this file is not shown; test_record_only_none_type_error is folded into the TestWarns unit.

<a id="u-f786960f15e7"></a>
### `TestDeprecatedCall`

`class TestDeprecatedCall:` · [testing/test_recwarn.py:L132-L135][f1]

Tests pytest.deprecated_call in call and context-manager modes against helper methods dep (warns DeprecationWarning when i==0, returns 42) and dep_explicit (warn_explicit variant).

When no matching warning is emitted, deprecated_call raises pytest.fail.Exception with 'No warnings of type'; on success it returns the function's return value. test_deprecated_call_preserves snapshots warnings.onceregistry, warnings.filters, and the warn/warn_explicit functions and asserts both call modes leave them unchanged. test_deprecated_call_no_warning covers both modes failing when nothing warns. test_deprecated_call_modes parametrizes PendingDeprecationWarning/DeprecationWarning/FutureWarning, both modes, and calling f beforehand (with an 'ignore' filterwarnings mark) to prove already-triggered warnings are still captured. test_deprecated_call_specificity asserts six other warning categories do not satisfy deprecated_call. test_deprecated_call_supports_match shows match regex support and a DID NOT WARN failure on non-match. test_deprecated_explicit_call asserts dep_explicit works and is idempotent across two calls.

<a id="u-aea0bf1fe4cf"></a>
### `TestSubclassWarningPop`

`class TestSubclassWarningPop:` · [testing/test_recwarn.py:L44-L45][f1]

Tests how WarningsRecorder.pop matches warnings when queried with a parent warning category.

It defines a three-level Warning hierarchy (ParentWarning, ChildWarning, ChildOfChildWarning) and a static helper raise_warnings_from_list that emits one warning per given category using warnings.warn. test_pop_finds_exact_match captures three warnings and verifies pop(ParentWarning) returns the exact-category warning. test_pop_raises_if_no_match expects an AssertionError when popping a category never emitted. test_pop_finds_best_inexact_match shows that with no exact match, pop returns the closest subclass (ChildWarning) rather than the deeper ChildOfChildWarning.

calls: [WarningsRecorder.pop](r3-recwarn.md#u-10692f5a6904)

<a id="u-6e5cebfc4d4f"></a>
### `TestWarningsRecorderChecker`

`class TestWarningsRecorderChecker:` · [testing/test_recwarn.py:L85-L86][f1]

Tests WarningsRecorder/WarningsChecker construction and context-manager protocol directly.

test_recording builds a recorder, asserts warnings accumulate in rec.list, pop removes the most recent warning, clear() empties the same list object in place, and pop on an empty list raises AssertionError. test_warn_stacklevel warns with stacklevel=2 inside a recorder. test_typechecking asserts WarningsChecker raises TypeError for non-warning-type arguments (int, str tuple, plain list). test_invalid_enter_exit asserts RuntimeError on __exit__ before __enter__ and on nested double entry, wrapping the whole test in a recorder to reset warning state.

<a id="u-99021e80f0a8"></a>
### `TestWarns`

`class TestWarns:` · [testing/test_recwarn.py:L251-L252][f1]

Exhaustively tests pytest.warns.

Construction/typing: non-callable second positional arg raises TypeError ('must be callable'); warns(None) raises TypeError; unexpected keyword arguments raise TypeError. Matching: warns accepts a class or tuple of classes, matches subclasses to the given bases, and supports a match regex against the message; mismatch or no warning raises pytest.fail.Exception with a DID NOT WARN message that lists emitted warnings (verified exactly for tuple expectations). Recording: the context-manager record supports indexing and length; with no expected class it records all warnings. Re-emission: warnings caught by an inner warns are not re-emitted to outer warns blocks (verified even under simplefilter('error')). Interaction with control flow: pytest.raises inside warns and warns inside raises both work; pytest.skip, pytest.fail, pytest.exit, and KeyboardInterrupt raised inside a warns block propagate correctly without a spurious DID NOT WARN failure (the interrupt case runs via runpytest_subprocess). Nested warns for multiple warnings report each message. Finally, warns can capture warnings already emitted earlier (with 'ignore' filtering), and repeated warns of an already-warned function still succeed.

calls: [ExceptionInfo.match](r1-code-exception-info.md#u-a3736b28ef2f), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346), [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f)

<a id="u-f5ddce318841"></a>
### `test_recwarn.py module code (L1–L12)`

`module_region` · [testing/test_recwarn.py:L1-L12][f1]

Module header: mypy pragma, __future__ annotations, and imports (sys, warnings, pytest, ExitCode, Pytester, WarningsRecorder).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_recwarn.py
