# Fixture Behavior Examples

**Capability.** Example scripts pinning fixture semantics: conftest fixture overriding in a subdirectory package, recursive-fixture detection, request-name shadowing, introspection, misspelled-fixture errors, and unittest interop with parametrized fixtures and skipped classes.

Use these to see the minimal source that triggers each documented fixture outcome; suites run them and assert the resulting messages or outcomes.

**Depends on.**

- [Python Test Collection and Execution](r7-python-collection.md) · model-inferred · 0 edge(s)

Parent: [Example Scripts and Packaging Harness](r7-example-scripts.md)

## Units (8)

<a id="u-73e0a8364a50"></a>
### `spam`

`def spam():` · [testing/example_scripts/fixtures/fill_fixtures/test_extend_fixture_conftest_conftest/conftest.py:L7-L9][f1]

Base fixture returning the string 'spam'.

It defines the package-outer fixture that pkg/conftest.py later overrides by requesting the same name, so this function runs first whenever the wider conftest scope is in effect.

<a id="u-7d5630de6ad7"></a>
### `testing/example_scripts/fixtures/fill_fixtures/test_extend_fixture_conftest_conftest/pkg/conftest.py:spam`

`def spam(spam):` · [testing/example_scripts/fixtures/fill_fixtures/test_extend_fixture_conftest_conftest/pkg/conftest.py:L7-L9][f2]

Overrides the parent conftest's spam fixture within pkg: by declaring a parameter also named spam, the inner fixture receives the outer value ('spam') and returns spam * 2, i.e. 'spamspam', for tests collected under pkg such as test_spam.

contract: [spam](r7-fixture-examples.md#u-73e0a8364a50)

<a id="u-67e720e01a22"></a>
### `test_detect_recursive_dependency_error.py`

`def fix1(fix2):` · [testing/example_scripts/fixtures/fill_fixtures/test_detect_recursive_dependency_error.py:L7-L9][f3]

Documents pytest's behavior on mutually recursive fixtures: fix1 requests fix2 and fix2 requests fix1, and test(fix1) triggers the cycle.

Neither fixture body runs successfully; pytest is expected to report the recursive dependency as an error rather than hang or loop. The file contains no self-recovery; the value 1 in each body is never reached if dependency resolution fails first.

**Uncertainties.**

- The exact error type/message raised for the cycle is not shown in this source; the example exists for the runner's diagnostics.

<a id="u-95e073f041ff"></a>
### `test_fixture_named_request.py`

`def request():` · [testing/example_scripts/fixtures/test_fixture_named_request.py:L7-L9][f4]

Shows that a user fixture may shadow the special 'request' fixture name.

The fixture request is declared with no body (returns None) and nothing consumes it; test takes no arguments, so collection and execution are expected to succeed despite the name collision.

<a id="u-dd6e078d7211"></a>
### `test_funcarg_basic.py`

`def some(request):` · [testing/example_scripts/fixtures/fill_fixtures/test_funcarg_basic.py:L7-L9][f5]

Illustrates introspection via the request object.

Fixture some returns request.function.__name__, i.e. the name of the test function being run ('test_func'), while other returns the constant 42; test_func(some, other) accepts both but does nothing with them, so the example only demonstrates that both fixtures resolve without error.

<a id="u-dbacb45a5993"></a>
### `test_funcarg_lookupfails.py`

`def xyzsomething(request):` · [testing/example_scripts/fixtures/fill_fixtures/test_funcarg_lookupfails.py:L7-L9][f6]

Documents fixture-name misspelling.

Fixture xyzsomething exists, but test_func(some) requests the nonexistent name 'some'; fixture resolution therefore raises a FixtureLookupError when collecting/running test_func, and xyzsomething is never instantiated because nothing depends on it.

**Uncertainties.**

- The failure occurs at fixture setup; whether it surfaces as an error or collection failure depends on runner internals not in this file.

<a id="u-3442a41fba71"></a>
### `test_parametrized_fixture_error_message.py`

`def two(request):` · [testing/example_scripts/unittest/test_parametrized_fixture_error_message.py:L9-L11][f7]

Sets up a parametrized fixture applied to a unittest.TestCase class.

Fixture two is parametrized with params=[1, 2] and returns request.param; TestSomethingElse opts in via @pytest.mark.usefixtures("two") while test_two takes no arguments, so the fixture runs twice (once per parameter) even though the test never names it, exercising the error/skip reporting path for parametrized fixtures on unittest classes.

**Uncertainties.**

- The file neither fails nor skips on its own; the 'error message' behavior named in the filename depends on runner-side reporting absent here.

<a id="u-f55647b0d92f"></a>
### `test_setup_skip_class.py`

`class Base(unittest.TestCase):` · [testing/example_scripts/unittest/test_setup_skip_class.py:L9-L10][f8]

Same skip-suppression contract for the class-level hook: Base.setUpClass is a classmethod whose 'assert 0' would fail if invoked; Test, decorated with @unittest.skip, inherits it, and skipping the class must prevent setUpClass (as well as test_foo) from running, so the module passes without any assertion firing.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/fixtures/fill_fixtures/test_extend_fixture_conftest_conftest/conftest.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/fixtures/fill_fixtures/test_extend_fixture_conftest_conftest/pkg/conftest.py
[f3]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/fixtures/fill_fixtures/test_detect_recursive_dependency_error.py
[f4]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/fixtures/test_fixture_named_request.py
[f5]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/fixtures/fill_fixtures/test_funcarg_basic.py
[f6]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/fixtures/fill_fixtures/test_funcarg_lookupfails.py
[f7]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/unittest/test_parametrized_fixture_error_message.py
[f8]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/unittest/test_setup_skip_class.py
