# Request Dispatch Pipeline

**Capability.** The WSGI entry (wsgi_app kept separate from __call__ so middleware can wrap it) and the ordered stages: full_dispatch_request runs preprocess hooks, dispatch_request matches and invokes the view (raising routing exceptions and serving automatic OPTIONS), finalize_request converts the return value via make_response and runs after-request hooks. ensure_sync/async_to_sync make coroutine hooks and views callable synchronously.

Read this subtree top-down to trace one request: __call__ to wsgi_app, full_dispatch_request through dispatch_request, then finalize_request. Response conversion rules live in make_response; hook execution order is fixed by this pipeline.

**Depends on.**

- [App and Request Contexts](r1-contexts-teardown.md) · graph-confirmed · 1 edge(s) · wsgi_app calls request_context to create the request context that scopes dispatch.
- [Diagnostics and Debug Errors](r1-debug-helpers.md) · graph-confirmed · 1 edge(s) · raise_routing_exception raises FormDataRoutingRedirect to give clear assertions for form-routing mistakes.
- [Exception and Error Handling](r1-error-handling.md) · graph-confirmed · 3 edge(s)
- [JSON Serialization](r1-json-support.md) · model-inferred · 0 edge(s) · jsonify delegates to the current app's JSONProvider for response serialization.
- [Session Support](r1-sessions.md) · graph-confirmed · 1 edge(s) · process_response invokes the session interface to save the session into the outgoing response.

**Depended on by.**

- [Exception and Error Handling](r1-error-handling.md) · graph-confirmed · 4 edge(s) · handle_exception calls finalize_request so even unhandled errors produce a response, forming a pipeline cycle with dispatch.
- [Functional Behavior Tests](r1-tests-functional.md) · model-inferred · 0 edge(s)
- [Helper and Resource Tests](r1-tests-helpers.md) · model-inferred · 0 edge(s)
- [App and Request Contexts](r1-contexts-teardown.md) · graph-only · 2 edge(s)
- [Template Rendering](r1-templating.md) · graph-only · 1 edge(s)

Parent: [Concrete WSGI Application](r1-concrete-app.md)

## Units (12)

<a id="u-c4752569664d"></a>
### `Flask.__call__`

`def __call__( self, environ: WSGIEnvironment, start_response: StartResponse ) -> cabc…` · [src/flask/app.py:L1529-L1536][f1]

WSGI-server entry point; delegates directly to wsgi_app so middlewares wrapping wsgi_app keep the app object intact.

<a id="u-3dbd60ee2ed7"></a>
### `Flask.wsgi_app`

`def wsgi_app( self, environ: WSGIEnvironment, start_response: StartResponse ) -> cabc…` · [src/flask/app.py:L1479-L1527][f1]

The actual WSGI entry point, kept separate from __call__ so middleware can wrap wsgi_app without losing the app object.

Creates a RequestContext and pushes it, then runs full_dispatch_request. Exception handling: an Exception becomes error=e and response=handle_exception(e) (a 500 path); a bare except captures error=sys.exc_info()[1] and re-raises (non-Exception BaseExceptions propagate). Otherwise response(environ, start_response) is returned. The finally block always: hands the current app and request contexts to werkzeug.debug.preserve_context when present in the environ; clears error when should_ignore_error(error) is true; and pops the context with ctx.pop(error), which drives teardown functions with the captured exception.

**Notes.**

- failure: BaseException (non-Exception) bypasses handle_exception and re-raises, but the context still pops with the error in finally.
- side_effect: In debug preserve_context mode, the app and request contexts are registered with the Werkzeug debugger so locals survive across requests.

calls: [Flask.full_dispatch_request](r1-request-dispatch.md#u-2c3fbb401742), [Flask.handle_exception](r1-error-handling.md#u-b192bc49a6bb); uses: [App.should_ignore_error](r1-error-handling.md#u-8c50f5d3809c)

**Uncertainties.**

- The response(environ, start_response) call resolves to whichever Response object full_dispatch_request returned; its exact WSGI iterable behavior is defined in wrappers, not here.

<a id="u-2c3fbb401742"></a>
### `Flask.full_dispatch_request`

`def full_dispatch_request(self) -> Response:` · [src/flask/app.py:L904-L920][f1]

Top-level request pipeline: set _got_first_request True, send request_started, run preprocess_request, and use dispatch_request only when no before-request returned a value.

Any Exception from that sequence goes to handle_user_exception, whose result (response value or handled HTTPException) is passed to finalize_request and returned.

**Notes.**

- side_effect: Marks the app as having handled its first request, which gates the once-only before_first_request-style semantics elsewhere.

calls: [Flask.preprocess_request](r1-request-dispatch.md#u-4de27b387d9d), [Flask.dispatch_request](r1-request-dispatch.md#u-3809816834d6), [Flask.handle_user_exception](r1-error-handling.md#u-fae95c7207e9), [Flask.finalize_request](r1-request-dispatch.md#u-1e825ac22ed6)

<a id="u-3809816834d6"></a>
### `Flask.dispatch_request`

`def dispatch_request(self) -> ft.ResponseReturnValue:` · [src/flask/app.py:L879-L902][f1]

Match the current request to a view and invoke it, returning the raw view value (not necessarily a Response).

If req.routing_exception is set, pass it to raise_routing_exception (which re-raises or swaps in a debug error). Take req.url_rule as the matched rule; when the rule provides automatic options and the method is OPTIONS, return make_default_options_response() without calling the view. Otherwise call the endpoint's view function from view_functions via ensure_sync with req.view_args as kwargs.

calls: [Flask.raise_routing_exception](r1-request-dispatch.md#u-7cc6e2e2ea33), [Flask.make_default_options_response](r1-request-dispatch.md#u-73709221d45d)

<a id="u-4de27b387d9d"></a>
### `Flask.preprocess_request`

`def preprocess_request(self) -> ft.ResponseReturnValue | None:` · [src/flask/app.py:L1271-L1296][f1]

Run pre-dispatch hooks.

Names are (None, *reversed(request.blueprints)): app-level first, then innermost blueprint outward. First all url_value_preprocessors for those names run with (request.endpoint, request.view_args) with no early exit; then before_request_funcs run in the same name order via ensure_sync, and the first non-None return value is returned immediately, short-circuiting the view; otherwise None is returned.

**Notes.**

- contract: A non-None before_request return value replaces the view entirely and flows through the normal response pipeline.

<a id="u-3f6d341b30fc"></a>
### `Flask.process_response`

`def process_response(self, response: Response) -> Response:` · [src/flask/app.py:L1298-L1324][f1]

Run after-request hooks over the response.

First ctx._after_request_functions (attached to the actual context object, not the proxy) run in insertion order, then after_request_funcs per name in request.blueprints order with each name's list reversed (reverse registration order), each via ensure_sync and reassigning response. Finally, unless the session is a null session, session_interface.save_session(self, ctx.session, response) persists the session onto the response. The returned response must be a response_class instance.

**Notes.**

- contract: Blueprint-level after-request functions run before the app-level (None) ones; within each list, last registered runs first.

calls: [SecureCookieSessionInterface](r1-sessions.md#u-560666a526c4)

<a id="u-1e825ac22ed6"></a>
### `Flask.finalize_request`

`def finalize_request( self, rv: ft.ResponseReturnValue | HTTPException, from_error_ha…` · [src/flask/app.py:L922-L951][f1]

Convert a view or error-handler return value into a finished Response: make_response(rv), then process_response and send request_finished.

If processing raises: when from_error_handler is false the exception propagates; when true (error path), it is logged with logger.exception('Request finalizing failed with an error while handling an error') and the response produced so far is returned.

**Notes.**

- failure: Safe mode (from_error_handler=True) swallows and logs processing failures instead of raising.

calls: [Flask.make_response](r1-request-dispatch.md#u-139748148362), [Flask.process_response](r1-request-dispatch.md#u-3f6d341b30fc)

<a id="u-139748148362"></a>
### `Flask.make_response`

`def make_response(self, rv: ft.ResponseReturnValue) -> Response:` · [src/flask/app.py:L1129-L1269][f1]

Convert any allowed view return value into a response_class instance; None and invalid types are errors.

Tuple unpacking: a 3-tuple is (body, status, headers); a 2-tuple is (body, headers) when the second element is Headers/dict/tuple/list, else (body, status); any other tuple length raises TypeError. After unpacking, a None body raises TypeError naming request.endpoint and stating the view returned None or fell off the end. Body conversion, applied only when rv is not already self.response_class: str/bytes/bytearray or any Iterator (streaming) becomes response_class(rv, status=status, headers=headers) with status/headers cleared; dict or list is JSON-encoded via self.json.response; a foreign BaseResponse instance or WSGI callable is coerced with response_class.force_type(rv, request.environ), and a TypeError from that is re-raised as a descriptive TypeError with the original traceback chained; anything else raises the generic TypeError listing accepted types. Afterwards, a tuple-provided status is applied (string/bytes forms set rv.status, others rv.status_code) and provided headers are merged with rv.headers.update(headers).

**Notes.**

- failure: force_type failures and unknown return types both surface as TypeError; the first includes the original Werkzeug message and traceback.

**Uncertainties.**

- headers type (HeadersValue) and json.response behavior are defined in other modules.

<a id="u-73709221d45d"></a>
### `Flask.make_default_options_response`

`def make_default_options_response(self) -> Response:` · [src/flask/app.py:L953-L964][f1]

Build the automatic OPTIONS response: take allowed_methods() from the request context's url_adapter, create an empty response_class instance, and set its Allow header to those methods via rv.allow.update(methods).

<a id="u-3d8c7c48ff53"></a>
### `Flask.ensure_sync`

`def ensure_sync(self, func: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:` · [src/flask/app.py:L966-L978][f1]

Return func unchanged when it is a plain def; when iscoroutinefunction(func) is true, return self.async_to_sync(func), a synchronous wrapper.

Override point for changing async view execution.

calls: [Flask.async_to_sync](r1-request-dispatch.md#u-36a0d31a3122)

<a id="u-36a0d31a3122"></a>
### `Flask.async_to_sync`

`def async_to_sync( self, func: t.Callable[..., t.Coroutine[t.Any, t.Any, t.Any]] ) ->…` · [src/flask/app.py:L980-L1001][f1]

Convert a coroutine function into a synchronously callable function using asgiref's async_to_sync.

If asgiref is not installed, raise RuntimeError with a message telling the user to install the 'async' extra; the original ImportError is suppressed (raise ... from None). Otherwise return asgiref_async_to_sync(func).

<a id="u-7cc6e2e2ea33"></a>
### `Flask.raise_routing_exception`

`def raise_routing_exception(self, request: Request) -> t.NoReturn:` · [src/flask/app.py:L478-L504][f1]

Re-raise a routing exception attached to the request, substituting a clearer error in one debug-mode case.

If debug is off, the exception is not a RequestRedirect, its code is 307 or 308, or the request method is GET/HEAD/OPTIONS, the original routing_exception is raised unchanged. Otherwise (debug mode, a redirect that would discard the request body) import and raise FormDataRoutingRedirect instead. Declared NoReturn: always raises.

raises: [FormDataRoutingRedirect](r1-debug-helpers.md#u-8135e71c270a); uses: [Flask.dispatch_request](r1-request-dispatch.md#u-3809816834d6)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/app.py
