# Plugin & Conftest Manager

**Capability.** PytestPluginManager: registers plugins (rejecting deprecated externals), parses legacy hook impl/spec marks, imports plugins from -p args, PYTEST_PLUGINS, and pytest_plugins attributes, and loads conftest.py files per directory with caching, confcutdir limits, and import-failure reporting. All plugin sources converge on register().

Use consider_* methods to load plugins from various sources; conftest lookup APIs (_getconftestmodules/_rget_with_confmod) answer which conftests apply to a path. Non-top-level pytest_plugins is rejected once the manager is configured.

**Depended on by.**

- [Cross-Session Cache Provider](r2-cache-provider.md) · model-inferred · 0 edge(s)
- [Collection & Performance Examples](r2-collection-example-scripts.md) · model-inferred · 0 edge(s)
- [CLI Entry & Bootstrap](r2-config-cli-entry.md) · graph-confirmed · 5 edge(s)
- [Ini & Option Value Access](r2-config-ini-options.md) · model-inferred · 0 edge(s)
- [Config Object & Parse Lifecycle](r2-config-lifecycle.md) · graph-confirmed · 1 edge(s) · Config's initial-conftest loading calls into the plugin manager's _try_load_conftest machinery.
- [Fixture Semantics Suite](r2-fixture-tests.md) · model-inferred · 0 edge(s)
- [Pastebin Report Plugin](r2-pastebin-plugin.md) · model-inferred · 0 edge(s)
- [Pytest Codebase](r2-pytest-root.md) · within containment · 1 edge(s)

Parent: [Configuration & Plugin Core](r2-config-core.md)

## Units (24)

<a id="u-ef8f6a30432d"></a>
### `PytestPluginManager`

`class PytestPluginManager(PluginManager):` · [src/_pytest/config/__init__.py:L391-L401][f1]

pluggy PluginManager with pytest-specific behavior: loading plugins from command line, PYTEST_PLUGINS env var, and pytest_plugins globals; startup conftest.py loading and per-directory conftest caching.

Registering a module plugin reconsiders its pytest_plugins attribute; registration fires pytest_plugin_registered historically.

<a id="u-f73ccf564a5d"></a>
### `ConftestImportFailure`

`class ConftestImportFailure(Exception):` · [src/_pytest/config/__init__.py:L114-L115][f1]

Exception carrying a conftest path plus the underlying cause; renders as '<CauseType>: <cause> (from <path>)'.

<a id="u-f1131cbb8740"></a>
### `PytestPluginManager.__init__`

`def __init__(self) -> None:` · [src/_pytest/config/__init__.py:L401-L451][f1]

Initializes conftest state (_conftest_plugins set, _dirpath2confmods cache, _confcutdir, _noconftest, skipped_plugins list), wraps _get_directory in an lru_cache(256) to avoid stat storms, adds the _pytest.hookspec hookspecs, registers self, and when PYTEST_DEBUG is set redirects tracing to a line-buffered duplicate of stderr and enables tracing.

Sets rewrite_hook to a DummyRewriteHook (replaced later by Config._consider_importhook) and _configured to False.

uses: [_get_directory](r2-config-cli-entry.md#u-6cf8be76c7ee)

<a id="u-ab6cdde49ec4"></a>
### `PytestPluginManager.register`

`def register(self, plugin: _PluggyPlugin, name: str | None = None) -> str | None:` · [src/_pytest/config/__init__.py:L492-L515][f1]

Registers a plugin, but first rejects names in DEPRECATED_EXTERNAL_PLUGINS with a PytestConfigWarning (plugins merged into core) and returns None without registering.

On successful registration, calls pytest_plugin_registered historically and, for module plugins, runs consider_module so their pytest_plugins lists are imported.

calls: [PytestPluginManager.consider_module](r2-config-plugin-manager.md#u-ebc48b4c170d)

<a id="u-979686e2d342"></a>
### `PytestPluginManager.parse_hookimpl_opts`

`def parse_hookimpl_opts( self, plugin: _PluggyPlugin, name: str ) -> HookimplOpts | N…` · [src/_pytest/config/__init__.py:L453-L478][f1]

Hook-impl option parsing: returns None for names not starting with 'pytest_' and for 'pytest_plugins' (avoiding reads of possibly non-readable attributes); otherwise defers to super(), and if that yields nothing, accepts only actual routines (inspect.isroutine), computing legacy mark options via _get_legacy_hook_marks for tryfirst/trylast/optionalhook/hookwrapper.

calls: [_get_legacy_hook_marks](r2-config-plugin-manager.md#u-2059f7b553ee)

<a id="u-e2ede93e29de"></a>
### `PytestPluginManager.parse_hookspec_opts`

`def parse_hookspec_opts(self, module_or_class, name: str) -> HookspecOpts | None:` · [src/_pytest/config/__init__.py:L480-L490][f1]

Hook-spec option parsing: returns super()'s opts when present; otherwise, for names starting with 'pytest_', derives legacy firstresult/historic opts via _get_legacy_hook_marks.

calls: [_get_legacy_hook_marks](r2-config-plugin-manager.md#u-2059f7b553ee)

<a id="u-2059f7b553ee"></a>
### `_get_legacy_hook_marks`

`def _get_legacy_hook_marks( method: Any, hook_type: str, opt_names: tuple[str, ...], …` · [src/_pytest/config/__init__.py:L359-L388][f1]

Detects legacy hook marks on a method: for each option name, a truthy attribute or a matching entry in the method's pytestmark sets opts[name]=True and queues a deprecation note; otherwise False.

If any legacy marks were found, warn_explicit_for issues the HOOK_LEGACY_MARKING deprecation at the method's location.

uses: [PytestPluginManager.parse_hookimpl_opts](r2-config-plugin-manager.md#u-979686e2d342), [PytestPluginManager.parse_hookspec_opts](r2-config-plugin-manager.md#u-e2ede93e29de)

<a id="u-a95c52f07b0b"></a>
### `_get_plugin_specs_as_list`

`def _get_plugin_specs_as_list( specs: None | types.ModuleType | str | Sequence[str], …` · [src/_pytest/config/__init__.py:L873-L891][f1]

Normalizes a plugin spec: None → []; a module type → [] (workaround for submodules named pytest_plugins); a string → comma-split list (empty string → []); a Sequence → list(specs); anything else raises UsageError.

<a id="u-a6a9f0f49e75"></a>
### `PytestPluginManager.consider_preparse`

`def consider_preparse( self, args: Sequence[str], *, exclude_only: bool = False ) -> …` · [src/_pytest/config/__init__.py:L766-L789][f1]

Scans args for '-p NAME' or '-pNAME' options and applies each via consider_pluginarg.

With exclude_only=True only 'no:' entries are applied (used when handling '-p no:X' before defaults load). A trailing '-p' with no following argument returns without error; non-string args are skipped.

calls: [PytestPluginManager.consider_pluginarg](r2-config-plugin-manager.md#u-ddc385d6feec)

<a id="u-ddc385d6feec"></a>
### `PytestPluginManager.consider_pluginarg`

`def consider_pluginarg(self, arg: str) -> None:` · [src/_pytest/config/__init__.py:L791-L812][f1]

Applies one '-p' argument.

'no:NAME' blocks the plugin (and 'pytest_NAME'); blocking an essential plugin raises UsageError 'plugin X cannot be disabled', and blocking cacheprovider additionally blocks stepwise and pytest_stepwise. Otherwise the name is unblocked (including the pytest_-prefixed form) and imported via import_plugin with entry points considered.

**Notes.**

- failure: Disabling essential_plugins (mark, main, runner, fixtures, helpconfig) raises UsageError.

calls: [PytestPluginManager.import_plugin](r2-config-plugin-manager.md#u-000f7dca0fed)

<a id="u-14b2302d3622"></a>
### `PytestPluginManager.consider_env`

`def consider_env(self) -> None:` · [src/_pytest/config/__init__.py:L820-L822][f1]

Imports plugins listed in the PYTEST_PLUGINS environment variable via _import_plugin_specs.

calls: [PytestPluginManager._import_plugin_specs](r2-config-plugin-manager.md#u-61fa46f034ad)

<a id="u-ebc48b4c170d"></a>
### `PytestPluginManager.consider_module`

`def consider_module(self, mod: types.ModuleType) -> None:` · [src/_pytest/config/__init__.py:L824-L826][f1]

Imports plugins declared in a module's pytest_plugins attribute via _import_plugin_specs.

calls: [PytestPluginManager._import_plugin_specs](r2-config-plugin-manager.md#u-61fa46f034ad)

<a id="u-a8f8f5074f70"></a>
### `PytestPluginManager.consider_conftest`

`def consider_conftest( self, conftestmodule: types.ModuleType, registration_name: str…` · [src/_pytest/config/__init__.py:L814-L818][f1]

Registers a conftest module as a plugin under the given registration name (usually the conftest's path).

calls: [PytestPluginManager.register](r2-config-plugin-manager.md#u-ab6cdde49ec4)

<a id="u-000f7dca0fed"></a>
### `PytestPluginManager.import_plugin`

`def import_plugin(self, modname: str, consider_entry_points: bool = False) -> None:` · [src/_pytest/config/__init__.py:L835-L870][f1]

Imports a plugin by module name (asserting a str was given).

Returns immediately if the name is blocked or already registered. The import spec gets a '_pytest.' prefix for builtin plugin names, and the rewrite hook marks it for assertion rewriting. With consider_entry_points, an entry point named modname in group pytest11 is loaded first and, if found, short-circuits. __import__ failure raises ImportError 'Error importing plugin "<modname>": ...' with the original traceback; a plugin raising Skipped is recorded in skipped_plugins (name, reason) instead; success registers sys.modules[importspec] under modname.

**Notes.**

- failure: ImportError is re-raised with plugin context; Skipped from the plugin is swallowed and stored.

calls: [PytestPluginManager.register](r2-config-plugin-manager.md#u-ab6cdde49ec4)

<a id="u-61fa46f034ad"></a>
### `PytestPluginManager._import_plugin_specs`

`def _import_plugin_specs( self, spec: None | types.ModuleType | str | Sequence[str] )…` · [src/_pytest/config/__init__.py:L828-L833][f1]

Normalizes a plugin spec (None, module, comma-separated string, or sequence) to a list via _get_plugin_specs_as_list and imports each entry with import_plugin.

calls: [_get_plugin_specs_as_list](r2-config-plugin-manager.md#u-a95c52f07b0b), [PytestPluginManager.import_plugin](r2-config-plugin-manager.md#u-000f7dca0fed)

<a id="u-c081401b21eb"></a>
### `PytestPluginManager._set_initial_conftests`

`def _set_initial_conftests( self, args: Sequence[str | pathlib.Path], pyargs: bool, n…` · [src/_pytest/config/__init__.py:L547-L596][f1]

Loads the initial conftests from a preparsed namespace.

Sets _confcutdir (invocation_dir/confcutdir when given, else None) and _noconftest from the namespace. For each arg, strips any '::node-id' suffix and absolutizes relative to invocation_dir; if that anchor exists (safe_exists), loads its conftests — this also prevents long option values (#10169) from being treated as anchors. If no anchor was found, loads conftests from invocation_dir itself.

calls: [PytestPluginManager._try_load_conftest](r2-config-plugin-manager.md#u-f48900696e3c)

<a id="u-f48900696e3c"></a>
### `PytestPluginManager._try_load_conftest`

`def _try_load_conftest( self, anchor: pathlib.Path, importmode: str | ImportMode, roo…` · [src/_pytest/config/__init__.py:L613-L636][f1]

Loads conftest modules for the anchor directory via _loadconftestmodules; when the anchor is a directory it additionally loads conftests for each direct subdirectory whose name starts with 'test'.

calls: [PytestPluginManager._loadconftestmodules](r2-config-plugin-manager.md#u-51c2ebc63b1f)

<a id="u-51c2ebc63b1f"></a>
### `PytestPluginManager._loadconftestmodules`

`def _loadconftestmodules( self, path: pathlib.Path, importmode: str | ImportMode, roo…` · [src/_pytest/config/__init__.py:L638-L668][f1]

Loads conftests applicable to a directory.

Returns immediately when _noconftest is set, and returns from the _dirpath2confmods cache when the directory was already processed. Otherwise walks from the directory up through all parents in reverse (topmost first), importing each existing conftest.py whose parent passes _is_in_confcutdir, and caches the resulting module list for the directory.

calls: [PytestPluginManager._importconftest](r2-config-plugin-manager.md#u-3b278d54448e)

<a id="u-3b278d54448e"></a>
### `PytestPluginManager._importconftest`

`def _importconftest( self, conftestpath: pathlib.Path, importmode: str | ImportMode, …` · [src/_pytest/config/__init__.py:L687-L738][f1]

Imports one conftest module and registers it.

If a plugin is already registered under the conftest's string path, returns it. For conftests not inside a Python package (resolve_package_path returns None), deletes the bare module name from sys.modules first to avoid returning a stale cached module. import_path failures are re-raised as ConftestImportFailure(conftestpath, cause=e). After import, _check_non_top_pytest_plugins enforces the pytest_plugins rule, the module is added to _conftest_plugins and appended to every cached dirpath list whose directory is the conftest's directory or below it — raising AssertionError if the same module object is already present there. Finally traces and registers the module via consider_conftest with the path as registration name.

**Notes.**

- failure: Import errors become ConftestImportFailure; duplicate module in cache raises AssertionError.

calls: [PytestPluginManager._check_non_top_pytest_plugins](r2-config-plugin-manager.md#u-3ee77fc8b7ad), [PytestPluginManager.consider_conftest](r2-config-plugin-manager.md#u-a8f8f5074f70)

<a id="u-c646f5477aac"></a>
### `PytestPluginManager._getconftestmodules`

`def _getconftestmodules(self, path: pathlib.Path) -> Sequence[types.ModuleType]:` · [src/_pytest/config/__init__.py:L670-L672][f1]

Cached lookup: returns the conftest module list stored for the directory of the given path, or an empty tuple when none is cached.

<a id="u-d1f437925baa"></a>
### `PytestPluginManager._rget_with_confmod`

`def _rget_with_confmod( self, name: str, path: pathlib.Path, ) -> tuple[types.ModuleT…` · [src/_pytest/config/__init__.py:L674-L685][f1]

Resolves a name against applicable conftest modules: searches the modules for the path in reverse order, returning (module, attribute) on the first module that has the attribute; raises KeyError(name) when no conftest defines it.

calls: [PytestPluginManager._getconftestmodules](r2-config-plugin-manager.md#u-c646f5477aac)

<a id="u-8030a7e104e3"></a>
### `PytestPluginManager._is_in_confcutdir`

`def _is_in_confcutdir(self, path: pathlib.Path) -> bool:` · [src/_pytest/config/__init__.py:L598-L611][f1]

Returns True when _confcutdir is None.

Otherwise a path is considered only if it is NOT a parent of _confcutdir: conftests found above the cutoff are skipped, but conftests in unrelated directory hierarchies (e.g. installed packages outside the source tree) are still loaded.

<a id="u-3ee77fc8b7ad"></a>
### `PytestPluginManager._check_non_top_pytest_plugins`

`def _check_non_top_pytest_plugins( self, mod: types.ModuleType, conftestpath: pathlib…` · [src/_pytest/config/__init__.py:L740-L759][f1]

Fails via fail(..., pytrace=False) when a conftest module defines pytest_plugins while the manager is already configured and pyargs were not used — non-top-level pytest_plugins is no longer supported because it affects the whole suite.

<a id="u-d5a1a6f1f2bc"></a>
### `PytestPluginManager.pytest_configure`

`def pytest_configure(self, config: Config) -> None:` · [src/_pytest/config/__init__.py:L526-L542][f1]

Registers the deprecated tryfirst/trylast marker descriptions as inivalue lines on the config and marks the manager as configured (self._configured = True), which later gates _check_non_top_pytest_plugins.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/__init__.py
