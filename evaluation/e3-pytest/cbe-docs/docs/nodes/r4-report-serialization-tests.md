# Report serialization regressions

**Capability.** TestReportSerialization round-trips: chained exceptions with and without reprcrash, ReprEntry and ReprEntryNative preservation, path-like conversion to strings (MyPathLike), extended attributes, timestamps vs duration, deserialization failure messages, and ConftestImportFailure transparency.

Each test pins a specific serialization regression (xdist issues 130/170/196/241, 5971); use it to see exactly which longrepr structures survive JSON.

Parent: [Report serialization tests](r4-test-reports.md)

## Units (18)

<a id="u-e1159aa49529"></a>
### `TestReportSerialization`

`class TestReportSerialization:` · [testing/test_reports.py:L16-L17][f1]

Groups regression tests that round-trip pytest reports through TestReport._to_json/_from_json and CollectReport._from_json, covering historical xdist serialization bugs, chained exceptions, path-like attributes, deserialization failure handling, and timestamp consistency.

Each member test builds reports inline via pytester and asserts field equality between original and reloaded reports.

<a id="u-4e788d8a656d"></a>
### `TestReportSerialization.test_xdist_longrepr_to_str_issue_241`

`def test_xdist_longrepr_to_str_issue_241(self, pytester: Pytester) -> None:` · [testing/test_reports.py:L17-L38][f1]

Verifies round-trip serialization of longrepr for failed and passing call reports (xdist issue 241).

Runs two tests inline, takes reports[1] (failed call) and reports[4] (passed call); asserts the failed report serializes longrepr.reprtraceback.style as 'long' and the passed report serializes longrepr to JSON null.

group: [TestReportSerialization](r4-report-serialization-tests.md#u-e1159aa49529)

**Uncertainties.**

- Exact expected report count of 6 depends on plugin-provided setup/teardown reports not visible here.

<a id="u-ec877ef78d53"></a>
### `TestReportSerialization.test_xdist_report_longrepr_reprcrash_130`

`def test_xdist_report_longrepr_reprcrash_130(self, pytester: Pytester) -> None:` · [testing/test_reports.py:L40-L77][f1]

Round-trips a failed call report whose longrepr is an ExceptionRepr with an added section, asserting all non-longrepr attributes and reprcrash fields (lineno, message, path), traceback style/entrysep/extraline, and sections survive _to_json/_from_json (xdist issue 130).

<a id="u-e8cb088b6ac4"></a>
### `TestReportSerialization.test_reprentries_serialization_170`

`def test_reprentries_serialization_170(self, pytester: Pytester) -> None:` · [testing/test_reports.py:L79-L122][f1]

Runs a failing test with --showlocals so the traceback contains ReprEntry objects, round-trips the call report, and asserts each reprentry's lines, reprfileloc (lineno/message/path), reprfuncargs.args, reprlocals.lines, and style are preserved (xdist issue 170).

Explicitly compares entry-list lengths before zipping to substitute for zip(strict=True) on Python < 3.10.

<a id="u-d713828795f2"></a>
### `TestReportSerialization.test_reprentries_serialization_196`

`def test_reprentries_serialization_196(self, pytester: Pytester) -> None:` · [testing/test_reports.py:L124-L152][f1]

Same round-trip check but with --tb=native so reprentries are ReprEntryNative; asserts entry counts match and each entry's lines survive serialization (xdist issue 196).

<a id="u-035ebafc6cda"></a>
### `TestReportSerialization.test_itemreport_outcomes`

`def test_itemreport_outcomes(self, pytester: Pytester) -> None: # This test came orig…` · [testing/test_reports.py:L154-L186][f1]

Round-trips all 17 reports from a session covering pass, fail, skipif-skip, imperative skip, xfail mark, and imperative xfail, asserting passed/failed/skipped flags, outcome, when, and keywords match.

For skipped reports without wasxfail it additionally asserts longrepr deserializes to a 3-tuple; for failed reports it asserts longreprtext equality.

<a id="u-1534a11400e6"></a>
### `TestReportSerialization.test_collectreport_passed`

`def test_collectreport_passed(self, pytester: Pytester) -> None:` · [testing/test_reports.py:L188-L197][f1]

Round-trips each collect report from a clean run and asserts passed/failed/skipped flags are preserved via CollectReport._from_json.

<a id="u-7362deadda88"></a>
### `TestReportSerialization.test_collectreport_fail`

`def test_collectreport_fail(self, pytester: Pytester) -> None:` · [testing/test_reports.py:L199-L211][f1]

Runs a syntactically invalid module ('qwe abc') so collection fails, round-trips every collect report, asserts outcome flags match and, when the report failed, that the deserialized longrepr equals str of the original longrepr.

<a id="u-452824c90b14"></a>
### `TestReportSerialization.test_extended_report_deserialization`

`def test_extended_report_deserialization(self, pytester: Pytester) -> None:` · [testing/test_reports.py:L213-L227][f1]

Sets an undeclared extra attribute on each collect report before serializing, then asserts the extra attribute survives CollectReport._from_json along with outcome flags and failed longrepr string equality, demonstrating extensibility of the serialized payload.

<a id="u-957f5e6f32c8"></a>
### `TestReportSerialization.test_paths_support`

`def test_paths_support(self, pytester: Pytester) -> None:` · [testing/test_reports.py:L229-L238][f1]

Verifies path-like report attributes become plain strings in the JSON payload.

Attaches a __fspath__-providing object and a pathlib Path to the failed call report as path1/path2 and asserts _to_json serializes both to str(pytester.path).

uses: [MyPathLike](r4-report-serialization-tests.md#u-92fb6fda1395)

<a id="u-92fb6fda1395"></a>
### `MyPathLike`

`class MyPathLike:` · [testing/test_reports.py:L238-L239][f1]

Minimal path-like helper storing a string and returning it from __fspath__, used to confirm that os.PathLike report attributes are converted to strings during serialization.

<a id="u-83835ed3f146"></a>
### `TestReportSerialization.test_deserialization_failure`

`def test_deserialization_failure(self, pytester: Pytester) -> None:` · [testing/test_reports.py:L255-L275][f1]

Checks the failure path when a serialized reprentry has an unrecognized type: it mutates the JSON entry's 'type' from 'ReprEntry' to 'Unknown' and asserts TestReport._from_json raises RuntimeError matching 'INTERNALERROR: Unknown entry type returned: Unknown'.

**Notes.**

- failure: Deserialization of an unknown reprentry type raises RuntimeError rather than skipping or guessing.

<a id="u-bd17e839db59"></a>
### `TestReportSerialization.test_chained_exceptions`

`def test_chained_exceptions( self, pytester: Pytester, tw_mock, report_class ) -> None:` · [testing/test_reports.py:L277-L312][f1]

Test setup phase: creates a test file where test_a raises ValueError inside foo and re-raises RuntimeError from it, conditionally calling test_a at module level when report_class is CollectReport so collection itself fails; then runs inline and selects the call report (TestReport) or the file collect report (CollectReport) for the round-trip checks.

group: [testing/test_reports.py:TestReportSerialization.test_chained_exceptions](r4-report-serialization-tests.md#u-9b01867645b5); calls: [TestReportSerialization.test_chained_exceptions](r4-report-serialization-tests.md#u-bd17e839db59)

<a id="u-9b01867645b5"></a>
### `testing/test_reports.py:TestReportSerialization.test_chained_exceptions`

`def test_chained_exceptions( self, pytester: Pytester, tw_mock, report_class ) -> None:` · [testing/test_reports.py:L332-L349][f1]

Assertion phase of the chained-exception round-trip: asserts the report failed with no sections, adds a section to its ExceptionChainRepr, round-trips via _to_json/_from_json, re-checks the chain via check_longrepr (two entries with ValueError and RuntimeError, direct-cause description on entry1, None on entry2), and finally calls toterminal on a mocked writer to ensure no blow-up.

<a id="u-352cbefab698"></a>
### `TestReportSerialization.test_chained_exceptions_no_reprcrash`

`def test_chained_exceptions_no_reprcrash(self, pytester: Pytester, tw_mock) -> None:` · [testing/test_reports.py:L351-L376][f1]

Test setup phase for issue 5971: writes a test using ProcessPoolExecutor whose worker exception becomes a RemoteTraceback without a ReprFileLocation, inserts syspath, runs inline, and fetches the runtest reports.

group: [testing/test_reports.py:TestReportSerialization.test_chained_exceptions_no_reprcrash](r4-report-serialization-tests.md#u-e1045bcc143b)

<a id="u-e1045bcc143b"></a>
### `testing/test_reports.py:TestReportSerialization.test_chained_exceptions_no_reprcrash`

`def test_chained_exceptions_no_reprcrash(self, pytester: Pytester, tw_mock) -> None:` · [testing/test_reports.py:L388-L406][f1]

Assertion phase: takes the call report, checks its ExceptionChainRepr has two chain entries with 'RemoteTraceback' and 'ValueError: value error' tracebacks, entry1's fileloc is None while entry2's message is 'ValueError: value error', then round-trips and calls toterminal on a mock writer to ensure the missing reprcrash does not break reconstruction or rendering.

<a id="u-5f84163a6bca"></a>
### `TestReportSerialization.test_report_prevent_ConftestImportFailure_hiding_exception`

`def test_report_prevent_ConftestImportFailure_hiding_exception( self, pytester: Pytes…` · [testing/test_reports.py:L408-L417][f1]

Creates a namespaced conftest importing an unknown module, runs pytest in a subprocess, and asserts the output shows the underlying ModuleNotFoundError ('E   *Error: No module named unknown') while asserting ConftestImportFailure text does not appear, i.e. the real error is not hidden by the wrapper type.

group: [TestReportSerialization](r4-report-serialization-tests.md#u-e1159aa49529)

<a id="u-174792e88ae6"></a>
### `TestReportSerialization.test_report_timestamps_match_duration`

`def test_report_timestamps_match_duration(self, pytester: Pytester, mock_timing):` · [testing/test_reports.py:L419-L437][f1]

Uses mock_timing with a fixture sleeping 5s before and after yield and a test sleeping 10s, round-trips each of the three reports, and asserts loaded_report.stop - loaded_report.start approx-equals the original report.duration, showing start/stop serialize consistently with duration.

**Uncertainties.**

- Behavior depends on the mock_timing fixture's semantics, which are not in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_reports.py
