# Runtest Protocol Functional Tests

**Capability.** End-to-end single-item scenarios: pass/fail/skip outcomes, failures in setup/teardown, custom repr_failure, exact teardown regressions, hook ordering (logstart/logfinish), SystemExit vs exit/KeyboardInterrupt propagation, and session-abort teardown regressions.

Use this to verify report shapes per phase and which exceptions propagate out of runitem. BaseFunctionalTests scenarios are inherited by the non-forked execution suite.

**Depends on.**

- [Runtest Protocol](r9-runner-protocol.md) · model-inferred · 0 edge(s)

Parent: [Runner Test Suite](r9-tests-runner.md)

## Units (20)

<a id="u-aaa64dac507f"></a>
### `BaseFunctionalTests.test_passfunction`

> **ID corrected by CBE.** CBE changed the unit ID from ` testing/test_runner.py::method::BaseFunctionalTests.test_passfunction::6350 ` to the inventory ID ` testing/test_runner.py::method::BaseFunctionalTests.test_passfunction::6012 `. The model wrote this body under the wrong ID; it may be inaccurate.

`def test_passfunction(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L182-L193][f1]

Runs a trivially passing item via pytester.runitem; reports[1] (call) must be passed, not failed, with outcome 'passed' and no longrepr.

<a id="u-2235c710185b"></a>
### `BaseFunctionalTests.test_failfunction`

`def test_failfunction(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L195-L208][f1]

Runs an item executing `assert 0`; the call report is failed, not passed or skipped, when=='call', outcome 'failed'.

<a id="u-d80d9b35bc99"></a>
### `BaseFunctionalTests.test_skipfunction`

`def test_skipfunction(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L210-L228][f1]

Runs an item calling pytest.skip('hello'); the call report is skipped, not failed or passed, outcome 'skipped'.

<a id="u-b5fdd70bef91"></a>
### `BaseFunctionalTests.test_skip_in_setup_function`

`def test_skip_in_setup_function(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L230-L249][f1]

With setup_function skipping: reports[0] is skipped and not failed/passed, exactly two reports exist, and reports[1] (teardown) still passed — the call phase produces no report but teardown runs.

<a id="u-5387baae1e91"></a>
### `BaseFunctionalTests.test_failure_in_setup_function`

`def test_failure_in_setup_function(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L251-L266][f1]

setup_function raising ValueError(42): reports[0] failed, not skipped/passed, when=='setup', exactly two reports — the call phase never reports.

<a id="u-771a77dbcb9a"></a>
### `BaseFunctionalTests.test_failure_in_setup_function_ignores_custom_repr`

`def test_failure_in_setup_function_ignores_custom_repr( self, pytester: Pytester ) ->…` · [testing/test_runner.py:L419-L447][f1]

With a conftest Function whose repr_failure itself asserts 0, a setup_function raising ValueError(42) still produces a failed setup report (two reports total, not skipped/passed) — the runner must not crash through the custom repr on setup failures.

**Uncertainties.**

- How the custom repr failure is avoided (fallback path) is only evidenced by the test passing assumption, not visible here.

<a id="u-d9af8f5ff107"></a>
### `BaseFunctionalTests.test_failure_in_teardown_function`

`def test_failure_in_teardown_function(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L268-L286][f1]

teardown_function raising ValueError(42) after a passing test yields three reports; reports[2] is failed, not skipped/passed, when=='teardown', so the earlier phases still show their own outcomes.

<a id="u-f03186b3a42e"></a>
### `BaseFunctionalTests.test_custom_failure_repr`

`def test_custom_failure_repr(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L288-L311][f1]

Installs a conftest Function subclass whose repr_failure returns 'hello' and runs a failing item; the call report is failed, not skipped or passed, exercising that custom repr failure output flows into the report.

**Uncertainties.**

- The returned 'hello' is not asserted here; only the failed/skipped/passed flags are checked.

<a id="u-caa7ae654c7b"></a>
### `BaseFunctionalTests.test_exact_teardown_issue90`

> **ID corrected by CBE.** CBE changed the unit ID from ` testing/test_runner.py::method::BaseFunctionalTests.test_exact_teardown_issue90 ` to the inventory ID ` testing/test_runner.py::method::BaseFunctionalTests.test_exact_teardown_issue90::10919 `. The model wrote this body under the wrong ID; it may be inaccurate.

`def test_exact_teardown_issue90(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L341-L379][f1]

Regression for issue 90: teardown_class and teardown_function both raising must not leak exc_info into subsequent test runs.

Six reports expected: test_method setup/call passed, its class-teardown report failed, then test_func setup/call passed, its function teardown failed — proving the later test ran with sys.exc_info() == (None, None, None).

<a id="u-1c1e3d412353"></a>
### `BaseFunctionalTests.test_exact_teardown_issue1206`

> **ID corrected by CBE.** CBE changed the unit ID from ` testing/test_runner.py::method::BaseFunctionalTests.test_exact_teardown_issue1206 ` to the inventory ID ` testing/test_runner.py::method::BaseFunctionalTests.test_exact_teardown_issue1206::12372 `. The model wrote this body under the wrong ID; it may be inaccurate.

`def test_exact_teardown_issue1206(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L381-L417][f1]

Regression for issue 1206 (error shadowing): teardown_method declared with three params but called with one must yield three reports — setup passed, call passed, teardown failed — and the teardown longrepr must be an ExceptionChainRepr whose crash message is the plain TypeError text, one of two variants depending on Python >= 3.10 adding the qualified class name.

<a id="u-1b782098b940"></a>
### `BaseFunctionalTests.test_teardown_final_returncode`

`def test_teardown_final_returncode(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L313-L322][f1]

Inline run of a passing test with a teardown_function raising ValueError(42) must produce overall exit code 1.

<a id="u-784764fe1a3b"></a>
### `BaseFunctionalTests.test_logstart_logfinish_hooks`

`def test_logstart_logfinish_hooks(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L324-L339][f1]

Inline run of a passing test; collects pytest_runtest_logstart and pytest_runtest_logfinish hook calls, asserting exactly those two hook names fire, in that order, with the expected nodeid and location tuple (file, 1, test_func).

<a id="u-1d2bc6863cbd"></a>
### `BaseFunctionalTests.test_systemexit_does_not_bail_out`

`def test_systemexit_does_not_bail_out(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L449-L461][f1]

A test function raising SystemExit(42) must be caught by the runner, not propagated: runitem returns normally, and the call report is failed with when=='call'.

<a id="u-f395a375f1ec"></a>
### `BaseFunctionalTests.test_exit_propagates`

`def test_exit_propagates(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L463-L475][f1]

Unlike SystemExit, a pytest.exit.Exception raised inside a test item propagates out of runitem; the test asserts it is raised and fails the suite otherwise.

<a id="u-9ef8c1898873"></a>
### `TestExecutionNonForked`

`class TestExecutionNonForked(BaseFunctionalTests):` · [testing/test_runner.py:L478-L479][f1]

Runs items with the in-process runner: getrunner returns a function executing runner.runtestprotocol(item, log=False); inherits all BaseFunctionalTests scenarios under that runner.

<a id="u-baa96dfb4727"></a>
### `TestExecutionNonForked.test_keyboardinterrupt_propagates`

`def test_keyboardinterrupt_propagates(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L485-L496][f1]

A test function raising KeyboardInterrupt('fake') must escape runitem as KeyboardInterrupt; if the runner swallowed it the test asserts failure with 'did not raise'.

<a id="u-e8f8ee482d08"></a>
### `test_runtest_in_module_ordering`

`def test_runtest_in_module_ordering(pytester: Pytester) -> None:` · [testing/test_runner.py:L569-L599][f1]

Marked xfail: checks ordering of module-level vs class-level pytest_runtest_setup plus a class-level call wrapper swallowing ValueError, expecting both tests to pass.

Intentionally expected to fail, so current behavior is not asserted as correct.

**Uncertainties.**

- Which assertion currently fails is not determined by the source.

<a id="u-e4776be27128"></a>
### `test_failure_in_setup`

`def test_failure_in_setup(pytester: Pytester) -> None:` · [testing/test_runner.py:L953-L963][f1]

A setup_module raising 0/0 with --tb=line must not print the source line 'def setup_module' in the output.

<a id="u-74491d1bf591"></a>
### `test_teardown_session_failed`

`def test_teardown_session_failed(pytester: Pytester) -> None:` · [testing/test_runner.py:L1219-L1241][f1]

Regression for #11706: with --maxfail=1 aborting the session after the first failing test, the module-scoped fixture's failing teardown still runs in the last item's context, yielding outcomes failed=1 (test) and errors=1 (teardown).

<a id="u-fa60467fce65"></a>
### `test_teardown_session_stopped`

`def test_teardown_session_stopped(pytester: Pytester) -> None:` · [testing/test_runner.py:L1244-L1266][f1]

Same scenario as the --maxfail regression but bailing via --stepwise: the module-scoped fixture teardown failure still surfaces, giving failed=1, errors=1.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_runner.py
