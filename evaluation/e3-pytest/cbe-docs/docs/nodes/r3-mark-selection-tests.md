# -k / -m Selection Tests

**Capability.** End-to-end verification of keyword and mark expression selection: matching matrices, malformed-expression error handling, parametrized-id keywords, dynamic markers, and absence of marker smear to sibling classes.

Use this subtree when checking or changing -k/-m semantics. The tests run pytester sessions asserting exactly which tests pass per expression, including error paths via stderr and USAGE_ERROR exits.

**Depends on.**

- [Marker Plugin Core](r3-mark-implementation.md) · model-inferred · 0 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 32 edge(s)

Parent: [Marking & Test Selection](r3-marking.md)

## Units (11)

<a id="u-3dac6f0ed76b"></a>
### `test-mark-py-test-keyword-selection`

`class TestKeywordSelection:` · [testing/test_mark.py:L815-L816][f1]

Tests -k keyword selection semantics.

test_select_simple uses a nested check(keyword, name) helper that runs with -k and asserts exactly one failure with the given name plus one deselection batch; substring keywords ('est_on') and 'TestClass and test' work. test_select_extra_keywords adds 'xxx' as an extra keyword to a class item via a conftest hook wrapping pytest_pycollect_makeitem; all six parametrized keyword variants select only test_2 and deselect test_1, proving hook-added keywords participate. test_keyword_extra matches a function attribute (test_one.mykeyword) with -k. test_keyword_extra_dash is xfail because argparse cannot accept an option value starting with '-'. test_no_magic_values ('__', '+', '..') deselects the single test, so magic/dunder values never match. test_no_match_directories_outside_the_suite builds a suite/ tree with an ini, collects via a nested get_collected_names helper over inline_genitems, and asserts that -k with the pytester's external directory name matches nothing while a plain run collects both tests (issue 7040).

calls: [pytester-collection-helpers](r6-pytester-run.md#u-0183c0c437e7)

**Uncertainties.**

- accessing pytester._name is a private attribute; its exact value format is not visible here

<a id="u-bde42daebeca"></a>
### `test-mark-py-test-functional`

`class TestFunctional:` · [testing/test_mark.py:L524-L525][f1]

Functional tests of marker propagation and keyword assignment across class hierarchies, fixtures, and sessions.

Key behaviors: pytestmark on a class propagates to nested classes' items (test_merging_markers_deep); decorators on a subclass do not add marks to a sibling-unmarked base usage, but marks from all base classes merge along the MRO (test_mark_decorator_subclass_does_not_propagate_to_base, test_mark_decorator_baseclasses_merged); a mark on one subclass stays isolated from siblings sharing an unmarked base (test_mark_should_not_pass_to_siebling_class). get_closest_marker returns the function's own mark over an inherited class mark and None when absent (test_mark_closest). A class attribute pytestmark that is not a mark fails collection with TypeError (test_mark_with_wrong_marker). request.applymarker inside a fixture affects item keywords visible in the terminal summary (test_mark_dynamically_in_funcarg). -m by test name does not match unmarked names and deselects both tests (test_no_marker_match_on_unmarked_names). Keywords set on a session-scoped fixture request propagate to function-level setup (test_keywords_at_node_level); session.add_marker accepts strings and Mark objects, and raises ValueError for an int (test_keyword_added_for_session). assert_markers maps item names to expected marker-name sets. Marks attached to pytest.param fixture values cause a skipif skip (test_mark_from_parameters); skipif expressions are re-evaluated per file so one file skips and the other passes (test_reevaluate_dynamic_expr).

**Uncertainties.**

- per-method line attribution inside the group relies on the inventory; some helper/test boundaries (e.g. inline source strings) are not individually verified

<a id="u-712e6f496f01"></a>
### `test_keyword_option_considers_mark`

`def test_keyword_option_considers_mark(pytester: Pytester) -> None:` · [testing/test_mark.py:L349-L353][f1]

Copies an example project and runs -k foo, asserting marks are considered keywords so exactly one test passes.

<a id="u-35a983eb06a0"></a>
### `test_keyword_option_custom`

`def test_keyword_option_custom( expr: str, expected_passed: list[str], pytester: Pyte…` · [testing/test_mark.py:L314-L346][f1]

Parametrized matrix for -k keyword expressions over five plainly named tests, covering substring match, 'not', double negation, and numeric operands ('1 or 2' matching test_1/test_2).

<a id="u-42ad26a73a89"></a>
### `test_keyword_option_parametrize`

`def test_keyword_option_parametrize( expr: str, expected_passed: list[str], pytester:…` · [testing/test_mark.py:L356-L378][f1]

Verifies -k matches against parametrized ids for None, 1.3, and '2-3' parameters, asserting the exact selected test id per expression.

<a id="u-25a7b9c2d447"></a>
### `test_keyword_option_wrong_arguments`

`def test_keyword_option_wrong_arguments( expr: str, expected_error: str, pytester: Py…` · [testing/test_mark.py:L396-L440][f1]

Parametrized over malformed -k expressions (trailing 'or', unbalanced parens, adjacent identifiers, call with kwargs); each run writes an error to stderr containing the expected parser message, captured via capsys.

<a id="u-652a28244d4b"></a>
### `test_mark_option`

`def test_mark_option( expr: str, expected_passed: list[str | None], pytester: Pyteste…` · [testing/test_mark.py:L205-L233][f1]

Parametrized matrix for -m marker expressions (plain, parenthesized, 'not not', and/or) selecting marked tests; asserts exact passed test names per expression.

<a id="u-180cba847c20"></a>
### `test_mark_option_custom`

`def test_mark_option_custom( expr: str, expected_passed: list[str], pytester: Pyteste…` · [testing/test_mark.py:L284-L311][f1]

A conftest pytest_collection_modifyitems adds an 'interface' marker to items by nodeid; -m interface and -m 'not interface' then select accordingly, showing dynamically added markers participate in -m.

<a id="u-0b83683916f4"></a>
### `test_mark_option_with_kwargs`

`def test_mark_option_with_kwargs( expr: str, expected_passed: list[str | None], pytes…` · [testing/test_mark.py:L236-L281][f1]

Exercises -m expressions with keyword arguments (car(color='red') etc.) against tests stacked with several car marks; asserts exact selection including negative temps, boolean, and None (sentinel) matching.

<a id="u-238ee9c68ace"></a>
### `test_mark_expressions_no_smear`

`def test_mark_expressions_no_smear(pytester: Pytester) -> None:` · [testing/test_mark.py:L1082-L1114][f1]

With a base class and two differently marked subclasses, -m FOO selects only the marked subclass's inherited test (1 passed, 1 deselected) — marker expressions do not smear to the base class's other subclass; the commented-out -k portion documents that keywords do smear (expected behavior).

<a id="u-d2e95515d0bc"></a>
### `test_marker_expr_eval_failure_handling`

`def test_marker_expr_eval_failure_handling(pytester: Pytester, expr) -> None:` · [testing/test_mark.py:L1185-L1199][f1]

Invalid -m expressions (unknown name with NOT, parenthesized, or a bogus 'bogus=') produce a stderr line 'ERROR: Wrong expression passed to -m: <expr>:' and exit with ExitCode.USAGE_ERROR rather than an internal error.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_mark.py
