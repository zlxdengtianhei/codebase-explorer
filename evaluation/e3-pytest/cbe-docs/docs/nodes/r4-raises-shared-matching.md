# Shared matcher core

**Capability.** State and subroutines common to both matchers: AbstractRaises storage of match/check state, argument parsing to concrete types, regex and check-predicate application, raw-type diagnostics, and shared string/regex formatting helpers.

Read here to understand how any matcher validates type, message regex, and predicate. Changes here affect all raises() semantics because RaisesExc and RaisesGroup both call into it.

**Depended on by.**

- [Single-exception matcher](r4-raises-exc.md) · graph-confirmed · 7 edge(s)
- [ExceptionGroup matcher](r4-raises-group.md) · graph-confirmed · 13 edge(s)

Parent: [Exception assertion helpers](r4-raises-module.md)

## Units (7)

<a id="u-a954012eb21c"></a>
### `raises.py-regex-helpers`

`def _match_pattern(match: Pattern[str]) -> str | Pattern[str]:` · [src/_pytest/raises.py:L314-L316][f1]

Small string/regex formatting helpers shared by RaisesExc and RaisesGroup for building match diagnostics and reprs.

`_match_pattern` returns `match.pattern` when the compiled pattern was created with no flags, so `re.compile` is not shown redundantly in output; otherwise it returns the Pattern itself. `repr_callable` returns `repr(fun)` for a check callable and is intentionally split out so tools like hypothesis can monkeypatch it. `backquote` wraps a string in backticks. `_exception_type_name` renders an expected exception spec as a name: a plain type yields `__name__`, a one-element tuple that element's name, and a multi-element tuple `(Name1, Name2, ...)`. `is_fully_escaped` reports whether a string contains no unescaped regex metacharacters from `{}()+.*?^$[]` (a character preceded by a backslash does not count); whitespace needs no escaping since re.VERBOSE is never compiled. `unescape` removes backslashes before those metacharacters (plus whitespace and backslash) via `re.sub`, recovering a literal string from an anchored fully-escaped pattern.

uses: [AbstractRaises.__init__](r4-raises-shared-matching.md#u-6e670e7645b6), [_check_raw_type](r4-raises-shared-matching.md#u-394c03698150)

**Uncertainties.**

- Exact consumers of repr_callable monkeypatching are outside this file.

<a id="u-2a4cdf055c84"></a>
### `AbstractRaises`

`class AbstractRaises(ABC, Generic[BaseExcT_co]):` · [src/_pytest/raises.py:L382-L385][f1]

ABC holding the state and matching subroutines shared by RaisesExc and RaisesGroup: a compiled or given `match` pattern, an optional `check` callable, a lazily set `_fail_reason`, and an `is_baseexception` flag.

It is generic over the expected exception type and constructed from expectations, unlike ExceptionInfo which wraps a caught exception. The abstract `matches` contract requires implementers to set `fail_reason` when returning False. Class-header code between method groups carries no separate behavior.

<a id="u-6e670e7645b6"></a>
### `AbstractRaises.__init__`

`def __init__( self, *, match: str | Pattern[str] | None, check: Callable[[BaseExcT_co…` · [src/_pytest/raises.py:L385-L435][f1]

Stores the shared match/check state and derives a fast-path raw string for diffable match failures.

For a string `match`, it compiles it, swallowing a `re.error` into a local so it can raise a test `fail` with the invalid-pattern message (propagating the pytest Failed outcome rather than re.error); an empty string additionally warns via PytestWarning that it always matches. Non-string patterns are stored as-is. When the pattern is a plain string or a no-flags Pattern whose text is anchored `^...$` and fully escaped in the middle, `rawmatch` is set to the unescaped literal interior, enabling a text diff on mismatch; otherwise rawmatch stays None. Initializes `check`, `_fail_reason` to None, `_nested` to False (suppressing repeated repr of check in nested contexts), and `is_baseexception` to False for `_parse_exc` to overwrite.

**Notes.**

- side_effect: Compiles user regex at construction time and emits a PytestWarning for empty match strings.

uses: [raises.py-regex-helpers](r4-raises-shared-matching.md#u-a954012eb21c); contract: [AbstractRaises._parse_exc](r4-raises-shared-matching.md#u-d509d34fa11b)

**Uncertainties.**

- The comment 'necessary?' marks the re.error juggling as possibly redundant; only the fail outcome is observable here.

<a id="u-d509d34fa11b"></a>
### `AbstractRaises._parse_exc`

`def _parse_exc( self, exc: type[BaseExcT_1] | types.GenericAlias, expected: str ) -> …` · [src/_pytest/raises.py:L437-L472][f1]

Validates one expected-exception argument and returns the concrete type to store, setting `is_baseexception` as a side effect.

A real BaseException subclass is returned directly and flagged if it is not an Exception subclass. A generic alias whose origin is a BaseExceptionGroup is accepted only as `ExceptionGroup[Exception]`/`ExceptionGroup[Any]` or `BaseExceptionGroup[BaseException]`/`BaseExceptionGroup[Any]`, returning the origin group type (and setting is_baseexception in the BaseExceptionGroup cases); any other generic argument raises ValueError pointing to RaisesGroup for nested checks. Anything else fails with ValueError if given a non-exception type, TypeError if given an exception instance, and TypeError for other kinds.

uses: [src/_pytest/raises.py:RaisesExc.__init__ (3)](r4-raises-exc.md#u-dca7c560f621); overrides: [RaisesGroup._parse_excgroup](r4-raises-group.md#u-fc915a276c7f)

<a id="u-82b6e36216ab"></a>
### `AbstractRaises._check_check`

`def _check_check( self: AbstractRaises[BaseExcT_1], exception: BaseExcT_1, ) -> bool:` · [src/_pytest/raises.py:L481-L493][f1]

Applies the stored `check` predicate to an exception.

With no check it returns True unconditionally. If the predicate returns falsy, it records a `_fail_reason` of the form `check <repr> did not return True` — omitting the repr when `self._nested` is set to avoid repetition in nested contexts — and returns False. Returning True leaves `_fail_reason` untouched from earlier stages.

uses: [RaisesExc.matches](r4-raises-exc.md#u-7ff7ba34a27f), [src/_pytest/raises.py:RaisesGroup.matches (2)](r4-raises-group.md#u-f641ac0065c8)

**Uncertainties.**

- A check returning a truthy non-bool is treated as a match; only None-check and falsy path are explicit.

<a id="u-0fcba48753df"></a>
### `AbstractRaises._check_match`

`def _check_match(self, e: BaseException) -> bool:` · [src/_pytest/raises.py:L496-L531][f1]

Tests the exception's stringified message (excluding nested-group subexception text) against the stored regex with `re.search`, including PEP 678 notes as documented.

Match is None or a successful search returns True. On failure it sets `_fail_reason` in one of two shapes: if a `rawmatch` literal exists it builds a text diff via `_pytest.assertion.util._diff_text` with a dummy highlighter, prefixed by a newline when the diff starts with '-'; otherwise a message showing the regex and input, appending the type name when the exception is a group, and appending a hint to `re.escape()` when the pattern text equals the input string. Both failure paths return False.

**Notes.**

- side_effect: Imports _pytest.assertion.util lazily inside the rawmatch branch.

uses: [raises.py-regex-helpers](r4-raises-shared-matching.md#u-a954012eb21c), [src/_pytest/raises.py:RaisesGroup.matches (2)](r4-raises-group.md#u-f641ac0065c8), [RaisesExc.matches](r4-raises-exc.md#u-7ff7ba34a27f)

**Uncertainties.**

- The imported _diff_text behavior (formatting of diff tuples) is outside this file.

<a id="u-394c03698150"></a>
### `_check_raw_type`

`def _check_raw_type( expected_type: type[BaseException] | tuple[type[BaseException], …` · [src/_pytest/raises.py:L341-L361][f1]

Type-checks one exception against an expected type and returns None on success or a diagnostic string on failure.

If the expected type is None or the empty tuple it returns None without checking. If the exception is not an instance of the expected type(s), two message shapes are produced: when the exception is a BaseExceptionGroup and the expectation is a single non-group type, the message says the nested group type was unexpected; otherwise it states `Actual() is not an instance of Expected`. It relies on `_exception_type_name` for naming and does not itself modify `_fail_reason`.

uses: [raises.py-regex-helpers](r4-raises-shared-matching.md#u-a954012eb21c), [RaisesExc](r4-raises-exc.md#u-3ca686c673f1), [RaisesGroup._check_expected](r4-raises-group.md#u-ad466ac330da)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/raises.py
