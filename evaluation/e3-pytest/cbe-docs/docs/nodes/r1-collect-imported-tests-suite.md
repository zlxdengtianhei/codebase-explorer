# collect_imported_tests tests

**Capability.** Tests the collect_imported_tests ini option using a shared setup_files helper that builds a src package with a test class imported into a separate tests module, with src on sys.path so the import resolves.

Use this suite to check whether test classes imported from other modules are collected or ignored. The helper defines both the source and the importing test module, so collection decisions are exercised against realistic cross-module imports.

Parent: [Environment & integration tests](r1-integration-environment-tests.md)

## Units (1)

<a id="u-559b2343c7d2"></a>
### `test_collect_imported_tests-tests`

`def setup_files(pytester: Pytester) -> None:` · [testing/test_collect_imported_tests.py:L11-L40][f1]

Tests for the collect_imported_tests ini option, sharing the setup_files helper, which creates a src/foo.py defining Testament and test_testament, a tests/foo_test.py importing them into a TestDomain class, and syspathinserts src so the import resolves.

test_collect_imports_disabled sets collect_imported_tests = false via makeini, runs pytest -v tests, and asserts only TestDomain::test is collected: it checks stdout lines, the collectreport nodeids (root, class, module, dir), the single item in pytest_collection_modifyitems, and the single pytest_itemcollected call. test_collect_imports_enabled, parametrized over configure_ini False/True, shows the default behavior: without or with an explicit collect_imported_tests = true ini, the imported names Testament::test_collections and test_testament are collected alongside TestDomain::test and all three pass.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346), [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_collect_imported_tests.py
