# Edge-Case Parsing Fixtures

**Capability.** Collects C, Python, and SQL files exercising parser edge cases: syntax errors, CRLF, unicode identifiers, and trivial statements.

Readers testing how tooling handles unusual or malformed sources should come here. The module spans a C file with a syntax error, unicode-identifier Python, a CRLF Python file, a single-statement SQL file, and well-formed C functions.

Parent: [Parser Fixtures and Type Samples](parser-fixtures-and-type-samples.md)

## Units (8)

<a id="u-c063c70ccae1"></a>
### `crlf.py-wrap-class`

`class Wrap:` · [src/crlf.py:L5-L6][f1]

Wrap defines one method that takes no arguments and returns the string "ok"; it has no state or constructor.

<a id="u-8b613b5bbcfe"></a>
### `unicode.py-n-code-class`

`class Ünïcode:` · [src/unicode.py:L6-L7][f2]

Class with a non-ASCII name whose single method emoji takes no arguments and returns the string "✓".

<a id="u-71d56cf1faca"></a>
### `broken.c module code (L1–L5)`

`module_region` · [src/broken.c:L1-L5][f3]

Region contains a function with a syntax error near line 1 (missing closing parenthesis in the parameter list), so the tree has an ERROR node; a later well-formed function returning 2 also appears in the region but declaration-level detail is degraded.

**Uncertainties.**

- Parser reports an ERROR node; exact symbol boundaries within this region may be unreliable.

<a id="u-484deef72ec0"></a>
### `first`

`def first(a):` · [src/crlf.py:L2-L3][f1]

Returns its single argument plus one.

<a id="u-1ee0163af371"></a>
### `q.sql module code (L1–L1)`

`module_region` · [src/q.sql:L1-L1][f4]

Whole-file SQL chunk containing the single statement 'select 1;', which yields the constant value 1 with no table references or parameters.

**Uncertainties.**

- No SQL grammar is registered, so only the frozen whole-file chunk is available; richer statement structure cannot be confirmed.

<a id="u-cef680402725"></a>
### `add`

`static int add(int a, int b)` · [src/sample.c:L9-L11][f5]

Static function returning the sum of its two integer parameters; a comment documents it as adding two integers.

No overflow handling.

<a id="u-69596f14b24e"></a>
### `main`

`int main(void)` · [src/sample.c:L13-L17][f5]

Entry point that initializes a local Point with x=1, y=2, prints add(p.x, p.y) via printf with a newline format, and returns 0.

<a id="u-63e2e1024b07"></a>
### `café`

`def café(naïve, 数=1):` · [src/unicode.py:L2-L4][f2]

Function with non-ASCII name and parameters that returns naïve + 数, with 数 defaulting to 1; the UTF-8 coding declaration at the top of the file supports these identifiers.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/crlf.py
[f2]: ../../source/src/unicode.py
[f3]: ../../source/src/broken.c
[f4]: ../../source/src/q.sql
[f5]: ../../source/src/sample.c
