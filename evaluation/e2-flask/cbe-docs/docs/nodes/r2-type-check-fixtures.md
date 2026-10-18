# Type-Checking Fixtures

**Capability.** Static typing fixtures exercised by type checkers rather than at runtime: every documented view return type, a TypedDict JSON payload, a templated View subclass, and sync/async request-hook registrations.

Read these as executable documentation of accepted signatures. typing_route covers each return type via single-return views; typing_app_decorators covers hook decorator typing.

Parent: [Flask Framework](r2-flask-framework.md)

## Units (4)

<a id="u-7775d9463af3"></a>
### `typing_app_decorators-before-and-after-request-and-teardown-hooks`

`def after_sync(response: Response) -> Response:` · [tests/type_check/typing_app_decorators.py:L9-L11][f1]

Type-checking fixtures registering Flask request hooks on a module-level app, covering sync and async variants.

Each decorated function is a one-line stub: after_request hooks (after_sync, after_async) take a Response and return a fresh Response; before_request hooks (before_sync, before_async) take no arguments and return None; teardown_appcontext hooks (teardown_sync, teardown_async) accept a BaseException | None and return None. No bodies perform work; the files exist so type checkers validate the decorators' accepted signatures.

**Uncertainties.**

- Whether Flask accepts async before_request/teardown handlers at runtime is not determinable from this file; only the annotations are exercised.

<a id="u-2c0b24b34cc7"></a>
### `typing_route-return-type-signatures`

`def hello_str() -> str:` · [tests/type_check/typing_route.py:L16-L18][f2]

Type-checking fixtures exercising every documented Flask view return type via app.route, each a single return statement.

Scalar returns: str (hello_str, async_route), bytes (hello_bytes). JSON returns: a Response from jsonify (hello_json), dict[str, Any] and list[Any] mapped directly (hello_json_dict, hello_json_list on the same /json/dict path), and a TypedDict StatusJSON {status: str} (typed_dict). Streaming returns: a nested generator show yielding "data:{x}\n\n" for x in range(100) (hello_generator), a generator expression of encoded bytes (hello_generator_expression), and iter over a built list (hello_iterator). Tuple returns: (str, int) with a default code of 200 and an optional <int:code> converter (tuple_status), HTTPStatus.OK accepted where int is annotated (tuple_status_enum), and (str, headers-dict) (tuple_headers). Template returns: render_template with an optional name parameter (return_template, dual route) and stream_template returning an iterator (return_template_stream). These verify annotations only; bodies contain no branching.

uses: [StatusJSON](r2-type-check-fixtures.md#u-298a31640904)

**Uncertainties.**

- Whether Flask's runtime response conversion accepts every annotated form (e.g. HTTPStatus in tuple position) is not proven by this file; it is a typing fixture.

<a id="u-298a31640904"></a>
### `StatusJSON`

`class StatusJSON(t.TypedDict):` · [tests/type_check/typing_route.py:L41-L42][f2]

A TypedDict describing a JSON payload with a single required string field, status.

Used as the return annotation of the typed_dict view to verify Flask's typing accepts TypedDict return types.

<a id="u-018aeb66b7ae"></a>
### `RenderTemplateView`

`class RenderTemplateView(View):` · [tests/type_check/typing_route.py:L101-L102][f2]

A View subclass rendered into a URL rule that templates a page from a configurable template name.

__init__ stores the template_name string on the instance; dispatch_request renders that template via render_template and returns the resulting string. The class-level app.add_url_rule call at module scope registers it at /about using RenderTemplateView.as_view("about_page", template_name="about.html"), passing the template name through the class-based-view construction path.

calls: [RenderTemplateView](r2-type-check-fixtures.md#u-018aeb66b7ae)

**Uncertainties.**

- Whether as_view forwards template_name to __init__ exactly as written is a Flask runtime behavior not verifiable in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/tests/type_check/typing_app_decorators.py
[f2]: ../../../../../../eval/flask-85c5d93/tests/type_check/typing_route.py
