# Helper and Resource Tests

**Capability.** tests/test_helpers.py: file-serving and streaming (send_file family, stream_with_context), url_for in request contexts, abort/redirect dispatch through the app aborter and redirect hook, get_debug_flag/make_response, the no-import guarantee of Flask(import_name), and the FakePath/PyBytesIO test doubles plus open_resource mode and encoding coverage.

Use this module when changing file serving, streaming, URL generation, or abort/redirect dispatch. The doubles at the top are fixtures consumed by the send-file tests.

**Depends on.**

- [Request Dispatch Pipeline](r1-request-dispatch.md) · model-inferred · 0 edge(s)
- [Functional Behavior Tests](r1-tests-functional.md) · graph-only · 3 edge(s)

**Depended on by.**

- [Functional Behavior Tests](r1-tests-functional.md) · graph-only · 1 edge(s)

Parent: [Test Suites and Fixture Apps](r1-tests.md)

## Units (15)

<a id="u-cafd7bd7bb4c"></a>
### `test_helpers.py-testsendfile`

`class TestSendfile:` · [tests/test_helpers.py:L33-L34][f1]

Covers send_file, send_static_file, and send_from_directory.

send_file of static/index.html returns a direct_passthrough response with mimetype text/html whose bytes equal the file's contents once passthrough is disabled. Default max_age is None; setting SEND_FILE_MAX_AGE_DEFAULT=3600 sets cache_control.max_age to 3600 for both the static handler and direct send_file, including when the filename is a FakePath path-like. A subclass overriding get_send_file_max_age to return 10 overrides the config for both paths. send_from_directory resolves a new root_path under test_apps/subdomaintestmodule and streams static/hello.txt with content 'Hello Subdomain'. All responses are closed after use.

<a id="u-f86b89444bfa"></a>
### `test_helpers.py-teststreaming`

`class TestStreaming:` · [tests/test_helpers.py:L236-L237][f1]

Verifies stream_with_context keeps the request context alive while a generator streams after the view returns.

Passing an existing generator to stream_with_context, or decorating a generator function (which then accepts arguments), lets the generator read flask.request.args during consumption: '/?name=World' yields 'Hello World!'. Wrapping in a custom iterator with a close method still triggers close on completion (called == [42]), showing stream_with_context preserves close semantics. A generator reading flask.session after the view returns sees the value set in the view, proving session access survives context preservation.

**Uncertainties.**

- The static call graph cannot decide which local generate() each index view calls, since three same-named generators exist in the class; behavior is read from the adjacent test bodies

<a id="u-37e039aa3eab"></a>
### `test_helpers.py-testurlfor`

`class TestUrlFor:` · [tests/test_helpers.py:L102-L103][f1]

Verifies url_for behaviors inside request contexts.

_anchor values are URL-quoted ('x y' becomes x%20y). _scheme='https' forces an external https URL (https://localhost/), including when _external is not passed; combining _scheme with _external=False raises ValueError, and scheme handling is not sticky across calls (alternating back to http works). _method selects between MyView's GET and POST rules so url_for picks /myview/, /myview/42, or /myview/create. A route parameter literally named 'self' can be supplied as the self keyword.

<a id="u-b1a00993ee85"></a>
### `test_helpers.py-testhelpers`

`class TestHelpers:` · [tests/test_helpers.py:L310-L311][f1]

Covers get_debug_flag and make_response.

get_debug_flag parses FLASK_DEBUG: '' , '0', 'False', and 'No' are False; 'True' is True. make_response inside a request context turns no argument into a 200 text/html response and a string into a 200 text/html response whose body is that string.

<a id="u-b3bea27df366"></a>
### `test_helpers.py-testnoimports`

`class TestNoImports:` · [tests/test_helpers.py:L217-L228][f1]

Flask(import_name) must not import the import name.

The test writes importerror.py (which raises NotImplementedError) into the modules temp path and constructs Flask('importerror'); if NotImplementedError escapes, the test converts it to an AssertionError signaling that Flask performed an import.

<a id="u-72f4dd11acd4"></a>
### `test_helpers.py-fakepath`

`class FakePath:` · [tests/test_helpers.py:L11-L18][f1]

A minimal path-like stand-in implementing __fspath__, letting file APIs that accept path-like objects be tested with an arbitrary wrapped string stored in the path attribute.

<a id="u-a067c614e71a"></a>
### `test_helpers.py-pybytesio`

`class PyBytesIO:` · [tests/test_helpers.py:L25-L26][f1]

A BytesIO wrapper that delegates all attribute access to an internal io.BytesIO via __getattr__, used where a pure-Python object is preferred over a C-backed one.

<a id="u-0370a433e011"></a>
### `test_helpers.py-test-abort-with-app`

`def test_abort_with_app(app):` · [tests/test_helpers.py:L207-L208][f1]

Inside an app context, flask.abort consults the app aborter's mapping.

Registering a custom HTTPException subclass with code 900 in app.aborter.mapping makes abort(900) raise that exact exception type.

<a id="u-9ff9cccc2bb9"></a>
### `test_helpers.py-test-app-aborter-class`

`def test_app_aborter_class():` · [tests/test_helpers.py:L196-L197][f1]

An app can supply its own aborter: subclassing flask.Flask with aborter_class set to a werkzeug Aborter subclass makes the app's aborter attribute an instance of that subclass.

<a id="u-829450e27c9d"></a>
### `test_helpers.py-test-redirect-with-app`

`def test_redirect_with_app(app):` · [tests/test_helpers.py:L178-L179][f1]

Inside an app context, flask.redirect dispatches to the app's redirect method: the test replaces app.redirect with a callable raising ValueError and asserts the ValueError propagates, proving the app-level hook is used rather than a fixed implementation.

<a id="u-fadbfe62749a"></a>
### `test_abort_no_app`

`def test_abort_no_app():` · [tests/test_helpers.py:L188-L193][f1]

Without an app, flask.abort(401) raises werkzeug's Unauthorized directly; an unmapped code like 900 raises LookupError, showing unknown status codes are not silently converted.

<a id="u-e082d249d659"></a>
### `test_redirect_no_app`

`def test_redirect_no_app():` · [tests/test_helpers.py:L172-L175][f1]

Outside any app context, flask.redirect still builds a response with the given location and status code (307 here), without needing an app.

<a id="u-70db08f5f81e"></a>
### `test_open_resource`

`def test_open_resource(mode):` · [tests/test_helpers.py:L338-L343][f1]

app.open_resource accepts text and binary modes ('r', 'rb', 'rt') as a context manager and reads static/index.html, whose content contains '<h1>Hello World!</h1>'.

<a id="u-4d15e7c39f7c"></a>
### `test_open_resource_exceptions`

`def test_open_resource_exceptions(mode):` · [tests/test_helpers.py:L346-L351][f1]

Write modes ('w', 'x', 'a', 'r+') are rejected: app.open_resource raises ValueError for each, since resources are read-only.

<a id="u-293e3f659d3b"></a>
### `test_open_resource_with_encoding`

`def test_open_resource_with_encoding(tmp_path, encoding):` · [tests/test_helpers.py:L354-L360][f1]

With a root_path set to a temp dir containing a file written as utf-8 or utf-16-le, open_resource with mode 'rt' and the matching encoding returns the decoded text 'test', showing encoding is forwarded to the underlying open.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/tests/test_helpers.py
