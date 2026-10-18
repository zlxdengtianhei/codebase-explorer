# Pytest Framework Codebase

**Capability.** Owns pytest's user-facing runtime capabilities — terminal I/O, output capture, marking/selection, warning handling, and report production — together with the framework's own test suites for these capabilities.

Use this root to navigate between runtime plugin capabilities under src/_pytest and the self-test suites under testing/. Each subtree groups one module-level responsibility with its verifying tests.

**Children.**

- [Terminal Output & Pretty-Printing](r3-terminal-io.md) `r3-terminal-io` · 0 unit(s)
- [Output & Input Capture](r3-io-capture.md) `r3-io-capture` · 0 unit(s)
- [Marking & Test Selection](r3-marking.md) `r3-marking` · 0 unit(s)
- [Warning Handling](r3-warnings.md) `r3-warnings` · 0 unit(s)
- [Test & Collection Reports](r3-reports.md) `r3-reports` · 0 unit(s)
- [Warning Assertion Helpers](r3-recwarn.md) `r3-recwarn` · 8 unit(s)
- [pytest.raises Test Suite](r3-raises-tests.md) `r3-raises-tests` · 12 unit(s)
- [Code Introspection Test Suite](r3-code-introspection-tests.md) `r3-code-introspection-tests` · 0 unit(s)
- [Assertion Rewrite Test Suite](r3-assertrewrite-tests.md) `r3-assertrewrite-tests` · 0 unit(s)
- [Thread & Unraisable Exception Warning Tests](r3-exception-warning-tests.md) `r3-exception-warning-tests` · 17 unit(s)
- [Test-Suite Infrastructure](r3-test-infra.md) `r3-test-infra` · 0 unit(s)

Parent: [Platform, I/O and Reporting Plugins](platform-io-plugins.md)

## Units (1)

<a id="u-07ae84cefd56"></a>
### `test_source.py-test_source_with_decorator`

`def test_source_with_decorator() -> None:` · [testing/code/test_source.py:L463-L466][f1]

Compares Source/decorator interaction with inspect.getsource.

For a @pytest.mark.foo-decorated function, indented Source output equals getsource exactly, confirming Source includes the decorator line. For a @pytest.fixture-decorated function, getsource of _get_wrapped_function() still shows the fixture decorator, Source(fixture) does not start with '@functools.wraps(function)', and indenting Source of the wrapped function reproduces getsource — the wrapped function is not itself treated as a wrapped artifact.

**Uncertainties.**

- _get_wrapped_function is a pytest fixture-runtime attribute whose definition is not in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/code/test_source.py
