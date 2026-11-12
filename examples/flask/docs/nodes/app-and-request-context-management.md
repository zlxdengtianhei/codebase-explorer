# App and Request Context Management

**Capability.** Defines application and request contexts, the g namespace and context helpers that bind per-app and per-request state, URL matching and session opening.

Read this to understand how contexts are created, pushed, popped and copied. It includes AppContext, RequestContext, has_*_context checks, after-request registration and URL adapter creation.

**Depended on by.**

- [Flask App Request Lifecycle](flask-app-request-lifecycle.md) · graph-confirmed · 1 edge(s) · The request lifecycle uses the app and request context classes to bind per-request state.
- [Sansio App Base Class](sansio-app-base-class.md) · graph-only · 1 edge(s)
- [WSGI Entry and Request Contexts](wsgi-entry-and-request-contexts.md) · graph-only · 1 edge(s)

Parent: [Runtime App, Contexts and Testing](runtime-app-contexts-and-testing.md)

## Units (15)

<a id="u-010f8f671eab"></a>
### `ctx.py-app-context-globals-namespace`

`class _AppCtxGlobals:` · [src/flask/ctx.py:L29-L52][f1]

_AppCtxGlobals is a plain attribute namespace object, created per AppContext and exposed as the g proxy.

It stores all data in its __dict__.
Attribute reads missing from __dict__ raise AttributeError (via __getattr__ fallback); __setattr__ writes into __dict__; __delattr__ raises AttributeError if the name is absent. get(name, default=None) is dict.get. pop(name) raises KeyError if absent and no default was given; with a default it returns that (the module sentinel distinguishes 'no default' from None). setdefault sets and returns the default when missing. `in` checks the names and iteration yields attribute names. __repr__ returns '<flask.g of APPNAME>' using the current app context's app name when a context is active, otherwise object's default repr (it does not check that the context's g is this object).

<a id="u-632b2e4dff54"></a>
### `ctx.py-appcontext`

`class AppContext:` · [src/flask/ctx.py:L238-L245][f1]

AppContext holds application-level state (app, URL adapter, g) and binds itself to the current context variable on push.

__init__ stores the app, creates a url_adapter with create_url_adapter(None) (None if SERVER_NAME is unset) and a g via app.app_ctx_globals_class(). push stores the token from setting the context variable and sends appcontext_pushed. pop: only when this is the outermost push (one stored token) it runs the app's teardown with exc (omitted exc falls back to sys.exc_info()[1]); in finally it reads the current context and resets the variable with the popped token. After that, if the context read was not this object it raises AssertionError ('Popped wrong app context'); only on success does it send appcontext_popped. pop on a context never pushed would fail on the empty token list. As a context manager it pushes on enter and pops with the exception value on exit.

<a id="u-9da9dd075001"></a>
### `ctx.py-context-presence-checks`

`def has_request_context() -> bool:` · [src/flask/ctx.py:L196-L225][f1]

has_request_context and has_app_context return True when the request or app context variable is currently set (_cv_request / _cv_app .get(None) is not None), otherwise False.

They never raise.

<a id="u-8d2e69e55e92"></a>
### `ctx.py-copy-current-request-context`

`def copy_current_request_context(f: F) -> F:` · [src/flask/ctx.py:L155-L189][f1]

Decorator that captures a copy of the current request context and returns a wrapper that pushes that copy while calling the function.

Used for greenlets or threads.
Raises RuntimeError if no request context is active at decoration time. ctx.copy() shares the same request object and session. The wrapper runs `with ctx:` (push on enter, pop on exit, so teardown runs at the end of each call) and calls the function through the copied context's app.ensure_sync so async functions work. functools.update_wrapper copies the wrapped function's metadata.

<a id="u-d9c90914b13c"></a>
### `ctx.py-requestcontext-context-manager`

`def __enter__(self) -> RequestContext:` · [src/flask/ctx.py:L433-L435][f1]

__enter__ pushes the request context and returns it; __exit__ pops it passing the exception value so teardown functions see the error.

__exit__ returns None, so exceptions are never suppressed.

<a id="u-2e69ab7b3042"></a>
### `Flask.app_context`

`def app_context(self) -> AppContext:` · [src/flask/app.py:L1386-L1405][f2]

Returns a new AppContext for this app.

Does not push it; callers use it as a with block or call push.

<a id="u-6afa91f86588"></a>
### `Flask.create_url_adapter`

`def create_url_adapter(self, request: Request | None) -> MapAdapter | None:` · [src/flask/app.py:L425-L476][f2]

Creates a werkzeug MapAdapter for a request, or for no request when SERVER_NAME is configured.

Returns None when no adapter can be made.
With a request: if TRUSTED_HOSTS config is not None it is set on request.trusted_hosts; request.host is then set from get_host(environ, trusted_hosts), which can raise for an untrusted host. server_name comes from SERVER_NAME config. If url_map.host_matching is on, server_name is forced to None so the real host is used. Else, if subdomain_matching is off, subdomain is forced to the map's default_subdomain or ''. It returns url_map.bind_to_environ(environ, server_name, subdomain).
Without a request: if SERVER_NAME is set it returns url_map.bind using SERVER_NAME, APPLICATION_ROOT as script_name and PREFERRED_URL_SCHEME; otherwise None.

**Uncertainties.**

- Which exceptions get_host raises for an untrusted host are not visible here; callers such as the request context catch HTTPException.

<a id="u-29aec47ecf61"></a>
### `RequestContext`

`class RequestContext:` · [src/flask/ctx.py:L287-L309][f1]

RequestContext holds the per-request state for one WSGI environ: the request, URL adapter, session, flashes and after-request functions.

It is created per request and pushed and popped around dispatch. Its members have their own descriptions; push/pop maintain a stack of (token, optional pushed app context) pairs so the same context can be pushed more than once.

<a id="u-af6ab0d1d1c8"></a>
### `after_this_request`

`def after_this_request( f: ft.AfterRequestCallable[t.Any], ) -> ft.AfterRequestCallab…` · [src/flask/ctx.py:L117-L149][f1]

Registers a function to run on the response of the current request, then returns that function unchanged (so it works as a decorator).

Raises RuntimeError if no request context is active. The function is appended to the request context's _after_request_functions, which run before the registered after_request functions; it must accept and return a response.

<a id="u-aa845546ef2e"></a>
### `RequestContext.__init__`

`def __init__( self, app: Flask, environ: WSGIEnvironment, request: Request | None = N…` · [src/flask/ctx.py:L309-L335][f1]

Initializes the request context, building the request object and URL adapter unless supplied.

If request is None it creates app.request_class(environ) and sets its json_module to app.json. It calls create_url_adapter(request); if that raises an HTTPException, the exception is stored as request.routing_exception and url_adapter stays None. session defaults to the given session (None means it is opened at push time). flashes starts None, _after_request_functions empty, and the token stack empty.

<a id="u-3dbbc97062ed"></a>
### `RequestContext.__repr__`

`def __repr__(self) -> str:` · [src/flask/ctx.py:L445-L449][f1]

Returns a readable representation '<ClassName URL [METHOD] of app-name>' using the request URL and method and the app name.

<a id="u-3e474474a244"></a>
### `RequestContext.copy`

`def copy(self) -> RequestContext:` · [src/flask/ctx.py:L337-L355][f1]

Returns a new RequestContext of the same class sharing the same request object, environ and the current session object (not a reloaded one).

Allows moving a context to another greenlet; not safe for threads without locking the request.

<a id="u-0961b57c625d"></a>
### `RequestContext.match_request`

`def match_request(self) -> None:` · [src/flask/ctx.py:L357-L365][f1]

Matches the request URL using url_adapter.match(return_rule=True) and stores the rule and view args on the request.

An HTTPException from matching is caught and stored as request.routing_exception instead (url_rule and view_args remain unset). Meant as an override hook; it assumes url_adapter is not None (push checks this).

<a id="u-08409a7997e6"></a>
### `RequestContext.pop`

`def pop(self, exc: BaseException | None = _sentinel) -> None: # type: ignore` · [src/flask/ctx.py:L396-L431][f1]

Pops the request context and runs teardown on the outermost pop.

clear_request is true when exactly one token is on the stack. In that case, in the try: an omitted exc is replaced with sys.exc_info()[1], app.do_teardown_request(exc) runs, and request.close() is called if it exists. In finally (always): the current context is read, the token is popped and the variable reset; for the outermost pop, environ['werkzeug.request'] is set to None to break reference cycles; if an app context was pushed by this context it is popped with exc; then if the context read was not this one, AssertionError 'Popped wrong request context' is raised. Because the checks are in finally, an exception from teardown propagates after cleanup.

<a id="u-aa9b2b9337a6"></a>
### `RequestContext.push`

`def push(self) -> None: # Before we push the request context we have to ensure that t…` · [src/flask/ctx.py:L367-L394][f1]

Binds the request context and ensures an app context, opens the session, and matches the URL.

If there is no current app context or its app differs from this app, a new app context is created and pushed; otherwise None is remembered (nothing pushed). The request variable token and that optional app context are stored on the stack. If the session is None (first push), session_interface.open_session is called; a None result falls back to make_null_session. Re-pushes keep the existing session. If url_adapter is not None, match_request runs after the session exists so converters can use it.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/ctx.py
[f2]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/app.py
