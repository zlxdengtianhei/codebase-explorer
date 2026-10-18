# Thread & Unraisable Exception Warning Tests

**Capability.** Tests that unhandled thread exceptions and garbage-collected/unraisable exceptions surface as PytestUnhandledThreadExceptionWarning / PytestUnraisableExceptionWarning, in default, error-filter, setup/teardown, aggregation, and broken-reporting scenarios.

Use this subtree when touching the thread-exception or unraisable hook machinery. The tests vary gc state, warning filters, and object lifetimes, asserting exit codes, ExceptionGroup aggregation, and warning summaries.

**Depends on.**

- [Warning Capture Hooks](r3-warning-capture.md) · model-inferred · 0 edge(s)

Parent: [Pytest Framework Codebase](r3-pytest.md)

## Units (17)

<a id="u-8f3990b07331"></a>
### `test_threadexception.py module code (L1–L6)`

`module_region` · [testing/test_threadexception.py:L1-L6][f1]

Imports Pytester and pytest for the thread-exception warning tests.

<a id="u-acdbca478156"></a>
### `test_unhandled_thread_exception`

`def test_unhandled_thread_exception(pytester: Pytester) -> None:` · [testing/test_threadexception.py:L7-L38][f1]

With filterwarnings default for PytestUnhandledThreadExceptionWarning, a test joining a thread that raises ValueError still passes (2 passed, 1 warning) and the warnings summary names the thread 'MyThread' with the ValueError traceback and the warnings.warn call site.

<a id="u-ec39c62cc132"></a>
### `test_unhandled_thread_exception_in_setup`

`def test_unhandled_thread_exception_in_setup(pytester: Pytester) -> None:` · [testing/test_threadexception.py:L41-L74][f1]

Same warning behavior when the failing thread is started inside a fixture during setup: session exits 0 with 2 passed and 1 warning attributed to test_it.

<a id="u-eba761b5e8c0"></a>
### `test_unhandled_thread_exception_in_teardown`

> **ID corrected by CBE.** CBE changed the unit ID from ` testing/test_threadexception.py::function::test_unhandled_thread_exception_in_teardown::1089 ` to the inventory ID ` testing/test_threadexception.py::function::test_unhandled_thread_exception_in_teardown::2181 `. The model wrote this body under the wrong ID; it may be inaccurate.

`def test_unhandled_thread_exception_in_teardown(pytester: Pytester) -> None:` · [testing/test_threadexception.py:L77-L111][f1]

Same warning behavior when the failing thread is started after yield in fixture teardown: exit 0, 2 passed, 1 warning attributed to test_it.

<a id="u-0ea6c2169545"></a>
### `test_unhandled_thread_exception_after_teardown`

`def test_unhandled_thread_exception_after_teardown(pytester: Pytester) -> None:` · [testing/test_threadexception.py:L195-L220][f1]

Registers a thread-joining cleanup via config.add_cleanup; under -Werror, a thread exception after teardown cannot attach to any test and becomes an INTERNAL_ERROR exit with 1 passed and the ValueError traceback on stderr.

The test's TODO notes this should ideally be a test failure/error.

**Notes.**

- failure: Thread exceptions surfacing after teardown currently produce an internal error rather than a test failure.

<a id="u-8108ab136538"></a>
### `test_unhandled_thread_exception_warning_error`

`def test_unhandled_thread_exception_warning_error(pytester: Pytester) -> None:` · [testing/test_threadexception.py:L114-L133][f1]

With the warning filtered as error, the unhandled thread exception turns the owning test into a failure: exit TESTS_FAILED with 1 passed and 1 failed, and no separate warning summary assertion.

<a id="u-3ec29dba6cdc"></a>
### `test_threadexception_warning_multiple_errors`

`def test_threadexception_warning_multiple_errors(pytester: Pytester) -> None:` · [testing/test_threadexception.py:L136-L162][f1]

With the warning as error and two failing threads joined in one test, the two warnings are aggregated into an ExceptionGroup: exit TESTS_FAILED, 1 passed/1 failed, output shows 'ExceptionGroup: multiple thread exception warnings (2 sub-exceptions)'.

<a id="u-fda020718a93"></a>
### `test_possibly_none_excinfo`

`def test_possibly_none_excinfo(pytester: Pytester) -> None:` · [testing/test_threadexception.py:L223-L255][f1]

With the warning as error, a test invokes threading.excepthook directly with a SimpleNamespace whose exc_value and traceback are None; the warning is still emitted ('Exception in thread <unknown>', 'NoneType: None') and fails the test, verifying None excinfo fields are tolerated.

<a id="u-320132f68256"></a>
### `test_unraisable_collection_failure`

`def test_unraisable_collection_failure(pytester: Pytester) -> None:` · [testing/test_threadexception.py:L165-L192][f1]

When a Thread subclass raises from its name property while pytest processes the thread exception, reporting itself fails: exit 1, 1 passed/1 failed, and output contains 'RuntimeError: Failed to process thread exception'.

<a id="u-53d3a5e57021"></a>
### `test_unraisableexception.py-unraisable-default`

`def test_unraisable(pytester: Pytester) -> None:` · [testing/test_unraisableexception.py:L32-L63][f2]

Three tests verify that a ValueError raised in __del__ of a BrokenDel object is reported as a PytestUnraisableExceptionWarning when the warning filter is 'default', whether the object is dropped in the test body, in fixture setup, or in fixture teardown (yield then drop).

In each case the nested run exits 0 with passed=2, warnings=1, and the warnings summary contains the test node id, the PytestUnraisableExceptionWarning line for BrokenDel.__del__ (wording differs on Python >= 3.14), the traceback 'ValueError: del is broken', tracemalloc hint lines (pre-3.14 only), and the warnings.warn call site. All are skipped on PyPy because garbage-collection differences make them flaky.

<a id="u-d8f4fe6be9ec"></a>
### `test_unraisableexception.py-refcycle-gc-disabled`

`def test_refcycle_unraisable(pytester: Pytester) -> None: # see: https://github.com/p…` · [testing/test_unraisableexception.py:L230-L258][f2]

Reference-cycle unraisables with gc disabled in the child run.

A self-referencing BrokenDel whose __del__ raises is collected even with gc.disable() at import time. test_refcycle_unraisable runs with -Wdefault: exit 0, passed=1, and 'ValueError: del is broken' appears on stderr (the warning can only reach stdout/stderr after the terminal reporter finished). With -Werror (test_refcycle_unraisable_warning_filter) and with -Werror in the asyncio create_task reproducer (test_create_task_raises_unraisable_warning_filter), the exception propagates to the top and the exit code is 1 despite passed=1 — both tests carry TODO comments that a test failure or error would be the proper outcome. The default-filter variant mirrors this using -Wdefault and asserts ExitCode.OK.

<a id="u-d52edef7e141"></a>
### `test_unraisableexception.py-collection-failure`

`def test_unraisable_collection_failure(pytester: Pytester) -> None:` · [testing/test_unraisableexception.py:L193-L209][f2]

Verifies error handling inside the unraisable-warning machinery itself.

mock.patch makes traceback.format_exception raise a custom BaseException subclass MyError while the plugin formats the unraisable exception; the nested run then exits 1 with passed=1, failed=1 and the output shows 'RuntimeError: Failed to process unraisable exception', so a failure during formatting is converted to that RuntimeError instead of crashing differently. On PyPy the test calls gc.collect() to force the __del__ to run. MyError subclasses BaseException specifically so it is not a plain Exception.

<a id="u-0557f3fbee83"></a>
### `_set_gc_state`

`def _set_gc_state(enabled: bool) -> bool:` · [testing/test_unraisableexception.py:L221-L227][f2]

Enables or disables the garbage collector per the enabled argument and returns whether gc was enabled before the change, letting a test save and restore gc state around unraisable-hook scenarios.

<a id="u-e970f2be3650"></a>
### `test_unraisable_warning_error`

`def test_unraisable_warning_error(pytester: Pytester) -> None:` · [testing/test_unraisableexception.py:L143-L161][f2]

With filterwarnings 'error::pytest.PytestUnraisableExceptionWarning', a broken __del__ turns the unraisable exception into a test failure: the run exits TESTS_FAILED with passed=1, failed=1.

On PyPy the generated test explicitly calls gc.collect() to force collection (conditional text interpolated via PYPY).

<a id="u-2a4e8b76680a"></a>
### `test_unraisable_warning_multiple_errors`

`def test_unraisable_warning_multiple_errors(pytester: Pytester) -> None:` · [testing/test_unraisableexception.py:L164-L190][f2]

With the unraisable warning escalated to error, two BrokenDel objects whose __del__ raise distinct messages produce a single failure aggregating both: ret is TESTS_FAILED with passed=1, failed=1, and the output contains an ExceptionGroup line 'multiple unraisable exception warnings (2 sub-exceptions)', so multiple unraisables in one run are grouped.

<a id="u-94c96e802828"></a>
### `testing/test_unraisableexception.py:test_possibly_none_excinfo`

`def test_possibly_none_excinfo(pytester: Pytester) -> None:` · [testing/test_unraisableexception.py:L362-L395][f2]

Calls sys.unraisablehook directly with a SimpleNamespace whose exc_value, exc_traceback, err_msg and object are all None, under an error filter for the unraisable warning.

The run fails (TESTS_FAILED, failed=1) and the output shows the warning formatted with 'Exception ignored in: None' and a 'NoneType: None' traceback, proving the plugin tolerates a None exc_value; a TODO notes the outcome should ideally be failure or error via a different path.

<a id="u-9f8859a8b755"></a>
### `test_create_task_raises_unraisable_warning_filter`

`def test_create_task_raises_unraisable_warning_filter(pytester: Pytester) -> None: # …` · [testing/test_unraisableexception.py:L293-L323][f2]

Issue reproducer (#10404): calling asyncio.create_task outside a running loop raises RuntimeError and leaves a never-awaited coroutine, producing a RuntimeWarning unraisable under -Werror in a subprocess run.

Exit code is 1 with passed=1 and 'RuntimeWarning: coroutine 'my_task' was never awaited' on stderr; a TODO notes the exit code should ideally be a test failure. The host pytest warning filter is disabled and the pytester filter applies during config teardown of unraisablehook.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_threadexception.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/test_unraisableexception.py
