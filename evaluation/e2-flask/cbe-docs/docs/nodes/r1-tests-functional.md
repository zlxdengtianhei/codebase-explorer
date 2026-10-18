# Functional Behavior Tests

**Capability.** End-to-end tests of core app behavior in test_basic.py, test_regression.py, test_converters.py, test_reqctx.py, test_request.py, test_subclassing.py, and the typing fixtures: routing and OPTIONS, sessions and cookies, lifecycle hooks, flashing, error-handler resolution, response/JSON conversion, URL building, SERVER_NAME/subdomains, run/teardown, context push/pop semantics, request limits, converter registration, and regression coverage for abort/redirect delivery.

Read these groups as executable specs: each covers one behavioral area via test clients and request contexts. test_reqctx is the authority on context push/pop and teardown; test_basic is the broadest coverage surface.

**Depends on.**

- [App and Request Contexts](r1-contexts-teardown.md) · graph-confirmed · 3 edge(s)
- [Exception and Error Handling](r1-error-handling.md) · model-inferred · 0 edge(s)
- [Request Dispatch Pipeline](r1-request-dispatch.md) · model-inferred · 0 edge(s)
- [Scaffold Registration Base](r1-scaffold-shared-base.md) · graph-only · 4 edge(s)
- [CLI Entry and Test Support](r1-app-test-support.md) · graph-only · 2 edge(s)
- [Helper and Resource Tests](r1-tests-helpers.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Helper and Resource Tests](r1-tests-helpers.md) · graph-only · 3 edge(s)
- [JSON Serialization](r1-json-support.md) · graph-only · 1 edge(s)
- [Configuration Loading](r2-configuration.md) · graph-only · 1 edge(s)

Parent: [Test Suites and Fixture Apps](r1-tests.md)

## Units (19)

<a id="u-d529fc3aa421"></a>
### `test-basic-py-url-mapping-and-routing`

`def test_request_dispatching(app, client):` · [tests/test_basic.py:L129-L130][f1]

Tests URL rule registration, dispatch, and view lookup.

test_request_dispatching verifies default GET rules auto-add HEAD/OPTIONS (405 with Allow list for POST/DELETE) and explicit methods lists work. test_disallow_string_for_allowed_methods asserts TypeError when methods is a string rather than a list. test_url_mapping additionally shows that a lowercase 'options' in methods suppresses automatic OPTIONS so the view itself answers OPTIONS (200 with view body). test_werkzeug_routing and test_endpoint_decorator build rules with werkzeug Submount/Rule directly, then bind views either via app.view_functions or the @app.endpoint decorator; both routes under /foo/ and /foo/bar resolve. test_multi_route_rules and test_multi_route_class_views show a view bound to multiple rules via stacked route decorators or repeated add_url_rule, with default argument test='a' filled when the variable rule does not match.

**Uncertainties.**

- test_url_mapping comment references issue 1288; the exact matcher mechanics for lowercase 'options' live in Flask/werkzeug, not this file.

<a id="u-6c9e34ed8c0a"></a>
### `test-basic-py-options-and-method-routes`

`def test_options_work(app, client):` · [tests/test_basic.py:L30-L31][f1]

Covers routing registration and automatic OPTIONS handling.

test_options_work registers GET/POST and asserts OPTIONS returns the union GET, HEAD, OPTIONS, POST with empty body; test_options_on_multiple_rules asserts the Allow header is the union across multiple rules on the same path. test_method_route parameterizes over lowercase method names, registering via app.<method> and requesting via client.<method>. test_method_route_no_methods asserts TypeError when both methods and the get-style shortcut are given. test_provide_automatic_options_attr shows an attribute provide_automatic_options=False on the view yields 405 for OPTIONS, while True plus methods=['OPTIONS'] makes the view itself handle OPTIONS (Allow: OPTIONS only). test_provide_automatic_options_kwarg does the same via add_url_rule(provide_automatic_options=False): disallowed methods still get 405 with correct Allow, HEAD is answered with 200 and truncated body, and OPTIONS is not auto-generated (405).

<a id="u-1894c4fe8d4c"></a>
### `test-basic-py-session-behavior`

`def test_session(app, client):` · [tests/test_basic.py:L234-L235][f1]

Covers session lifecycle, persistence, and cookie emission.

test_session asserts the accessed/modified flags transition only after session reads/writes. test_session_path and test_session_using_application_root verify the cookie Path derives from APPLICATION_ROOT or the WSGI SCRIPT_NAME (a PrefixPathMiddleware injects environ['SCRIPT_NAME'] and delegates to app.wsgi_app). test_session_using_session_settings checks domain, path, secure, httponly, samesite, and partitioned flags from config, and that popping the session emits an expiring 'session=;' cookie. test_session_using_samesite_attribute expects ValueError for an invalid samesite and absence for None, strict/lax otherwise. test_missing_session shows reads return None while writes and pop raise RuntimeError mentioning 'session is unavailable' when no secret key is set. test_session_secret_key_fallbacks verifies session decryption via SECRET_KEY_FALLBACKS after secret_key rotation, returning {} when no key matches. test_session_expiration shows permanent sessions get an Expires date within permanent_session_lifetime, non-permanent get none. test_session_stored_last shows after_request session mutations are persisted (first request reads None, second 42). test_session_special_types round-trips tuples, bytes, Markup, UUID, datetime, and specially keyed dict tags unchanged. test_session_cookie_setting asserts Set-Cookie is refreshed per request only when session.permanent and SESSION_REFRESH_EACH_REQUEST are both true; the closure reads is_permanent at request time so reassignment between run_test calls changes behavior. test_session_vary_cookie asserts Flask adds Vary: Cookie exactly once for any session access (get/getitem/setdefault/clear), merges with an existing Vary list, keeps a pre-set Cookie Vary single, and leaves /no-vary-header without Vary. test_session_refresh_vary asserts Vary: Cookie on permanent-session refresh even for views not touching the session. test_max_cookie_size shows Response.max_cookie_size falls back to the Werkzeug default outside app context, uses app config inside, warns 'cookie is too large' once when exceeded, and never warns when MAX_COOKIE_SIZE is 0.

**Notes.**

- side_effect: test_session_vary_cookie.expect asserts the Vary header appears at most once, merging view-added Vary values with Flask's Cookie value.

**Uncertainties.**

- recwarn.pop() in test_max_cookie_size matched multiple ctx.pop candidates in the dependency graph; the warning source is asserted only by message text here.
- Or-conditionals for 'domain=example.com' vs 'domain=.example.com' accommodate Werkzeug version differences not resolved from this file.

<a id="u-95ff2b8e35ec"></a>
### `test-basic-py-flashing`

`def test_flashes(app, req_ctx):` · [tests/test_basic.py:L598-L604][f1]

Tests the flash message machinery.

test_flashes shows flashing marks the session modified even if modified was reset afterwards, and get_flashed_messages returns and consumes both messages in order. test_extended_flashing exercises default-category messages, category-tagged messages (including Markup content), with_categories tuples, and single- or multi-value category_filter, both with and without returning categories; each scenario uses a fresh test client so flashed messages are cleaned between scenarios, and relies on app.testing=True so assertion failures in views propagate rather than becoming 500 responses.

<a id="u-df984174252d"></a>
### `test-basic-py-request-lifecycle-hooks`

`def test_request_processing(app, client):` · [tests/test_basic.py:L688-L691][f1]

Covers before_request, after_request, after_this_request, and teardown_request semantics.

test_request_processing shows before hooks run before the view and after hooks mutate the response body. test_request_preprocessing_early_return shows before hooks run in registration order and the first non-None return short-circuits (before_request2's 'hello' wins; the view and later hooks do not run). test_after_request_processing shows flask.after_this_request registers a callback applied to the eventual response (X-Foo header). test_teardown_request_handler and its debug-mode variant show teardown functions run once, their return values are ignored, and the response is unaffected. test_teardown_request_handler_error (testing=False) shows each teardown function receives the same original exception even if an earlier teardown raises a new exception that would blow away sys.exc_info, and the client sees a 500. test_before_after_request_order pins the exact sequence: before hooks in order, after hooks in reverse registration order, then teardown hooks in reverse order ([1,2,3,4,5,6]). test_error_handler_after_processor_error shows a 500 raised in before or after processing is still routed to the registered 500 errorhandler. test_before_request_and_routing_errors shows the 404 handler can read values a before_request attached to flask.g even when routing fails before the view.

**Notes.**

- failure: In test_teardown_request_handler_error, raising inside a teardown function does not change the exception passed to subsequent teardown functions, and the response becomes a 500.

**Uncertainties.**

- The two teardown test variants (test_teardown_request_handler vs ..._debug_mode) have identical bodies in this file; any behavioral difference would come from fixtures or config not visible here.

<a id="u-88971316ef79"></a>
### `test-basic-py-error-handling`

`def test_error_handling(app, client):` · [tests/test_basic.py:L867-L870][f1]

Covers errorhandler registration, exception-to-handler resolution, and trapping.

test_error_handling registers handlers by status code (404, 500) and by exception class (Forbidden), each producing its custom body. test_error_handling_processing shows after_request hooks still run on the errorhandler's response (mimetype overridden). test_baseexception_error_handling shows non-Exception BaseExceptions like KeyboardInterrupt propagate out of the client instead of becoming 500. test_user_error_handling shows arbitrary user exception classes get their registered handler. test_http_error_subclass_handling shows handler lookup prefers the most specific class: a ForbiddenSubclass handler wins for /1, while plain 403 aborts or Forbidden match the 403 handler. test_errorhandler_precedence shows a registered Exception handler catches unmatched E1, and for E3(E1,E2) the more specific registered E2 handler wins. test_trap_bad_request_key_error (parameterized) shows KeyError from form access becomes 400 by default, is re-raised as BadRequest carrying the key name when TRAP_BAD_REQUEST_ERRORS is set, and DEBUG untraps it; likewise flask.abort(400) re-raises BadRequest when trapping is on. test_trapping_of_all_http_exceptions shows TRAP_HTTP_EXCEPTIONS re-raises the NotFound instead of returning a response. test_error_handler_after_processor_error belongs to lifecycle and is documented in the hooks group.

**Notes.**

- condition: test_trap_bad_request_key_error combines DEBUG and TRAP_BAD_REQUEST_ERRORS parameters; expect_abort is only False in the (debug=False, trap=True) case.

**Uncertainties.**

- The exact MRO-based handler selection algorithm is in Flask's app code, not this file; conclusions here come from the asserted outcomes.

<a id="u-599525cdb05b"></a>
### `test-basic-py-response-and-json`

`def test_response_types(app, client):` · [tests/test_basic.py:L1122-L1123][f1]

Covers view return value conversion and JSON support.

test_response_types enumerates accepted return forms: str, bytes, (body, status, headers) full tuple, (body, headers), (body, status), (Response, headers) where dict headers override matching response headers and add new ones, (Response, status) where the tuple status overrides, a valid WSGI/HTTP exception (NotFound becomes a 404 page), and dict or list bodies which become JSON responses with the tuple's status. test_response_type_errors asserts TypeError with specific messages for None returns (names the view), one-element tuples, four-element tuples, a bool ('it was a bool'), and a non-callable-callable WSGI object. test_make_response and test_make_response_with_response_instance exercise make_response inside a request context: no-arg default 200 text/html, string body, (body, status), generator body joined to 'Hello', jsonify bodies gaining 400 and newline-terminated compact JSON, and a third list-of-headers argument merged into a Response with preserved Content-Type. test_jsonify_no_prettyprint parameterizes app.json.compact: when compact, output has no spaces or newlines, otherwise it is pretty-printed. test_jsonify_mimetype shows app.json.mimetype overrides the JSON response mimetype. test_json_dump_dataclass shows dataclasses serialize via app.json. test_jsonify_args_and_kwargs_check asserts TypeError mentioning 'args or kwargs' when jsonify gets both positional and keyword arguments.

**Uncertainties.**

- The conversion rules themselves (tuple unpacking, dict-to-JSON) are implemented in Flask's app/flatten helpers; this file only fixes their asserted boundary behavior.

<a id="u-31d1b155aa71"></a>
### `test-basic-py-urls-static-and-g`

`def test_url_generation(app, req_ctx):` · [tests/test_basic.py:L1339-L1340][f1]

Covers URL generation, build error handling, static files, URL value processors, and the g object.

test_url_generation shows url_for percent-encodes values ('test x' -> 'test%20x') and supports _external against localhost. test_build_error_handler shows unhandled BuildError propagates from url_for; app.handle_url_build_error re-raises the BuildError when it is not the current exception; a handler appended to url_build_error_handlers returning a path replaces the result. test_build_error_handler_reraise shows a handler that re-raises the error propagates it. test_url_for_passes_special_values_to_build_error_handler pins the values dict passed to handlers: _external False, _anchor/_method/_scheme None. test_static_files and the static_url_path/folder tests verify configurable static URL paths (including trailing-slash normalization), empty static_folder still serving the default /static route, pathlib static_folder, and a trailing-slash static folder not shadowing a catch-all route. test_static_route_with_host_matching shows static served bound to static_host, external url_for reflecting it, and AssertionError when static_host is given without host_matching or host_matching is used with a static_folder but no static_host; host_matching with static_folder=None is valid. test_url_processors registers url_defaults and url_value_preprocessor hooks that inject and strip lang_code, so generated URLs under /<lang_code>/ carry the current code. test_inject_blueprint_url_defaults shows blueprint url_defaults feed app.inject_url_defaults and url_for. test_nonascii_pathinfo matches a Cyrillic path. test_no_setup_after_first_request asserts AssertionError naming the setup method when add_url_rule is called after the first request. test_routing_redirect_debugging shows in debug mode a 301/302 RequestRedirect raises AssertionError naming the canonical URL while the default (308) redirect preserves form data. test_route_decorator_custom_endpoint verifies route(endpoint=...) names, including a numeric endpoint, for both url_for and dispatched views. test_request_locals asserts repr(flask.g) is '<LocalProxy unbound>' and empty g is falsy. test_get_method_on_g shows g.get returns None, a default, then stored values; test_g_iteration_protocol shows g supports membership tests and sorted iteration over its attribute names.

**Notes.**

- failure: test_static_route_with_host_matching asserts two AssertionError construction conditions and one valid construction (host_matching=True, static_folder=None, no static_host).

**Uncertainties.**

- The 'current exception' check in test_build_error_handler depends on whether the BuildError is sys.exc_info()'s active exception at handler time; the file asserts the outcome without showing that mechanism.

<a id="u-382d719cabe8"></a>
### `test-basic-py-server-name-and-subdomains`

`def test_server_name_matching( subdomain_matching: bool, host_matching: bool, expect_…` · [tests/test_basic.py:L1494-L1517][f1]

Covers SERVER_NAME-driven host and subdomain matching.

test_server_name_matching parameterizes subdomain_matching and host_matching: with both off, all requests match the default '/' rule; with subdomain_matching on, abc.example.test matches the subdomain rule while xyz.other.test warns (guarded by pytest.warns only in that case) and yields '<invalid>' for the <name> converter; with host_matching on, the Host header rule matches abc but not xyz. test_server_name_subdomain checks port handling: SERVER_NAME with a port matches requests with and without explicit base URLs, https/443 matching depends on Werkzeug version (404 tolerated), name mismatch warns (suppressed) and 404s, and foo.dev.local matches the subdomain='foo' rule. test_subdomain_basic_support, test_subdomain_matching, and test_subdomain_matching_with_ports show static and <user>-parameterized subdomain rules matching against SERVER_NAME, including with a :3000 port. test_subdomain_matching_other_name parameterizes subdomain_matching: requests to an IP or foreign subdomain 404 when matching is enabled and succeed (204) when disabled, with the Werkzeug name-mismatch UserWarning suppressed.

**Notes.**

- side_effect: Warning suppression via warnings.filterwarnings('ignore', 'Current server name', UserWarning, 'flask.app') is used in two tests to silence a version-dependent warning.

**Uncertainties.**

- test_server_name_subdomain branches on rv.status_code != 404 for Werkzeug 1.0 https/port matching, so the expected outcome on modern Werkzeug is ambiguous from this file alone.
- The '<invalid>' output for the unmatched subdomain comes from the <name> string converter failing; the mechanism is outside this file.

<a id="u-41e0ae9709d1"></a>
### `test-basic-py-run-and-app-lifecycle`

`def test_run_defaults(monkeypatch, app):` · [tests/test_basic.py:L1852-L1856][f1]

Covers app.run configuration and app teardown.

test_werkzeug_passthrough_errors monkeypatches werkzeug.serving.run_simple to capture kwargs and asserts, over the parameter grid of debug, use_debugger, use_reloader, and PROPAGATE_EXCEPTIONS, that app.run completes; the captured passthrough_errors value is stored but the parameterized expectations are implicit in the grid (no assertion on rv here). test_exception_propagation parameterizes TESTING, PROPAGATE_EXCEPTIONS, DEBUG, and None: setting any config key to True re-raises the view's ZeroDivisionError through the client, while None yields a normal 500. test_run_defaults and test_run_server_port verify app.run forwards to run_simple with default or explicit hostname/port (debug=True allowed). test_run_from_config pins host/port resolution: explicit arguments win over SERVER_NAME, port 0 is preserved, and SERVER_NAME supplies both when arguments are None. test_app_freed_on_zero_refcount (CPython-only) disables GC, creates a Flask app, takes a weakref, deletes the last reference, and asserts the app is collected, proving no reference cycle keeps it alive.

**Uncertainties.**

- test_werkzeug_passthrough_errors records passthrough_errors in a dict but contains no assertion on it in this file, so the expected value per parameter combination cannot be established from the source.
- The graph matched kwargs.get('passthrough_errors') to unrelated session .get methods; that linkage is name-based, not behavioral.

<a id="u-aaf5baa695cb"></a>
### `test_regression.py-abort-redirect`

`def test_aborting(app):` · [tests/test_regression.py:L4-L5][f2]

Regression test: raising flask.abort(flask.redirect(...)) inside a view must be delivered as a redirect response, not converted to 500, and a registered custom exception handler still fires for other exceptions.

GET / raises abort(redirect(url_for('test'))); the client receives a redirect whose Location header ends in '/test' (the prefix check tolerates older Werkzeug absolute redirects 'http://localhost'). GET /test raises a custom Foo exception with attribute whatever=42; the @app.errorhandler(Foo) handler returns str(e.whatever), so the response body is b'42'. The app fixture's test client is used as a context manager.

<a id="u-4af41a6b7d84"></a>
### `test_converters.py-custom-converters`

`def test_custom_converters(app, client):` · [tests/test_converters.py:L8-L9][f3]

Tests for registering custom Werkzeug URL converters on a Flask app.

test_custom_converters defines ListConverter: to_python splits the matched segment on commas into a list, and to_url delegates each element through BaseConverter.to_url then joins with commas. After app.url_map.converters['list'] is set, GET /1,2,3 renders '1|2|3' and url_for('index', args=[4,5,6]) inside a test request context produces '/4,5,6', proving round-tripping in both directions. test_context_available defines ContextConverter whose to_python asserts that the request and session proxies are not None, demonstrating that converters run with request context available during matching; GET /<ctx:name> for '/admin' returns 'admin'.

<a id="u-0c602e0f57a9"></a>
### `test_reqctx.py-request-context`

`def test_teardown_on_pop(app):` · [tests/test_reqctx.py:L16-L19][f4]

Tests for request-context push/pop, teardown, environ validation, session interfaces, and greenlet copying.

Teardown: a teardown_request callback appends its exception argument only when the context pops, and receives None when no exception or a handled (except-block) exception occurred, including when a prior exception existed before the context. test_proper_test_request_context verifies external url_for under SERVER_NAME 'localhost.localdomain:5000' for both host and subdomain ('foo.') routes, and that SERVER_NAME/HTTP_HOST mismatches only produce suppressed Werkzeug warnings plus valid contexts for localhost variants. Context binding: view functions called directly inside a test_request_context see flask.request data, and flask.request is falsy outside. has_request_context flips with push/pop; after manual pop, calling the view raises RuntimeError. Greenlet tests (skipped without greenlet): request_ctx.copy() and flask.copy_current_request_context both allow a greenlet to access request args, session values set in the request, and current_app. Session error handling: a session interface whose open_session raises causes a 500 response, the view never runs, and both request and current_app proxies are empty afterwards. PathAwareSessionInterface overrides get_cookie_name to return a distinct cookie name for URLs ending in 'dynamic_cookie'; the two-cookies assertion (42 vs 616) proves isolation. Environ handling: a non-printable HTTP_HOST (\x8a) yields a 400 from full_dispatch_request, while IDNA-compatible unicode hosts and punycode ('xn--on-0ia.com') complete with 200.

inherits: [SecureCookieSessionInterface][f5], [SessionInterface][f5]

<a id="u-25389f21160c"></a>
### `test_request.py`

`def test_max_content_length(app: Flask, client: FlaskClient) -> None:` · [tests/test_request.py:L9-L12][f6]

Tests that Flask app configuration controls Werkzeug request limits and trusted-host validation.

Covers MAX_CONTENT_LENGTH producing a 413 handled by an error handler, the precedence of app config versus Werkzeug defaults versus explicit overrides for request size limits, and TRUSTED_HOSTS matching with exact and leading-dot suffix hostnames.

calls: [Flask.app_context](r1-contexts-teardown.md#u-2e69ab7b3042), [Flask.test_client](r1-app-test-support.md#u-b8a91912b6a5)

**Uncertainties.**

- Where Request.max_content_length/max_form_memory_size/max_form_parts read app config is in unshown flask code; the test only pins observed values (Werkzeug defaults 500_000/1_000, None)

<a id="u-8617d3524406"></a>
### `test_limit_config`

`def test_limit_config(app: Flask):` · [tests/test_request.py:L25-L54][f6]

Sets MAX_CONTENT_LENGTH=100, MAX_FORM_MEMORY_SIZE=50, MAX_FORM_PARTS=3 on the app and probes a bare Request({}) in three phases.

Outside app context the request reports Werkzeug defaults (max_content_length None, max_form_memory_size 500_000, max_form_parts 1_000); inside app.app_context() it reports the config values; after assigning explicit overrides (90/30/4) those override values hold both outside and inside app context, demonstrating override precedence over config.

<a id="u-e9ea590a1faf"></a>
### `test_max_content_length`

`def test_max_content_length(app: Flask, client: FlaskClient) -> None:` · [tests/test_request.py:L9-L12][f6]

Sets MAX_CONTENT_LENGTH to 50, registers a POST '/' view that touches request.form['myfile'] (and would raise AssertionError if reached), and a 413 error handler returning '42'.

Posting 150 bytes then asserts the oversized body triggers the 413 handler response b"42".

<a id="u-ba82a4722d34"></a>
### `test_trusted_hosts_config`

`def test_trusted_hosts_config(app: Flask) -> None:` · [tests/test_request.py:L57-L60][f6]

Sets TRUSTED_HOSTS to ['example.test', '.other.test'], registers a trivial GET '/' view, and builds its own test client.

Requests to http://example.test and http://a.other.test (suffix match via the leading dot) return 200; a request to http://bad.test is rejected with 400.

<a id="u-bae2c6e2d5da"></a>
### `test_suppressed_exception_logging`

`def test_suppressed_exception_logging():` · [tests/test_subclassing.py:L6-L7][f7]

Confirms subclassing Flask to override log_exception as a no-op suppresses error logging for unhandled view exceptions.

A SuppressedFlask app routes '/' to a view raising Exception('test'); the test client requests it with errors_stream pointed at a StringIO, then asserts a 500 status, the body contains 'Internal Server Error', and the captured stream stays empty — the exception still produces the default 500 response but nothing is logged.

**Uncertainties.**

- That log_exception is the only logging path for unhandled exceptions is inferred from the assertion, not from supplied Flask source

<a id="u-64181f39f093"></a>
### `typing_error_handler-error-handler-signatures`

`def handle_400(e: BadRequest) -> str:` · [tests/type_check/typing_error_handler.py:L13-L17][f8]

Type-checking fixtures registering Flask error handlers with different key kinds on a module-level app, all returning an empty string.

handle_400 is stacked under three decorators: an integer code 400, the HTTPStatus.BAD_REQUEST enum, and the BadRequest exception class, showing all three key forms are accepted. handle_custom and handle_accept_base both register for ValueError, the latter declaring a broader Exception parameter, checking handler parameter contra-variance tolerance. handle_multiple registers for both BadRequest and 404 with a BadRequest | NotFound union parameter. No handler logic exists beyond returning "".

**Uncertainties.**

- Whether Flask resolves handler selection among stacked decorators or the union parameter at runtime is not visible here; this file only validates type-checker acceptance.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/tests/test_basic.py
[f2]: ../../../../../../eval/flask-85c5d93/tests/test_regression.py
[f3]: ../../../../../../eval/flask-85c5d93/tests/test_converters.py
[f4]: ../../../../../../eval/flask-85c5d93/tests/test_reqctx.py
[f5]: ../../../../../../eval/flask-85c5d93/src/flask/sessions.py
[f6]: ../../../../../../eval/flask-85c5d93/tests/test_request.py
[f7]: ../../../../../../eval/flask-85c5d93/tests/test_subclassing.py
[f8]: ../../../../../../eval/flask-85c5d93/tests/type_check/typing_error_handler.py
