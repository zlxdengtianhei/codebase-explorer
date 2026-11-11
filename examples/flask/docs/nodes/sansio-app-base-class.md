# Sansio App Base Class

**Capability.** Defines the framework-agnostic App base class: construction, config and Jinja environment setup, template registrations, URL building support and teardown or shell registrations.

Come here for how the application object is initialized and the setup-time methods it exposes independent of WSGI. It includes template filter, global and test registration, instance path logic, URL default and build-error handling, and url_for.

**Depends on.**

- [Scaffold Base and Setup Decorators](scaffold-base-and-setup-decorators.md) · graph-only · 9 edge(s)
- [Helpers, Flask Blueprint and Run](helpers-flask-blueprint-and-run.md) · graph-only · 2 edge(s)
- [App and Request Context Management](app-and-request-context-management.md) · graph-only · 1 edge(s)

**Depended on by.**

- [WSGI Entry and Request Contexts](wsgi-entry-and-request-contexts.md) · graph-only · 1 edge(s)

Parent: [Sansio App Base and Logging](sansio-app-base-and-logging.md)

## Units (26)

<a id="u-b1db9535a7db"></a>
### `app.py-debug-property`

`def debug(self) -> bool:` · [src/flask/sansio/app.py:L549-L560][f1]

The debug property reads and writes the DEBUG config key.

The getter returns self.config["DEBUG"]. The setter stores the value in config["DEBUG"]; then, only if config["TEMPLATES_AUTO_RELOAD"] is None, it sets jinja_env.auto_reload to the same value. That access instantiates the Jinja environment if not yet created, so in this base class it would hit the NotImplementedError of create_jinja_environment when no subclass override exists. An explicit TEMPLATES_AUTO_RELOAD (True or False) leaves the environment untouched. Setting debug after the environment is created updates auto_reload only in the None case.

<a id="u-e1087c682a9d"></a>
### `app.py-template-filter-decorator`

`def template_filter( self, name: str | None = None ) -> t.Callable[[T_template_filter…` · [src/flask/sansio/app.py:L663-L679][f1]

template_filter(name) is a setup method returning a decorator that registers a function as a Jinja filter.

The inner decorator calls add_template_filter(f, name=name) and returns f unchanged, so the function remains usable. With name None, the filter name is the function's __name__. Registration happens when the decorator is applied, not when template_filter is called.

<a id="u-55c2d8c9c14c"></a>
### `app.py-template-global-decorator`

`def template_global( self, name: str | None = None ) -> t.Callable[[T_template_global…` · [src/flask/sansio/app.py:L740-L758][f1]

template_global(name) is a setup method returning a decorator that registers a function as a Jinja global through add_template_global(f, name=name), returning f unchanged.

The name defaults to the function's __name__.

<a id="u-c75607d2fe3e"></a>
### `app.py-template-test-decorator`

`def template_test( self, name: str | None = None ) -> t.Callable[[T_template_test], T…` · [src/flask/sansio/app.py:L697-L720][f1]

template_test(name) is a setup method returning a decorator that registers a function as a Jinja test via add_template_test(f, name=name), then returns f unchanged.

A missing name falls back to the function's __name__.

<a id="u-f591687825aa"></a>
### `Flask.url_for`

`def url_for( self, /, endpoint: str, *, _anchor: str | None = None, _method: str | No…` · [src/flask/app.py:L1003-L1127][f2]

Builds a URL for an endpoint using the request or app URL adapter, applying url defaults and delegating build failures to a handler.

In a request context (_cv_request set): uses the request's adapter; an endpoint starting with '.' is prefixed with the current blueprint name, or loses the dot if no blueprint matched; _external defaults to (_scheme is not None).
Outside a request: uses the active app context's adapter if there is one, else create_url_adapter(None); a None adapter raises RuntimeError about missing SERVER_NAME; _external defaults to True.
In both: _scheme given with a falsy _external raises ValueError. It then calls inject_url_defaults(endpoint, values) and url_adapter.build(...). On BuildError it merges _anchor/_method/_scheme/_external into values and returns the result of handle_url_build_error (which may itself return a string or raise). On success an _anchor is percent-quoted with a safe set and appended as '#anchor'. Note that the anchor is not appended to the value returned by the build error handler.

calls: [App.inject_url_defaults](../../catalog.json.gz), [App.handle_url_build_error](../../catalog.json.gz)

<a id="u-c945a7570d6a"></a>
### `App`

`class App(Scaffold):` · [src/flask/sansio/app.py:L59-L282][f1]

App is the framework-agnostic (sansio) application base class built on Scaffold.

It holds the central registries and routing, config and Jinja setup, while leaving request-handling and Jinja environment creation to a subclass.
The class body defines overridable class attributes: aborter_class (werkzeug Aborter), jinja_environment, app_ctx_globals_class, config_class (Config), json_provider_class (DefaultJSONProvider), a shared mutable jinja_options dict, url_rule_class (Rule), url_map_class (Map), and test client/CLI runner classes defaulting to None. The testing, secret_key and permanent_session_lifetime attributes are ConfigAttribute descriptors bound to the TESTING, SECRET_KEY and PERMANENT_SESSION_LIFETIME config keys; the lifetime descriptor converts reads through the timedelta helper. default_config and response_class are only annotated here, so a subclass must supply them (make_config and redirect depend on them). jinja_options is a class-level dict, so mutating it affects all instances sharing it.

inherits: [Scaffold](../../catalog.json.gz)

<a id="u-1485dc10cd8e"></a>
### `src/flask/sansio/app.py:_make_timedelta`

`def _make_timedelta(value: timedelta | int | None) -> timedelta | None:` · [src/flask/sansio/app.py:L52-L56][f1]

Normalizes a session-lifetime config value into a timedelta or None.

None and existing timedelta values pass through unchanged; any other value is treated as a number of seconds and wrapped via timedelta(seconds=value). A non-numeric value would raise inside timedelta; nothing is caught here.

<a id="u-1118e2b10fe6"></a>
### `App.__init__`

`def __init__( self, import_name: str, static_url_path: str | None = None, static_fold…` · [src/flask/sansio/app.py:L282-L411][f1]

Constructs the application: initializes the Scaffold base, resolves the instance path, then creates the config, aborter, JSON provider, registries, URL map and first-request flag.

If instance_path is None it is computed by auto_find_instance_path; if given but not absolute (os.path.isabs false) it raises ValueError. The config is built with make_config(instance_relative_config), the aborter with make_aborter, and the JSON provider as json_provider_class(self). It initializes empty url_build_error_handlers, teardown_appcontext_funcs, shell_context_processors, blueprints and extensions containers, and creates the URL map as url_map_class(host_matching=host_matching). It stores subdomain_matching and sets _got_first_request to False, which later gates setup methods. Order matters: the instance path and config rely on the Scaffold-set root_path and import_name. make_config reads self.default_config, which this class only annotates.

calls: [Scaffold.__init__](../../catalog.json.gz), [App.make_config](sansio-app-base-class.md#u-7c1f1572f574), [App.auto_find_instance_path](sansio-app-base-class.md#u-401411ba15a9), [App.make_aborter](sansio-app-base-class.md#u-37e02c065230)

**Uncertainties.**

- default_config is only annotated in this class; whether a subclass always defines it is not visible here.

<a id="u-47e9aede35af"></a>
### `App._check_setup_finished`

`def _check_setup_finished(self, f_name: str) -> None:` · [src/flask/sansio/app.py:L413-L423][f1]

Guards setup-time methods on the application once it has started serving.

Raises AssertionError with an explanatory message naming the method if the internal first-request flag is true; otherwise does nothing. Called by the setupmethod wrapper before each decorated registration method. The flag itself is set elsewhere, not in this file.

<a id="u-7fd5d53aa731"></a>
### `App.add_template_filter`

`def add_template_filter( self, f: ft.TemplateFilterCallable, name: str | None = None …` · [src/flask/sansio/app.py:L685-L695][f1]

Registers a custom Jinja filter directly: sets jinja_env.filters[name or f.__name__] = f.

Being a setup method, it fails after the first request. It accesses jinja_env, creating the environment if needed; an existing filter of the same name is overwritten.

<a id="u-5b520aceb956"></a>
### `App.add_template_global`

`def add_template_global( self, f: ft.TemplateGlobalCallable, name: str | None = None …` · [src/flask/sansio/app.py:L764-L776][f1]

Registers a Jinja global by setting jinja_env.globals[name or f.__name__] = f.

A setup method; it triggers creation of the Jinja environment and overwrites an existing global of the same name.

<a id="u-005391c85b52"></a>
### `App.add_template_test`

`def add_template_test( self, f: ft.TemplateTestCallable, name: str | None = None ) ->…` · [src/flask/sansio/app.py:L726-L738][f1]

Registers a custom Jinja test by setting jinja_env.tests[name or f.__name__] = f.

A setup method; accesses jinja_env (creating it if needed) and overwrites a same-named test.

<a id="u-401411ba15a9"></a>
### `App.auto_find_instance_path`

`def auto_find_instance_path(self) -> str:` · [src/flask/sansio/app.py:L510-L521][f1]

Computes a default instance folder when none was given.

Calls find_package(import_name). If the returned prefix is None (package not installed under a prefix), the result is <package_path>/instance. Otherwise it is <prefix>/var/<name>-instance, using the app name property. Pure path computation; it does not check existence or create directories.

<a id="u-8450dbb577ff"></a>
### `App.create_jinja_environment`

`def create_jinja_environment(self) -> Environment:` · [src/flask/sansio/app.py:L479-L480][f1]

Abstract hook for building the Jinja Environment; the base implementation always raises NotImplementedError.

A concrete subclass must override it, since jinja_env calls it.

<a id="u-42ba1794dea3"></a>
### `App.handle_url_build_error`

`def handle_url_build_error( self, error: BuildError, endpoint: str, values: dict[str,…` · [src/flask/sansio/app.py:L932-L964][f1]

Recovers from a BuildError raised during URL building by consulting url_build_error_handlers.

Each handler is called with (error, endpoint, values) in list order. If it raises BuildError, that new error replaces the current error and the loop continues. If it returns a non-None value, that value is returned immediately. A None return is skipped. If no handler produces a value: when the current error is the exception currently being handled (sys.exc_info()[1]) a bare `raise` re-raises it with its context; otherwise `raise error` raises the (possibly replaced) error. So the method either returns a string or raises a BuildError; other exception types from handlers propagate unhandled.

<a id="u-8bdea1636623"></a>
### `App.inject_url_defaults`

`def inject_url_defaults(self, endpoint: str, values: dict[str, t.Any]) -> None:` · [src/flask/sansio/app.py:L911-L930][f1]

Applies registered URL default functions to a values dict in place before URL building.

The scopes are None (app-wide) first; if the endpoint contains a dot, it also adds the blueprint path portion (endpoint up to the last dot) split via _split_blueprint_path and iterated in reversed order of that helper's result. For each scope present in url_default_functions (checked with `in`, so no defaultdict entries are created), every function is called as func(endpoint, values) in registration order, and may mutate values. Parsed from the endpoint rather than the request, so it works outside a request context. Exceptions from the callbacks propagate.

calls: [_split_blueprint_path](../../catalog.json.gz)

**Uncertainties.**

- The exact ordering produced by _split_blueprint_path is not visible in this batch; only that the result is reversed.

<a id="u-5dbbac5289a7"></a>
### `App.iter_blueprints`

`def iter_blueprints(self) -> t.ValuesView[Blueprint]:` · [src/flask/sansio/app.py:L597-L602][f1]

Returns the live values view of the blueprints dict, in registration order.

It is a view, not a copy, so later registrations show up in it.

<a id="u-76927d5a1e1f"></a>
### `App.jinja_env`

`def jinja_env(self) -> Environment:` · [src/flask/sansio/app.py:L469-L477][f1]

Cached property providing the Jinja environment.

The first access calls create_jinja_environment and the result is cached for the instance, so later changes to jinja_options have no effect. In this base class that creation method raises NotImplementedError, so access fails unless a subclass overrides it.

<a id="u-37e02c065230"></a>
### `App.make_aborter`

`def make_aborter(self) -> Aborter:` · [src/flask/sansio/app.py:L498-L508][f1]

Creates the object used to raise HTTP errors by instantiating aborter_class with no arguments (werkzeug Aborter by default).

Overriding aborter_class changes the result.

<a id="u-7c1f1572f574"></a>
### `App.make_config`

`def make_config(self, instance_relative: bool = False) -> Config:` · [src/flask/sansio/app.py:L482-L496][f1]

Builds the Config object for the app.

Uses root_path as the config root, or instance_path when instance_relative is true. Copies default_config into a new dict and overwrites its DEBUG entry with get_debug_flag(), so the environment-derived debug flag always wins over a default_config DEBUG value. Returns config_class(root_path, defaults). Requires instance_path to already be set when instance_relative is true, and default_config to exist.

calls: [get_debug_flag](../../catalog.json.gz)

<a id="u-1d21e745baf6"></a>
### `App.name`

`def name(self) -> str:` · [src/flask/sansio/app.py:L425-L440][f1]

Cached display name of the application, derived from the import name.

If import_name is "__main__", it reads __file__ from sys.modules["__main__"]; with no __file__ it returns "__main__", otherwise the file's basename without extension. For any other import name it returns the import name unchanged. Being a cached_property, it is computed once and can be overridden by assignment. auto_find_instance_path and the logger use it.

<a id="u-b737095e43e9"></a>
### `App.redirect`

`def redirect(self, location: str, code: int = 302) -> BaseResponse:` · [src/flask/sansio/app.py:L893-L909][f1]

Builds a redirect response by calling werkzeug's redirect with location, the status code (default 302) and the app's response_class as the Response class.

Returns the response without raising. response_class is only annotated in this class, so it must be provided by a subclass.

<a id="u-1a7f67b1b674"></a>
### `App.select_jinja_autoescape`

`def select_jinja_autoescape(self, filename: str) -> bool:` · [src/flask/sansio/app.py:L536-L547][f1]

Decides whether Jinja autoescaping applies to a template name.

A None filename returns True, despite the str annotation. Otherwise returns True only if the name ends with .html, .htm, .xml, .xhtml or .svg (case-sensitive); other names return False.

<a id="u-94836406bd81"></a>
### `App.shell_context_processor`

`def shell_context_processor( self, f: T_shell_context_processor ) -> T_shell_context_…` · [src/flask/sansio/app.py:L812-L821][f1]

Registers a shell context processor by appending f to shell_context_processors and returning it unchanged.

A setup method that raises AssertionError after the app has handled a request.

<a id="u-8c50f5d3809c"></a>
### `App.should_ignore_error`

`def should_ignore_error(self, error: BaseException | None) -> bool:` · [src/flask/sansio/app.py:L883-L891][f1]

Hook deciding whether a teardown error should be hidden from teardown handlers.

The base implementation always returns False, so errors are passed on; subclasses may override.

<a id="u-6b3e4a9135e9"></a>
### `App.teardown_appcontext`

`def teardown_appcontext(self, f: T_teardown) -> T_teardown:` · [src/flask/sansio/app.py:L778-L810][f1]

Decorator-style registration of an app-context teardown function: appends f to teardown_appcontext_funcs and returns f unchanged.

A setup method (fails after first request). The calling of these functions at context pop, and the error argument, happen elsewhere; the docstring says return values are ignored.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/sansio/app.py
[f2]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/app.py
