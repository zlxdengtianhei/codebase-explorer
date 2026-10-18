# Expression compilation and matcher bridge

**Capability.** Expression as a compiled match expression holding a code object, and the adapters bridging the parsed AST to a caller-supplied matcher callable.

The entry layer: compile and evaluate expressions against matchers. It calls into parsing and the matcher adapters.

**Depends on.**

- [Expression lexer](r4-expression-lexing.md) · graph-confirmed · 1 edge(s)
- [Expression parser](r4-expression-parsing.md) · graph-confirmed · 1 edge(s)

Parent: [Mark expression evaluation](r4-mark-expression.md)

## Units (2)

<a id="u-32276e45b778"></a>
### `expression.py-compile-and-evaluate`

`class Expression:` · [src/_pytest/mark/expression.py:L296-L304][f1]

Expression is a compiled match expression holding a code object in __slots__.

compile() parses the input through expression(Scanner(input)) and compiles the resulting AST in 'eval' mode with filename '<pytest match expression>', returning an Expression. evaluate() runs eval on the code with globals {'__builtins__': {}} and a MatcherAdapter of the given matcher as locals, returning the boolean result — so identifiers resolve through the matcher and no builtins are available to the expression. An empty expression compiles to Constant(False) and therefore always evaluates False.

<a id="u-fe83d5189674"></a>
### `expression.py-matcher-adapters`

`class MatcherCall(Protocol):` · [src/_pytest/mark/expression.py:L264-L265][f1]

Bridge between parsed AST and a matcher callable.

MatcherCall is a typing Protocol for callables (name, /, **kwargs) -> bool; its __call__ entry is declaration-only. MatcherNameAdapter wraps a matcher plus one name: __bool__ calls matcher(name), __call__ forwards call parameters as matcher(name, **kwargs), so bare identifiers evaluate via truthiness and ident(k=v) via kwargs filtering. MatcherAdapter adapts the matcher to a Mapping for eval(): __getitem__ strips the '$' IDENT_PREFIX from the key and returns a MatcherNameAdapter for the remaining name; __iter__ and __len__ raise NotImplementedError because eval mode never needs them.

**Uncertainties.**

- Whether eval in 'eval' mode can ever trigger MatcherAdapter.__iter__/__len__ is not proven here; the NotImplementedError paths are untested by this module.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/mark/expression.py
