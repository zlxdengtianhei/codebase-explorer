# View and MethodView Core

**Capability.** Base View requires dispatch_request and provides as_view(name) to produce a routed function; MethodView subclasses auto-derive methods and dispatch by lowercased HTTP method name.

Read this before writing custom views. __init_subclass__ computes cls.methods from defined handlers unless explicitly set; as_view is shared by both classes.

**Depended on by.**

- [View and Async Dispatch Tests](r2-view-tests.md) · model-inferred · 0 edge(s)

Parent: [Class-Based Views](r2-view-system.md)

## Units (5)

<a id="u-9c7d9676c296"></a>
### `View`

`class View:` · [src/flask/views.py:L16-L78][f1]

Base class for class-based views; subclasses override dispatch_request and register as_view(name)'s generated function for a route.

Class attributes shape routing behavior: methods (default None, falls back to the route default GET/HEAD/OPTIONS), provide_automatic_options (None, route default True), decorators (applied to the generated view function, not the class), and init_every_request (default True, meaning a fresh instance per request; False shares one instance, making self-storage across requests unsafe). dispatch_request itself is abstract and raises NotImplementedError with URL variables passed as keyword arguments.

<a id="u-6ed5ce9cd825"></a>
### `MethodView`

`class MethodView(View):` · [src/flask/views.py:L138-L165][f1]

A View subclass that dispatches by HTTP method to same-named lowercase instance methods (get handles GET, post handles POST, etc.).

Subclasses automatically derive their methods set at class creation time, so they need not set View.methods manually.

<a id="u-45dd9f3b6b44"></a>
### `View.as_view`

`def as_view( cls, name: str, *class_args: t.Any, **class_kwargs: t.Any ) -> ft.RouteC…` · [src/flask/views.py:L85-L106][f1]

Converts the view class into a plain view function.

If init_every_request is True, view() constructs a new instance per call with the class_args/class_kwargs captured at as_view time; otherwise one instance is created when as_view runs and reused for every request. Both paths call current_app.ensure_sync(self.dispatch_request)(**kwargs) with the URL variables. If cls.decorators is non-empty, view gets its __name__/__module__ set first and then each decorator wraps it in list order. Finally the function is tagged with view_class, __name__, __doc__, __module__, methods, and provide_automatic_options from the class, so routing reads these attributes; decorator replacement of the function is preserved because tagging happens after decoration.

uses: [View](r2-view-core.md#u-9c7d9676c296); inherits: [MethodView](r2-view-core.md#u-6ed5ce9cd825)

**Uncertainties.**

- The graph lists 13 candidates for decorator(view); the actual decorators are whatever cls.decorators contains at runtime.
- Behavior when a decorator strips or replaces attached attributes is not handled in this code.

<a id="u-2f38fa122265"></a>
### `MethodView.__init_subclass__`

`def __init_subclass__(cls, **kwargs: t.Any) -> None:` · [src/flask/views.py:L165-L180][f1]

Runs at subclass creation to auto-set cls.methods when the subclass does not define 'methods' in its own __dict__.

It starts from the union of any truthy methods attributes on the direct bases, adds the uppercase form of every name in http_method_funcs (get/post/head/options/delete/put/trace/patch) that the class has as an attribute, and assigns the resulting set to cls.methods only if non-empty; a subclass with no handlers inherits no methods attribute change.

uses: [View](r2-view-core.md#u-9c7d9676c296)

**Uncertainties.**

- Only direct bases are scanned for inherited methods, not the full MRO.

<a id="u-55d9ca77774c"></a>
### `MethodView.dispatch_request`

`def dispatch_request(self, **kwargs: t.Any) -> ft.ResponseReturnValue:` · [src/flask/views.py:L182-L191][f1]

Dispatches the request to the instance method matching the HTTP method name lowercased.

If no such handler exists and the method is HEAD, it falls back to 'get'. If no handler is found it raises AssertionError 'Unimplemented method <METHOD>' (assert, so it disappears under python -O, leaving AttributeError behavior uncertain). Otherwise it calls current_app.ensure_sync(meth)(**kwargs) with the URL rule variables and returns its result.

**Uncertainties.**

- Under -O the assert is stripped, so the failure path for an unimplemented method differs and is not shown here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/views.py
