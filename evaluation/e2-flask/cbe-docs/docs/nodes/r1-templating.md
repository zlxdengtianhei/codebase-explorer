# Template Rendering

**Capability.** Jinja integration: the Flask-aware Environment, a DispatchingJinjaLoader that searches app and blueprint loaders (with an explained-failure path feeding diagnostics), render_template/render_template_string with signal dispatch and context processors, and streaming variants that yield output incrementally. Environment construction and autoescape policy hang off the app.

Use this subtree to trace how a template name resolves across app and blueprint folders and how context processors inject variables. Streaming variants return iterators instead of full strings; loader failures get the explained diagnostic path.

**Depends on.**

- [Sans-I/O Application Core](r1-core-app-model.md) · graph-confirmed · 1 edge(s) · create_global_jinja_loader constructs the DispatchingJinjaLoader, and jinja_env drives environment creation off the app.
- [Diagnostics and Debug Errors](r1-debug-helpers.md) · graph-confirmed · 1 edge(s) · The loader's explained-failure path calls explain_template_loading_attempts for template-loading diagnostics.
- [Request Dispatch Pipeline](r1-request-dispatch.md) · graph-only · 1 edge(s)
- [stream\_with\_context](r2-streaming-helpers.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Fixture Applications](r1-tests-fixture-apps.md) · model-inferred · 0 edge(s)

Parent: [Flask Framework](r1-flask-framework.md)

## Units (16)

<a id="u-4d36739b53d0"></a>
### `Environment`

`class Environment(BaseEnvironment):` · [src/flask/templating.py:L39-L45][f1]

A Jinja2 Environment subclass aware of Flask's app/blueprint template layout.

__init__ injects a default loader: if the caller did not pass 'loader' in options, app.create_global_jinja_loader() is used, so a custom loader passed via options replaces Flask's dispatching loader entirely. It then initializes the Jinja base and stores the app as self.app.

uses: [DispatchingJinjaLoader](r1-templating.md#u-86b8c98f3d78)

<a id="u-86b8c98f3d78"></a>
### `DispatchingJinjaLoader`

`class DispatchingJinjaLoader(BaseLoader):` · [src/flask/templating.py:L52-L57][f1]

A Jinja loader that searches the app's loader and every blueprint's loader.

__init__ stores only the app. get_source delegates to _get_source_explained when config['EXPLAIN_TEMPLATE_LOADING'] is true, otherwise to _get_source_fast. _iter_loaders yields (scaffold, loader) pairs: first the app with its jinja_loader, then each blueprint from app.iter_blueprints() with its jinja_loader, skipping scaffolds with no loader. list_templates unions all loaders' template lists into a set and returns the deduplicated list; order is therefore unspecified.

**Uncertainties.**

- Whether iter_blueprints ordering is stable is not determined here.

<a id="u-e8e6fd78dfd8"></a>
### `DispatchingJinjaLoader._get_source_fast`

`def _get_source_fast( self, environment: BaseEnvironment, template: str ) -> tuple[st…` · [src/flask/templating.py:L91-L99][f1]

First-match template lookup.

It iterates _iter_loaders and returns the first loader.get_source result; TemplateNotFound from one loader is swallowed and the next loader is tried. If no loader yields a source, TemplateNotFound is raised for the template name.

<a id="u-dd9ec306c4bf"></a>
### `DispatchingJinjaLoader._get_source_explained`

`def _get_source_explained( self, environment: BaseEnvironment, template: str ) -> tup…` · [src/flask/templating.py:L67-L89][f1]

Template lookup with full diagnostics.

It iterates every loader from _iter_loaders, calling loader.get_source and recording each outcome (TemplateNotFound becomes rv = None); the first successful result is remembered as trv. After all attempts it imports and calls explain_template_loading_attempts to log the report, returns trv if any loader matched, and otherwise raises TemplateNotFound for the template.

calls: [explain_template_loading_attempts](r1-debug-helpers.md#u-6856219e158f); uses: [DispatchingJinjaLoader](r1-templating.md#u-86b8c98f3d78)

<a id="u-ac93acab0ceb"></a>
### `_default_template_ctx_processor`

`def _default_template_ctx_processor() -> dict[str, t.Any]:` · [src/flask/templating.py:L24-L36][f1]

Builds the default template context by injecting Flask's implicit variables.

It reads the current app and request contexts via the context-vars sentinels; 'g' is added only when an app context is active, and 'request' and 'session' only when a request context is active. With no contexts active it returns an empty dict.

<a id="u-7946814d7c34"></a>
### `_render`

`def _render(app: Flask, template: Template, context: dict[str, t.Any]) -> str:` · [src/flask/templating.py:L126-L135][f1]

Renders a template to a string with signal dispatch.

It first asks the app to update the context with processor values, sends before_render_template, calls template.render(context), then sends template_rendered, and returns the rendered string. Signal sends use app.ensure_sync as the async wrapper; failures inside render propagate to the caller.

uses: [render_template](r1-templating.md#u-a5b7d66b7ea8), [render_template_string](r1-templating.md#u-f3ccecd24256)

<a id="u-a5b7d66b7ea8"></a>
### `render_template`

`def render_template( template_name_or_list: str | Template | list[str | Template], **…` · [src/flask/templating.py:L138-L150][f1]

Renders a template by name, Template object, or list of these, with keyword context.

It resolves current_app to the real app, uses app.jinja_env.get_or_select_template so a list picks the first existing template, then delegates to _render for context update, signals, and rendering. Requires an active app context.

calls: [_render](r1-templating.md#u-7946814d7c34)

<a id="u-f3ccecd24256"></a>
### `render_template_string`

`def render_template_string(source: str, **context: t.Any) -> str:` · [src/flask/templating.py:L153-L162][f1]

Renders a template compiled from the given source string with keyword context.

It resolves current_app, compiles via app.jinja_env.from_string, and delegates to _render for context update, signal dispatch, and rendering. Template name/lookup machinery does not apply.

calls: [_render](r1-templating.md#u-7946814d7c34)

<a id="u-c8e749b54f01"></a>
### `stream_template`

`def stream_template( template_name_or_list: str | Template | list[str | Template], **…` · [src/flask/templating.py:L188-L204][f1]

Renders a template by name, Template object, or list as a stream.

It resolves current_app, selects the template with app.jinja_env.get_or_select_template (first existing name in a list wins), and returns the iterator produced by _stream; nothing is rendered until the iterator is consumed.

calls: [templating.py-_stream](r1-templating.md#u-22f9e0781d9c)

<a id="u-557a3a767477"></a>
### `stream_template_string`

`def stream_template_string(source: str, **context: t.Any) -> t.Iterator[str]:` · [src/flask/templating.py:L207-L219][f1]

Renders a template compiled from the given source string as a stream.

It resolves current_app, compiles with app.jinja_env.from_string, and returns the _stream iterator; output is produced lazily on consumption.

calls: [templating.py-_stream](r1-templating.md#u-22f9e0781d9c)

<a id="u-22f9e0781d9c"></a>
### `templating.py-_stream`

`def _stream( app: Flask, template: Template, context: dict[str, t.Any] ) -> t.Iterato…` · [src/flask/templating.py:L165-L173][f1]

Streams a template's output as an iterator of strings instead of rendering it whole.

It updates the context via the app and sends before_render_template up front. The nested generate() generator yields template.generate(context) chunks and only after the final chunk sends template_rendered, so the signal fires when streaming completes. If a request context is active (truthy request proxy), the generator is wrapped with stream_with_context so the request context stays alive during lazy iteration; otherwise the raw generator is returned.

uses: [src/flask/helpers.py:stream_with_context (2)](r2-streaming-helpers.md#u-22c67a9b00e0)

**Uncertainties.**

- If the generator is never exhausted, template_rendered never fires.

<a id="u-f0108cd6a729"></a>
### `Flask.create_jinja_environment`

`def create_jinja_environment(self) -> Environment:` · [src/flask/app.py:L385-L423][f2]

Build the Jinja environment once from jinja_options.

Copies the options dict; fills in autoescape with select_jinja_autoescape when absent, and auto_reload from TEMPLATES_AUTO_RELOAD, falling back to self.debug when that config is None. Instantiates jinja_environment with the app and options, injects template globals (url_for, get_flashed_messages, config, and the request/session/g proxies so imported templates can access them), sets the json.dumps_function policy to self.json.dumps, and returns it. Mutating jinja_options afterwards has no effect because options were copied here.

uses: [Flask.url_for](r1-url-building-resources.md#u-f591687825aa)

**Uncertainties.**

- jinja_environment and select_jinja_autoescape are inherited attributes/methods not visible in this file.

<a id="u-927338959329"></a>
### `Flask.update_template_context`

`def update_template_context(self, context: dict[str, t.Any]) -> None:` · [src/flask/app.py:L506-L532][f2]

Inject context-processor values into a template context dict in place.

Starts with name None (app-level), chained with reversed(request.blueprints) only when a request is active, so rendering works outside a request too. Saves a copy of the incoming context, then for each name runs its registered processors via ensure_sync, updating the dict; finally re-applies the original copy so values passed to render_template win over processor output.

**Notes.**

- contract: Original caller-supplied keys always override context-processor keys of the same name, applied after all processors run.

**Uncertainties.**

- request is a proxy; truthiness of request outside a request context relies on proxy behavior defined elsewhere.

<a id="u-76927d5a1e1f"></a>
### `App.jinja_env`

`def jinja_env(self) -> Environment:` · [src/flask/sansio/app.py:L469-L477][f3]

Lazily builds and caches the Jinja environment by calling create_jinja_environment.

Because the environment exists after the first access, later mutations of jinja_options have no effect.

calls: [App](r1-core-app-model.md#u-c945a7570d6a)

<a id="u-88c7e542733f"></a>
### `App.create_global_jinja_loader`

`def create_global_jinja_loader(self) -> DispatchingJinjaLoader:` · [src/flask/sansio/app.py:L523-L534][f3]

Returns the loader for the Jinja environment: a DispatchingJinjaLoader over this app, which dispatches between the app's templates and registered blueprints' loaders.

The docstring discourages overriding this; overriding jinja_loader (on Scaffold) is the intended hook.

calls: [DispatchingJinjaLoader](r1-templating.md#u-86b8c98f3d78)

<a id="u-1a7f67b1b674"></a>
### `App.select_jinja_autoescape`

`def select_jinja_autoescape(self, filename: str) -> bool:` · [src/flask/sansio/app.py:L536-L547][f3]

Decides per-template autoescaping.

Returns True when filename is None (inline templates), otherwise True only for names ending in .html, .htm, .xml, .xhtml, or .svg; all other extensions get no autoescape.

**Uncertainties.**

- The annotation is str but the code compares filename to None, so None appears tolerated at runtime despite the signature.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/templating.py
[f2]: ../../../../../../eval/flask-85c5d93/src/flask/app.py
[f3]: ../../../../../../eval/flask-85c5d93/src/flask/sansio/app.py
