# Blueprint Deferred Registration

**Capability.** Implements the sansio Blueprint, which records routes and callbacks as deferred functions and applies them, including app-wide Jinja and handler registrations, when registered on an app.

Read this module to understand how a blueprint is collected, set up and registered on an application or parent blueprint. It covers the setup state, record and record_once, app-wide template and error handler decorators, and nested blueprint registration.

**Depends on.**

- [Scaffold Base and Setup Decorators](scaffold-base-and-setup-decorators.md) · graph-confirmed · 19 edge(s) · 2 inferred relation(s) · The sansio Blueprint uses the Scaffold setup decorators and setup-finished checks to guard and record its deferred registrations.

Parent: [Scaffold and Blueprint Registration](scaffold-and-blueprint-registration.md)

## Units (21)

<a id="u-92b128a62ade"></a>
### `blueprints.py-add-app-template-filter`

`def add_app_template_filter( self, f: ft.TemplateFilterCallable, name: str | None = N…` · [src/flask/sansio/blueprints.py:L460-L472][f1]

Defers registration of an app-wide Jinja filter.

It defines a callback that sets state.app.jinja_env.filters[name or f.__name__] = f and records it with record_once, so it runs on the first registration only. Nothing touches an app until the blueprint is registered.

<a id="u-225d3946c255"></a>
### `blueprints.py-add-app-template-global`

`def add_app_template_global( self, f: ft.TemplateGlobalCallable, name: str | None = N…` · [src/flask/sansio/blueprints.py:L534-L548][f1]

Defers registration of an app-wide Jinja global: records, via record_once (first registration only), a callback that sets state.app.jinja_env.globals[name or f.__name__] = f.

<a id="u-1eb156ba8714"></a>
### `blueprints.py-add-app-template-test`

`def add_app_template_test( self, f: ft.TemplateTestCallable, name: str | None = None …` · [src/flask/sansio/blueprints.py:L496-L510][f1]

Defers registration of an app-wide Jinja test: records, via record_once (first registration only), a callback that sets state.app.jinja_env.tests[name or f.__name__] = f.

<a id="u-949032be71a1"></a>
### `blueprints.py-app-errorhandler`

`def app_errorhandler( self, code: type[Exception] | int ) -> t.Callable[[T_error_hand…` · [src/flask/sansio/blueprints.py:L595-L603][f1]

app_errorhandler(code) is a setup-method decorator factory for app-wide error handlers.

The inner decorator defines from_blueprint, which calls state.app.errorhandler(code)(f), and records it with record_once so it applies to the app on the blueprint's first registration only; the decorator returns f unchanged. Errors from the app's errorhandler, such as an unrecognized code, surface at registration time rather than at decoration time.

<a id="u-1f11b53f4722"></a>
### `blueprints.py-app-template-filter`

`def app_template_filter( self, name: str | None = None ) -> t.Callable[[T_template_fi…` · [src/flask/sansio/blueprints.py:L443-L454][f1]

app_template_filter(name) is a setup-method decorator factory; the inner decorator calls add_app_template_filter(f, name=name) and returns f unchanged.

The filter becomes available across the whole application, not only the blueprint's templates.

<a id="u-93128a952cd4"></a>
### `blueprints.py-app-template-global`

`def app_template_global( self, name: str | None = None ) -> t.Callable[[T_template_gl…` · [src/flask/sansio/blueprints.py:L515-L528][f1]

app_template_global(name) is a setup-method decorator factory; the inner decorator calls add_app_template_global(f, name=name) and returns f unchanged, making the global available app-wide.

<a id="u-dd2e119636c5"></a>
### `blueprints.py-app-template-test`

`def app_template_test( self, name: str | None = None ) -> t.Callable[[T_template_test…` · [src/flask/sansio/blueprints.py:L477-L490][f1]

app_template_test(name) is a setup-method decorator factory; the inner decorator calls add_app_template_test(f, name=name) and returns f unchanged, making the test available app-wide.

<a id="u-da2d7e7ff958"></a>
### `blueprints.py-app-wide-request-callbacks`

`def before_app_request(self, f: T_before_request) -> T_before_request:` · [src/flask/sansio/blueprints.py:L553-L561][f1]

These setup methods register callbacks that apply to every request on the app, not just the blueprint's.

Each calls record_once with a lambda that does setdefault(None, []).append(f) on the matching app registry at first registration, then returns f unchanged. before_app_request uses before_request_funcs, after_app_request uses after_request_funcs, teardown_app_request uses teardown_request_funcs, app_context_processor uses template_context_processors, app_url_value_preprocessor uses url_value_preprocessors, and app_url_defaults uses url_default_functions. The None key means app-wide scope. Because of record_once, a second registration of the blueprint does not add the function again.

<a id="u-593c4323149c"></a>
### `blueprints.py-blueprintsetupstate-construction`

`class BlueprintSetupState:` · [src/flask/sansio/blueprints.py:L34-L41][f1]

BlueprintSetupState is the temporary holder passed to deferred blueprint callbacks during registration; its __init__ resolves the effective registration settings.

It stores app, blueprint, options and first_registration. Subdomain is options['subdomain'], falling back to blueprint.subdomain when the option is None. url_prefix likewise falls back to blueprint.url_prefix when the option is None. name is options.get('name', blueprint.name) and name_prefix is options.get('name_prefix', ''); these use the default only when the key is missing, so an explicit None name is kept. url_defaults starts as a copy of blueprint.url_values_defaults and is updated by options['url_defaults'] (default empty), so option values override blueprint ones.

<a id="u-ba470935275d"></a>
### `blueprints.py-merge-blueprint-funcs`

`def _merge_blueprint_funcs(self, app: App, name: str) -> None:` · [src/flask/sansio/blueprints.py:L379-L380][f1]

Copies the blueprint's registries into the application under the registration name.

The inner extend helper takes a blueprint-keyed dict and a parent dict, renames each key (None becomes name, other keys become 'name.key') and extends the parent's list at that key. The method first copies each error_handler_spec scope into app.error_handler_spec under the renamed key, as a fresh defaultdict(dict) of code to a copied class-to-handler dict, replacing any existing entry for that key. It then copies all view_functions into app.view_functions by endpoint (overwriting existing ones without the duplicate check used by add_url_rule). Finally it extends before_request, after_request, teardown_request, url_default, url_value_preprocessor and template_context_processors lists. Mutates the app's registries; no return value.

<a id="u-e33badf31b12"></a>
### `blueprints.py-record-once`

`def record_once(self, func: DeferredSetupFunction) -> None:` · [src/flask/sansio/blueprints.py:L232-L240][f1]

record_once wraps a callback so it only runs on the blueprint's first registration on an app, then records the wrapper.

The inner wrapper calls func(state) only if state.first_registration is true; it is given func's metadata via update_wrapper before being passed to record. If the same blueprint is registered again, for example under another name, the callback is skipped. Setup method.

<a id="u-139d60765559"></a>
### `App.register_blueprint`

`def register_blueprint(self, blueprint: Blueprint, **options: t.Any) -> None:` · [src/flask/sansio/app.py:L569-L595][f2]

Registers a blueprint on the application by calling blueprint.register(self, options).

Decorated as a setup method, so it raises AssertionError once the app has handled a request. The keyword options (for example url_prefix, subdomain, name) are passed through as a dict; recording in self.blueprints is done by Blueprint.register, not here. Errors such as duplicate names propagate from that call.

calls: [Blueprint.register](blueprint-deferred-registration.md#u-e0d107e183f6)

<a id="u-d7d5b4b4bcc2"></a>
### `src/flask/sansio/blueprints.py:Blueprint`

`class Blueprint(Scaffold):` · [src/flask/sansio/blueprints.py:L119-L174][f1]

Blueprint is a Scaffold subclass collecting routes and callbacks as deferred functions, so they can be applied later to an application.

It tracks whether it has ever been registered via the class attribute _got_registered_once, which locks further setup calls. Most decorators on it are setup methods that either record work on deferred_functions or write into Scaffold registries.

inherits: [Scaffold](../../catalog.json.gz)

<a id="u-6140c4847d46"></a>
### `src/flask/sansio/blueprints.py:Blueprint.__init__`

`def __init__( self, name: str, import_name: str, static_folder: str | os.PathLike[str…` · [src/flask/sansio/blueprints.py:L174-L211][f1]

Initializes the blueprint after the Scaffold setup.

Raises ValueError if name is empty or contains a dot. Stores name, url_prefix, subdomain, an empty deferred_functions list, url_values_defaults (an empty dict if url_defaults is None; a passed dict is stored as is, not copied), cli_group (default is the module sentinel, meaning use the blueprint name) and an empty _blueprints list of nested (blueprint, options) pairs. Scaffold init runs first, so Scaffold side effects precede the name validation errors.

<a id="u-6560000f6f91"></a>
### `Blueprint._check_setup_finished`

`def _check_setup_finished(self, f_name: str) -> None:` · [src/flask/sansio/blueprints.py:L213-L221][f1]

Blocks setup calls after the blueprint has been registered.

If _got_registered_once is true, raises AssertionError naming the method and blueprint; otherwise does nothing.

<a id="u-115c8d08d2f5"></a>
### `Blueprint.add_url_rule`

`def add_url_rule( self, rule: str, endpoint: str | None = None, view_func: ft.RouteCa…` · [src/flask/sansio/blueprints.py:L412-L441][f1]

Registers a URL rule with the blueprint by deferring it.

Raises ValueError if endpoint contains a dot, or if view_func has a __name__ containing a dot. Otherwise records a callback that calls state.add_url_rule(rule, endpoint, view_func, provide_automatic_options=..., **options) at registration time, so no rule exists on the app until registration. Setup method. Overrides the abstract Scaffold method.

uses: [BlueprintSetupState.add_url_rule](blueprint-deferred-registration.md#u-14b96816dcf8)

<a id="u-cdd8d4a4352d"></a>
### `Blueprint.make_setup_state`

`def make_setup_state( self, app: App, options: dict[str, t.Any], first_registration: …` · [src/flask/sansio/blueprints.py:L246-L253][f1]

Factory for the setup state: returns BlueprintSetupState(self, app, options, first_registration).

Subclasses can override it to supply a different state class. first_registration defaults to False.

<a id="u-26efb075394f"></a>
### `Blueprint.record`

`def record(self, func: DeferredSetupFunction) -> None:` · [src/flask/sansio/blueprints.py:L223-L230][f1]

Appends a callback to deferred_functions; it will be called with the BlueprintSetupState on every registration of this blueprint.

Setup method, so fails once the blueprint was registered.

<a id="u-e0d107e183f6"></a>
### `Blueprint.register`

`def register(self, app: App, options: dict[str, t.Any]) -> None:` · [src/flask/sansio/blueprints.py:L273-L377][f1]

Applies the blueprint to an application: validates the name, records it, merges its registries, runs deferred callbacks, wires CLI commands, and registers nested blueprints.

The name is options['name_prefix'] + '.' + options.get('name', self.name) with leading dots stripped. If that name is already in app.blueprints, raises ValueError (message says this or a different blueprint and suggests name=). first_bp_registration is true if this blueprint object isn't among app.blueprints values; first_name_registration is true when the name is new (always true after the check above). It then sets app.blueprints[name] and _got_registered_once = True, and builds the setup state via make_setup_state. If has_static_folder, adds a 'static' rule at static_url_path + '/<path:filename>' using send_static_file through the state (that attribute is not defined here). If first_bp_registration or first_name_registration, calls _merge_blueprint_funcs. Then each deferred function is called with the state, in order; exceptions propagate after the earlier mutations have been made. CLI: if self.cli.commands is non-empty, cli_group (options override self.cli_group) None merges commands into app.cli.commands directly; the sentinel renames the group to the registration name and adds it; any other value renames the group to that value and adds it. Nested blueprints: for each child, options are copied and subdomain computed (child's option, else its own; joined as child + '.' + parent when both exist, else whichever exists). url_prefix likewise (parent stripped of trailing slash, plus '/' plus child stripped of leading slash, else whichever exists). name_prefix is set to this blueprint's full name, then child.register(app, options) is called recursively.

calls: [Blueprint.make_setup_state](blueprint-deferred-registration.md#u-cdd8d4a4352d), [blueprints.py-merge-blueprint-funcs](blueprint-deferred-registration.md#u-ba470935275d), [Blueprint.register](../../catalog.json.gz)

**Uncertainties.**

- send_static_file is type-ignored and not defined in this batch, so the static view's behavior depends on the concrete subclass.

<a id="u-f6af7e7aaa66"></a>
### `Blueprint.register_blueprint`

`def register_blueprint(self, blueprint: Blueprint, **options: t.Any) -> None:` · [src/flask/sansio/blueprints.py:L255-L271][f1]

Registers a child blueprint on this blueprint.

Raises ValueError if the child is the blueprint itself; otherwise appends (blueprint, options) to _blueprints. Nothing is applied now; children are registered when this blueprint is itself registered on an app. A setup method.

<a id="u-14b96816dcf8"></a>
### `BlueprintSetupState.add_url_rule`

`def add_url_rule( self, rule: str, endpoint: str | None = None, view_func: ft.RouteCa…` · [src/flask/sansio/blueprints.py:L87-L116][f1]

Registers a rule on the real application on behalf of the blueprint, applying prefix, subdomain, endpoint naming and defaults.

If url_prefix is not None: a non-empty rule is joined as prefix.rstrip('/') + '/' + rule.lstrip('/'); an empty rule becomes the prefix itself. Subdomain is set with setdefault, so an explicit subdomain in options wins. A missing endpoint is derived from the view function name. Defaults start as the state's url_defaults; if options contains 'defaults' it is popped and merged over them. Calls app.add_url_rule with endpoint f'{name_prefix}.{name}.{endpoint}' with leading dots stripped, so an empty prefix yields 'name.endpoint'. Errors from the app (duplicate endpoints, bad methods) propagate.

calls: [_endpoint_from_view_func](scaffold-base-and-setup-decorators.md#u-5eef70528339), [App.add_url_rule](scaffold-base-and-setup-decorators.md#u-3cdcd592ec60)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/sansio/blueprints.py
[f2]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/sansio/app.py
