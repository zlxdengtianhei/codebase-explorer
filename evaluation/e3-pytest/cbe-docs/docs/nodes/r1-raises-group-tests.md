# RaisesGroup test suite

**Capability.** Tests for exception-group assertion helpers: construction validation and matching semantics (nesting, allow_unwrapped, flatten_subgroups, match/check, matches(), rejection of invalid generics) plus exact DID-NOT-RAISE and per-expected/per-raised mismatch report formatting.

Use the matching-semantics group for behavioral contracts and the mismatch-message group for pinned user-visible text. Both lean on the shared fails_raises_group and wrap_escape helpers to assert exact messages. Where the implementation itself is not part of these units, behavior conclusions are inferred from the tests only.

Parent: [pytest codebase](r1-pytest-codebase.md)

## Units (4)

<a id="u-2d04582d3194"></a>
### `raises_group.py-matching-semantics`

`def test_raises_group() -> None:` · [testing/python/raises_group.py:L36-L88][f1]

Verifies RaisesGroup and RaisesExc construction validation plus matching semantics: valid exception types and nesting, allow_unwrapped and flatten_subgroups behavior, match/check application to the group, matches() predicate results, rejection of tuples and bad generic arguments, and xfail/parametrized usage.

**Notes.**

- condition: Constructors reject invalid input eagerly: RaisesExc(non-type) and RaisesGroup(exception instance) raise TypeError; RaisesExc(int/object) and RaisesGroup(nested structure with flatten_subgroups=True, multiple exceptions with allow_unwrapped=True, nested RaisesGroup with allow_unwrapped=True, tuple argument) raise ValueError with explanatory text.
- contract: allow_unwrapped=True bypasses match and check for unwrapped exceptions; combining them raises ValueError advising a RaisesExc instead.
- condition: allow_unwrapped catches a bare matching exception; fully emulating except* requires allow_unwrapped=True plus flatten_subgroups=True, since allow_unwrapped alone does not match inside nested groups; with allow_unwrapped=False a bare exception is not caught and the failure suggests allow_unwrapped=True.
- condition: RaisesGroup match supports ^$ anchors and matches the group message plus notes; match/check apply to the whole ExceptionGroup, not sub-exceptions, and a check that returns True for the sub-exception triggers a RaisesExc suggestion.
- failure: DID NOT RAISE paths are covered: RaisesExc() with no parameters raises ValueError; a non-matching check yields 'check <repr> did not return True on the ExceptionGroup'; unmatched RunsExc raises AssertionError on regex mismatch rather than Failed in one RaisesExc case.
- contract: matches() returns False for None and non-matching exceptions, True for a matching ExceptionGroup or bare exception; test_assert_matches shows the walrus form asserting m.fail_reason for detailed assertion output.
- condition: test_annotated_group accepts only ExceptionGroup[Exception]/BaseExceptionGroup[BaseException] generics (otherwise ValueError) and shows the repr depends on whether the exceptiongroup backport is used.
- condition: test_tuples shows RaisesExc accepts a tuple of exception types while RaisesGroup rejects tuples with a message listing the alternatives; test_parametrizing_conditional_raisesgroup parametrizes bare vs grouped ValueError with a shared context-manager handler.

calls: [fails_raises_group](r1-raises-group-tests.md#u-039de5265f95), [testing/python/raises_group.py:wrap_escape](r1-raises-group-tests.md#u-7dffe063a62f), [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- test_assert_matches resolves to several matches candidates (AbstractRaises/RaisesExc/RaisesGroup); which implementation executes for a RaisesExc instance is not proven here.
- Internals of RaisesGroup/RaisesExc are outside this file; behavior is evidenced only by expected message strings and outcomes.

<a id="u-1734bfc1415c"></a>
### `raises_group.py-mismatch-message-formatting`

`def test_message() -> None:` · [testing/python/raises_group.py:L482-L483][f1]

Pins the exact human-readable mismatch reports of RaisesGroup/RaisesExc: DID-NOT-RAISE descriptions, per-expected/per-raised tables, indentation of nested reports, brief vs full tables, identity handling of duplicated exceptions, repr/str forms, and repr-patching interplay.

**Notes.**

- contract: test_message fixes group description strings: base-ness transfers from children to the parent container (BaseExceptionGroup(...)) but sibling containers keep their own base-ness, and a one-element tuple prints as a single type.
- condition: A brief single-line error is printed when exactly one raised and one expected fail to match and neither would match an already-paired counterpart; if the unmatched raised (or expected) would match an already-paired counterpart, a full table with 'It matches X which was paired with Y' lines is emitted instead (test_brief_error_on_one_fail).
- failure: test_misordering_example documents the greedy algorithm: a combinatorially possible match is not found, and the message advises tightening expected exceptions with RaisesExc.
- side_effect: test_identity_oopsies shows duplicated identical raised exceptions and repeated expected matchers are each reported separately, not deduplicated.
- condition: test_suggestion_on_nested_and_brief_error pins indentation: 'Did you mean' and re.escape suggestions are indented only when they follow a single-line error, to avoid looking like another raised exception.
- contract: test_raisesexc_tostring and test_raisesgroup_tostring pin str/repr forms: RaisesExc(ValueError), match strings (compiled patterns keep flags in repr), RaisesGroup nesting, allow_unwrapped/match/check parameters; test_raisesgroup_tostring additionally requires eval(str(x)) round-trip equality.
- condition: test_RaisesExc_check shows verbose check reprs are printed once per RaisesExc but repeatedly when nested inside RaisesGroup; specifying exception_type narrows the check callable's parameter type.
- condition: test_check_no_patched_repr is skipped when hypothesis is imported (it may monkeypatch _check_repr) and pins the verbose lambda-repr message emitted when _check_repr is unpatched.
- failure: test_incorrect_number_exceptions and test_assert_message(_nested) fix excess/missing-exception wording, flatten_subgroups suggestions (including when a check is present and when nested), unexpected-nested wording, and re.escape suggestions; test_message_indent pins nested-report indentation.

calls: [fails_raises_group](r1-raises-group-tests.md#u-039de5265f95), [testing/python/raises_group.py:wrap_escape](r1-raises-group-tests.md#u-7dffe063a62f)

**Uncertainties.**

- Full message rendering lives in _pytest.raises; this file evidences only the expected strings.

<a id="u-039de5265f95"></a>
### `fails_raises_group`

`def fails_raises_group(msg: str, add_prefix: bool = True) -> RaisesExc[Failed]:` · [testing/python/raises_group.py:L28-L33][f1]

Builds a pytest.raises(Failed, match=...) context asserting that a RaisesGroup mismatch produces exactly the given message, optionally prefixed.

**Notes.**

- contract: Asserts the expected message does not end with a newline (developer guard raising AssertionError).
- condition: add_prefix=True (default) prepends 'Raised exception group did not match: ' to the expected text; tests with multi-line tables pass add_prefix=False.

calls: [testing/python/raises_group.py:wrap_escape](r1-raises-group-tests.md#u-7dffe063a62f)

**Uncertainties.**

- Actual Failed message formatting comes from _pytest.raises internals not present in this file; only expected strings are visible.

<a id="u-7dffe063a62f"></a>
### `testing/python/raises_group.py:wrap_escape`

`def wrap_escape(s: str) -> str:` · [testing/python/raises_group.py:L24-L25][f1]

Wraps a string as a full-match regex by escaping it and adding ^ and $ anchors.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/python/raises_group.py
