# TestCaseFunction item and setup fixtures

**Capability.** The Function item for one unittest method: runtest on a fresh TestCase instance, pdb-aware setup/teardown with deferred tearDown, traceback filtering of unittest internals, and autouse generator fixtures wrapping setUpClass/tearDownClass and setup_method/teardown_method with teardown-exception propagation.

Read this for the lifecycle of a single unittest test inside pytest, including how class- and method-level unittest setup is expressed as pytest fixtures.

**Depends on.**

- [TestCase collection](r5-unittest-collection.md) · graph-confirmed · 4 edge(s)

Parent: [unittest integration bridge](r5-unittest-bridge.md)

## Units (16)

<a id="u-6f70ff8af141"></a>
### `TestCaseFunction`

`class TestCaseFunction(Function):` · [src/_pytest/unittest.py:L203-L207][f1]

Function item representing a single unittest test method; nofuncargs=True like UnitTestCase, and holds _excinfo, a list of collected ExceptionInfos.

It doubles as a unittest result reporter, implementing the result callbacks documented separately, and adapts unittest's execution model to pytest.

<a id="u-c5131017faf6"></a>
### `TestCaseFunction.runtest`

`def runtest(self) -> None:` · [src/_pytest/unittest.py:L322-L353][f1]

Executes the unittest test method.

Obtains the TestCase instance (asserted non-None), applies --trace wrapping via maybe_wrap_pytest_function_for_tracing, and lets unittest handle async functions by passing this item as the result object (testcase(result=self)). For sync tests with --pdb and a non-skipped test or class, it defers tearDown: saves testcase.tearDown into _explicit_tearDown and replaces the attribute with a no-op lambda, so tearDown runs later in teardown() after any pdb session. It then binds the (possibly wrapped) self.obj onto the testcase instance under the test's name, runs testcase(result=self), and removes the temporary attribute in a finally block.

calls: [maybe_wrap_pytest_function_for_tracing](r4-debugging-pdb-plugins.md#u-6b8fccc2e7b6)

**Uncertainties.**

- The skipped check reads __unittest_skip__ on the bound method (self.obj) and the parent class; method-level skip markers on the underlying function rather than the method object may not be detected.

<a id="u-2bd6cf7dd3a2"></a>
### `TestCaseFunction.setup`

`def setup(self) -> None: # A bound method to be called during teardown() if set (see …` · [src/_pytest/unittest.py:L217-L220][f1]

Initializes self._explicit_tearDown to None (set during runtest when --pdb defers tearDown) before delegating to the standard Function.setup.

<a id="u-4cea509ad3a4"></a>
### `TestCaseFunction.teardown`

`def teardown(self) -> None:` · [src/_pytest/unittest.py:L222-L228][f1]

Runs the deferred tearDown captured in _explicit_tearDown when set (then clears it), drops the cached _obj and deletes _instance so the TestCase is released, and delegates to Function.teardown.

**Uncertainties.**

- If _explicit_tearDown itself raises, _obj/_instance cleanup and super().teardown() are skipped since there is no try/finally; the error propagates.

<a id="u-35a4a2e3f20e"></a>
### `TestCaseFunction._getinstance`

`def _getinstance(self):` · [src/_pytest/unittest.py:L207-L209][f1]

Asserts the parent is a UnitTestCase and returns a new instance of its TestCase class constructed via parent.obj(self.name) — i.e. instantiated with this test's method name.

<a id="u-0f93a5570ffa"></a>
### `TestCaseFunction._testcase`

`def _testcase(self):` · [src/_pytest/unittest.py:L213-L215][f1]

Backward-compatibility property for pytest-django that simply returns self.instance.

<a id="u-6e8c47bffffe"></a>
### `TestCaseFunction._traceback_filter`

`def _traceback_filter( self, excinfo: _pytest._code.ExceptionInfo[BaseException] ) ->…` · [src/_pytest/unittest.py:L355-L364][f1]

Filters unittest-internal frames out of tracebacks by removing entries whose frame globals contain a truthy __unittest marker.

If filtering removes everything, the original unfiltered traceback is kept so the failure is not rendered empty.

<a id="u-a046ae5fc136"></a>
### `TestCaseFunction.startTest`

`def startTest(self, testcase: unittest.TestCase) -> None:` · [src/_pytest/unittest.py:L230-L231][f1]

unittest result callback; intentionally does nothing.

<a id="u-82875e00a08d"></a>
### `TestCaseFunction.stopTest`

`def stopTest(self, testcase: unittest.TestCase) -> None:` · [src/_pytest/unittest.py:L316-L317][f1]

unittest result callback; intentionally does nothing.

<a id="u-522f98f2e7b7"></a>
### `TestCaseFunction.addSuccess`

`def addSuccess(self, testcase: unittest.TestCase) -> None:` · [src/_pytest/unittest.py:L313-L314][f1]

unittest success callback; intentionally does nothing.

<a id="u-0d717386eb55"></a>
### `TestCaseFunction.addDuration`

`def addDuration(self, testcase: unittest.TestCase, elapsed: float) -> None:` · [src/_pytest/unittest.py:L319-L320][f1]

unittest duration callback; intentionally does nothing, discarding timing data.

<a id="u-1e547876fb61"></a>
### `UnitTestCase._register_unittest_setup_class_fixture`

`def _register_unittest_setup_class_fixture(self, cls: type) -> None:` · [src/_pytest/unittest.py:L116-L125][f1]

Registers a class-scoped autouse fixture invoking setUpClass/tearDownClass.

Returns early when the class defines neither; otherwise reads doClassCleanups (defaulting to a no-op lambda) and registers a uniquely named fixture (_unittest_setUpClass_fixture_<qualname>) on the fixture manager. The generated fixture body is documented in its own unit, as is its exception-processing helper.

<a id="u-dca10a98b4bf"></a>
### `unittest_setup_class_fixture`

`def unittest_setup_class_fixture( request: FixtureRequest, ) -> Generator[None]:` · [src/_pytest/unittest.py:L139-L161][f1]

Generator fixture wrapping setUpClass/tearDownClass for the request's class.

If the class is skipped, raises pytest.skip.Exception with the class's __unittest_skip_why__ reason and _use_item_location=True so the skip reports at the item. Runs setUpClass if defined; if it raises an ordinary Exception, calls doClassCleanups and process_teardown_exceptions (to surface class-cleanup errors) and re-raises — mirroring unittest, which does not run cleanups for BaseExceptions. After yielding (tests run), runs tearDownClass if defined inside a try/finally that always calls doClassCleanups then process_teardown_exceptions, so class-cleanup errors propagate even if teardown itself failed.

**Uncertainties.**

- A BaseException from setUpClass skips doClassCleanups here, matching unittest, but whether trial/other paths compensate is not shown in this file.

<a id="u-cb3c7f4740f4"></a>
### `process_teardown_exceptions`

`def process_teardown_exceptions() -> None: # tearDown_exceptions is a list set in the…` · [src/_pytest/unittest.py:L125-L137][f1]

Raises errors recorded during class teardown.

Reads cls.tearDown_exceptions (a list of (type, exc, tb) triples); does nothing when absent/empty. With exactly one exception raises it directly for readability; otherwise raises an ExceptionGroup named 'Unittest class cleanup errors' containing all of them.

<a id="u-f3d0ca89095c"></a>
### `UnitTestCase._register_unittest_setup_method_fixture`

`def _register_unittest_setup_method_fixture(self, cls: type) -> None:` · [src/_pytest/unittest.py:L172-L180][f1]

Registers a function-scoped autouse fixture invoking setup_method/teardown_method.

Returns early if the class defines neither; otherwise registers a uniquely named fixture (_unittest_setup_method_fixture_<qualname>) whose generator body is documented in its own unit.

<a id="u-35f055795681"></a>
### `unittest_setup_method_fixture`

`def unittest_setup_method_fixture( request: FixtureRequest, ) -> Generator[None]:` · [src/_pytest/unittest.py:L180-L191][f1]

Generator fixture around setup_method/teardown_method.

Takes the TestCase instance from request.instance; if the instance is skipped, raises pytest.skip.Exception with __unittest_skip_why__ and _use_item_location=True. Calls setup_method(self, request.function) if defined, yields for the test, then calls teardown_method(self, request.function) if defined — no special cleanup handling, unlike the class fixture.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/unittest.py
