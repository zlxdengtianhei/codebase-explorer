# unittest integration tests

**Capability.** Behavioral coverage of the unittest bridge: basic collection and per-test instances, setUp/tearDown and class-cleanup semantics, skip/xfail/expected-failure handling, excinfo translation, trial (Twisted) integration, async support, and regressions for garbage collection and collection errors.

Use this to see the end-user-visible contract of running unittest suites under pytest, including trial-specific and cleanup-related edge cases.

**Depends on.**

- [unittest integration bridge](r5-unittest-bridge.md) · model-inferred · 0 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-only · 71 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 70 edge(s)

Parent: [pytest's own test suites](r5-test-suites.md)

## Units (38)

<a id="u-b861e062464c"></a>
### `test_unittest.py module code (L1–L11)`

`module_region` · [testing/test_unittest.py:L1-L11][f1]

File header of the unittest-integration test module: it imports sys, ExitCode, MonkeyPatch, Pytester, and pytest, and enables untyped defs for mypy.

Contains no behavior; the imports support the Pytester-based integration tests below.

<a id="u-1e7fd43d84e9"></a>
### `test_simple_unittest`

`def test_simple_unittest(pytester: Pytester) -> None:` · [testing/test_unittest.py:L12-L25][f1]

Verifies pytest collects and runs a standard unittest.TestCase with one passing and one failing test.

It writes a sample file via makepyfile, runs it with inline_run, and asserts the matched reports have the expected passed/failed outcomes; any deviation in collection or outcome reporting fails the assertion.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d), [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

<a id="u-8e72e8355627"></a>
### `test_runTest_method`

`def test_runTest_method(pytester: Pytester) -> None:` · [testing/test_unittest.py:L28-L49][f1]

Checks that a TestCase defining only runTest is collected as the single item MyTestCaseWithRunTest::runTest, while a class defining both runTest and test_something only yields test_something (runTest is skipped when named test methods exist).

Uses runpytest -v and matches verbose output lines including '2 passed'.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-8814b83126f5"></a>
### `test_isclasscheck_issue53`

`def test_isclasscheck_issue53(pytester: Pytester) -> None:` · [testing/test_unittest.py:L52-L63][f1]

Regression test for issue 53: a module-level instance of a class whose __getattr__ swallows all attribute access must not be mistaken for a test class.

Writes the module, runs pytest, and asserts collection finishes with NO_TESTS_COLLECTED instead of crashing or miscollecting.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-d2115e79e029"></a>
### `test_setup`

`def test_setup(pytester: Pytester) -> None:` · [testing/test_unittest.py:L66-L86][f1]

Confirms both unittest setUp and pytest-style setup_method run before the test and can set instance attributes used by the test body.

Runs with -s so teardown is captured, then inspects reports: the call report must pass, and the teardown report (from teardown_method raising assert 0 with message '42') must fail with '42' in longrepr.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-09f07aed77e4"></a>
### `test_function_item_obj_is_instance`

`def test_function_item_obj_is_instance(pytester: Pytester) -> None:` · [testing/test_unittest.py:L147-L167][f1]

Guarantees item.obj on a TestCaseFunction is a bound method of the TestCase instance (#5390).

A conftest hook pytest_runtest_makereport, during the call phase, reads item.parent.obj as the class and asserts item.obj.__self__ is an instance of it; the sample TestCase test must then pass (stdout '1 passed'). A non-bound obj would make the assertion fail inside the hook.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-c96829c16a21"></a>
### `test_new_instances`

`def test_new_instances(pytester: Pytester) -> None:` · [testing/test_unittest.py:L132-L144][f1]

Asserts each unittest test method runs on a fresh TestCase instance: test_func1 sets self.x = 2 and test_func2 asserts 'x' is absent.

Both tests must pass (assertoutcome(passed=2)); a shared instance would make test_func2 fail.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-cdde94c8e814"></a>
### `test_teardown`

`def test_teardown(pytester: Pytester) -> None:` · [testing/test_unittest.py:L170-L189][f1]

Shows tearDown runs after each test method on per-test instances: MyTestCase.tearDown appends None to a shared class list, and a second TestCase asserts the list is [None].

Counted outcomes must be exactly 2 passed and nothing else, so any error in setUp/teardown counting fails.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-6c370fb7790c"></a>
### `test_teardown_issue1649`

`def test_teardown_issue1649(pytester: Pytester) -> None:` · [testing/test_unittest.py:L192-L223][f1]

Regression test for #1649/#12367: after a passing test, the TestCase instance (and attributes it set, like the expensive object) should be garbage collected, because pytest drops references to passing TestCase objects.

The sample's second test runs gc.collect(), scans gc.get_objects() for a surviving instance, and asserts it no longer holds an_expensive_obj (or that no instance survives at all). The whole run must exit with ExitCode.OK; a leaked reference keeps the attribute reachable and fails the inner assertion.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- Guaranteed collection depends on GC behavior not proven here; the inner test's else-branch 'Could not find' also counts as pass.

<a id="u-0ce67ed5b024"></a>
### `test_unittest_skip_issue148`

`def test_unittest_skip_issue148(pytester: Pytester) -> None:` · [testing/test_unittest.py:L226-L244][f1]

When a whole TestCase is decorated @unittest.skip, pytest must skip the class without ever invoking setUpClass or tearDownClass (which would raise NameError on 'xxx').

Exactly one skipped outcome is expected.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-e0ebeb488ea9"></a>
### `test_method_and_teardown_failing_reporting`

`def test_method_and_teardown_failing_reporting(pytester: Pytester) -> None:` · [testing/test_unittest.py:L247-L268][f1]

When both the test method and tearDown fail, pytest reports them separately: runpytest -s must return exit code 1 and stdout must show both the tearDown failure ('assert 0') and the test_method failure ('assert False') summarized as '1 failed, 1 error'.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-525822ced29a"></a>
### `test_setup_failure_is_shown`

`def test_setup_failure_is_shown(pytester: Pytester) -> None:` · [testing/test_unittest.py:L271-L287][f1]

If setUp fails, the test body never executes: the run fails with setUp's 'assert 0 down1' shown, and stdout must NOT contain the body's print 'never42'.

Exit code must be 1.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-cbc3820fe126"></a>
### `test_unittest.py-setupmodule`

`def test_setUpModule(pytester: Pytester) -> None:` · [testing/test_unittest.py:L89-L108][f1]

Two tests of module-level unittest fixtures.

test_setUpModule writes a module where setUpModule appends to a list and tearDownModule removes the element; both tests observe values == [1], proving setUpModule runs once before the tests and tearDownModule afterwards (matched via '2 passed' on stdout). test_setUpModule_failing_no_teardown makes setUpModule raise ZeroDivisionError; it asserts zero passed and one failed outcome and, via the captured pytest_runtest_setup call, that the module values list is empty — i.e. tearDownModule is not invoked when setUpModule failed.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-73312c20da75"></a>
### `test_unittest.py-setupclass-behavior`

`def test_setup_setUpClass(pytester: Pytester) -> None:` · [testing/test_unittest.py:L290-L312][f1]

Five tests of class-scoped setup/teardown handling for unittest and plain classes.

test_setup_setUpClass and test_setup_class each verify that setUpClass (or plain setup_class) increments a class attribute once before the two test methods, teardown restores it to 0, and a module-level test confirms the class is torn down — 3 passed. test_fixtures_setup_setUpClass_issue8394 checks --fixtures output for a TestCase with setUpClass/tearDownClass: without -v the placeholder must not say 'no docstring available', with -v it must. test_non_unittest_no_setupclass_support proves setUpClass/tearDownClass on a plain (non-unittest) class are ignored — self.x stays 0, 2 passed. test_no_teardown_if_setupclass_failed proves tearDownClass is skipped after a failing setUpClass: the class attribute remains 1 (one error, one passed outcome).

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-1e97666cac6c"></a>
### `test_unittest.py-excinfo-handling`

`def test_testcase_adderrorandfailure_defers(pytester: Pytester, type: str) -> None:` · [testing/test_unittest.py:L362-L382][f1]

Three tests of how TestCaseFunction converts unittest-style result errors into pytest reports.

test_testcase_adderrorandfailure_defers (parametrized over addError/addFailure) calls result.add{type} with a real pytest _excinfo inside the overridden run; the call must not raise (any non-KeyboardInterrupt exception triggers pytest.fail('add{type} should not raise'), and stdout must not show that message) — recording is deferred, not immediate. test_testcase_custom_exception_info monkeypatches _pytest._code.ExceptionInfo with an incompatible fake whose constructor raises TypeError; the resulting report must still render as 'NOTE: Incompatible Exception Representation' containing the original ZeroDivisionError, with 1 failed, and the monkeypatch is undone in a finally. test_testcase_totally_incompatible_exception_info collects the item directly and calls item.addError(None, 42); the stored _excinfo repr must contain 'ERROR: Unknown Incompatible'.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-36a1b7239b1d"></a>
### `test_unittest.py-traceback-quality`

`def test_unittest_not_shown_in_traceback(pytester: Pytester) -> None:` · [testing/test_unittest.py:L734-L745][f1]

Three tests guarding collection and traceback output quality.

test_unittest_not_shown_in_traceback asserts the legacy unittest name 'failUnlessEqual' does not appear in the failure output of an assertEqual(3, 4). test_unorderable_types writes classes with reassigned __name__ (historically causing TypeError during sorting/collection); pytest must not print 'TypeError' and must exit NO_TESTS_COLLECTED. test_unittest_typerror_traceback writes a test method requiring an extra argument, which must fail with 'TypeError' in stdout and exit code 1.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-d5df6424567e"></a>
### `test_unittest.py-expected-failure`

`def test_unittest_expected_failure_for_failing_test_is_xfail( pytester: Pytester, run…` · [testing/test_unittest.py:L782-L805][f1]

Parametrized over runner='pytest'|'unittest', both tests use a TestCase with @unittest.expectedFailure.

test_unittest_expected_failure_for_failing_test_is_xfail: a failing expected-failure test is XFAIL under pytest ('1 xfailed', exit 0) and 'OK (expected failures=1)' under the stdlib runner. test_unittest_expected_failure_for_passing_test_is_fail: a passing expected-failure test is a failure under pytest ('Unexpected success', '1 failed', exit 1) and 'unexpected successes=1' under unittest (exit 1).

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-0b7fb721e7c4"></a>
### `test_unittest_setup_interaction`

`def test_unittest_setup_interaction(pytester: Pytester, stmt: str) -> None:` · [testing/test_unittest.py:L841-L869][f1]

Parametrized over stmt in ('return', 'yield'), verifying pytest fixtures work on unittest classes regardless of whether the fixture body returns or is a generator.

A class-scoped autouse fixture sets request.cls.hello and a function-scoped one sets request.instance.funcname; three test methods assert those attributes, including that the class attribute is shared. All 3 tests must pass in both parametrizations.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-dc190f589585"></a>
### `test_djangolike_testcase`

`def test_djangolike_testcase(pytester: Pytester) -> None: # contributed from Morten B…` · [testing/test_unittest.py:L676-L731][f1]

Checks pytest honors a TestCase subclass that overrides __call__ to run custom _pre_setup/_post_teardown around the normal unittest call.

Exceptions in those hooks are reported via result.addError (KeyboardInterrupt/SystemExit re-raised, other Exceptions recorded and returning early). Running with -s must exit 0 and stdout must show the ordered prints _pre_setup, setUp, test_thing, tearDown, _post_teardown.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-2b4e74a571d7"></a>
### `TestTrialUnittest`

`class TestTrialUnittest:` · [testing/test_unittest.py:L462-L463][f1]

Groups integration tests for twisted.trial unittest support; setup_class skips the whole class when twisted.trial.unittest is not importable (pytest.importorskip) and stores an ignore-unclosed-socket warning flag tuple used on Windows (twisted reactor socket leak, ticket 9227).

The folded method tests: test_trial_testcase_runtest_not_collected asserts a trial TestCase with test_hello yields 1 passed and one defining only runTest also yields 1 passed (via two inline_runs). test_trial_testcase_skip_property / test_trial_testfunction_skip_property check that a trial class-level or function-level skip attribute causes 1 skipped. test_trial_testcase_todo_property / test_trial_testfunction_todo_property check that trial 'todo' attributes (class or per-function) turn failing tests into skipped outcomes. test_trial_pdb spawns pytest in a pty (spawn_pytest), expects the failure message 'hellopdb' and sends EOF, exercising pdb on a failing trial test.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

**Uncertainties.**

- Property/todo behavior requires twisted to be installed; the class is skipped otherwise.

<a id="u-e3d8aebe6528"></a>
### `TestTrialUnittest.test_trial_exceptions_with_skips`

`def test_trial_exceptions_with_skips(self, pytester: Pytester) -> None:` · [testing/test_unittest.py:L493-L541][f1]

Exercises mixed skip/xfail markers plus trial-specific skip/todo attributes on trial TestCases.

It writes a module using pytest.skip, skipif, xfail marker, pytest.xfail, trial .skip and .todo attributes, and a class whose setup_class skips. runpytest -rxs (plus the socket-warning flag) must print XFAIL/todo/skip reasons (matched with fnmatch_lines_random) and end with '1 failed 4 skipped 3 xfailed' and exit code 1 — the failed item is test_trial_todo_success which has a todo but passes... actually the failed one is the todo-marked test that also asserts 0 is counted per trial semantics; the test only asserts the aggregate line.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- Exact mapping of which trial item is '1 failed' is not derivable from this test alone; only the aggregate outcome string is asserted.

<a id="u-98c21747f428"></a>
### `TestTrialUnittest.test_trial_error`

`def test_trial_error(self, pytester: Pytester) -> None:` · [testing/test_unittest.py:L543-L605][f1]

Verifies trial deferred/reactor errors surface as pytest failures and teardown errors.

The sample has four tests: test_one crashes directly; test_two returns a Deferred whose callback crashes; test_three schedules a reactor call and crashes at teardown; test_four both crashes and has a failing teardown. With -vv and classic console output, stdout must list each test as FAILED, test_four additionally as ERROR, a ERRORS section with 'ERROR at teardown of TC.test_four', DelayedCalls summaries for the reactor-based tests, NameError tracebacks for each crash, and a final '4 failed, 1 error'.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-8fa5ce0b55e6"></a>
### `test_module_level_pytestmark`

`def test_module_level_pytestmark(pytester: Pytester) -> None:` · [testing/test_unittest.py:L447-L459][f1]

A module-level pytestmark = pytest.mark.xfail must apply to unittest.TestCase tests in that module: the failing test_func1 is reported as skipped (xfail non-strict), asserted via assertoutcome(skipped=1) on an inline_run with -s.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-be189ab5237a"></a>
### `test_cleanup_functions`

`def test_cleanup_functions(pytester: Pytester) -> None:` · [testing/test_unittest.py:L926-L954][f1]

Ensures functions registered with self.addCleanup run after each test ends, even when the test fails (#6947).

test_func_1 and the failing test_func_2 each register a cleanup appending their name; a third test asserts the list equals ['test_func_1', 'test_func_2']. Expected verbose outcomes: PASSED, FAILED, PASSED.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-c03d6c603bfb"></a>
### `test_unittest.py-skip-detection`

`def test_unittest_raise_skip_issue748(pytester: Pytester) -> None:` · [testing/test_unittest.py:L980-L996][f1]

Three small skip/collection tests.

test_unittest_raise_skip_issue748 shows raising unittest.SkipTest inside a test yields 'SKIP [1] ... skipping due to reasons' with -rs and '1 skipped'. test_unittest_skip_issue1169 shows the @unittest.skip decorator on a method likewise reports the reason and '1 skipped' (the failing body never runs). test_class_method_containing_test_issue1558 shows a method flagged __test__ = False is not collected, so only the other method runs (1 passed).

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-6b791aa5ea4f"></a>
### `test_issue333_result_clearing`

`def test_issue333_result_clearing(pytester: Pytester) -> None:` · [testing/test_unittest.py:L957-L977][f1]

Regression for #333: a conftest wrapper hook around pytest_runtest_call raises assert 0 after the call phase; even though the test itself also fails (0/0), the recorded outcome must be exactly one failed — i.e. result clearing from the aborted wrapper does not lose or duplicate the unittest failure.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-bb5bcc45e18b"></a>
### `test_usefixtures_marker_on_unittest`

`def test_usefixtures_marker_on_unittest(base, pytester: Pytester) -> None:` · [testing/test_unittest.py:L1036-L1094][f1]

Verifies @pytest.mark.usefixtures works on unittest.TestCase methods (#3498), parametrized over the base class ('builtins.object' vs 'unittest.TestCase', module skipped if absent).

The conftest defines function-scoped fixtures that monkeypatch fixture1/fixture2 onto request.instance, an autouse fixture printing node marks, and a collection hook printing marks. test_one requests only fixture1 (asserts fixture1 set, fixture2 not); test_two requests both. Both must pass, proving usefixtures injection and per-instance attribute setting.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-799d8723ab01"></a>
### `test_testcase_handles_init_exceptions`

`def test_testcase_handles_init_exceptions(pytester: Pytester) -> None:` · [testing/test_unittest.py:L1097-L1115][f1]

A TestCase whose __init__ always raises must surface that exception in the output ('should raise this exception' in stdout) without producing a spurious 'ERROR at teardown of MyTestCase.test_hello' entry — i.e. collection/creation failures are not misattributed to teardown (#3788).

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-660fb2c62c46"></a>
### `test_unittest.py-copy-example-errors`

`def test_error_message_with_parametrized_fixtures(pytester: Pytester) -> None:` · [testing/test_unittest.py:L1118-L1127][f1]

Two tests using pytester.copy_example against example files not present in this source.

test_error_message_with_parametrized_fixtures runs an example where a plain method named test_two collides with fixture parameterization; stdout must contain 'test_two does not support fixtures', the item id 'TestSomethingElse::test_two', and 'Function type: TestCaseFunction'. test_setup_inheritance_skipping (parametrized over example name and expected outcome) checks skipping inherited setUp/tearDown/setUpModule (#4700): test_setup_skip.py and test_setup_skip_class.py produce '1 skipped', test_setup_skip_module.py produces '1 error'.

calls: [Pytester.copy_example](r6-pytester-core.md#u-c15c0894e320)

**Uncertainties.**

- Behavior of the example files is external; only the matched output lines are documented here.

<a id="u-4505223d5fc3"></a>
### `test_unittest.py-exit-outcomes`

`def test_BdbQuit(pytester: Pytester) -> None:` · [testing/test_unittest.py:L1147-L1162][f1]

Control-flow exit handling inside unittest tests.

test_BdbQuit: raising bdb.BdbQuit in one test stops the debugger path without aborting the session — outcomes are 1 failed (the BdbQuit test) and 1 passed (the next test still runs). test_exit_outcome: calling pytest.exit inside a test ends the session immediately; stdout shows 'Exit: pytest_exit called' and the summary 'no tests ran in', and the second test does not run.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-dfa186079bc2"></a>
### `test_unittest.py-trace`

`def test_trace(pytester: Pytester, monkeypatch: MonkeyPatch) -> None:` · [testing/test_unittest.py:L1183-L1186][f1]

All fragment ids of one test.

test_trace verifies --trace on a unittest test invokes the debugger via pytestPDB._init_pdb with exactly the args ('runcall',): the local check_call monkeypatches _init_pdb, records each call, asserts args == ('runcall',), and returns a fake _pdb object whose runcall also records. After runpytest --trace, the calls list must contain exactly two entries (the _init_pdb call and the fake runcall) and the run must exit 0. The nested class _pdb and its runcall method exist only to record; the duplicated inventory fragments (s0/s1 of check_call and test_trace) are parts of these two functions.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- The split s0/s1 fragments reflect how the inventory segmented the nested functions; their combined behavior is described here.

<a id="u-4ec8edad106a"></a>
### `test_unittest.py-pdb-teardown`

`def test_pdb_teardown_called(pytester: Pytester, monkeypatch: MonkeyPatch) -> None:` · [testing/test_unittest.py:L1212-L1244][f1]

Three tests of tearDown behavior under --pdb.

test_pdb_teardown_called (#memory-leak guard): with --pdb, tearDown calls are delayed but must still happen for both tests; the test monkeypatches a shared list onto pytest, the sample tearDown appends self.id(), and after runpytest_inprocess('--pdb') (2 passed) the list must equal the two test ids in order. test_pdb_teardown_skipped_for_functions and test_pdb_teardown_skipped_for_classes (parametrized over @unittest.skip and @pytest.mark.skip) verify that setUp and tearDown are never invoked for a test skipped by decorator on the method or on the whole class (#7215, #10060): after the skipped run, the tracked list must be empty and the summary must read '1 skipped'.

calls: [src/_pytest/monkeypatch.py:MonkeyPatch.setattr (2)](r6-monkeypatch-engine.md#u-7e3e8acd6062), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-52d1ee36fc1d"></a>
### `test_unittest.py-async-support`

`def test_async_support(pytester: Pytester) -> None:` · [testing/test_unittest.py:L1317-L1322][f1]

Async unittest integration.

test_async_support (skips without unittest.async_case) and test_asynctest_support (skips without the asynctest package) each copy an example file and inline-run it, expecting 2 passed and 1 failed — async-aware TestCase coroutines run and the deliberately failing one is reported. test_plain_unittest_does_not_support_async guards against accidentally supporting coroutines in plain TestCase: a subprocess run of the example must print '1 passed'; on CPython it must also print 'RuntimeWarning: coroutine ... was never awaited', while on PyPy that warning is unreliable (garbage-collection dependent) and only the passed line is required.

calls: [Pytester.copy_example](r6-pytester-core.md#u-c15c0894e320)

**Uncertainties.**

- The exact pass/fail split comes from example files outside this source.
- The PyPy branch depends on hasattr(sys, 'pypy_version_info').

<a id="u-3c039d877724"></a>
### `test_unittest.py-cleanups`

`def test_do_class_cleanups_on_success(pytester: Pytester) -> None:` · [testing/test_unittest.py:L1357-L1379][f1]

Six tests verifying addCleanup/addClassCleanup run under all setup/teardown outcomes, using a shared class values list and a module-level checker test.

Class cleanups: registered in setUpClass, they run exactly once on success (values == [1], 3 passed), once even when setUpClass fails after registration (values == [1]; 1 failed outcome for the tests plus the checker passing), and once when tearDownClass fails (values == [1]; 3 passed outcomes counted, the tearDownClass error not counted as failed here). Instance cleanups registered in setUp: on success each test's cleanup runs, giving [1, 1] with 3 passed; when setUp fails after addCleanup the cleanups still run for both failing tests ([1, 1]; 2 failed, checker passed); when tearDown fails after addCleanup the cleanups still run ([1, 1]; 2 failed, 1 passed).

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-c19a25e9a329"></a>
### `TestClassCleanupErrors`

`class TestClassCleanupErrors:` · [testing/test_unittest.py:L1508-L1516][f1]

Verifies exceptions raised in class-level cleanup functions (addClassCleanup) are shown to the user (#11728).

test_class_cleanups_failure_in_setup: setUpClass registers two failing cleanups (LIFO order: fail 2 then fail 1) and then itself raises 'fail 0'; the run has 0 passed, 1 error, stdout shows 'Unittest class cleanup errors ... 2 sub-exceptions' listing both cleanup exceptions, plus 'ERROR at setup of MyTestCase.test' with 'Exception: fail 0'. test_class_cleanups_failure_in_teardown: cleanups registered in a passing setUpClass both fail; the test passes but there is 1 error, with the same grouped two-sub-exception report. test_class_cleanup_1_failure_in_teardown: a single failing cleanup yields 'ERROR at teardown of MyTestCase.test' with 'Exception: fail 1' and 1 error alongside 1 passed.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-b8dc1cedc65a"></a>
### `test_traceback_pruning`

`def test_traceback_pruning(pytester: Pytester) -> None:` · [testing/test_unittest.py:L1597-L1620][f1]

Regression for #9610: a TestCase subclass whose __init__ takes the test method argument must not crash pytest's traceback pruning when tearDownClass fails.

Outcomes must be exactly 1 passed and 1 failed (the tearDownClass error) with reprec.ret == 1.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-6216b26db57a"></a>
### `test_raising_unittest_skiptest_during_collection`

`def test_raising_unittest_skiptest_during_collection( pytester: Pytester, ) -> None:` · [testing/test_unittest.py:L1623-L1647][f1]

A module that raises unittest.SkipTest at import time after defining one TestCase must skip the whole module: unittest reports one fake skipped test for the module (skipped == 1, passed 0, failed 0, including the class defined before the raise and the one after), and pytest exits with NO_TESTS_COLLECTED.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-f3827ae4161a"></a>
### `test_abstract_testcase_is_not_collected`

`def test_abstract_testcase_is_not_collected(pytester: Pytester) -> None:` · [testing/test_unittest.py:L1650-L1675][f1]

Regression for #12275: TestCase subclasses that remain abstract (missing abstractmethod implementations) must not be collected.

Of TestBase (abstract), TestPartial (still abstract), and TestConcrete (fully implemented), only TestConcrete's test_it runs: ExitCode.OK with exactly 1 passed outcome.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_unittest.py
