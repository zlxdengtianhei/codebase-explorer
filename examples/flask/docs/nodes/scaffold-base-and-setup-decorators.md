# Scaffold Base and Setup Decorators

**Capability.** Provides the Scaffold base class shared by apps and blueprints, with route, error handler and callback registration decorators plus static folder and path helpers.

Come here to see how routes, HTTP-verb shortcuts, hooks and error handlers are registered on an app or blueprint. It holds the Scaffold class, the setupmethod guard, and abstract rule registration that subclasses implement.

**Depends on.**

- [Helpers, Flask Blueprint and Run](helpers-flask-blueprint-and-run.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Blueprint Deferred Registration](blueprint-deferred-registration.md) · graph-confirmed · 19 edge(s) · 2 inferred relation(s) · The sansio Blueprint uses the Scaffold setup decorators and setup-finished checks to guard and record its deferred registrations.
- [Sansio App Base Class](sansio-app-base-class.md) · graph-only · 9 edge(s)

Parent: [Scaffold and Blueprint Registration](scaffold-and-blueprint-registration.md)

## Units (22)

<a id="u-9d6999ad07f0"></a>
### `scaffold.py-context-and-url-callbacks`

`def context_processor( self, f: T_template_context_processor, ) -> T_template_context…` · [src/flask/sansio/scaffold.py:L541-L556][f1]

context_processor, url_value_preprocessor and url_defaults are setup methods that append f to the None-scope list of template_context_processors, url_value_preprocessors or url_default_functions and return f unchanged.

These use direct indexing on defaultdicts, creating the None entry if needed. On a blueprint, None scope means that blueprint's own requests.

<a id="u-5abafff9c523"></a>
### `scaffold.py-endpoint`

`def endpoint(self, endpoint: str) -> t.Callable[[F], F]:` · [src/flask/sansio/scaffold.py:L435-L453][f1]

endpoint(name) is a setup-method decorator factory that associates a view function with an endpoint name directly in view_functions.

The inner decorator assigns view_functions[endpoint] = f and returns f unchanged. Unlike add_url_rule, it performs no duplicate-endpoint check, so it overwrites an existing entry silently.

<a id="u-d029878e2400"></a>
### `scaffold.py-errorhandler`

`def errorhandler( self, code_or_exception: type[Exception] | int ) -> t.Callable[[T_e…` · [src/flask/sansio/scaffold.py:L597-L635][f1]

errorhandler(code_or_exception) is a setup-method decorator factory.

The inner decorator calls register_error_handler(code_or_exception, f) and returns f unchanged. Invalid codes or non-exception classes raise from the resolution helper at decoration time.

<a id="u-11c2cd02a992"></a>
### `scaffold.py-http-method-shortcuts`

`def get(self, rule: str, **options: t.Any) -> t.Callable[[T_route], T_route]:` · [src/flask/sansio/scaffold.py:L295-L301][f1]

get, post, put, delete and patch are setup methods that return route decorators fixed to a single HTTP method by calling _method_route with GET, POST, PUT, DELETE or PATCH respectively.

Passing 'methods' in options raises TypeError.

<a id="u-2e0fd8b5ac1d"></a>
### `scaffold.py-request-lifecycle-registrations`

`def before_request(self, f: T_before_request) -> T_before_request:` · [src/flask/sansio/scaffold.py:L459-L484][f1]

before_request, after_request and teardown_request are setup methods that register a callback for this object's app-wide (None) scope.

Each does setdefault(None, []).append(f) on before_request_funcs, after_request_funcs or teardown_request_funcs respectively, and returns f unchanged. On a blueprint the None key means requests handled by that blueprint.

<a id="u-e6d0d54380a0"></a>
### `scaffold.py-route`

`def route(self, rule: str, **options: t.Any) -> t.Callable[[T_route], T_route]:` · [src/flask/sansio/scaffold.py:L335-L360][f1]

route(rule, **options) is a setup-method decorator factory for view registration.

The inner decorator pops 'endpoint' from options (default None), calls self.add_url_rule(rule, endpoint, f, **options) and returns f unchanged. The pop mutates the options dict captured by the closure, so applying the same returned decorator to a second function would lose the endpoint option.

calls: [Scaffold.add_url_rule](scaffold-base-and-setup-decorators.md#u-bc031014d4da)

<a id="u-de0aacedffad"></a>
### `scaffold.py-setupmethod`

`def setupmethod(f: F) -> F:` · [src/flask/sansio/scaffold.py:L42-L45][f1]

setupmethod is a decorator that wraps a registration method with a pre-call guard.

The wrapper calls self._check_setup_finished(f_name) with the wrapped function's name before invoking the function with the original arguments and returning its result. Whether the guard raises depends on the subclass override; it propagates unchanged. update_wrapper copies the wrapped function's metadata onto the wrapper.

<a id="u-c4ec36d95164"></a>
### `scaffold.py-static-folder`

`def static_folder(self) -> str | None:` · [src/flask/sansio/scaffold.py:L223-L231][f1]

static_folder property exposes the configured static directory.

The getter returns os.path.join(root_path, _static_folder), or None if none is set. The setter converts the value with os.fspath and strips trailing slashes and backslashes (None stays None) before storing it; the stored value is relative or absolute as given (an absolute value wins in os.path.join). has_static_folder is True when the getter returns a non-None value.

<a id="u-52ad74f2629e"></a>
### `scaffold.py-static-url-path`

`def static_url_path(self) -> str | None:` · [src/flask/sansio/scaffold.py:L248-L262][f1]

static_url_path property gives the URL prefix of the static route.

The getter returns the explicitly configured value if set; otherwise, if a static folder exists, '/' plus the folder's basename with trailing slashes stripped; otherwise None. The setter strips trailing slashes from a non-None value; None clears it so derivation applies again.

<a id="u-3cdcd592ec60"></a>
### `App.add_url_rule`

`def add_url_rule( self, rule: str, endpoint: str | None = None, view_func: ft.RouteCa…` · [src/flask/sansio/app.py:L604-L661][f2]

Creates a routing Rule for the app and records the view function.

This is the concrete implementation of the Scaffold abstract method and is a setup method.
Endpoint defaults to the view function's __name__ via _endpoint_from_view_func (an assertion fails if view_func is also None). "methods" is popped from options; if None it falls back to view_func.methods, then to ("GET",). A str methods value raises TypeError; otherwise methods are uppercased into a set. Required methods come from view_func.required_methods. provide_automatic_options, when None, falls back to view_func.provide_automatic_options; if still None, it becomes True and adds OPTIONS to the required set only when OPTIONS is absent from methods and config PROVIDE_AUTOMATIC_OPTIONS is truthy, else False. Required methods are merged in; the Rule is built from url_rule_class(rule, methods=..., **options) with provide_automatic_options set as an attribute, then added to url_map. If view_func is not None: an existing different function registered for the same endpoint (checked with !=) raises AssertionError, otherwise it is stored in view_functions. The rule is added to the map before that check, so the map is already modified when the duplicate-endpoint error is raised.

calls: [_endpoint_from_view_func](scaffold-base-and-setup-decorators.md#u-5eef70528339); overrides: [Scaffold.add_url_rule](scaffold-base-and-setup-decorators.md#u-bc031014d4da)

**Uncertainties.**

- Rule construction errors from url_rule_class and url_map.add are not visible here.

<a id="u-2ed8d6dfaa9a"></a>
### `Scaffold`

`class Scaffold:` · [src/flask/sansio/scaffold.py:L52-L75][f1]

Scaffold is the base class shared by Flask applications and Blueprints.

It holds paths, static/template configuration and the registries of routes and callbacks, and provides the decorators that populate them.
Subclasses must implement _check_setup_finished and add_url_rule, which raise NotImplementedError here. Class attributes cli and name are only annotated, so subclasses supply them. _static_folder and _static_url_path default to None.

<a id="u-5eef70528339"></a>
### `_endpoint_from_view_func`

`def _endpoint_from_view_func(view_func: ft.RouteCallable) -> str:` · [src/flask/sansio/scaffold.py:L701-L706][f1]

Returns view_func.__name__ as the default endpoint name.

Uses an assert that view_func is not None, so a missing view function raises AssertionError (unless assertions are disabled, where it would fail on attribute access).

<a id="u-79978c79c17d"></a>
### `_find_package_path`

`def _find_package_path(import_name: str) -> str:` · [src/flask/sansio/scaffold.py:L709-L751][f1]

Returns the directory that contains a package or module, used for locating it on disk.

Only the first dotted component of import_name is inspected via importlib.util.find_spec. If find_spec returns None or raises ImportError or ValueError (invalid name, __main__ and similar), the current working directory is returned. If the root spec has submodule_search_locations (a package): for a namespace package (origin None or 'namespace'), the full import_name is resolved, and if it has search locations the common path of those is matched to the first root location that contains it (next() would raise StopIteration if none matches); otherwise the first root location is used; the result is its parent directory. For a regular package, the result is two dirname levels above its __init__ origin. For a plain module it is the directory of the module's origin.

<a id="u-9a80c302e7bb"></a>
### `find_package`

`def find_package(import_name: str) -> tuple[str | None, str]:` · [src/flask/sansio/scaffold.py:L754-L792][f1]

Finds where a package is installed and the sys.path entry it is imported from, returning (prefix, package_path).

It calls _find_package_path, then compares with the absolute sys.prefix. If package_path is under sys.prefix, returns (sys.prefix, package_path). Otherwise if the last path component is 'site-packages' (case-insensitive), the prefix is derived: parent folder 'lib' (Windows layout) gives the grandparent directory; a Unix layout where the parent's parent folder is 'lib' gives that directory's parent; anything else gives the site-packages parent. If not under a prefix or site-packages, returns (None, package_path), meaning not installed. Pure path logic with no filesystem writes.

calls: [_find_package_path](scaffold-base-and-setup-decorators.md#u-79978c79c17d)

<a id="u-fd5da6beb6e6"></a>
### `Scaffold.__init__`

`def __init__( self, import_name: str, static_folder: str | os.PathLike[str] | None = …` · [src/flask/sansio/scaffold.py:L75-L215][f1]

Initializes the shared state of an application or blueprint.

Stores import_name, then assigns static_folder and static_url_path through their property setters, and template_folder. root_path defaults to get_root_path(import_name) when None. Creates empty view_functions and the registries: error_handler_spec (nested defaultdicts), before_request_funcs, after_request_funcs, teardown_request_funcs, url_value_preprocessors and url_default_functions (defaultdict(list)), and template_context_processors, which starts with {None: [_default_template_ctx_processor]}. The registries are keyed by None for app-wide scope or a blueprint name.

calls: [get_root_path](../../catalog.json.gz)

<a id="u-83ed2a11651d"></a>
### `Scaffold.__repr__`

`def __repr__(self) -> str:` · [src/flask/sansio/scaffold.py:L217-L218][f1]

Returns a debug representation of the form <ClassName 'name'> using the runtime class name and self.name.

<a id="u-bb5a9a7a65c7"></a>
### `Scaffold._check_setup_finished`

`def _check_setup_finished(self, f_name: str) -> None:` · [src/flask/sansio/scaffold.py:L220-L221][f1]

Abstract guard for setup methods; the base implementation always raises NotImplementedError and must be overridden by subclasses.

<a id="u-9b269dc0fdb3"></a>
### `Scaffold._get_exc_class_and_code`

`def _get_exc_class_and_code( exc_class_or_code: type[Exception] | int, ) -> tuple[typ…` · [src/flask/sansio/scaffold.py:L656-L698][f1]

Static helper that normalizes an HTTP status code or exception class into a (class, code) tuple.

An int is looked up in werkzeug default_exceptions; a missing code raises ValueError (cause suppressed). Other values are used as the class directly. If the result is an Exception instance, raises TypeError (instance instead of class). If it is not a subclass of Exception, raises ValueError (a non-class argument would raise TypeError from issubclass instead, since only an Exception instance is checked beforehand). For HTTPException subclasses returns (class, class.code), where code may be None for the base class; any other exception class returns (class, None).

<a id="u-be159a7133a5"></a>
### `Scaffold._method_route`

`def _method_route( self, method: str, rule: str, options: dict[str, t.Any], ) -> t.Ca…` · [src/flask/sansio/scaffold.py:L284-L293][f1]

Shared helper behind the HTTP-verb shortcuts.

If the options dict contains 'methods', it raises TypeError directing the caller to route. Otherwise returns self.route(rule, methods=[method], **options), the decorator.

calls: [scaffold.py-route](scaffold-base-and-setup-decorators.md#u-e6d0d54380a0)

<a id="u-bc031014d4da"></a>
### `Scaffold.add_url_rule`

`def add_url_rule( self, rule: str, endpoint: str | None = None, view_func: ft.RouteCa…` · [src/flask/sansio/scaffold.py:L367-L433][f1]

Abstract definition of URL rule registration (rule, endpoint, view_func, provide_automatic_options, options).

The base implementation raises NotImplementedError; Flask apps and blueprints provide the concrete versions. The docstring describes the intended defaults, such as GET-only methods and automatic HEAD/OPTIONS.

<a id="u-a575979fb70d"></a>
### `Scaffold.jinja_loader`

`def jinja_loader(self) -> BaseLoader | None:` · [src/flask/sansio/scaffold.py:L271-L282][f1]

Cached property providing the Jinja loader for this object's templates.

If template_folder is not None, returns a FileSystemLoader over os.path.join(root_path, template_folder); otherwise None. The result is cached after the first access, so later template_folder changes are not seen.

<a id="u-62e789484fe6"></a>
### `Scaffold.register_error_handler`

`def register_error_handler( self, code_or_exception: type[Exception] | int, f: ft.Err…` · [src/flask/sansio/scaffold.py:L641-L654][f1]

Registers an error handler under the None scope.

It resolves the argument with _get_exc_class_and_code, then sets error_handler_spec[None][code][exc_class] = f, replacing any existing handler for the same class. Raises ValueError or TypeError from the resolution helper for invalid codes or classes. Setup method.

calls: [Scaffold._get_exc_class_and_code](scaffold-base-and-setup-decorators.md#u-9b269dc0fdb3)

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/sansio/scaffold.py
[f2]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/sansio/app.py
