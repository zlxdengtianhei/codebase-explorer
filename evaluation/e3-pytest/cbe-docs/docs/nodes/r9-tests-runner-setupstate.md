# SetupState Tests

**Capability.** Unit tests of ss.setup, finalizer registration and teardown_exact: stack semantics, empty-stack tolerance, cached setup failures, and finalizer error grouping/ordering across single and multiple scopes.

Read this to understand the exact teardown contract, including ExceptionGroup ordering (readability-reversed) and single-failure unwrapping across scopes.

**Depends on.**

- [Session SetupState](r9-runner-setupstate.md) · model-inferred · 0 edge(s)

Parent: [Runner Test Suite](r9-tests-runner.md)

## Units (10)

<a id="u-8bf7f1ab68c6"></a>
### `TestSetupState`

`class TestSetupState:` · [testing/test_runner.py:L28-L29][f1]

Holds unit tests for the session SetupState, covering setup, finalizer registration, teardown_exact stack semantics, cached setup failures, and grouped finalizer errors across scopes.

<a id="u-3aa933250e0d"></a>
### `TestSetupState.test_setup`

`def test_setup(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L29-L37][f1]

After ss.setup(item) and adding a finalizer that pops the last of [1], the value survives setup; teardown_exact(None) runs the finalizer so the list ends empty.

<a id="u-e7c8f3d370a1"></a>
### `TestSetupState.test_teardown_exact_stack_empty`

`def test_teardown_exact_stack_empty(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L39-L45][f1]

After setup and one teardown_exact(None), two further teardown_exact(None) calls on the same state must complete without raising, showing the empty-stack case is tolerated.

<a id="u-b5fe5f95c915"></a>
### `TestSetupState.test_setup_fails_and_failure_is_cached`

`def test_setup_fails_and_failure_is_cached(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L47-L59][f1]

A setup_module raising ValueError(42) propagates from ss.setup(item); a second ss.setup for the same item raises ValueError again without re-running setup_module, evidencing cached setup failure.

<a id="u-64472307a47d"></a>
### `TestSetupState.test_cached_exception_doesnt_get_longer`

`def test_cached_exception_doesnt_get_longer(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L143-L178][f1]

Regression for #12204: a Collector whose setup() raises must error all its yielded items with the same cached exception, and each failure traceback must not grow per item.

It installs a MyBadCollector yielding three items with setup doing 1/0, runs with --tb=native, expects TESTS_FAILED, three failures, and equal first-reprentry line counts for failures 1 and 2.

**Uncertainties.**

- Equality is checked only by comparing traceback reprentry line counts, not full text.

<a id="u-5422e83171e6"></a>
### `BaseFunctionalTests`

`class BaseFunctionalTests:` · [testing/test_runner.py:L181-L182][f1]

Base functional suite for running a single item end to end: pass/fail/skip call outcomes, skip or failure in setup, failure in teardown, custom repr_failure, hook and report-shape regressions, and exception propagation rules.

Subclasses supply the actual runner via getrunner.

<a id="u-163e8ab81c1b"></a>
### `test-runner-test_teardown_multiple_fail`

`def test_teardown_multiple_fail(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L84-L85][f1]

When every registered finalizer raises, teardown_exact(None) raises one ExceptionGroup; its exceptions are ordered fin1 ('oops1') before fin2 ('oops2') even though execution is LIFO, as the in-code comment notes the group order is reversed for user readability.

<a id="u-7b6fcc4320cc"></a>
### `test-runner-test_teardown_multiple_one_fails`

`def test_teardown_multiple_one_fails(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L61-L64][f1]

With three finalizers where only the middle (fin2) raises Exception('oops'), teardown_exact(None) still runs all finalizers LIFO — r ends ['fin3','fin1'] — and the single error propagates as a plain Exception with args ('oops',), not wrapped in a group.

<a id="u-8b47b2ee33d2"></a>
### `test-runner-test_teardown_multiple_scopes_one_fails`

`def test_teardown_multiple_scopes_one_fails(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L105-L108][f1]

A raising function-scope finalizer and an appending module-scope finalizer: teardown_exact(None) raises the function-scope exception (match 'oops1') while the module-scope finalizer still runs, leaving module_teardown == ['fin_module'].

<a id="u-d3b7486cc35c"></a>
### `test-runner-test_teardown_multiple_scopes_several_fail`

`def test_teardown_multiple_scopes_several_fail(self, pytester) -> None:` · [testing/test_runner.py:L124-L125][f1]

Several failures across scopes: module-scope finalizer raises KeyError, function-scope finalizers raise TypeError then ValueError.

teardown_exact(None) raises an ExceptionGroup matching 'errors during test teardown' whose first member is the module KeyError and whose second is a nested group holding TypeError then ValueError.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_runner.py
