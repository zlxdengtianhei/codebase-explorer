# View and Async Dispatch Tests

**Capability.** Pins view behavior (method dispatch, OPTIONS/Allow headers, explicit and implicit HEAD, decorators, patching view_class, init_once, methods inheritance) plus async view, handler, and hook dispatch via asgiref.

Read these to confirm dispatch order and method-set computation, including 405 responses and endpoint-collision assertions in debug mode. The async tests are skipped when asgiref is absent.

**Depends on.**

- [Request and Response Helpers](r2-request-response-helpers.md) · model-inferred · 0 edge(s)
- [Testing Support](r2-testing-support.md) · graph-confirmed · 2 edge(s)
- [View and MethodView Core](r2-view-core.md) · model-inferred · 0 edge(s)
- [CLI Entry and Test Support](r1-app-test-support.md) · graph-only · 2 edge(s)

Parent: [Class-Based Views](r2-view-system.md)

## Units (16)

<a id="u-ebd07ac0c149"></a>
### `test_views.py module code (L1–L6)`

`module_region` · [tests/test_views.py:L1-L6][f1]

Imports pytest, werkzeug.http.parse_set_header, and flask.views used by the tests.

<a id="u-ab9c5a5f38b5"></a>
### `common_test`

`def common_test(app):` · [tests/test_views.py:L7-L14][f1]

Shared MethodView/View assertions against a test client: GET returns b'GET', POST returns b'POST', PUT yields 405, and the OPTIONS Allow header lists exactly GET, HEAD, OPTIONS, POST (parsed with werkzeug's parse_set_header).

uses: [test_basic_view](r2-view-tests.md#u-8938cc495853)

<a id="u-8938cc495853"></a>
### `test_basic_view`

`def test_basic_view(app):` · [tests/test_views.py:L17-L18][f1]

Registers a plain View whose dispatch_request returns flask.request.method with methods = ['GET', 'POST']; the shared client assertions confirm GET/POST dispatch and OPTIONS allow-list behavior.

calls: [common_test](r2-view-tests.md#u-ab9c5a5f38b5)

<a id="u-c96644371ef3"></a>
### `test_endpoint_override`

`def test_endpoint_override(app):` · [tests/test_views.py:L171-L174][f1]

With app.debug = True, registering two views under the same rule and endpoint raises AssertionError on the second add_url_rule; the first registration remains valid and common_test still passes afterwards (non-debug mode only logs a warning, per the comment).

calls: [common_test](r2-view-tests.md#u-ab9c5a5f38b5)

**Uncertainties.**

- Warning-only behavior in non-debug mode is asserted by comment, not exercised here

<a id="u-54906e4cfbf7"></a>
### `test_explicit_head`

`def test_explicit_head(app, client):` · [tests/test_views.py:L155-L156][f1]

When a MethodView defines an explicit head handler, HEAD requests dispatch to it: it returns an empty Response with header X-Method: HEAD, and GET still works normally.

<a id="u-bd786f9db335"></a>
### `test_implicit_head`

`def test_implicit_head(app, client):` · [tests/test_views.py:L141-L142][f1]

A MethodView with only get automatically serves HEAD: the head request returns an empty body while the view sees request.method == 'HEAD' (reported via the X-Method header), showing HEAD is routed through get with the method overridden.

<a id="u-1afb736edba9"></a>
### `test_init_once`

`def test_init_once(app, client):` · [tests/test_views.py:L245-L248][f1]

With init_every_request = False, CountInit is instantiated once, not per request: __init__ increments a nonlocal counter, and both requests see b'1', confirming a single shared view instance across requests.

**Uncertainties.**

- Whether instances would be per-request without the flag is implied by the flag name and asserted value, not shown here

<a id="u-9cd0447fc18e"></a>
### `test_method_based_view`

`def test_method_based_view(app):` · [tests/test_views.py:L28-L29][f1]

Registers a MethodView with get and post implementations; common_test confirms method dispatch to the matching handler and the Allow header.

calls: [common_test](r2-view-tests.md#u-ab9c5a5f38b5)

<a id="u-a6899088560a"></a>
### `test_methods_var_inheritance`

`def test_methods_var_inheritance(app, client):` · [tests/test_views.py:L189-L190][f1]

A BaseView declaring methods = ['GET', 'PROPFIND'] passes the attribute to ChildView implementing get and propfind.

Both methods are served, and MethodView normalizes ChildView.methods into the set {'PROPFIND', 'GET'}, which the test compares as an unordered set.

<a id="u-f770591b1652"></a>
### `test_multiple_inheritance`

`def test_multiple_inheritance(app, client):` · [tests/test_views.py:L207-L208][f1]

GetDeleteView combining GetView (get) and DeleteView (delete) via multiple inheritance serves both methods, and its computed methods attribute equals {'DELETE', 'GET'} (compared sorted).

<a id="u-c73bc68fe08e"></a>
### `test_remove_method_from_parent`

`def test_remove_method_from_parent(app, client):` · [tests/test_views.py:L226-L227][f1]

An explicit methods = ['GET'] on the combining subclass overrides method inference from parents: GET is served, but POST (defined on OtherView) returns 405, and View.methods contains only GET.

<a id="u-b38a528388aa"></a>
### `test_view_decorators`

`def test_view_decorators(app, client):` · [tests/test_views.py:L80-L81][f1]

A View with decorators = [add_x_parachute] has its dispatch wrapped: the decorator builds a response via flask.make_response around the wrapped call and adds header X-Parachute: awesome.

The GET response carries both the header and the body b'Awesome'.

<a id="u-d173a7324c3e"></a>
### `test_view_inheritance`

`def test_view_inheritance(app, client):` · [tests/test_views.py:L62-L63][f1]

BetterIndex extends a MethodView with get/post and adds delete; the OPTIONS Allow header then advertises DELETE, GET, HEAD, OPTIONS, POST, showing inherited and added methods all contribute to the allow-list.

<a id="u-d74d65c5f46d"></a>
### `test_view_patching`

`def test_view_patching(app):` · [tests/test_views.py:L41-L42][f1]

Demonstrates dispatch uses view.view_class at registration time, not the object's original class: a view created from Index (whose get/post raise ZeroDivisionError) has view_class reassigned to subclass Other implementing get/post; requests then succeed per common_test without hitting the raising methods.

calls: [common_test](r2-view-tests.md#u-ab9c5a5f38b5)

**Uncertainties.**

- Whether instantiation uses view_class is inferred from the passing assertions; the mechanism lives in flask.views

<a id="u-74c154ede848"></a>
### `test_view_provide_automatic_options_attr`

`def test_view_provide_automatic_options_attr():` · [tests/test_views.py:L101-L104][f1]

Three scenarios for OPTIONS handling.

Index1 sets provide_automatic_options = False without declaring OPTIONS: an OPTIONS request returns 405, since automatic options are disabled and the method is not in methods. Index2 declares methods = ['OPTIONS'] with provide_automatic_options = True: OPTIONS is handled and its allow list contains only OPTIONS. Index3 declares no methods and leaves provide_automatic_options defaulting on: OPTIONS is served automatically and 'OPTIONS' is in the allow list.

<a id="u-379bed2b7148"></a>
### `test_async.py-async-support`

`class AppError(Exception):` · [tests/test_async.py:L14-L15][f2]

Tests that Flask dispatches async views, error handlers, and before/after hooks (requires asgiref, enforced by importorskip so the module is skipped if absent).

The `async_app` fixture builds an app whose index route ('/' and '/home') is an async coroutine returning request.method, an async AppError handler returning 412, an /error route raising AppError, a blueprint 'bp' mounted at /bp with the same async pattern using BlueprintError, plus AsyncView (View subclass with async dispatch_request returning request.method) and AsyncMethodView (MethodView with async get/post) registered as class-based views. test_async_route parameterizes GET and POST over '/', '/home', '/bp/', '/view', '/methodview' and asserts the response body contains the request method. test_async_error_handler asserts both app and blueprint async error handlers convert the raised exceptions to 412 responses. test_async_before_after_request builds a fresh app and blueprint with async before_request/after_request hooks and nonlocal flags, then asserts app hooks fire for '/' and blueprint hooks fire for '/bp/', proving async hooks are awaited during dispatch.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/tests/test_views.py
[f2]: ../../../../../../eval/flask-85c5d93/tests/test_async.py
