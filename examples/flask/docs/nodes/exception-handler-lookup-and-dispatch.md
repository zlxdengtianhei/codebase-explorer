# Exception Handler Lookup and Dispatch

**Capability.** Finds registered error handlers and decides how HTTP and other exceptions raised during dispatch are handled, trapped or re-raised.

Come here to learn how an exception is mapped to a handler or response. It includes handler lookup, HTTP exception handling, the trap decision and the generic handle-user-exception logic.

**Depends on.**

- [Response Finalization and Error Fallback](response-finalization-and-error-fallback.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Request Dispatch Cycle](request-dispatch-cycle.md) · graph-confirmed · 1 edge(s) · The dispatch cycle uses handler lookup to decide how exceptions raised during dispatch are handled.
- [Response Finalization and Error Fallback](response-finalization-and-error-fallback.md) · graph-confirmed · 1 edge(s)

Parent: [Flask App Request Lifecycle](flask-app-request-lifecycle.md)

## Units (4)

<a id="u-fd7f7a52badc"></a>
### `Flask.handle_http_exception`

`def handle_http_exception( self, e: HTTPException ) -> HTTPException | ft.ResponseRet…` · [src/flask/app.py:L744-L777][f1]

Handles an HTTPException by running a registered error handler, or returns the exception itself as the response.

Returns e unchanged if e.code is None (proxy exceptions) or if e is a RoutingException (internal redirects are never given to user handlers). Otherwise it looks up a handler via _find_error_handler(e, request.blueprints). If none is found it returns e; if found it calls the handler (wrapped with ensure_sync) with e and returns its result. Handler exceptions propagate.

calls: [App._find_error_handler](../../catalog.json.gz)

<a id="u-fae95c7207e9"></a>
### `Flask.handle_user_exception`

`def handle_user_exception( self, e: Exception ) -> HTTPException | ft.ResponseReturnV…` · [src/flask/app.py:L779-L809][f1]

Decides how an exception raised during dispatch is handled: returns a response value or re-raises.

A BadRequestKeyError gets show_exception=True when debug or the TRAP_BAD_REQUEST_ERRORS config is truthy. An HTTPException that trap_http_exception does not trap goes to handle_http_exception and its result is returned. Otherwise a handler is found via _find_error_handler; if none exists the bare `raise` re-raises the active exception (this relies on being called while that exception is being handled), else the handler is called via ensure_sync and its value returned.

calls: [Flask.handle_http_exception](../../catalog.json.gz), [App.trap_http_exception](../../catalog.json.gz)

<a id="u-947bcd626caf"></a>
### `App._find_error_handler`

`def _find_error_handler( self, e: Exception, blueprints: list[str] ) -> ft.ErrorHandl…` · [src/flask/sansio/app.py:L823-L846][f2]

Looks up the registered error handler for an exception, returning the handler callable or None.

It calls _get_exc_class_and_code(type(e)) to get the class and HTTP code (code is None for non-HTTP exceptions). Search order: code-specific first (only if code is not None), then the code-less (None) entries. Within each code level, scopes are tried in the order of the blueprints argument followed by None (app-level); so a blueprint-specific handler outranks the app one at the same code level. For each non-empty handler map, it walks exc_class.__mro__ and returns the first handler found, so the most specific class wins within a map. Empty maps are skipped; returns None when nothing matches. Note error_handler_spec is a defaultdict, so indexing [name][c] creates empty entries as a side effect of lookup.

calls: [Scaffold._get_exc_class_and_code](scaffold-base-and-setup-decorators.md#u-9b269dc0fdb3)

<a id="u-6b6469ec6169"></a>
### `App.trap_http_exception`

`def trap_http_exception(self, e: Exception) -> bool:` · [src/flask/sansio/app.py:L848-L881][f2]

Decides whether an HTTP exception should be trapped instead of handled.

Evaluated in order: if config TRAP_HTTP_EXCEPTIONS is truthy, returns True. If TRAP_BAD_REQUEST_ERRORS is None, debug is on and e is a BadRequestKeyError, returns True. If TRAP_BAD_REQUEST_ERRORS is truthy, returns isinstance(e, BadRequest). Otherwise returns False. A falsy-but-not-None TRAP_BAD_REQUEST_ERRORS (False) disables debug-based trapping. Reads config and self.debug only; no side effects.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/app.py
[f2]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/sansio/app.py
