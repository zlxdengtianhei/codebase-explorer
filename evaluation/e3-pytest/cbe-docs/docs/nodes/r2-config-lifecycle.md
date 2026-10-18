# Config Object & Parse Lifecycle

**Capability.** The Config object itself: construction, one-shot argument parsing, rootdir/inifile determination, initial conftest loading, pythonpath handling, configure/unconfigure teardown, and nodeid/terminal-writer conveniences. Grouped because these all manage the mutable state of a single invocation.

Read here to understand Config.parse and when cleanup callbacks fire. rootpath/inipath are valid only after parsing; _ensure_unconfigure guarantees single teardown; fromdictargs supports subprocess-based re-invocations.

**Depends on.**

- [Ini & Option Value Access](r2-config-ini-options.md) · graph-confirmed · 6 edge(s) · Config._preparse and Config.parse read ini values through getini before resolving rootpath/inipath.
- [Plugin & Conftest Manager](r2-config-plugin-manager.md) · graph-confirmed · 1 edge(s) · Config's initial-conftest loading calls into the plugin manager's _try_load_conftest machinery.
- [Config Warnings & Assertion-Rewrite Setup](r2-config-warnings-rewrite.md) · graph-confirmed · 6 edge(s)

**Depended on by.**

- [CLI Entry & Bootstrap](r2-config-cli-entry.md) · graph-confirmed · 4 edge(s) · main and _prepareconfig drive Config parsing and ensure unconfigure at shutdown.

Parent: [Configuration & Plugin Core](r2-config-core.md)

## Units (24)

<a id="u-ee2b09815a27"></a>
### `Config`

`class Config:` · [src/_pytest/config/__init__.py:L967-L979][f1]

Provides access to configuration values, the pluginmanager, and plugin hooks for one pytest invocation.

Holds the argparse Namespace (option), the Parser, InvocationParams (frozen dataclass of args/plugins/dir with a custom __init__ coercing args to tuple), the ArgsSource enum (ARGS, INVOCATION_DIR with legacy INCOVATION_DIR alias, TESTPATHS), a Stash (deprecated alias _store), and verbosity constants VERBOSITY_ASSERTIONS/VERBOSITY_TEST_CASES with _VERBOSITY_INI_DEFAULT='auto'.

<a id="u-1445ff816cd7"></a>
### `Config.__init__`

`def __init__( self, pluginmanager: PytestPluginManager, *, invocation_params: Invocat…` · [src/_pytest/config/__init__.py:L1031-L1090][f1]

Constructs a Config: defaults invocation_params to args=(), plugins=None, dir=cwd; creates an empty argparse.Namespace for option, a Parser with usage for FILE_OR_DIR args whose processopt callback is self._processopt, an empty Stash (alias _store), trace from the pluginmanager's root trace, and wraps the pluginmanager hook relay in a PathAwareHookProxy as self.hook.

Registers self as the 'pytestconfig' plugin, sets _configured False, fires pytest_addoption historically (so option declarations accumulate across plugins), and initializes args=[] with args_source ARGS.

calls: [Config._processopt](r2-config-lifecycle.md#u-99cb2df68f66)

**Uncertainties.**

- PathAwareHookProxy wrapping behavior lives in config/compat.py, not visible here.

<a id="u-99cb2df68f66"></a>
### `Config._processopt`

`def _processopt(self, opt: Argument) -> None:` · [src/_pytest/config/__init__.py:L1206-L1212][f1]

Parser callback for each registered Argument: maps every short and long option string to the option's dest in _opt2dest, and seeds self.option.<dest> with the option default when the attribute does not exist yet.

<a id="u-7ea45dbe606d"></a>
### `Config.parse`

`def parse(self, args: list[str], addopts: bool = True) -> None: # Parse given cmdline…` · [src/_pytest/config/__init__.py:L1519-L1542][f1]

Parses command-line args into the config exactly once (asserts self.args still empty).

Fires pytest_addhooks historically, runs _preparse, sets parser after_preparse, then parses the option values and decides the final args/args_source via _decide_args with warn=True. A PrintHelp exception (raised by --help during parsing) is swallowed here.

calls: [Config._preparse](r2-config-lifecycle.md#u-9478fabcf228), [Config._decide_args](r2-config-lifecycle.md#u-c338996c7903)

<a id="u-0a7500cac2dd"></a>
### `Config.pytest_cmdline_parse`

`def pytest_cmdline_parse( self, pluginmanager: PytestPluginManager, args: list[str] )…` · [src/_pytest/config/__init__.py:L1142-L1165][f1]

Hook implementation producing this config: parses args into self; on UsageError it still honors --version (showversion via helpconfig) or --help/-h (minimal parser help plus a note) before re-raising, since helpconfig's normal handler does not run on errors.

calls: [Config.parse](r2-config-lifecycle.md#u-7ea45dbe606d)

<a id="u-9478fabcf228"></a>
### `Config._preparse`

`def _preparse(self, args: list[str], addopts: bool = True) -> None:` · [src/_pytest/config/__init__.py:L1385-L1443][f1]

Preparsing pipeline.

With addopts: prepends validated PYTEST_ADDOPTS env args (shlex-split) and, after _initini, prepends validated addopts ini args. Parses known args (checking minversion via _checkversion), installs the assertion importhook, configures pythonpath, considers '-p' args, and unless autoload is disabled (env or option) loads pytest11 entry points; then considers PYTEST_PLUGINS. Re-parses known args to fold in plugin-added options, validates required_plugins, warns about skipped plugins, defaults confcutdir to the inifile's parent or rootpath, and fires pytest_load_initial_conftests. A ConftestImportFailure is downgraded to a PytestConfigWarning only when --help or --version was requested; otherwise it propagates.

**Notes.**

- failure: ConftestImportFailure propagates unless help/version suppressed it to a config-time warning.

calls: [Config._initini](r2-config-lifecycle.md#u-cc80392726c9), [Config._consider_importhook](r2-config-warnings-rewrite.md#u-444636576272)

<a id="u-cc80392726c9"></a>
### `Config._initini`

`def _initini(self, args: Sequence[str]) -> None:` · [src/_pytest/config/__init__.py:L1241-L1267][f1]

Determines rootdir/inifile: parses known and unknown args against a copy of option, then calls determine_setup with inifilename, file_or_dir plus unknown args, rootdir argument, and invocation dir.

Stores _rootpath, _inipath, inicfg, records them in parser extra_info, registers the core ini options (addopts, minversion, pythonpath, required_plugins), and captures -o/--override-ini values.

calls: [determine_setup](r5-config-findpaths.md#u-4c6e4cc79376)

**Uncertainties.**

- rootdir/inifile resolution rules live in findpaths.py.

<a id="u-c338996c7903"></a>
### `Config._decide_args`

`def _decide_args( self, *, args: list[str], pyargs: bool, testpaths: list[str], invoc…` · [src/_pytest/config/__init__.py:L1340-L1383][f1]

Chooses the initial test arguments and their source.

Explicit args win (ARGS). Otherwise, when invocation_dir equals rootpath: TESTPATHS is used — with pyargs the testpaths entries verbatim, else each path is glob-expanded recursively; if testpaths were configured but matched nothing and warn is set, issues a PytestConfigWarning suggesting adjusting testpaths. When invocation_dir differs from rootpath the result starts empty. An empty result falls back to the invocation directory string with source INVOCATION_DIR. Return is guaranteed non-empty.

calls: [Config.issue_config_time_warning](r2-config-warnings-rewrite.md#u-fbb29f3a2355)

<a id="u-e506fe1bb4ef"></a>
### `Config._validate_args`

`def _validate_args(self, args: list[str], via: str) -> list[str]:` · [src/_pytest/config/__init__.py:L1328-L1338][f1]

Parses args against a copy of option purely for validation, with the parser's _config_source_hint set to via (removed in finally), so config-sourced args report their origin in errors; returns args unchanged.

<a id="u-f25a5abad90c"></a>
### `Config._checkversion`

`def _checkversion(self) -> None:` · [src/_pytest/config/__init__.py:L1454-L1470][f1]

Enforces the minversion ini value: a non-string minversion raises UsageError 'minversion must be a single value'; a version newer than the running pytest raises UsageError naming both versions (compared with packaging Version).

<a id="u-16d48817bb53"></a>
### `Config.inipath`

`def inipath(self) -> pathlib.Path | None:` · [src/_pytest/config/__init__.py:L1102-L1108][f1]

Property returning the config file path (or None) determined during _initini.

<a id="u-664a10fe4440"></a>
### `Config.rootpath`

`def rootpath(self) -> pathlib.Path:` · [src/_pytest/config/__init__.py:L1092-L1100][f1]

Property returning the rootdir path set during parsing (_initini); reading before parse would raise AttributeError.

<a id="u-a226606b0680"></a>
### `Config.cwd_relative_nodeid`

`def cwd_relative_nodeid(self, nodeid: str) -> str: # nodeid's are relative to the roo…` · [src/_pytest/config/__init__.py:L1185-L1194][f1]

Re-renders a nodeid relative to the invocation directory: only when invocation dir differs from rootpath, the path part before the first '::' is resolved against rootpath and rewritten via bestrelpath; parameters after '::' are preserved.

<a id="u-762ec43ea2be"></a>
### `Config.notify_exception`

`def notify_exception( self, excinfo: ExceptionInfo[BaseException], option: argparse.N…` · [src/_pytest/config/__init__.py:L1167-L1183][f1]

Reports an internal error.

Traceback style is 'long' when option.fulltrace is set, else 'native'; locals are shown when option.showlocals is set (defaults False when option is None). Fires pytest_internalerror; only if no hook implementation returned a truthy result does it print each line of the repr prefixed 'INTERNALERROR> ' to stderr and flush.

calls: [ExceptionInfo.getrepr](r1-code-exception-info.md#u-adfe45903a4e)

<a id="u-4ef12a354446"></a>
### `Config.get_terminal_writer`

`def get_terminal_writer(self) -> TerminalWriter:` · [src/_pytest/config/__init__.py:L1135-L1140][f1]

Returns the TerminalReporter's writer; asserts the 'terminalreporter' plugin is registered (it is a default plugin).

<a id="u-86ce20c8bc34"></a>
### `create_terminal_writer`

`def create_terminal_writer( config: Config, file: TextIO | None = None ) -> TerminalW…` · [src/_pytest/config/__init__.py:L1876-L1897][f1]

Builds a TerminalWriter for the given optional file and applies config: option.color 'yes' forces hasmarkup True, 'no' forces False; option.code_highlight 'yes'/'no' force code_highlight True/False.

Other values leave defaults.

<a id="u-6ed386e09426"></a>
### `Config.add_cleanup`

`def add_cleanup(self, func: Callable[[], None]) -> None:` · [src/_pytest/config/__init__.py:L1110-L1114][f1]

Registers func as an exit-stack callback run when the config is discarded (normally with pytest_unconfigure).

uses: [Config._ensure_unconfigure](r2-config-lifecycle.md#u-219ad4a29791)

<a id="u-dd4c3d492d72"></a>
### `Config._do_configure`

`def _do_configure(self) -> None:` · [src/_pytest/config/__init__.py:L1116-L1119][f1]

Asserts the config is not yet configured, sets _configured, and calls the pytest_configure hook historically (so late-registered plugins still receive it).

<a id="u-219ad4a29791"></a>
### `Config._ensure_unconfigure`

`def _ensure_unconfigure(self) -> None:` · [src/_pytest/config/__init__.py:L1121-L1133][f1]

Tears the config down exactly once.

When configured: clears the flag, calls pytest_unconfigure, then clears pytest_configure's call history (nested in try/finally so history is cleared even if the hook raises). The cleanup stack is always closed in a finally, then replaced with a fresh ExitStack, so repeated calls are safe no-ops after teardown.

<a id="u-f5dfcb619e85"></a>
### `Config.fromdictargs`

`def fromdictargs(cls, option_dict, args) -> Config:` · [src/_pytest/config/__init__.py:L1196-L1204][f1]

Subprocess-friendly constructor: builds a config via get_config(args), merges option_dict into the option namespace, parses args without addopts handling, then considers each entry of config.option.plugins via consider_pluginarg.

calls: [get_config](r2-config-cli-entry.md#u-d9b901196c45), [PytestPluginManager.consider_pluginarg](r2-config-plugin-manager.md#u-ddc385d6feec)

<a id="u-cb774678a646"></a>
### `Config.pytest_collection`

`def pytest_collection(self) -> Generator[None, object, object]: # Validate invalid in…` · [src/_pytest/config/__init__.py:L1445-L1452][f1]

Wrapper hook around collection that validates config options in its finally, after collection, so ini keys registered by late-loaded conftests are recognized.

calls: [Config._validate_config_options](r2-config-warnings-rewrite.md#u-3aecd6f5d66b)

<a id="u-96170c457fea"></a>
### `Config.pytest_load_initial_conftests`

`def pytest_load_initial_conftests(self, early_config: Config) -> None: # We haven't f…` · [src/_pytest/config/__init__.py:L1214-L1239][f1]

trylast hook pre-running conftest discovery before full parsing: derives args via _decide_args from known_args_namespace.file_or_dir (warn=False), then hands them to _set_initial_conftests with pyargs/noconftest/confcutdir/importmode from the namespace and consider_namespace_packages from the ini.

The real args decision is redone in parse().

calls: [Config._decide_args](r2-config-lifecycle.md#u-c338996c7903)

<a id="u-3b3f93b9a060"></a>
### `Config._configure_python_path`

`def _configure_python_path(self) -> None: # pythonpath = a b will set sys.path to…` · [src/_pytest/config/__init__.py:L1316-L1320][f1]

Inserts each pythonpath ini entry at the front of sys.path in reverse order (so listed order is preserved) and registers _unconfigure_python_path as a cleanup.

calls: [Config._unconfigure_python_path](r2-config-lifecycle.md#u-78778243f1e9)

<a id="u-78778243f1e9"></a>
### `Config._unconfigure_python_path`

`def _unconfigure_python_path(self) -> None:` · [src/_pytest/config/__init__.py:L1322-L1326][f1]

Removes each pythonpath ini entry from sys.path when still present, restoring the original path ordering for other entries.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/__init__.py
