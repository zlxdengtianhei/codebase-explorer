# Hook and plugin deprecation tests

**Capability.** Warnings for hookimpl/hookspec declared via function attributes, py.path.local hook signatures (hookproxy/hookimpl pathlib tests), removed external plugins recognized with a clear warning, deprecated fspath node-constructor argument, and check_ispytest private-API enforcement.

Use this subtree to see the precise warning types and counts pinned for each legacy hooking mechanism.

**Depends on.**

- [Fixture-mark deprecation tests](r4-deprecation-fixture-tests.md) · model-inferred · 0 edge(s)

Parent: [Deprecation tests](r4-deprecated-tests.md)

## Units (7)

<a id="u-93d88e5a09f2"></a>
### `test_hookspec_via_function_attributes_are_deprecated`

`def test_hookspec_via_function_attributes_are_deprecated():` · [testing/deprecated_test.py:L25-L30][f1]

Adds hookspecs to a PytestPluginManager from a class whose pytest_bad_hook carries a historic=False function attribute instead of the @pytest.hookspec(historic=False) decorator.

Inside pytest.warns(PytestDeprecationWarning, match 'Please use the pytest\.hookspec\(historic=False\) decorator') it asserts exactly one record, whose lineno equals the function's co_firstlineno and whose filename is this file, pinning the deprecation warning's location.

<a id="u-5091c952390d"></a>
### `test_external_plugins_integrated`

`def test_external_plugins_integrated(pytester: Pytester, plugin) -> None:` · [testing/deprecated_test.py:L15-L22][f1]

Parametrized over sorted deprecated.DEPRECATED_EXTERNAL_PLUGINS with filterwarnings 'default', this test writes an empty module file named after the plugin, inserts the temp dir into sys.path, and asserts inside pytest.warns(PytestConfigWarning) that parsing a config with -p <plugin> warns — verifying the removed external plugins are recognized and rejected with a clear message.

<a id="u-1465f85a8499"></a>
### `test_hookimpl_via_function_attributes_are_deprecated`

`def test_hookimpl_via_function_attributes_are_deprecated():` · [testing/deprecated_test.py:L49-L54][f1]

Registers on a PytestPluginManager a plugin whose pytest_runtest_call carries a tryfirst=True function attribute instead of the @pytest.hookimpl(tryfirst=True) decorator.

Inside pytest.warns(PytestDeprecationWarning, match 'Please use the pytest.hookimpl\(tryfirst=True\)') it asserts exactly one record, whose lineno equals the method's co_firstlineno and whose filename is this file.

<a id="u-65464fd14cb5"></a>
### `test_hookproxy_warnings_for_pathlib`

`def test_hookproxy_warnings_for_pathlib(tmp_path, hooktype, request):` · [testing/deprecated_test.py:L95-L123][f1]

Parametrized over hooktype 'hook' (config.hook) and 'ihook' (node.ihook); for both it calls pytest_ignore_collect passing both the legacy path and pathlib collection_path, and inside pytest.warns(PytestDeprecationWarning) asserts exactly one record whose lineno falls between two sys._getframe() markers in this file.

It then calls the hook with only collection_path and expects no warning. Finally, passing a collection_path entirely different from path is an outright error: the call must raise ValueError matching 'path.*fspath.*need to be equal', even while the deprecation warning is still expected inside.

<a id="u-60ca3921a77c"></a>
### `test_hookimpl_warnings_for_pathlib`

`def test_hookimpl_warnings_for_pathlib() -> None:` · [testing/deprecated_test.py:L126-L127][f1]

Registers a local plugin whose five hook implementations (pytest_ignore_collect, pytest_collect_file, pytest_pycollect_makemodule take path; pytest_report_header, pytest_report_collectionfinish take startdir; all raise NotImplementedError) use the deprecated py.path.local-style signatures.

Inside pytest.warns(PytestRemovedIn9Warning, match 'py\.path\.local.* argument is deprecated') it asserts exactly five warnings are collected, one per deprecated hookimpl.

<a id="u-b1ac13e802d0"></a>
### `test_node_ctor_fspath_argument_is_deprecated`

`def test_node_ctor_fspath_argument_is_deprecated(pytester: Pytester) -> None:` · [testing/deprecated_test.py:L152-L155][f1]

Builds a module column via pytester.getmodulecol, defines a MyFile(pytest.File) whose collect raises NotImplementedError, and asserts that MyFile.from_parent with a legacy fspath argument warns PytestDeprecationWarning matching the escaped message 'The (fspath: py.path.local) argument to MyFile is deprecated.', pinning the deprecated node-constructor path.

<a id="u-9cfa797e0654"></a>
### `test_private_is_deprecated`

`def test_private_is_deprecated() -> None:` · [testing/deprecated_test.py:L81-L82][f1]

Defines a class whose __init__ calls deprecated.check_ispytest on its _ispytest keyword flag.

Constructing it without the flag must warn PytestDeprecationWarning 'private pytest class or function'; constructing it with _ispytest=True must not warn, verifying the internal-use escape hatch.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/deprecated_test.py
