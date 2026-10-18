# Mark Expression Test Suite

**Capability.** Parametrized tests of mark-expression parsing and evaluation through a shared evaluate helper and a session-scoped MarkMatcher fixture covering numbers, builtins, strings and unicode identifiers.

Use this when changing the mark expression grammar or matcher semantics; all cases flow through evaluate.

Parent: [pytest Core](r9-pytest-core.md)

## Units (3)

<a id="u-ae6a8bc4d9db"></a>
### `test_mark_expression-tests`

`def test_empty_is_false() -> None:` · [testing/test_mark_expression.py:L17-L21][f1]

Parametrized tests of mark-expression parsing and evaluation, all through the evaluate helper.

test_empty_is_false asserts empty and whitespace-only expressions evaluate falsy regardless of the matcher. test_basic and test_syntax_oddities cover boolean truth tables, not/and/or nesting, parentheses, and liberal whitespace, with matcher {'true': True, 'false': False}.__getitem__. test_backslash_not_treated_specially shows backslashes are ordinary identifier characters: the raw string \nfoo\n matches a set containing it literally, 'foo' does not, and a real newline in the expression raises ParseError. test_syntax_errors checks ParseError column and exact message for eleven malformed inputs, including trailing operators and stray identifiers. test_valid_idents confirms punctuation-heavy, numeric, keyword-prefixed ('1234and', 'notandor'), unicode, and Python-keyword identifiers ('True', 'if') all parse; test_invalid_idents confirms bare punctuation characters and '←' raise ParseError. test_invalid_kwarg_name_or_value, using the mark_matcher fixture, checks ParseError messages for reserved keywords as kwarg names, non-identifier names, unterminated quotes, unsupported backslash escaping, empty-list values, and bare string literals. test_keyword_expressions_with_numbers, test_builtin_matchers_keyword_expressions, and test_str_keyword_expressions evaluate keyword arguments against the fixture's marks: numeric comparisons pass only on exact values (a='1' fails), None matches only z=None (z=0/1/True/False all fail), and string values must match exactly including empty strings and non-ASCII names.

calls: [evaluate](r9-tests-mark-expression.md#u-a82f6b10bf2d); uses: [mark_matcher](r9-tests-mark-expression.md#u-d59be4fe68e0)

<a id="u-a82f6b10bf2d"></a>
### `evaluate`

`def evaluate(input: str, matcher: Callable[[str], bool]) -> bool:` · [testing/test_mark_expression.py:L13-L14][f1]

Compiles a mark expression string and evaluates it against a str-to-bool matcher, returning the boolean result.

The matcher is cast to MatcherCall, so the callable is invoked by identifier at evaluation time. Compilation errors from Expression.compile propagate as ParseError to the caller.

uses: [Expression](../../catalog.json)

<a id="u-d59be4fe68e0"></a>
### `mark_matcher`

`def mark_matcher() -> MarkMatcher:` · [testing/test_mark_expression.py:L241-L251][f1]

Session-scoped fixture building a MarkMatcher over three marks: number_mark(a=1,b=2,c=3,d=999_999), builtin_matchers_mark(x=True,y=False,z=None), and str_mark with string, space, empty and Hebrew-identifier values.

Returns MarkMatcher.from_markers(markers) for the keyword-expression tests; a failure in from_markers would surface as a fixture error for every dependent test.

**Uncertainties.**

- Behavior of MarkMatcher.from_markers is defined outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_mark_expression.py
