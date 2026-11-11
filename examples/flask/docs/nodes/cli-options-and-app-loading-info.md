# CLI Options and App Loading Info

**Capability.** Supports the command line with Click parameter types, option callbacks, dotenv loading and the ScriptInfo object that tracks how to find the app.

Come here for the options and callbacks of the flask command, such as --app, --debug, --cert, --env-file and --version. It also contains ScriptInfo, the load error, and the custom path types.

**Depends on.**

- [Helpers, Flask Blueprint and Run](helpers-flask-blueprint-and-run.md) · graph-only · 1 edge(s)

**Depended on by.**

- [CLI Run Command and Command Discovery](cli-run-command-and-command-discovery.md) · graph-confirmed · 1 edge(s) · The run command and command discovery use ScriptInfo and the CLI options to load the application.
- [Helpers, Flask Blueprint and Run](helpers-flask-blueprint-and-run.md) · graph-only · 1 edge(s)
- [Test Client and CLI Runner](test-client-and-cli-runner.md) · graph-only · 1 edge(s)

Parent: [Flask CLI Implementation](flask-cli-implementation.md)

## Units (17)

<a id="u-24f31c731d02"></a>
### `CertParamType`

`class CertParamType(click.ParamType):` · [src/flask/cli.py:L780-L788][f1]

Click parameter type for the --cert option.

It accepts an existing file path, the string 'adhoc', or an import string that resolves to an ssl.SSLContext.

<a id="u-68b618421e9e"></a>
### `NoAppException`

`class NoAppException(click.UsageError):` · [src/flask/cli.py:L37-L38][f1]

Exception raised when a Flask application cannot be found or loaded by the CLI.

It subclasses click.UsageError, so Click reports it as a usage error rather than a traceback.

inherits: [click.UsageError](../../catalog.json.gz)

<a id="u-e0ddadae27ac"></a>
### `ScriptInfo`

`class ScriptInfo:` · [src/flask/cli.py:L293-L305][f1]

Holds how to find and load the Flask application for CLI commands, caching the loaded app.

It is normally created by FlaskGroup and stored as the Click context object.
State: app_import_path, create_app factory, a free-form data dict, set_debug_flag, load_dotenv_defaults and the private cached app. ScriptInfo itself does not load dotenv files; the attribute is only a record for other code.

<a id="u-137becebe47f"></a>
### `SeparatedPathType`

`class SeparatedPathType(click.Path):` · [src/flask/cli.py:L867-L873][f1]

Click Path subclass for options holding several paths separated by the OS path separator, used for --extra-files and --exclude-patterns.

<a id="u-82625d9d59c9"></a>
### `_env_file_callback`

`def _env_file_callback( ctx: click.Context, param: click.Option, value: str | None ) …` · [src/flask/cli.py:L493-L512][f1]

Click eager callback for -e/--env-file that loads dotenv files as early as possible.

Tries to import dotenv. If it is missing and a file value was given, it raises click.BadParameter; if no value was given it continues silently so load_dotenv can print its tip. Then, if a value was given or ctx.obj.load_dotenv_defaults is true, it calls load_dotenv(value, load_defaults=...) and returns the value. It reads ctx.obj directly, assuming it is a ScriptInfo; a context without one would fail with AttributeError.

calls: [load_dotenv](cli-options-and-app-loading-info.md#u-896a31ca6044)

<a id="u-893b72fd2f0c"></a>
### `_path_is_ancestor`

`def _path_is_ancestor(path: str, other: str) -> bool:` · [src/flask/cli.py:L691-L695][f1]

Returns True if one path is an ancestor of another using string arithmetic only.

It strips len(path) characters off the front of other, removes leading separators, joins it back to path, and compares to other. No filesystem access or normalization is performed, so it depends on both strings having the same form. An empty remainder for equal paths: join(path, '') adds a trailing separator, so it only matches if other has it. Note: not referenced elsewhere in the supplied files.

<a id="u-3ddd294cf2d6"></a>
### `_set_app`

`def _set_app(ctx: click.Context, param: click.Option, value: str | None) -> str | None:` · [src/flask/cli.py:L440-L446][f1]

Click callback for --app/-A that stores the import path on the ScriptInfo.

Returns None and does nothing when no value was given. Otherwise it gets or creates the ScriptInfo on the context (ensure_object) and sets app_import_path to the value, overwriting a prior value, and returns the value.

<a id="u-954e541b98b6"></a>
### `_set_debug`

`def _set_debug(ctx: click.Context, param: click.Option, value: bool) -> bool | None: …` · [src/flask/cli.py:L468-L482][f1]

Click callback for --debug/--no-debug that publishes the choice through the FLASK_DEBUG environment variable.

If the parameter source is DEFAULT or DEFAULT_MAP (user did not pass it), it returns None and leaves the environment untouched so environment configuration still decides. Otherwise it sets os.environ['FLASK_DEBUG'] to '1' or '0' and returns the value. Using the environment, rather than ScriptInfo, makes the setting visible early, including inside app factories.

<a id="u-d4711d5746d9"></a>
### `_validate_key`

`def _validate_key(ctx: click.Context, param: click.Parameter, value: t.Any) -> t.Any:` · [src/flask/cli.py:L828-L864][f1]

Click callback for --key that validates it against --cert and rewrites the cert parameter into a (cert, key) pair.

Reads cert from ctx.params, so --cert must have been processed first (it is eager). When a key is given: BadParameter if cert is 'adhoc', if cert is an SSLContext, or if no cert was given; otherwise ctx.params['cert'] becomes (cert, key). When no key is given: BadParameter 'Required when using --cert' if a cert is present that is not adhoc and not a context. If ssl cannot be imported, the context check is treated as False. Returns the value unchanged.

<a id="u-81f903d14e67"></a>
### `get_version`

`def get_version(ctx: click.Context, param: click.Parameter, value: t.Any) -> None:` · [src/flask/cli.py:L267-L280][f1]

Click eager option callback that prints the Python, Flask and Werkzeug versions and exits.

Does nothing if the flag value is falsy or the context is in resilient parsing (e.g. completion). Otherwise it reads installed versions via importlib.metadata (PackageNotFoundError is not caught), echoes them honoring ctx.color, and calls ctx.exit(), which ends command processing.

<a id="u-896a31ca6044"></a>
### `load_dotenv`

`def load_dotenv( path: str | os.PathLike[str] | None = None, load_defaults: bool = Tr…` · [src/flask/cli.py:L698-L763][f1]

Loads .flaskenv, .env and an optional explicit file into os.environ without overriding variables that are already set.

Returns whether any data was found.
If python-dotenv cannot be imported, it prints a yellow tip to stderr when path is given or a .env or .flaskenv file exists in the working directory, then returns False. Otherwise values are merged into one dict in increasing precedence: .flaskenv, then .env (each located with find_dotenv(usecwd=True), only when load_defaults is true), then the explicit path if it is an existing file (a non-file path is silently ignored). Files are read as UTF-8. Then each key is set in os.environ only if it is not already present and its value is not None (keys with no value are skipped). The return value is bool(data), True if any key was parsed even if none were applied, since existing variables win.

<a id="u-cdc90319c105"></a>
### `CertParamType.__init__`

`def __init__(self) -> None:` · [src/flask/cli.py:L788-L789][f1]

Creates the helper click.Path type used for validating file paths, requiring an existing file (not a directory) and resolving the path.

<a id="u-ff76cacd654f"></a>
### `CertParamType.convert`

`def convert( self, value: t.Any, param: click.Parameter | None, ctx: click.Context | …` · [src/flask/cli.py:L791-L825][f1]

Converts the --cert value to a path, 'adhoc', or an SSLContext, or raises BadParameter.

First imports ssl; if the interpreter lacks SSL it raises BadParameter. Then it tries the Path type; success returns the resolved path. On BadParameter, the value is lowercased through click.STRING and: 'adhoc' requires the cryptography package (BadParameter if missing) and returns the string 'adhoc'; otherwise import_string(value, silent=True) is tried and an ssl.SSLContext result is returned. If neither applies, the original path BadParameter is re-raised. Note the value is lowercased before import, so import names with uppercase letters will not resolve.

<a id="u-b3f5ebf225ef"></a>
### `FlaskGroup.make_context`

`def make_context( self, info_name: str | None, args: list[str], parent: click.Context…` · [src/flask/cli.py:L657-L676][f1]

Creates the Click context, ensuring a ScriptInfo object and signaling that app.run must be a no-op.

Sets os.environ['FLASK_RUN_FROM_CLI']='true' as a side effect on every call, which makes app.run (in user code) skip starting a server while the CLI is running. If 'obj' is not in the passed extras and not in the group's context_settings, a new ScriptInfo is built from the group's create_app, set_debug_flag and load_dotenv values (the latter as load_dotenv_defaults). Then delegates to the parent make_context.

uses: [ScriptInfo](cli-options-and-app-loading-info.md#u-e0ddadae27ac)

<a id="u-3068e27c0020"></a>
### `FlaskGroup.parse_args`

`def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:` · [src/flask/cli.py:L678-L688][f1]

Parses arguments, first processing --env-file and --app by hand in the no-arguments and help-only cases.

If there are no args and no_args_is_help is set, or the sole argument is one of the help option names, it calls handle_parse_result on the env-file and app options with empty values. This lets environment variables (FLASK_APP, env files) take effect even though eager option processing is bypassed in those cases, so help lists app commands. Then delegates to the parent parse_args and returns its result.

<a id="u-14c585213f84"></a>
### `ScriptInfo.__init__`

`def __init__( self, app_import_path: str | None = None, create_app: t.Callable[..., F…` · [src/flask/cli.py:L305-L331][f1]

Initializes ScriptInfo state without loading anything.

Stores the import path, the optional create_app callable, an empty data dict and the debug-flag switch. load_dotenv_defaults is not stored as given: it passes through get_load_dotenv, so the FLASK_SKIP_DOTENV environment variable can override the argument. The cached app starts as None.

calls: [get_load_dotenv](helpers-flask-blueprint-and-run.md#u-1ebc0586f976)

<a id="u-7f6c836c796e"></a>
### `SeparatedPathType.convert`

`def convert( self, value: t.Any, param: click.Parameter | None, ctx: click.Context | …` · [src/flask/cli.py:L873-L879][f1]

Splits the raw value on the OS path separator and validates each item with the normal click.Path conversion.

Returns a list of converted values. Any item failing validation raises BadParameter via the parent convert. The parent convert is bound before the list comprehension to avoid a no-argument super() limitation in comprehensions on older Python versions.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/cli.py
