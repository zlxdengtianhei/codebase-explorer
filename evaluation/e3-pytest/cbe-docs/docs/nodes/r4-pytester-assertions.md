# Pytester assertion helpers

**Capability.** Shared assertions for pytester-based tests: assertoutcome checks grouped pass/skip/fail counts from reports, assert_outcomes compares a run's outcome stats dict to expected counts.

Import these helpers in test suites that run pytest in-process and need to assert result statistics.

Parent: [Runtime library](r4-runtime-library.md)

## Units (2)

<a id="u-527966c642ef"></a>
### `assertoutcome`

`def assertoutcome( outcomes: tuple[ Sequence[TestReport], Sequence[CollectReport | Te…` · [src/_pytest/pytester_assertions.py:L15-L34][f1]

Asserts that grouped report sequences match expected pass/skip/fail counts.

Unpacks the outcomes tuple into passed/skipped/failed sequences, compares their lengths against the keyword counts (default 0), and on mismatch fails an assert whose message embeds the actual reports. `__tracebackhide__` hides this frame from pytest tracebacks.

uses: [TestReport](r3-report-model.md#u-84690a33cd57), [CollectReport](r3-report-model.md#u-5719d522515d)

<a id="u-3e511961b3f2"></a>
### `assert_outcomes`

`def assert_outcomes( outcomes: dict[str, int], passed: int = 0, skipped: int = 0, fai…` · [src/_pytest/pytester_assertions.py:L37-L74][f1]

Asserts a run's outcome stats dict equals expected counts, for pytester-based tests.

Builds an obtained dict reading the six base outcome keys with default 0 when absent, and an expected dict from the keyword defaults (all 0). `warnings` and `deselected` enter the comparison only when their arguments are not None; a missing key counts as 0. Any inequality raises AssertionError, hidden by `__tracebackhide__`.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/pytester_assertions.py
