# RaisesGroup Typing Tests

**Capability.** testing/typing_raises_group.py is a static-type-checking suite pinning RaisesGroup/RaisesExc overload surfaces, TypeVar defaults, context-manager result typing, and matches-based narrowing through arbitrary nesting depths; rejected overloads are pinned via type: ignore.

Read this when changing RaisesGroup/RaisesExc generics: it documents the intended type-level API. It checks types only, not runtime behavior.

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Units (14)

<a id="u-d72bc2e418bf"></a>
### `typing_raises_group.py-narrowing`

`def raisesgroup_check_type_narrowing() -> None:` · [testing/typing_raises_group.py:L95-L100][f1]

Two functions checking RaisesGroup's check-argument and container type narrowing.

raisesgroup_check_type_narrowing verifies the check callable's parameter type against the expected exceptions: for a single expected type T, check taking BaseExceptionGroup[BaseException] is always valid, while narrower callables (BaseExceptionGroup[KeyboardInterrupt], BaseExceptionGroup[ValueError]) are valid only when compatible with T — e.g. handle_kbi is rejected for ValueError and handle_value for KeyboardInterrupt, and both are rejected when two exception types are expected. raisesgroup_narrow_baseexceptiongroup verifies the container group type of the check parameter: RaisesGroup(ValueError) accepts check taking ExceptionGroup[ValueError], and RaisesGroup(Exception) accepts one taking ExceptionGroup[Exception]. All intended type errors carry type: ignore.

<a id="u-dbce9e12e7fd"></a>
### `check_basic_contextmanager`

`def check_basic_contextmanager() -> None:` · [testing/typing_raises_group.py:L36-L39][f1]

Uses RaisesGroup(ValueError) as a context manager catching an ExceptionGroup('foo', (ValueError(),)) and asserts the excinfo's .value is typed ExceptionGroup[ValueError].

<a id="u-3cfc10d10740"></a>
### `check_basic_matches`

`def check_basic_matches() -> None: # check that matches gets rid of the naked ValueEr…` · [testing/typing_raises_group.py:L42-L50][f1]

Verifies .matches narrows the tested exception union.

Given exc typed ExceptionGroup[ValueError] | ValueError: when RaisesGroup(ValueError).matches(exc) is true, exc narrows to ExceptionGroup[ValueError], removing the naked ValueError. When RaisesGroup(KeyboardInterrupt).matches(exc) is true, exc narrows to BaseExceptionGroup[KeyboardInterrupt], showing BaseExceptionGroup appears for BaseException matchers.

<a id="u-970bb1b23295"></a>
### `check_check_typing`

`def check_check_typing() -> None: # BaseExceptiongroup should perhaps be Exception…` · [testing/typing_raises_group.py:L239-L247][f1]

Asserts RaisesGroup(ValueError).check types as Callable[[BaseExceptionGroup[ValueError]], bool] | None; a comment notes BaseExceptionGroup may ideally be ExceptionGroup but is accepted as close enough.

<a id="u-87582ef9d85f"></a>
### `check_matches_with_different_exception_type`

`def check_matches_with_different_exception_type() -> None:` · [testing/typing_raises_group.py:L53-L62][f1]

Given a BaseExceptionGroup[KeyboardInterrupt], if RaisesGroup(ValueError).matches(e) is true, e narrows to ExceptionGroup[ValueError].

A comment notes that warning on this mismatched match is impossible under current typing, so no warning is expected.

<a id="u-4be1bac83a58"></a>
### `check_multiple_exceptions_1`

`def check_multiple_exceptions_1() -> None:` · [testing/typing_raises_group.py:L181-L190][f1]

RaisesGroup(ValueError, ValueError), RaisesGroup(RaisesExc(ValueError), RaisesExc(ValueError)) and the mixed form must all be assignable to a variable annotated RaisesGroup[ValueError], verifying heterogeneous element spellings share one type.

<a id="u-34176967a926"></a>
### `check_multiple_exceptions_2`

`def check_multiple_exceptions_2() -> None: # This previously failed due to lack of co…` · [testing/typing_raises_group.py:L193-L203][f1]

RaisesGroup over mixed element types (RaisesExc(ValueError), RaisesExc(TypeError), plain TypeError, and combinations) must all be assignable to RaisesGroup[Exception].

A comment notes this previously failed due to lack of covariance in the TypeVar.

<a id="u-639c21be7958"></a>
### `check_nested_raisesgroups_contextmanager`

`def check_nested_raisesgroups_contextmanager() -> None:` · [testing/typing_raises_group.py:L149-L167][f1]

Catches ExceptionGroup('foo', (ValueError(),)) with nested RaisesGroup(RaisesGroup(ValueError)).

The value is assignable to BaseExceptionGroup[BaseExceptionGroup[ValueError]] and assert_type narrows it to ExceptionGroup[ExceptionGroup[ValueError]]; .exceptions[0] types as the union ExceptionGroup[ValueError] | ExceptionGroup[ExceptionGroup[ValueError]], a comment attributes this union to how typeshed defines .exceptions.

<a id="u-96ca100776fc"></a>
### `check_nested_raisesgroups_matches`

`def check_nested_raisesgroups_matches() -> None:` · [testing/typing_raises_group.py:L170-L178][f1]

Given exc typed ExceptionGroup[ExceptionGroup[ValueError]], when nested RaisesGroup(RaisesGroup(ValueError)).matches(exc) is true, exc stays narrowed to ExceptionGroup[ExceptionGroup[ValueError]], verifying matches works through nesting.

<a id="u-99171483007d"></a>
### `check_raisesexc_init`

`def check_raisesexc_init() -> None:` · [testing/typing_raises_group.py:L65-L66][f1]

Checks RaisesExc constructor overloads.

At least one argument is required: RaisesExc() is a type error. expected_exception is positional-only (RaisesExc(expected_exception=ValueError) is an error); match and check are keyword-only (RaisesExc(ValueError, 'regex') is an error). Valid forms combine an exception type, match='regex', and check=callable in any subset. When exception_type is given, the check callable's parameter is narrowed to that type: check taking FileNotFoundError is valid with FileNotFoundError, but is a type error with ValueError or with no exception type; check taking BaseException is valid with any type.

<a id="u-e9706926a19b"></a>
### `check_raisesexc_transparent`

`def check_raisesexc_transparent() -> None:` · [testing/typing_raises_group.py:L142-L146][f1]

Using RaisesGroup(RaisesExc(ValueError)) as a context manager, the excinfo value must be assignable to BaseExceptionGroup[ValueError] and assert_type confirms ExceptionGroup[ValueError], verifying nested RaisesExc stays transparent in the resulting type.

<a id="u-10d8c86b4a9c"></a>
### `check_raisesexc_typevar_default`

`def check_raisesexc_typevar_default(e: RaisesExc) -> None:` · [testing/typing_raises_group.py:L29-L33][f1]

Verifies RaisesExc's TypeVar default: with a bare RaisesExc annotation, expected_exceptions must be typed as type[BaseException] or a tuple of such types (asserted non-None first), and e.exception_type().blah() still requires a type: ignore because the default type is BaseException, not Any as it previously was.

<a id="u-959c5fd7037f"></a>
### `check_raisesgroup_overloads`

`def check_raisesgroup_overloads() -> None: # allow_unwrapped=True does not allow: # m…` · [testing/typing_raises_group.py:L206-L231][f1]

Pins RaisesGroup's overload surface via allowed and rejected (type: ignore) constructor calls.

allow_unwrapped=True forbids multiple exceptions, a nested RaisesGroup, and specifying match or check; it allows a single exception type, flatten_subgroups=True, and a single RaisesExc. flatten_subgroups=True forbids a nested RaisesGroup but allows multiple exception types, match, check, a single type, or a single RaisesExc. With neither flag, everything including a nested RaisesGroup is allowed.

<a id="u-e9f284faff84"></a>
### `check_triple_nested_raisesgroup`

`def check_triple_nested_raisesgroup() -> None:` · [testing/typing_raises_group.py:L234-L236][f1]

Triple-nested RaisesGroup(RaisesGroup(RaisesGroup(ValueError))) as a context manager must give e.value typed ExceptionGroup[ExceptionGroup[ExceptionGroup[ValueError]]].

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/typing_raises_group.py
