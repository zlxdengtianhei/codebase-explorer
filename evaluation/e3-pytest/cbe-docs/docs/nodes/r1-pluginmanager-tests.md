# Plugin manager test suite

**Capability.** Tests PytestPluginManager across registration/discovery, early '-p' bootstrapping with blocking, and runtime plugin-config-hook interactions, plus an isolated pytestpm fixture and guards for marker listings and plugin import-error messages.

Use the child suites by concern: discovery and registration APIs, preparse blocking, or configure/hook lifecycle. The shared pytestpm fixture gives each test an isolated manager. The module_residual unit is imports only and carries no behavior.

**Children.**

- [Plugin registration & discovery tests](r1-pm-registration-discovery.md) `r1-pm-registration-discovery` · 12 unit(s)
- [Plugin bootstrapping tests](r1-pm-bootstrapping.md) `r1-pm-bootstrapping` · 6 unit(s)
- [Plugin-config-hook interaction tests](r1-pm-interactions.md) `r1-pm-interactions` · 11 unit(s)

**Depended on by.**

- [Plugin bootstrapping tests](r1-pm-bootstrapping.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-pm-bootstrapping ` → ` r1-pluginmanager-tests `) · Bootstrapping tests use the shared pytestpm fixture infrastructure of the plugin-manager suite.
- [Plugin-config-hook interaction tests](r1-pm-interactions.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-pm-interactions ` → ` r1-pluginmanager-tests `)
- [Plugin registration & discovery tests](r1-pm-registration-discovery.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-pm-registration-discovery ` → ` r1-pluginmanager-tests `)

Parent: [pytest codebase](r1-pytest-codebase.md)

## Units (4)

<a id="u-e648d8b4d873"></a>
### `pytestpm`

`def pytestpm() -> PytestPluginManager:` · [testing/test_pluginmanager.py:L20-L22][f1]

Fixture returning a fresh PytestPluginManager, giving tests an isolated plugin manager independent of ambient test configuration.

<a id="u-d00fa86ee438"></a>
### `test_default_markers`

`def test_default_markers(pytester: Pytester) -> None:` · [testing/test_pluginmanager.py:L233-L235][f1]

Runs pytest --markers and asserts the marker listing advertises tryfirst/trylast with 'first'/'last' descriptions, guarding the built-in hook marker options.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-7fe2b82dee63"></a>
### `test_importplugin_error_message`

`def test_importplugin_error_message( pytester: Pytester, pytestpm: PytestPluginManage…` · [testing/test_pluginmanager.py:L238-L260][f1]

Guards import-error reporting for plugins (#375, #1998): importing a module 'qwe' whose import raises ImportError('Not possible to import: ☺') must not hide the original error.

It adds pytester.path to sys.path, writes qwe.py that raises at import, calls pytestpm.import_plugin('qwe') and expects ImportError whose message ends with 'Error importing plugin "qwe": Not possible to import: ☺' and whose traceback's last entry still mentions test_traceback.

calls: [PytestPluginManager.import_plugin](r2-config-plugin-manager.md#u-000f7dca0fed), [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

<a id="u-38c534f14542"></a>
### `test_pluginmanager.py module code (L1–L19)`

`module_region` · [testing/test_pluginmanager.py:L1-L19][f1]

Imports only (os, shutil, sys, types and pytest internals); no behavior of its own.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_pluginmanager.py
