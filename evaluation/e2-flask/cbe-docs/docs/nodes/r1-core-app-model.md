# Sans-I/O Application Core

**Capability.** The framework-agnostic application model: a central registry for URL rules, blueprints, error handlers, hooks, and configuration, plus the Scaffold base shared by apps and blueprints for route, endpoint, error-handler, and request-hook registration. Concrete request handling is deliberately excluded and left to subclasses.

Use this subtree to understand how views, blueprints, and handlers get registered and how app configuration, paths, and shared state are initialized. Everything here is usable before any request arrives; subclasses (see concrete-app) consume these registries at dispatch time.

**Children.**

- [Scaffold Registration Base](r1-scaffold-shared-base.md) `r1-scaffold-shared-base` · 16 unit(s)

**Depends on.**

- [Application Logging](r1-logging.md) · model-inferred · 0 edge(s) · App.logger obtains its logger through flask.logging.create_logger.
- [URL Building, Redirects, and Resources](r1-url-building-resources.md) · graph-only · 1 edge(s)
- [Blueprint Registration](r2-blueprint-registration.md) · graph-only · 1 edge(s)
- [Environment and Path Helpers](r2-environment-helpers.md) · graph-only · 1 edge(s)
- [Scaffold Registration Base](r1-scaffold-shared-base.md) · within containment · 10 edge(s)

**Depended on by.**

- [Concrete WSGI Application](r1-concrete-app.md) · graph-confirmed · 2 edge(s) · Flask.__init__ forwards constructor parameters to the sansio App, extending the registration-only core into a runnable application.
- [Exception and Error Handling](r1-error-handling.md) · graph-confirmed · 1 edge(s) · Handler resolution calls Scaffold._get_exc_class_and_code to normalize exception keys during lookup.
- [Template Rendering](r1-templating.md) · graph-confirmed · 1 edge(s) · create_global_jinja_loader constructs the DispatchingJinjaLoader, and jinja_env drives environment creation off the app.
- [URL Building, Redirects, and Resources](r1-url-building-resources.md) · model-inferred · 0 edge(s) · url_for calls the app's inject_url_defaults and handle_url_build_error hooks defined in the core model.

Parent: [Flask Framework](r1-flask-framework.md)

## Units (12)

<a id="u-c945a7570d6a"></a>
### `App`

`class App(Scaffold):` · [src/flask/sansio/app.py:L59-L282][f1]

App is the sansio core of the Flask application: a central registry for URL rules, blueprints, template hooks, error handlers, and configuration, with concrete request handling and environment construction left to subclasses.

It inherits Scaffold, which owns root-path resolution, the static route, and the view_functions/url_default_functions/error_handler_spec storage. Class-level hooks (aborter_class, jinja_environment, config_class, app_ctx_globals_class, url_rule_class, url_map_class, json_provider_class, jinja_options) are customization points. testing, secret_key, and permanent_session_lifetime are ConfigAttributes reading/writing the config dict, the lifetime one converting ints via _make_timedelta. _check_setup_finished enforces the setup lock: once _got_first_request is set after the first request, all @setupmethod registration APIs raise AssertionError naming the method, because changes would no longer apply consistently. create_jinja_environment is an abstract stub raising NotImplementedError; the concrete subclass supplies it. iter_blueprints returns the insertion-ordered values view of the blueprints dict.

inherits: [method::Scaffold][f2]; uses: [src/flask/sansio/app.py:_make_timedelta](r1-core-app-model.md#u-1485dc10cd8e)

**Uncertainties.**

- Concrete WSGI dispatch and environment construction live in subclasses not in this file.

<a id="u-1118e2b10fe6"></a>
### `App.__init__`

`def __init__( self, import_name: str, static_url_path: str | None = None, static_fold…` · [src/flask/sansio/app.py:L282-L411][f1]

Initializes the app: delegates shared setup to Scaffold.__init__, then builds instance path, config, aborter, JSON provider, and empty registries.

If instance_path is None it is auto-detected via auto_find_instance_path; a provided relative path raises ValueError immediately. Config comes from make_config(instance_relative_config), the aborter from make_aborter, and app.json is a new json_provider_class instance. It initializes url_build_error_handlers, teardown_appcontext_funcs, shell_context_processors, blueprints (an insertion-ordered dict; re-registration under the same name is allowed and not counted), and extensions to empty containers. url_map is created from url_map_class with host_matching passed through, so converters must be customized after construction and before routes are added. subdomain_matching is stored as an attribute and _got_first_request starts False, arming the setup lock.

**Notes.**

- failure: A relative instance_path raises ValueError at construction time.

calls: [App.auto_find_instance_path](r1-core-app-model.md#u-401411ba15a9), [App.make_config](r1-core-app-model.md#u-7c1f1572f574), [App.make_aborter](r1-url-building-resources.md#u-37e02c065230)

<a id="u-7c1f1572f574"></a>
### `App.make_config`

`def make_config(self, instance_relative: bool = False) -> Config:` · [src/flask/sansio/app.py:L482-L496][f1]

Creates the app's Config object.

The root path passed to config_class is self.instance_path when instance_relative is true, otherwise self.root_path. Defaults are a copy of default_config with DEBUG set from get_debug_flag(), so environment-driven debug detection applies at construction time. Returns an instance of config_class.

calls: [get_debug_flag](r2-environment-helpers.md#u-88884dd6c1eb)

<a id="u-401411ba15a9"></a>
### `App.auto_find_instance_path`

`def auto_find_instance_path(self) -> str:` · [src/flask/sansio/app.py:L510-L521][f1]

Locates the instance folder when none was given to the constructor.

It resolves the package via find_package; when no prefix is found it joins 'instance' beside the package path, otherwise it returns prefix/var/<name>-instance, relying on the cached name property.

calls: [find_package](r1-scaffold-shared-base.md#u-9a80c302e7bb)

<a id="u-1d21e745baf6"></a>
### `App.name`

`def name(self) -> str:` · [src/flask/sansio/app.py:L425-L440][f1]

Cached display name for the application.

When import_name is '__main__', the name is derived from the __main__ module's file basename without extension; if that module has no __file__, the literal '__main__' is returned. Otherwise import_name is returned unchanged.

**Notes.**

- side_effect: Cached via cached_property: later changes to import_name or the main module file have no effect after first access.

<a id="u-eeb70e011e34"></a>
### `App.debug`

`def debug(self) -> bool:` · [src/flask/sansio/app.py:L549-L560][f1]

Debug-mode property backed by the DEBUG config key.

The getter returns config['DEBUG']. The setter writes config['DEBUG'] and then, only when TEMPLATES_AUTO_RELOAD is still None (unset), synchronizes jinja_env.auto_reload to the new value; an explicitly set TEMPLATES_AUTO_RELOAD wins. Setting debug also triggers jinja_env creation, freezing jinja_options. The docstring warns DEBUG set late may misbehave and must not be enabled in production.

<a id="u-1485dc10cd8e"></a>
### `src/flask/sansio/app.py:_make_timedelta`

`def _make_timedelta(value: timedelta | int | None) -> timedelta | None:` · [src/flask/sansio/app.py:L52-L56][f1]

Coerces a config value into a timedelta for the PERMANENT_SESSION_LIFETIME ConfigAttribute converter.

Returns None and timedelta values unchanged; wraps any other value as timedelta(seconds=value). Non-numeric values are not checked here and would fail inside timedelta.

**Uncertainties.**

- Behavior for non-int, non-timedelta values depends on timedelta(seconds=...) raising, not on code in this function.

<a id="u-3cdcd592ec60"></a>
### `App.add_url_rule`

`def add_url_rule( self, rule: str, endpoint: str | None = None, view_func: ft.RouteCa…` · [src/flask/sansio/app.py:L604-L661][f1]

Registers a URL rule and its view function, subject to the @setupmethod lock.

If endpoint is None it is derived from view_func; options['endpoint'] is set and 'methods' is popped from options. When methods are not given, view_func.methods is used, defaulting to ('GET',); passing methods as a plain string raises TypeError. Methods are uppercased into a set. provide_automatic_options resolves in order: the explicit argument, then view_func.provide_automatic_options, then True with 'OPTIONS' added to required_methods only when 'OPTIONS' is not in methods and config PROVIDE_AUTOMATIC_OPTIONS is truthy, else False. required_methods from the view are unioned in, a url_rule_class rule is built with the remaining options and added to url_map. If a view_func is given and a different function is already registered under the endpoint, AssertionError is raised; otherwise view_functions[endpoint] is overwritten/stored.

**Notes.**

- failure: Duplicate endpoint with a different view function raises AssertionError; a string methods argument raises TypeError.

calls: [_endpoint_from_view_func](r1-scaffold-shared-base.md#u-5eef70528339); uses: [App](r1-core-app-model.md#u-c945a7570d6a)

<a id="u-139d60765559"></a>
### `App.register_blueprint`

`def register_blueprint(self, blueprint: Blueprint, **options: t.Any) -> None:` · [src/flask/sansio/app.py:L569-L595][f1]

Registers a blueprint after the setup-lock check imposed by @setupmethod.

All keyword options (url_prefix, subdomain, url_defaults, name, etc.) are passed verbatim to blueprint.register, which applies them via BlueprintSetupState; the 'name' option lets the same blueprint register multiple times under distinct names. The blueprint was already recorded in app.blueprints by this method's caller contract here: this method delegates entirely to blueprint.register(self, options).

calls: [Blueprint.register](r2-blueprint-registration.md#u-e0d107e183f6)

**Uncertainties.**

- Whether app.blueprints is populated here or inside Blueprint.register is not visible in this file's body.

<a id="u-2665deb0894d"></a>
### `app-py-template-filter`

`def template_filter( self, name: str | None = None ) -> t.Callable[[T_template_filter…` · [src/flask/sansio/app.py:L663-L679][f1]

Decorator factory registering a custom Jinja template filter.

template_filter(name=None) returns a decorator that calls add_template_filter(f, name=name) and returns f unchanged; the optional name defaults to the function's __name__. add_template_filter writes directly into jinja_env.filters[name or f.__name__], which materializes the environment on first registration and therefore freezes jinja_options. Both entry points are wrapped in @setupmethod, so they raise AssertionError once the app has handled its first request.

uses: [setupmethod](r1-scaffold-shared-base.md#u-81ccd06c4290)

<a id="u-a9a49185c50c"></a>
### `app-py-template-global`

`def template_global( self, name: str | None = None ) -> t.Callable[[T_template_global…` · [src/flask/sansio/app.py:L740-L758][f1]

Decorator factory registering a custom Jinja template global.

template_global(name=None) returns a decorator that calls add_template_global(f, name=name) and returns f; the optional name defaults to the function's __name__. add_template_global assigns into jinja_env.globals[name or f.__name__], materializing the environment and freezing jinja_options on first use. Both are @setupmethod and raise AssertionError after the first request.

uses: [setupmethod](r1-scaffold-shared-base.md#u-81ccd06c4290)

<a id="u-4c26c77d25b6"></a>
### `app-py-template-test`

`def template_test( self, name: str | None = None ) -> t.Callable[[T_template_test], T…` · [src/flask/sansio/app.py:L697-L720][f1]

Decorator factory registering a custom Jinja template test.

template_test(name=None) returns a decorator that calls add_template_test(f, name=name) and returns f; the optional name defaults to the function's __name__. add_template_test assigns into jinja_env.tests[name or f.__name__], materializing the environment and freezing jinja_options on first use. Both are @setupmethod and raise AssertionError after the first request.

uses: [setupmethod](r1-scaffold-shared-base.md#u-81ccd06c4290)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/sansio/app.py
[f2]: ../../../../../../eval/flask-85c5d93/src/flask/sansio/scaffold.py
