# Explanation Formatting and Truncation

**Capability.** Tests the post-processing of explanation text: format_explanation's whitespace/line reformatting and _truncate_explanation's line and character limits.

Use these when changing how explanations are shaped or capped; both groups assert on deterministic text transformations, truncation also through runpytest paths.

**Depends on.**

- [Test Run Invocation](r6-pytester-run.md) · graph-confirmed · 5 edge(s)

Parent: [Assertion Rewriting Suite](r6-test-assertion.md)

## Units (2)

<a id="u-fa4008c17780"></a>
### `test-assertion-formatexplanation`

`class TestFormatExplanation:` · [testing/test_assertion.py:L1261-L1262][f1]

Tests util.format_explanation's text reformatting of assertion messages.

test_fmt_simple: plain text passes through. test_fmt_where: '{expr = value' followed by '}' becomes ' +  where expr = value' appended to the assert line. test_fmt_and: a second '{...}' block becomes ' +  and   expr = value'. test_fmt_where_nested: nested '{' blocks indent the inner where clause. test_fmt_newline: '~-'/'~+' prefixed lines are joined with two-space indentation instead of newlines. test_fmt_newline_escaped: an unmarked trailing line becomes a literal '\n' in a single line. test_fmt_newline_before_where and test_fmt_multi_newline_before_where: a '>' marker line splits the message, so content before '>' is kept as-is and the assert plus where/and clauses are reformatted after it. test_special_chars_full runs a subprocess test asserting '\n}' == '' no longer raises IndexError, expecting a normal AssertionError report.

uses: [_pytest.assertion.util.format_explanation](../../catalog.json)

<a id="u-72c458a5e21e"></a>
### `test-assertion-truncateexplanation`

`class TestTruncateExplanation: # The number of lines in the truncation explanation me…` · [testing/test_assertion.py:L1348-L1353][f1]

Tests truncate._truncate_explanation's line and character limits directly.

Behavior pinned by the tests: an empty input is returned unchanged; input at or under the limits is returned unchanged; otherwise the result keeps the first kept lines, appends '...' to the last kept line, and adds a 2-line 'Full output truncated (N lines hidden)' message (LINES_IN_TRUNCATION_MSG = 2). Line keeping respects max_lines (e.g. 8) but shrinks further when the kept lines exceed max_chars (250-char lines with max_chars=999 keep only 4 lines; with max_chars=100 only 1 line), and the hidden-count message reflects the reduced keep. Two edge cases assert no truncation when adding the message would make the result longer than the input (max_lines=10/max_chars=10 for 2 ten-char lines; max_lines=1 for 2 lines). test_full_output_truncated runs the real pytester flow: without -vv the long diff is truncated with a 'truncated (2 lines hidden)' hint pointing at -vv; with -vv or CI=1 the full lines appear. test_truncation_with_ini parametrizes truncation_limit_lines and truncation_limit_chars ini settings against a 6-line/79-char diff, checking that thresholds below the effective limits truncate and at-or-above limits do not (fnmatch/no_fnmatch_line on '*truncated*' and the '+ 3'/'- 4' diff lines).

uses: [_pytest.assertion.truncate._truncate_explanation](../../catalog.json)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_assertion.py
