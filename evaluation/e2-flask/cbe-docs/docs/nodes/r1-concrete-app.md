# Concrete WSGI Application

**Capability.** The flask.Flask class in src/flask/app.py: it turns the sansio registry into a runnable WSGI application with a Click CLI, dev server, static folder serving, the full request dispatch pipeline, error handling, contexts, URL building, resource access, and test-client support. Its children separate the pipeline stages that only make sense at request time.

Use this subtree for runtime behavior: what happens between an incoming environ and the returned response, and how the app is constructed and served. Registration itself lives under core-app-model; this subtree executes what was registered.

**Children.**

- [Request Dispatch Pipeline](r1-request-dispatch.md) `r1-request-dispatch` · 12 unit(s)
- [Exception and Error Handling](r1-error-handling.md) `r1-error-handling` · 7 unit(s)
- [App and Request Contexts](r1-contexts-teardown.md) `r1-contexts-teardown` · 6 unit(s)
- [URL Building, Redirects, and Resources](r1-url-building-resources.md) `r1-url-building-resources` · 10 unit(s)
- [CLI Entry and Test Support](r1-app-test-support.md) `r1-app-test-support` · 3 unit(s)

**Depends on.**

- [Sans-I/O Application Core](r1-core-app-model.md) · graph-confirmed · 2 edge(s) · Flask.__init__ forwards constructor parameters to the sansio App, extending the registration-only core into a runnable application.
- [Scaffold Registration Base](r1-scaffold-shared-base.md) · graph-confirmed · 2 edge(s) · Route/template-filter registration decorators call setupmethod, the shared Scaffold guard for mutating registration.
- [Environment and Path Helpers](r2-environment-helpers.md) · graph-only · 2 edge(s)
- [FlaskGroup and App Context Commands](r2-cli-command-group.md) · graph-only · 1 edge(s)
- [Run, Shell, and Routes Commands](r2-cli-server-commands.md) · graph-only · 1 edge(s)

Parent: [Flask Framework](r1-flask-framework.md)

## Units (6)

<a id="u-42109b968e96"></a>
### `Flask`

`class Flask(App):` · [src/flask/app.py:L81-L226][f1]

Concrete WSGI application extending the sansio App: it adds a Click CLI group, serves the static folder, and implements request dispatch, error handling, response conversion, context teardown, and URL building.

Class-level defaults include default_config (an ImmutableDict of config keys such as DEBUG, SECRET_KEY, session cookie settings, SEND_FILE_MAX_AGE_DEFAULT), request_class, response_class, and a class-wide session_interface instance of SecureCookieSessionInterface. Members documented in their own units are not repeated here.

inherits: [class::App][f2]; uses: [class::SecureCookieSessionInterface][f3]

**Uncertainties.**

- Behavior of inherited App attributes and methods (e.g. add_url_rule, config loading) is defined in sansio/app.py and not visible here.

<a id="u-82664df1a740"></a>
### `Flask.__init__`

`def __init__( self, import_name: str, static_url_path: str | None = None, static_fold…` · [src/flask/app.py:L226-L279][f1]

Initialize the concrete app: forward all constructor parameters to App.__init__, then create the app's Click group (cli.AppGroup) named after self.name.

If has_static_folder is truthy, assert that static_host is set exactly when host_matching is true (AssertionError otherwise), and register the static route f"{static_url_path}/<path:filename>" with endpoint 'static'; the view lambda resolves the app through a weakref to avoid a reference cycle and calls send_static_file.

**Notes.**

- side_effect: Registers the 'static' URL rule whenever the app has a static folder, without checking that the folder exists on disk.
- failure: Mismatched static_host/host_matching raises AssertionError at construction time.

calls: [method::App.__init__][f2]; uses: [Flask.send_static_file](r1-url-building-resources.md#u-9555b369e50a)

**Uncertainties.**

- add_url_rule resolution is ambiguous in the graph (App vs Blueprint variants); the call target class is inferred, not proven from this file.

<a id="u-e0e32d77b132"></a>
### `app.py module code (L1–L73)`

`module_region` · [src/flask/app.py:L1-L73][f1]

Import block for app.py: stdlib and Werkzeug names, internal flask imports (cli, typing, ctx, globals, helpers, sansio.app, sessions, signals, templating, wrappers), TYPE_CHECKING-only type imports, and five typing TypeVars bound to flask.typing callables.

Pure declarations with no runtime behavior beyond the class-level session_interface instantiation referenced by the Flask class unit.

<a id="u-77f2bfe17f97"></a>
### `_make_timedelta`

`def _make_timedelta(value: timedelta | int | None) -> timedelta | None:` · [src/flask/app.py:L74-L78][f1]

Coerce a sentinels-allowed duration value into a timedelta.

Returns the value unchanged when it is None or already a timedelta; otherwise wraps it with timedelta(seconds=value), so integer input is read as seconds. No other validation occurs.

**Uncertainties.**

- Non-int, non-timedelta, non-None values rely on timedelta(seconds=...) raising; that error is not caught here.

<a id="u-7caab98d1048"></a>
### `Flask.run`

`def run( self, host: str | None = None, port: int | None = None, debug: bool | None =…` · [src/flask/app.py:L546-L667][f1]

Start the Werkzeug development server for this app; not for production.

If FLASK_RUN_FROM_CLI is 'true', print a red warning when not running under the reloader and return without starting a server. When load_dotenv resolves truthy (via get_load_dotenv), call cli.load_dotenv() and let FLASK_DEBUG override self.debug. An explicit debug argument then wins over everything. Host defaults to the SERVER_NAME host part, else '127.0.0.1'; port: an explicitly passed port (including 0) is int-coerced, else the SERVER_NAME port part, else 5000. Defaults options use_reloader and use_debugger to self.debug and threaded to True, print the server banner, and block in werkzeug run_simple(host, port, self, **options). In a finally block, resets self._got_first_request to False so a non-reloader restart in a shell works.

**Notes.**

- side_effect: Mutates self.debug and self._got_first_request; loads .env/.flaskenv files and may change the working directory via cli.load_dotenv.
- failure: Invalid options forwarded to run_simple surface as Werkzeug errors after the banner is printed.

calls: [load_dotenv](r2-cli-command-group.md#u-896a31ca6044), [show_server_banner](r2-cli-server-commands.md#u-b8abb08fd76f), [get_debug_flag](r2-environment-helpers.md#u-88884dd6c1eb), [get_load_dotenv](r2-environment-helpers.md#u-1ebc0586f976)

<a id="u-ba7ba74658a9"></a>
### `Flask.make_shell_context`

`def make_shell_context(self) -> dict[str, t.Any]:` · [src/flask/app.py:L534-L544][f1]

Build the interactive shell namespace: {'app': self, 'g': g}, then update with each registered shell context processor's return dict, so processors can add or override entries.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/app.py
[f2]: ../../../../../../eval/flask-85c5d93/src/flask/sansio/app.py
[f3]: ../../../../../../eval/flask-85c5d93/src/flask/sessions.py
