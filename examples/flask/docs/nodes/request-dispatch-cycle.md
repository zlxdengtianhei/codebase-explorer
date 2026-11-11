# Request Dispatch Cycle

**Capability.** Runs the per-request cycle: preprocessing, dispatching to the view function, default OPTIONS response and routing exception handling.

Read this module to see the main steps from a pushed request to the view's raw return value. It holds full_dispatch_request, dispatch_request, preprocess hooks and routing error raising.

**Depends on.**

- [Exception Handler Lookup and Dispatch](exception-handler-lookup-and-dispatch.md) · graph-confirmed · 1 edge(s) · The dispatch cycle uses handler lookup to decide how exceptions raised during dispatch are handled.
- [Response Finalization and Error Fallback](response-finalization-and-error-fallback.md) · graph-confirmed · 3 edge(s) · The dispatch cycle hands view return values and unhandled errors to response finalization and the error fallback.
- [Views, Wrappers, Signals and Debug Aids](views-wrappers-signals-and-debug-aids.md) · graph-only · 1 edge(s)

**Depended on by.**

- [WSGI Entry and Request Contexts](wsgi-entry-and-request-contexts.md) · graph-confirmed · 1 edge(s) · The WSGI entry point runs the dispatch cycle for each request once a request context has been pushed.

Parent: [Flask App Request Lifecycle](flask-app-request-lifecycle.md)

## Units (5)

<a id="u-3809816834d6"></a>
### `Flask.dispatch_request`

`def dispatch_request(self) -> ft.ResponseReturnValue:` · [src/flask/app.py:L879-L902][f1]

Dispatches the current request to its view function, returning the view's raw return value (not yet a response).

If the request has a routing_exception it calls raise_routing_exception, which raises. If the matched rule has provide_automatic_options truthy (read with getattr default False) and the method is OPTIONS, it returns make_default_options_response(). Otherwise it calls view_functions[rule.endpoint] through ensure_sync with the request's view_args as keyword arguments. If url_rule is None without a routing exception, rule.endpoint would fail; that case is not handled here.

<a id="u-2c3fbb401742"></a>
### `Flask.full_dispatch_request`

`def full_dispatch_request(self) -> Response:` · [src/flask/app.py:L904-L920][f1]

Runs the full request cycle for the pushed request: marks first request, preprocess, dispatch, error handling and finalization.

It sets _got_first_request True, sends request_started, runs preprocess_request, and only if that returns None calls dispatch_request. Any Exception raised in this block is passed to handle_user_exception, whose return value becomes rv (if that re-raises, the exception propagates out). The value is always passed to finalize_request. Non-Exception BaseExceptions are not caught.

<a id="u-73709221d45d"></a>
### `Flask.make_default_options_response`

`def make_default_options_response(self) -> Response:` · [src/flask/app.py:L953-L964][f1]

Builds the default OPTIONS response: a new response_class instance whose Allow header is updated with the methods from the request context URL adapter's allowed_methods().

Relies on request_ctx.url_adapter not being None.

<a id="u-4de27b387d9d"></a>
### `Flask.preprocess_request`

`def preprocess_request(self) -> ft.ResponseReturnValue | None:` · [src/flask/app.py:L1271-L1296][f1]

Runs pre-dispatch hooks and may short-circuit with a response value.

Names are (None, *reversed(request.blueprints)). First, every url_value_preprocessor for each name is called directly with (request.endpoint, request.view_args). Then, for each name, before_request functions run through ensure_sync; the first non-None return value is returned immediately, skipping the remaining hooks and the view. Returns None if none returned a value.

<a id="u-7cc6e2e2ea33"></a>
### `Flask.raise_routing_exception`

`def raise_routing_exception(self, request: Request) -> t.NoReturn:` · [src/flask/app.py:L478-L504][f1]

Re-raises the routing exception stored on the request, except in one debug case where it raises FormDataRoutingRedirect instead.

Never returns normally.
The stored routing_exception is raised unchanged if any of these hold: not debug; it is not a RequestRedirect; its code is 307 or 308; or the request method is GET, HEAD or OPTIONS. Only for debug mode with a RequestRedirect whose code is not 307/308 and a body-carrying method does it import and raise FormDataRoutingRedirect(request).

raises: [FormDataRoutingRedirect](../../catalog.json.gz)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/app.py
