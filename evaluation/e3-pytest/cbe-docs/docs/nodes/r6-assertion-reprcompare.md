# Comparison Explanation Tests

**Capability.** Unit and integration tests of the == explanation generator across ordinary objects, attrs classes and named tuples (via callequal), plus dataclass examples run end to end from copied example files.

Use the callequal-driven groups for exact expected explanation lines; the dataclass group verifies real run output for dataclass comparisons.

**Depends on.**

- [In-Process Explanation Harness](r6-assertion-harness.md) · graph-confirmed · 53 edge(s)

**Depended on by.**

- [In-Process Explanation Harness](r6-assertion-harness.md) · model-inferred · 0 edge(s)

Parent: [Assertion Rewriting Suite](r6-test-assertion.md)

## Units (4)

<a id="u-55da5cd931c1"></a>
### `test-assertion-reprcompare`

`class TestAssert_reprcompare:` · [testing/test_assertion.py:L416-L417][f1]

Unit tests of the == explanation generator, driven almost entirely through callequal and asserting exact explanation line lists.

Observed expectations: comparing different types ([0,1] vs 'foo') yields None; the summary line stays under 65 chars. Text diffs render '- right'/'+ left'; differences beyond a shared 50-char prefix collapse to a 'Skipping' line at verbose=0 but show full text at verbose=1; multiline strings diff line-wise. Bytes comparisons at verbose=0 give 'At index 0 diff' plus 'Use -v to get more diff'; verbose=1 gives a 'Full diff:' ndiff block. Containers at verbose=0 end with 'Use -v to get more diff'; verbose=1/2 append an ndiff 'Full diff:' with '? ' markers; verbose=-1 stays quiet like verbose=0; CI=true in the environment forces the full diff even without -v (tested via runpytest in test_iterable_full_diff_ci). Length mismatches produce 'Left/Right contains one more item' or 'N more items, first extra item'; long elements are abbreviated in summaries and wrapped lists keep element lines intact. Dictionaries at default verbosity report 'Omitting N identical items' with differing items; verbose=1 shows differing items; verbose=2 shows 'Common items:' instead. Custom sequence-like objects (MutableSequence subclass) get explanations; objects whose __repr__ raises produce '<[ValueError raised in repr]>' placeholders and a '(pytest_assertion plugin: representation of details failed: ...)' trailer naming this file and line. A str subclass with empty repr yields no explanation (not expl). Unicode, mojibake bytes, and NFC/NFD comparisons produce str lines with repr-escaped non-ASCII where expected. NamedTuple comparisons use attribute-wise drilldown; two different namedtuple types fall back to the generic sequence matcher. attrs classes are compared attribute-wise by default and are skipped (None) when the class defines a custom __eq__.

calls: [callequal](r6-assertion-harness.md#u-4bbd2900dd1c); uses: [_pytest.assertion.util.format_explanation](../../catalog.json)

**Uncertainties.**

- Exact wrapping/truncation thresholds come only from the literal expected strings in these tests; the wrapping algorithm is in _pytest.assertion.util, not here.

<a id="u-d8d6c2505a5b"></a>
### `test-assertion-reprcompare-attrsclass`

`class TestAssert_reprcompare_attrsclass:` · [testing/test_assertion.py:L1078-L1079][f1]

Tests the == explanation generator against attr-decorated classes, mostly in-process via callequal.

test_attrs expects 'Omitting 1 identical item' with no 'Matching attributes' section at default verbosity and field_a absent from detail lines. test_attrs_recursive and test_attrs_recursive_verbose verify nested attrs objects are drilled into, with indentation for the nested structure at verbose output. test_attrs_verbose at verbose=2 expects 'Matching attributes:' with ['field_a']. test_attrs_with_attribute_comparison_off expects fields declared with eq=False excluded from comparison even when their values differ. test_comparing_two_different_attrs_classes expects None when the two operands have different attrs classes. test_attrs_with_auto_detect_and_custom_eq and test_attrs_with_custom_eq expect None when the class defines a custom __eq__ (issue 9362), including under attr.s(auto_detect=True).

calls: [callequal](r6-assertion-harness.md#u-4bbd2900dd1c)

<a id="u-9aded396e671"></a>
### `test-assertion-reprcompare-namedtuple`

`class TestAssert_reprcompare_namedtuple:` · [testing/test_assertion.py:L1215-L1216][f1]

Tests explanations for NamedTuple comparisons via callequal.

test_namedtuple expects attribute-wise output: 'Omitting 1 identical items', 'Differing attributes: ['b']', a 'Drill down into differing attribute b:' block, and a trailing 'Use -v to get more diff'. test_comparing_two_different_namedtuple shows that two distinct NamedTuple types (NT1 vs NT2) use the generic sequence matcher instead, producing 'At index 0 diff: 1 != 2' plus the -v hint.

<a id="u-f16c9ef9e9aa"></a>
### `test-assertion-reprcompare-dataclass`

`class TestAssert_reprcompare_dataclass:` · [testing/test_assertion.py:L965-L966][f1]

Integration tests copying example files from the dataclasses/ example directory and running pytest on them, asserting output shapes.

test_dataclasses expects the 'Omitting identical items / Differing attributes / Drill down into differing attribute' output. test_recursive_dataclasses expects nested drill-down with a truncation notice at default verbosity; test_recursive_dataclasses_verbose with -vv expects full recursive 'Matching attributes'/'Differing attributes' blocks. test_dataclasses_verbose expects -vv output including Matching attributes and per-field diff. test_dataclasses_with_attribute_comparison_off expects the example passes (fields with compare=False are ignored). test_comparing_two_different_data_classes expects a pass. test_data_classes_with_custom_eq (issue 9362) expects a failure with no 'Differing attributes' line. test_data_classes_with_initvar (issue 9820) expects a failure with no AttributeError leakage.

uses: [Pytester.copy_example](r6-pytester-core.md#u-c15c0894e320)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_assertion.py
