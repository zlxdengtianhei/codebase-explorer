# ExceptionGroup reporting tests

**Capability.** End-to-end output tests around _exceptiongroup_common: generated modules raising BaseExceptionGroups chained or unchained from f/g exceptions, asserting the group header, sub-exception lines, FAILED summaries, and pytest-frame filtering.

Read here for the exact expected terminal output of ExceptionGroup tracebacks, including chained SyntaxError causes.

**Depends on.**

- [Traceback rendering tests](r4-excinfo-repr-tests.md) · model-inferred · 0 edge(s)

Parent: [Excinfo and traceback tests](r4-test-excinfo.md)

## Units (1)

<a id="u-2edccdceb700"></a>
### `test_excinfo.py-exceptiongroup`

`def _exceptiongroup_common( pytester: Pytester, outer_chain: str, inner_chain: str, n…` · [testing/code/test_excinfo.py:L1732-L1802][f1]

ExceptionGroup reporting tests built around _exceptiongroup_common, which generates a module where inner() collects ValueError and BaseException from f/g into a BaseExceptionGroup raised unchained, 'from' a SyntaxError, or unchained-again ('another'), and outer() re-raises bare, raises IndexError from the group, or raises bare IndexError; it then runs pytest and asserts the 'Exception Group Traceback' header, the group summary with '(2 sub-exceptions)', per-sub-exception '| ValueError/BaseException' lines, the FAILED summary line (IndexError when outer re-raises differently), a SyntaxError line only for chained inner variants, and that pytest-internal frames are filtered from the output.

test_native_exceptiongroup (3.11+) and test_exceptiongroup (backport, skipped without the exceptiongroup package) parametrize both chains; prefix logic picks exceptiongroup. only on old interpreters or non-native mode. test_exceptiongroup_short_summary_info verifies -vv summary lines show single sub-exceptions as 'ValueError(...) [single exception in ExceptionGroup]' or group summaries with sub-exception counts, including nested groups. test_all_entries_hidden checks all-tb-styles runs report the ZeroDivisionError and, except for line/native styles, 'All traceback entries are hidden.'; chained-exception hidden entries are omitted from short tracebacks. add_note uses err.add_note on 3.11+ else appends to __notes__; note-matching tests confirm pytest.raises(match=) matches notes (including multiline/case-insensitive regexes) and raises AssertionError when the pattern matches neither message nor notes.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/code/test_excinfo.py
