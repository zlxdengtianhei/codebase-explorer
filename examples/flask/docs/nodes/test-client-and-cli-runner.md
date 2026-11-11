# Test Client and CLI Runner

**Capability.** Offers testing tools: an environment builder with app defaults, a context-aware test client with session editing, and an app-aware CLI runner.

Go here when writing or debugging tests against a Flask app. It covers building environ values, sending requests, preserving contexts in with-blocks, session transactions and invoking CLI commands.

**Depends on.**

- [Flask App Request Lifecycle](flask-app-request-lifecycle.md) · graph-confirmed · 1 edge(s) · The test client sends requests through the app's request lifecycle.
- [CLI Options and App Loading Info](cli-options-and-app-loading-info.md) · graph-only · 1 edge(s)
- [WSGI Entry and Request Contexts](wsgi-entry-and-request-contexts.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Flask App Request Lifecycle](flask-app-request-lifecycle.md) · graph-confirmed · 1 edge(s)
- [WSGI Entry and Request Contexts](wsgi-entry-and-request-contexts.md) · graph-only · 1 edge(s)

Parent: [Runtime App, Contexts and Testing](runtime-app-contexts-and-testing.md)

## Units (15)

<a id="u-84a78615434e"></a>
### `EnvironBuilder`

`class EnvironBuilder(werkzeug.test.EnvironBuilder):` · [src/flask/testing.py:L27-L49][f1]

Werkzeug EnvironBuilder subclass that takes default host, scheme and path root from the Flask app's configuration.

<a id="u-150c825458c0"></a>
### `FlaskCliRunner`

`class FlaskCliRunner(CliRunner):` · [src/flask/testing.py:L265-L271][f1]

Click CliRunner that knows the Flask app under test, so CLI commands can be invoked with an app-aware ScriptInfo.

<a id="u-fd5d935bcad4"></a>
### `FlaskClient`

`class FlaskClient(Client):` · [src/flask/testing.py:L109-L125][f1]

Test client that extends Werkzeug's Client with Flask context handling: it can defer cleanup of request contexts until the end of a with-block, and supports editing the session.

<a id="u-fe45dcc38431"></a>
### `_get_werkzeug_version`

`def _get_werkzeug_version() -> str:` · [src/flask/testing.py:L100-L106][f1]

Returns the installed Werkzeug version, caching it in a module-level global after the first lookup using importlib.metadata (PackageNotFoundError would propagate).

<a id="u-a2e21fc42188"></a>
### `EnvironBuilder.__init__`

`def __init__( self, app: Flask, path: str = "/", base_url: str | None = None, subdoma…` · [src/flask/testing.py:L49-L86][f1]

Builds the WSGI environment defaults from the app config unless a base_url is given.

An assert rejects passing subdomain or url_scheme together with base_url (asserts can be disabled with -O, which would skip this check). When base_url is None: the host is SERVER_NAME or 'localhost', prefixed by 'subdomain.' if given; the scheme defaults to PREFERRED_URL_SCHEME; path is parsed with urlsplit, so a full URL in path overrides the scheme and host with its own, and only its path and query are kept as the request path. The base URL becomes '<scheme>://<host>/<APPLICATION_ROOT without leading slashes>'. The app is stored on the builder and the remaining args go to the base class.

<a id="u-863658a423f8"></a>
### `EnvironBuilder.json_dumps`

`def json_dumps(self, obj: t.Any, **kwargs: t.Any) -> str:` · [src/flask/testing.py:L88-L94][f1]

Serializes an object to a JSON string with the app's configured JSON provider (app.json.dumps), so test requests use the same JSON settings as the app.

<a id="u-3bf1d744dcc8"></a>
### `FlaskCliRunner.__init__`

`def __init__(self, app: Flask, **kwargs: t.Any) -> None:` · [src/flask/testing.py:L271-L273][f1]

Stores the app and passes other keyword arguments to the CliRunner initializer.

<a id="u-d5c64e6ca337"></a>
### `FlaskCliRunner.invoke`

`def invoke( # type: ignore self, cli: t.Any = None, args: t.Any = None, **kwargs: t.A…` · [src/flask/testing.py:L275-L298][f1]

Invokes a CLI command in isolation, defaulting the command and the context object to the test app.

If cli is None, the app's own cli group is used. If 'obj' is not in kwargs, a ScriptInfo whose create_app returns this runner's app is passed, so commands can load the app without discovery; a caller-supplied obj is left alone. It then delegates to CliRunner.invoke and returns its Result. Errors in the command are captured by the runner, per Click's behavior.

uses: [ScriptInfo](cli-options-and-app-loading-info.md#u-e0ddadae27ac)

<a id="u-5d545bf15a14"></a>
### `FlaskClient.__enter__`

`def __enter__(self) -> FlaskClient:` · [src/flask/testing.py:L249-L253][f1]

Enters a with-block on the client, turning on context preservation; raises RuntimeError if already preserving, so client blocks cannot be nested.

Returns the client.

<a id="u-52e57d237f37"></a>
### `FlaskClient.__exit__`

`def __exit__( self, exc_type: type | None, exc_value: BaseException | None, tb: Trace…` · [src/flask/testing.py:L255-L262][f1]

Leaves a with-block: turns off context preservation and closes the exit stack, popping any contexts kept alive during the block.

Exceptions from the block are not suppressed.

<a id="u-a1f3e16d6fb4"></a>
### `FlaskClient.__init__`

`def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:` · [src/flask/testing.py:L125-L133][f1]

Initializes the test client with context-preservation state and default environ values.

After the base initializer, preserve_context is False, a list collects contexts pushed during requests, and an ExitStack holds contexts kept open. environ_base defaults to REMOTE_ADDR 127.0.0.1 and a Werkzeug/<version> user agent.

<a id="u-176c2841f116"></a>
### `FlaskClient._copy_environ`

`def _copy_environ(self, other: WSGIEnvironment) -> WSGIEnvironment:` · [src/flask/testing.py:L185-L191][f1]

Builds the WSGI environ for a request by overlaying the given values on environ_base, and when preserve_context is on adds a 'werkzeug.debug.preserve_context' hook that collects contexts into the client's pending list.

The given environ takes precedence over the defaults.

<a id="u-4d7d108665e4"></a>
### `FlaskClient._request_from_builder_args`

`def _request_from_builder_args( self, args: tuple[t.Any, ...], kwargs: dict[str, t.An…` · [src/flask/testing.py:L193-L202][f1]

Creates a Request from builder arguments.

environ_base in kwargs (default empty) is merged through _copy_environ, then an EnvironBuilder bound to the app is created with the arguments. The request is built with get_request and the builder is always closed in a finally block, even if building fails.

uses: [EnvironBuilder.__init__](test-client-and-cli-runner.md#u-a2e21fc42188)

<a id="u-70ac1361856c"></a>
### `FlaskClient.open`

`def open( self, *args: t.Any, buffered: bool = False, follow_redirects: bool = False,…` · [src/flask/testing.py:L204-L247][f1]

Sends a request through the app and returns the test response, handling preserved contexts.

Input kinds: if the first argument is a Werkzeug EnvironBuilder, it is shallow-copied and given merged environ_base; if a dict, an environ is turned into a request via the Flask EnvironBuilder.from_environ; if a BaseRequest, it is copied and its environ is merged; otherwise a request is built from the arguments and keywords. Previously preserved contexts are closed first, so contexts do not persist across requests or redirects. The request is sent through the parent open with buffered and follow_redirects; the response's json_module is set to the app's JSON provider. Contexts collected during the request (only when preserve_context) are then popped from the pending list and entered in the exit stack, keeping them active until the next request or the end of the with-block.

<a id="u-4f514cbf5322"></a>
### `FlaskClient.session_transaction`

`def session_transaction( self, *args: t.Any, **kwargs: t.Any ) -> t.Iterator[SessionM…` · [src/flask/testing.py:L135-L183][f1]

Context manager that lets a test read and modify the client's session, saving it back and updating the client's cookies on exit.

Raises TypeError if cookies are disabled (client built without cookie support). A test request context is built from the passed arguments, the client's cookies are added to its environ, and the session is opened inside it using the app's session interface; if the backend returns None, RuntimeError is raised. The session is yielded. After the with-block (only on normal completion, since an exception in the body skips the save), if the session is a null session nothing is saved. Otherwise the session is saved into a new response and the Set-Cookie headers are fed back to the client's cookie jar for the request host (port removed) and path.

calls: [Flask.test_request_context](../../catalog.json.gz)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/testing.py
