# App Discovery and Loading

**Capability.** Resolves a Flask app from an explicit import string, a factory callable, or the best candidate in a module, with ScriptInfo caching results and NoAppException signaling failure.

Read this when debugging why --app fails to import or which app is auto-detected. ScriptInfo is the cache point all commands go through; prepare_import converts paths to importable module names.

**Depends on.**

- [Environment and Path Helpers](r2-environment-helpers.md) · graph-only · 2 edge(s)

**Depended on by.**

- [FlaskGroup and App Context Commands](r2-cli-command-group.md) · graph-confirmed · 3 edge(s) · FlaskGroup resolves the target app through ScriptInfo, the shared discovery and caching point.
- [Run, Shell, and Routes Commands](r2-cli-server-commands.md) · graph-confirmed · 1 edge(s)
- [CLI Test Suite](r2-cli-tests.md) · model-inferred · 0 edge(s)

Parent: [Command-Line Interface](r2-cli-system.md)

## Units (8)

<a id="u-68b618421e9e"></a>
### `NoAppException`

`class NoAppException(click.UsageError):` · [src/flask/cli.py:L37-L38][f1]

Usage error signaling that a Flask application could not be found or loaded; it subclasses click.UsageError so CLI dispatch renders it as a user-facing message rather than a traceback.

<a id="u-e0ddadae27ac"></a>
### `ScriptInfo`

`class ScriptInfo:` · [src/flask/cli.py:L293-L305][f1]

Holds everything needed to locate and cache the Flask application for a CLI run: an optional import path, an optional create_app callable, an arbitrary data dict, and the debug/dotenv flag settings.

Its __init__ stores those fields, resolves load_dotenv_defaults through get_load_dotenv (allowing an environment override), and initializes the _loaded_app cache to None. load_app returns the cached app if present; otherwise it calls create_app if set, or splits app_import_path on a colon into path and name, prepares the import, and calls locate_app; with no import path it probes 'wsgi.py' then 'app.py' with raise_if_not_found=False and stops at the first hit. If no app results, NoAppException tells the user to use --app, FLASK_APP, or a wsgi.py/app.py file. When set_debug_flag is set, app.debug is assigned through the descriptor from get_debug_flag so related flags repopulate; the app is cached and returned.

calls: [src/flask/cli.py:locate_app (2)](r2-cli-app-discovery.md#u-4c152a2459fc), [prepare_import](r2-cli-app-discovery.md#u-f08e3cd8f1fb); raises: [NoAppException](r2-cli-app-discovery.md#u-68b618421e9e)

**Uncertainties.**

- create_app is invoked with no arguments; whether it may receive the ScriptInfo depends on code outside this batch.

<a id="u-8597d7387a6f"></a>
### `_called_with_wrong_args`

`def _called_with_wrong_args(f: t.Callable[..., Flask]) -> bool:` · [src/flask/cli.py:L94-L117][f1]

Decides whether the active TypeError came from calling the given function with missing arguments rather than from code inside it.

It walks the current traceback; if a frame's code is the function's own code, the function was entered and it returns False. If the traceback ends without reaching the function, the call never entered it and it returns True. A finally block deletes the local traceback reference to break a reference cycle.

uses: [find_best_app](r2-cli-app-discovery.md#u-6522d181aa3f)

<a id="u-81ef5022e21a"></a>
### `find_app_by_string`

`def find_app_by_string(module: ModuleType, app_name: str) -> Flask:` · [src/flask/cli.py:L120-L197][f1]

Resolves an explicit 'module:name' or 'module:name(args)' specification.

The name is parsed with ast.parse in eval mode: SyntaxError, or an expression that is neither a Name nor a Call, raises NoAppException. A Call node must have a bare Name function; positional and keyword arguments are parsed with ast.literal_eval and ValueError (non-literals) raises NoAppException showing the original expression. The attribute is fetched from the module, with AttributeError converted to NoAppException. If the attribute is a function it is called with the parsed args/kwargs; a TypeError propagates unless _called_with_wrong_args says the call itself failed, in which case NoAppException is raised. The result must be a Flask instance or NoAppException is raised.

raises: [NoAppException](r2-cli-app-discovery.md#u-68b618421e9e); calls: [_called_with_wrong_args](r2-cli-app-discovery.md#u-8597d7387a6f)

<a id="u-6522d181aa3f"></a>
### `find_best_app`

`def find_best_app(module: ModuleType) -> Flask:` · [src/flask/cli.py:L41-L91][f1]

Locates the best Flask app in a module when no explicit name was given.

It first checks attributes named 'app' and 'application' and returns the first that is a Flask instance. Otherwise it collects all Flask instances in the module: exactly one is returned; more than one raises NoAppException suggesting 'module:name'. Next it tries factories named 'create_app' then 'make_app': a call returning a Flask instance is returned; a TypeError is re-raised unless _called_with_wrong_args determines the call itself lacked required arguments, in which case NoAppException suggests 'module:create_app(args)'. If nothing matches, NoAppException reports failure.

raises: [NoAppException](r2-cli-app-discovery.md#u-68b618421e9e); calls: [_called_with_wrong_args](r2-cli-app-discovery.md#u-8597d7387a6f)

**Uncertainties.**

- Factories returning a non-Flask value are silently skipped; a later factory or the final error path then applies.

<a id="u-4c152a2459fc"></a>
### `src/flask/cli.py:locate_app (2)`

`def locate_app( module_name: str, app_name: str | None, raise_if_not_found: bool = Tr…` · [src/flask/cli.py:L241-L264][f1]

Imports a module by name and returns its app.

If __import__ raises ImportError, traceback depth distinguishes causes: tb_next set means the error occurred inside the target module, so it is wrapped in NoAppException including the full traceback; otherwise the module itself was not found, which raises NoAppException ('Could not import ...') when raise_if_not_found is true or returns None when false. On success, app_name None selects find_best_app on the module; a non-None name selects find_app_by_string. Two typed overloads declare the Flask and Flask | None return variants for raise_if_not_found True/False.

calls: [find_best_app](r2-cli-app-discovery.md#u-6522d181aa3f), [find_app_by_string](r2-cli-app-discovery.md#u-81ef5022e21a); raises: [NoAppException](r2-cli-app-discovery.md#u-68b618421e9e)

**Uncertainties.**

- The overload declarations (lines 229-238) are typing-only; their runtime effect is none beyond the shared implementation.

<a id="u-f08e3cd8f1fb"></a>
### `prepare_import`

`def prepare_import(path: str) -> str:` · [src/flask/cli.py:L200-L226][f1]

Turns a file path into a dotted module name and makes its package root importable.

The path is realpath'd, a '.py' extension is stripped, and a trailing '__init__' component is replaced by its parent directory. Components are then split off upward, stopping once the enclosing directory has no '__init__.py', so names above that point are excluded. The final directory is inserted at sys.path[0] if not already present, and the reversed components joined with dots are returned.

<a id="u-3ddd294cf2d6"></a>
### `_set_app`

`def _set_app(ctx: click.Context, param: click.Option, value: str | None) -> str | None:` · [src/flask/cli.py:L440-L446][f1]

Callback for the --app option: when the value is None it returns None unchanged; otherwise it stores the value as ScriptInfo.app_import_path on the context object (created if absent) and returns the value.

uses: [ScriptInfo](r2-cli-app-discovery.md#u-e0ddadae27ac)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/cli.py
