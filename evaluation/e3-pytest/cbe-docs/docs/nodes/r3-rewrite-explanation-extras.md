# Explanation Features Tests

**Capability.** Tests auxiliary explanation features: the assertion-pass hook and its ini option, verbosity-controlled saferepr truncation, unbounded saferepr formatting, and _get_assertion_exprs expression extraction.

Use this subtree for features around the rewritten explanation output rather than the rewrite itself. Each group targets one option or helper with focused unit or pytester tests.

Parent: [Assertion Rewrite Test Suite](r3-assertrewrite-tests.md)

## Units (4)

<a id="u-741682dff23e"></a>
### `test_assertrewrite.py-assertion-pass`

`class TestAssertionPass:` · [testing/test_assertrewrite.py:L2006-L2007][f1]

TestAssertionPass covers the enable_assertion_pass_hook ini option and the pytest_assertion_pass hook.

test_option_default parses a bare config and asserts the ini value defaults to False. The flag_on fixture writes an ini enabling the option; hook_on writes a conftest whose pytest_assertion_pass raises an Exception carrying orig, expl and lineno, making the hook's invocation observable in output. test_hook_call (flag on) expects the line 'Assertion Passed: a+b == c+d (1 + 2) == (3 + 0) at line 7' plus a failing message assert in the same run; test_hook_call_with_parens expects 'Assertion Passed: f() 1'. The negative tests monkeypatch _pytest.assertion.rewrite._call_assertion_pass to raise if ever called: test_hook_not_called_without_hookimpl (flag on, no hook impl) and test_hook_not_called_without_cmd_option (hook impl present, option off) both require the test to pass, proving the callback and formatting are skipped in each case.

**Uncertainties.**

- The exact gating between _call_assertion_pass and the plugin hook lives in _pytest.assertion.rewrite.

<a id="u-bce6042d2701"></a>
### `test_assertrewrite.py-repr-size-verbosity`

`class TestReprSizeVerbosity:` · [testing/test_assertrewrite.py:L2307-L2313][f1]

TestReprSizeVerbosity checks that verbosity controls the saferepr truncation threshold.

test_get_maxsize_for_saferepr is parametrized: verbosity 0 yields DEFAULT_REPR_MAX_SIZE, 1 yields ten times that, and 2 or 3 yield None (unbounded), using a FakeConfig whose get_verbosity returns the parametrized value cast to Config. test_get_maxsize_for_saferepr_no_config asserts None config falls back to DEFAULT_REPR_MAX_SIZE. create_test_file writes a test asserting a substring inside a long 'x' string of given size. The session tests then pin output: at default verbosity the long string appears truncated as 'xxx...xxx'; at -v the DEFAULT_REPR_MAX_SIZE string is shown whole; at -vv even a ten-times-larger string is shown whole (no truncation marker).

<a id="u-0578be030e57"></a>
### `test_assertrewrite.py-saferepr-unbounded`

`class TestSafereprUnbounded:` · [testing/test_assertrewrite.py:L2372-L2373][f1]

TestSafereprUnbounded checks _saferepr formatting of methods and objects.

test_saferepr_bound_method asserts a bound method of the nested Help class formats as just 'bound_method'. test_saferepr_unbounded asserts an instance formats as '<{module}.{qualname}.Help object at 0x...>' matched by a regex built from Path(__file__).stem and the class name (avoiding platform-specific id()), and the class itself formats as "<class 'module...Help'>" — i.e. unbounded (None maxsize) reprs keep full information.

<a id="u-5e1bfefdd0f0"></a>
### `test_get_assertion_exprs`

`def x(): assert 1\n", {1: "1"}, id="assert statement not on own line", ), pytest.para…` · [testing/test_assertrewrite.py:L2119-L2201][f1]

Parametrized unit test for _get_assertion_exprs over twelve source-byte cases.

It asserts the returned lineno-to-expression-string mapping for: empty source, single-line asserts, multiple asserts, latin1 and utf-8 encoded non-ASCII on the first line, multi-line parenthesized asserts preserving inner whitespace and comments, list-literal continuations, backslash continuations (including escaped newlines before a message), asserts with messages (only the test expression, not the message, is captured), and a file without a trailing newline.

**Uncertainties.**

- The parsing implementation under test lives in _pytest.assertion.rewrite.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_assertrewrite.py
