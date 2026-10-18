# Statement Recovery Tests

**Capability.** Pins getstatementrange_ast statement boundaries: comments, strings, decorators, semicolons, single-line compound clauses, and multiline calls are delimited exactly as the traceback renderer expects.

Use this subtree when changing statement-range logic. The shared getstatement helper wraps the AST range computation and each test asserts the recovered source text slice for a given line.

**Depends on.**

- [Source Construction & Access Tests](r3-source-construction-tests.md) · model-inferred · 0 edge(s)

Parent: [Code Introspection Test Suite](r3-code-introspection-tests.md)

## Units (19)

<a id="u-73c873108c2e"></a>
### `getstatement`

`def getstatement(lineno: int, source) -> Source:` · [testing/code/test_source.py:L398-L403][f1]

Test helper wrapping the statement-range logic: builds Source(source), calls getstatementrange_ast(lineno, src) to get (ast, start, end), and returns the src[start:end] slice so individual tests can assert the recovered statement text.

<a id="u-e5e29b5e78f0"></a>
### `TestSourceParsing`

`class TestSourceParsing:` · [testing/code/test_source.py:L108-L109][f1]

Tests statement-boundary reconstruction on a shared indented source whose body is one multi-line assert.

test_getstatement expects any starting line within the statement (1-3) to return the whole statement slice. test_getstatementrange_triple_quoted expects getstatement(0) and getstatement(1) on a source containing a triple-quoted string with embedded quotes to return the entire source, since the string spans both lines. test_getstatementrange_within_constructs maps traceback line numbers inside a try/finally to sub-ranges: nested statements get their own line ranges (2→(2,3), 3→(3,4), 4→(4,5), 6→(6,7)) while construct headers span the whole block (commented cases 0,1,5). test_getstatementrange_bug expects a multi-line parenthesized assignment inside try to span (1,4) when starting from line 2. test_getstatementrange_bug2 expects a deeply nested assert expression spanning all 9 lines to map line 5 to (0,9). test_getstatementrange_ast_issue58 pins getstatement via the helper on a source whose first line is blank and contains an AST-unparseable comprehension name, returning single-line slices for lines 2 and 3, i.e. the AST fallback path. test_getstatementrange_out_of_bounds_py3 expects a relative-import line inside an if to map to (1,2). test_getstatementrange_with_syntaxerror_issue7 expects getstatementrange(0) on the unparsable source ':' to raise SyntaxError, so unparsable input propagates rather than being guessed.

**Uncertainties.**

- Which lines of the try/finally source span the whole construct is asserted only for the uncommented cases; (0,7) and (1,5) remain commented-out expectations.

<a id="u-ff9489a432f3"></a>
### `TestIf`

`class TestIf:` · [testing/code/test_source.py:L567-L568][f1]

Pins boundaries in an if/elif/else chain: line 1 yields the if body '    y = 3'; line 2 yields the bare 'elif False:' header; line 3 yields the elif body '    y = 5'; line 5 yields the else body '    y = 7'.

<a id="u-fff0e22cb4c3"></a>
### `TestTry`

`class TestTry:` · [testing/code/test_source.py:L521-L522][f1]

Pins statement boundaries in a try/except/else block: line 1 (body) yields '    raise ValueError' alone; line 2 yields the bare 'except Something:' header; line 3 yields its body '    raise IndexError(1)'; line 5 yields the else body '    raise KeyError()'.

Headers and bodies are separate statements.

<a id="u-34e8fcab5b97"></a>
### `TestTryFinally`

`class TestTryFinally:` · [testing/code/test_source.py:L549-L550][f1]

Same boundary pinning for try/finally: line 1 yields the try body '    raise ValueError' and line 3 yields the finally body '    raise IndexError(1)'.

<a id="u-b5dea13b8290"></a>
### `test_oneline`

`def test_oneline() -> None:` · [testing/code/test_source.py:L406-L408][f1]

Asserts a single-line source 'raise ValueError' recovered at line 0 round-trips unchanged.

<a id="u-7b0f66b90559"></a>
### `test_oneline_and_comment`

`def test_oneline_and_comment() -> None:` · [testing/code/test_source.py:L425-L427][f1]

A trailing '#hello' comment after 'raise ValueError' is excluded: getstatement(0) returns only the statement line.

<a id="u-ffd1dcde174d"></a>
### `test_comments`

`def test_comments() -> None:` · [testing/code/test_source.py:L430-L448][f1]

Maps statement recovery around comments and strings: lines 2-5 (docstring, assignment, indented and flush comments, blank) recover '    x = 1'; lines 6-7 recover '    assert False'; lines 8-9 recover the triple-quoted block '"""\ncomment 4\n"""' as one statement.

Comments attach to the following statement rather than forming their own.

<a id="u-ec08866ef47f"></a>
### `test_comment_in_statement`

`def test_comment_in_statement() -> None:` · [testing/code/test_source.py:L451-L460][f1]

A comment inside a multi-line call is part of the statement: getstatement on lines 1-2 returns the full 'test(foo=1,\n    # comment 1\n    bar=2)' text including the comment.

<a id="u-985881bbe04b"></a>
### `test_comment_and_no_newline_at_end`

`def test_comment_and_no_newline_at_end() -> None:` · [testing/code/test_source.py:L411-L422][f1]

With a source whose last line is a comment and no trailing newline, getstatementrange_ast(1) must end at 2 — the trailing comment line is excluded from the statement range ending at the assert.

<a id="u-b94aa32aaddc"></a>
### `test_decorator`

`def test_decorator() -> None:` · [testing/code/test_source.py:L614-L624][f1]

getstatement(3) on a source where line 3 is a decorated def returns a statement containing '@foo', so decorator lines are part of the decorated def's statement.

<a id="u-264d6914636c"></a>
### `test_def_online`

`def test_def_online() -> None:` · [testing/code/test_source.py:L603-L611][f1]

A one-line def ('def func(): raise ValueError(42)') recovers exactly that line, not bleeding into the following def.

<a id="u-b52f6fae48a6"></a>
### `test_semicolon`

`def test_semicolon() -> None:` · [testing/code/test_source.py:L595-L600][f1]

A line with two semicolon-separated statements ('hello ; pytest.skip()') is recovered whole, stripped of the trailing newline.

<a id="u-152e18d28a51"></a>
### `test_single_line_else`

`def test_single_line_else() -> None:` · [testing/code/test_source.py:L489-L491][f1]

Line 1 of 'if False: 2\nelse: 3' recovers exactly 'else: 3', so single-line compound-clause statements are delimited without consuming the if.

<a id="u-2dc0047ea348"></a>
### `test_single_line_finally`

`def test_single_line_finally() -> None:` · [testing/code/test_source.py:L494-L496][f1]

Line 1 of 'try: 1\nfinally: 3' recovers exactly 'finally: 3'.

<a id="u-7e6ca53cdeb8"></a>
### `test_multiline`

`def test_multiline() -> None:` · [testing/code/test_source.py:L508-L518][f1]

A multi-line call statement starting at line 0 recovers only the statement ('raise ValueError(\n    23\n)'), excluding the following 'x = 3'.

<a id="u-12ba3c5f0bf4"></a>
### `test_issue55`

`def test_issue55() -> None:` · [testing/code/test_source.py:L499-L505][f1]

A def containing an empty triple-quoted string does not confuse statement extraction: getstatement(3) returns '  round_trip("""\n""")' including the multi-line string literal.

<a id="u-5ff16ef92334"></a>
### `XXX_test_expression_multiline`

`def XXX_test_expression_multiline() -> None:` · [testing/code/test_source.py:L627-L633][f1]

Pinned with XXX prefix (likely flaky or known-broken): getstatement(1) on a bare multi-line triple-quoted expression recovers exactly the string literal lines "'''\n'''".

**Uncertainties.**

- XXX prefix suggests a known-problematic case; the reason is not documented in this file.

<a id="u-f65ec6a26a33"></a>
### `testing/code/test_source.py:test_getline_finally`

`def test_getline_finally() -> None:` · [testing/code/test_source.py:L230-L240][f1]

Checks statement extraction for a finally block.

Calling c(1) (wrong arity) inside try/finally raises TypeError; excinfo.traceback[-1].statement must strip to 'c(1)  # type: ignore', showing the failing call's statement is recovered including a trailing comment, and that teardown being None short-circuits before calling it.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/code/test_source.py
