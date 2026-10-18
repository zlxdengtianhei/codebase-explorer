# Collection Error Handling

**Capability.** Tests behavior when collection fails: exit codes and interruption with/without --continue-on-collection-errors and --maxfail, traceback-style filtering of collection errors, system exceptions, yield-in-test rejection, invalid signatures, and crash-resistance regressions.

Use it to pin expected exit codes, banners and summaries for broken modules. Several tests assert internal-error resistance rather than success.

**Depends on.**

- [Test Run Invocation](r6-pytester-run.md) · graph-confirmed · 13 edge(s)

Parent: [Collection Suite](r6-test-collection.md)

## Units (11)

<a id="u-586d9f364512"></a>
### `TestPrunetraceback`

`class TestPrunetraceback:` · [testing/test_collection.py:L296-L297][f1]

Traceback formatting of collection errors.

test_custom_repr_failure installs a conftest whose custom File raises MyError from collect and overrides repr_failure to return 'hello world' for MyError (delegating to pytest.File.repr_failure otherwise); output must show the ERROR collecting header and the custom message. test_collect_report_postprocessing is marked xfail: a wrapper hook appending rep.headerlines in pytest_make_collect_report is expected to appear in output but currently does not. test_collection_error_traceback_is_clean raises Exception('LOUSY') at module top level and asserts a consecutive, clean one-frame user traceback ending in the short test summary, with no internal pytest stack entries.

<a id="u-e2fc549e99ea"></a>
### `test_exit_on_collection_error`

`def test_exit_on_collection_error(pytester: Pytester) -> None:` · [testing/test_collection.py:L1037-L1052][f1]

With the shared COLLECTION_ERROR_PY_FILES set (1 failure, 2 import errors, 1 success), a default run exits with code 2 and reports 'collected 2 items / 2 errors' with ERROR collecting lines for both import-error modules.

<a id="u-b75d77bbbf88"></a>
### `test_exit_on_collection_with_maxfail_bigger_than_n_errors`

`def test_exit_on_collection_with_maxfail_bigger_than_n_errors( pytester: Pytester, ) …` · [testing/test_collection.py:L1078-L1099][f1]

With --maxfail=4 exceeding the 2 collection errors, the run still aborts with exit code 2, both import errors reported, and an 'Interrupted: 2 errors during collection' summary, showing collection errors abort even when maxfail is not reached.

<a id="u-6c53e538d7aa"></a>
### `test_exit_on_collection_with_maxfail_smaller_than_n_errors`

`def test_exit_on_collection_with_maxfail_smaller_than_n_errors( pytester: Pytester, )…` · [testing/test_collection.py:L1055-L1075][f1]

With --maxfail=1, collection aborts at the first import error: exit code 1, 'collected 1 item / 1 error', a '!

stopping after 1 failures !' banner, and test_03 must not appear, showing later modules are never collected.

<a id="u-1a6daebd202b"></a>
### `test_continue_on_collection_errors`

`def test_continue_on_collection_errors(pytester: Pytester) -> None:` · [testing/test_collection.py:L1102-L1114][f1]

With --continue-on-collection-errors, the 2 collected tests still run despite the 2 collection errors; exit code 1 and a '1 failed, 1 passed, 2 errors' summary.

<a id="u-38b2964b8c46"></a>
### `test_continue_on_collection_errors_maxfail`

`def test_continue_on_collection_errors_maxfail(pytester: Pytester) -> None:` · [testing/test_collection.py:L1117-L1130][f1]

With --continue-on-collection-errors and --maxfail=3, collection errors count toward maxfail, so after 2 errors plus 1 failure the run interrupts before test_4; exit code 1 with 'collected 2 items / 2 errors' and '1 failed, 2 errors'.

<a id="u-fd707420e8bc"></a>
### `test_collector_respects_tbstyle`

`def test_collector_respects_tbstyle(pytester: Pytester) -> None:` · [testing/test_collection.py:L1551-L1565][f1]

A module that asserts 0 at import time fails collection; with --tb=native the collection error report shows a real Python traceback (file, line, 'assert 0', AssertionError) followed by 'Interrupted: 1 error during collection', exit code INTERRUPTED.

<a id="u-ce5005c42f72"></a>
### `test_does_not_crash_on_error_from_decorated_function`

`def test_does_not_crash_on_error_from_decorated_function(pytester: Pytester) -> None:` · [testing/test_collection.py:L1729-L1740][f1]

A module containing only a fixture whose body returns 4 (wrong for a fixture, yielding a collection/setup error) must not crash pytest with an internal error due to assertion-rewriting lineno mangling (#4984); the run ends with exit code INTERRUPTED.

<a id="u-0a12bc56292b"></a>
### `test_yield_disallowed_in_tests`

`def test_yield_disallowed_in_tests(pytester: Pytester):` · [testing/test_collection.py:L1883-L1897][f1]

A test function containing 'yield' fails collection (#12960): exit code 2 with the message "'yield' keyword is allowed in fixtures, but not in tests (test_with_yield)" and 'collected 0 items'.

<a id="u-6204adedfdcb"></a>
### `test_collect_invalid_signature_message`

`def test_collect_invalid_signature_message(pytester: Pytester) -> None:` · [testing/test_collection.py:L1244-L1261][f1]

A fixture defined on a class without a self parameter has an indeterminable signature; the run must report 'Could not determine arguments of *.fix *: invalid method signature' (#4026).

<a id="u-56550c56e028"></a>
### `test_respect_system_exceptions`

`def test_respect_system_exceptions( pytester: Pytester, exception_class: type[BaseExc…` · [testing/test_collection.py:L1853-L1880][f1]

Parametrized over KeyboardInterrupt and SystemExit: three modules print 'Before exception', raise the system exception, and would print 'After exception'.

A subprocess run with -s shows the head output and the expected message ('!!! KeyboardInterrupt !!!' or 'INTERNALERROR> SystemExit') but never the tail output, proving collection stops at the system exception instead of swallowing it.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_collection.py
