# Mixed Syntax and Template Examples

**Capability.** Groups malformed C, Python wrappers, SQL select, C++ template Box, and maximum examples that exercise parser and syntax handling.

Come here for mixed-language snippets including a parser error, simple Python functions, a SQL statement, and C++ template/function examples. The broken C file's function boundaries are explicitly unreliable.

Parent: [Struct Closure Syntax Examples](struct-closure-syntax-examples.md)

## Units (6)

<a id="u-c063c70ccae1"></a>
### `crlf.py-wrap-class`

`class Wrap:` · [src/crlf.py:L5-L6][f1]

Wrap exposes one method that returns the literal string "ok".

<a id="u-568d50500096"></a>
### `sample.cpp-box-template`

`class Box` · [src/sample.cpp:L5-L9][f2]

Box is a template class holding a value, initialized by its constructor and read by get.

The constructor stores its argument in value; get returns that stored value.

<a id="u-71d56cf1faca"></a>
### `broken.c module code (L1–L5)`

`module_region` · [src/broken.c:L1-L5][f3]

The file contains malformed C declarations; the parser reports a syntax error near line 1, so function boundaries are unreliable.

<a id="u-484deef72ec0"></a>
### `first`

`def first(a):` · [src/crlf.py:L2-L3][f1]

first returns its argument plus one.

<a id="u-1ee0163af371"></a>
### `q.sql module code (L1–L1)`

`module_region` · [src/q.sql:L1-L1][f4]

The file contains a single SQL statement selecting 1; no declarations or functions are present.

<a id="u-b90b2acf48ce"></a>
### `maximum`

`template <typename T> T maximum(T a, T b)` · [src/sample.cpp:L13-L19][f2]

maximum returns a when a is greater than b, otherwise it returns b.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: ../../source/src/crlf.py
[f2]: ../../source/src/sample.cpp
[f3]: ../../source/src/broken.c
[f4]: ../../source/src/q.sql
