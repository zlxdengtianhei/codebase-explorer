# Parametrize marks and id segments

**Capability.** Marks applied to individual parametrized sets via pytest.param(marks=...) and HIDDEN_PARAM suppression of id segments.

Covers how per-parameter marks and custom id handling surface in collection and reporting.

Parent: [Metafunc and parametrize tests](r4-test-metafunc.md)

## Units (2)

<a id="u-6ec400a26178"></a>
### `metafunc.py-testmarkerswithparametrization`

`class TestMarkersWithParametrization:` · [testing/python/metafunc.py:L1849-L1852][f1]

Tests marks applied to individual parametrized sets via pytest.param(marks=...).

Marks: pytest.mark.foo on the function applies to all items, while a per-param bar mark appears only in that item's keywords; -m foo selects exactly the marked param. xfail as a per-param mark (plain, with condition string, with reason kwarg, or both) makes the failing param report as skipped while others pass (2 passed, 1 skipped); with strict=True an unexpected pass (xpass) is reported failed (2 passed, 1 failed), with strict=False it passes (3 passed). parametrize called from pytest_generate_tests accepts pytest.param entries with marks (2 passed, 2 skipped/xfailed). Mixed int/str ids collect and pass (#290). A marked value passed as a parametrized value and marks given as a list both behave like direct marks, with strict controlling xpass→failed. The pytest_make_parametrize_id hook in conftest overrides generated ids (val*2), and receives argname so different argnames can format differently (x: val*2, y: val*10). Parametrize accepts positional indirect (False) argument. ids supplied as a generator are consumed lazily per parameter per function: two functions sharing a count() generator-based ids expression each get param0/param1 because the shared generator expression in the module is re-evaluated per decorator application, while a shared itertools.count() passed directly continues across parameters (0, 1) within one function's parametrize call; all 6 tests pass.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917); uses: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- The exact per-test-module vs shared generator semantics for ids generators is inferred from the asserted ids in test_parametrize_iterator, not from IdMaker source in this file.

<a id="u-ca42631953c7"></a>
### `metafunc.py-testhiddenparam`

`class TestHiddenParam:` · [testing/python/metafunc.py:L2153-L2156][f1]

Tests pytest.HIDDEN_PARAM for suppressing a parametrized id segment.

In an ids list, HIDDEN_PARAM for one entry yields an item named without brackets ('test_func') while other entries keep their given ids; the same works for pytest.param(id=pytest.HIDDEN_PARAM). Two HIDDEN_PARAM entries within one parametrize call are a collection error: 'multiple instances of HIDDEN_PARAM cannot be used in the same parametrize call, because the tests names need to be unique.' — asserted both end-to-end via --collect-only and directly on IdMaker, which raises Failed matching 'In some_node_id: multiple instances of HIDDEN_PARAM'. Across separate stacked parametrize marks, hiding the id of the inner (second-applied) dimension drops only that segment: items are named 'test_func[a-x]', 'test_func[a-y]', 'test_func[x]', 'test_func[y]', i.e. the hidden 'b'/'a' segments vanish while the other dimension's ids remain.

uses: [_pytest.python.IdMaker](../../catalog.json); calls: [pytester-collection-helpers](r6-pytester-run.md#u-0183c0c437e7), [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

**Uncertainties.**

- Whether a hidden id combined with auto-generated duplicate names in the other dimension is uniquified is not covered here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/python/metafunc.py
