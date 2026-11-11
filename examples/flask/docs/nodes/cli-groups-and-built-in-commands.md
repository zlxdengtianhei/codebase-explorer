# CLI Groups and Built-in Commands

**Capability.** Defines the app-context-aware Click groups, the top-level flask group, its entry point, and the routes and shell commands.

Read this for how the flask command is assembled. It contains AppGroup, FlaskGroup, with_appcontext, main and the routes and shell commands.

**Depends on.**

- [CLI Run Command and Command Discovery](cli-run-command-and-command-discovery.md) · model-inferred · 2 inferred relation(s)

**Depended on by.**

- [Views, Wrappers, Signals and Debug Aids](views-wrappers-signals-and-debug-aids.md) · graph-only · 1 edge(s)

Parent: [Flask CLI Implementation](flask-cli-implementation.md)

## Units (10)

<a id="u-246a978f9356"></a>
### `cli.py-appgroup-command`

`def command( # type: ignore[override] self, *args: t.Any, **kwargs: t.Any ) -> t.Call…` · [src/flask/cli.py:L413-L422][f1]

Overrides the command decorator factory so commands run in an app context by default.

The 'with_appcontext' keyword is popped from kwargs (default True) before the remaining arguments go to click's own command. The returned decorator wraps the function with with_appcontext when the flag is true, and passes it unwrapped when False, then registers it through the parent class's command. The flag is evaluated when command() is called, not when the decorator is applied.

calls: [cli.py-with-appcontext](cli-groups-and-built-in-commands.md#u-34528f82677d)

<a id="u-34528f82677d"></a>
### `cli.py-with-appcontext`

`def with_appcontext(f: F) -> F:` · [src/flask/cli.py:L380-L394][f1]

Decorator that makes a Click callback run inside the script's Flask application context.

The inner decorator is a Click pass_context wrapper and the outer function returns it with the original function's metadata copied by update_wrapper.
At call time: if current_app is falsy (no context active), it loads the app via the ScriptInfo object on the Click context (ensure_object creates one if absent; NoAppException from load_app propagates) and registers app.app_context() as a context resource, which is entered and closed with the Click context, so it also covers subcommands. If an app context is already active it is reused and nothing is pushed. It then calls the wrapped function through ctx.invoke with the given arguments, returning its result.

calls: [ScriptInfo.load_app](cli-run-command-and-command-discovery.md#u-3b32724f1b82)

<a id="u-75aed86ad24c"></a>
### `AppGroup`

`class AppGroup(click.Group):` · [src/flask/cli.py:L405-L413][f1]

Click Group subclass whose command decorator automatically wraps callbacks in with_appcontext and whose group decorator defaults to AppGroup.

Distinct from FlaskGroup, which adds app discovery.

inherits: [click.Group](../../catalog.json.gz)

<a id="u-afea71329c0c"></a>
### `FlaskGroup`

`class FlaskGroup(AppGroup):` · [src/flask/cli.py:L531-L563][f1]

Top-level group for the 'flask' command.

It extends AppGroup with the default run/shell/routes commands, eager --env-file/--app/--debug/--version options, plugin commands, and commands taken from the loaded app's cli group.

<a id="u-f24b5a461e65"></a>
### `main`

`def main() -> None:` · [src/flask/cli.py:L1122-L1123][f1]

Console entry point that runs the 'flask' FlaskGroup via cli.main(), which parses sys.argv and exits the process through Click.

uses: [FlaskGroup](cli-groups-and-built-in-commands.md#u-afea71329c0c)

<a id="u-21939f98a070"></a>
### `routes_command`

`def routes_command(sort: str, all_methods: bool) -> None:` · [src/flask/cli.py:L1048-L1107][f1]

The 'flask routes' command, which prints a table of registered URL rules sorted by a chosen column.

It runs inside an app context. If the URL map has no rules it prints 'No routes were registered.' and returns. Methods HEAD and OPTIONS are omitted unless --all-methods is set. A domain column is added only if some rule has a host (when host_matching is on) or a subdomain (otherwise); its header is 'Host' or 'Subdomain'. Each row is endpoint, comma-joined sorted methods, optional domain, rule. Sorting uses the position of the --sort choice in the active column list; 'domain' is not a valid column when no domain column exists, in which case sorting raises ValueError that is swallowed and rows stay in url_map order; 'match' is not in the list either, so it also keeps matching order. Column widths are computed from the header and rows, a dashes row is inserted under the header, and each row is printed left-aligned with two spaces between columns.

<a id="u-43159ceb5ced"></a>
### `shell_command`

`def shell_command() -> None:` · [src/flask/cli.py:L999-L1045][f1]

The 'flask shell' command, which starts an interactive Python shell with the app's shell context.

Runs under with_appcontext, so the app is loaded and its context pushed first. Builds a banner with the Python version, platform, app import_name and instance_path. If PYTHONSTARTUP names an existing file it is compiled and executed into the shell namespace (exceptions propagate). Then the namespace is updated with current_app.make_shell_context(). If sys.__interactivehook__ exists, it tries to import readline and rlcompleter; on success it installs a Completer bound to the shell namespace (instead of __main__), on ImportError it skips that; the hook is then called regardless. Finally code.interact starts the REPL with the banner and namespace.

<a id="u-7efba01c0ffd"></a>
### `AppGroup.group`

`def group( # type: ignore[override] self, *args: t.Any, **kwargs: t.Any ) -> t.Callab…` · [src/flask/cli.py:L429-L437][f1]

Overrides group so nested groups are AppGroup instances by default.

Sets kwargs['cls'] to AppGroup unless the caller supplied one, then delegates to click.Group.group. Passing an explicit cls disables the default.

<a id="u-bd2447709d65"></a>
### `FlaskGroup.__init__`

`def __init__( self, add_default_commands: bool = True, create_app: t.Callable[..., Fl…` · [src/flask/cli.py:L563-L598][f1]

Builds the FlaskGroup with its eager options and default commands.

Params are the caller's 'params' (popped from extra) plus, in order, --env-file, --app, --debug, then --version if add_version_option; the order matters because env-file must run before app. context_settings is created if missing and gets auto_envvar_prefix='FLASK' via setdefault, so an explicit prefix is preserved (the caller's dict is mutated). Remaining kwargs go to the AppGroup constructor. It stores create_app, load_dotenv and set_debug_flag, adds run, shell and routes commands when add_default_commands is true, and marks plugin commands as not yet loaded.

uses: [cli.py-run-command](cli-run-command-and-command-discovery.md#u-b1014640bb4c), [shell_command](cli-groups-and-built-in-commands.md#u-43159ceb5ced), [routes_command](cli-groups-and-built-in-commands.md#u-21939f98a070)

<a id="u-2e0c84588a24"></a>
### `cli.py module code (L1107–L1121)`

`module_region` · [src/flask/cli.py:L1107-L1121][f1]

Module-level construction of the 'flask' group: a FlaskGroup named 'flask' with help text, used by main and as the console entry object.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/cli.py
