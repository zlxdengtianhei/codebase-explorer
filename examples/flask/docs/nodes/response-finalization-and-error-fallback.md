# Response Finalization and Error Fallback

**Capability.** Turns view return values into responses, runs post-processing and session saving, and handles unhandled exceptions, with sync wrappers for async views.

Come here to follow how a view's result becomes a final response and how uncaught errors become 500 responses or propagate. It also includes the async to sync adapters and exception logging.

**Depends on.**

- [Exception Handler Lookup and Dispatch](exception-handler-lookup-and-dispatch.md) · graph-confirmed · 1 edge(s)
- [Session Interface and Cookies](session-interface-and-cookies.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Exception Handler Lookup and Dispatch](exception-handler-lookup-and-dispatch.md) · graph-confirmed · 2 edge(s)
- [Flask App Class and Utilities](flask-app-class-and-utilities.md) · graph-confirmed · 3 edge(s)
- [Request Dispatch Cycle](request-dispatch-cycle.md) · graph-confirmed · 3 edge(s) · The dispatch cycle hands view return values and unhandled errors to response finalization and the error fallback.
- [WSGI Entry and Request Contexts](wsgi-entry-and-request-contexts.md) · graph-confirmed · 1 edge(s)

Parent: [Flask App Request Lifecycle](flask-app-request-lifecycle.md)

## Units (7)

<a id="u-36a0d31a3122"></a>
### `Flask.async_to_sync`

`def async_to_sync( self, func: t.Callable[..., t.Coroutine[t.Any, t.Any, t.Any]] ) ->…` · [src/flask/app.py:L980-L1001][f1]

Wraps a coroutine function to run synchronously using asgiref's async_to_sync.

If asgiref cannot be imported it raises RuntimeError telling the user to install Flask with the 'async' extra (the ImportError is suppressed via `from None`). The import is deferred to call time. Intended as an override point.

<a id="u-3d8c7c48ff53"></a>
### `Flask.ensure_sync`

`def ensure_sync(self, func: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:` · [src/flask/app.py:L966-L978][f1]

Returns a callable safe to invoke from sync WSGI code.

If func is a coroutine function (inspect.iscoroutinefunction) it is wrapped with async_to_sync; otherwise it is returned unchanged. Intended as an override point.

<a id="u-1e825ac22ed6"></a>
### `Flask.finalize_request`

`def finalize_request( self, rv: ft.ResponseReturnValue | HTTPException, from_error_ha…` · [src/flask/app.py:L922-L951][f1]

Converts a view or handler return value to a response and runs post-processing.

make_response(rv) runs first and is outside the try, so its TypeError propagates. Then process_response and the request_finished signal are tried. On Exception: if from_error_handler is False it re-raises; if True it logs 'Request finalizing failed...' with logger.exception and swallows the error, returning the response as it was before (the one from make_response, or the one process_response had assigned only if failure came after assignment, i.e. from the signal).

<a id="u-b192bc49a6bb"></a>
### `Flask.handle_exception`

`def handle_exception(self, e: Exception) -> Response:` · [src/flask/app.py:L811-L862][f1]

Final fallback for unhandled exceptions: signals, then either re-raises (propagate) or turns the error into a 500 response.

It always sends got_request_exception. propagate comes from PROPAGATE_EXCEPTIONS config; if None it is testing or debug. If propagating, it re-raises with a bare `raise` when sys.exc_info()[1] is e, else `raise e`. Otherwise it logs via log_exception, wraps e in InternalServerError(original_exception=e), looks up a handler for it by blueprint names and, if one exists, replaces server_error with the handler's return value. The result is passed through finalize_request(..., from_error_handler=True), so after-request processing still runs and its failures are logged rather than raised.

<a id="u-d8585d22939a"></a>
### `Flask.log_exception`

`def log_exception( self, exc_info: (tuple[type, BaseException, TracebackType] | tuple…` · [src/flask/app.py:L864-L877][f1]

Logs an unhandled exception at error level on the app logger with message 'Exception on <path> [<method>]' and the given exc_info.

Reads request.path and request.method, so it needs an active request context.

<a id="u-139748148362"></a>
### `Flask.make_response`

`def make_response(self, rv: ft.ResponseReturnValue) -> Response:` · [src/flask/app.py:L1129-L1269][f1]

Coerces a view return value into a response_class instance, applying an optional status and headers.

Tuples: length 3 is (body, status, headers); length 2 is treated as (body, headers) if the second item is a Headers, dict, tuple or list, otherwise (body, status); other lengths raise TypeError. A None body raises TypeError naming request.endpoint.
If the body is not already a response_class: str/bytes/bytearray or an Iterator builds response_class(body, status, headers) and clears status/headers (the class handles them); dict or list goes through self.json.response and status/headers are applied afterwards; a werkzeug BaseResponse or any callable goes through response_class.force_type(rv, request.environ), whose TypeError is re-raised with an extended message; anything else raises TypeError describing the bad type.
Finally a non-None status sets rv.status (for str/bytes) or rv.status_code (otherwise), and truthy headers are merged into rv.headers with update. A response_class instance is only changed by the tuple's status/headers.

calls: [JSONProvider.response](../../catalog.json.gz)

**Uncertainties.**

- The graph lists two candidate response() implementations for json provider calls; which one applies depends on the app's json attribute, defined elsewhere.

<a id="u-3f6d341b30fc"></a>
### `Flask.process_response`

`def process_response(self, response: Response) -> Response:` · [src/flask/app.py:L1298-L1324][f1]

Applies after-request processing to a response and saves the session.

First the functions registered with after_this_request on the request context run in registration order. Then after_request_funcs for blueprint names (innermost first via request.blueprints order) and finally the app (None) run, each list in reversed order. Each function (through ensure_sync) receives and returns the response. Finally, if the context session is not a null session (per session_interface.is_null_session), save_session is called with the response. Exceptions from hooks or session saving propagate.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/app.py
