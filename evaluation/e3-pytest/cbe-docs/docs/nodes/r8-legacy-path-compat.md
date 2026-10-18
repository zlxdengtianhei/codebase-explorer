# Legacy py.path Compatibility Layer

**Capability.** Re-introduces py.path-style legacy_path APIs across Config, Session, Node, FixtureRequest, Cache, TerminalReporter, and the tmpdir/testdir fixtures by monkeypatch-style binding of property getters and fixtures that wrap modern Path values, installed as early as pytest_load_initial_conftests.

Read this to understand which legacy attributes still exist and how they map to modern Path-based APIs. The Testdir facade wraps Pytester; TempdirFactory and the tmpdir fixture wrap TempPathFactory/tmp_path results.

**Depends on.**

- [Temporary Directory Management](r8-tmp-path-management.md) · model-inferred · 0 edge(s)

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Units (18)

<a id="u-ebfe3b2ae7f6"></a>
### `legacypath.py-testdir`

`class Testdir:` · [src/_pytest/legacypath.py:L41-L55][f1]

Provides a legacy-path facade over Pytester: a Testdir instance wraps an internal Pytester and forwards nearly every method to it, converting Path results to legacy_path objects where applicable, so tests written against the old py.path-style API keep working.

Construction requires _ispytest=True (checked by check_ispytest), so users cannot build it directly; the testdir fixture is the sanctioned entry point. Read-mostly properties expose underlying Pytester state: tmpdir and test_tmproot wrap the tester's paths via legacy_path; request, monkeypatch, and plugins (with a matching setter) delegate directly to Pytester attributes; getinicfg returns the SectionWrapper unchanged. File-creation helpers (makefile, makeconftest, makeini, makepyprojecttoml, makepyfile, maketxtfile, mkdir, mkpydir, copy_example) return legacy_path. makefile is the only wrapper with real logic: if ext is truthy and does not start with '.', it prepends '.' before forwarding, because pathlib suffix rules are stricter than py.path and Pytester would otherwise raise ValueError for legacy usage that historically worked; an empty-string ext is forwarded unchanged. Run/collect helpers (make_hook_recorder, chdir, finalize, getnode, getpathnode, genitems, runitem, inline_runsource, inline_genitems, inline_run, runpytest_inprocess, runpytest, parseconfig, parseconfigure, getitem, getitems, getmodulecol, collect_by_name, popen, run, runpython, runpython_c, runpytest_subprocess, spawn_pytest, spawn) forward unchanged, keeping Pytester defaults such as CLOSE_STDIN for popen/run and expect_timeout=10.0 for spawn; results and errors are exactly those of the underlying Pytester calls. finalize forwards to Pytester._finalize. __repr__ renders '<Testdir {tmpdir!r}>'; __str__ returns str(self.tmpdir).

**Notes.**

- contract: CLOSE_STDIN and TimeoutExpired are Final aliases re-exported from Pytester.
- failure: Only makefile alters arguments before forwarding; other methods propagate Pytester errors unchanged.

contract: [LegacyTestdirPlugin.testdir](r8-legacy-path-compat.md#u-17702af4fb50)

**Uncertainties.**

- Behavior of forwarded calls depends on Pytester, which is not in this batch.

<a id="u-ccf979d00d96"></a>
### `TempdirFactory`

`class TempdirFactory:` · [src/_pytest/legacypath.py:L266-L281][f1]

Backward-compatibility wrapper exposing TempPathFactory results as legacy py.path objects; the docstring prefers tmp_path_factory for new code.

Construction requires _ispytest=True (check_ispytest); __init__ stores the given TempPathFactory as _tmppath_factory. mktemp delegates to TempPathFactory.mktemp(basename, numbered) and returns legacy_path of the resolved() result, so the returned legacy path is fully resolved; getbasetemp likewise returns legacy_path of the underlying factory's resolved base temp. Errors from the inner factory propagate unchanged.

uses: [TempPathFactory](r8-tmp-path-management.md#u-bfe642169624)

<a id="u-bafc07a1c156"></a>
### `Cache_makedir`

`def Cache_makedir(self: Cache, name: str) -> LEGACY_PATH:` · [src/_pytest/legacypath.py:L323-L328][f1]

Binds as Cache.makedir: returns legacy_path(self.mkdir(name)), giving the cache's mkdir a legacy-path return type while delegating creation to the existing Cache.mkdir implementation.

<a id="u-d671fcd62f72"></a>
### `Config__getini_unknown_type`

`def Config__getini_unknown_type(self, name: str, type: str, value: str | list[str]):` · [src/_pytest/legacypath.py:L387-L395][f1]

Replaces Config._getini_unknown_type to add support for the 'pathlist' ini type in legacy form.

For type 'pathlist' it asserts self.inipath is not None (the comment admits this assert is probably not valid in all cases), uses the ini file's parent as base directory, splits the value with shlex.split when it is a string (otherwise uses the list as-is), and returns legacy_path(str(dp / x)) for each entry. For any other type it raises ValueError('unknown configuration type: {type}', value), preserving the original failure mode for genuinely unknown types.

**Notes.**

- failure: The bare assert on inipath can raise AssertionError if a pathlist option is read without an ini file; the code itself flags this as questionable.

<a id="u-bcd73294d062"></a>
### `Config_inifile`

`def Config_inifile(self: Config) -> LEGACY_PATH | None:` · [src/_pytest/legacypath.py:L367-L374][f1]

Binds as Config.inifile property getter: returns legacy_path(str(self.inipath)) when inipath is set, otherwise None; the only legacy alias here that can be absent.

<a id="u-96adf9a7d2cb"></a>
### `Config_invocation_dir`

`def Config_invocation_dir(self: Config) -> LEGACY_PATH:` · [src/_pytest/legacypath.py:L346-L354][f1]

Binds as Config.invocation_dir property getter: returns legacy_path(str(self.invocation_params.dir)), the directory pytest was invoked from, as a legacy path built from the InvocationParams Path.

<a id="u-1b4a17150813"></a>
### `Config_rootdir`

`def Config_rootdir(self: Config) -> LEGACY_PATH:` · [src/_pytest/legacypath.py:L357-L364][f1]

Binds as Config.rootdir property getter: returns legacy_path(str(self.rootpath)); docstring prefers the rootpath Path attribute.

<a id="u-96f5d3677e73"></a>
### `FixtureRequest_fspath`

`def FixtureRequest_fspath(self: FixtureRequest) -> LEGACY_PATH:` · [src/_pytest/legacypath.py:L331-L333][f1]

Binds as the deprecated FixtureRequest.fspath property getter: returns legacy_path(self.path), converting the request's Path to the legacy type.

<a id="u-681a2689e6f3"></a>
### `Node_fspath`

`def Node_fspath(self: Node) -> LEGACY_PATH:` · [src/_pytest/legacypath.py:L398-L400][f1]

Binds as the deprecated Node.fspath property getter: returns legacy_path(self.path).

<a id="u-907e75211818"></a>
### `Node_fspath_set`

`def Node_fspath_set(self: Node, value: LEGACY_PATH) -> None:` · [src/_pytest/legacypath.py:L403-L404][f1]

Binds as the Node.fspath property setter: assigns self.path = Path(value), so setting fspath actually changes the node's modern path attribute.

<a id="u-5378e93a5f60"></a>
### `Session_startdir`

`def Session_startdir(self: Session) -> LEGACY_PATH:` · [src/_pytest/legacypath.py:L377-L384][f1]

Binds as Session.startdir property getter: returns legacy_path(self.startpath), the invocation directory for the session in legacy form.

<a id="u-aefd65851114"></a>
### `TerminalReporter_startdir`

`def TerminalReporter_startdir(self: TerminalReporter) -> LEGACY_PATH:` · [src/_pytest/legacypath.py:L336-L343][f1]

Binds as TerminalReporter.startdir property getter: returns legacy_path(self.startpath), the invocation directory in legacy form; docstring prefers startpath.

<a id="u-cbe6d2a661d0"></a>
### `src/_pytest/legacypath.py:pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/legacypath.py:L439-L459][f1]

Installs the legacy tmpdir fixtures when the tmpdir plugin is active.

If config.pluginmanager.has_plugin('tmpdir') is false, nothing happens. Otherwise it creates a MonkeyPatch registered via config.add_cleanup(mp.undo), then tries to read config._tmp_path_factory: on AttributeError (tmpdir plugin blocked) it skips creating the handler; otherwise it builds TempdirFactory(tmp_path_factory, _ispytest=True) and monkeypatches it onto config as _tmpdirhandler with raising=False. In both successful-registration cases it registers LegacyTmpdirPlugin under the name 'legacypath-tmpdir'; registering twice across calls would be up to the plugin manager's behavior, not visible here.

uses: [MonkeyPatch](r6-monkeypatch-engine.md#u-3cde513da82a), [LegacyTmpdirPlugin.tmpdir_factory](r8-legacy-path-compat.md#u-9ada753816ea); calls: [TempdirFactory](r8-legacy-path-compat.md#u-ccf979d00d96)

**Uncertainties.**

- Whether has_plugin('tmpdir') can change between configure calls (repeat registration) is not determined by this file.

<a id="u-5cac1b46b993"></a>
### `src/_pytest/legacypath.py:pytest_load_initial_conftests`

`def pytest_load_initial_conftests(early_config: Config) -> None:` · [src/_pytest/legacypath.py:L407-L436][f1]

Hookimpl (tryfirst) that installs all legacy path aliases as early as possible, before conftests load.

It creates a MonkeyPatch, registers config.add_cleanup(mp.undo) so all patches are removed at config teardown, then patches class attributes: adds Cache.makedir, FixtureRequest.fspath, TerminalReporter.startdir, Config.{invocation_dir,rootdir,inifile}, Session.startdir, and Node.fspath (getter plus setter) as properties, all with raising=False so an existing attribute of the same name would be recorded and replaced rather than erroring; it also replaces Config._getini_unknown_type to support the 'pathlist' type. Errors during setattr itself (e.g. on a non-class target) would propagate, but these are all plain classes.

uses: [MonkeyPatch](r6-monkeypatch-engine.md#u-3cde513da82a); calls: [Cache_makedir](r8-legacy-path-compat.md#u-bafc07a1c156), [Config__getini_unknown_type](r8-legacy-path-compat.md#u-d671fcd62f72)

<a id="u-11f0f498abe1"></a>
### `src/_pytest/legacypath.py:pytest_plugin_registered`

`def pytest_plugin_registered(plugin: object, manager: PytestPluginManager) -> None: #…` · [src/_pytest/legacypath.py:L462-L468][f1]

Registers the legacy Testdir plugin lazily: pytester is often loaded from a conftest after pytest_configure, so this hook checks on every plugin registration whether the newly registered plugin is the 'pytester' plugin (plugin is manager.get_plugin('pytester')); only then, and only if LegacyTestdirPlugin is not already registered (manager.is_registered), does it register LegacyTestdirPlugin under the name 'legacypath-pytester'.

Non-pytester registrations do nothing.

uses: [LegacyTestdirPlugin.testdir](r8-legacy-path-compat.md#u-17702af4fb50)

<a id="u-17702af4fb50"></a>
### `LegacyTestdirPlugin.testdir`

`def testdir(pytester: Pytester) -> Testdir:` · [src/_pytest/legacypath.py:L254-L263][f1]

Static fixture adapting the pytester fixture into the legacy Testdir API.

It receives the Pytester instance and returns Testdir(pytester, _ispytest=True), the only sanctioned construction path; the class holds nothing else, and the docstring steers new code toward pytester.

calls: [legacypath.py-testdir](r8-legacy-path-compat.md#u-ebfe3b2ae7f6)

<a id="u-e3b64d7a5ecb"></a>
### `LegacyTmpdirPlugin.tmpdir`

`def tmpdir(tmp_path: Path) -> LEGACY_PATH:` · [src/_pytest/legacypath.py:L304-L320][f1]

Function-scoped fixture wrapping the tmp_path Path into a legacy_path, so the tmpdir fixture yields the same per-test directory as tmp_path but with the legacy type.

Directory creation and retention are entirely the responsibility of tmp_path; this wrapper only converts the type.

uses: [tmp_path](r8-tmp-path-management.md#u-fee0ae1b62c7)

<a id="u-9ada753816ea"></a>
### `LegacyTmpdirPlugin.tmpdir_factory`

`def tmpdir_factory(request: FixtureRequest) -> TempdirFactory:` · [src/_pytest/legacypath.py:L297-L302][f1]

Session-scoped fixture returning the TempdirFactory for the session.

It does not create the factory; it reads request.config._tmpdirhandler, which pytest_configure attaches dynamically when the tmpdir plugin is present. If that attribute is absent (plugin never configured), the fixture raises AttributeError.

contract: [src/_pytest/legacypath.py:pytest_configure](r8-legacy-path-compat.md#u-cbe6d2a661d0)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/legacypath.py
