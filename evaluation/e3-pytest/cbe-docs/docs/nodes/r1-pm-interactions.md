# Plugin-config-hook interaction tests

**Capability.** Covers runtime interactions: conftest-provided hook implementations through declared hookspecs, error reporting for hookspec-less add_hookspecs, addoption timing (post-initialize and during hooks), pytest_configure lifecycle timing including late registration and unconfigure, Windows conftest path case sensitivity, hook proxies, and hook tracing indent handling.

Use these tests to pin when plugins are configured and how hooks and options interleave with the config lifecycle. test_configure and test_hook_tracing are split into setup/verification segments that share local state. Failures here usually indicate ordering problems rather than API misuse.

**Depends on.**

- [Plugin manager test suite](r1-pluginmanager-tests.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-pm-interactions ` → ` r1-pluginmanager-tests `)

Parent: [Plugin manager test suite](r1-pluginmanager-tests.md)

## Units (11)

<a id="u-35dec5718100"></a>
### `TestPytestPluginInteractions`

`class TestPytestPluginInteractions:` · [testing/test_pluginmanager.py:L25-L26][f1]

Groups tests of plugin-manager interactions: hookspecs from conftest, option registration timing, the configure lifecycle, conftest path handling, hook tracing, hook proxies, and hooks used inside pytest_addoption.

Members are documented individually in this batch.

<a id="u-a89354512624"></a>
### `TestPytestPluginInteractions.test_addhooks_conftestplugin`

`def test_addhooks_conftestplugin( self, pytester: Pytester, _config_for_test: Config …` · [testing/test_pluginmanager.py:L26-L57][f1]

Verifies a conftest-provided hook implementation runs through declared hookspecs.

Creates a newhooks module defining pytest_myhook and a conftest whose pytest_addhooks registers those hookspecs and whose pytest_myhook returns xyz+1. It replays the historic pytest_addhooks hook with the test config's plugin manager, imports the conftest via _importconftest (prepend mode), then expects config.hook.pytest_myhook(xyz=10) to return [11].

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

<a id="u-c0fa7947871d"></a>
### `TestPytestPluginInteractions.test_addhooks_nohooks`

`def test_addhooks_nohooks(self, pytester: Pytester) -> None:` · [testing/test_pluginmanager.py:L59-L69][f1]

Checks error reporting when add_hookspecs is given an object with no hook implementations: the conftest calls add_hookspecs(sys); runpytest must exit nonzero and stderr must match '*did not find*sys*'.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-ca210285f629"></a>
### `TestPytestPluginInteractions.test_do_option_postinitialize`

`def test_do_option_postinitialize(self, pytester: Pytester) -> None:` · [testing/test_pluginmanager.py:L71-L87][f1]

Shows a conftest pytest_addoption still takes effect after config initialization.

parseconfigure() first yields a config lacking test123; importing a conftest that adds --test123 (store_true, default True) via _importconftest then makes config.option.test123 truthy.

calls: [pytester-parseconfig](r6-pytester-run.md#u-4da6110e81d7)

<a id="u-0a89e563be23"></a>
### `TestPytestPluginInteractions.test_configure`

`def test_configure(self, pytester: Pytester) -> None:` · [testing/test_pluginmanager.py:L89-L93][f1]

Verifies pytest_configure timing across the configure lifecycle using a local class A whose pytest_configure appends itself to a list.

After parseconfig(), registering A before configure appends nothing; _do_configure() configures already-registered plugins (values reaches 1). Registering a second A after configuration immediately calls pytest_configure (values reaches 2, distinct instances). After _ensure_unconfigure(), registering a third A adds nothing: late registration in the unconfigured phase is not configured.

calls: [pytester-parseconfig](r6-pytester-run.md#u-4da6110e81d7), [Config._do_configure](r2-config-lifecycle.md#u-dd4c3d492d72), [Config._ensure_unconfigure](r2-config-lifecycle.md#u-219ad4a29791)

<a id="u-893b75f05ed3"></a>
### `testing/test_pluginmanager.py:TestPytestPluginInteractions.test_configure`

`def test_configure(self, pytester: Pytester) -> None:` · [testing/test_pluginmanager.py:L95-L107][f1]

Second segment of test_configure continuing after the local class A: it registers a second A instance, which is configured immediately because the config was already configured, asserts the two recorded instances differ, then after _ensure_unconfigure() shows a newly registered A is left unconfigured (values stays at 2).

Behavior is covered in full by the test_configure unit.

group: [TestPytestPluginInteractions.test_configure](r1-pm-interactions.md#u-0a89e563be23)

<a id="u-83b9555106ca"></a>
### `TestPytestPluginInteractions.test_conftestpath_case_sensitivity`

`def test_conftestpath_case_sensitivity(self, pytester: Pytester) -> None:` · [testing/test_pluginmanager.py:L109-L141][f1]

Windows-only regression test for issue #9765, skipped elsewhere via skipif on sys.platform.

After creating tests/conftest.py it imports tests/conftest.py and then TESTS/conftest.py via _importconftest (prepend mode) against the same parsed config. Each import registers a plugin keyed by its str(path): get_plugin(str(conftest)) is the first module and get_plugin(str(conftest_upper_case)) the second. Because paths are not normalized, the two modules are distinct objects even though they refer to the same file on a case-insensitive filesystem.

**Notes.**

- condition: Skipped on non-Windows platforms because it depends on a case-insensitive filesystem.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-parseconfig](r6-pytester-run.md#u-4da6110e81d7)

<a id="u-babebc03c7b6"></a>
### `TestPytestPluginInteractions.test_hook_tracing`

`def test_hook_tracing(self, _config_for_test: Config) -> None:` · [testing/test_pluginmanager.py:L143-L147][f1]

Setup segment of test_hook_tracing: binds pytestpm to _config_for_test.pluginmanager and declares the local api1/api2 classes used by the tracing assertions.

Covered in full by the test_hook_tracing unit.

group: [testing/test_pluginmanager.py:TestPytestPluginInteractions.test_hook_tracing](r1-pm-interactions.md#u-8a1652406869)

<a id="u-8a1652406869"></a>
### `testing/test_pluginmanager.py:TestPytestPluginInteractions.test_hook_tracing`

`def test_hook_tracing(self, _config_for_test: Config) -> None:` · [testing/test_pluginmanager.py:L154-L174][f1]

Verifies hook tracing indent handling and cleanup.

It wires the trace root writer to a list, enables tracing, and registers api1 whose pytest_plugin_registered records the trace indent at call time. After registration the trace indent is restored to its pre-call value, the log contains at least two entries, the first mentioning pytest_plugin_registered and the second containing 'finish'. Registering api2, whose hook raises ValueError, propagates the exception (asserted with pytest.raises) yet the trace indent is still restored, and the recorded indent inside the hook was greater than the base indent. Tracing is undone in a finally block.

calls: [PytestPluginManager.register](r2-config-plugin-manager.md#u-ab6cdde49ec4)

<a id="u-c62d10d0a94f"></a>
### `TestPytestPluginInteractions.test_hook_proxy`

`def test_hook_proxy(self, pytester: Pytester) -> None:` · [testing/test_pluginmanager.py:L176-L200][f1]

Regression test for gethookproxy (#2016).

It parses a config, builds a Session, and creates tests/conftest.py plus tests/subdir/conftest.py. After importing only the first conftest, session.gethookproxy(pytester.path/'tests') returns a proxy; after importing the second, a new call returns a different proxy object, showing the proxy is invalidated by newly registered conftest plugins rather than cached forever.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-parseconfig](r6-pytester-run.md#u-4da6110e81d7)

<a id="u-7308e0c79be2"></a>
### `TestPytestPluginInteractions.test_hook_with_addoption`

`def test_hook_with_addoption(self, pytester: Pytester) -> None:` · [testing/test_pluginmanager.py:L202-L230][f1]

Checks that hooks may be called during pytest_addoption.

It defines a newhooks module with a firstresult hookspec pytest_default_value, a myplugin whose pytest_addoption calls pluginmanager.hook.pytest_default_value() and uses the result as the default of --config, and a conftest (loaded via pytest_plugins) implementing the hook returning 'default_value'. Running pytest --help must print --config with that computed default in the help text.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_pluginmanager.py
