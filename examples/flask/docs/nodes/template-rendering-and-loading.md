# Template Rendering and Loading

**Capability.** Handles Jinja integration: the app-bound environment, a loader spanning app and blueprints, and render and stream functions with signals and context processors.

Go here for how templates are located and rendered. It includes the dispatching loader, render_template and streaming variants, the default context processor and streamed-response context preservation.

**Depends on.**

- [Views, Wrappers, Signals and Debug Aids](views-wrappers-signals-and-debug-aids.md) · graph-confirmed · 1 edge(s)

Parent: [Templates, Views and Wrappers](templates-views-and-wrappers.md)

## Units (18)

<a id="u-123009fa213a"></a>
### `helpers.py-stream-with-context`

`def stream_with_context( generator_or_function: t.Iterator[t.AnyStr], ) -> t.Iterator…` · [src/flask/helpers.py:L50-L53][f1]

Keeps the current request context alive while a streamed response generator runs.

The first two definitions are typing overloads; the nested decorator and generator are the inner pieces of the implementation.
The argument is first passed to iter(). If that raises TypeError, the argument is treated as a generator function: a decorator wrapper is returned (with the original's metadata via update_wrapper) that calls the function with its arguments and passes the resulting generator back through stream_with_context. Otherwise an inner generator is created and started immediately with next(), which runs until its first dummy yield; it reads the request context var and raises RuntimeError right then if none is active. Inside, the context is entered with 'with ctx' and stays pushed while the real iterator is consumed via yield from; in a finally block gen.close() is called if present, so non-generator iterators get cleanup. The dummy value is discarded, and the started wrapped generator is returned. The request context is therefore pushed at call time but only popped when the stream ends, is closed or is garbage collected.

uses: [_cv_request](../../catalog.json)

<a id="u-7680aedfd1b1"></a>
### `templating.py-stream`

`def _stream( app: Flask, template: Template, context: dict[str, t.Any] ) -> t.Iterato…` · [src/flask/templating.py:L165-L173][f2]

Starts streaming a template, returning an iterator of string chunks.

The nested generate function does the iteration.
It updates the context and sends before_render_template immediately (when _stream is called, not on first iteration). The generator yields from template.generate and sends template_rendered only after the stream is fully consumed. If a request context is active (request is truthy), the iterator is wrapped with stream_with_context so the request context remains active while chunks are generated; stream_with_context requires an active context and starts the iterator's wrapper right away. Without a request, the plain generator is returned.

calls: [helpers.py-stream-with-context](template-rendering-and-loading.md#u-123009fa213a)

<a id="u-88c7e542733f"></a>
### `App.create_global_jinja_loader`

`def create_global_jinja_loader(self) -> DispatchingJinjaLoader:` · [src/flask/sansio/app.py:L523-L534][f3]

Returns a DispatchingJinjaLoader for this app, which dispatches template lookup between the application's and blueprints' loaders.

It is a thin factory so subclasses can replace only the loader.

<a id="u-86b8c98f3d78"></a>
### `DispatchingJinjaLoader`

`class DispatchingJinjaLoader(BaseLoader):` · [src/flask/templating.py:L52-L57][f2]

Jinja loader that searches the application's template loader and then every blueprint's loader, in that order, for a template.

<a id="u-4d36739b53d0"></a>
### `Environment`

`class Environment(BaseEnvironment):` · [src/flask/templating.py:L39-L45][f2]

Jinja Environment subclass that is bound to a Flask app, and by default takes its template loader from the app so blueprint templates are found.

<a id="u-ac93acab0ceb"></a>
### `_default_template_ctx_processor`

`def _default_template_ctx_processor() -> dict[str, t.Any]:` · [src/flask/templating.py:L24-L36][f2]

Default template context processor that exposes g, request and session to templates.

Reads the app and request context variables with a default of None. If an app context exists, 'g' is added; if a request context exists, 'request' and 'session' are added. Outside any context it returns an empty dict.

<a id="u-7946814d7c34"></a>
### `_render`

`def _render(app: Flask, template: Template, context: dict[str, t.Any]) -> str:` · [src/flask/templating.py:L126-L135][f2]

Renders a template with signals around it.

It calls app.update_template_context(context) (mutating the passed context to add processor values), sends before_render_template, renders the template, then sends template_rendered, and returns the string. Signal receivers are called through the app's ensure_sync wrapper. If rendering raises, template_rendered is not sent.

<a id="u-a5b7d66b7ea8"></a>
### `render_template`

`def render_template( template_name_or_list: str | Template | list[str | Template], **…` · [src/flask/templating.py:L138-L150][f2]

Renders a template selected by name, Template object or list of candidates using the current app.

The real app is obtained from the current_app proxy, and get_or_select_template picks the first existing template (TemplateNotFound or related errors propagate). Rendering goes through the shared render helper, which adds context processor values and sends signals.

<a id="u-f3ccecd24256"></a>
### `render_template_string`

`def render_template_string(source: str, **context: t.Any) -> str:` · [src/flask/templating.py:L153-L162][f2]

Renders a template from a source string with the current app's Jinja environment, through the shared render helper that adds context and sends signals.

<a id="u-c8e749b54f01"></a>
### `stream_template`

`def stream_template( template_name_or_list: str | Template | list[str | Template], **…` · [src/flask/templating.py:L188-L204][f2]

Streams a template selected by name, Template object, or list, returning an iterator of strings for use as a streaming response.

Resolves the template with get_or_select_template on the current app and delegates to _stream, which keeps the request context if one is active.

<a id="u-557a3a767477"></a>
### `stream_template_string`

`def stream_template_string(source: str, **context: t.Any) -> t.Iterator[str]:` · [src/flask/templating.py:L207-L219][f2]

Streams a template compiled from a source string with the current app's Jinja environment, returning an iterator of strings through the shared streaming helper.

<a id="u-ee0a5f9a99ff"></a>
### `DispatchingJinjaLoader.__init__`

`def __init__(self, app: App) -> None:` · [src/flask/templating.py:L57-L58][f2]

Stores the app whose application and blueprint loaders will be searched.

<a id="u-dd9ec306c4bf"></a>
### `DispatchingJinjaLoader._get_source_explained`

`def _get_source_explained( self, environment: BaseEnvironment, template: str ) -> tup…` · [src/flask/templating.py:L67-L89][f2]

Finds template source while recording every loader's outcome so the loading attempts can be reported.

It asks every loader in order (no early exit), recording (loader, source object, result or None on TemplateNotFound) for each. The first successful result is kept as the answer. It then lazily imports and calls explain_template_loading_attempts with the app, template and attempts, which reports on them (its output behavior is outside this file). If a result was found it is returned, else TemplateNotFound is raised after the report. Loader errors other than TemplateNotFound propagate before the report.

calls: [DispatchingJinjaLoader._iter_loaders](template-rendering-and-loading.md#u-eb5ed28e1cfb), [explain_template_loading_attempts](../../catalog.json)

<a id="u-e8e6fd78dfd8"></a>
### `DispatchingJinjaLoader._get_source_fast`

`def _get_source_fast( self, environment: BaseEnvironment, template: str ) -> tuple[st…` · [src/flask/templating.py:L91-L99][f2]

Finds template source by trying loaders in order and returning the first success.

TemplateNotFound from a loader moves on to the next; if all loaders fail, TemplateNotFound(template) is raised.

calls: [DispatchingJinjaLoader._iter_loaders](template-rendering-and-loading.md#u-eb5ed28e1cfb)

<a id="u-eb5ed28e1cfb"></a>
### `DispatchingJinjaLoader._iter_loaders`

`def _iter_loaders(self, template: str) -> t.Iterator[tuple[Scaffold, BaseLoader]]:` · [src/flask/templating.py:L101-L109][f2]

Yields (scaffold, loader) pairs: first the app with its jinja_loader, then each blueprint with its loader.

Any app or blueprint whose jinja_loader is None is skipped. Blueprints come from app.iter_blueprints(), so their order is determined by that method. The template argument is not used.

<a id="u-3d609283dfcb"></a>
### `DispatchingJinjaLoader.get_source`

`def get_source( self, environment: BaseEnvironment, template: str ) -> tuple[str, str…` · [src/flask/templating.py:L60-L65][f2]

Returns template source, choosing between a debug-explaining path and a fast path according to configuration.

If app.config['EXPLAIN_TEMPLATE_LOADING'] is truthy, uses the explained variant; otherwise the fast variant. Both raise TemplateNotFound if no loader has the template.

<a id="u-280e0620f523"></a>
### `DispatchingJinjaLoader.list_templates`

`def list_templates(self) -> list[str]:` · [src/flask/templating.py:L111-L123][f2]

Returns the union of template names from the app loader and all blueprint loaders as a list.

Names are collected in a set, so duplicates are removed and the returned order is arbitrary. App and blueprints without a jinja_loader are skipped.

<a id="u-fb32437d7c56"></a>
### `Environment.__init__`

`def __init__(self, app: App, **options: t.Any) -> None:` · [src/flask/templating.py:L45-L49][f2]

Initializes the Jinja environment with a loader from the app unless one is passed.

If 'loader' is not among the options, app.create_global_jinja_loader() is used. Options are passed to the base environment initializer and the app is stored as self.app (after the base init).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/helpers.py
[f2]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/templating.py
[f3]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/sansio/app.py
