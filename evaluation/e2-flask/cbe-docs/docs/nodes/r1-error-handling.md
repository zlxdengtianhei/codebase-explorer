# Exception and Error Handling

**Capability.** Classification and resolution of exceptions raised during dispatch: handle_user_exception distinguishes HTTPExceptions (handle_http_exception) from arbitrary user exceptions, consults trap_http_exception, and resolves a handler via the sansio _find_error_handler search order; handle_exception is the last-resort 500 path that logs via log_exception and still finalizes a response.

Use this subtree to predict which handler runs for a raised exception and what happens when none matches. The lookup precedence (blueprint code, app code, blueprint class, app class) is implemented with the Scaffold key normalization; logging behavior is overridable by subclasses.

**Depends on.**

- [Sans-I/O Application Core](r1-core-app-model.md) · graph-confirmed · 1 edge(s) · Handler resolution calls Scaffold._get_exc_class_and_code to normalize exception keys during lookup.
- [Application Logging](r1-logging.md) · model-inferred · 0 edge(s)
- [Request Dispatch Pipeline](r1-request-dispatch.md) · graph-confirmed · 4 edge(s) · handle_exception calls finalize_request so even unhandled errors produce a response, forming a pipeline cycle with dispatch.
- [Scaffold Registration Base](r1-scaffold-shared-base.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Request Dispatch Pipeline](r1-request-dispatch.md) · graph-confirmed · 3 edge(s)
- [Functional Behavior Tests](r1-tests-functional.md) · model-inferred · 0 edge(s)

Parent: [Concrete WSGI Application](r1-concrete-app.md)

## Units (7)

<a id="u-fae95c7207e9"></a>
### `Flask.handle_user_exception`

`def handle_user_exception( self, e: Exception ) -> HTTPException | ft.ResponseReturnV…` · [src/flask/app.py:L779-L809][f1]

Handle an exception raised during dispatch.

For BadRequestKeyError when debug or TRAP_BAD_REQUEST_ERRORS is set, sets e.show_exception = True to show the bad key. If it is an HTTPException and trap_http_exception is false, delegate to handle_http_exception and return its result. Otherwise look up a handler via _find_error_handler(e, request.blueprints); if none exists, bare 'raise' re-raises the original exception with its traceback; else run the handler via ensure_sync and return its value.

calls: [Flask.handle_http_exception](r1-error-handling.md#u-fd7f7a52badc), [App._find_error_handler](r1-error-handling.md#u-947bcd626caf); uses: [App.trap_http_exception](r1-error-handling.md#u-6b6469ec6169)

<a id="u-fd7f7a52badc"></a>
### `Flask.handle_http_exception`

`def handle_http_exception( self, e: HTTPException ) -> HTTPException | ft.ResponseRet…` · [src/flask/app.py:L744-L777][f1]

Handle an HTTPException by routing it to a registered error handler or returning it as the response.

Order of checks: an exception with code None (proxy-style errors) is returned unchanged; an internal RoutingException (e.g. slash redirects) is returned unchanged, never passed to handlers; otherwise _find_error_handler(e, request.blueprints) is consulted — if no handler, the exception itself is returned, else the handler is run via ensure_sync and its return value returned.

calls: [App._find_error_handler](r1-error-handling.md#u-947bcd626caf)

<a id="u-b192bc49a6bb"></a>
### `Flask.handle_exception`

`def handle_exception(self, e: Exception) -> Response:` · [src/flask/app.py:L811-L862][f1]

Last-resort handling for exceptions with no handler or raised from a handler; always ends in a 500.

Captures sys.exc_info() and sends got_request_exception first. propagate is PROPAGATE_EXCEPTIONS, defaulting to (testing or debug) when config is None; if propagating, re-raise the active exception via bare raise when exc_info[1] is e, otherwise raise e. When not propagating: log via log_exception, build InternalServerError(original_exception=e), look up a handler for it (the handler always receives the InternalServerError), and return finalize_request(server_error, from_error_handler=True) so after-request processing still runs and failures inside it are logged, not raised.

**Notes.**

- side_effect: Sends the got_request_exception signal before any propagation decision.
- failure: If PROPAGATE_EXCEPTIONS/testing/debug says propagate, the exception leaves this method; the 500 response path is skipped.

calls: [App._find_error_handler](r1-error-handling.md#u-947bcd626caf), [Flask.log_exception](r1-error-handling.md#u-d8585d22939a), [Flask.finalize_request](r1-request-dispatch.md#u-1e825ac22ed6)

<a id="u-d8585d22939a"></a>
### `Flask.log_exception`

`def log_exception( self, exc_info: (tuple[type, BaseException, TracebackType] | tuple…` · [src/flask/app.py:L864-L877][f1]

Log an exception as an error on self.logger with the message 'Exception on <path> [<method>]' plus the traceback; relies on the request proxy for path and method, so it presumes an active request context.

<a id="u-947bcd626caf"></a>
### `App._find_error_handler`

`def _find_error_handler( self, e: Exception, blueprints: list[str] ) -> ft.ErrorHandl…` · [src/flask/sansio/app.py:L823-L846][f2]

Finds a registered error handler for an exception, trying in order: blueprint handler for the specific status code, app handler for the code, blueprint handler for the exception class, app handler for the class, else None.

It converts the exception type via _get_exc_class_and_code into (exc_class, code); when a code exists it searches code-keyed maps first, otherwise only the None-keyed maps. Names searched are the given blueprint names (in order) followed by None for the app level. For each handler_map it walks exc_class.__mro__ and returns the first non-None match, so the most specific exception class wins within a map.

calls: [Scaffold._get_exc_class_and_code](r1-scaffold-shared-base.md#u-9b269dc0fdb3)

**Uncertainties.**

- Ordering among the passed blueprints is the caller's responsibility; this method trusts the given list order.

<a id="u-6b6469ec6169"></a>
### `App.trap_http_exception`

`def trap_http_exception(self, e: Exception) -> bool:` · [src/flask/sansio/app.py:L848-L881][f2]

Decides whether an HTTP exception should bypass its error handler and surface as a regular traceback.

Returns True when config TRAP_HTTP_EXCEPTIONS is set. Otherwise it considers TRAP_BAD_REQUEST_ERRORS: when that key is None, debug mode is on, and the exception is a BadRequestKeyError, it returns True (implicit key errors surface in debug); when the key is truthy it returns True only for BadRequest instances; in all other cases False. Called for every HTTP exception raised by a view.

<a id="u-8c50f5d3809c"></a>
### `App.should_ignore_error`

`def should_ignore_error(self, error: BaseException | None) -> bool:` · [src/flask/sansio/app.py:L883-L891][f2]

Hook consulted by the teardown system: when it returns True, teardown handlers are not passed the error.

The default implementation always returns False, so no teardown error is ignored unless a subclass overrides it.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/app.py
[f2]: ../../../../../../eval/flask-85c5d93/src/flask/sansio/app.py
