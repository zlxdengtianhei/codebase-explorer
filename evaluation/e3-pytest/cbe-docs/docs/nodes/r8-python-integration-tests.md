# Python Feature Integration Tests

**Capability.** testing/python/integration.py verifies pytest's integration with Python idioms: mock-decorated tests (patch detection, ordering, sentinel identity), nose-style __test__ collection attribute, parametrize behavior, .instance on Function items, session-scoped pytestconfig, __wrapped__-aware getfslineno, and rerun protocols with fixture re-instantiation.

Read this when changing collection of decorated classes/functions or the Function item lifecycle. Tests run through pytester inline runs and getitems.

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Units (10)

<a id="u-80c9b6aec34d"></a>
### `integration.py-testmockdecoration`

`class TestMockDecoration:` · [testing/python/integration.py:L29-L30][f1]

Integration tests for pytest's handling of mock-decorated tests.

test_wrapped_getfuncargnames builds a wrapper setting func.__wrapped__ and asserts getfuncargnames recovers the original ('x',). test_getfuncargnames_patching applies @patch.object(T, 'original') to a standalone f(x, y, z) and asserts getfuncargnames drops the patched-out first argument, yielding ('y', 'z'). test_unittest_mock, test_unittest_mock_and_fixture, and test_unittest_mock_and_pypi_mock write modules where unittest.mock (and the pypi mock package, guarded by pytest.importorskip('mock','1.0.1') in the latter) patch targets and inject mock arguments, then assert inline_run outcomes of passed=1, passed=1, and passed=2 respectively. test_mock_double_patch_issue473 verifies class-level stacked @patch decorators with @mark.slow pass once. Each test writes source with pytester.makepyfile and runs pytester.inline_run; failures surface as outcome-count assertion errors or collection failures.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

**Uncertainties.**

- Whether pytest.importorskip skips or fails the run depends on the runtime presence of the pypi 'mock' package, not determinable from this file.

<a id="u-976aa454004e"></a>
### `integration.py-testnoseliketestattribute`

`class TestNoselikeTestAttribute:` · [testing/python/integration.py:L274-L275][f1]

Tests the nose-style __test__ attribute controlling collection.

test_module_with_global_test sets module-level __test__ = False and asserts no collections failed and no reports were produced. test_class_and_method sets a function's __test__ to False and a class's to False, again asserting no failures and no reports. test_unittest_class confirms unittest classes collect normally (one item, cls named 'TC') while a unittest class with __test__ = False is excluded, checked via pytest_collection_modifyitems. test_class_with_nasty_getattr defines a metaclass whose __getattr__ returns a lambda; collection must not interpret attribute access as __test__ = True, and the test asserts zero collected items. All use pytester.makepyfile plus inline_run.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-1ae9dd686dcd"></a>
### `integration.py-testparameterize`

`class TestParameterize:` · [testing/python/integration.py:L358-L361][f1]

Parametrize integration tests.

test_idfn_marker and test_idfn_fixture both use an idfn returning 'spam' for 0, 'ham' for 1, None otherwise; applied via the parametrize marker and via fixture params respectively, and both assert --collect-only output contains 'spam-2' and 'ham-2', showing idfn-derived ids for the first parameter combined with the second parameter value. test_param_rejects_usefixtures parametrizes with pytest.param(..., marks=[usefixtures('foo')]) and asserts the collect-only output contains an error referencing the source line and 'pytest.param(', i.e. usefixtures is rejected inside pytest.param. All write modules with makepyfile and run pytester.runpytest('--collect-only').

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-d1cc5291be2f"></a>
### `test_function_instance`

`def test_function_instance(pytester: Pytester) -> None:` · [testing/python/integration.py:L428-L465][f1]

Collects items via pytester.getitems and checks the .instance attribute of Function items.

Of four collected items, the module-level test_func has instance None; the class methods test_method, test_class (classmethod) and test_static (staticmethod) each have a non-None instance of class TestIt, and the three instances are pairwise distinct objects — class and static methods get their own instance, the one used for bound fixture methods.

calls: [pytester-collection-helpers](r6-pytester-run.md#u-0183c0c437e7)

<a id="u-5fe7ce131146"></a>
### `test_pytestconfig_is_session_scoped`

`def test_pytestconfig_is_session_scoped() -> None:` · [testing/python/integration.py:L266-L271][f1]

Asserts the built-in pytestconfig fixture is session-scoped: imports pytestconfig from _pytest.fixtures, extracts its fixture marker via getfixturemarker (asserting the marker is not None first), and asserts marker.scope == 'session'.

<a id="u-c6705784de65"></a>
### `test_wrapped_getfslineno`

`def test_wrapped_getfslineno() -> None:` · [testing/python/integration.py:L11-L12][f1]

Asserts getfslineno unwraps functions carrying __wrapped__ back to their true source line.

The nested wrap attaches __wrapped__ and a patchings attribute to func and decorates wrapped_func, mimicking mock-decorated functions. It compares the line number of wrapped_func against wrap itself; the assertion fails with 'getfslineno does not unwrap correctly' if the wrapped function resolves to the wrapper's earlier line.

imports: [integration.py module code (L1–L10)][f1]

<a id="u-f4f91eada3f9"></a>
### `TestMockDecoration.test_mock`

`def test_mock(self, pytester: Pytester) -> None:` · [testing/python/integration.py:L150-L181][f1]

End-to-end check of pypi mock integration (skipped via pytest.importorskip('mock','1.0.1') when absent).

The written module patches os.path.abspath on an unittest method and stacks three patches on a plain function, one supplying a custom new callable; it verifies injected mock arguments and the custom basename replacement. After asserting passed=2, it reads pytest_runtest_logreport calls and asserts the call-phase report location names equal ['T.test_hello', 'test_something'], confirming decorated functions keep correct identities.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-297e059afd6a"></a>
### `TestMockDecoration.test_mock_sentinel_check_against_numpy_like`

`def test_mock_sentinel_check_against_numpy_like(self, pytester: Pytester) -> None:` · [testing/python/integration.py:L122-L148][f1]

Regression test that mock-argument detection compares patch targets against sentinels by identity, so targets whose __eq__ raises (numpy-like objects) can still be patched.

It writes a dummy module defining NumpyLike whose __eq__ raises ValueError plus FOO=NumpyLike(10), then a test patching dummy.FOO with NumpyLike(50) and asserting value==50. Asserts inline_run reports passed=1; an equality-based sentinel check would raise inside the run and break the outcome.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-307ce9181004"></a>
### `TestMockDecoration.test_mock_sorting`

`def test_mock_sorting(self, pytester: Pytester) -> None:` · [testing/python/integration.py:L183-L205][f1]

Asserts mock-patched test functions run in source declaration order.

Three @mock.patch-decorated tests are run inline (after importorskip of the mock package); call-phase reports are filtered, nodeid last components extracted, and asserted to equal ['test_one','test_two','test_three'] exactly.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-eb027ab23beb"></a>
### `TestReRunTests.test_rerun`

`def test_rerun(self, pytester: Pytester) -> None:` · [testing/python/integration.py:L227-L263][f1]

Verifies a conftest pytest_runtest_protocol hook that calls runtestprotocol twice (log=False then log=True) re-runs each test, with function-scoped fixtures freshly instantiated per run.

The fixture asserts each request object differs from the previous global and prints an incrementing count. Running with -s, it matches 'fix count 0' then 'fix count 1' and a '2 passed' summary in stdout; an equal-request assertion inside the fixture or mismatched output fails the test.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/python/integration.py
