# In-Process Explanation Harness

**Capability.** Drives pytest_assertrepr_compare directly: a minimal fake Config with controlled verbosity, callop/callequal wrappers invoking the plugin, and tests of the mock's verbosity semantics plus hook-invocation verification.

Use callequal for quick unit checks of equality explanations; callop exposes operator choice and verbosity. mock_config underpins all in-process calls.

**Depends on.**

- [Comparison Explanation Tests](r6-assertion-reprcompare.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Comparison Explanation Tests](r6-assertion-reprcompare.md) · graph-confirmed · 53 edge(s)
- [Assertion Rewriting Suite](r6-test-assertion.md) · within containment · 4 edge(s)

Parent: [Assertion Rewriting Suite](r6-test-assertion.md)

## Units (5)

<a id="u-4bbd2900dd1c"></a>
### `callequal`

`def callequal(left: Any, right: Any, verbose: int = 0) -> list[str] | None:` · [testing/test_assertion.py:L412-L413][f1]

Convenience wrapper fixing the operator to '==': returns callop('==', left, right, verbose) unchanged, so callers get the plugin's explanation lines for an equality comparison or None when no explanation applies.

calls: [callop](r6-assertion-harness.md#u-ea59edc57454)

<a id="u-ea59edc57454"></a>
### `callop`

`def callop(op: str, left: Any, right: Any, verbose: int = 0) -> list[str] | None:` · [testing/test_assertion.py:L407-L409][f1]

In-process driver for the assertion explanation plugin: constructs mock_config(verbose=verbose) and calls plugin.pytest_assertrepr_compare(config, op, left, right), returning the plugin's list[str] explanation or None.

Tests use it to exercise explanation generation without spawning subprocesses.

calls: [mock_config](r6-assertion-harness.md#u-fcb1b34a1197), [_pytest.assertion](../../catalog.json)

<a id="u-fcb1b34a1197"></a>
### `mock_config`

`def mock_config(verbose: int = 0, assertion_override: int | None = None):` · [testing/test_assertion.py:L22-L23][f1]

Builds a minimal fake pytest Config whose verbosity lookups are controlled by two captured parameters.

The returned Config.get_verbosity returns verbose when called with no type; for _Config.VERBOSITY_ASSERTIONS it returns assertion_override when that is not None, else verbose; any other verbosity_type raises KeyError('Not mocked out: ...'). get_terminal_writer returns a TerminalWriter whose _highlight echoes the source unchanged, so plugin output paths never exercise real highlighting. This stub lets pytest_assertrepr_compare run in-process without a real Config.

uses: [_pytest.config](../../catalog.json)

**Uncertainties.**

- Only get_verbosity and get_terminal_writer are implemented; callers needing other Config methods are outside this file's evidence.

<a id="u-03b46dc5fc5f"></a>
### `test-assertion-mockconfig-tests`

`class TestMockConfig:` · [testing/test_assertion.py:L44-L48][f1]

Tests the mock_config stub's verbosity semantics.

test_verbose_exposes_value checks get_verbosity() with no argument returns the verbose value (3). test_get_assertion_override_not_set_verbose_value checks that with assertion_override unset, get_verbosity(_Config.VERBOSITY_ASSERTIONS) falls back to verbose. test_get_assertion_override_set_custom_value checks that an explicit assertion_override (10) wins over verbose for the assertions verbosity type. test_get_unsupported_type_error asserts any unrecognized verbosity_type string raises KeyError. All four build the config through mock_config and assert only on its return values; no pytester subprocess is involved.

<a id="u-659a313e5fe7"></a>
### `TestBinReprIntegration.test_pytest_assertrepr_compare_called`

`def test_pytest_assertrepr_compare_called(self, pytester: Pytester) -> None:` · [testing/test_assertion.py:L382-L404][f1]

Verifies the pytest_assertrepr_compare hook is invoked with the comparison operator and operands.

A conftest defines a recording hook appending (op, left, right) tuples and a 'list' fixture exposing the recorded values. A failing 'assert 0 == 1' test then a passing test asserting the recorded list equals [('==', 0, 1)] confirm the hook ran exactly once with those arguments. Run with runpytest('-v') and matched via fnmatch_lines for FAIL and PASS outcomes.

**Uncertainties.**

- Hook return value None (not a list) is assumed to let the default explanation proceed; that fallback lives outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_assertion.py
