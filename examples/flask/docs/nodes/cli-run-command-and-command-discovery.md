# CLI Run Command and Command Discovery

**Capability.** Runs the development server command and discovers commands from plugins and the user's app, loading and caching the application.

Go here for the flask run command, the startup banner and how command names are listed and looked up. It also loads plugin entry points and the cached app.

**Depends on.**

- [CLI App Import and Discovery](cli-app-import-and-discovery.md) · model-inferred · 1 inferred relation(s)
- [CLI Options and App Loading Info](cli-options-and-app-loading-info.md) · graph-confirmed · 1 edge(s) · The run command and command discovery use ScriptInfo and the CLI options to load the application.
- [Helpers, Flask Blueprint and Run](helpers-flask-blueprint-and-run.md) · graph-only · 2 edge(s)

**Depended on by.**

- [CLI Groups and Built-in Commands](cli-groups-and-built-in-commands.md) · model-inferred · 2 inferred relation(s)
- [Helpers, Flask Blueprint and Run](helpers-flask-blueprint-and-run.md) · graph-only · 1 edge(s)

Parent: [Flask CLI Implementation](flask-cli-implementation.md)

## Units (7)

<a id="u-b1014640bb4c"></a>
### `cli.py-run-command`

`def run_command( info: ScriptInfo, host: str, port: int, reload: bool, debugger: bool…` · [src/flask/cli.py:L882-L963][f1]

The 'flask run' command, which loads the app and starts Werkzeug's development server.

The decorators define options (host 127.0.0.1, port 5000, cert, key, reload, debugger, threading, extra-files, exclude-patterns); the nested 'app' function is a fallback WSGI app.
App loading: info.load_app() is tried. On any Exception: if running under the reloader, the traceback is printed immediately and a replacement WSGI app is defined that re-raises the saved error on every request (so the debugger can show it and the reloader keeps watching); otherwise the error is re-raised at once so the command fails. Then debug is read from get_debug_flag(); reload and debugger default to that value only when they are None (not passed). show_server_banner is called, then run_simple is called with the host, port, app, use_reloader, use_debugger, threaded=with_threads, ssl_context=cert, extra_files and exclude_patterns. This blocks until the server exits. An additional module-level statement (outside this function) inserts the debug option into this command's params.

calls: [ScriptInfo.load_app](cli-run-command-and-command-discovery.md#u-3b32724f1b82), [show_server_banner](cli-run-command-and-command-discovery.md#u-b8abb08fd76f), [get_debug_flag](helpers-flask-blueprint-and-run.md#u-88884dd6c1eb), [werkzeug.run_simple](../../catalog.json)

<a id="u-f08e3cd8f1fb"></a>
### `prepare_import`

`def prepare_import(path: str) -> str:` · [src/flask/cli.py:L200-L226][f1]

Turns a file path into an importable module name and ensures its root directory is on sys.path, mutating sys.path.

The path is made real (symlinks resolved); a '.py' extension is dropped, and a trailing '__init__' component is replaced by its directory. It then climbs directories, collecting names, for as long as the parent directory contains an __init__.py, so a package nested in packages yields a dotted name. The first non-package ancestor is inserted at sys.path[0] unless it is already there. Returns the dotted name. Does not check that the file exists or can be imported.

<a id="u-b8abb08fd76f"></a>
### `show_server_banner`

`def show_server_banner(debug: bool, app_import_path: str | None) -> None:` · [src/flask/cli.py:L766-L777][f1]

Prints startup banner lines for the development server unless this is the reloader's child process.

Returns silently when is_running_from_reloader() is true. Otherwise prints the app import path line if the path is not None, and prints the debug mode line if debug is not None, showing on or off. Output goes to stdout through click.echo.

<a id="u-014e5abf5c5d"></a>
### `FlaskGroup._load_plugin_commands`

`def _load_plugin_commands(self) -> None:` · [src/flask/cli.py:L600-L607][f1]

Loads CLI plugin commands from the 'flask.commands' entry-point group once per group instance.

Returns immediately if already loaded. Otherwise each entry point is loaded and added under its entry-point name. The loaded flag is set only after the loop finishes, so an exception from ep.load() propagates and the next call retries (earlier plugins would be re-added, replacing same-named commands).

<a id="u-57a22695859c"></a>
### `FlaskGroup.get_command`

`def get_command(self, ctx: click.Context, name: str) -> click.Command | None:` · [src/flask/cli.py:L609-L634][f1]

Looks up a command by name, first among built-in and plugin commands and then among commands from the user's app.

Plugins are loaded first. If the parent lookup finds a command it is returned without loading the app, so built-ins work when the app is broken. Otherwise the ScriptInfo is fetched (created if missing) and load_app is called; a NoAppException is printed in red to stderr as 'Error: ...' and None is returned (command not found). Other exceptions propagate. If no app context is active, or the active app is not the loaded app, an app context for the loaded app is registered on the Click context so later callbacks have it. Finally it returns app.cli.get_command(ctx, name), which can be None.

calls: [ScriptInfo.load_app](cli-run-command-and-command-discovery.md#u-3b32724f1b82)

<a id="u-397de5bdf862"></a>
### `FlaskGroup.list_commands`

`def list_commands(self, ctx: click.Context) -> list[str]:` · [src/flask/cli.py:L636-L655][f1]

Lists all command names: built-in, plugin, and those from the app, sorted.

Starts with the parent group's names plus plugins. It then tries to load the app and merge app.cli commands. A NoAppException prints 'Error: ...' in red to stderr without a traceback and listing continues. Any other exception prints the full traceback in red to stderr and also continues; the exception is swallowed. The result is sorted, so a failed app load yields just the built-in and plugin commands.

<a id="u-3b32724f1b82"></a>
### `ScriptInfo.load_app`

`def load_app(self) -> Flask:` · [src/flask/cli.py:L333-L372][f1]

Loads, caches and returns the Flask app, using the first available source.

If already loaded, the cached app is returned. Otherwise: (1) if create_app is set it is called with no arguments (note: the docstring of the class says it receives the script info, but the code passes nothing). (2) Else if app_import_path is set, it is split on the first ':' not followed by a backslash or slash (so Windows drive letters stay in the path) into path and optional name; prepare_import converts it to a module name, then locate_app resolves it (raising on failure). (3) Else it tries 'wsgi.py' then 'app.py' in the current directory using locate_app with raise_if_not_found=False, stopping at the first non-None result; import errors inside those modules still raise NoAppException. If no app was obtained, NoAppException with guidance on --app/FLASK_APP is raised. If set_debug_flag is true, app.debug is assigned get_debug_flag() (reading FLASK_DEBUG), which overrides any debug value the factory set. The result is cached. A create_app that returns None also ends in the NoAppException.

calls: [prepare_import](cli-run-command-and-command-discovery.md#u-f08e3cd8f1fb), [cli.py-locate-app](cli-app-import-and-discovery.md#u-cd9b790319da), [get_debug_flag](helpers-flask-blueprint-and-run.md#u-88884dd6c1eb)

**Uncertainties.**

- locate_app has three same-named definitions; the call resolves to the implementation at runtime, graph shows 3 candidates.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/cli.py
