# Collection and Assertion Payload Examples

**Capability.** Trivial payload modules and demos: package/__init__ collection cases, a __main__.py doctest-ignoring case, a collect-stats template, a UsageError-raising conftest, dataclass comparison examples (verbose output and InitVar exclusion), and the warnings-grouping example projects.

Each module exists to be collected or copied by a test and produce a predictable result; the warnings examples are duplicated by the warnings grouping tests to check summary aggregation across modules.

**Depended on by.**

- [Warning Handling Tests](r7-warnings-tests.md) · model-inferred · 0 edge(s)

Parent: [Example Scripts and Packaging Harness](r7-example-scripts.md)

## Units (9)

<a id="u-6dde8633637e"></a>
### `collect_init_tests-tests-init`

`def test_init():` · [testing/example_scripts/collect/collect_init_tests/tests/__init__.py:L5-L6][f1]

Package __init__ defining one trivially passing test_init; used to verify that pytest collects tests declared inside package __init__ files.

<a id="u-c10f1309e468"></a>
### `package_init_given_as_arg-pkg-init`

`def test_init():` · [testing/example_scripts/collect/package_init_given_as_arg/pkg/__init__.py:L5-L6][f2]

Package __init__ defining one trivially passing test_init; used to check collection when the package __init__ itself is given as a command-line argument.

<a id="u-37acbec672ae"></a>
### `main_py-main`

`def test_this_is_ignored():` · [testing/example_scripts/doctest/main_py/__main__.py:L5-L6][f3]

__main__.py containing one trivially passing test, test_this_is_ignored; used to verify that doctest collection ignores __main__.py modules.

<a id="u-339860a12060"></a>
### `template_test-py`

`def test_x():` · [testing/example_scripts/perf_examples/collect_stats/template_test.py:L5-L6][f4]

Template module copied byte-for-byte by generate_folders into the generated tree; contains one trivially passing test_x used purely as collection payload.

<a id="u-38c571e36a5d"></a>
### `conftest_usageerror-conftest`

`def pytest_configure(config):` · [testing/example_scripts/conftest_usageerror/conftest.py:L5-L8][f5]

conftest where pytest_configure unconditionally raises pytest.UsageError('hello'), turning session startup into a usage error; the hook never completes and there is no fallback.

pytest_unconfigure prints 'pytest_unconfigure_called', probing whether unconfigure still runs after a configure-time UsageError.

**Notes.**

- failure: pytest_configure always raises pytest.UsageError; no other path exists.

**Uncertainties.**

- Execution of pytest_unconfigure after the configure-time UsageError cannot be decided from this source.

<a id="u-5c1c003f09af"></a>
### `test_compare_dataclasses_verbose.py`

`def test_dataclasses_verbose() -> None:` · [testing/example_scripts/dataclasses/test_compare_dataclasses_verbose.py:L7-L8][f6]

Same shape as the basic dataclass-comparison example: test_dataclasses_verbose defines a local SimpleDataObject with two comparing fields, builds instances with differing field_b, and the failing 'assert left == right' exercises verbose assertion output for dataclasses.

The -v runtime mode is implied by the file name, not by code in this file.

**Uncertainties.**

- Verbose mode is an external pytest option; nothing in this file enables it.

<a id="u-702dc2e9158d"></a>
### `test_compare_initvar.py`

`class Foo:` · [testing/example_scripts/dataclasses/test_compare_initvar.py:L8-L11][f7]

Demonstrates that InitVar fields are excluded from dataclass equality.

Module-level @dataclass Foo declares init_only: InitVar[int] plus real_attr: int; test_demonstrate asserts Foo(1, 2) == Foo(1, 3), which holds because init_only (2 vs 3) does not participate in comparison while real_attr matches.

<a id="u-7e3235fbdc25"></a>
### `test_group_warnings_by_message.py`

`def func(msg):` · [testing/example_scripts/warnings/test_group_warnings_by_message.py:L9-L10][f8]

Produces warnings expected to be grouped by message in the summary.

func(msg) emits warnings.warn(UserWarning(msg)); test_foo and test_bar are each parametrized over range(5) and call func('foo')/func('bar') respectively, and test_foo_1 calls func('foo') once. All tests pass; the example exists so the runner's warning summary shows repeated identical messages grouped.

**Uncertainties.**

- Warning-summary grouping is runner behavior; nothing in this file asserts it.

<a id="u-abd809fc5bd3"></a>
### `test_2.py`

`def test_2():` · [testing/example_scripts/warnings/test_group_warnings_by_message_summary/test_2.py:L7-L8][f9]

Imports func from sibling module test_1 and emits one UserWarning('foo') from test_2, so the summary mixes warnings raised from two modules with the same message text; the test itself passes.

imports: [test_1.py](r2-pytest-root.md#u-785b38f87501)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/collect/collect_init_tests/tests/__init__.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/collect/package_init_given_as_arg/pkg/__init__.py
[f3]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/doctest/main_py/__main__.py
[f4]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/perf_examples/collect_stats/template_test.py
[f5]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/conftest_usageerror/conftest.py
[f6]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/dataclasses/test_compare_dataclasses_verbose.py
[f7]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/dataclasses/test_compare_initvar.py
[f8]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/warnings/test_group_warnings_by_message.py
[f9]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/warnings/test_group_warnings_by_message_summary/test_2.py
