# Scaffold Registration Base

**Capability.** Behavior shared by Flask apps and blueprints: the route/endpoint/verb-shortcut decorators, error-handler registration and key normalization, request-hook registrars, static-folder resolution, the setupmethod lock that freezes registration after setup, and import-name path discovery. All of it mutates the registries initialized in Scaffold.__init__.

Use this subtree when you need to know how a decorator call becomes a stored view, handler, or hook. Note that the concrete add_url_rule is abstract here; App supplies the implementation. setupmethod is the guard every mutating registrar goes through.

**Depends on.**

- [Environment and Path Helpers](r2-environment-helpers.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Concrete WSGI Application](r1-concrete-app.md) · graph-confirmed · 2 edge(s) · Route/template-filter registration decorators call setupmethod, the shared Scaffold guard for mutating registration.
- [App-Scope Blueprint Hooks](r2-blueprint-app-integrations.md) · graph-only · 13 edge(s)
- [JSON Test Suite](r2-json-tests.md) · graph-only · 11 edge(s)
- [Context and Signal Tests](r2-context-lifecycle-tests.md) · graph-only · 5 edge(s)
- [Functional Behavior Tests](r1-tests-functional.md) · graph-only · 4 edge(s)
- [Blueprint Deferred Setup](r2-sansio-blueprint-core.md) · graph-only · 3 edge(s)
- [Logging Test Suite](r2-logging-tests.md) · graph-only · 2 edge(s)
- [App and Request Contexts](r1-contexts-teardown.md) · graph-only · 1 edge(s)
- [Exception and Error Handling](r1-error-handling.md) · graph-only · 1 edge(s)
- [Blueprint Registration](r2-blueprint-registration.md) · graph-only · 1 edge(s)
- [Flask Framework](r2-flask-framework.md) · graph-only · 1 edge(s)
- [Sans-I/O Application Core](r1-core-app-model.md) · within containment · 10 edge(s)
- [Flask Framework](r1-flask-framework.md) · within containment · 1 edge(s)

Parent: [Sans-I/O Application Core](r1-core-app-model.md)

## Units (16)

<a id="u-2ed8d6dfaa9a"></a>
### `Scaffold`

`class Scaffold:` · [src/flask/sansio/scaffold.py:L52-L75][f1]

Common base shared by Flask apps and blueprints: it stores the import name, root path, static/template folder configuration, and the registries (view functions, error handlers, request hooks, template context processors, URL helpers) that route registration and request handling populate.

It is an abstract scaffold: add_url_rule and _check_setup_finished raise NotImplementedError and must be implemented by subclasses. Class-level defaults set _static_folder and _static_url_path to None. The type annotations cli and name are declared without values and must be set elsewhere.

**Uncertainties.**

- Concrete name/cli values and setup-finished semantics come from subclasses; this file only shows the declarations and the NotImplementedError.

<a id="u-fd5da6beb6e6"></a>
### `Scaffold.__init__`

`def __init__( self, import_name: str, static_folder: str | os.PathLike[str] | None = …` · [src/flask/sansio/scaffold.py:L75-L215][f1]

Initializes the shared registries.

Stores import_name, and assigns static_folder and static_url_path through their property setters (stripping trailing slashes). If root_path is None it is derived by calling get_root_path(import_name); otherwise the supplied path is used as-is. All hook registries are defaultdicts keyed by scope (a blueprint name or None for app-wide): before/after/teardown request function lists, url_value_preprocessors, url_default_functions, and error_handler_spec as nested defaultdicts {scope: {code: {class: handler}}}. template_context_processors is pre-seeded with the app-scope entry [_default_template_ctx_processor], so app-scope renders always include the default context processor. view_functions starts as an empty plain dict.

calls: [get_root_path](r2-environment-helpers.md#u-da4504f7f768)

**Uncertainties.**

- Behavior of get_root_path for unknown import names is defined in helpers.py and not visible here.

<a id="u-81ccd06c4290"></a>
### `setupmethod`

`def setupmethod(f: F) -> F:` · [src/flask/sansio/scaffold.py:L42-L45][f1]

Decorates a method so it is blocked once setup (app/blueprint registration) has finished.

The returned wrapper calls the instance's _check_setup_finished with the decorated function's name before invoking the original function, then update_wrapper copies the original's metadata so the wrapper is transparent to callers. The original function runs unchanged otherwise; any exception _check_setup_finished raises propagates and the wrapped function is not called.

calls: [Scaffold](r1-scaffold-shared-base.md#u-2ed8d6dfaa9a)

**Uncertainties.**

- _check_setup_finished raises NotImplementedError here; the concrete setup-finished condition is defined by subclasses not in this file.

<a id="u-d7424e65b32f"></a>
### `Scaffold.route`

`def route(self, rule: str, **options: t.Any) -> t.Callable[[T_route], T_route]:` · [src/flask/sansio/scaffold.py:L335-L360][f1]

Decorator factory registering a view function under a URL rule.

When the returned decorator is applied to a function, it pops the optional 'endpoint' value out of options and calls add_url_rule(rule, endpoint, f, **remaining options), then returns the function unchanged. Being a setupmethod, the call is guarded by the setup-finished check. Methods default to GET at the add_url_rule layer, which this decorator does not inspect.

calls: [Scaffold.add_url_rule](r1-scaffold-shared-base.md#u-bc031014d4da)

<a id="u-bc031014d4da"></a>
### `Scaffold.add_url_rule`

`def add_url_rule( self, rule: str, endpoint: str | None = None, view_func: ft.RouteCa…` · [src/flask/sansio/scaffold.py:L367-L433][f1]

Abstract registration point for URL rules; this base implementation raises NotImplementedError.

Per the docstring contract, concrete implementations must default the endpoint to view_func.__name__, reject duplicate endpoint registrations, default methods to GET with HEAD added automatically and OPTIONS by default, honor view_func.required_methods and provide_automatic_methods attributes, and allow rules registered without a view function to later receive one via the endpoint decorator. Until a subclass overrides it, every call fails.

**Uncertainties.**

- The actual registration logic lives in subclasses (app.py/blueprints.py) and is not visible in this file.

<a id="u-bec6b7299a56"></a>
### `Scaffold.endpoint`

`def endpoint(self, endpoint: str) -> t.Callable[[F], F]:` · [src/flask/sansio/scaffold.py:L435-L453][f1]

Decorator binding a view function to a pre-declared endpoint name.

The returned decorator stores f into self.view_functions[endpoint] and returns f unchanged, so a rule added earlier without a view function can be completed. It is a setupmethod, so registration is blocked once setup finished; the assignment itself performs no duplicate-endpoint check here, silently overwriting an existing entry.

<a id="u-1d2cd6d2d565"></a>
### `Scaffold.errorhandler`

`def errorhandler( self, code_or_exception: type[Exception] | int ) -> t.Callable[[T_e…` · [src/flask/sansio/scaffold.py:L597-L635][f1]

Decorator factory registering an error handler by HTTP status code (int) or exception class.

The returned decorator calls register_error_handler(code_or_exception, f) and returns f unchanged, so all validation and storage happen there; an invalid code or class raises at decoration time, not at error time. Blueprint-scoped equivalents exist elsewhere; this always registers app-wide under the None scope via register_error_handler.

calls: [Scaffold.register_error_handler](r1-scaffold-shared-base.md#u-62e789484fe6)

<a id="u-62e789484fe6"></a>
### `Scaffold.register_error_handler`

`def register_error_handler( self, code_or_exception: type[Exception] | int, f: ft.Err…` · [src/flask/sansio/scaffold.py:L641-L654][f1]

Non-decorator form of errorhandler: normalizes code_or_exception via _get_exc_class_and_code, then stores the handler at error_handler_spec[None][code][exc_class].

Because error_handler_spec is a defaultdict-of-defaultdicts, accessing [None] creates the scope and code entries on demand. Any ValueError/TypeError from normalization propagates before storage, so a failed registration leaves the spec unchanged.

calls: [Scaffold._get_exc_class_and_code](r1-scaffold-shared-base.md#u-9b269dc0fdb3)

<a id="u-9b269dc0fdb3"></a>
### `Scaffold._get_exc_class_and_code`

`def _get_exc_class_and_code( exc_class_or_code: type[Exception] | int, ) -> tuple[typ…` · [src/flask/sansio/scaffold.py:L656-L698][f1]

Normalizes an error-handler key to (exception class, status code or None).

If given an int, it looks the code up in werkzeug's default_exceptions; an unknown code raises ValueError (chained from None) telling the caller to use an HTTPException subclass. If given a class it is used directly. An instance of Exception (not a class) raises TypeError; a non-Exception class raises ValueError. If the resolved class subclasses HTTPException, returns (class, class.code); otherwise returns (class, None), meaning the handler is keyed for that exception type regardless of status code.

**Notes.**

- failure: KeyError from the default_exceptions lookup is caught and re-raised as ValueError; TypeError/ValueError from the class checks propagate to the caller.

<a id="u-524d6ad4d5d6"></a>
### `Scaffold.static_folder`

`def static_folder(self) -> str | None:` · [src/flask/sansio/scaffold.py:L223-L231][f1]

Getter returns the absolute static folder path or None.

Property pair managing the configured static folder. The getter joins _static_folder with root_path when set, returning an absolute path; otherwise None. The setter converts a path-like value via os.fspath and strips any trailing forward or back slashes before storing it in _static_folder; None is stored unchanged.

**Notes.**

- contract: has_static_folder is True exactly when the getter yields a non-None absolute path; jinja_loader is unrelated to this property.

<a id="u-620a2ebcac73"></a>
### `src/flask/sansio/scaffold.py:Scaffold.static_url_path`

`def static_url_path(self) -> str | None:` · [src/flask/sansio/scaffold.py:L248-L262][f1]

Getter derives the static URL prefix from the static folder when not explicitly configured.

If _static_url_path is set it is returned directly. Otherwise, if a static folder is set, the prefix is '/' plus the folder's basename with trailing slashes stripped; with no static folder it returns None. The setter rstrip's trailing '/' from non-None values before storing. Note the getter uses the absolute static_folder, so the basename is taken from the resolved path, though it normally equals the configured folder name.

**Uncertainties.**

- The getter rstrips '/' from '/{basename}'; a basename that is empty after stripping would yield an empty string, which the code does not guard against.

<a id="u-bbd07a7cf1ec"></a>
### `scaffold.py-http-verb-shortcuts`

`def _method_route( self, method: str, rule: str, options: dict[str, t.Any], ) -> t.Ca…` · [src/flask/sansio/scaffold.py:L284-L293][f1]

Shortcuts get/post/put/delete/patch each delegate to _method_route with their HTTP method name, returning a route decorator.

_method_route raises TypeError if the caller supplied a 'methods' key in options, forcing use of the full route decorator; otherwise it returns self.route(rule, methods=[method], **options). All are wrapped in setupmethod, so each checks setup-finished before running. If setup already finished, the wrapper raises before any options validation.

calls: [Scaffold.route](r1-scaffold-shared-base.md#u-d7424e65b32f)

<a id="u-f78ddda5923a"></a>
### `scaffold.py-request-hook-registrars`

`def before_request(self, f: T_before_request) -> T_before_request:` · [src/flask/sansio/scaffold.py:L459-L484][f1]

Registrars for request and template hooks on the app (None) scope.

before_request, after_request, and teardown_request append f to before/after/teardown_request_funcs under key None and return f unchanged; on a blueprint these still register under None, with blueprint-scoped variants handled elsewhere. after_request functions receive and must return the response; if one raises, later after_request functions are skipped, so must-run cleanup belongs in teardown_request, which receives the exception object on unhandled errors, has its return value ignored, and must not itself raise. context_processor appends to template_context_processors[None] so returned dicts become template variables app-wide (the list already contains the default context processor from __init__). url_value_preprocessor appends to url_value_preprocessors[None]; it receives the endpoint and values dict and may modify values before views see them, return value ignored. url_defaults appends to url_default_functions[None]; it receives endpoint and values and should update values in place for URL generation. All are setupmethod-wrapped, so registration raises once setup finished.

**Uncertainties.**

- When these hook lists are actually executed during a request is implemented outside this file; here only registration is visible.

<a id="u-5eef70528339"></a>
### `_endpoint_from_view_func`

`def _endpoint_from_view_func(view_func: ft.RouteCallable) -> str:` · [src/flask/sansio/scaffold.py:L701-L706][f1]

Returns the default endpoint name for a view function: its __name__.

It asserts view_func is not None, so a call with None fails the assertion (the caller is expected to pass a function whenever no explicit endpoint was given); otherwise the function name string is returned with no other logic.

<a id="u-9a80c302e7bb"></a>
### `find_package`

`def find_package(import_name: str) -> tuple[str | None, str]:` · [src/flask/sansio/scaffold.py:L754-L792][f1]

Determines the install prefix of a package and the sys.path-style directory containing it.

It calls _find_package_path to get package_path, then: if that path is under the absolute sys.prefix, returns (py_prefix, package_path) for a system install. Otherwise, if the path's final folder is 'site-packages' (case-insensitive), it inspects the parent: a 'lib' folder parent means a Windows layout and returns (that parent, package_path); a parent whose own basename is 'lib' means Unix prefix/lib/pythonX.Y/site-packages and returns (dirname of that parent, package_path); any other layout returns (site_parent, package_path). If neither condition holds, the package is treated as not installed and (None, package_path) is returned.

calls: [_find_package_path](r1-scaffold-shared-base.md#u-79978c79c17d)

<a id="u-79978c79c17d"></a>
### `_find_package_path`

`def _find_package_path(import_name: str) -> str:` · [src/flask/sansio/scaffold.py:L709-L751][f1]

Locates the filesystem directory containing the package or module named by import_name.

It splits off the root module name and resolves it with importlib.util.find_spec; if that raises ImportError or ValueError (invalid name, __main__, or a spec of None, which the code raises itself), it returns os.getcwd(). If the root spec has submodule_search_locations: for a namespace package (origin None or 'namespace') it tries to resolve the full import_name's spec; if that spec has search locations it picks the common path of those locations and returns os.path.dirname of the first root search location containing it, else falls back to the first root search location's dirname. For a regular package with __init__.py it returns os.path.dirname(os.path.dirname(origin)), i.e. the parent of the package directory. For a plain module (no search locations) it returns the directory of origin.

**Notes.**

- failure: If the full name is a namespace submodule and its spec lacks search locations, the first root search location is used; the generator in the commonpath branch would raise StopIteration if no root location contains the package path, which is not handled.

**Uncertainties.**

- root_spec.origin is typed as possibly None; the plain-module branch indexes it without a None check (silenced with a type-ignore).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/sansio/scaffold.py
