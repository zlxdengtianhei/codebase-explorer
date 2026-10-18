# pytest.raises Test Suite

**Capability.** Tests pytest.raises argument validation, match= behavior (with exact-match escaping), context-manager form, exotic expected-exception objects, failure messages, and regression cases like reference cycles and in-flight repr.

Use this subtree when changing RaisesExc behavior. wrap_escape is the shared helper for exact match patterns; the groups cover validation, match failure messages, stdout reporting, and unusual exception objects.

**Depends on.**

- [Safe Pretty-Printer](r3-pprint.md) · model-inferred · 0 edge(s)

Parent: [Pytest Framework Codebase](r3-pytest.md)

## Units (12)

<a id="u-1bf3f3eb31a7"></a>
### `wrap_escape`

`def wrap_escape(s: str) -> str:` · [testing/python/raises.py:L14-L15][f1]

Wraps a literal string into an anchored regex by concatenating '^', re.escape(s), and '$', so it can be used as an exact-match pytest.raises match pattern.

<a id="u-e0d195a9f7eb"></a>
### `raises.py-testraises-argument-validation`

`class TestRaises:` · [testing/python/raises.py:L18-L19][f1]

Tests pytest.raises argument validation and basic callable form.

test_raises and test_raises_function call pytest.raises(ValueError, int, 'qwe'/'hello') in function form and assert excinfo.value carries 'invalid literal'. test_check_callable expects TypeError with 'must be callable' when a string is passed as the callable position. test_raises_does_not_allow_none and test_raises_does_not_allow_empty_tuple expect ValueError ('You must specify at least one parameter to match on.') for None and () as expected_exception. test_raises_false_and_arg expects the special ValueError explaining that False is not an exception type. test_noclass expects TypeError for a string expected_exception with a lambda. test_invalid_arguments_to_raises expects TypeError matching 'unknown' for an unknown keyword. test_raises_falsey_type_error expects TypeError when match=0 is passed. test_raises_context_manager_with_kwargs shows expected_exception=ValueError works as a keyword and that extra keyword foo='bar' raises TypeError 'Unexpected keyword arguments passed to pytest.raises: foo'. test_expected_exception_is_not_a_baseexception asserts TypeError-style 'expected exception must be a BaseException type' messages for 'hello', a plain NotAnException class, and a tuple containing invalid members. Most expected errors are matched through wrap_escape so literals match exactly.

**Uncertainties.**

- Exact exception type for the tuple-of-invalid-members case ('hello', NotAnException) is asserted as TypeError via the expected match message; the raiser itself is not in this file.

<a id="u-90351620be13"></a>
### `raises.py-match-failure-messages`

`def test_match_failure_string_quoting(self):` · [testing/python/raises.py:L287-L292][f1]

Pinpoints the exact failure text produced when the regex does not match.

test_match_failure_string_quoting asserts the message renders the pattern and input with repr, preserving embedded quotes exactly. test_match_failure_exact_string_message asserts the additional 'Did you mean to re.escape() the regex?' hint when pattern and input differ only by regex metacharacters. test_raises_match_wrong_type raises a ValueError while expecting IndexError with match= given, and asserts the ValueError itself propagates (matched via wrap_escape), i.e. the pattern check is skipped when the exception type already mismatches.

<a id="u-935bc5073385"></a>
### `raises.py-raises-stdout-reporting`

`def test_does_not_raise(self, pytester: Pytester) -> None:` · [testing/python/raises.py:L120-L139][f1]

Subprocess-style checks of raises' user-facing behavior.

test_does_not_raise runs a parametrized division test using nullcontext vs pytest.raises and asserts 4 passed, validating the documented does-not-raise pattern. test_does_not_raise_does_raise inverts expectations and asserts 2 failed, confirming failure when the expectation mismatches. test_raises_with_invalid_regex uses match with an unterminated character set and asserts the output contains the dedicated 'Invalid regex pattern provided to match: unterminated character set at position 24' message while explicitly asserting no 'Traceback', 'File', or 'line' appears — the error must be reported without a traceback.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-ab39274ab734"></a>
### `raises.py-raises-exotic-exception-objects`

`def test_raises_exception_looks_iterable(self):` · [testing/python/raises.py:L320-L321][f1]

Covers raises against unusual expected-exception objects.

test_raises_exception_looks_iterable defines an exception class with a metaclass providing __getitem__ (raising via 1/0) and __len__ (1), so the class looks iterable; calling pytest.raises on it with a no-op callable must produce Failed matching 'DID NOT RAISE <class ...ClassLooksIterableException>', showing the class is not accidentally iterated. test_raises_with_raising_dunder_class passes CrappyClass(), whose __class__ property asserts False, as the expected exception and asserts the AssertionError 'via __class__' surfaces, documenting that __class__ access on instances raises here.

**Uncertainties.**

- Whether the implementation inspects __len__/__getitem__ at all is not derivable here; the test only pins the observed DID NOT RAISE outcome.

<a id="u-ffe6d683ac7c"></a>
### `TestRaises.test_raises_as_contextmanager`

`def test_raises_as_contextmanager(self, pytester: Pytester) -> None:` · [testing/python/raises.py:L92-L118][f1]

Runs an inline module exercising raises as a context manager: test_simple asserts excinfo is an ExceptionInfo before the ZeroDivisionError, then checks .type and .value; test_noraise expects raises' own failure exception when nothing raises inside; test_raise_wrong_exception_passes_by expects a ZeroDivisionError raised inside a ValueError-expecting block to propagate past it.

Asserts '3 passed' in runpytest output.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-6d8cd1f03d85"></a>
### `TestRaises.test_raises_callable_no_exception`

`def test_raises_callable_no_exception(self) -> None:` · [testing/python/raises.py:L60-L61][f1]

Checks that pytest.raises with a callable raising nothing fails: a ValueError raised check around a no-op callable A() instance must raise pytest.fail.Exception, which the try/except swallows; any other outcome would propagate or fail the test.

<a id="u-9a7d762b6f7f"></a>
### `TestRaises.test_raises_cyclic_reference`

`def test_raises_cyclic_reference(self, method):` · [testing/python/raises.py:L209-L216][f1]

Parametrized over five usage forms (function, function with .match, with-block, pytest.RaisesExc, pytest.RaisesGroup with allow_unwrapped) to ensure none leaves a reference cycle around the raising callable nor a lingering exception in sys.exc_info().

It records gc.get_referrers(t) length before, runs the chosen form raising ValueError, asserts sys.exc_info() == (None, None, None), and asserts the referrer count is unchanged. An unrecognized parameter reaches a pragma-no-cover AssertionError.

<a id="u-48920c41c90a"></a>
### `TestRaises.test_raises_match`

`def test_raises_match(self) -> None:` · [testing/python/raises.py:L244-L271][f1]

Exercises match= in all its modes.

A regex pattern matches int('asdf'); a plain string matches the same message; a non-matching pattern raises AssertionError whose message must exactly equal the formatted 'Regex pattern did not match. Regex: ... Input: ...' text, checked both inside a context manager and via .match() on the returned excinfo (its non-matching case also raises AssertionError with the same string). pytest.raises(TypeError, int, match='invalid') shows match with a callable; tfunc shows match against keyword-passed callable arguments, including empty string matching 'match='. Finally pytest.raises(match='') is expected to emit a PytestWarning that an empty match string always passes, recommending '^$' or None.

**Uncertainties.**

- Whether pytest.raises(match='') raises or only warns is fixed here solely by the surrounding pytest.warns expectation; the raiser's own behavior is not in this file.

<a id="u-3d17dbd6e6ee"></a>
### `TestRaises.test_raises_repr_inflight`

`def test_raises_repr_inflight(self):` · [testing/python/raises.py:L75-L78][f1]

Regression test that repr/str/pprint on an in-flight ExceptionInfo inside a raises block works (#4386).

Inside pytest.raises(E), the test prints str, repr, and pprint of excinfo before raising E; success means no error occurs during formatting of the uninitialized object.

<a id="u-7a760d8d5d00"></a>
### `TestRaises.test_no_raise_message`

`def test_no_raise_message(self) -> None:` · [testing/python/raises.py:L193-L207][f1]

Asserts the DID-NOT-RAISE failure message is identical in function and context-manager form: both pytest.raises(ValueError, int, '0') and a raises block containing pass raise pytest.fail.Exception whose e.msg equals 'DID NOT RAISE <class ValueError-like repr>'; any other outcome hits the else branch's failing assert.

<a id="u-29232605a259"></a>
### `TestRaises.test_issue_11872`

`def test_issue_11872(self) -> None:` · [testing/python/raises.py:L395-L410][f1]

Regression for #11872: raising urllib.error.HTTPError (with BytesIO fp and email Message headers) inside pytest.raises(HTTPError, match='Not Found') must succeed on Python versions where invalid attribute access on HTTPError raises KeyError instead of AttributeError.

It closes exc_info.value afterwards to avoid resource warnings.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/python/raises.py
