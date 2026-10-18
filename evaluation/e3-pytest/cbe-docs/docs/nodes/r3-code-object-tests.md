# Code & Frame Tests

**Capability.** Tests Code equality by underlying code object, path/name exposure, getargs across signatures, Frame source/statement and getargs with live values, plus ExceptionInfo, TracebackEntry, and ExceptionChainRepr behavior including non-ASCII payloads.

Use this subtree for the runtime introspection side (_pytest._code). The helpers raise NotImplementedError so only their source matters, exercising the source-recovery paths.

Parent: [Code Introspection Test Suite](r3-code-introspection-tests.md)

## Units (13)

<a id="u-1bb57683f04b"></a>
### `test_code.py-code-source-helpers`

`def x() -> None:` · [testing/code/test_code.py:L42-L43][f1]

Helper x raises NotImplementedError; only its source matters.

test_code_fullsource wraps Code.from_function(x) and asserts the fullsource contains the caller expression 'test_code_fullsource()'. test_code_source asserts code.source() reproduces x's exact two-line definition byte-faithfully.

**Uncertainties.**

- test_code_fullsource's expectation depends on Frame/Source call-site reconstruction not visible here.

<a id="u-fa60b301c3ac"></a>
### `test_code.py-frame-tests`

`def test_frame_getsourcelineno_myself() -> None:` · [testing/code/test_code.py:L60-L61][f1]

Covers Frame source and statement behavior.

test_frame_getsourcelineno_myself wraps sys._getframe(0) from an inner func and asserts source[lineno] starts with the indented 'return sys._getframe(0)'. test_getstatement_empty_fullsource patches the frame code class so fullsource is None and asserts f.statement degrades to an empty Source('') instead of raising.

**Uncertainties.**

- The exact f.lineno indexing offset into the deindented Source is pinned only by this test's expected prefix.

<a id="u-88400477cb37"></a>
### `test_code.py-test_code_from_function_with_class`

`def test_code_from_function_with_class() -> None:` · [testing/code/test_code.py:L34-L35][f1]

Verifies Code.from_function rejects a class.

A local class A with no members is defined and the test expects Code.from_function(A) to raise TypeError, documenting that from_function accepts functions, not classes.

<a id="u-694f367c9d01"></a>
### `test_code.py-test_code_getargs`

`def test_code_getargs() -> None:` · [testing/code/test_code.py:L95-L96][f1]

Checks Code.getargs(var=True) name extraction across signatures: f1(x) yields ('x',); f2(x, *y) adds 'y'; f3(x, **z) adds 'z'; f4(x, *y, **z) returns ('x','y','z').

Inner functions only supply signatures.

<a id="u-e40b8e2e9e40"></a>
### `test_code.py-test_frame_getargs`

`def test_frame_getargs() -> None:` · [testing/code/test_code.py:L121-L122][f1]

Checks Frame.getargs(var=True), pairing parameter names with live frame values: f1('a') gives [('x','a')]; f2('a','b','c') gives the vararg as a tuple [('y',('b','c'))]; f3('a',b='c') gives [('z',{'b':'c'})]; f4 combines all three.

Each inner function returns sys._getframe(0) so the Frame carries the actual bound arguments.

<a id="u-697c51bf679b"></a>
### `test_code.py-test_unicode_handling`

`def test_unicode_handling() -> None:` · [testing/code/test_code.py:L85-L88][f1]

Exercises exception formatting with non-ASCII bytes: f raises Exception with the UTF-8 encoding of 'ąć'; pytest.raises captures it and str(excinfo) must succeed, showing the repr path tolerates bytes payloads.

<a id="u-a0ba8d94b617"></a>
### `TestExceptionInfo`

`class TestExceptionInfo:` · [testing/code/test_code.py:L147-L148][f1]

Tests ExceptionInfo capture and misuse.

test_bad_getsource forces an AssertionError via if False/else, captures ExceptionInfo.from_current() in the except block, and asserts getrepr() is truthy despite potentially missing source. test_from_current_with_missing expects from_current() with no active exception to raise AssertionError matching 'no current exception'.

<a id="u-330ec7523b06"></a>
### `TestTracebackEntry`

`class TestTracebackEntry:` · [testing/code/test_code.py:L163-L164][f1]

Tests TracebackEntry source access and string form.

test_getsource captures an AssertionError traceback, takes entry 0, and asserts getsource() returns a 6-line Source whose line 5 contains 'assert False', covering multi-line statement retrieval. test_tb_entry_str str()'s an entry and matches the pattern File '<file>':<lineno> in <name> plus the failing line, pinning the entry's textual format.

<a id="u-e300de5ffa61"></a>
### `TestReprFuncArgs`

`class TestReprFuncArgs:` · [testing/code/test_code.py:L188-L189][f1]

Verifies ReprFuncArgs.toterminal does not raise on mixed encodings: args pair a unicode string ('São Paulo') with a bytes value; the rendered first terminal line must show the unicode decoded and the bytes as an escaped literal.

<a id="u-e0357bf2dfdc"></a>
### `test_ExceptionChainRepr`

`def test_ExceptionChainRepr():` · [testing/code/test_code.py:L201-L215][f1]

Tests ExceptionChainRepr construction and hashability.

Two separate ValueError exception captures produce getrepr() results that are unequal, hash differently, and are distinct objects even when re-requested from the same excinfo, so each getrepr call creates a fresh repr instance.

<a id="u-0f1fb7776bde"></a>
### `test_code_from_func`

`def test_code_from_func() -> None:` · [testing/code/test_code.py:L79-L82][f1]

Sanity-checks Code.from_function on a test function: asserts the produced Code has a truthy firstlineno and a resolvable path.

<a id="u-619367b4f28d"></a>
### `test_code_gives_back_name_for_not_existing_file`

`def test_code_gives_back_name_for_not_existing_file() -> None:` · [testing/code/test_code.py:L25-L31][f1]

Checks Code exposure of a fabricated filename.

Compiles 'pass' under the nonexistent name 'abc-123', wraps it in Code, and asserts str(code.path) equals that name while fullsource is None, since no real file can be read.

<a id="u-f7bd0ca4f25e"></a>
### `test_ne`

`def test_ne() -> None:` · [testing/code/test_code.py:L18-L22][f1]

Verifies Code equality semantics for compiled code objects: a Code equals itself, while two Codes wrapping distinct compile results compare unequal, so underlying code-object identity drives __eq__/__ne__.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/code/test_code.py
