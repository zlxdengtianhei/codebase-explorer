# Assertion Rewriting Suite

**Capability.** Verifies assertion rewriting end to end (import-hook installation across conftest/plugins, == explanation generation, explanation formatting and truncation) through both Pytester runs and in-process plugin calls.

Start with the in-process harness to unit-test explanations, then the e2e and import-hook groups for full-run behavior. The dataclass group shows the copy_example idiom.

**Children.**

- [In-Process Explanation Harness](r6-assertion-harness.md) `r6-assertion-harness` · 5 unit(s)
- [Comparison Explanation Tests](r6-assertion-reprcompare.md) `r6-assertion-reprcompare` · 4 unit(s)
- [Explanation Formatting and Truncation](r6-assertion-formatting.md) `r6-assertion-formatting` · 2 unit(s)

**Depends on.**

- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-confirmed · 56 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-confirmed · 51 edge(s)
- [In-Process Explanation Harness](r6-assertion-harness.md) · within containment · 4 edge(s)

Parent: [Regression Suites](r6-test-suites.md)

## Units (2)

<a id="u-41042708def9"></a>
### `test-assertion-e2e`

`def test_python25_compile_issue257(pytester: Pytester) -> None:` · [testing/test_assertion.py:L1533-L1548][f1]

End-to-end tests exercising assertion rewriting and reporting through pytester runs, plus a few in-process callop/callequal tests.

In-process: test_reprcompare_notin expects a 'not in' explanation with a containment annotation; test_reprcompare_whitespaces expects a whitespace-only diff with repr() escaping note; test_reprcompare_verbose_long pins the unabbreviated verbose=2 header for an 11-key dict; test_exit_from_assertrepr_compare monkeypatches util.istext to raise outcomes.Exit and asserts callequal propagates that Exit. Subprocess tests: test_python25_compile_issue257 and test_rewritten check rewritten assertions report failures or pass when globals are checked; test_assertion_options checks rewritten '3 == 4' detail in-process but not under --assert=plain subprocess; test_triple_quoted_string_issue113 checks no SyntaxError with --fulltrace; test_traceback_failure pins the long and auto traceback layout including 'E assert 3 == 2' and 'where 2 = g()'; test_exception_handling_no_traceback checks multiprocessing chain tracebacks render; test_warn_missing runs python -OO variants and matches PytestConfigWarning output for assertions not being executed; test_recursion_source_decode checks --collect-only output with python_files = *.py; test_AssertionError_message checks 'assert 0, (x,y)' message rendering; test_diff_newline_at_end checks trailing-newline diffs; test_assert_tuple_warning expects the 'assertion is always true' warning for a 2-tuple operand but not for an empty tuple; test_assert_indirect_tuple_no_warning expects no warning for a named tuple variable; test_assert_with_unicode, test_raise_unprintable_assertion_error, and test_raise_assertion_error_raising_repr check message rendering including '<exception str() failed>'; test_issue_1944 expects '1 error' without the historical AttributeError; test_assertion_location_with_coverage checks correct location reporting with a msg argument; test_assertrepr_loaded_per_dir verifies per-directory pytest_assertrepr_compare conftest summaries are applied per test file; test_assertrepr_compare_integration in TestSetAssertions and test_set_extra_item/test_set_proper_superset_equal pin set-difference explanations ('Extra items in the left/right set', 'Both sets are equal'); test_comparisons_handle_colors verifies colored and uncolored diff output via color_mapping formatting; test_fine_grained_assertion_verbosity checks verbosity_assertions = 2 ini yields full diffs for list, dict, and substring assertions; test_full_output_vvv checks argument truncation at default verbosity and full display at -vvv.

calls: [callequal](r6-assertion-harness.md#u-4bbd2900dd1c)

**Uncertainties.**

- The color_mapping fixture and color tag semantics ({bold}, {number}, etc.) are external fixtures not shown in this file.

<a id="u-b85efa5ee622"></a>
### `test-assertion-importhookinstallation`

`class TestImportHookInstallation:` · [testing/test_assertion.py:L79-L80][f1]

Integration tests that assertion rewriting is installed for conftest files, pytest_plugins modules, and distribution-installed plugins, comparing --assert=plain against --assert=rewrite output.

test_conftest_assertion_rewrite places a conftest at root or in foo/ and expects 'E AssertionError' under plain but '*assert 10 == 30*' detail under rewrite. test_rewrite_assertions_pytester_plugin asserts failures inside the pytester plugin itself get rewritten diff output, with an unstable pair matched via fnmatch_lines_random. test_pytest_plugins_rewrite runs the same plain/rewrite expectation when the plugin comes from conftest pytest_plugins. test_pytest_plugins_rewrite_module_names checks str and list forms of pytest_plugins mark 'ham' in rewrite_hook._must_rewrite (exit 0). test_pytest_plugins_rewrite_module_names_correctly checks find_spec matches 'ham' but not 'hamster' (prefix-safety). test_installed_plugin_rewrite runs a wrapper script monkeypatching importlib.metadata.distributions with a fake pytest11 entry point; its disable_plugin_autoload and explicit_specify parameters decide outcomes: when the plugin is visible (autoload on or explicitly specified) both tests fail with the expected plain/rewrite line, otherwise both error with 'fixture not found'. test_rewrite_ast verifies modules registered via pytest.register_assert_rewrite get rewritten assertions. test_register_assert_rewrite_checks_types asserts register_assert_rewrite rejects a list argument with TypeError but accepts multiple string arguments.

**Uncertainties.**

- Whether DummyDistInfo satisfies every importlib.metadata consumer is defined only by the embedded wrapper script; behavior outside pytest's use of distributions() is unproven.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_assertion.py
