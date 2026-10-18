# Mark expression evaluation

**Capability.** The small language behind -m/-k style match expressions: lexing, recursive-descent parsing (including keyword arguments) to a Python AST, and compiling that AST against a matcher callable.

Follow lexing → parsing → evaluation to trace a match expression from string to boolean result. The module preamble/exports live at this node.

**Children.**

- [Expression lexer](r4-expression-lexing.md) `r4-expression-lexing` · 1 unit(s)
- [Expression parser](r4-expression-parsing.md) `r4-expression-parsing` · 2 unit(s)
- [Expression compilation and matcher bridge](r4-expression-evaluation.md) `r4-expression-evaluation` · 2 unit(s)

Parent: [Runtime library](r4-runtime-library.md)

## Units (1)

<a id="u-52f6835e917e"></a>
### `expression.py module code (L1–L45)`

`module_region` · [src/_pytest/mark/expression.py:L1-L45][f1]

Module docstring (grammar and semantics), imports, and __all__ = ['Expression', 'ParseError']; no behavior.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/mark/expression.py
