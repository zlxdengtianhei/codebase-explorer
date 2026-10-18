# Python Collection Tests

**Capability.** testing/python/collect.py: end-to-end tests of Module, Class, and Function collection behavior, module import/import-mode semantics, sorting, and conftest-driven collection customization.

Use these suites as behavioral reference for collection edge cases (import errors, __init__/__new__ warnings, --import-mode=append). They exercise the py-module-class-package and py-function-item subtrees through pytester runs.

**Depends on.**

- [Hook Specifications](r7-core-hook-contracts.md) · model-inferred · 0 edge(s)
- [Module, Class, and Package Collectors](r7-py-module-class-package.md) · model-inferred · 0 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-only · 94 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 69 edge(s)

Parent: [pytest's Own Test Suites](r7-internal-test-suites.md)

## Units (7)

<a id="u-83e0b596aac7"></a>
### `collect.py module code (L1–L19)`

`module_region` · [testing/python/collect.py:L1-L19][f1]

Module-level imports and typing directives only; no executable test logic in lines 1-19.

<a id="u-307ca2850770"></a>
### `collect.py-test-module`

`def test_failing_import(self, pytester: Pytester) -> None:` · [testing/python/collect.py:L21-L23][f1]

Groups the TestModule suite: tests that module-level collection reports import failures, syntax errors, duplicate-basename mismatches, sys.path insert-vs-append semantics (test_import_prepend_append asserts --import-mode=append imports x456 from root2 while default prepend fails the assertion inside the test module), invalid module file names, plugin-import errors surfaced via modcol.obj, and import-error tracebacks whose verbosity (parametrized 0/1/2) controls whether _pytest internals appear in stdout; each test drives pytester with a source snippet or files and asserts outcome counts or fnmatch output patterns.

<a id="u-e8b49c967b02"></a>
### `collect.py-test-class`

`def test_class_with_init_warning(self, pytester: Pytester) -> None:` · [testing/python/collect.py:L147-L161][f1]

Groups the TestClass suite: class collection edge cases.

Classes with __init__ or __new__ are skipped with a PytestCollectionWarning naming the class and source file; namedtuple classes (which define __new__) trigger the same warning; plain subclass of object collects 0 items; staticmethods are collected and run (2 passed), while classmethod setup_class/teardown_class work normally; an instance whose class defines __getattr__ yields no collected items (test_issue1035_obj_has_getattr checks modcol.collect() is empty); properties and custom instance descriptors are never discovered even when the descriptor would raise SystemExit if evaluated (exit code NO_TESTS_COLLECTED); and abstract classes are not collected unless all abstract methods are overridden, so TestBase and TestPartial yield nothing while TestConcrete's test runs (1 passed, exit OK).

<a id="u-4273fc6093f4"></a>
### `collect.py-test-function`

`def test_getmodulecollector(self, pytester: Pytester) -> None:` · [testing/python/collect.py:L331-L335][f1]

Groups the TestFunction suite for Function-item behavior.

make_function builds a pytest.Function under a fresh Session with a FixtureManager via parseconfigure, used by equality/id tests. Parametrize cases cover: empty parameter set yields a skipped item; a single-tuple argname unwraps to one argument; parameter values whose __eq__ raises are still collected (fulltrace run passes); non-hashable dict values parametrize both directly and via indirect fixtures; a parametrize argument overrides a same-named fixture (single, parametrized, and as an indirect dependency whose overridden fixture replaces the fixture chain so fix3 is never instantiated); per-parameter marks merge with function marks (test_parametrize_with_mark asserts baz/bar only on the pytest.param item); empty-string argument values produce [-]/[ -] style ids; callspec items compare unequal. Skips/xfails attached to individual parameters behave per mark condition (skipif True skips, False fails, xfail True xfails, xfail-True passing test xpasses, xfail-False passes). originalname stays the un-parametrized function name across parametrized items, and function names containing brackets are escaped in output ids. test_pyfunc_call registers two hook plugins where MyPlugin2 returns True so config.hook.pytest_pyfunc_call succeeds despite MyPlugin1 raising ValueError. test_multiple_parametrize and test_issue751 verify nested parametrize id ordering like test1[2-0] and test1[a-c].

**Uncertainties.**

- Whether MyPlugin1's ValueError is swallowed or reported depends on hook firstresult semantics not shown here; the test asserts no exception propagates from the call.

<a id="u-c7b561cce0c0"></a>
### `collect.py-test-sorting`

`def test_check_equality(self, pytester: Pytester) -> None:` · [testing/python/collect.py:L788-L814][f1]

Groups the TestSorting suite.

test_check_equality verifies two collections of the same module function yield equal, same-hash Function items, unequal to other functions, the module collector, and arbitrary objects like 3 or lists. test_allow_sane_sorting_for_decorators checks a decorator setting g.place_as = f keeps the item at the decorated function's source position (names collected as test_b then test_a despite assignment order). test_ordered_by_definition_order checks methods keep definition order even when one class method aliases another class's method (Test2 keeps its own foo before bar).

<a id="u-b5e6c95e4f1c"></a>
### `collect.py-test-conftest-customization`

`def test_pytest_pycollect_module(self, pytester: Pytester) -> None:` · [testing/python/collect.py:L870-L884][f1]

Groups the TestConftestCustomization suite for collection hooks.

pytest_pycollect_makemodule in conftest can substitute a custom Module subclass for a named file (test_xyz shows <MyModule*xyz>); a wrapper hookimpl around pytest_pycollect_makemodule can inject attributes onto mod.obj consumed by the test module; a wrapper around pytest_pycollect_makeitem can tag collected functions with attributes visible through request.node; pytest_pycollect_makeitem can replace collection of a specific name with a custom Function subclass (MyFunction*some collected). test_issue2369 registers a meta-path finder in conftest so files with a .narf extension import as Python modules, using runpytest_subprocess to isolate the sys.meta_path mutation. test_early_ignored_attributes confirms builtin attributes are skipped before python_classes/python_functions wildcards apply, so only test_real is collected and no PytestCollectionWarning fires.

<a id="u-9fc0e8ab9c00"></a>
### `collect.py-module-functions`

`def test_setup_only_available_in_subdir(pytester: Pytester) -> None:` · [testing/python/collect.py:L1030-L1064][f1]

Groups module-level test functions.

Collection/traceback areas: test_modulecol_roundtrip re-collects a module via perform_collect on its nodeid; TestTracebackCutting tests pytest.skip exception traceback hiding (Python 3.11+ checks co_qualname), fixture-setup error tracebacks (default mode hides separators, --fulltrace shows them), import-error tracebacks hiding earlier source lines unless --fulltrace, filtered tracebacks for generated code (path is str, filter_traceback rejects it) and for a source file deleted after the exception (filter_traceback still accepts it). Report info: custom Function.reportinfo overrides item.location; default function reportinfo is (item.path str, 0, function name); class reportinfo points at the module path with the class name/lineno; classes with hostile __getattr__/__class_getattr__ returning non-int still collect and report. Discovery: custom python_files/classes/functions patterns (check_*, Check, check and _test) are honored. Ordering/dedup: duplicate directory arguments collect once by default, twice with --keep-duplicates; unorderable duplicate class names do not raise TypeError; non-function callables warn but do not crash collection; injected class attributes during pytest_generate_tests avoid dictionary-changed-size errors; non-ASCII syntax errors format without decoding failures; --fulltrace shows assert failures during collection; package recursion, __init__.py given as argument (collects only the init module), nested package layout from cwd or explicit args, python_files=*.py package ordering, and a full hierarchy tree (including --keep-duplicates overlap when both a subdir and its parent are passed, in either argument order) all collect as asserted.

**Uncertainties.**

- Exact traceback-entry counts in test_traceback_argsetup (0 vs >3 separators) depend on terminal reporter formatting not in this file.
- Whether os.chdir in test_package_with_modules is restored between runs is not shown; later tests could be affected.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/python/collect.py
