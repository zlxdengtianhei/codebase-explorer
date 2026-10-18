# Plugin registration & discovery tests

**Capability.** Covers module registration (with duplicate-registration errors), canonical imports, consider_module/consider_env/consider_conftest, PYTEST_PLUGINS handling end to end, plugin skipping, import_plugin naming (prefix stripping, dotted names, reuse of sys.modules entries), and loud failure on unimportable conftest-declared plugins.

Use these tests to understand how plugins enter the manager from modules, env vars, and conftests. Failure-to-import cases assert raised ImportErrors rather than silent skips. The class group and its method units share one concern and should be read together.

**Depends on.**

- [Plugin manager test suite](r1-pluginmanager-tests.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-pm-registration-discovery ` → ` r1-pluginmanager-tests `)

Parent: [Plugin manager test suite](r1-pluginmanager-tests.md)

## Units (12)

<a id="u-d8cd3c35245d"></a>
### `TestPytestPluginManager`

`class TestPytestPluginManager:` · [testing/test_pluginmanager.py:L263-L264][f1]

Groups tests of PytestPluginManager registration and plugin discovery: module registration, canonical imports, consider_module/consider_env/consider_conftest, env-var-driven plugin loading, and import_plugin naming.

Members are documented individually in this batch.

<a id="u-52d8a406b872"></a>
### `TestPytestPluginManager.test_register_imported_modules`

`def test_register_imported_modules(self) -> None:` · [testing/test_pluginmanager.py:L264-L274][f1]

Registers a freshly created module 'x.y.pytest_hello' on a new PytestPluginManager and asserts is_registered, membership in get_plugins, and that get_plugins() is unchanged after two duplicate register attempts, each of which must raise ValueError (registering an already-registered plugin is an error).

<a id="u-22cf725647bb"></a>
### `TestPytestPluginManager.test_canonical_import`

`def test_canonical_import(self, monkeypatch):` · [testing/test_pluginmanager.py:L276-L282][f1]

Inserts a module named 'pytest_xyz' into sys.modules via monkeypatch, then import_plugin('pytest_xyz') must reuse the already-imported module: get_plugin('pytest_xyz') is that module and it is registered.

calls: [MonkeyPatch.setitem](r6-monkeypatch-engine.md#u-0494ec708f24)

<a id="u-29ac1e28536a"></a>
### `TestPytestPluginManager.test_consider_module`

`def test_consider_module( self, pytester: Pytester, pytestpm: PytestPluginManager ) -…` · [testing/test_pluginmanager.py:L284-L298][f1]

consider_module reads a module's 'pytest_plugins' variable and imports the named plugins.

It puts pytest_p1/pytest_p2 on the path as empty files, builds a temp module whose pytest_plugins is ['pytest_p1', 'pytest_p2'], calls consider_module, and asserts both were imported and registered under those names.

calls: [PytestPluginManager.consider_module](r2-config-plugin-manager.md#u-ebc48b4c170d), [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

<a id="u-b90de15cf89e"></a>
### `TestPytestPluginManager.test_consider_module_import_module`

`def test_consider_module_import_module( self, pytester: Pytester, _config_for_test: C…` · [testing/test_pluginmanager.py:L300-L316][f1]

Uses the test config's plugin manager with a hook recorder attached.

A module x declares pytest_plugins='pytest_a'; a pytest_a.py file is created and its directory added to sys.path. The first consider_module fires pytest_plugin_registered exactly once with plugin.__name__ == 'pytest_a'; calling consider_module again must not re-register, as the recorder still shows only one call.

calls: [PytestPluginManager.consider_module](r2-config-plugin-manager.md#u-ebc48b4c170d), [pytester-core](r6-pytester-core.md#u-f18f003077f1)

<a id="u-7239fdf74de0"></a>
### `TestPytestPluginManager.test_consider_env_fails_to_import`

`def test_consider_env_fails_to_import( self, monkeypatch: MonkeyPatch, pytestpm: Pyte…` · [testing/test_pluginmanager.py:L318-L323][f1]

Sets PYTEST_PLUGINS to a nonexistent module name and asserts consider_env() raises ImportError rather than silently skipping the unimportable plugin.

calls: [PytestPluginManager.consider_env](r2-config-plugin-manager.md#u-14b2302d3622)

<a id="u-981b8088362d"></a>
### `TestPytestPluginManager.test_plugin_skip`

`def test_plugin_skip(self, pytester: Pytester, monkeypatch: MonkeyPatch) -> None:` · [testing/test_pluginmanager.py:L325-L339][f1]

Module-level plugin skipping.

Creates skipping1.py that calls pytest.skip(..., allow_module_level=True), copies it to skipping2.py, sets PYTEST_PLUGINS=skipping2, and runs pytest with -p skipping1. Both plugin loads are skipped: the run returns ExitCode.NO_TESTS_COLLECTED and stdout reports '*skipped plugin*skipping1*hello*' and '*skipped plugin*skipping2*hello*'.

calls: [MonkeyPatch.setenv](r6-monkeypatch-engine.md#u-3bcdaba77d61), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-f36a2933ae38"></a>
### `TestPytestPluginManager.test_consider_env_plugin_instantiation`

`def test_consider_env_plugin_instantiation( self, pytester: Pytester, monkeypatch: Mo…` · [testing/test_pluginmanager.py:L341-L357][f1]

With an empty xy123.py on the path and PYTEST_PLUGINS=xy123 in os.environ, consider_env() registers exactly one new plugin retrievable as get_plugin('xy123').

A second consider_env() call adds nothing: plugin count stays constant, showing env plugins are registered once.

calls: [PytestPluginManager.consider_env](r2-config-plugin-manager.md#u-14b2302d3622), [MonkeyPatch.setitem](r6-monkeypatch-engine.md#u-0494ec708f24)

<a id="u-75dc1a062c01"></a>
### `TestPytestPluginManager.test_pluginmanager_ENV_startup`

`def test_pluginmanager_ENV_startup( self, pytester: Pytester, monkeypatch: MonkeyPatc…` · [testing/test_pluginmanager.py:L359-L374][f1]

End-to-end check of PYTEST_PLUGINS at startup: with pytest_x500.py on the path (syspathinsert=True) and the env var set, a test that looks up pytestconfig.pluginmanager.get_plugin('pytest_x500') passes, confirming env-declared plugins are available to test bodies.

calls: [MonkeyPatch.setenv](r6-monkeypatch-engine.md#u-3bcdaba77d61), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-31d12f2be689"></a>
### `TestPytestPluginManager.test_import_plugin_importname`

`def test_import_plugin_importname( self, pytester: Pytester, pytestpm: PytestPluginMa…` · [testing/test_pluginmanager.py:L376-L394][f1]

import_plugin with a 'pytest_'-prefixed name strips the prefix when locating the module.

Importing unknown dotted names 'qweqwex.y' and 'pytest_qweqwx.y' raises ImportError. With pytest_hello.py created and on the path, import_plugin('pytest_hello') registers it; a second import adds no plugins, returns the identical plugin object, and its __name__ ends with 'pytest_hello'.

calls: [PytestPluginManager.import_plugin](r2-config-plugin-manager.md#u-000f7dca0fed), [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

<a id="u-ca6cf023080e"></a>
### `TestPytestPluginManager.test_import_plugin_dotted_name`

`def test_import_plugin_dotted_name( self, pytester: Pytester, pytestpm: PytestPluginM…` · [testing/test_pluginmanager.py:L396-L408][f1]

import_plugin accepts dotted names: after creating pkg/plug.py (x=3) inside a package directory and importing 'pkg.plug', get_plugin('pkg.plug') exposes attribute x == 3.

Unknown dotted names still raise ImportError.

calls: [PytestPluginManager.import_plugin](r2-config-plugin-manager.md#u-000f7dca0fed), [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

<a id="u-793f56830568"></a>
### `TestPytestPluginManager.test_consider_conftest_deps`

`def test_consider_conftest_deps( self, pytester: Pytester, pytestpm: PytestPluginMana…` · [testing/test_pluginmanager.py:L410-L421][f1]

Imports a conftest module whose content is pytest_plugins='xyz' (xyz not importable) and asserts consider_conftest raises ImportError, showing conftest-declared plugin dependencies are resolved at conftest registration time and fail loudly when unimportable.

calls: [PytestPluginManager.consider_conftest](r2-config-plugin-manager.md#u-a8f8f5074f70), [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_pluginmanager.py
