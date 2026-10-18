# Fixture Applications

**Capability.** Importable sample applications under tests/test_apps consumed by other tests: the blueprintapp package registering admin/frontend blueprints with template-rendering views, cliapp's factories and discovery targets (single app, multiple apps per module, nested package app, import-error module), the helloworld app with its WSGI entry point, and the old-style subdomain Module fixture.

Use this subtree as test data, not behavior: CLI app-discovery tests import cliapp modules, blueprint tests exercise blueprintapp's templates, and subdomain tests use subdomaintestmodule. The missing_template view exists for error-path testing.

**Depends on.**

- [Template Rendering](r1-templating.md) · model-inferred · 0 edge(s)

Parent: [Test Suites and Fixture Apps](r1-tests.md)

## Units (20)

<a id="u-5776fc52332f"></a>
### `__init__.py module code (L1–L9)`

`module_region` · [tests/test_apps/blueprintapp/__init__.py:L1-L9][f1]

Builds the blueprintapp test application: creates a Flask app with DEBUG enabled, imports the admin and frontend blueprints (imports deferred after app creation, hence noqa E402), and registers both so their routes are mounted at import time of this package.

**Notes.**

- side_effect: Registering admin and frontend on import makes importing the package a stateful operation that fails if either blueprint module fails.

imports: [tests/test_apps/blueprintapp/apps/admin/__init__.py:__init__.py module code (L1–L12)](r1-tests-fixture-apps.md#u-a604cd6fadbc), [__init__.py module code (L1–L6)](r1-tests-fixture-apps.md#u-0f1d914a68c3)

<a id="u-a604cd6fadbc"></a>
### `tests/test_apps/blueprintapp/apps/admin/__init__.py:__init__.py module code (L1–L12)`

`module_region` · [tests/test_apps/blueprintapp/apps/admin/__init__.py:L1-L12][f2]

Defines the admin Blueprint named 'admin' with url_prefix /admin, template folder 'templates' and static folder 'static', and registers two GET routes: '/' -> index and '/index2' -> index2, both rendering admin templates.

The module-level blueprint object is the export consumed by the application package.

group: [tests/test_apps/blueprintapp/apps/admin/__init__.py:index](r1-tests-fixture-apps.md#u-b45aa966c16b), [index2](r1-tests-fixture-apps.md#u-ded7167aa67a)

**Uncertainties.**

- Whether index2's './admin/index.html' template path resolves identically to index's is a Flask loader behavior not provable from this file.

<a id="u-b45aa966c16b"></a>
### `tests/test_apps/blueprintapp/apps/admin/__init__.py:index`

`def index():` · [tests/test_apps/blueprintapp/apps/admin/__init__.py:L13-L15][f2]

Renders the 'admin/index.html' template for the /admin/ route, returning the rendered string; template lookup failures propagate to Flask's error handling.

<a id="u-ded7167aa67a"></a>
### `index2`

`def index2():` · [tests/test_apps/blueprintapp/apps/admin/__init__.py:L18-L20][f2]

Renders './admin/index.html' for the /admin/index2 route.

The './' prefix differs from index's plain template name; whether the template loader treats them identically is decided by Flask's loader, not visible here.

**Uncertainties.**

- Resolution of the './' template name relative to normal lookup is unverified.

<a id="u-0f1d914a68c3"></a>
### `__init__.py module code (L1–L6)`

`module_region` · [tests/test_apps/blueprintapp/apps/frontend/__init__.py:L1-L6][f3]

Defines the frontend Blueprint with a template folder and no URL prefix, exposing routes '/' (index) and '/missing' (missing_template).

Its module-level blueprint is registered by the application package.

group: [tests/test_apps/blueprintapp/apps/frontend/__init__.py:index](r1-tests-fixture-apps.md#u-1851b7bffd8e), [missing_template](r1-tests-fixture-apps.md#u-856c17171fde)

<a id="u-1851b7bffd8e"></a>
### `tests/test_apps/blueprintapp/apps/frontend/__init__.py:index`

`def index():` · [tests/test_apps/blueprintapp/apps/frontend/__init__.py:L7-L9][f3]

Renders 'frontend/index.html' for the frontend root route, returning the rendered template output.

<a id="u-856c17171fde"></a>
### `missing_template`

`def missing_template():` · [tests/test_apps/blueprintapp/apps/frontend/__init__.py:L12-L14][f3]

Attempts to render 'missing_template.html' for the /missing route; the file name and its likely use in error-path testing indicate the template is expected to be absent, so TemplateNotFound should propagate (observed intent, not proven behavior).

**Uncertainties.**

- Whether missing_template.html actually lacks a matching file cannot be confirmed from source.

<a id="u-5f98ae67eea9"></a>
### `factory.py module code (L1–L3)`

`def create_app():` · [tests/test_apps/cliapp/factory.py:L4-L5][f4]

Module providing app-factory callables for CLI testing: create_app and create_app2 construct Flask instances, no_app constructs nothing.

<a id="u-4d486a074025"></a>
### `create_app`

`def create_app():` · [tests/test_apps/cliapp/factory.py:L4-L5][f4]

Factory returning a new Flask app named 'app' with no configuration; a fresh instance per call.

<a id="u-c3927d768ba7"></a>
### `create_app2`

`def create_app2(foo, bar):` · [tests/test_apps/cliapp/factory.py:L8-L9][f4]

Factory returning a Flask app named by joining 'app2', foo, and bar with underscores; both parameters are required positional arguments and their string values are interpolated into the app name.

**Uncertainties.**

- Whether foo/bar are strings is not enforced; non-string values would fail in str.join.

<a id="u-c585477a6983"></a>
### `no_app`

`def no_app():` · [tests/test_apps/cliapp/factory.py:L12-L13][f4]

Returns None implicitly; used where a 'factory' that produces no app is required.

<a id="u-082bf2c8c405"></a>
### `app-py-module`

`group` · [tests/test_apps/cliapp/app.py:L1-L3][f5]

Test fixture module holding a single Flask application instance named testapp.

It imports Flask from the flask package and constructs it with the fixed name string 'testapp'; no routes or other configuration appear in the file.

imports: [flask.Flask](../../catalog.json)

<a id="u-1971c06f1aa4"></a>
### `flask-py-module`

`group` · [tests/test_apps/cliapp/inner1/inner2/flask.py:L1-L3][f6]

Test fixture module creating a Flask application named after this module via __name__.

It imports Flask and instantiates a single app object; no routes or configuration appear in the file. Its location deeper in the package likely serves name-resolution testing.

imports: [flask.Flask](../../catalog.json)

<a id="u-6262a9d8df12"></a>
### `__init__.py module code (L1–L3)`

`module_region` · [tests/test_apps/cliapp/inner1/__init__.py:L1-L3][f7]

Defines application = Flask(__name__), an app instance exported from the inner1 package for CLI app-discovery testing.

<a id="u-6e0597561f2d"></a>
### `multiapp.py module code (L1–L4)`

`module_region` · [tests/test_apps/cliapp/multiapp.py:L1-L4][f8]

Defines two Flask instances, app1 and app2, in one module; used to exercise discovery of multiple apps per importable module.

<a id="u-e28ca089c836"></a>
### `importerrorapp.py module code (L1–L5)`

`module_region` · [tests/test_apps/cliapp/importerrorapp.py:L1-L5][f9]

Module that raises ImportError() at import time before defining testapp = Flask('testapp'); the Flask line is unreachable on import, so importing this module always fails by design (likely testing import-error handling).

**Uncertainties.**

- The unreachable testapp line suggests deliberate error simulation; the intended consumer behavior is outside this file.

<a id="u-d3ecd9d4ac3a"></a>
### `hello.py module code (L1–L5)`

`def hello():` · [tests/test_apps/helloworld/hello.py:L6-L8][f10]

Minimal Flask app with a root route: creates app = Flask(__name__) and registers hello on '/'.

The app object is exported for wsgi.py.

group: [hello](r1-tests-fixture-apps.md#u-023702c45f79)

<a id="u-023702c45f79"></a>
### `hello`

`def hello():` · [tests/test_apps/helloworld/hello.py:L6-L8][f10]

Route handler for '/' returning the literal string 'Hello World!' as the response body.

<a id="u-2c625ae5b357"></a>
### `wsgi.py module code (L1–L1)`

`module_region` · [tests/test_apps/helloworld/wsgi.py:L1-L1][f11]

WSGI entry point re-exporting app from the hello module (noqa F401 marks the import as intentionally unused locally).

Import resolution of 'hello' depends on the caller's path containing the package directory.

<a id="u-8c371dc28656"></a>
### `tests/test_apps/subdomaintestmodule/__init__.py:__init__.py module code (L1–L3)`

`module_region` · [tests/test_apps/subdomaintestmodule/__init__.py:L1-L3][f12]

Creates mod = Module(__name__, 'foo', subdomain='foo'), an old-style Flask Module bound to subdomain 'foo'.

Uses the Flask Module API, which is legacy and absent from current Flask versions, so importability depends on the installed Flask.

**Uncertainties.**

- Flask.Module was removed in modern Flask; whether this module imports at all depends on the test environment.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/tests/test_apps/blueprintapp/__init__.py
[f2]: ../../../../../../eval/flask-85c5d93/tests/test_apps/blueprintapp/apps/admin/__init__.py
[f3]: ../../../../../../eval/flask-85c5d93/tests/test_apps/blueprintapp/apps/frontend/__init__.py
[f4]: ../../../../../../eval/flask-85c5d93/tests/test_apps/cliapp/factory.py
[f5]: ../../../../../../eval/flask-85c5d93/tests/test_apps/cliapp/app.py
[f6]: ../../../../../../eval/flask-85c5d93/tests/test_apps/cliapp/inner1/inner2/flask.py
[f7]: ../../../../../../eval/flask-85c5d93/tests/test_apps/cliapp/inner1/__init__.py
[f8]: ../../../../../../eval/flask-85c5d93/tests/test_apps/cliapp/multiapp.py
[f9]: ../../../../../../eval/flask-85c5d93/tests/test_apps/cliapp/importerrorapp.py
[f10]: ../../../../../../eval/flask-85c5d93/tests/test_apps/helloworld/hello.py
[f11]: ../../../../../../eval/flask-85c5d93/tests/test_apps/helloworld/wsgi.py
[f12]: ../../../../../../eval/flask-85c5d93/tests/test_apps/subdomaintestmodule/__init__.py
