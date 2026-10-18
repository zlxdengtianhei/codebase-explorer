# Source Construction & Access Tests

**Capability.** Tests the Source container: construction from functions, methods, inner functions, lines, and strings; deindent and strip semantics; sequence access; getstartingblock frame statements; findsource for compiled code; and getfslineno across object kinds.

Use this subtree for Source-level behavior rather than statement boundaries. These tests establish how source text is acquired, normalized, and located on disk before any slicing happens.

**Depended on by.**

- [Statement Recovery Tests](r3-source-statement-recovery.md) · model-inferred · 0 edge(s)

Parent: [Code Introspection Test Suite](r3-code-introspection-tests.md)

## Units (17)

<a id="u-1b0dd86151d7"></a>
### `TestAccesses`

`class TestAccesses:` · [testing/code/test_source.py:L76-L77][f1]

Exercises Source sequence-style access against a shared four-line source of two def blocks.

test_getrange slices [0:2] into a two-line Source whose str is the first def block; test_getrange_step_not_supported expects IndexError mentioning 'step' for a [::2] slice, so extended slicing is rejected; test_getline indexes [0] to the raw line text; test_len and test_iter confirm len 4 and iteration yielding four lines.

<a id="u-994dec5a1184"></a>
### `test_source.py-source-from-method-inner`

`def test_source_from_method() -> None:` · [testing/code/test_source.py:L39-L40][f1]

Verifies Source works on bound methods and inner functions: test_source_from_method wraps TestClass().test_method and expects exact lines ['def test_method(self):','    pass']; test_source_from_inner_function wraps a nested f and asserts the def line starts the source, showing nested-function source is recoverable via file introspection.

<a id="u-7b225610593d"></a>
### `test_source.py-getfuncsource`

`def test_getfuncsource_dynamic() -> None:` · [testing/code/test_source.py:L243-L244][f1]

Verifies Source(func) source recovery.

test_getfuncsource_dynamic asserts nested f and g recover to exactly their def plus one body line after strip, including inline comments. test_getfuncsource_with_multiline_string asserts a function whose body contains a triple-quoted string spanning lines is recovered with its internal indentation and newlines intact, comparing to an exact expected text with rstrip.

<a id="u-2f865fb8b1d4"></a>
### `test_source.py-getstartingblock-singleline`

`def test_getstartingblock_singleline() -> None:` · [testing/code/test_source.py:L216-L217][f1]

Verifies Frame.statement reconstruction at a call site.

A's __init__ captures sys._getframe(1) — the caller's frame — and stores Frame(frame).statement; constructing A('x','y') from the test body yields a statement source whose non-blank lines number exactly one, i.e. the single-line call expression is recovered.

<a id="u-ac7ac74c118f"></a>
### `test_source.py-getstartingblock-multiline`

`def test_getstartingblock_multiline() -> None:` · [testing/code/test_source.py:L636-L637][f1]

Like the singleline case, A.__init__ stores Frame(sys._getframe(1)).statement for the caller; a multi-line call A('x','y','z') spread over four source lines yields a statement whose non-blank lines number exactly four, showing the full physical call expression is recovered.

<a id="u-c82d25d71e57"></a>
### `test_source.py-code-of-object-instance-with-call`

`def test_code_of_object_instance_with_call() -> None:` · [testing/code/test_source.py:L378-L379][f1]

Tests Code/Source on object instances.

Source(A()) on a plain instance raises TypeError. Code.from_function(WithCall()) — an instance with __call__ — succeeds and its source contains 'pass'. Code.from_function(Hello), the class itself rather than an instance, raises TypeError, so from_function distinguishes callable instances (accepted) from classes (rejected).

<a id="u-952667169a87"></a>
### `test_source.py-fallback-x`

`def x():` · [testing/code/test_source.py:L304-L305][f1]

Uses the module-level x() defined under 'if True:' at end of file.

test_source_fallback asserts Source(x) recovers exactly 'def x():\n    pass', exercising the fallback source path for a function whose definition is nested in an if block. test_findsource_fallback asserts findsource(x) returns non-None source containing 'test_findsource_simple' with src[lineno] equal to the indented def line, pinning the reported line number to the def rather than the if line.

**Uncertainties.**

- test_findsource_fallback expects the literal 'test_findsource_simple' in the source, which is not visible in this file excerpt; likely a function name in the same module or an assertion key on a fixture-modified source.

<a id="u-9a2c37a8677e"></a>
### `test_source.py-test_getfslineno`

`def test_getfslineno() -> None:` · [testing/code/test_source.py:L345-L346][f1]

Tests getfslineno across object kinds.

For a function f it returns a Path named test_source.py and lineno equal to co_firstlineno - 1 (comment: 'see findsource'). For a class A the lineno matches inspect.findsource's reported line. For the non-source value 3 it returns ('', -1). For class B renamed via __name__/__qualname__ to 'B2', behavior is version-dependent: on Python ≥3.13 the line number resolves (≠ -1); before that it returns -1.

<a id="u-a190328789f6"></a>
### `test_source.py-module-residuals`

`group` · [testing/code/test_code.py:L1-L17][f2]

Module-level import blocks and residual regions carry no behavior of their own: test_code.py's header imports re, sys, FrameType, unittest.mock, and the _pytest._code names Code, ExceptionInfo, Frame, Source, ExceptionChainRepr, ReprFuncArgs plus pytest; test_source.py's header imports inspect, linecache, Path, sys, textwrap, typing.Any, the _pytest._code names Code, Frame, getfslineno, Source, import_path, and pytest, with a trailing residual after the last test.

These names supply the API surface the tests exercise.

<a id="u-a5d5cca70f38"></a>
### `test_source_str_function`

`def test_source_str_function() -> None:` · [testing/code/test_source.py:L19-L31][f1]

Pins Source(str) construction: '3' stays '3'; leading whitespace is stripped ('   3' becomes '3'); a multi-line block with surrounding blank lines deindents to '\n3', keeping the internal newline but trimming common indentation and outer blank lines.

uses: [test_source_str_function](r3-source-construction-tests.md#u-a5d5cca70f38)

<a id="u-f6d0bce9dba0"></a>
### `test_source_from_function`

`def test_source_from_function() -> None:` · [testing/code/test_source.py:L34-L36][f1]

Asserts Source(function) starts with the function's def line, i.e. source introspection includes the signature.

<a id="u-404ad8bb55b2"></a>
### `test_source_from_lines`

`def test_source_from_lines() -> None:` · [testing/code/test_source.py:L48-L51][f1]

Checks Source(list_of_lines) construction strips trailing newlines: ['a \n','b\n','c'] yields lines ['a ','b','c'], keeping interior spacing but removing line terminators.

<a id="u-722b2fd44b13"></a>
### `test_deindent`

`def test_deindent() -> None:` · [testing/code/test_source.py:L271-L282][f1]

Tests the deindent helper on line lists: tab-indented lines become unindented; a multi-line source deindents each line by the block's common leading whitespace, preserving relative nesting ('def f():' then nested 'def g():' at one and two levels).

<a id="u-8dc70a4310a3"></a>
### `test_source_strip_multiline`

`def test_source_strip_multiline() -> None:` · [testing/code/test_source.py:L69-L73][f1]

Sets lines ['', ' hello', '  '] and asserts strip() drops leading blank and whitespace-only lines, leaving only [' hello']; blank/whitespace-only lines inside are removed from the edges.

<a id="u-70da737e7930"></a>
### `test_source_strips`

`def test_source_strips() -> None:` · [testing/code/test_source.py:L62-L66][f1]

Asserts an empty Source equals the default Source, str()'s to '', and strip() is idempotent on already-blank sources.

<a id="u-dd8d08e24b61"></a>
### `test_source_of_class_at_eof_without_newline`

`def test_source_of_class_at_eof_without_newline(_sys_snapshot, tmp_path: Path) -> Non…` · [testing/code/test_source.py:L285-L299][f1]

Round-trips a class written to a file lacking a trailing newline: the module is imported via import_path and Source(mod.A) must match the original written source after strip.

The comment notes the test previously failed because implicit inspect.getsource(A) omitted the last 'x = 1' line, so this pins end-of-file handling.

<a id="u-7e3a8630ea74"></a>
### `test_findsource`

`def test_findsource(monkeypatch) -> None:` · [testing/code/test_source.py:L324-L342][f1]

Tests findsource for compiled code without a real file.

It compiles three lines under the pseudo-filename '<pytest-test_findsource>', injects them into linecache.cache via monkeypatch.setitem (auto-undone after the test), and asserts findsource(co) returns source containing 'if 1:'. It then evals the code object to obtain function x and asserts findsource(x) finds the same source with src[lineno] equal to the indented 'def x():' line, showing the nested-in-if def is located correctly.

calls: [MonkeyPatch.setitem](r6-monkeypatch-engine.md#u-0494ec708f24)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/code/test_source.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/code/test_code.py
