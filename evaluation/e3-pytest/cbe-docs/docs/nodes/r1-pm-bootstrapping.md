# Plugin bootstrapping tests

**Capability.** Tests early '-p' preparse handling: argument forms, 'no:name' blocking so blocked plugins are never registered, unregistration of already-registered blocked plugins, dependent-plugin unregistration (stepwise following cacheprovider), and re-allowing a blocked plugin with a later '-p name'.

Use these tests for the semantics of blocking and unblocking plugins before normal startup. Blocking is overridable by a subsequent explicit load directive. The stepwise/cacheprovider case shows dependent plugins are dropped with their provider.

**Depends on.**

- [Plugin manager test suite](r1-pluginmanager-tests.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-pm-bootstrapping ` → ` r1-pluginmanager-tests `) · Bootstrapping tests use the shared pytestpm fixture infrastructure of the plugin-manager suite.

Parent: [Plugin manager test suite](r1-pluginmanager-tests.md)

## Units (6)

<a id="u-d40a7b710b06"></a>
### `TestPytestPluginManagerBootstrapping`

`class TestPytestPluginManagerBootstrapping:` · [testing/test_pluginmanager.py:L424-L425][f1]

Groups tests of early '-p' preparse handling: argument forms, blocking registration with 'no:' names, unregistration of already-registered plugins, cacheprovider/stepwise coupling, and reuse of blocked plugins.

Members are documented individually in this batch.

<a id="u-c705b11ee2a5"></a>
### `TestPytestPluginManagerBootstrapping.test_preparse_args`

`def test_preparse_args(self, pytestpm: PytestPluginManager) -> None:` · [testing/test_pluginmanager.py:L425-L440][f1]

Covers consider_preparse argument forms.

['xyz', '-p', 'hello123'] raises ImportError for the unimportable plugin; the attached '-p hello123' form works; '-phello123' (no space, #3532) parses to 'hello123' as shown by the error message containing '"hello123"'; '-pno:hello123' (a block directive) is accepted silently; a trailing '-p' with no argument is tolerated; and '-p no:main' raises UsageError matching '^plugin main cannot be disabled$'.

calls: [PytestPluginManager.consider_preparse](r2-config-plugin-manager.md#u-a6a9f0f49e75)

<a id="u-f3892e634f08"></a>
### `TestPytestPluginManagerBootstrapping.test_plugin_prevent_register`

`def test_plugin_prevent_register(self, pytestpm: PytestPluginManager) -> None:` · [testing/test_pluginmanager.py:L442-L448][f1]

After consider_preparse(['xyz', '-p', 'no:abc']), registering a plugin under the blocked name 'abc' is refused: get_plugins() is unchanged and 42 is absent, showing blocked names are never registered.

calls: [PytestPluginManager.consider_preparse](r2-config-plugin-manager.md#u-a6a9f0f49e75), [PytestPluginManager.register](r2-config-plugin-manager.md#u-ab6cdde49ec4)

<a id="u-a560eff71ca4"></a>
### `TestPytestPluginManagerBootstrapping.test_plugin_prevent_register_unregistered_already_registered`

`def test_plugin_prevent_register_unregistered_already_registered( self, pytestpm: Pyt…` · [testing/test_pluginmanager.py:L450-L458][f1]

Registers 42 under name 'abc' first, confirms it is present, then runs consider_preparse(['xyz', '-p', 'no:abc']): the already-registered plugin is removed, since 42 is absent afterwards.

calls: [PytestPluginManager.consider_preparse](r2-config-plugin-manager.md#u-a6a9f0f49e75), [PytestPluginManager.register](r2-config-plugin-manager.md#u-ab6cdde49ec4)

<a id="u-b6a660d118b9"></a>
### `TestPytestPluginManagerBootstrapping.test_plugin_prevent_register_stepwise_on_cacheprovider_unregister`

`def test_plugin_prevent_register_stepwise_on_cacheprovider_unregister( self, pytestpm…` · [testing/test_pluginmanager.py:L460-L476][f1]

From PR #4304: blocking cacheprovider via '-p no:cacheprovider' after registering plugins named cacheprovider (42) and stepwise (43) unregisters both — stepwise is dropped as a dependent of cacheprovider.

Both 42 and 43 must be absent from get_plugins() afterwards.

calls: [PytestPluginManager.consider_preparse](r2-config-plugin-manager.md#u-a6a9f0f49e75), [PytestPluginManager.register](r2-config-plugin-manager.md#u-ab6cdde49ec4)

<a id="u-49c5cdad73e2"></a>
### `TestPytestPluginManagerBootstrapping.test_blocked_plugin_can_be_used`

`def test_blocked_plugin_can_be_used(self, pytestpm: PytestPluginManager) -> None:` · [testing/test_pluginmanager.py:L478-L483][f1]

A later explicit '-p abc' after '-p no:abc' re-allows the plugin: has_plugin('abc') is true, and neither 'abc' nor 'pytest_abc' is considered blocked, showing a block is overridable by a subsequent load directive.

calls: [PytestPluginManager.consider_preparse](r2-config-plugin-manager.md#u-a6a9f0f49e75)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_pluginmanager.py
