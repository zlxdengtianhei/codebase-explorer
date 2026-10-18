# Error Handler Tests

**Capability.** Pins Flask's error-handler resolution and registration validation for app-level handlers, including which exceptions match which handlers and invalid registration forms.

Read this to understand handler lookup precedence and the validation errors raised for malformed registrations. Cross-reference blueprint-scoped handler tests in blueprint-tests.

Parent: [Flask Framework](r2-flask-framework.md)

## Units (1)

<a id="u-2fa158c13689"></a>
### `test_user_error_handler.py-error-dispatch`

`def test_error_handler_no_match(app, client):` · [tests/test_user_error_handler.py:L10-L11][f1]

Tests for Flask's error-handler resolution and registration validation.

Registration checks: register_error_handler raises TypeError for an exception instance ('CustomException() is an instance, not a class.'), ValueError for a non-Exception class (list), and ValueError for an integer code that is not a valid HTTPException code (999). Subclass dispatch (non-HTTP): an unhandled child of a registered parent falls back to the parent handler ('parent'), while a directly registered child wins over the parent. HTTP subclasses: a 403-code handler receives plain Forbidden and any unregistered Forbidden subclass (matching by code), while a class-registered Forbidden subclass wins for its own type. Blueprint scoping: a blueprint errorhandler(500) handles 500s only for blueprint routes, while the app handler covers app routes. Default handlers: registering errorhandler(HTTPException) catches any HTTPException including 404 routing misses, but not the RequestRedirect produced when following the trailing-slash redirect (GET /slash follows through to the view's own body). Specific handlers (Forbidden) beat the HTTPException catch-all on both app and blueprint levels. TestGenericHandlers explores generic handlers with PROPAGATE_EXCEPTIONS False: handlers keyed on InternalServerError or 500 are aliases and receive only InternalServerError — wrapping the original exception when one exists (reporting 'wrapped KeyError'/'wrapped Custom') and 'direct InternalServerError' for plain abort(500) or explicit raises; errorhandler(HTTPException) receives only HTTPExceptions including routing 404; errorhandler(Exception) receives everything directly, including HTTPExceptions ('direct NotFound') and aborts ('direct InternalServerError').

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/tests/test_user_error_handler.py
