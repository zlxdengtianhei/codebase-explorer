# Explanation Summary & Formatting

**Capability.** The assertrepr_compare entry point plus pytest's marker-based explanation formatting language ({, }, ~, >) and an identity highlighter, converting raw comparison data into the final summary/explanation text.

Call assertrepr_compare for a failed 'left op right'; format_explanation post-processes explanation strings. Returns None when no specialized explanation applies.

**Depends on.**

- [Type-Specialized Comparisons](r2-comparison-strategies.md) · graph-confirmed · 2 edge(s) · assertrepr_compare dispatches to _compare_eq_any and the set comparators to build failure explanations.
- [Pytest Codebase](r2-pytest-root.md) · within containment · 16 edge(s)

Parent: [Assertion Failure Reporting](r2-assertion-reporting.md)

## Units (5)

<a id="u-28eb36a31d2c"></a>
### `assertrepr_compare`

`def assertrepr_compare( config, op: str, left: Any, right: Any, use_ascii: bool = Fal…` · [src/_pytest/assertion/util.py:L178-L245][f1]

Produces the summary and specialised explanation for a failed comparison `left op right`, or None when no specialised explanation applies.

It reads the assertions verbosity; string operands whose NFD normalizations are equal force ascii() reprs (issue #3246). Reprs are saferepr_unlimited when verbosity > 1, otherwise saferepr sized to (80 - 15 - len(op) - 2) // 2 per side; the summary is 'left_repr op right_repr'. The highlighter comes from config.get_terminal_writer()._highlight. op dispatch: '==' always delegates to _compare_eq_any; 'not in' only for two str operands (via _notin_text); '!=', '>=', '<=', '>', '<' only for two set/frozenset operands ('!=' yielding 'Both sets are equal', ordering ops delegating to the corresponding set comparators). outcomes.Exit propagates unchanged; any other Exception is caught and replaced by a two-line message embedding ExceptionInfo's reprcrash blaming a possibly faulty __repr__. An empty/falsy explanation returns None; otherwise an empty first line is prepended when explanation[0] != '' and the result is [summary, *explanation].

**Notes.**

- failure: Non-Exit exceptions inside comparison building never abort the test run; they downgrade the explanation to the 'representation of details failed' message.

calls: [_compare_eq_any](r2-comparison-strategies.md#u-ff4132716b63), [_notin_text](r2-comparison-strategies.md#u-949df6bf05d2), [set-comparators](r2-pytest-root.md#u-066911b3d9de); uses: [src/_pytest/assertion/util.py][f1]

**Uncertainties.**

- use_ascii parameter is overwritten unconditionally by the normalization check, so a caller-provided use_ascii=True for non-matching strings is discarded.
- config.get_terminal_writer()._highlight and config.get_verbosity(VERBOSITY_ASSERTIONS) are duck-typed; mock configs in tests provide alternates.

<a id="u-42d9b1371b85"></a>
### `format_explanation`

`def format_explanation(explanation: str) -> str:` · [src/_pytest/assertion/util.py:L54-L66][f1]

Reformats an explanation string written in pytest's mini formatting language.

It splits the input on the markers '\n{', '\n}', and '\n~' (other embedded newlines stay escaped as literal \n) via _split_explanation, then converts the markers into readable 'where ...' / 'and ...' / continuation lines with indentation via _format_lines, and joins the result with real newlines.

calls: [_split_explanation](r2-explanation-formatting.md#u-b99db733d975), [_format_lines](r2-explanation-formatting.md#u-9cc9f76678ba)

<a id="u-b99db733d975"></a>
### `_split_explanation`

`def _split_explanation(explanation: str) -> list[str]:` · [src/_pytest/assertion/util.py:L69-L83][f1]

Splits an explanation into logical lines at the '{', '}', '~', and '>' formatting markers.

It splits raw text on '\n'; the first raw fragment always starts a logical line, and each subsequent fragment beginning with one of those marker characters starts a new logical line, while any other fragment is appended to the previous line with a literal '\\n' escape. An empty/None explanation is treated as the empty string.

**Notes.**

- contract: Non-marker newlines never produce a split; they remain escaped inside the logical line.

**Uncertainties.**

- The '>' marker is accepted here although the docstring mentions only \n{, \n}, \n~; _format_lines asserts on '~' or '>'.

<a id="u-9cc9f76678ba"></a>
### `_format_lines`

`def _format_lines(lines: Sequence[str]) -> list[str]:` · [src/_pytest/assertion/util.py:L86-L118][f1]

Renders the marker-based logical lines into final display lines with indentation.

Line 0 passes through. A '{' line opens a nesting level, emitted as ' +' + indent + ('where ' or 'and   ' — 'and' when this level already had a preceding item) plus the line body after the marker. A '}' line closes the current level and appends its body directly to the line recorded when that level opened. Any other line (asserted to start with '~' or '>') continues the current level with indentation of len(stack) for '~' or len(stack)-1 for '>'. Finally asserts the stack is back to a single base level, so unbalanced markers fail this assertion.

**Notes.**

- failure: Unbalanced '}' or leftover open '{' triggers the trailing assert len(stack) == 1 AssertionError; a non-marker non-empty line violates the inner assert.

<a id="u-62647747da9d"></a>
### `dummy_highlighter`

`def dummy_highlighter(source: str, lexer: Literal["diff", "python"] = "python") -> str:` · [src/_pytest/assertion/util.py:L46-L51][f1]

Identity highlighter returning its source string unchanged for either lexer ('diff' or 'python').

It exists so _notin_text can reuse _diff_text without applying color highlighting, since that diff is later post-processed to show only '+' lines.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/assertion/util.py
