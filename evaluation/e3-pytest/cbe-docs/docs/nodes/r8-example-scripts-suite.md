# Example Script Scenarios

**Capability.** testing/example_scripts plus a few runner tests act as executable fixtures for specific behaviors: custom collectors, fixture shadowing and scoping order (issue 519, module/class fixtures, subdirectory conftests), assertion explanation output on recursive dataclasses, doctest-in-docstring modules, unittest skip/setup semantics, tmp_path with hostile names, and frozen-build sanity checks.

Use this subtree as expected-outcome examples: each script is run by a companion test or serves as a regression scenario. They are not unit tests of a single module but demonstrations of end-to-end contracts.

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Units (15)

<a id="u-554a833bf9e8"></a>
### `custom_item-conftest`

`class CustomItem(pytest.Item):` · [testing/example_scripts/fixtures/custom_item/conftest.py:L7-L8][f1]

Defines a custom Item/File collector pair.

pytest_collect_file unconditionally returns a CustomFile built via from_parent from the given path and parent, so every file reaching the hook maps to a CustomFile. CustomFile.collect yields one CustomItem named 'foo' parented to the file; CustomItem.runtest is a no-op, so the item always passes.

**Uncertainties.**

- Any filtering of files before pytest_collect_file runs is decided upstream and not visible here.

<a id="u-c9894b4fcee2"></a>
### `customdirectory-conftest`

`class ManifestDirectory(pytest.Directory):` · [testing/example_scripts/customdirectory/conftest.py:L10-L11][f2]

Custom directory collector driven by a manifest.json file.

pytest_collect_directory returns a ManifestDirectory via from_parent only when path joined with 'manifest.json' is a file, otherwise None so other collectors can claim the path. ManifestDirectory.collect reads manifest.json as UTF-8 JSON and, for each entry in manifest['files'], delegates to ihook.pytest_collect_file with the joined child path and itself as parent, yielding all collected nodes. A missing manifest suppresses node creation; malformed JSON or a missing 'files' key raises from collect.

calls: [path-localpath-readwrite](r6-path-fs.md#u-4e0de7f2e479); uses: [hookspec-collection-hooks](r7-core-hook-contracts.md#u-f28b159c5c5d)

**Uncertainties.**

- Manifest 'files' entries are assumed to be relative names joinable via self.path / file; their exact form is not visible here.

<a id="u-916bedbdbc66"></a>
### `issue88_initial_file_multinodes-conftest`

`class MyFile(pytest.File):` · [testing/example_scripts/issue88_initial_file_multinodes/conftest.py:L7-L8][f3]

Reproduces issue 88: a file collector producing custom item nodes.

pytest_collect_file wraps every collected file in a MyFile via from_parent; MyFile.collect returns a list with one MyItem named 'hello'. MyItem.runtest raises NotImplementedError unconditionally, so running the item always fails; this failure is the intended demonstration.

**Notes.**

- failure: MyItem.runtest raises NotImplementedError on every run; the item can never pass.

<a id="u-49cf42f40d22"></a>
### `issue_519-py-other`

`def pytest_generate_tests(metafunc):` · [testing/example_scripts/issue_519.py:L9-L14][f4]

Remaining issue-519 pieces demonstrating parametrization scope versus fixture instantiation order.

pytest_generate_tests parametrizes 'arg1' with two module-scoped values and 'arg2' with two function-scoped values, each only when the name appears in metafunc.fixturenames. Module-scoped fix1 depends on arg1 and checked_order, appends (node name, 'fix1', arg1) and yields 'fix1-'+arg1; function-scoped fix2 depends on fix1, arg2 and checked_order, appends (node name, 'fix2', arg2) and yields 'fix2-'+arg2+fix1. test_one and test_two each request fix2 only; the exact expected ordering is asserted by the checked_order fixture.

uses: [checked_order](r8-example-scripts-suite.md#u-b128343257fb); calls: [Metafunc.parametrize](r7-py-parametrization.md#u-8c79ced9d8b3)

<a id="u-b128343257fb"></a>
### `checked_order`

`def checked_order():` · [testing/example_scripts/issue_519.py:L17-L34][f4]

Session-scoped yield fixture that records and verifies fixture instantiation order.

It creates a list of (node name, fixture name, arg value) tuples, yields it so other fixtures append entries, and at session teardown pretty-prints the list and asserts it equals an exact expected sequence: fix1 once per module-scoped arg1 value before that value's four function-scoped fix2 entries. Any deviation fails the session with AssertionError after the order is printed.

**Notes.**

- side_effect: pprint.pprint(order) writes the recorded order to stdout during finalization, before the assertion.
- failure: AssertionError at session end unless the recorded tuples match the exact expected ten-entry sequence.

<a id="u-d41a2ba31d24"></a>
### `test_519`

`def test_519(pytester: Pytester) -> None:` · [testing/examples/test_issue519.py:L6-L9][f5]

Regression test running an example file through pytest and asserting eight passing tests.

It copies issue_519.py from the examples directory into the pytester sandbox, runs pytest on it in-process, and fails via assert_outcomes unless exactly 8 tests passed with no other outcomes.

**Uncertainties.**

- Behavior depends on the external example file issue_519.py, which is not supplied here; what the 8 tests cover is unknown.

<a id="u-671e57f7ee7e"></a>
### `test_extend_fixture_module_class.py`

`def spam():` · [testing/example_scripts/fixtures/fill_fixtures/test_extend_fixture_module_class.py:L7-L9][f6]

Shows fixture shadowing at class level.

Module fixture spam returns 'spam'; TestSpam defines its own @pytest.fixture spam(self, spam) that requests the module-level value and returns it doubled, so test_spam(spam) inside the class receives 'spamspam' and its assertion passes. Outside the class the module fixture still yields the undoubled string.

<a id="u-0b6aa585e359"></a>
### `test_funcarg_lookup_modulelevel.py`

`def something(request):` · [testing/example_scripts/fixtures/fill_fixtures/test_funcarg_lookup_modulelevel.py:L7-L9][f7]

Compares module-level fixture resolution for a class method and a plain function.

Fixture something returns request.function.__name__; for TestClass.test_method this is 'test_method' and for test_func it is 'test_func', and each test asserts its own expected name, so both pass only if request.function reflects the actual requesting function rather than the defining context.

<a id="u-591d8776a48c"></a>
### `arg2`

`def arg2(request):` · [testing/example_scripts/fixtures/fill_fixtures/test_conftest_funcargs_only_available_in_subdir/sub2/conftest.py:L7-L9][f8]

Fixture arg2 mirrors the sub1 case in the other direction: pytest.raises(Exception, request.getfixturevalue, "arg1") attempts to resolve arg1 (defined only in sub1's conftest) and catches the resulting lookup error, so the fixture returns None and test_2 can request it without error.

uses: [FixtureRequest](r5-fixture-request-context.md#u-e8edbc928469)

<a id="u-f31398c3399b"></a>
### `test_doc`

`def test_doc():` · [testing/example_scripts/doctest/main_py/test_normal_module.py:L5-L10][f9]

A normal pytest test whose docstring carries a doctest example ('10 > 5' yielding True) while the body raises AssertionError via 'assert False'.

As written, calling the function always fails; the passing doctest inside the docstring only runs if the doctest plugin collects this module, which the surrounding example script presumably configures.

**Uncertainties.**

- Nothing in this file enables doctest collection; whether the docstring example executes depends on external runner flags.

<a id="u-ba786845f193"></a>
### `test_setup_skip.py`

`class Base(unittest.TestCase):` · [testing/example_scripts/unittest/test_setup_skip.py:L9-L10][f10]

Verifies that unittest.skip on a subclass suppresses base-class setUp.

Base.setUp raises AssertionError via 'assert 0'; the empty @unittest.skip-decorated Test inherits it. Because the whole class is skipped, setUp and test_foo never execute, so no assertion fires — matching the docstring's claim that skipping a subclass must not call inherited setUp.

<a id="u-0aaa02bb7275"></a>
### `test_setup_skip_module.py`

`def setUpModule():` · [testing/example_scripts/unittest/test_setup_skip_module.py:L9-L10][f11]

Establishes the contrasting contract for module setup: setUpModule unconditionally executes 'assert 0' and is always called even when every test in the module is skipped, so this module is expected to error during setup despite Test being decorated with @unittest.skip and its inherited test never running.

<a id="u-290c4f124837"></a>
### `test_unittest_asynctest.py`

`class Test(asynctest.TestCase):` · [testing/example_scripts/unittest/test_unittest_asynctest.py:L14-L15][f12]

Regression example for issue #7110 using the third-party asynctest.TestCase.

Test.tearDown appends to module-level teardowns; async test_error awaits asyncio.sleep(0) then calls self.fail, failing on purpose; async test_ok just sleeps; and test_teardowns asserts len(teardowns) == 2, expecting tearDown to have run even for the failing test_error.

**Uncertainties.**

- asynctest is an external dependency; its coroutine-running semantics for test_error/test_ok are not defined by this source.
- The teardowns count assumes both async tests run before test_teardowns and that tearDown fires despite the deliberate failure.

<a id="u-2e660d9bec0a"></a>
### `test_trivial-py-string-case-tests`

`def test_upper():` · [testing/freeze/tests/test_trivial.py:L5-L6][f13]

Collects two trivial string-case sanity tests verifying built-in str methods.

test_upper asserts that calling .upper() on 'foo' yields 'FOO', and test_lower asserts that calling .lower() on 'FOO' yields 'foo'. Each test is a single assert; a failing comparison raises AssertionError and marks the test failed. The file opts out of typed-def enforcement via a mypy per-file comment and enables postponed annotations, with no other imports or state.

<a id="u-ae2d838e8b25"></a>
### `test_compare_recursive_dataclasses.py`

`class S:` · [testing/example_scripts/dataclasses/test_compare_recursive_dataclasses.py:L7-L10][f14]

Asserts nested dataclass equality through three levels.

S (int, str), C (two S), C2 (C plus S), and C3 (S, C2, two str) are all @dataclasses. test_recursive_dataclasses builds left and right whose deep fields mostly match but differ in scattered leaf values (S.a/S.b values 10 vs 20, 'two' vs 'yyy', 2 vs 3, 'left' vs 'right'), so the generated recursive __eq__ chain makes 'assert left == right' fail; the example exists to exercise how rewritten assertions display nested dataclass diffs.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/fixtures/custom_item/conftest.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/customdirectory/conftest.py
[f3]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/issue88_initial_file_multinodes/conftest.py
[f4]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/issue_519.py
[f5]: ../../../../../../eval/pytest-5989efe/testing/examples/test_issue519.py
[f6]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/fixtures/fill_fixtures/test_extend_fixture_module_class.py
[f7]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/fixtures/fill_fixtures/test_funcarg_lookup_modulelevel.py
[f8]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/fixtures/fill_fixtures/test_conftest_funcargs_only_available_in_subdir/sub2/conftest.py
[f9]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/doctest/main_py/test_normal_module.py
[f10]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/unittest/test_setup_skip.py
[f11]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/unittest/test_setup_skip_module.py
[f12]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/unittest/test_unittest_asynctest.py
[f13]: ../../../../../../eval/pytest-5989efe/testing/freeze/tests/test_trivial.py
[f14]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/dataclasses/test_compare_recursive_dataclasses.py
