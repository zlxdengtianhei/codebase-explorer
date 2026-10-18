# Testing Support

**Capability.** Owns Flask's test tooling: an app-aware EnvironBuilder, FlaskClient preserving contexts across requests, FlaskCliRunner binding ScriptInfo for CLI tests, and shared pytest fixtures in conftest.

Use these when writing tests for Flask apps. conftest fixtures provide environment isolation, app/client fixtures, import-path sandboxes, and context-leak detection for the suite itself.

**Depended on by.**

- [Blueprint Test Suite](r2-blueprint-tests.md) · model-inferred · 0 edge(s)
- [Configuration Loading](r2-configuration.md) · graph-confirmed · 7 edge(s) · Instance-path configuration tests rely on shared conftest fixtures.
- [View and Async Dispatch Tests](r2-view-tests.md) · graph-confirmed · 2 edge(s)
- [App and Request Contexts](r1-contexts-teardown.md) · graph-only · 1 edge(s)

Parent: [Flask Framework](r2-flask-framework.md)

## Units (5)

<a id="u-84a78615434e"></a>
### `EnvironBuilder`

`class EnvironBuilder(werkzeug.test.EnvironBuilder):` · [src/flask/testing.py:L27-L49][f1]

Werkzeug EnvironBuilder subclass that derives WSGI environ defaults from a Flask app.

`__init__` asserts that `base_url` is mutually exclusive with `subdomain`/`url_scheme` (AssertionError otherwise). When `base_url` is None it builds one: host from `SERVER_NAME` or 'localhost', prefixed with `subdomain.` if given; scheme from `PREFERRED_URL_SCHEME` unless `url_scheme` overrides; path may carry its own scheme/netloc via `urlsplit`, which override the built base; APPLICATION_ROOT forms the base path and a query string in the path is preserved. It stores `self.app` and delegates to the werkzeug constructor. `json_dumps` serializes with the app's JSON provider so test payloads match the app's serialization config.

group: [EnvironBuilder](r2-testing-support.md#u-84a78615434e); uses: [FlaskClient](r2-testing-support.md#u-fd5d935bcad4)

<a id="u-fd5d935bcad4"></a>
### `FlaskClient`

`class FlaskClient(Client):` · [src/flask/testing.py:L109-L125][f1]

Werkzeug test Client that understands Flask contexts and can preserve them across requests within a `with` block.

`__init__` sets `preserve_context` False, an empty context-manager list and ExitStack, and default `environ_base` with REMOTE_ADDR and a Werkzeug user-agent including the cached version. `session_transaction` requires cookies (raises TypeError if `_cookies is None`); it opens a temporary test request context (`app.test_request_context(*args, **kwargs)`), injects the client's cookies into the environ, opens a session inside that context (raising RuntimeError if the backend returns None), yields the session, and on exit saves it via the session interface into a fresh response unless it is a null session, then copies the response's Set-Cookie headers back onto the client's cookie jar. `_copy_environ` merges `environ_base` into a given environ and, when `preserve_context` is on, inserts `werkzeug.debug.preserve_context` pointing at `_new_contexts.append`. `_request_from_builder_args` merges environ_base into kwargs, builds an EnvironBuilder, and returns its request, closing the builder in a finally. `open` dispatches on the first argument: an EnvironBuilder is copied and given merged environ_base; a dict goes through `EnvironBuilder.from_environ`; a BaseRequest is copied with a rewritten environ; otherwise arguments build a request via `_request_from_builder_args`. Before dispatch it closes the context stack (so preserved contexts do not leak across redirects or multiple requests), calls the werkzeug `Client.open`, attaches the app's json module to the response, then re-enters any contexts that were preserved during the request. `__enter__` enables preserve_context, raising RuntimeError on nesting; `__exit__` disables it and closes the stack.

uses: [EnvironBuilder](r2-testing-support.md#u-84a78615434e); calls: [_get_werkzeug_version](r2-testing-support.md#u-fe45dcc38431), [Flask.test_request_context](r1-contexts-teardown.md#u-0f74641220cd)

**Uncertainties.**

- The `werkzeug.debug.preserve_context` environ key is consumed by external code (debugger); its effect here is only to collect context managers.
- `Client.open` and cookie-jar methods are inherited from werkzeug and not visible in this file.

<a id="u-150c825458c0"></a>
### `FlaskCliRunner`

`class FlaskCliRunner(CliRunner):` · [src/flask/testing.py:L265-L271][f1]

Click CliRunner bound to a Flask app for CLI testing.

`__init__` stores the app and passes remaining kwargs to CliRunner. `invoke` defaults `cli` to `self.app.cli` and, unless the caller supplied `obj`, injects a `ScriptInfo(create_app=lambda: self.app)` so commands can load the tested app, then delegates to CliRunner.invoke and returns its Result.

calls: [ScriptInfo](r2-cli-app-discovery.md#u-e0ddadae27ac)

<a id="u-fe45dcc38431"></a>
### `_get_werkzeug_version`

`def _get_werkzeug_version() -> str:` · [src/flask/testing.py:L100-L106][f1]

Returns the installed Werkzeug version string, caching it in the module global `_werkzeug_version` so `importlib.metadata.version` runs only once.

<a id="u-7a1aa125604a"></a>
### `conftest.py-fixtures`

`def _standard_os_environ():` · [tests/conftest.py:L11-L33][f2]

pytest fixtures shared by the Flask test suite, covering environment isolation, standard app/context/client fixtures, import-path sandboxes, and context-leak detection.

The session-scoped autouse `_standard_os_environ` deletes FLASK_ENV_FILE, FLASK_APP, FLASK_DEBUG, FLASK_RUN_FROM_CLI and WERKZEUG_RUN_MAIN via MonkeyPatch.delenv (notset value) or sets them, yields the recorded op list, and undoes everything at session end. The per-test autouse `_reset_os_environ` extends `monkeypatch._setitem` with that list, so os.environ is restored after each test even if a test mutated it. `app` builds a Flask('flask_test') rooted at the tests directory with TESTING and SECRET_KEY set. `app_ctx` and `req_ctx` push an app/test-request context and yield the ctx object inside a `with`, guaranteeing pop on exit. `test_apps` prepends the test_apps directory to sys.path and, after the test, pops every module added during it so stale 'import app' entries cannot leak between tests. The autouse `leak_detector` runs after each test: while request_ctx is active it records the underlying object and pops it, then asserts no leaks were found. `modules_tmp_path` creates and sys.path-prepends a temp dir; `modules_tmp_path_prefix` points sys.prefix at it; `site_packages` additionally creates and prepends lib/pythonX.Y/site-packages. `purge_module` returns `inner(name)` which registers a finalizer popping the named module at teardown.

uses: [conftest.py-fixtures](r2-testing-support.md#u-7a1aa125604a); contract: [conftest.py-fixtures](r2-testing-support.md#u-7a1aa125604a)

**Uncertainties.**

- Whether monkeypatch._setitem.extend semantics match upstream _pytest internals is not visible in this file

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/testing.py
[f2]: ../../../../../../eval/flask-85c5d93/tests/conftest.py
