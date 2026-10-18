# Parametrize & Parameter-Set Tests

**Capability.** Verifies parametrize value handling and the empty_parameter_set_mark option: iterators and odd values as argvalues, name/value mismatch errors, pytest.param id validation, and per-option empty-set mark resolution.

Use this subtree when touching ParameterSet or parametrize collection. Tests assert collected ids, collection-error messages, and that invalid empty-set mark names raise UsageError.

**Depends on.**

- [Marker Plugin Core](r3-mark-implementation.md) · model-inferred · 0 edge(s)

Parent: [Marking & Test Selection](r3-marking.md)

## Units (11)

<a id="u-e769e7b59bd8"></a>
### `test_parametrize_iterator`

`def test_parametrize_iterator(pytester: Pytester) -> None:` · [testing/test_mark.py:L502-L521][f1]

parametrize accepts a generator of argvalues; all three yielded cases run and none are skipped, asserting '3 passed' in output (issue 5354).

<a id="u-dc801fce1292"></a>
### `test_parametrize_with_module`

`def test_parametrize_with_module(pytester: Pytester) -> None:` · [testing/test_mark.py:L381-L393][f1]

Parametrizes with the pytest module object itself as a value; the generated id uses pytest.__name__, asserted on the collected nodeid.

<a id="u-7d7317774ab2"></a>
### `test_parametrized_collect_with_wrong_args`

`def test_parametrized_collect_with_wrong_args(pytester: Pytester) -> None:` · [testing/test_mark.py:L459-L479][f1]

parametrize with 2 names but 3 values produces a collection error whose message reports both counts and contents via stdout fnmatch.

<a id="u-5fb5a790cfee"></a>
### `test_parametrized_collected_from_command_line`

`def test_parametrized_collected_from_command_line(pytester: Pytester) -> None:` · [testing/test_mark.py:L443-L456][f1]

Selecting a parametrized function by node name on the command line collects all three parametrized variants (issue 649).

<a id="u-c16220a2611f"></a>
### `test_parametrized_with_kwargs`

`def test_parametrized_with_kwargs(pytester: Pytester) -> None:` · [testing/test_mark.py:L482-L499][f1]

parametrize called with keyword arguments (argnames/argvalues) combined with a parametrized fixture collects and passes all tests (ret 0).

<a id="u-af0cba0b51e3"></a>
### `test_paramset_empty_no_idfunc`

`def test_paramset_empty_no_idfunc( pytester: Pytester, monkeypatch: pytest.MonkeyPatc…` · [testing/test_mark.py:L1051-L1074][f1]

An empty parametrize set must not invoke the user's id function (which raises ValueError here); the test is reported as SKIPPED with the empty-parameter-set reason, not errored.

<a id="u-f5ee4c0d3623"></a>
### `test_pytest_param_id_allows_none_or_string`

`def test_pytest_param_id_allows_none_or_string(s) -> None:` · [testing/test_mark.py:L1180-L1182][f1]

pytest.param accepts id=None and id='hello world' without raising.

<a id="u-b96e1e95f9ea"></a>
### `test_pytest_param_id_requires_string`

`def test_pytest_param_id_requires_string() -> None:` · [testing/test_mark.py:L1169-L1177][f1]

pytest.param(id=True) raises TypeError with the exact message 'Expected id to be a string or a pytest.HIDDEN_PARAM sentinel, got <class bool>: True'.

<a id="u-b7ec9b8f81e0"></a>
### `test_parameterset_for_fail_at_collect`

`def test_parameterset_for_fail_at_collect(pytester: Pytester) -> None:` · [testing/test_mark.py:L1010-L1048][f1]

With the empty-parameter-set option set to fail_at_collect, resolving the mark directly raises Collector.CollectError matching 'Empty parameter set ...

at line \d\d+', and a real run of an empty parametrize errors during collection, exits with ExitCode.INTERRUPTED.

<a id="u-50324bbabe57"></a>
### `test_parameterset_for_parametrize_bad_markname`

`def test_parameterset_for_parametrize_bad_markname(pytester: Pytester) -> None:` · [testing/test_mark.py:L1077-L1079][f1]

Calling the previous test's body with mark name 'bad' raises pytest.UsageError, verifying invalid option values are rejected.

calls: [test_parameterset_for_parametrize_marks](r3-mark-parametrize-tests.md#u-aab0586c5bc7)

<a id="u-aab0586c5bc7"></a>
### `test_parameterset_for_parametrize_marks`

`def test_parameterset_for_parametrize_marks( pytester: Pytester, mark: str | None ) -…` · [testing/test_mark.py:L983-L1007][f1]

Parametrized over empty-parameter-set mark names (None, '', 'skip', 'xfail'): when a value is given it is written into the ini as EMPTY_PARAMETERSET_OPTION, then pytest_configure runs and get_empty_parameterset_mark resolves the effective mark.

For None or empty input the expected name normalizes to 'skip'; the mark always carries a reason starting 'got empty parameter set ', and xfail additionally gets run=False.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_mark.py
