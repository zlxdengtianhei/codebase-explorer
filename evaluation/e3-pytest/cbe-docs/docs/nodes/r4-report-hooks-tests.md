# Report hook tests

**Capability.** Verifies pytest_report_to_serializable/pytest_report_from_serializable on config: round-tripping TestReport and CollectReport and rejecting unknown $report_type values with AssertionError.

Read here for the hook-level contract; serialization details are in the sibling node.

Parent: [Report serialization tests](r4-test-reports.md)

## Units (4)

<a id="u-d4c17e7f4646"></a>
### `TestHooks`

`class TestHooks:` · [testing/test_reports.py:L440-L443][f1]

Verifies the pytest_report_to_serializable/pytest_report_from_serializable hooks registered on the config: round-tripping TestReports, CollectReports, and the rejection of unknown $report_type values.

<a id="u-5e51dc9a6adf"></a>
### `TestHooks.test_test_report`

`def test_test_report(self, pytester: Pytester, pytestconfig: Config) -> None:` · [testing/test_reports.py:L443-L463][f1]

Runs two tests (one failing), then for each of the six runtest reports serializes via pytestconfig.hook.pytest_report_to_serializable asserting $report_type is 'TestReport', deserializes via pytest_report_from_serializable, and checks nodeid, when, and outcome match.

group: [TestHooks](r4-report-hooks-tests.md#u-d4c17e7f4646)

<a id="u-96607db76bce"></a>
### `TestHooks.test_collect_report`

`def test_collect_report(self, pytester: Pytester, pytestconfig: Config) -> None:` · [testing/test_reports.py:L465-L485][f1]

Round-trips the three collect reports through the config hooks, asserting $report_type is 'CollectReport' and that nodeid, when ('collect'), and outcome survive.

group: [TestHooks](r4-report-hooks-tests.md#u-d4c17e7f4646)

<a id="u-ee2fe36e1f28"></a>
### `TestHooks.test_invalid_report_types`

`def test_invalid_report_types( self, pytester: Pytester, pytestconfig: Config, hook_n…` · [testing/test_reports.py:L487-L509][f1]

Parametrized over pytest_runtest_logreport and pytest_collectreport: serializes the first report, tampers $report_type to 'Unknown', and asserts pytest_report_from_serializable raises AssertionError, proving the hook rejects unrecognized report type tags.

group: [TestHooks](r4-report-hooks-tests.md#u-d4c17e7f4646)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_reports.py
