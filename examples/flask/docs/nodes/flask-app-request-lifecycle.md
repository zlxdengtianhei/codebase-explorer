# Flask App Request Lifecycle

**Capability.** Implements the concrete Flask application and its request lifecycle: WSGI entry, dispatch, response finalization and exception handling, grouped as the app's per-request pipeline.

Come here to trace how a WSGI call becomes a response. The Flask class and WSGI entry start the work, dispatch runs the view, and the response and error-handler modules finish results and handle failures.

**Children.**

- [Flask App Class and Utilities](flask-app-class-and-utilities.md) `flask-app-class-and-utilities` · 14 unit(s)
- [Response Finalization and Error Fallback](response-finalization-and-error-fallback.md) `response-finalization-and-error-fallback` · 7 unit(s)
- [Request Dispatch Cycle](request-dispatch-cycle.md) `request-dispatch-cycle` · 5 unit(s)
- [Exception Handler Lookup and Dispatch](exception-handler-lookup-and-dispatch.md) `exception-handler-lookup-and-dispatch` · 4 unit(s)
- [WSGI Entry and Request Contexts](wsgi-entry-and-request-contexts.md) `wsgi-entry-and-request-contexts` · 4 unit(s)

**Depends on.**

- [App and Request Context Management](app-and-request-context-management.md) · graph-confirmed · 1 edge(s) · The request lifecycle uses the app and request context classes to bind per-request state.
- [Test Client and CLI Runner](test-client-and-cli-runner.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Test Client and CLI Runner](test-client-and-cli-runner.md) · graph-confirmed · 1 edge(s) · The test client sends requests through the app's request lifecycle.

Parent: [Runtime App, Contexts and Testing](runtime-app-contexts-and-testing.md)

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.
