# Context and Signal Tests

**Capability.** Verifies context lifecycle: app-context and request signals ordering, teardown behavior, `g` and url_for requirements, and a session interface that drives request matching manually.

Read these tests to confirm when context signals fire relative to handlers and views, and what remains valid during teardown. test_appctx pins the `g` object and app-context lifecycle; test_session_interface exercises RequestContext.match_request directly.

**Depends on.**

- [Application and Request Contexts](r2-app-context-and-globals.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r2-context-lifecycle-tests ` → ` r2-app-context-and-globals `)
- [App and Request Contexts](r1-contexts-teardown.md) · graph-only · 11 edge(s)
- [Scaffold Registration Base](r1-scaffold-shared-base.md) · graph-only · 5 edge(s)

Parent: [Application and Request Contexts](r2-app-context-and-globals.md)

## Units (10)

<a id="u-e470bc6fa0dc"></a>
### `test_appcontext_signals`

`def test_appcontext_signals(app, client):` · [tests/test_signals.py:L115-L118][f1]

appcontext_pushed and appcontext_popped fire around a request: one 'push' record before the response and one 'pop' after, in that order.

Receivers accept **kwargs beyond sender. Disconnected in finally.

<a id="u-05247d9d9d28"></a>
### `test_appcontext_tearing_down_signal`

`def test_appcontext_tearing_down_signal(app, client):` · [tests/test_signals.py:L163-L167][f1]

With app.testing = False, a view raising ZeroDivisionError results in a 500 response, and appcontext_tearing_down fires once during teardown, receiving the ZeroDivisionError instance as exc.

Receiver disconnected in finally.

<a id="u-1da7bed56d2c"></a>
### `test_before_render_template`

`def test_before_render_template():` · [tests/test_signals.py:L25-L28][f1]

A before_render_template receiver mutates context['whiskey'] to 43 before rendering; the response body becomes b'<h1>43</h1>' and one signal is recorded with template name 'simple_template.html'.

Receiver is disconnected in a finally block.

<a id="u-2d93433f310d"></a>
### `test_flash_signal`

`def test_flash_signal(app):` · [tests/test_signals.py:L139-L140][f1]

A route flashes 'This is a flash message' with category 'notice' and redirects; flask.flash fires message_flashed exactly once with those message and category values.

The test opens a session via session_transaction to enable flashing, then requests the route; receiver disconnected in finally.

**Uncertainties.**

- Why the session_transaction context is required for the flash to be recorded is not shown in this file

<a id="u-814ed6971cc5"></a>
### `test_request_exception_signal`

`def test_request_exception_signal():` · [tests/test_signals.py:L95-L99][f1]

A view raising ZeroDivisionError produces a 500 response and fires got_request_exception once, with the receiver receiving that ZeroDivisionError instance as the exception argument.

Signal disconnected in finally.

<a id="u-9eceb9a304b0"></a>
### `test_request_signals`

`def test_request_signals():` · [tests/test_signals.py:L50-L54][f1]

Establishes total ordering of request lifecycle callbacks: request_started signal, before_request handler, view, after_request handler, then request_finished signal.

The after_request handler replaces the response body with 'stuff' (view's 'ignored anyway' is discarded), and the request_finished receiver asserts it sees that body. The ordered calls list is asserted exactly; signals are disconnected in finally.

<a id="u-f00fd50c0732"></a>
### `test_template_rendered`

`def test_template_rendered(app, client):` · [tests/test_signals.py:L4-L5][f1]

Connects a record receiver to flask.template_rendered for this app, requests a route rendering simple_template.html with whiskey=42, and asserts exactly one signal carrying the template (name 'simple_template.html') and context with whiskey == 42.

Disconnects in finally even on failure.

<a id="u-aa07dd482f7c"></a>
### `test_signals.py module code (L1–L3)`

`module_region` · [tests/test_signals.py:L1-L3][f1]

Module imports only flask; all behavior lives in the test functions.

<a id="u-d465f22b9252"></a>
### `test_appctx.py-app-context`

`def test_basic_url_generation(app):` · [tests/test_appctx.py:L8-L12][f2]

Tests for Flask app-context lifecycle, url_for requirements, and the `g` object.

URL generation: with an app context and SERVER_NAME plus PREFERRED_URL_SCHEME set, url_for('index') yields the absolute https URL; without SERVER_NAME, or without any app context, url_for raises RuntimeError. `current_app` proxies to the active app for both app contexts and test request contexts, and is falsy after the context pops. Teardown callbacks registered with teardown_appcontext run once when the context pops: they receive None when exceptions were absent or handled (by an except block, or by an Exception errorhandler during a client request), but receive the original exception when PROPAGATE_EXCEPTIONS is on and the exception escapes the client request (the ValueError propagates out of client.get while cleanup records it). `flask.g` behaves as a dict-like namespace: get returns None or the default, __contains__ reflects attributes, setdefault keeps the first value, pop raises KeyError on a missing key unless a default is given, __iter__ lists set attributes, and repr shows '<flask.g of 'app name'>'. Setting app.app_ctx_globals_class to a custom class makes `g.spam` available in templates. test_context_refcounts confirms teardown_request and teardown_appcontext fire in that order for a client request that nests additional contexts. test_clean_pop, with testing disabled, shows a teardown_request callback that raises ZeroDivisionError does not stop the app-context teardown callback from running afterwards.

calls: [Flask.app_context](r1-contexts-teardown.md#u-2e69ab7b3042), [Flask.test_request_context](r1-contexts-teardown.md#u-0f74641220cd)

**Uncertainties.**

- The exact dispatch path converting a raised view exception into the teardown argument is in src/flask and only observable here via assertions

<a id="u-6981010d0e66"></a>
### `test_open_session_with_endpoint`

`def test_open_session_with_endpoint():` · [tests/test_session_interface.py:L6-L12][f3]

Verifies a session interface that needs URL-matching results can call request_ctx.match_request() manually during open_session.

The custom MySessionInterface defines no-op save_session and an open_session that calls request_ctx.match_request() then asserts request.endpoint is not None. The test installs it on a fresh Flask app, maps GET '/', and asserts the request returns 200, so open_session ran without the endpoint assertion failing.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/tests/test_signals.py
[f2]: ../../../../../../eval/flask-85c5d93/tests/test_appctx.py
[f3]: ../../../../../../eval/flask-85c5d93/tests/test_session_interface.py
