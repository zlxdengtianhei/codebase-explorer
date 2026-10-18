# Test Client Behavior Tests

**Capability.** tests/test_testing.py: environ defaults and overrides (REMOTE_ADDR, User-Agent, SERVER_NAME/APPLICATION_ROOT derived defaults, URL schemes, full URLs), subdomain matching, JSON requests/responses and EnvironBuilder json_dumps, context binding and preservation layers, session_transaction semantics, CLI runner invocation, and client reuse.

Use this module to pin how the test client and test_request_context synthesize environments. Session-transaction tests document the cookie and backend preconditions.

**Depends on.**

- [CLI Entry and Test Support](r1-app-test-support.md) · model-inferred · 0 edge(s)

Parent: [Test Suites and Fixture Apps](r1-tests.md)

## Units (25)

<a id="u-11b224e9c82f"></a>
### `test_testing.py-test-environ-defaults-from-config`

`def test_environ_defaults_from_config(app, client):` · [tests/test_testing.py:L15-L19][f1]

SERVER_NAME and APPLICATION_ROOT config feed the test client and test_request_context: both the context's request.url and a client GET response report http://example.com:1234/foo/, showing environ defaults derive from app config.

<a id="u-3957f00f478f"></a>
### `test_testing.py-test-environ-defaults`

`def test_environ_defaults(app, client, app_ctx, req_ctx):` · [tests/test_testing.py:L30-L31][f1]

Without config overrides, requests default to http://localhost/: a bare test_request_context yields that URL, and a client GET inside 'with client' returns the same body.

<a id="u-3227bf266e0f"></a>
### `test_testing.py-test-environ-base-default`

`def test_environ_base_default(app, client):` · [tests/test_testing.py:L42-L43][f1]

By default the test client presents remote_addr 127.0.0.1 and a User-Agent of 'Werkzeug/<installed version>'; the view stores both on flask.g for assertion after the request.

<a id="u-c9c719e135b5"></a>
### `test_testing.py-test-environ-base-modified`

`def test_environ_base_modified(app, client):` · [tests/test_testing.py:L57-L58][f1]

Setting client.environ_base before requests overrides REMOTE_ADDR and HTTP_USER_AGENT for subsequent calls: the view observes 192.168.0.22 and 'Foo'.

<a id="u-12eb2dcc0ab1"></a>
### `test_testing.py-test-specify-url-scheme`

`def test_specify_url_scheme(app, client):` · [tests/test_testing.py:L90-L91][f1]

Passing url_scheme='https' to test_request_context or client.get makes request.url report https://localhost/ for both the context and the response body.

<a id="u-7e97ba6c5ed4"></a>
### `test_path_is_url`

`def test_path_is_url(app):` · [tests/test_testing.py:L102-L107][f1]

EnvironBuilder accepts a full URL as the path: 'https://example.com/' decomposes into url_scheme 'https', host 'example.com', script_root '', and path '/'.

<a id="u-ecafbbe250fc"></a>
### `test_environbuilder_json_dumps`

`def test_environbuilder_json_dumps(app):` · [tests/test_testing.py:L110-L114][f1]

EnvironBuilder.json_dumps takes settings from the app: after app.json.ensure_ascii=False, a JSON body containing '€' is serialized as raw UTF-8 rather than escaped ASCII, readable from the builder's input stream.

<a id="u-2e764342f777"></a>
### `test_testing.py-test-client-open-environ`

`def test_client_open_environ(app, client, request):` · [tests/test_testing.py:L73-L74][f1]

client.open accepts both an EnvironBuilder and a raw WSGI environ.

A builder request to /index reports 127.0.0.1; after mutating client.environ_base, opening builder.get_environ() reflects the new REMOTE_ADDR 127.0.0.2. The builder is closed via a request finalizer.

<a id="u-ddcc854b26cb"></a>
### `test_testing.py-test-full-url-request`

`def test_full_url_request(app, client):` · [tests/test_testing.py:L251-L252][f1]

client.post accepts an absolute URL: posting to http://domain.com/action?vodka=42 hits the /action route, with query parameter 'vodka' in request.args and form field 'gin' in request.form, both reaching the view.

<a id="u-1e3cac9bffb8"></a>
### `test_testing.py-test-json-request-and-response`

`def test_json_request_and_response(app, client):` · [tests/test_testing.py:L263-L264][f1]

Posting with json= makes the request JSON (request.is_json true, get_json round-trips the nested payload) and jsonify in the view produces a JSON response (rv.is_json, get_json equal to the original data) with status 200.

<a id="u-67b5e3635af3"></a>
### `test_testing.py-test-client-json-no-app-context`

`def test_client_json_no_app_context(app, client):` · [tests/test_testing.py:L282-L283][f1]

Requests that end normally still push and pop an app context exactly once per request, observed by counting appcontext_popped signals with a Namespace counter.

The /hello route reads request.json and responds 'Hello, Flask!', and the pop count after the request is 1.

<a id="u-e598025089f3"></a>
### `test_testing.py-test-redirect-keep-session`

`def test_redirect_keep_session(app, client, app_ctx):` · [tests/test_testing.py:L141-L142][f1]

Session data survives a redirect through the test client.

GET /getsession before anything is set yields '<missing>'; GET / sets session['data']='foo'; POST / redirects to /getsession and, with follow_redirects=True, the response body is 'foo' and flask.session still holds 'foo' after the redirect chain.

<a id="u-8b8dbb99c801"></a>
### `test_testing.py-test-session-transactions`

`def test_session_transactions(app, client):` · [tests/test_testing.py:L169-L170][f1]

client.session_transaction() opens an editable session outside requests: initially empty, setting sess['foo']=[42] makes len 1, a later GET sees '[42]' rendered by the view, and a second transaction observes the persisted value.

<a id="u-c387ff3d08d2"></a>
### `test_session_transaction_needs_cookies`

`def test_session_transaction_needs_cookies(app):` · [tests/test_testing.py:L204-L209][f1]

session_transaction requires cookie support: on a client built with use_cookies=False, entering it raises TypeError matching 'Cookies are disabled.'.

<a id="u-c33177a84b18"></a>
### `test_session_transactions_keep_context`

`def test_session_transactions_keep_context(app, client, req_ctx):` · [tests/test_testing.py:L196-L201][f1]

Inside an existing request context (req_ctx fixture), a session_transaction does not tear down or replace the surrounding request: the request proxy object observed before and during the transaction is identical.

<a id="u-7a0241c921a4"></a>
### `test_session_transactions_no_null_sessions`

`def test_session_transactions_no_null_sessions():` · [tests/test_testing.py:L186-L193][f1]

When the session backend does not open a session, entering session_transaction raises RuntimeError whose message contains 'Session backend did not open a session'.

<a id="u-3728c1eaa92f"></a>
### `test_testing.py-test-test-client-context-binding`

`def test_test_client_context_binding(app, client):` · [tests/test_testing.py:L212-L215][f1]

With app.testing False, 'with client' binds a request context around each request: after a successful GET, flask.g.value set by the view remains readable (42); after a 500 error on /other, g has no value, the body contains 'Internal Server Error', and a value set afterwards (23) is readable within the block.

Outside the client block, touching flask.g raises RuntimeError because no context is pushed.

<a id="u-f11cf834747a"></a>
### `test_reuse_client`

`def test_reuse_client(client):` · [tests/test_testing.py:L241-L248][f1]

A test client can be reused across separate 'with client' blocks: each block pushes fresh contexts and a GET returns 404 in both.

<a id="u-ec6506b4d637"></a>
### `test_testing.py-test-client-pop-all-preserved`

`def test_client_pop_all_preserved(app, req_ctx, client):` · [tests/test_testing.py:L382-L383][f1]

Context preservation layers: the req_ctx fixture pushes one request context, the client GET pushes a second (preserved by the client), and stream_with_context inside the view pushes a third (preserved by the response).

Closing the response releases its context; afterwards the only active request context is the fixture's, verified by _cv_request.get(None) being req_ctx.

<a id="u-149fa7e7db3b"></a>
### `test_testing.py-test-cli-invoke`

`def test_cli_invoke(app):` · [tests/test_testing.py:L350-L351][f1]

The app's CLI runner invokes app commands both by name (args=['hello']) and by passing the command object directly; both capture the echoed 'Hello, World!' in result.output.

<a id="u-8872b1e38feb"></a>
### `test_testing.py-test-cli-custom-obj`

`def test_cli_custom_obj(app):` · [tests/test_testing.py:L364-L365][f1]

A custom obj can be supplied to runner.invoke: passing a ScriptInfo whose create_app flips NS.called makes the CLI invoke that factory, proving the obj reaches FlaskGroup's app loading path (NS.called becomes True).

<a id="u-5a94b31e0750"></a>
### `test_testing.py-test-cli-runner-class`

`def test_cli_runner_class(app):` · [tests/test_testing.py:L338-L342][f1]

app.test_cli_runner returns a FlaskCliRunner by default; setting app.test_cli_runner_class to a subclass makes subsequent calls return instances of that subclass.

<a id="u-b80677491ba2"></a>
### `test_testing.py-test-subdomain`

`def test_subdomain():` · [tests/test_testing.py:L302-L307][f1]

With subdomain_matching and SERVER_NAME example.com, a route '/' with subdomain '<company_id>' lets url_for build '/xxx' from company_id='xxx', and a client GET of that URL returns 200 with body 'xxx'.

<a id="u-56b9d89963a0"></a>
### `test_testing.py-test-nosubdomain`

`def test_nosubdomain(app, client):` · [tests/test_testing.py:L321-L324][f1]

Even with SERVER_NAME set, a route without a subdomain converter matches normally: url_for('view', company_id='xxx') yields '/xxx' and the client GET returns 200 with body 'xxx'.

<a id="u-74a4f2a34fed"></a>
### `test_testing.py-test-blueprint-with-subdomain`

`def test_blueprint_with_subdomain():` · [tests/test_testing.py:L117-L125][f1]

With subdomain_matching and SERVER_NAME example.com:1234, a blueprint on subdomain 'xxx' serves '/': a test_request_context with subdomain='xxx' reports http://xxx.example.com:1234/foo/ and request.blueprint equals the blueprint name, and a client GET with subdomain='xxx' returns the same URL as the body.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/tests/test_testing.py
