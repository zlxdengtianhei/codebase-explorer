# ExceptionGroup matcher

**Capability.** Structural matching of (Base)ExceptionGroups against expectations (types, RaisesExc, nested RaisesGroup): validation, unrolling/flattening, greedy pairing with ResultHolder bookkeeping plus backtracking via possible_match, failure messages, and repr/expected-signature rendering.

Use this subtree for pytest.raises(ExceptionGroup, ...) semantics. It reuses the shared matcher core per expectation and coordinates pairwise results through ResultHolder and _check_exceptions.

**Depends on.**

- [Single-exception matcher](r4-raises-exc.md) · model-inferred · 0 edge(s)
- [Shared matcher core](r4-raises-shared-matching.md) · graph-confirmed · 13 edge(s)

Parent: [Exception assertion helpers](r4-raises-module.md)

## Units (12)

<a id="u-b0e1234080f6"></a>
### `RaisesGroup`

`class RaisesGroup(AbstractRaises[BaseExceptionGroup[BaseExcT_co]]):` · [src/_pytest/raises.py:L733-L848][f1]

Context manager matching an expected BaseExceptionGroup/ExceptionGroup against a structural list of expected sub-exceptions (plain types, RaisesExc, or nested RaisesGroup), requiring every expected exception to be present and no unexpected ones, order-independent.

Supports `match`/`check` on the group itself, `allow_unwrapped` (accept a bare exception when a single non-RaisesGroup expectation is given; incompatible with multiple exceptions, nested RaisesGroup, and match/check), and `flatten_subgroups` (flatten nested groups before matching; incompatible with nested RaisesGroup expectations). Matching is greedy, which can mispair ambiguous exceptions; __enter__/__enter__ overloads only create and return an `ExceptionInfo.for_later()`. Note in the class docstring that match strips the `(5 subgroups)` suffix from the repr before matching.

**Notes.**

- contract: expected_exceptions may mix types, RaisesExc, and RaisesGroup; tuple expectations are rejected.

**Uncertainties.**

- How the repr-stripping for match mentioned in the docstring is implemented is not visible in this file's shown source.

<a id="u-ae60a5bf9707"></a>
### `src/_pytest/raises.py:RaisesGroup.__init__ (8)`

`def __init__( self: RaisesGroup[ExcT_1 | BaseExcT_1 | BaseExceptionGroup[BaseExcT_2]]…` · [src/_pytest/raises.py:L950-L1011][f1]

Validates and stores group expectations.

After casting `check` for the super constructor and initializing allow_unwrapped, flatten_subgroups, and resetting is_baseexception, it enforces three allow_unwrapped constraints with ValueError: multiple positional expectations are rejected (suggesting RaisesExc for variable types), a RaisesGroup expectation is rejected as unaffected, and match or check is rejected because unwrapped exceptions bypass them. Expectations are then normalized through `_parse_excgroup` into `expected_exceptions`, which also ORs nested objects' is_baseexception flags into self. The many overloads exist purely to narrow the typevars for different combinations of types, RaisesExc, and nested RaisesGroup.

calls: [RaisesGroup._parse_excgroup](r4-raises-group.md#u-fc915a276c7f), [AbstractRaises.__init__](r4-raises-shared-matching.md#u-6e670e7645b6)

<a id="u-fc915a276c7f"></a>
### `RaisesGroup._parse_excgroup`

`def _parse_excgroup( self, exc: ( type[BaseExcT_co] | types.GenericAlias | RaisesExc[…` · [src/_pytest/raises.py:L1013-L1047][f1]

Normalizes one RaisesGroup expectation before delegating to the shared parser.

A nested RaisesGroup is rejected when `flatten_subgroups` is set (a flattened raise can never match nested structure, ValueError); otherwise it ORs the nested object's is_baseexception into self, marks the nested object `_nested` to suppress repeated reprs, and returns it. RaisesExc expectations get the same _nested flag and is_baseexception propagation. A tuple expectation raises TypeError explaining that RaisesGroup needs separate arguments for multiple exceptions. Any other value falls through to `AbstractRaises._parse_exc` for plain type/generic validation.

calls: [AbstractRaises._parse_exc](r4-raises-shared-matching.md#u-d509d34fa11b); uses: [src/_pytest/raises.py:RaisesGroup.__init__ (8)](r4-raises-group.md#u-ae60a5bf9707)

<a id="u-12875509fc95"></a>
### `RaisesGroup._unroll_exceptions`

`def _unroll_exceptions( self, exceptions: Sequence[BaseException], ) -> Sequence[Base…` · [src/_pytest/raises.py:L1080-L1092][f1]

Recursively flattens nested BaseExceptionGroups in a sequence of exceptions into a flat list, used when `flatten_subgroups=True` so nested groups' members compete directly for matches.

Non-group exceptions are appended unchanged; groups recurse into their `.exceptions`.

uses: [src/_pytest/raises.py:RaisesGroup.matches (2)](r4-raises-group.md#u-f641ac0065c8)

<a id="u-f641ac0065c8"></a>
### `src/_pytest/raises.py:RaisesGroup.matches (2)`

`def matches( self, exception: BaseException | None, ) -> bool:` · [src/_pytest/raises.py:L1105-L1226][f1]

Full matcher for one exception against the group's structure, recording why it failed on `_fail_reason`.

None fails immediately. A non-group exception produces `X() is not an exception group`; when a single expectation is given it additionally probes `_check_expected` on the bare exception: a successful probe returns True only if `allow_unwrapped` is set, otherwise the reason notes it would match with allow_unwrapped, or the probe's own reason when allow_unwrapped allows reporting it. For real groups it optionally flattens subgroups, then checks the group-level regex/match; on failure, if there is exactly one expected type and one actual exception of that type whose inner `_check_match` succeeds, it augments the reason suggesting `RaisesExc(<T>, match=...)`. Next `_check_exceptions` pairs expectations with actuals; failure may append a `flatten_subgroups=True` hint when no nested structure was expected but nested groups exist and a flattened second pass succeeds (indenting the hint only for single-line reasons). Finally `_check_check` runs on the group; if it fails, the reason is suffixed with the group type, and when one expected type's predicate would return True for the single actual exception, a hint to use RaisesExc with check is appended. All failure paths return False; full success returns True.

**Notes.**

- failure: Greedy pairing means structurally satisfiable inputs can still fail; the reason may suggest more stringent RaisesExc expectations.

calls: [src/_pytest/raises.py:RaisesGroup._check_exceptions (2)](r4-raises-group.md#u-88a1898bdd87), [AbstractRaises._check_match](r4-raises-shared-matching.md#u-0fcba48753df), [AbstractRaises._check_check](r4-raises-shared-matching.md#u-82b6e36216ab), [RaisesGroup._unroll_exceptions](r4-raises-group.md#u-12875509fc95), [RaisesGroup._check_expected](r4-raises-group.md#u-ad466ac330da)

**Uncertainties.**

- The single-expected non-group branch returns True for a matching bare exception only when allow_unwrapped is set; interaction with a `check` on the group in that path is not exercised here since allow_unwrapped forbids check.

<a id="u-88a1898bdd87"></a>
### `src/_pytest/raises.py:RaisesGroup._check_exceptions (2)`

`def _check_exceptions( self, _exception: BaseException, actual_exceptions: Sequence[B…` · [src/_pytest/raises.py:L1268-L1409][f1]

Greedily pairs expected with actual exceptions and builds the failure message when they do not line up.

It first fills a ResultHolder table: for each expected (in declaration order) it scans remaining actuals, recording each probe result; the first None result consumes that actual and records the match, otherwise the expected is appended to failed_expected. If all expected found matches and no actuals remain it returns True. With exactly one expected and one actual it asserts nothing matched, sets `_fail_reason` to that single result, and fails. Otherwise it completes an exhaustive table (probing every unmatched pair) to surface duplicates, then chooses among message shapes: all expected matched but extra actuals remain → 'Unexpected exception(s)' listing them; all actuals consumed but expected unmatched → 'Too few exceptions raised' with the unmatched expectation reprs; a single unmatched pair on both sides whose entries match nothing else → just that pair's reason; and the general case enumerating unmatched expectations (noting which actual already matched another expectation) and unmatched actuals with per-expectation probe reasons indented, plus — when counts are equal and `possible_match` finds an exhaustive pairing exists — a note that a match exists but the greedy algorithm requires more stringent expectations. Returns False in every non-success case; `_exception` exists only for TypeGuard typing.

**Notes.**

- contract: The `_exception` parameter is unused except to satisfy TypeGuard overloads.

calls: [RaisesGroup._check_expected](r4-raises-group.md#u-ad466ac330da), [possible_match](r4-raises-group.md#u-40484bce1980); uses: [ResultHolder](r4-raises-group.md#u-315daddf914b), [raises.py-regex-helpers](r4-raises-shared-matching.md#u-a954012eb21c), [RaisesGroup](r4-raises-group.md#u-b0e1234080f6)

**Uncertainties.**

- In the failed-expectation detail loop `i_exp` reuses the outer comprehension variable rather than `i_failed`, so which expectation's pairing is printed there is ambiguous from the source and possibly a bug; the surrounding message text is unaffected only when results coincide.
- The junitxml append entry in the call graph appears unrelated to this method's visible source.

<a id="u-ad466ac330da"></a>
### `RaisesGroup._check_expected`

`def _check_expected( expected_type: ( type[BaseException] | RaisesExc[BaseException] …` · [src/_pytest/raises.py:L1228-L1245][f1]

Static helper checking one actual exception against one expectation.

Plain types go through `_check_raw_type` (None means match). RaisesExc/RaisesGroup expectations call their `matches`; a True result returns None, a False result asserts their fail_reason is set and returns it formatted as `<repr>: <reason>`, with a leading-newline reason additionally indented two spaces after the repr. This shared formatting feeds both `matches` and `_check_exceptions`.

calls: [_check_raw_type](r4-raises-shared-matching.md#u-394c03698150), [RaisesExc.matches](r4-raises-exc.md#u-7ff7ba34a27f)

<a id="u-315daddf914b"></a>
### `ResultHolder`

`class ResultHolder:` · [src/_pytest/raises.py:L1465-L1470][f1]

Matrix of pairwise match results between expected and actual exceptions used by RaisesGroup._check_exceptions and possible_match.

`results` is indexed [actual][expected] and initialized with the NotChecked sentinel. `set_result` stores a string reason or None (None means the pair matches). `get_result` asserts the cell was written and returns it. `has_result` reports whether a cell has been probed. `no_match_for_expected` scans a list of expected indexes across all actuals and returns False as soon as any of them matches some actual; `no_match_for_actual` symmetrically scans rows for a given actual list, so a True result means none of the listed exceptions matched any expectation. All sub-cells assert against NotChecked to catch reads of unprobed pairs.

<a id="u-40484bce1980"></a>
### `possible_match`

`def possible_match(results: ResultHolder, used: set[int] | None = None) -> bool:` · [src/_pytest/raises.py:L1510-L1519][f1]

Exhaustive backtracking check used only for the greedy-algorithm hint: determines whether a perfect one-to-one pairing of actual exceptions (rows) to expected ones (columns) exists given the None cells of the ResultHolder table.

Starting at row `len(used)`, an empty used-set row count of zero means all rows are assigned and it returns True; otherwise it tries every unassigned column whose cell is None and recurses, returning True if any branch completes.

uses: [ResultHolder](r4-raises-group.md#u-315daddf914b), [src/_pytest/raises.py:RaisesGroup._check_exceptions (2)](r4-raises-group.md#u-88a1898bdd87)

<a id="u-b4bc20177c81"></a>
### `RaisesGroup.__exit__`

`def __exit__( self, exc_type: type[BaseException] | None, exc_val: BaseException | No…` · [src/_pytest/raises.py:L1411-L1443][f1]

Context-manager exit for the group matcher, with hidden tracebacks.

No raised exception fails with `fail(f"DID NOT RAISE any exception, expected `{self.expected_type()}`")`. A missing excinfo triggers an internal-error assert. It computes a `group_str` of '(group)' only when allow_unwrapped is set and the raised type is not a BaseExceptionGroup (i.e. the exception arrived unwrapped), else 'group'. If `matches(exc_val)` fails it calls `fail` with `Raised exception <group_str> did not match: <reason>` — raising the pytest Failed outcome rather than AssertionError. On success it fills the unfilled excinfo with the narrowed group tuple and returns True.

**Notes.**

- failure: Unlike RaisesExc.__exit__, match failures raise the Failed outcome (fail) instead of AssertionError.

calls: [src/_pytest/raises.py:RaisesGroup.matches (2)](r4-raises-group.md#u-f641ac0065c8), [RaisesGroup.expected_type](r4-raises-group.md#u-ff64ac2156d5), [function::fail][f2]

**Uncertainties.**

- Graph lists three matches candidates; on RaisesGroup instances RaisesGroup.matches is selected, but dispatch is dynamic.

<a id="u-ff64ac2156d5"></a>
### `RaisesGroup.expected_type`

`def expected_type(self) -> str:` · [src/_pytest/raises.py:L1445-L1457][f1]

Builds the expected signature string for messages: each expectation contributes `repr` (RaisesExc), a recursive `expected_type()` (nested RaisesGroup), or its `__name__` (plain type); any other kind raises an uncovered AssertionError.

The result is wrapped as `ExceptionGroup(...)` or `BaseExceptionGroup(...)` depending on `is_baseexception`, with sub-expectations comma-joined.

uses: [RaisesExc.__repr__](r4-raises-exc.md#u-b10ce9ef1d21), [RaisesGroup.__exit__](r4-raises-group.md#u-b4bc20177c81)

<a id="u-e3e81c5b9cdc"></a>
### `RaisesGroup.__repr__`

`def __repr__(self) -> str:` · [src/_pytest/raises.py:L1064-L1078][f1]

Renders `RaisesGroup(...)` listing each expectation (its `__name__` if a plain type, else its repr), then any of `allow_unwrapped=True`, `flatten_subgroups=True`, `match=<pattern>` (via `_match_pattern` to elide a flag-less re.compile), and `check=<repr>` via `repr_callable`, joined with commas.

uses: [raises.py-regex-helpers](r4-raises-shared-matching.md#u-a954012eb21c)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/raises.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/outcomes.py
