# Report and CallInfo Tests

**Capability.** Tests of report objects and CallInfo: from_call result/exception reprs, longreprtext and captured-text accumulation across phases, collect reports, constructor tolerance of extra parameters, and unicode longrepr survival.

Use this to pin the user-level TestReport/CollectReport API, including the #7559 tuple-longrepr rendering contract and captured-output accumulation semantics.

**Depends on.**

- [CallInfo and Collection](r9-runner-callinfo-collect.md) · model-inferred · 0 edge(s)
- [Runtest Protocol](r9-runner-protocol.md) · model-inferred · 0 edge(s)

Parent: [Runner Test Suite](r9-tests-runner.md)

## Units (14)

<a id="u-5cd72a65ec75"></a>
### `test-runner-test_callinfo`

`def test_callinfo() -> None:` · [testing/test_runner.py:L541-L557][f1]

CallInfo.from_call behavior: a successful call stores result and when ('collect'), repr/str equal '<CallInfo when='collect' result: 0>'; a raising call has no result attribute, exposes excinfo, and repr embeds excinfo with newlines escaped (asserting message 'assert_msg' produces no newline in repr).

<a id="u-7d9d076f359c"></a>
### `TestReportContents`

`class TestReportContents:` · [testing/test_runner.py:L1080-L1083][f1]

Tests the user-level API of TestReport/CollectReport objects — longreprtext, captured stdout/stderr, and longrepr type — using a runtestprotocol-based getrunner returning reports without logging.

<a id="u-93c93096149e"></a>
### `TestReportContents.test_longreprtext_pass`

`def test_longreprtext_pass(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L1086-L1094][f1]

For a passing item, the call report's longreprtext is the empty string.

<a id="u-753cfbebd9bb"></a>
### `TestReportContents.test_longreprtext_skip`

`def test_longreprtext_skip(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L1096-L1107][f1]

For a skipped call, longrepr is a tuple (not a str), yet longreprtext renders it containing 'Skipped' (#7559).

<a id="u-b54f7edf48e7"></a>
### `TestReportContents.test_longreprtext_collect_skip`

`def test_longreprtext_collect_skip(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L1109-L1121][f1]

Module-level pytest.skip(allow_module_level=True): the collected CollectReport's longrepr is a tuple and its longreprtext contains 'Skipped', covering the collect-report path of #7559.

<a id="u-6d9b83c69fd2"></a>
### `TestReportContents.test_longreprtext_failure`

`def test_longreprtext_failure(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L1123-L1132][f1]

For `assert x == 4` with x=1, the call report's longreprtext contains 'assert 1 == 4'.

<a id="u-6d9a7657da70"></a>
### `TestReportContents.test_captured_text`

`def test_captured_text(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L1134-L1162][f1]

Captured-output accumulation across phases: the setup report contains only setup-phase stdout/stderr; the call report accumulates setup+call text; the teardown report accumulates setup+call+teardown text, for both capstdout and capstderr, with a failing fixture and failing test.

<a id="u-454a07b606e1"></a>
### `TestReportContents.test_no_captured_text`

`def test_no_captured_text(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L1164-L1173][f1]

A passing item with no output has empty capstdout and capstderr on its call report.

<a id="u-fe5d71e0fc54"></a>
### `TestReportContents.test_longrepr_type`

`def test_longrepr_type(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L1175-L1184][f1]

pytest.fail(pytrace=False) produces a call report whose longrepr is an ExceptionChainRepr instance.

<a id="u-f72a5f47cfc8"></a>
### `TestSessionReports`

`class TestSessionReports:` · [testing/test_runner.py:L499-L500][f1]

Tests collection reporting via runner.collect_one_node on a module collected by pytester.

<a id="u-08963f5c0bbb"></a>
### `TestSessionReports.test_collect_result`

`def test_collect_result(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L500-L521][f1]

For a module with one test function and an empty class, collect_one_node returns a CollectReport that is passed (not failed/skipped), location[0] equals the file name with lineno 0 and location[2] the file name, and result holds exactly two collectors named 'test_func1' and 'TestClass'.

<a id="u-993ebcd97307"></a>
### `test_report_extra_parameters`

`def test_report_extra_parameters(reporttype: type[reports.BaseReport]) -> None:` · [testing/test_runner.py:L531-L538][f1]

Parametrized over BaseReport, TestReport, CollectReport: builds each report type passing an unknown kwarg 'newthing=1' plus empty-list values for every __init__ parameter, asserting the attribute is stored — i.e. report constructors tolerate extra parameters.

<a id="u-d02b4ebca7c1"></a>
### `test_unicode_in_longrepr`

`def test_unicode_in_longrepr(pytester: Pytester) -> None:` · [testing/test_runner.py:L930-L950][f1]

A conftest wrapper hook replaces the call report's longrepr with the non-ascii string 'ä'; the failing run returns exit code 1 and stderr must not contain 'UnicodeEncodeError', i.e. unicode longrepr survives report handling.

<a id="u-9dcc33081a4f"></a>
### `test_runner.py module code (L521–L530)`

`module_region` · [testing/test_runner.py:L521-L530][f1]

Module-level constant list of report types used for parametrization.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_runner.py
