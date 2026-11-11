# Helpers, Flask Blueprint and Run

**Capability.** Gathers public helper functions (url_for, redirect, flash, send_file, abort, debug flags), the WSGI-aware Blueprint, and the app's run method.

Read this for user-facing utilities and the concrete Blueprint class with CLI group and static serving. It also includes the development server run method and dotenv or debug environment checks.

**Depends on.**

- [Flask CLI Implementation](flask-cli-implementation.md) · graph-confirmed · 2 edge(s)
- [CLI Options and App Loading Info](cli-options-and-app-loading-info.md) · graph-only · 1 edge(s)
- [CLI Run Command and Command Discovery](cli-run-command-and-command-discovery.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Flask CLI Implementation](flask-cli-implementation.md) · graph-confirmed · 3 edge(s) · 3 inferred relation(s) · The CLI implementation uses helpers such as debug-flag checks and the app run method.
- [CLI Run Command and Command Discovery](cli-run-command-and-command-discovery.md) · graph-only · 2 edge(s)
- [Sansio App Base Class](sansio-app-base-class.md) · graph-only · 2 edge(s)
- [CLI Options and App Loading Info](cli-options-and-app-loading-info.md) · graph-only · 1 edge(s)
- [Flask App Class and Utilities](flask-app-class-and-utilities.md) · graph-only · 1 edge(s)
- [Scaffold Base and Setup Decorators](scaffold-base-and-setup-decorators.md) · graph-only · 1 edge(s)
- [Views, Wrappers, Signals and Debug Aids](views-wrappers-signals-and-debug-aids.md) · graph-only · 1 edge(s)

Parent: [Command Line and Public Helpers](command-line-and-public-helpers.md)

## Units (20)

<a id="u-7caab98d1048"></a>
### `Flask.run`

`def run( self, host: str | None = None, port: int | None = None, debug: bool | None =…` · [src/flask/app.py:L546-L667][f1]

Starts the Werkzeug development server for this app, resolving host, port, debug and load_dotenv options.

Not for production.
If env FLASK_RUN_FROM_CLI == 'true' it returns immediately without serving; when not running under the reloader it also prints a red warning via click.secho. If get_load_dotenv(load_dotenv) is true, cli.load_dotenv() runs and, if FLASK_DEBUG is in the environment, self.debug = get_debug_flag(). A non-None debug argument overrides everything with bool(debug).
Host: explicit host wins, else the host part of SERVER_NAME, else 127.0.0.1. Port: a truthy port or 0 is converted with int(); else the SERVER_NAME port; else 5000. Options use setdefault: use_reloader and use_debugger default to self.debug, threaded to True. It shows the banner, imports run_simple, and runs it; in a finally block it resets _got_first_request to False even when the server raises. Non-integer port strings raise ValueError.

<a id="u-340cf74dd862"></a>
### `Blueprint`

`class Blueprint(SansioBlueprint):` · [src/flask/blueprints.py:L18-L19][f2]

Flask's WSGI-aware Blueprint, extending the sansio Blueprint with a Click command group and app-context-based static file serving and resource opening.

Methods are documented separately; the class body itself only adds the three methods plus a constructor.

inherits: [SansioBlueprint](../../catalog.json)

<a id="u-2111fdf38502"></a>
### `Blueprint.__init__`

`def __init__( self, name: str, import_name: str, static_folder: str | os.PathLike[str…` · [src/flask/blueprints.py:L19-L53][f2]

Constructs a Blueprint by forwarding every argument to the sansio base initializer, then attaches a Click command group named after the blueprint.

The cli_group default is the shared _sentinel value, so the base class can tell whether the caller passed it. After super().__init__, self.cli is a fresh AppGroup and its name is set to self.name (the blueprint name as set by the base class). No validation happens here; any validation of names or paths is in the base class.

calls: [AppGroup](../../catalog.json)

<a id="u-b3f294891469"></a>
### `Blueprint.get_send_file_max_age`

`def get_send_file_max_age(self, filename: str | None) -> int | None:` · [src/flask/blueprints.py:L55-L80][f2]

Returns the cache max-age for static files from the current app's SEND_FILE_MAX_AGE_DEFAULT setting, normalised to int seconds or None.

Reads current_app.config at call time, so it needs an active app context (otherwise the proxy access fails; not caught here). None gives None; a timedelta becomes int(total_seconds()), truncating fractions; any other value is returned unchanged with no type check. The filename argument is ignored, so every file gets the same value.

<a id="u-79aeaf78f841"></a>
### `Blueprint.open_resource`

`def open_resource( self, resource: str, mode: str = "rb", encoding: str | None = "utf…` · [src/flask/blueprints.py:L104-L128][f2]

Opens a file relative to the blueprint's root_path for reading only.

A mode outside 'r', 'rt', 'rb' raises ValueError before any filesystem access. Binary mode ('rb') opens without an encoding; text modes pass the encoding argument (default utf-8, None allowed). The path is os.path.join(root_path, resource) with no containment check, so absolute or parent-relative resources are not blocked here. OSError from open propagates. The caller owns closing the returned file.

<a id="u-9d50961e7564"></a>
### `Blueprint.send_static_file`

`def send_static_file(self, filename: str) -> Response:` · [src/flask/blueprints.py:L82-L102][f2]

View function that serves a file from the blueprint's static folder via send_from_directory.

Raises RuntimeError if the blueprint has no static folder (has_static_folder false). Otherwise it computes max_age with this blueprint's get_send_file_max_age and passes it explicitly, because send_file only consults the app's version. Missing or unsafe paths are handled inside send_from_directory (the 404 behavior is documented there, not here).

calls: [Blueprint.get_send_file_max_age](helpers-flask-blueprint-and-run.md#u-b3f294891469), [send_from_directory](../../catalog.json)

<a id="u-6855621e8eaf"></a>
### `_prepare_send_file_kwargs`

`def _prepare_send_file_kwargs(**kwargs: t.Any) -> dict[str, t.Any]:` · [src/flask/helpers.py:L387-L397][f3]

Completes keyword arguments for Werkzeug's send_file and send_from_directory with Flask-specific values.

If max_age is missing or None, it is replaced by current_app.get_send_file_max_age (the bound method, evaluated lazily per file by Werkzeug). It then overwrites environ, use_x_sendfile (from USE_X_SENDFILE config), response_class and _root_path from the request and app, so those keys cannot be overridden by callers. Returns the modified dict. Requires both app and request contexts.

<a id="u-03dadcbb1883"></a>
### `_split_blueprint_path`

`def _split_blueprint_path(name: str) -> list[str]:` · [src/flask/helpers.py:L627-L634][f3]

Returns a blueprint name and each of its ancestors, most specific first, for a dotted nested blueprint name.

For 'a.b.c' it returns ['a.b.c', 'a.b', 'a']. The result is memoized with functools.cache, so the same list object is returned for repeated calls and callers must not mutate it.

<a id="u-3a4f71214dc8"></a>
### `abort`

`def abort(code: int | BaseResponse, *args: t.Any, **kwargs: t.Any) -> t.NoReturn:` · [src/flask/helpers.py:L266-L286][f3]

Raises an HTTP exception for a status code, via the current app's aborter when available and Werkzeug's abort otherwise.

If current_app is active, its aborter is called with the code and extra arguments; it is expected to raise. If it returns normally, execution falls through to the Werkzeug abort call, which raises as well, so the function never returns.

<a id="u-880145f6d7d9"></a>
### `flash`

`def flash(message: str, category: str = "message") -> None:` · [src/flask/helpers.py:L311-L342][f3]

Stores a flash message in the session for the next request and sends the message_flashed signal.

Reads the '_flashes' list from the session (default new list), appends (category, message), and writes the list back to the session key explicitly so that sessions with external storage notice the change. It then sends the signal with the real app object as sender and the app's ensure_sync as async wrapper. Needs a request context with a session; failures there propagate.

calls: [message_flashed](../../catalog.json)

<a id="u-88884dd6c1eb"></a>
### `get_debug_flag`

`def get_debug_flag() -> bool:` · [src/flask/helpers.py:L27-L32][f3]

Reads the FLASK_DEBUG environment variable and returns whether debug mode is on.

False if the variable is unset or empty; also False when its lowercased value is '0', 'false' or 'no'. Any other non-empty value, including 'off', counts as True.

<a id="u-993c1b0209f4"></a>
### `get_flashed_messages`

`def get_flashed_messages( with_categories: bool = False, category_filter: t.Iterable[…` · [src/flask/helpers.py:L345-L384][f3]

Returns the flashed messages for the current request, removing them from the session the first time they are read.

The result is cached on the request context's flashes attribute: if it is None, the '_flashes' value is popped from the session (or an empty list if absent) and cached, so later calls in the same request return the same messages. If category_filter is non-empty, only entries whose category is in it are kept. With with_categories false (default) a list of message strings is returned; with true, the list of (category, message) tuples.

<a id="u-1ebc0586f976"></a>
### `get_load_dotenv`

`def get_load_dotenv(default: bool = True) -> bool:` · [src/flask/helpers.py:L35-L47][f3]

Returns whether default dotenv files should be loaded, allowing FLASK_SKIP_DOTENV to override the passed default.

If the variable is unset or empty, the default is returned. Otherwise returns True only when the lowercased value is '0', 'false' or 'no' (meaning do not skip), and False for any other non-empty value (skip).

<a id="u-da4504f7f768"></a>
### `get_root_path`

`def get_root_path(import_name: str) -> str:` · [src/flask/helpers.py:L570-L624][f3]

Finds the directory that contains a module or package, falling back to the current directory when it cannot be determined.

Order: (1) if the module is already in sys.modules with a non-None __file__, return the directory of its absolute path. (2) Otherwise importlib.util.find_spec is called; a None spec, ImportError or ValueError means no loader. With no loader (such as an unloaded __main__ or interactive session), os.getcwd() is returned. (3) If the loader has get_filename, it is used. Otherwise the module is imported with __import__ and its __file__ read; if that is None (namespace package or import hook), RuntimeError is raised telling the caller to provide the root path explicitly. Import errors raised there propagate. Returns the directory of the file path.

<a id="u-e1f4c98caba1"></a>
### `get_template_attribute`

`def get_template_attribute(template_name: str, attribute: str) -> t.Any:` · [src/flask/helpers.py:L289-L308][f3]

Fetches a macro or variable exported by a template, for use from Python code.

Gets the template through current_app.jinja_env.get_template (TemplateNotFound propagates) and returns the named attribute of its module object; a missing attribute raises AttributeError. Needs an app context.

<a id="u-132e9804ecee"></a>
### `make_response`

`def make_response(*args: t.Any) -> Response:` · [src/flask/helpers.py:L139-L185][f3]

Builds a response object from view-return-style arguments through the current app.

No arguments returns a new empty current_app.response_class(). One argument is unpacked and passed to current_app.make_response; several arguments are passed as one tuple. Needs an active app context; its conversion rules and errors come from the app's make_response, which is not in this file.

<a id="u-8a60c1d60c8b"></a>
### `redirect`

`def redirect( location: str, code: int = 302, Response: type[BaseResponse] | None = N…` · [src/flask/helpers.py:L242-L263][f3]

Creates a redirect response, using the current app's redirect when an app context is active and Werkzeug's otherwise.

With an active app, current_app.redirect(location, code=code) is used and the Response argument is ignored. Without one, werkzeug.utils.redirect is called with code and the optional Response class.

<a id="u-93a20210ed51"></a>
### `send_file`

`def send_file( path_or_file: os.PathLike[t.AnyStr] | str | t.BinaryIO, mimetype: str …` · [src/flask/helpers.py:L400-L523][f3]

Sends a file or file-like object to the client by calling Werkzeug's send_file with Flask-specific arguments.

All options are packed with the path and request.environ and passed through _prepare_send_file_kwargs, which fills in a default max_age callable, X-Sendfile setting, response class and root path. Behavior such as MIME detection, conditional and range responses, ETag, and errors for text-mode file objects is implemented in Werkzeug, not here. Paths are trusted and not checked, so untrusted user paths must not be passed. Requires a request context.

calls: [_prepare_send_file_kwargs](helpers-flask-blueprint-and-run.md#u-6855621e8eaf), [werkzeug.utils.send_file](../../catalog.json)

<a id="u-b61c28e0e520"></a>
### `send_from_directory`

`def send_from_directory( directory: os.PathLike[str] | str, path: os.PathLike[str] | …` · [src/flask/helpers.py:L526-L567][f3]

Serves a file from a directory safely by delegating to Werkzeug's send_from_directory with Flask-specific arguments.

Extra keyword arguments are completed by _prepare_send_file_kwargs. Path-escape protection (safe_join) and the 404 NotFound for missing or non-regular files are implemented in Werkzeug. The directory is relative to the app's root path via the _root_path argument. Requires an app and request context.

calls: [_prepare_send_file_kwargs](helpers-flask-blueprint-and-run.md#u-6855621e8eaf), [werkzeug.utils.send_from_directory](../../catalog.json)

<a id="u-221362c3f2fb"></a>
### `url_for`

`def url_for( endpoint: str, *, _anchor: str | None = None, _method: str | None = None…` · [src/flask/helpers.py:L188-L239][f3]

Thin wrapper that generates a URL by calling current_app.url_for with the same arguments.

Needs an active app context (the proxy fails otherwise). The special underscore parameters and extra values are forwarded unchanged, so any overriding of URL building is done by the app, not here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/app.py
[f2]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/blueprints.py
[f3]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/helpers.py
