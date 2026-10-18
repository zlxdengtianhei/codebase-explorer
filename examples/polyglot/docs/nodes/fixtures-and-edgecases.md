# Encoding and Parser Fixtures

**Capability.** Owns the corpus's edge-case fixtures: the CRLF-line-ending crlf.py (trivial Wrap and first), unicode.py exercising non-ASCII identifiers and emoji literals, the uncompilable broken.c residual, and the always-passing placeholder test. Each exists to verify toolchain behavior (encoding, line endings, error tolerance), not to deliver application capability.

Read these only when validating parser/encoding behavior; broken.c has no attributable behavior as written. test_x.py is a trivial passing placeholder. crlf.py's first and unicode.py's café return small deterministic sums.

Parent: [Polyglot Sample Corpus](sample-corpus.md)

## Units (6)

<a id="u-694cd62c19f1"></a>
### `crlf-py-wrap`

`def one(self):` · [src/crlf.py:L6-L7][f1]

Wrap's only behavior is the method one, which returns the constant string "ok".

It holds no state and takes no inputs; under the visible code it cannot fail.

<a id="u-484deef72ec0"></a>
### `first`

`def first(a):` · [src/crlf.py:L2-L3][f1]

first returns its argument plus 1.

It accepts any value supporting addition with the int 1; for incompatible operands a TypeError propagates from the addition. No other branches or side effects exist.

<a id="u-5c3b99e6f290"></a>
### `unicode-py-class`

`def emoji(self):` · [src/unicode.py:L7-L8][f2]

Ünïcode's only behavior is the method emoji, which returns the constant string "✓".

The class holds no state; the non-ASCII name affects only identifiers, not behavior.

<a id="u-63e2e1024b07"></a>
### `café`

`def café(naïve, 数=1):` · [src/unicode.py:L2-L4][f2]

café returns naïve + 数, adding its first argument to the keyword 数 which defaults to 1.

Identifiers and the docstring are non-ASCII but behavior is ordinary addition; incompatible operands raise TypeError. Callers omitting 数 get the default 1.

<a id="u-71d56cf1faca"></a>
### `broken.c module code (L1–L5)`

`module_region` · [src/broken.c:L1-L5][f3]

This C file is not compilable as written: the first function header 'int broken( {' is malformed, so no behavior can be attributed to broken.

The preserved text also shows ok defined to return 2, but because the translation unit is ill-formed, the parse effect on the second definition cannot be established from the source.

**Uncertainties.**

- Whether the ERROR node affects how much of ok() parsed correctly; only the preserved residual text is available.

<a id="u-7f6ce92bf7b8"></a>
### `test_x`

`def test_x():` · [tests/test_x.py:L1-L2][f4]

Placeholder test that always passes, asserting the constant True.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/crlf.py
[f2]: ../../source/src/unicode.py
[f3]: ../../source/src/broken.c
[f4]: ../../source/tests/test_x.py
