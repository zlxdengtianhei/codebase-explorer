# WSGI Entry and Request Contexts

**Capability.** Provides the WSGI entry points that create and push request contexts, dispatch, produce responses and always pop the context.

This is where a WSGI call enters the app. It contains wsgi_app, the __call__ forwarder and builders of request contexts for real and test environs.

**Depends on.**

- [Request Dispatch Cycle](request-dispatch-cycle.md) · graph-confirmed · 1 edge(s) · The WSGI entry point runs the dispatch cycle for each request once a request context has been pushed.
- [Response Finalization and Error Fallback](response-finalization-and-error-fallback.md) · graph-confirmed · 1 edge(s)
- [App and Request Context Management](app-and-request-context-management.md) · graph-only · 1 edge(s)
- [Sansio App Base Class](sansio-app-base-class.md) · graph-only · 1 edge(s)
- [Test Client and CLI Runner](test-client-and-cli-runner.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Test Client and CLI Runner](test-client-and-cli-runner.md) · graph-only · 1 edge(s)

Parent: [Flask App Request Lifecycle](flask-app-request-lifecycle.md)

## Units (4)

<a id="u-c4752569664d"></a>
### `Flask.__call__`

`def __call__( self, environ: WSGIEnvironment, start_response: StartResponse ) -> cabc…` · [src/flask/app.py:L1529-L1536][f1]

WSGI entry point that forwards to self.wsgi_app(environ, start_response).

Kept separate so middleware can wrap wsgi_app without losing the app reference.

<a id="u-da4ac8a4efb0"></a>
### `Flask.request_context`

`def request_context(self, environ: WSGIEnvironment) -> RequestContext:` · [src/flask/app.py:L1407-L1421][f1]

Returns a new RequestContext for the given WSGI environ and this app.

It is not pushed. wsgi_app calls this for each request.

<a id="u-0f74641220cd"></a>
### `Flask.test_request_context`

`def test_request_context(self, *args: t.Any, **kwargs: t.Any) -> RequestContext:` · [src/flask/app.py:L1423-L1477][f1]

Creates a RequestContext from an environ built by the Flask EnvironBuilder from the given arguments, for tests and shells.

The testing module is imported lazily. EnvironBuilder(self, *args, **kwargs) is built, request_context(builder.get_environ()) is returned, and builder.close() always runs in finally. The returned context is not pushed.

calls: [EnvironBuilder.__init__](../../catalog.json)

<a id="u-3dbd60ee2ed7"></a>
### `Flask.wsgi_app`

`def wsgi_app( self, environ: WSGIEnvironment, start_response: StartResponse ) -> cabc…` · [src/flask/app.py:L1479-L1527][f1]

The core WSGI entry: creates and pushes a request context, dispatches, handles errors, produces the response, and always pops the context.

The try block pushes the context and calls full_dispatch_request. An Exception is saved as error and converted with handle_exception (which may re-raise it, e.g. when propagating). A non-Exception BaseException is recorded as error and re-raised. If a response exists it is called with (environ, start_response) and its iterable returned.
In finally: if environ contains 'werkzeug.debug.preserve_context', it is called with the current app and request contexts so the debugger can keep them. If error is not None and should_ignore_error(error) returns true, error is cleared. Then ctx.pop(error) runs, so teardown functions get the error unless ignored. Because response(...) runs before the pop, the context is popped before a lazy response body is iterated by the server, unless the context was preserved.

calls: [App.should_ignore_error](../../catalog.json), [Flask.handle_exception](../../catalog.json)

**Uncertainties.**

- response(environ, start_response) is an unresolved call with two candidate response implementations in the graph; the response object is normally a werkzeug Response.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/app.py
