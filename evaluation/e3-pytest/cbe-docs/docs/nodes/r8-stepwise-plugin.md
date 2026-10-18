# Stepwise Run Resumption

**Capability.** src/_pytest/stepwise.py implements --stepwise/--stepwise-skip/--stepwise-reset: a StepwisePlugin that persists the last failing nodeid (StepwiseCacheInfo) in the cache, reorders collection to resume from it, and tracks failures during the run.

Read this to understand fail-first resume behavior and cache invalidation via last_test_count. pytest_configure only registers the plugin when stepwise is enabled.

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Units (9)

<a id="u-7a5564869417"></a>
### `StepwiseCacheInfo`

`class StepwiseCacheInfo: # The nodeid of the last failed test.` · [src/_pytest/stepwise.py:L70-L83][f1]

Dataclass describing the persisted stepwise state: `last_failed` nodeid, `last_test_count` used to invalidate stale caches, and a string timestamp that is informational.

`last_cache_date` parses the timestamp with datetime.fromisoformat (raises ValueError on malformed strings); `empty()` builds an all-None state stamped with the current time; `update_date_to_now` rewrites the timestamp.

**Uncertainties.**

- last_cache_date will raise ValueError if the cached string is not ISO-formatted; _load_cached_info does not catch that around the property call, only around construction.

<a id="u-612a2e636aeb"></a>
### `StepwisePlugin`

`class StepwisePlugin:` · [src/_pytest/stepwise.py:L99-L100][f1]

Implements --stepwise: resume the run from the last failing test.

`__init__` stores config/cache, reads the skip and reset flags, and loads cached state via _load_cached_info. `pytest_sessionstart` records the session so failures can stop it. `pytest_report_collectionfinish` returns the collected status lines as 'stepwise: ...' entries at verbosity >= 0, else None. `pytest_sessionfinish` skips persistence in xdist workers (workerinput attribute) to avoid races (#10641); otherwise it stamps the cache date to now and writes the dataclass as a dict under `cache/stepwise`. The collection and logreport hooks have their own units.

calls: [StepwisePlugin._load_cached_info](r8-stepwise-plugin.md#u-4de1635b76f1); uses: [StepwiseCacheInfo](r8-stepwise-plugin.md#u-7a5564869417)

<a id="u-fba1974f1c4c"></a>
### `src/_pytest/stepwise.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/stepwise.py:L23-L50][f1]

Registers --sw/--stepwise, --sw-skip/--stepwise-skip, and --sw-reset/--stepwise-reset (all store_true).

Skip and reset each independently imply stepwise at configure time; their help text documents that implication.

<a id="u-e6be8e85cc4a"></a>
### `src/_pytest/stepwise.py:pytest_configure`

`def pytest_configure(config: Config) -> None: # --stepwise-skip/--stepwise-reset impl…` · [src/_pytest/stepwise.py:L53-L58][f1]

Turns on stepwise when stepwise_skip or stepwise_reset was given, then registers StepwisePlugin as 'stepwiseplugin' only when the stepwise option is on; otherwise the plugin never loads.

uses: [StepwisePlugin](r8-stepwise-plugin.md#u-612a2e636aeb)

<a id="u-b977bffd3d8c"></a>
### `src/_pytest/stepwise.py:pytest_sessionfinish`

`def pytest_sessionfinish(session: Session) -> None:` · [src/_pytest/stepwise.py:L61-L67][f1]

As written, this module-level hook only early-returns for xdist workers (workerinput attribute) when stepwise is disabled and otherwise performs no action — no cache is written or cleared in the visible body.

This looks like an incomplete/no-op implementation; actual stepwise persistence happens in StepwisePlugin.pytest_sessionfinish.

**Uncertainties.**

- The body contains no statement after the early return, so the hook has no observable effect; whether a non-worker branch was intended is not determinable from the source.

<a id="u-4de1635b76f1"></a>
### `StepwisePlugin._load_cached_info`

`def _load_cached_info(self) -> StepwiseCacheInfo:` · [src/_pytest/stepwise.py:L110-L124][f1]

Loads StepwiseCacheInfo from `cache/stepwise`.

Missing or falsy cached data yields `empty()`. Present data is reconstructed by key; KeyError or TypeError during reconstruction records 'error reading cache, discarding (<type>: <msg>)' in report_status and falls back to `empty()`, so corrupt caches never abort a run.

uses: [StepwiseCacheInfo](r8-stepwise-plugin.md#u-7a5564869417)

<a id="u-ce03598b7046"></a>
### `StepwisePlugin.pytest_collection_modifyitems`

`def pytest_collection_modifyitems( self, config: Config, items: list[nodes.Item] ) ->…` · [src/_pytest/stepwise.py:L129-L172][f1]

Updates last_test_count to the current collection size, then decides whether to skip ahead.

With reset active it clears last_failed and reports 'resetting state'. With no cached last_failed it reports 'no previously failed tests, not skipping'. If the previously recorded test count differs from the current count it invalidates the cache (clears last_failed) and reports the change — this is the staleness guard. Otherwise it scans items for the nodeid matching last_failed: not found means no skipping; found means all preceding items are deselected via pytest_deselected and removed from `items`, with a status reporting how many were skipped, the cache age rounded to whole seconds, and a pointer to --sw-reset.

<a id="u-11497a086c8b"></a>
### `StepwisePlugin.pytest_runtest_logreport`

`def pytest_runtest_logreport(self, report: TestReport) -> None:` · [src/_pytest/stepwise.py:L174-L196][f1]

Tracks failures during the run.

On a failed report: if the skip flag is set, it clears last_failed when the failed nodeid is the cached one and turns the flag off so only the first failure is ignored; otherwise it records the failing nodeid as the new last_failed and sets session.shouldstop ('Test failed, continuing from this test next run.'), ending the run there. On non-failed reports in the call phase, a nodeid matching the cached last_failed is cleared, advancing the stepwise pointer.

**Uncertainties.**

- session must have been set by pytest_sessionstart; the assert would fail if a report arrived first.

<a id="u-6ce97d0282ff"></a>
### `stepwise.py module code (L1–L22)`

`module_region` · [src/_pytest/stepwise.py:L1-L22][f1]

Module imports and the stepwise cache key constant.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/stepwise.py
