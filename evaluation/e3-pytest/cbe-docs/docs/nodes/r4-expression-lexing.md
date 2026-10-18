# Expression lexer

**Capability.** TokenType naming the token kinds and Token as a frozen dataclass of type/value/position, plus the scanning routines producing the token stream.

The lowest layer of the expression pipeline; both the grammar parser and kwargs parsing consume this token stream.

**Depended on by.**

- [Expression compilation and matcher bridge](r4-expression-evaluation.md) · graph-confirmed · 1 edge(s)
- [Expression parser](r4-expression-parsing.md) · graph-confirmed · 19 edge(s)

Parent: [Mark expression evaluation](r4-mark-expression.md)

## Units (1)

<a id="u-9e25ac56abdb"></a>
### `expression.py-lexing`

`class TokenType(enum.Enum):` · [src/_pytest/mark/expression.py:L46-L56][f1]

TokenType names the token kinds (LPAREN, RPAREN, OR, AND, NOT, IDENT, EOF, EQUAL, STRING, COMMA); Token is a frozen dataclass of type, value, and 0-based pos.

ParseError carries a 1-based column and message, with __str__ rendering 'at column <column>: <message>'. Scanner turns the input string into a token generator in lex: whitespace is skipped; '(', ')', '=', ',' become their tokens; a quoted string must find its closing quote within the same input or ParseError 'closing quote ... is missing' is raised, and any backslash anywhere in the input raises ParseError rejecting escapes; otherwise a regex of word/:+-.[ ]\/ characters forms an ident, mapped to OR/AND/NOT for the keywords or IDENT, and any other character raises ParseError 'unexpected character'. lex ends with an EOF token. Scanner.__init__ stores the generator and primes self.current with the first token. accept (three entries: two overloads and the implementation) returns and advances past the current token when its type matches — except EOF, which never advances — otherwise returns None, or calls reject when reject=True. reject raises ParseError listing the expected types versus the current one, at column current.pos + 1.

**Notes.**

- failure: The backslash escape check searches the whole input (input.find('\\')), so a backslash anywhere — even later outside a string — fails lexing with an escape-rejection ParseError.

**Uncertainties.**

- Because the escape check scans the entire input, a backslash in an unrelated part of the expression rejects lexing before parsing; this looks intentional but its rationale is not stated in code.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/mark/expression.py
