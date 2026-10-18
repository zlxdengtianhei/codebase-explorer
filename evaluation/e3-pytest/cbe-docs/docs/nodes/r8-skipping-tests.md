# Skipping and xfail Tests

**Capability.** testing/test_skipping.py verifies the whole skip/xfail surface: direct marker evaluation (evaluate_skip_marks/evaluate_xfail_marks), skipif conditions including boolean callables, xfail outcomes including failures raised in setup/teardown, module-level reporting edge cases, and skip/xfail on non-Python items via the outcome API.

Use this to understand expected skip/xfail semantics and error messages. Tests mix pytester inline runs with direct item evaluation.

**Depends on.**

- [Test Run Invocation](r6-pytester-run.md) · graph-only · 83 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 67 edge(s)

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Units (8)

<a id="u-04e3161d1c73"></a>
### `test_skipping-item-and-api-tests`

`def test_xfail_item(pytester: Pytester) -> None: # Ensure pytest.xfail works with non…` · [testing/test_skipping.py:L1301-L1320][f1]

Tests for skip/xfail support on non-Python items and outcome API details.

test_xfail_item and test_mark_xfail_item register a conftest-defined custom pytest.Item; the former calls pytest.xfail() inside runtest, the latter adds two xfail markers in setup (a false string-condition one and a true boolean one with reason); both assert via inline_run/listoutcomes that no failure occurred and that skipped reports carry wasxfail, so the false-condition marker's reason ('Expected failure - true') governs. test_module_level_skip_error, test_module_level_skip_with_allow_module_level, and test_invalid_skip_keyword_parameter cover pytest.skip misuse at module level: bare module-level skip reports 'Using pytest.skip outside of a test will skip the entire module' as a collection error, allow_module_level=True skips the whole module with a SKIP summary, and an unknown keyword raises TypeError listing the offending name. test_summary_list_after_errors pins the ordering 'FAILURES' section before 'short test summary info' under -ra. test_importorskip asserts pytest.importorskip('doesnotexist') raises pytest.skip.Exception matching 'could not import ...'. test_relpath_rootdir and test_skip_from_fixture check that skip locations are shown relative to --rootdir ('tests/test_1.py:2') for both a marker skip and a skip raised inside a fixture. The final three tests confirm reason= keyword accepts pytest.skip(reason=...), pytest.fail(reason=...), and pytest.exit(reason=...) without PytestDeprecationWarning, producing respectively skipped=1, failed=1, and the '*_pytest.outcomes.Exit: foo*' message.

uses: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

**Uncertainties.**

- Which of the two stacked xfail markers in test_mark_xfail_item supplies the reported reason is asserted only indirectly (wasxfail presence), not by matching the reason text.

<a id="u-9e880a160cdd"></a>
### `test_skipping-module-level-tests`

`def test_skip_not_report_default(pytester: Pytester) -> None:` · [testing/test_skipping.py:L947-L961][f1]

Module-level functional tests for skip/xfail reporting and evaluation edge cases.

test_skip_not_report_default and test_skipif_class check that skipped outcomes appear as '1 skipped'/'2 skipped' without extra hints. test_skipped_reasons_functional verifies that skip reasons report the skip() call site (helpers.py line) or decorator line via fnmatch_lines_random. test_skipped_folding checks that a module-level pytestmark skip folds both tests into one 'SKIP [2]' summary line. The reportchars group (-rfxXs, -rE, -ra) asserts that failures, xfails, xpasses, skips, and teardown errors each get their designated summary letter, with '-ra' covering all and errors surfacing from a conftest pytest_runtest_teardown that asserts 0. test_errors_in_xfail_skip_expressions checks that a NameError in skipif and a SyntaxError in xfail conditions become per-test ERRORs with 'evaluating skipif/xfail condition' messages and a final '1 pass 2 errors', with Python-3.10+-specific chained-traceback lines and a pypy-adjusted caret line. test_xfail_skipif_with_globals confirms module globals (x == 3) are visible to condition expressions. test_default_markers lists built-in skipif/xfail help via --markers. test_xfail_test_setup_exception shows an xfail test whose conftest setup raises still counts as xfailed with exit 0 and no xpassed. test_imperativeskip_on_xfail_test installs a conftest hook that skips every item in setup and asserts both the imperative 'abc' skip reason and the skipif 'condition: True' reason are reported (2 skipped), i.e. imperative skip takes precedence over xfail/skipif markers.

uses: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- test_errors_in_xfail_skip_expressions branches on sys.version_info and pypy presence, so its exact expected lines are platform-dependent and only the listed branch is asserted per interpreter.

<a id="u-c55c87c814bd"></a>
### `TestBooleanCondition`

`class TestBooleanCondition:` · [testing/test_skipping.py:L1247-L1248][f1]

Covers boolean (non-string) conditions.

skipif(True, reason=...) skips while skipif(False, reason=...) runs; skipif(True) without a reason produces a collection/evaluation error ('1 error') per the boolean-needs-reason rule; xfail(True, reason='True123') of a failing test reports XFAIL with that reason and '1 xfail' under -rxs.

<a id="u-87d6a39d8f8a"></a>
### `TestEvaluation`

`class TestEvaluation:` · [testing/test_skipping.py:L15-L16][f1]

Verifies direct evaluation of skipif and xfail markers on collected items via evaluate_skip_marks/evaluate_xfail_marks and pytester-built items.

Key behaviors established: no marker yields no skip; bare markers evaluate with empty reason; a string condition's reason becomes 'condition: <expr>' while an explicit reason overrides it; multiple skipif marks short-circuit to the truthy condition's reason regardless of stacking order; boolean conditions without reason raise pytest.fail.Exception mentioning reason=STRING, and a condition whose __bool__ raises TypeError is converted into that same exception with the original message embedded; class-level pytestmark participates in evaluation; pytest_markeval_namespace() from conftest injects names into marker expressions, with nested-package conftests overriding the root's keys (all three tests skip), and a non-dict return triggers a ValueError naming the hook and the returned object. test_skipif_markeval_namespace_multiple builds root/foo/bar packages each with their own conftest and asserts three skips under inline_run('-vs','--capture=no').

uses: [function::evaluate_skip_marks][f2], [function::evaluate_xfail_marks][f2]

**Uncertainties.**

- The exact precedence when both a string condition and a later truthy mark supply reasons is only evidenced by the specific stacking orders tested in test_marked_one_arg_twice and test_marked_one_arg_twice2.

<a id="u-46774b86ea55"></a>
### `TestSkip`

`class TestSkip:` · [testing/test_skipping.py:L770-L771][f1]

Functional tests of @pytest.mark.skip.

A skipped class skips all its methods (2 skipped) leaving unmarked module tests passing; a string argument is taken as the reason even when it is the string 'False' (skip is unconditional, unlike skipif); no reason reports 'unconditional skip', a positional or reason= argument is shown verbatim with -rs; only marked tests are skipped while others pass; --strict-markers does not alter skip behavior; and misuse skip(False, reason=...) surfaces a TypeError about __init__() got multiple values for argument 'reason' with a hint suggesting pytest.mark.skipif.

<a id="u-d263ef2ec1a9"></a>
### `TestSkipif`

`class TestSkipif:` · [testing/test_skipping.py:L884-L885][f1]

Exercises skipif evaluation through pytest_runtest_setup on direct items and through runpytest reporting.

Calling pytest_runtest_setup on a skipif('hasattr(os, sep)') item raises pytest.skip.Exception with msg 'condition: ...'; a platform.platform() expression likewise raises. Reporting tests assert '-rs' lines show the failing condition/reason ('platform', 'invalid platform', 'second_condition') with exit 0, and test_skipif_reporting_multiple additionally covers the xfail/XPASS variant where the truthy second marker wins over the false first one, reporting '1 xpassed'.

calls: [function::pytest_runtest_setup][f2]

<a id="u-3ccd7213c87d"></a>
### `TestXFail`

`class TestXFail:` · [testing/test_skipping.py:L298-L299][f1]

End-to-end behavior of xfail markers and imperative pytest.xfail() via runtestprotocol and runpytest runs.

Marker-based cases: strict=False xfail of a failing test yields a skipped call report with wasxfail=''; non-strict xfail of a passing test reports wasxfail with the reason and exit 0; strict=True with a passing test fails with '[XPASS(strict)] <reason>' and no wasxfail attribute; a false string condition leaves the test as a normal failure but still tags 'xfail' in keywords; run=False marks are NOTRUN before the test body (even when setup_module raises, the xfail reason is reported) and pass counts as 1 xfailed; --runxfail disables both decorator xfail (test fails as normal) and imperative xfail (counts as pass); --runxfail does not affect @pytest.mark.skip, which still reports its skip location; dynamic xfail added via request.applymarker in fixtures becomes XFAIL (NOTRUN with run=False), and add_marker during runtest flips a failure to xfailed and a strict pass to failed; raises=TypeError (or a tuple) turns a matching exception into xfail and a non-matching one into failure; strict default comes from the xfail_struct ini setting in test_strict_xfail_default_from_file, where true yields exit 1 and false xpass exit 0; pytest_markeval_namespace() also feeds xfail conditions (color=='green' xfails, color=='red' leaves the test to fail). test_xfail_not_report_default and test_xfail_not_run_xfail_reporting exercise -v/-rx reporting lines.

calls: [function::runtestprotocol][f3]; uses: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- xtest_dynamic_xfail_set_during_setup is name-prefixed with 'x' suggesting it is intentionally deselected, but the source shows no skip mechanism; its stated stdout expectations are unverified by any assertion beyond fnmatch_lines.
- Whether a false-condition xfail sets wasxfail is only negatively evidenced in test_xfail_evalfalse_but_fails; other false-condition paths (strict params) do not check the attribute.

<a id="u-9e6758d06b13"></a>
### `TestXFailwithSetupTeardown`

`class TestXFailwithSetupTeardown:` · [testing/test_skipping.py:L738-L739][f1]

Confirms that an xfail marker turns failures occurring outside the test body into xfail outcomes: a raising setup_function and a raising teardown_function each produce '*1 xfail*' in runpytest output for an otherwise-passing marked test.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_skipping.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/skipping.py
[f3]: ../../../../../../eval/pytest-5989efe/src/_pytest/runner.py
