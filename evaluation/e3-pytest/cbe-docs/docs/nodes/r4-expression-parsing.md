# Expression parser

**Capability.** Recursive-descent parser producing a Python AST for the match grammar, including parsing of keyword arguments inside ident(...) calls.

Consumes the token stream from the lexer; heavily dependent on it (11 call edges from grammar, 8 from kwargs parsing). Output ASTs are handed to evaluation.

**Depends on.**

- [Expression lexer](r4-expression-lexing.md) · graph-confirmed · 19 edge(s)

**Depended on by.**

- [Expression compilation and matcher bridge](r4-expression-evaluation.md) · graph-confirmed · 1 edge(s)

Parent: [Mark expression evaluation](r4-mark-expression.md)

## Units (2)

<a id="u-c85630370b91"></a>
### `expression.py-grammar`

`def expression(s: Scanner) -> ast.Expression:` · [src/_pytest/mark/expression.py:L175-L181][f1]

Recursive-descent parser producing Python AST for the match grammar.

expression(): an empty input (EOF accepted first) yields the constant False; otherwise parse expr and require EOF (reject=True fails otherwise), returning ast.fix_missing_locations(ast.Expression(ret)). expr() parses and_expr and folds left-associative 'or' chains into ast.BoolOp(ast.Or()). and_expr() likewise folds 'not_expr and not_expr' with ast.And(). not_expr() handles, in order: 'not' prefix → ast.UnaryOp(ast.Not(), recursive); '(' expr ')' with required RPAREN; an IDENT, optionally followed by '(' kwargs ')' → ast.Call with $-prefixed name and empty args; anything else is rejected with a ParseError listing not/LPAREN/IDENT. IDENT_PREFIX '$' prefixes every identifier so the reserved Python names True/False/None become legal expression names.

<a id="u-be2c209de3d8"></a>
### `expression.py-kwargs-parsing`

`def single_kwarg(s: Scanner) -> ast.keyword:` · [src/_pytest/mark/expression.py:L223-L254][f1]

Parses keyword arguments inside ident(...) calls.

single_kwarg() requires an IDENT keyword name (reject=True otherwise), failing with ParseError when it is not a valid Python identifier or is a reserved Python keyword; then requires '='; then takes either a STRING token whose quotes are stripped, or an IDENT that must be a (possibly negative) integer literal or one of True/False/None (mapped via BUILTIN_MATCHERS to True/False/None); anything else raises ParseError 'unexpected character/s'. all_kwargs() parses one kwarg and continues while commas appear, returning the ast.keyword list.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/mark/expression.py
