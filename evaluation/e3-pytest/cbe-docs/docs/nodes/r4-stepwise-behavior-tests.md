# Stepwise behavior tests

**Capability.** Behavioral assertions: stop-on-failure and resume, skip-option aliases, reset semantics, cache non-clearing when stepwise is disabled or under xdist workers, corrupted-cache recovery, change-of-testfile/test-count handling, collection errors, xfail interaction, and help-text documentation of --sw-skip.

Read here for the exact stepwise cache and messaging contract, including the xdist no-store/no-clear guarantees.

**Depends on.**

- [Stepwise fixtures and helpers](r4-stepwise-fixtures.md) · graph-confirmed · 6 edge(s)

Parent: [Stepwise tests](r4-test-stepwise.md)

## Units (16)

<a id="u-3d63c1b6e292"></a>
### `test_run_without_stepwise`

`def test_run_without_stepwise(stepwise_pytester: Pytester) -> None:` · [testing/test_stepwise.py:L99-L103][f1]

Baseline: without --stepwise, all tests run despite --fail, showing first pass, flag-induced failure, and subsequent pass.

<a id="u-c8230f557a20"></a>
### `test_stepwise_output_summary`

`def test_stepwise_output_summary(pytester: Pytester) -> None:` · [testing/test_stepwise.py:L106-L123][f1]

Checks stepwise user-facing messages with a 5-case parametrized test: first --stepwise run prints 'no previously failed tests, not skipping'; after failing at case 5, a second run prints 'skipping 4 already passed items (cache from * ago, use --sw-reset to discard)' and '1 failed, 4 deselected'.

<a id="u-8e8d53e0f539"></a>
### `test_fail_and_continue_with_stepwise`

`def test_fail_and_continue_with_stepwise(stepwise_pytester: Pytester) -> None: # Run …` · [testing/test_stepwise.py:L126-L147][f1]

With --stepwise --fail, the run stops after the first failing test (asserts the following test never ran, stderr empty after stripping resource warnings).

Re-running without --fail resumes at the previously failed test, which now passes and execution continues past it.

<a id="u-9811b759dafa"></a>
### `test_run_with_skip_option`

`def test_run_with_skip_option(stepwise_pytester: Pytester, stepwise_skip: str) -> None:` · [testing/test_stepwise.py:L150-L167][f1]

Parametrized over '--stepwise-skip' and its alias '--sw-skip': with both failure flags set, the first failing test is skipped past (subsequent test passes) and the run stops at the second failing test, whose successor never runs.

<a id="u-48f47c124aae"></a>
### `test_fail_on_errors`

`def test_fail_on_errors(error_pytester: Pytester) -> None:` · [testing/test_stepwise.py:L170-L177][f1]

With --stepwise and an erroring test (missing fixture), the run stops at the errored test ('test_error ERROR') and the later test never runs.

<a id="u-713db7aa6328"></a>
### `test_change_testfile`

`def test_change_testfile(stepwise_pytester: Pytester) -> None:` · [testing/test_stepwise.py:L180-L197][f1]

Runs --stepwise on test_a.py stopping at the failing test, then runs --stepwise on test_b.py; asserts the second run starts from the beginning ('test_success PASSED') because the cached failing test does not exist in the new file.

<a id="u-9003a8257a34"></a>
### `test_stop_on_collection_errors`

`def test_stop_on_collection_errors( broken_pytester: Pytester, broken_first: bool ) -…` · [testing/test_stepwise.py:L200-L210][f1]

Parametrized broken_first True/False: passes a broken and a working test file to --stepwise in either order and asserts output contains 'error during collection' either way (regression 5444).

<a id="u-b1be7574001c"></a>
### `test_xfail_handling`

`def test_xfail_handling(pytester: Pytester, monkeypatch: MonkeyPatch) -> None:` · [testing/test_stepwise.py:L213-L262][f1]

Ensures stepwise interacts correctly with xfail (issue 5547), running --sw three times against rewritten files: non-strict xfail of test_b runs all four tests fully; strict xfail with a passing body fails and interrupts the session; strict xfail with a failing body is XFAIL and subsequent tests pass with test_a deselected.

monkeypatch sets sys.dont_write_bytecode to avoid bytecode side effects between rewrites.

uses: [test_run_without_stepwise](r4-stepwise-behavior-tests.md#u-3d63c1b6e292)

<a id="u-efe1338d8b64"></a>
### `test_stepwise_skip_is_independent`

`def test_stepwise_skip_is_independent(pytester: Pytester) -> None:` · [testing/test_stepwise.py:L265-L287][f1]

With three failing tests and --stepwise-skip alone (no --stepwise), two tests run and fail, then the session interrupts with 'continuing from this test next run', showing --stepwise-skip implies stepwise behavior independently.

<a id="u-adf1698177e6"></a>
### `test_stepwise_xdist_dont_store_lastfailed`

`def test_stepwise_xdist_dont_store_lastfailed(pytester: Pytester) -> None:` · [testing/test_stepwise.py:L295-L322][f1]

Simulates an xdist worker by setting config.workerinput in a tryfirst pytest_configure hook, runs --stepwise on a failing test expecting INTERRUPTED exit, then asserts the stepwise values cache file (Cache._CACHE_PREFIX_VALUES / STEPWISE_CACHE_DIR) was NOT created, i.e. xdist runs do not persist stepwise state.

**Uncertainties.**

- Relies on Cache._CACHE_PREFIX_VALUES private attribute.

<a id="u-8558e87b430e"></a>
### `test_disabled_stepwise_xdist_dont_clear_cache`

`def test_disabled_stepwise_xdist_dont_clear_cache(pytester: Pytester) -> None:` · [testing/test_stepwise.py:L325-L365][f1]

Pre-creates the stepwise cache file with a nodeid value, then runs pytest without --stepwise but with a fake xdist workerinput conftest and a passing test; asserts exit 0 and that the cache file still exists with exactly its original content, i.e. disabled/non-stepwise xdist runs never clear the cache.

<a id="u-81b8eb3d4a1b"></a>
### `test_do_not_reset_cache_if_disabled`

`def test_do_not_reset_cache_if_disabled(pytester: Pytester) -> None:` · [testing/test_stepwise.py:L368-L409][f1]

Verifies the IDE workflow: a --stepwise run stops at test_2; running a subset with -k without --stepwise passes but must not clear the cache; a subsequent --stepwise run skips the cached passed item and resumes at test_2, printing the cache-age message and '1 failed, 1 deselected'.

<a id="u-9ade5ffa1274"></a>
### `test_reset`

`def test_reset(pytester: Pytester) -> None:` · [testing/test_stepwise.py:L412-L451][f1]

First --stepwise run caches test_1 as passed and stops at test_2; second run skips 1 already passed item and stops at test_2 again; a run with --stepwise-reset prints 'resetting state, not skipping', reruns test_1, and stops at test_2, proving reset discards cached state.

<a id="u-449f445a9f46"></a>
### `test_change_test_count`

`def test_change_test_count(pytester: Pytester) -> None: # Run initially with 3 tests.` · [testing/test_stepwise.py:L454-L512][f1]

With 3 tests, first run stops at test_2 as usual.

Adding test_4 and rerunning prints 'test count changed, not skipping (now 4 tests, previously 3)' and restarts from the beginning. After fixing test_2, the next run skips the 1 cached passed item and runs tests 2-4 with test_1 deselected.

<a id="u-7b2e450e0566"></a>
### `test_cache_error`

`def test_cache_error(pytester: Pytester) -> None:` · [testing/test_stepwise.py:L515-L545][f1]

Generates the stepwise cache normally, then corrupts the cache file at .pytest_cache/v/STEPWISE_CACHE_DIR with JSON {'invalid': True}; the next --stepwise run prints 'error reading cache, discarding (KeyError: *' and behaves as if no cache existed, running the single test and passing.

**Notes.**

- failure: A malformed cache entry surfaces a KeyError that stepwise catches, discards the cache, and reports without failing the session.

<a id="u-38634346ff50"></a>
### `test_sw_skip_help`

`def test_sw_skip_help(pytester: Pytester) -> None:` · [testing/test_stepwise.py:L290-L292][f1]

Checks -h output documents that --sw-skip implicitly enables --stepwise.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_stepwise.py
