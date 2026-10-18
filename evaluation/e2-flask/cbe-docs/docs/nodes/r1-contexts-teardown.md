# App and Request Contexts

**Capability.** Creation (not pushing) of AppContext and RequestContext objects and the teardown machinery that runs registered functions just before each context pops. test_request_context builds a synthetic environ via EnvironBuilder so tests can drive the same context stack.

Use this subtree to understand context lifetimes: pushing a request context pushes an app context, and do_teardown_request/do_teardown_appcontext drain the hook lists at pop time. Most code interacts with these through the with-statement helpers.

**Depends on.**

- [Request Dispatch Pipeline](r1-request-dispatch.md) · graph-only · 2 edge(s)
- [Application and Request Contexts](r2-app-context-and-globals.md) · graph-only · 2 edge(s)
- [Scaffold Registration Base](r1-scaffold-shared-base.md) · graph-only · 1 edge(s)
- [Testing Support](r2-testing-support.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Request Dispatch Pipeline](r1-request-dispatch.md) · graph-confirmed · 1 edge(s) · wsgi_app calls request_context to create the request context that scopes dispatch.
- [Functional Behavior Tests](r1-tests-functional.md) · graph-confirmed · 3 edge(s)
- [Context and Signal Tests](r2-context-lifecycle-tests.md) · graph-only · 11 edge(s)
- [Logging Test Suite](r2-logging-tests.md) · graph-only · 1 edge(s)

Parent: [Concrete WSGI Application](r1-concrete-app.md)

## Units (6)

<a id="u-2e69ab7b3042"></a>
### `Flask.app_context`

`def app_context(self) -> AppContext:` · [src/flask/app.py:L1386-L1405][f1]

Create (not push) an AppContext bound to this app; pushing it with a with block makes current_app point here and runs the app-context teardowns on pop.

Request handling and CLI commands push one automatically.

calls: [AppContext](r2-app-context-and-globals.md#u-9b040980ce77)

<a id="u-da4ac8a4efb0"></a>
### `Flask.request_context`

`def request_context(self, environ: WSGIEnvironment) -> RequestContext:` · [src/flask/app.py:L1407-L1421][f1]

Create (not push) a RequestContext for a WSGI environ; pushing it makes request active and pushes an app context.

Normal requests get this from wsgi_app; tests should use test_request_context.

calls: [RequestContext](r2-app-context-and-globals.md#u-29aec47ecf61)

<a id="u-0f74641220cd"></a>
### `Flask.test_request_context`

`def test_request_context(self, *args: t.Any, **kwargs: t.Any) -> RequestContext:` · [src/flask/app.py:L1423-L1477][f1]

Create a RequestContext from a synthetic environ built by flask.testing.EnvironBuilder(self, *args, **kwargs), accepting EnvironBuilder's arguments (path, base_url, subdomain, url_scheme, data, json, ...).

The environ is obtained with builder.get_environ() and passed to self.request_context; builder.close() runs in a finally block whether or not context creation succeeds.

calls: [EnvironBuilder](r2-testing-support.md#u-84a78615434e), [Flask.request_context](r1-contexts-teardown.md#u-da4ac8a4efb0)

<a id="u-8e0454a8887a"></a>
### `Flask.do_teardown_request`

`def do_teardown_request( self, exc: BaseException | None = _sentinel, # type: ignore[…` · [src/flask/app.py:L1326-L1358][f1]

Run request teardown before the request context pops.

exc defaults to _sentinel; when so, it is taken from sys.exc_info()[1]. Functions run per name over chain(request.blueprints, (None,)) — blueprints first, then app level — each list reversed and called via ensure_sync with exc. Then the request_tearing_down signal is sent with exc. Exceptions from teardown functions are not caught here; they propagate to the context pop logic.

**Notes.**

- side_effect: Teardown functions run even when the dispatch raised; the exception is passed as an argument, not swallowed.

<a id="u-5275f696c753"></a>
### `Flask.do_teardown_appcontext`

`def do_teardown_appcontext( self, exc: BaseException | None = _sentinel, # type: igno…` · [src/flask/app.py:L1360-L1384][f1]

Run app-context teardown before the app context pops.

exc defaults from sys.exc_info()[1] when the _sentinel is passed. All teardown_appcontext_funcs run in reverse registration order via ensure_sync with exc, then the appcontext_tearing_down signal is sent. Called by AppContext.pop.

**Notes.**

- side_effect: Runs during both normal and error unwinding of the app context.

<a id="u-6b3e4a9135e9"></a>
### `App.teardown_appcontext`

`def teardown_appcontext(self, f: T_teardown) -> T_teardown:` · [src/flask/sansio/app.py:L778-L810][f2]

Registers a function to run when the application context is popped (after each request, at the end of CLI commands, or when a manually pushed context ends), appending it to teardown_appcontext_funcs and returning f so it can be used as a decorator.

Per the contract, an unhandled exception is passed to the function as an argument unless an errorhandler handled it; teardown functions must not raise, and their return values are ignored. Guarded by @setupmethod.

uses: [setupmethod](r1-scaffold-shared-base.md#u-81ccd06c4290)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/app.py
[f2]: ../../../../../../eval/flask-85c5d93/src/flask/sansio/app.py
