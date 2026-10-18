# Warning Handling Tests

**Capability.** testing/test_warnings.py and testing/test_warning_types.py: filter precedence, warnings-summary grouping, deprecation-to-error lifecycle, config-time warning forwarding, warning location annotation, and the pytest __module__ display contract.

Read for the expected warning-reporting behavior at each stage (configure, collection, runtest, sessionfinish) and for the grouping rules exercised against the copied example projects.

**Depends on.**

- [Hook Specifications](r7-core-hook-contracts.md) · model-inferred · 0 edge(s)
- [Collection and Assertion Payload Examples](r7-misc-examples.md) · model-inferred · 0 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 42 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-only · 35 edge(s)

Parent: [pytest's Own Test Suites](r7-internal-test-suites.md)

## Units (14)

<a id="u-5c28f5557ee0"></a>
### `test_warnings.py-warnings-summary`

`def pyfile_with_warnings(pytester: Pytester, request: FixtureRequest) -> str:` · [testing/test_warnings.py:L16-L37][f1]

The pyfile_with_warnings fixture creates a test importing a module (named from the test function) whose foo() warns UserWarning and RuntimeWarning, and inserts it on sys.path.

The grouped tests assert the 'warnings summary' section: test_normal_flow expects per-warning location lines and '1 passed, 2 warnings' under default filters; test_setup_teardown_warnings shows warnings from fixture setup and teardown attributed to the test file lines; test_unicode shows a non-ASCII warning message; test_non_string_warning_argument confirms a multi-argument UserWarning does not break capture ('1 passed, 1 warning'); test_collection_warnings verifies module-level warnings during collection are captured; test_mark_regex_escape confirms filterwarnings mark patterns pass regex characters through unescaped (warning ignored).

<a id="u-e096d007b467"></a>
### `test_warnings.py-filter-precedence`

`def test_as_errors(pytester: Pytester, pyfile_with_warnings, method) -> None:` · [testing/test_warnings.py:L87-L106][f1]

Tests filter ordering.

test_as_errors (parametrized cmdline/ini, run in a subprocess) expects the UserWarning to fail the test ('1 failed'). test_ignore expects a pass with no warnings-summary header. test_filterwarnings_mark shows the filterwarnings mark beating ini and cmdline 'always::RuntimeWarning': the marked-ignore test passes, the marked-error test fails, the unmarked one warns ('1 failed, 2 passed, 1 warning'). test_filterwarnings_mark_registration asserts --strict-markers accepts the mark. test_hide_pytest_internal_warnings (parametrized no/ini/cmdline) shows PytestWarning from the test module appears unless an ignore filter for it is set via ini or -W. test_option_precedence_cmdline_over_ini shows -W ignore overriding an ini 'error::UserWarning' (pass) while without -W the test fails; test_option_precedence_mark shows a mark's 'error' overriding even cmdline '-W ignore' (fail).

**Uncertainties.**

- test_works_with_filterwarnings is permanently skipped (issue #13485), so its pass condition is asserted only by the docstring scenario, not by an active run.

<a id="u-89a0815ee13e"></a>
### `test_warnings.py-deprecation-default`

`class TestDeprecationWarningsByDefault:` · [testing/test_warnings.py:L428-L434][f1]

All runs use runpytest_subprocess to avoid inheriting this suite's filters.

create_file emits a DeprecationWarning at collection and a PendingDeprecationWarning in the test (optionally behind a mark). test_shown_by_default shows both warnings appear even when the ini customizes other filters (parametrized). test_hidden_by_ini hides both via ini ignores. test_hidden_by_mark hides only the marked PendingDeprecationWarning, leaving the collection warning shown. test_hidden_by_cmdline hides both via -W flags; test_hidden_by_system hides them via the PYTHONWARNINGS environment variable. test_invalid_regex_in_filterwarning feeds 'ignore::DeprecationWarning:*' whose message part '[*]' is an invalid regex and asserts USAGE_ERROR with the parsing-error text on stderr.

<a id="u-8d4399746cfd"></a>
### `test_warnings.py-assertion-warnings`

`class TestAssertionWarnings:` · [testing/test_warnings.py:L576-L577][f1]

test_tuple_warning runs a test whose assertion is a parenthesized tuple and expects the rewrite warning 'assertion is always true, perhaps remove parentheses?' in stdout, via the assert_result_warns helper matching PytestAssertRewriteWarning lines.

<a id="u-3911d78ae66e"></a>
### `test_warnings.py-grouping`

`def test_group_warnings_by_message(pytester: Pytester) -> None:` · [testing/test_warnings.py:L603-L631][f1]

Both tests copy example projects and assert warnings-summary output with consecutive=True matching.

test_group_warnings_by_message expects same-message warnings grouped per test id (test_foo[0..4], test_foo_1 under 'foo'; test_bar[0..4] under 'bar'), totaling 11 passed/11 warnings. test_group_warnings_by_message_summary expects cross-file count lines ('test_1.py: 21 warnings', 'test_2.py: 1 warning' for foo; 'test_1.py: 20 warnings' for bar), totaling 42 passed/42 warnings.

<a id="u-589d5892232c"></a>
### `test_warnings.py-stacklevel`

`class TestStackLevel:` · [testing/test_warnings.py:L676-L677][f1]

The capwarn fixture installs a CapturedWarnings plugin appending (warning_message, location) and exposes the class for assertions.

test_issue4445_rewrite registers assert-rewrite for an empty module in conftest and expects the 'Module already imported' warning location to be conftest.py line 4, function '<module>'. test_issue4445_preparse breaks conftest loading (imports nothing) and expects the warning from config.__init__._preparse ('could not load initial conftests'). test_conftest_warning_captured shows a conftest-time UserWarning appears in stdout at conftest.py:2. test_issue4445_import_plugin skips a plugin at module level and expects the 'skipped plugin' warning from _warn_about_skipped_plugins in config/__init__. test_issue4445_issue5928_mark_generator runs a test with an unknown mark in a subprocess and expects 'Unknown pytest.mark.unknown' output pointing at the test file line 3.

<a id="u-8033381d60f8"></a>
### `test_pytest_configure_warning`

`def test_pytest_configure_warning(pytester: Pytester, recwarn) -> None:` · [testing/test_warnings.py:L658-L673][f1]

A conftest warns during pytest_configure; the run collects nothing (ret 5), stderr has no INTERNALERROR, and the current-process recwarn.pop() yields the 'from pytest_configure' message, showing config-time warnings are forwarded into the invoking session (issue 5115) rather than crashing.

calls: [WarningsRecorder.pop](r3-recwarn.md#u-10692f5a6904)

<a id="u-c2abe6c2812b"></a>
### `test_removed_in_x_warning_as_error`

`def test_removed_in_x_warning_as_error(pytester: Pytester, change_default) -> None:` · [testing/test_warnings.py:L539-L573][f1]

Currently skipped until pytest 9.0; parametrized on None/ini/cmdline, it warns PytestRemovedIn9Warning and asserts the default turns it into a test failure, while an ini or cmdline ignore filter makes it pass, guarding the deprecation-to-error lifecycle.

<a id="u-4ce8daffac87"></a>
### `test_warnings_checker_twice`

`def test_warnings_checker_twice() -> None:` · [testing/test_warnings.py:L594-L600][f1]

Reuses a single pytest.warns(UserWarning) expectation for two sequential with-blocks, each catching one UserWarning, showing the checker supports repeated entry (issue #4617).

<a id="u-512b01224556"></a>
### `testing/test_warnings.py:test_warning_recorded_hook`

`def test_warning_recorded_hook(pytester: Pytester) -> None:` · [testing/test_warnings.py:L271-L297][f1]

Verifies the pytest_warning_recorded hook fires for warnings at each stage.

conftest issues a config-time warning via issue_config_time_warning; the test module warns at collection, and a fixture warns at setup/teardown with one at call. A local WarningCollector plugin records (message, when, nodeid, location) tuples; the test asserts the exact sequence config/collect/runtest×3 with nodeids, and checks location loosely (types str/int/str when present, else None) because it is platform-dependent.

<a id="u-d84e229fd4af"></a>
### `test_warning_on_testpaths_not_found`

`def test_warning_on_testpaths_not_found(pytester: Pytester) -> None: # Check for warn…` · [testing/test_warnings.py:L798-L809][f1]

With ini testpaths='absent' matching nothing, the run emits a ConfigWarning 'No files were found in testpaths' and reports 1 warning in the summary.

<a id="u-d94e6d644c0e"></a>
### `test_resource_warning`

`def test_resource_warning(pytester: Pytester, monkeypatch: pytest.MonkeyPatch) -> Non…` · [testing/test_warnings.py:L812-L863][f1]

Detects tracemalloc availability (ImportError branch sets has_tracemalloc False, deliberately not skipping so PyPy keeps coverage), deletes PYTHONTRACEMALLOC, and runs a child test leaving a file open under -Xdev.

Without tracemalloc enabled, output lacks ResourceWarning lines; with monkeypatched PYTHONTRACEMALLOC=20 the second run expects '*Object allocated at*' instead of the generic 'Enable tracemalloc' hint; both runs must end '1 passed'.

<a id="u-562ae7314c57"></a>
### `test_warning_types.py-warning-module`

`def test_warning_types(warning_class: UserWarning) -> None:` · [testing/test_warning_types.py:L11-L23][f2]

test_warning_types iterates every Warning subclass declared in _pytest.warning_types and asserts each has __module__ == 'pytest', the #5452 display hack.

test_pytest_warnings_repr_integration_test turns pytest.PytestWarning into an error via filterwarnings and expects the child run's output to render 'E pytest.PytestWarning: some warning', confirming the module rename in reprs.

**Uncertainties.**

- The __module__ assignment itself happens in _pytest.warning_types, not in this batch.

<a id="u-0e21d6377d01"></a>
### `test_warn_explicit_for_annotates_errors_with_location`

`def test_warn_explicit_for_annotates_errors_with_location():` · [testing/test_warning_types.py:L44-L50][f2]

With all warnings as errors, calls warning_types.warn_explicit_for on pytest.raises with a PytestWarning and expects the raised Warning whose message matches 'test' with an 'at ...raises.py:<n>' location line, verifying the function annotates warnings with the target function's source location.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_warnings.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/test_warning_types.py
