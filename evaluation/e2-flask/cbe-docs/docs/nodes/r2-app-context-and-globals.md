# Application and Request Contexts

**Capability.** Owns the runtime context machinery: AppContext and RequestContext push/pop, the `g` namespace, and the ContextVar-backed global proxies that make app and request state visible to application code.

Use this subtree to understand how app and request state is scoped and accessed via proxies. Readers handling concurrency, teardown, or custom state should start with AppContext and RequestContext, then globals.py for the public proxies.

**Children.**

- [Context and Signal Tests](r2-context-lifecycle-tests.md) `r2-context-lifecycle-tests` · 10 unit(s)

**Depends on.**

- [Flask Framework](r2-flask-framework.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r2-app-context-and-globals ` → ` r2-flask-framework `)
- [URL Building, Redirects, and Resources](r1-url-building-resources.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Context and Signal Tests](r2-context-lifecycle-tests.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r2-context-lifecycle-tests ` → ` r2-app-context-and-globals `)
- [Shared Helpers](r2-helpers-utilities.md) · model-inferred · 0 edge(s)
- [Request and Response Helpers](r2-request-response-helpers.md) · model-inferred · 0 edge(s)
- [stream\_with\_context](r2-streaming-helpers.md) · model-inferred · 0 edge(s)
- [App and Request Contexts](r1-contexts-teardown.md) · graph-only · 2 edge(s)

Parent: [Flask Framework](r2-flask-framework.md)

## Units (8)

<a id="u-9b040980ce77"></a>
### `AppContext`

`class AppContext:` · [src/flask/ctx.py:L238-L245][f1]

Holds application-scoped state for one app context: the app, its URL adapter, a fresh `g` namespace, and a token stack for contextvars rebinding.

`__init__` stores the app, builds `url_adapter` via `app.create_url_adapter(None)`, instantiates `app.app_ctx_globals_class()`, and starts `_cv_tokens` empty. `push` binds the context with `_cv_app.set` (recording the token) and sends the `appcontext_pushed` signal with an async wrapper. `pop` runs `app.do_teardown_appcontext(exc)` on the last token, where `exc` defaults to the current in-flight exception from `sys.exc_info()` when the `_sentinel` default is kept; teardown runs in a `try`, and the contextvars token is reset in a `finally` so unbinding happens even if teardown raises. Afterwards it asserts the popped context is itself, raising `AssertionError` with both reprs on mismatch, then sends `appcontext_popped`. `__enter__` pushes and returns self; `__exit__` pops with the caught exception value.

calls: [Flask.create_url_adapter](r1-url-building-resources.md#u-6afa91f86588); uses: [_AppCtxGlobals](r2-app-context-and-globals.md#u-0fcc88751f58), [ctx.py module code (L1–L28)][f1]

**Uncertainties.**

- Ordering and error semantics of `do_teardown_appcontext` live in app.py, not visible here.

<a id="u-29aec47ecf61"></a>
### `RequestContext`

`class RequestContext:` · [src/flask/ctx.py:L287-L309][f1]

Per-request context carrying the request object, URL adapter, session, after-request callbacks, and a token stack; pushed/popped around each request.

`__init__` stores the app; if no `request` is given it builds `app.request_class(environ)` and sets `request.json_module = app.json`. It then tries `app.create_url_adapter(self.request)`, storing an `HTTPException` as `request.routing_exception` instead of propagating (routing errors surface later). `flashes` starts None, `session` starts as the given value or None, and `_after_request_functions` starts empty. `push` first ensures a matching app context: if none is active or it belongs to a different app it creates and pushes one, recording it in the token tuple so pop can unwind it. It binds itself with `_cv_request.set`, opens the session only on first push (falling back to `make_null_session`), and calls `match_request()` when a URL adapter exists — after session loading so converters can see the session. `pop` (when this is the outermost push) resolves the sentinel `exc` from `sys.exc_info()`, runs `app.do_teardown_request(exc)`, and closes the request if it has a `close` method; in a `finally` it resets the request contextvar, clears `environ['werkzeug.request']` on the last pop, pops and pops any paired app context with the same `exc`, then raises `AssertionError` if the popped context is not self. `copy` builds a new context reusing the same request, environ, and session objects. `match_request` sets `request.url_rule`/`view_args` from `url_adapter.match(return_rule=True)` or records an `HTTPException` as `routing_exception`. `__enter__`/`__exit__` push and pop with the exception value; `__repr__` shows URL, method, and app name.

calls: [Flask.create_url_adapter](r1-url-building-resources.md#u-6afa91f86588), [RequestContext](r2-app-context-and-globals.md#u-29aec47ecf61); uses: [AppContext](r2-app-context-and-globals.md#u-9b040980ce77), [after_this_request](r2-app-context-and-globals.md#u-af6ab0d1d1c8)

**Uncertainties.**

- Which side consumes `routing_exception` (URL matching error surface) is outside this file.
- Exact semantics of `do_teardown_request` are defined in app.py.
- Whether pop's AssertionError aborts remaining cleanup when raised inside `finally` is source-visible but its downstream effect is not.

<a id="u-0fcc88751f58"></a>
### `_AppCtxGlobals`

`class _AppCtxGlobals:` · [src/flask/ctx.py:L29-L52][f1]

Namespace object backing Flask's `g`, storing per-app-context data as arbitrary attributes in its instance dict.

`__getattr__` reads `self.__dict__[name]` and converts a missing key to `AttributeError(name)`; `__setattr__` and `__delattr__` write/delete the dict, with `__delattr__` also converting missing keys to `AttributeError`. `get`, `pop`, `setdefault` mirror their dict equivalents; `pop` distinguishes whether a default was supplied via the module-level `_sentinel`, so a stored `_sentinel` value is indistinguishable from no default. `__contains__` and `__iter__` expose dict membership and key iteration. `__repr__` returns `<flask.g of 'appname'>` when an app context is currently bound in `_cv_app`, otherwise falls back to `object.__repr__`; it does not raise when no context is active.

group: [_AppCtxGlobals](r2-app-context-and-globals.md#u-0fcc88751f58); uses: [ctx.py module code (L1–L28)][f1]

<a id="u-af6ab0d1d1c8"></a>
### `after_this_request`

`def after_this_request( f: ft.AfterRequestCallable[t.Any], ) -> ft.AfterRequestCallab…` · [src/flask/ctx.py:L117-L149][f1]

Registers a function to run on the current request's response after the view returns.

It looks up the active request context via `_cv_request.get(None)`; if none is active it raises `RuntimeError` naming the restriction. Otherwise it appends the callable to the context's `_after_request_functions` list and returns the function unchanged. These callbacks run before regular after-request functions, but who consumes the list lives outside this file.

uses: [RequestContext](r2-app-context-and-globals.md#u-29aec47ecf61)

**Uncertainties.**

- The consumer of `_after_request_functions` (order/guarantees of invocation) is not in this file.

<a id="u-44e6c4d67a2f"></a>
### `copy_current_request_context`

`def copy_current_request_context(f: F) -> F:` · [src/flask/ctx.py:L155-L189][f1]

Decorator that captures a copy of the active request context so the wrapped function can run elsewhere (e.g. a greenlet) with request/session access.

At decoration time it reads the request context from `_cv_request`; without one it raises `RuntimeError`. It copies the context via `ctx.copy()` and returns a wrapper that, on each call, enters the copied context (`with ctx:`) and invokes `ctx.app.ensure_sync(f)(*args, **kwargs)`. `update_wrapper` copies the wrapped function's metadata onto the wrapper. The copy shares the same request object, so concurrent access from threads would need external locking per RequestContext.copy's documented caveat.

calls: [RequestContext](r2-app-context-and-globals.md#u-29aec47ecf61); group: [copy_current_request_context](r2-app-context-and-globals.md#u-44e6c4d67a2f)

**Uncertainties.**

- `ensure_sync` behavior (sync/async bridging) is defined in app.py, not visible here.

<a id="u-ae4d007c82d0"></a>
### `has_app_context`

`def has_app_context() -> bool:` · [src/flask/ctx.py:L228-L235][f1]

Returns True when an app context is currently active, by checking `_cv_app.get(None) is not None`.

No side effects.

<a id="u-9d1faad5d98c"></a>
### `has_request_context`

`def has_request_context() -> bool:` · [src/flask/ctx.py:L196-L225][f1]

Returns True when a request context is currently active, by checking `_cv_request.get(None) is not None`.

No side effects.

<a id="u-6371f70e8a7d"></a>
### `globals.py module code (L1–L51)`

`module_region` · [src/flask/globals.py:L1-L51][f2]

Defines Flask's proxy globals via ContextVars and Werkzeug LocalProxy.

_cv_app and _cv_request store the active app and request contexts; app_ctx, current_app, and g proxy the app context (current_app and g access 'app'/'g' attributes), while request_ctx, request, and session proxy the request context. Accessing any proxy outside its context raises Werkzeug's unbound error carrying the module's explanatory messages about working outside application or request context.

**Uncertainties.**

- The exact resolution order of LocalProxy attribute lookup versus unbound-message raising is Werkzeug behavior not shown here

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/ctx.py
[f2]: ../../../../../../eval/flask-85c5d93/src/flask/globals.py
