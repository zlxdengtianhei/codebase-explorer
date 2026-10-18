# Stepwise fixtures and helpers

**Capability.** Fixture builders for the stepwise suites (stepwise_pytester with --fail/--fail-last conftest, error_pytester, broken_pytester), the _strip_resource_warnings output filter, and module imports.

All behavioral tests consume these fixtures; the filter keeps stderr assertions stable against GC-timing ResourceWarnings.

**Depended on by.**

- [Stepwise behavior tests](r4-stepwise-behavior-tests.md) · graph-confirmed · 6 edge(s)

Parent: [Stepwise tests](r4-test-stepwise.md)

## Units (5)

<a id="u-14ca3953c2cc"></a>
### `test_stepwise.py module code (L1–L14)`

`module_region` · [testing/test_stepwise.py:L1-L14][f1]

Imports for the stepwise tests, including Cache, MonkeyPatch, STEPWISE_CACHE_DIR, json, and Path.

<a id="u-ccb0c5c16c65"></a>
### `stepwise_pytester`

`def stepwise_pytester(pytester: Pytester) -> Pytester: # Rather than having to modify…` · [testing/test_stepwise.py:L15-L63][f1]

Fixture that builds a reusable two-file suite: a conftest adding --fail and --fail-last flags, test_a.py with five tests whose middle tests fail only under those flags, test_b.py with one passing test, and an ini setting cache_dir to .cache to avoid a flaky shared cache; returns the pytester.

uses: [test_run_without_stepwise](r4-stepwise-behavior-tests.md#u-3d63c1b6e292)

<a id="u-a4014b237292"></a>
### `error_pytester`

`def error_pytester(pytester: Pytester) -> Pytester:` · [testing/test_stepwise.py:L66-L78][f1]

Fixture creating test_a.py where the first test errors on a non-existing fixture and a second test would pass after it; used to test stepwise behavior on collection/setup errors.

<a id="u-c52122b2cba3"></a>
### `broken_pytester`

`def broken_pytester(pytester: Pytester) -> Pytester:` · [testing/test_stepwise.py:L81-L86][f1]

Fixture creating one valid test file and one unparseable file ('foobar'), for collection-error tests.

<a id="u-b1132eef1f5a"></a>
### `testing/test_stepwise.py:_strip_resource_warnings`

`def _strip_resource_warnings(lines: Sequence[str]) -> Sequence[str]: # Strip unreliab…` · [testing/test_stepwise.py:L89-L96][f1]

Filters out lines starting with 'Exception ignored in:' or 'ResourceWarning' from captured output so stderr emptiness assertions remain reliable despite GC-timing-dependent resource warnings (issue 5088).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_stepwise.py
