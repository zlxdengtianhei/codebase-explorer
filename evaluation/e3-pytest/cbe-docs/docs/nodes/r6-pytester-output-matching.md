# Output Capture and Line Matching

**Capability.** Captures terminal output into buffers and matches it line by line; LineMatcher handles multi-line comparison with various match modes, LineComp accumulates StringIO content for checking.

Use LineMatcher (via result.stdout.fnmatch_lines and friends) to assert on run output. Both the harness internals and suites depend on this layer.

**Depended on by.**

- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-confirmed · 10 edge(s)
- [Hook Recording](r6-pytester-recording.md) · model-inferred · 0 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-confirmed · 8 edge(s)
- [TerminalReporter Unit Tests](r6-terminal-reporter-internals.md) · graph-confirmed · 2 edge(s)

Parent: [Pytester Test Harness](r6-pytester-harness.md)

## Units (2)

<a id="u-a5f6b7ea6e06"></a>
### `pytester-linematcher`

`class LineMatcher:` · [src/_pytest/pytester.py:L1557-L1567][f1]

Matches multi-line text, typically captured command output, given as lines without trailing newlines.

__init__ stores the lines and a log buffer; __str__/str return the lines newline-joined (the original text). _getlines normalizes expected input: a str becomes a Source (stripped, split into lines); Source input is stripped; sequences pass through. Sequential matchers: fnmatch_lines and re_match_lines delegate to _match_lines with fnmatch or re.match (pattern applied to the output line) and optional consecutive mode. _match_lines raises TypeError if lines2 is not a Sequence, then consumes output lines left to right for each expected pattern: exact equality or a pattern match logs the match and moves to the next pattern; a non-matching line is logged as 'nomatch'/'and' and appended to extralines; in consecutive mode, once a match has started, any non-matching line immediately calls _fail('no consecutive match'); if output is exhausted before a pattern matches, _fail('remains unmatched: ...') is called. _fail hides the traceback via __tracebackhide__ and calls fail() with the accumulated log text, clearing the log. The log buffer is cleared at the end of a successful _match_lines. Negative matchers: no_fnmatch_line and no_re_match_line delegate to _no_match_line, which scans every line and calls _fail as soon as one matches (so the first matching line fails the assertion), logging 'nomatch' for the first non-matching line and clearing the log on success. Random-order matchers fnmatch_lines_random/re_match_lines_random use _match_lines_random: each expected line must equal or fnmatch/re.match some output line (order irrelevant, output reusable); the first unmatched line fails. get_lines_after finds the first line equal to or fnmatch-matching fnline and returns everything after it, raising ValueError if none matches. Matching side effects: all failures carry the full log of matches/non-matches for diagnosis.

raises: [pytester-linematcher](r6-pytester-output-matching.md#u-a5f6b7ea6e06)

**Uncertainties.**

- Source(str) splitting behavior for odd line endings is defined in _pytest._code.Source.
- In _match_lines, extralines is built but never returned or logged, so its purpose is unclear from this source alone.

<a id="u-2f4a8ec2d818"></a>
### `pytester-linecomp`

`class LineComp:` · [src/_pytest/pytester.py:L1539-L1540][f1]

Holds a StringIO buffer and checks its accumulated contents.

assert_contains_lines reads the buffer value, truncates and seeks it back to empty (so the check consumes the buffer), splits the value on newlines, and requires the given lines to appear in order via LineMatcher.fnmatch_lines, which fails through pytest's fail() with logged match details if not found.

uses: [pytester-linematcher](r6-pytester-output-matching.md#u-a5f6b7ea6e06)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/pytester.py
