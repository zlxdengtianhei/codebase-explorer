# ExceptionInfo API tests

**Capability.** Tests of ExceptionInfo construction entry points, convenience API methods, group_contains, pytest.raises acceptance of generic ExceptionGroup annotations, and the match() failure reporting integration.

Use this subtree for the public ExceptionInfo surface, including its ExceptionGroup-aware helpers.

**Depends on.**

- [Exception assertion helpers](r4-raises-module.md) · model-inferred · 0 edge(s)

Parent: [Excinfo and traceback tests](r4-test-excinfo.md)

## Units (5)

<a id="u-626b22993687"></a>
### `test_excinfo.py-excinfo-construction`

`def test_excinfo_simple() -> None:` · [testing/code/test_excinfo.py:L46-L51][f1]

Tests the ExceptionInfo construction entry points.

from_current() captures the active exception and exposes its type; from_exc_info() accepts a (type, value, traceback) triple; from_exception() accepts an exception instance and asserts its __traceback__ is set before use. A bare ValueError() passed to from_exception is expected to raise an AssertionError matching /must have.*__traceback__/. Each success case asserts info.type == ValueError after catching a raised ValueError.

uses: [class::ExceptionInfo][f2]

**Uncertainties.**

- The exact AssertionError text of from_exception is only verified via a regex, not read from its implementation

<a id="u-13aaccc85b22"></a>
### `test_excinfo.py-excinfo-api`

`def test_excinfo_exconly():` · [testing/code/test_excinfo.py:L335-L342][f1]

Module-level tests of ExceptionInfo convenience API.

exconly() starts with the exception type name and, with tryshort=True, collapses a multi-line ValueError message to a single line ending in 'world'. repr/str of ExceptionInfo render as '<ExceptionInfo <name-or-repr> tblen=N>', using the exception's own __repr__ for a custom exception. for_later() creates a lazily-filled instance whose repr/str contain 'for raises'. errisinstance() reports True for the caught type. When source is unavailable (exec'd string, or a jinja2 template that is skipped without jinja2), entry str/source access must not fail; the exec case matches a 'File <string>' pattern and the jinja2 case expects the template text as source. Queue examples check entry.getsource() starts with 'def get' and entry.path is an existing queue.py. match() with a non-matching regex fails the run with a 'Regex pattern did not match' error naming regex and input.

uses: [class::ExceptionInfo][f2]

**Uncertainties.**

- A TODO comment notes that under Python 3.13b1 with pytest-xdist the '*' placeholder in test_excinfo_no_sourcecode may render bootstrap code instead of '???'

<a id="u-a996e2acc9d7"></a>
### `test_excinfo.py-group-contains`

`class TestGroupContains:` · [testing/code/test_excinfo.py:L490-L491][f1]

Tests ExceptionInfo.group_contains against ExceptionGroup instances.

A plain group containing RuntimeError matches by type and not when only a ValueError is present; match='^exception message$' additionally requires a sub-exception whose str matches the regex. Depth semantics: default searches nested groups without limit (a RuntimeError inside a nested group matches at default depth); depth=1 matches only direct sub-exceptions (nested RuntimeError fails), depth=2 matches one level of nesting; the same type/depth and match/depth combinations are covered for positive and negative cases, all asserting on group_contains's boolean result.

calls: [ExceptionInfo._group_contains](r1-code-exception-info.md#u-b5ceec9284d2)

<a id="u-884ed6b1f258"></a>
### `test_excinfo.py-raises-generic-groups`

`def test_raises_accepts_generic_group() -> None:` · [testing/code/test_excinfo.py:L457-L460][f1]

Tests pytest.raises acceptance of generic ExceptionGroup annotations.

raises(ExceptionGroup[Exception]) and raises(BaseExceptionGroup[BaseException]) catch a raised ExceptionGroup containing a RuntimeError, verified via exc_info.group_contains(RuntimeError). raises((ValueError, ExceptionGroup[Exception])) also accepts the group inside a tuple. Constructing raises(ExceptionGroup[RuntimeError]) inside a `with pytest.raises(ValueError)` block is expected to raise ValueError, i.e. a more specific element type is rejected. An ordinary ValueError escaping a raises(ExceptionGroup[Exception]) context propagates out of the with-block and is caught by the test itself; failing that, pytest.fail is called.

calls: [ExceptionInfo._group_contains](r1-code-exception-info.md#u-b5ceec9284d2); uses: [class::Pytester][f3]

<a id="u-4fe98740505c"></a>
### `test_match_raises_error`

`def test_match_raises_error(pytester: Pytester) -> None:` · [testing/code/test_excinfo.py:L431-L454][f1]

Integration test that a failing excinfo.match() is reported correctly.

It writes a test where excinfo.match(r'[123]+') does not match 'division by zero', runs pytest with --tb=short, expects failure and three specific error lines (did not match, regex, input), and asserts no '__tracebackhide__ = True' leaks into output. A second run with --fulltrace expects the same error lines preceded by the hidden-marker line, showing hiding is disabled under fulltrace.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/code/test_excinfo.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/_code/code.py
[f3]: ../../../../../../eval/pytest-5989efe/src/_pytest/pytester.py
