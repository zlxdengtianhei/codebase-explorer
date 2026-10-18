# CLI Entry & Bootstrap

**Capability.** Turns process arguments into a parsed Config via main/_prepareconfig/get_config, exposes canonical ExitCode semantics, and provides argparse validators and traceback filtering for bootstrap error paths.

Call main()/console_main() to run pytest in-process or as a console script; get_plugin_manager() serves tooling that wants to hook pytest. ExitCode is the exit-status contract.

**Depends on.**

- [Config Object & Parse Lifecycle](r2-config-lifecycle.md) · graph-confirmed · 4 edge(s) · main and _prepareconfig drive Config parsing and ensure unconfigure at shutdown.
- [Plugin & Conftest Manager](r2-config-plugin-manager.md) · graph-confirmed · 5 edge(s)

**Depended on by.**

- [Frozen Executable Tooling](r2-freeze-tooling.md) · model-inferred · 0 edge(s)
- [Argcomplete Shell Completion](r2-shell-completion.md) · model-inferred · 0 edge(s)

Parent: [Configuration & Plugin Core](r2-config-core.md)

## Units (11)

<a id="u-b420848647de"></a>
### `console_main`

`def console_main() -> int:` · [src/_pytest/config/__init__.py:L194-L209][f1]

CLI entry point: calls main(), flushes stdout, returns the code; on BrokenPipeError redirects stdout to os.devnull so the exit-time flush cannot raise again, and returns 1.

calls: [main](r2-config-cli-entry.md#u-1425330076ac)

<a id="u-1425330076ac"></a>
### `main`

`def main( args: list[str] | os.PathLike[str] | None = None, plugins: Sequence[str | _…` · [src/_pytest/config/__init__.py:L139-L191][f1]

Runs pytest in-process and returns an exit code.

Sets PYTEST_VERSION in os.environ for the run, restoring or removing it in finally. Builds a config via _prepareconfig; on ConftestImportFailure prints a red 'ImportError while loading conftest' line plus the cause's traceback filtered by filter_traceback_for_conftest_import_failure (short-style repr if any entries remain, else exconly()) and returns USAGE_ERROR. On success invokes pytest_cmdline_main, returning ExitCode(ret) when coercion succeeds, else the raw int; _ensure_unconfigure runs in finally. A UsageError prints each e.args entry as a red 'ERROR: <msg>' line and returns USAGE_ERROR.

**Notes.**

- side_effect: os.environ['PYTEST_VERSION'] is set for the run and restored afterwards.

calls: [_prepareconfig](r2-config-cli-entry.md#u-97cf326e917b), [Config._ensure_unconfigure](r2-config-lifecycle.md#u-219ad4a29791), [filter_traceback_for_conftest_import_failure](r2-config-cli-entry.md#u-0a39a43322c9)

**Uncertainties.**

- What pytest_cmdline_main does depends on registered plugins, not visible here.

<a id="u-97cf326e917b"></a>
### `_prepareconfig`

`def _prepareconfig( args: list[str] | os.PathLike[str] | None = None, plugins: Sequen…` · [src/_pytest/config/__init__.py:L319-L348][f1]

Normalizes args (None → sys.argv[1:]; PathLike → [os.fspath]; otherwise non-list → TypeError), builds an initial config via get_config, registers/considers the given plugins (strings via consider_pluginarg, objects via register), and produces the final Config by firing pytest_cmdline_parse.

On any BaseException the initial config's _ensure_unconfigure runs before re-raising.

calls: [get_config](r2-config-cli-entry.md#u-d9b901196c45), [PytestPluginManager.consider_pluginarg](r2-config-plugin-manager.md#u-ddc385d6feec), [PytestPluginManager.register](r2-config-plugin-manager.md#u-ab6cdde49ec4), [Config._ensure_unconfigure](r2-config-lifecycle.md#u-219ad4a29791)

<a id="u-d9b901196c45"></a>
### `get_config`

`def get_config( args: list[str] | None = None, plugins: Sequence[str | _PluggyPlugin]…` · [src/_pytest/config/__init__.py:L283-L305][f1]

Builds a fresh Config with a new PytestPluginManager; InvocationParams defaults to args=(), plugins=None, dir=cwd.

If args is not None, applies only '-p no:...' preparse entries, then imports each default_plugins spec. Returns the config before argument parsing.

calls: [PytestPluginManager.consider_preparse](r2-config-plugin-manager.md#u-a6a9f0f49e75), [PytestPluginManager.import_plugin](r2-config-plugin-manager.md#u-000f7dca0fed); uses: [Config](r2-config-lifecycle.md#u-ee2b09815a27)

<a id="u-b712859a5d9e"></a>
### `get_plugin_manager`

`def get_plugin_manager() -> PytestPluginManager:` · [src/_pytest/config/__init__.py:L308-L316][f1]

Returns the pluginmanager of a default-args Config from get_config(), for tooling that hooks into pytest.

calls: [get_config](r2-config-cli-entry.md#u-d9b901196c45)

<a id="u-6cd9646f81c7"></a>
### `ExitCode`

`class ExitCode(enum.IntEnum):` · [src/_pytest/config/__init__.py:L91-L111][f1]

Enumerates the canonical pytest exit codes as an IntEnum: OK=0, TESTS_FAILED=1, INTERRUPTED=2, INTERNAL_ERROR=3, USAGE_ERROR=4, NO_TESTS_COLLECTED=5; usable as ints.

<a id="u-bdc66f3b44e6"></a>
### `cmdline`

`class cmdline: # compatibility namespace` · [src/_pytest/config/__init__.py:L212-L213][f1]

Compatibility namespace exposing main as a staticmethod for the historical pytest.cmdline.main entry point.

<a id="u-aae81f7f8eea"></a>
### `directory_arg`

`def directory_arg(path: str, optname: str) -> str:` · [src/_pytest/config/__init__.py:L227-L235][f1]

Argparse type validator: raises UsageError naming the option if the path is not an existing directory, otherwise returns it.

<a id="u-5ce849c0ef2b"></a>
### `filename_arg`

`def filename_arg(path: str, optname: str) -> str:` · [src/_pytest/config/__init__.py:L216-L224][f1]

Argparse type validator: raises UsageError naming the option if the path is an existing directory, otherwise returns the path.

<a id="u-6cf8be76c7ee"></a>
### `_get_directory`

`def _get_directory(path: pathlib.Path) -> pathlib.Path:` · [src/_pytest/config/__init__.py:L351-L356][f1]

Returns path.parent when path is a file, otherwise the path itself.

<a id="u-0a39a43322c9"></a>
### `filter_traceback_for_conftest_import_failure`

`def filter_traceback_for_conftest_import_failure( entry: _pytest._code.TracebackEntry…` · [src/_pytest/config/__init__.py:L128-L136][f1]

Predicate for conftest import-failure tracebacks: an entry is kept only if filter_traceback accepts it and no os.sep-separated component of its path is 'importlib', since import_path uses importlib.

uses: [main](r2-config-cli-entry.md#u-1425330076ac)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/__init__.py
