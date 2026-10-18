# App-Scope Blueprint Hooks

**Capability.** Provides the decorator factories that inject blueprint code into app-wide registries: before/after/teardown_app_request, app_errorhandler, app_url_defaults, app_url_value_preprocessor, and app-level Jinja filters, tests, and globals.

Use this to see which registrations are app-wide (None key) versus blueprint-scoped. All are implemented via record_once so repeated registration does not duplicate hooks.

**Depends on.**

- [Scaffold Registration Base](r1-scaffold-shared-base.md) · graph-only · 13 edge(s)
- [Blueprint Deferred Setup](r2-sansio-blueprint-core.md) · graph-only · 10 edge(s)

**Depended on by.**

- [Blueprint Test Suite](r2-blueprint-tests.md) · model-inferred · 0 edge(s)

Parent: [Blueprint System](r2-blueprint-system.md)

## Units (13)

<a id="u-d35d0ef58088"></a>
### `Blueprint.before_app_request`

`def before_app_request(self, f: T_before_request) -> T_before_request:` · [src/flask/sansio/blueprints.py:L553-L561][f1]

App-scope before-request hook: records via record_once a lambda appending f to s.app.before_request_funcs under the None (app-wide) key with setdefault(None, []).append, so the function runs before every request regardless of blueprint and is not duplicated on re-registration.

Returns f unchanged.

<a id="u-b6dc97c967e6"></a>
### `Blueprint.after_app_request`

`def after_app_request(self, f: T_after_request) -> T_after_request:` · [src/flask/sansio/blueprints.py:L563-L571][f1]

App-scope after-request hook: records via record_once a lambda appending f to s.app.after_request_funcs under the None key; runs after every request, registered only on first registration.

Returns f.

<a id="u-9931b0187264"></a>
### `Blueprint.teardown_app_request`

`def teardown_app_request(self, f: T_teardown) -> T_teardown:` · [src/flask/sansio/blueprints.py:L573-L581][f1]

App-scope teardown hook: records via record_once a lambda appending f to s.app.teardown_request_funcs under the None key; the function runs after every request's teardown phase, registered only on first registration.

Returns f.

<a id="u-477d5bdc73e1"></a>
### `Blueprint.app_context_processor`

`def app_context_processor( self, f: T_template_context_processor ) -> T_template_cont…` · [src/flask/sansio/blueprints.py:L583-L593][f1]

App-scope context processor: records via record_once a lambda appending f to s.app.template_context_processors under the None key, injecting its context into every rendered template, registered only on first registration.

Returns f.

<a id="u-d0f105d149d5"></a>
### `Blueprint.app_errorhandler`

`def app_errorhandler( self, code: type[Exception] | int ) -> t.Callable[[T_error_hand…` · [src/flask/sansio/blueprints.py:L595-L603][f1]

Decorator factory for an app-wide error handler for the given code (exception class or HTTP status int).

Returns a decorator that records, via record_once, a callback calling state.app.errorhandler(code)(f) at registration time, deferring the handler registration to the app's own mechanism; the decorated function is returned unchanged.

<a id="u-48612a43cd68"></a>
### `Blueprint.app_url_defaults`

`def app_url_defaults(self, f: T_url_defaults) -> T_url_defaults:` · [src/flask/sansio/blueprints.py:L624-L632][f1]

App-scope url_defaults hook: records via record_once a lambda appending f to s.app.url_default_functions under the None key, applied when building URLs app-wide, registered only on first registration.

Returns f.

<a id="u-db92a6f24ce9"></a>
### `Blueprint.app_url_value_preprocessor`

`def app_url_value_preprocessor( self, f: T_url_value_preprocessor ) -> T_url_value_pr…` · [src/flask/sansio/blueprints.py:L612-L622][f1]

App-scope URL value preprocessor: records via record_once a lambda appending f to s.app.url_value_preprocessors under the None key, applied for every request, registered only on first registration.

Returns f.

<a id="u-02c9a9161fc7"></a>
### `Blueprint.add_app_template_filter`

`def add_app_template_filter( self, f: ft.TemplateFilterCallable, name: str | None = N…` · [src/flask/sansio/blueprints.py:L460-L472][f1]

Records, via record_once, a callback that at registration time sets state.app.jinja_env.filters[name or f.__name__] = f.

Because of record_once, the filter is installed only on the blueprint's first registration, so registering the blueprint again does not overwrite the env entry.

<a id="u-a1ae0b1860b9"></a>
### `Blueprint.add_app_template_global`

`def add_app_template_global( self, f: ft.TemplateGlobalCallable, name: str | None = N…` · [src/flask/sansio/blueprints.py:L534-L548][f1]

Records, via record_once, a callback setting state.app.jinja_env.globals[name or f.__name__] = f at registration; runs only on first registration.

<a id="u-640be4ffb363"></a>
### `Blueprint.add_app_template_test`

`def add_app_template_test( self, f: ft.TemplateTestCallable, name: str | None = None …` · [src/flask/sansio/blueprints.py:L496-L510][f1]

Records, via record_once, a callback setting state.app.jinja_env.tests[name or f.__name__] = f at registration; runs only on first registration.

<a id="u-081105ad1fac"></a>
### `Blueprint.app_template_filter`

`def app_template_filter( self, name: str | None = None ) -> t.Callable[[T_template_fi…` · [src/flask/sansio/blueprints.py:L443-L454][f1]

Decorator factory registering a Jinja filter available in any template rendered by the app.

Returns a decorator that delegates to add_app_template_filter with the optional name and returns the function unchanged.

<a id="u-28814a103be2"></a>
### `Blueprint.app_template_global`

`def app_template_global( self, name: str | None = None ) -> t.Callable[[T_template_gl…` · [src/flask/sansio/blueprints.py:L515-L528][f1]

Decorator factory registering a Jinja global available in any template; returns a decorator delegating to add_app_template_global with the optional name and returning the function unchanged.

<a id="u-e8d96cbfebbd"></a>
### `Blueprint.app_template_test`

`def app_template_test( self, name: str | None = None ) -> t.Callable[[T_template_test…` · [src/flask/sansio/blueprints.py:L477-L490][f1]

Decorator factory registering a Jinja test available in any template; returns a decorator delegating to add_app_template_test with the optional name and returning the function unchanged.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/sansio/blueprints.py
