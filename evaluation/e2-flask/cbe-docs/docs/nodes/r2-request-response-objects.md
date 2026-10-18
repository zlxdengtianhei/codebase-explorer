# Request and Response Wrappers

**Capability.** Owns Flask's Request and Response classes: routing metadata on the request (endpoint, blueprint chain, url_rule), per-request and config-derived limits (max_content_length, max_form_memory_size, max_form_parts, max_cookie_size), and JSON failure handling.

Use this to understand what extra state Flask attaches to Werkzeug's request/response and how limits resolve per-request versus from app config. Request.blueprints uses helpers._split_blueprint_path for the parent chain.

**Depends on.**

- [Shared Helpers](r2-helpers-utilities.md) · graph-confirmed · 1 edge(s) · Request.blueprints uses helpers._split_blueprint_path to expand the blueprint parent chain.
- [Diagnostics and Debug Errors](r1-debug-helpers.md) · graph-only · 1 edge(s)
- [Environment and Path Helpers](r2-environment-helpers.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Blueprint Registration](r2-blueprint-registration.md) · model-inferred · 0 edge(s)
- [File Serving Helpers](r2-file-serving-helpers.md) · model-inferred · 0 edge(s)
- [Logging Test Suite](r2-logging-tests.md) · model-inferred · 0 edge(s)

Parent: [Flask Framework](r2-flask-framework.md)

## Units (14)

<a id="u-000b3c1e5029"></a>
### `Request`

`class Request(RequestBase):` · [src/flask/wrappers.py:L18-L59][f1]

Flask's default request class, a Werkzeug RequestBase subclass that remembers the matched URL rule, view args, and routing exception as instance attributes (all defaulting to None).

Overrides body-size limit properties to prefer per-request values over app config, exposes endpoint/blueprint metadata derived from url_rule, adjusts form-data loading in debug mode, and converts JSON decode failures to a debug-aware BadRequest. json_module is bound to flask's json module for JSON support.

group: [Request.max_content_length](r2-request-response-objects.md#u-9f037a89f7f7), [Request.max_form_memory_size](r2-request-response-objects.md#u-5588aa8fc2b0), [Request.max_form_parts](r2-request-response-objects.md#u-e74cbc1275b7), [Request.endpoint](r2-request-response-objects.md#u-b771240fce69), [Request.blueprint](r2-request-response-objects.md#u-6ce5803abadf), [Request.blueprints](r2-request-response-objects.md#u-c935945f2966), [Request._load_form_data](r2-request-response-objects.md#u-d5c5bdfdf91e), [Request.on_json_loading_failed](r2-request-response-objects.md#u-9e4702950ec1)

**Uncertainties.**

- Werkzeug RequestBase parsing behavior (form, files, json) is inherited and not shown

<a id="u-a9d0483c8ba1"></a>
### `Response`

`class Response(ResponseBase):` · [src/flask/wrappers.py:L222-L246][f1]

Flask's default response class, a Werkzeug ResponseBase subclass with HTML default mimetype ('text/html'), JSON support via the flask json module (json_module attribute), and autocorrect_location_header disabled so redirect Location headers are not rewritten to absolute URLs.

Provides max_cookie_size as a config-backed read-only view.

group: [Response.max_cookie_size](r2-request-response-objects.md#u-351422557d75)

<a id="u-d5c5bdfdf91e"></a>
### `Request._load_form_data`

`def _load_form_data(self) -> None:` · [src/flask/wrappers.py:L197-L210][f1]

Loads form data via the Werkzeug superclass, then in debug mode attaches an error-reporting multidict: only when an app is active, current_app.debug is true, the mimetype is NOT multipart/form-data, and self.files is empty.

In that case it lazily imports attach_enctype_error_multidict and applies it to this request, so a missing enctype produces a clearer error on file access.

calls: [attach_enctype_error_multidict](r1-debug-helpers.md#u-40a0a4a04dae)

**Uncertainties.**

- The replacement multidict's exact error behavior is defined in debughelpers.py, not supplied

<a id="u-6ce5803abadf"></a>
### `Request.blueprint`

`def blueprint(self) -> str | None:` · [src/flask/wrappers.py:L161-L178][f1]

Returns the registered blueprint name derived from the endpoint by splitting on the last '.': rpartition('.')[0] when the endpoint contains a dot, else None (endpoint None or non-blueprint).

This is the registered name, which may differ from the creation name for nested or renamed blueprints.

<a id="u-c935945f2966"></a>
### `Request.blueprints`

`def blueprints(self) -> list[str]:` · [src/flask/wrappers.py:L180-L195][f1]

Returns the chain of blueprint names for the current request, outermost parents included.

Empty list when blueprint is None (no blueprint, failed or missing matching); otherwise delegates to _split_blueprint_path on the blueprint name.

calls: [_split_blueprint_path](r2-environment-helpers.md#u-03dadcbb1883)

<a id="u-b771240fce69"></a>
### `Request.endpoint`

`def endpoint(self) -> str | None:` · [src/flask/wrappers.py:L146-L159][f1]

Returns the endpoint string from the matched url_rule, or None if no rule matched or matching has not happened.

Combined with view_args it allows reconstructing the URL.

<a id="u-9f037a89f7f7"></a>
### `Request.max_content_length`

`def max_content_length(self) -> int | None:` · [src/flask/wrappers.py:L59-L86][f1]

Property returning the max bytes readable for this request.

If a per-request _max_content_length was set via the setter, it wins. Otherwise, when no app context is active it falls back to Werkzeug's base property; with an app it returns current_app.config['MAX_CONTENT_LENGTH']. Exceeding the limit produces a 413 at the parsing layer (per docstring). The setter (second id) just stores the value on the instance.

**Uncertainties.**

- The 413 raise itself is Werkzeug parsing behavior not visible here

<a id="u-e0199e3d41f4"></a>
### `src/flask/wrappers.py:Request.max_content_length`

`def max_content_length(self, value: int | None) -> None:` · [src/flask/wrappers.py:L88-L90][f1]

Setter storing the per-request max content length on the instance.

<a id="u-5588aa8fc2b0"></a>
### `Request.max_form_memory_size`

`def max_form_memory_size(self) -> int | None:` · [src/flask/wrappers.py:L92-L113][f1]

Property for the max non-file form field size in multipart bodies: per-request _max_form_memory_size if set, else the base property when no app is active, else current_app.config['MAX_FORM_MEMORY_SIZE'] (docstring default 500_000).

Exceeding yields 413 per docstring. The setter stores the per-request value.

**Uncertainties.**

- Enforcement of the limit happens in Werkzeug parsing not shown

<a id="u-f734cee58127"></a>
### `src/flask/wrappers.py:Request.max_form_memory_size`

`def max_form_memory_size(self, value: int | None) -> None:` · [src/flask/wrappers.py:L115-L117][f1]

Setter storing the per-request max form memory size on the instance.

<a id="u-e74cbc1275b7"></a>
### `Request.max_form_parts`

`def max_form_parts(self) -> int | None:` · [src/flask/wrappers.py:L119-L140][f1]

Property for the max number of multipart form fields: per-request _max_form_parts if set, else the base property outside an app context, else current_app.config['MAX_FORM_PARTS'] (docstring default 1_000).

Setter stores the per-request value. Docstring notes 413 on exceeding the limit.

**Uncertainties.**

- Enforcement is in Werkzeug multipart parsing, not shown

<a id="u-4a56e491a11d"></a>
### `src/flask/wrappers.py:Request.max_form_parts`

`def max_form_parts(self, value: int | None) -> None:` · [src/flask/wrappers.py:L142-L144][f1]

Setter storing the per-request max form parts on the instance.

<a id="u-9e4702950ec1"></a>
### `Request.on_json_loading_failed`

`def on_json_loading_failed(self, e: ValueError | None) -> t.Any:` · [src/flask/wrappers.py:L212-L219][f1]

Handles JSON parsing failure by first delegating to the superclass handler.

If that raises BadRequest: in debug mode with an active app it re-raises the original error for diagnosis; otherwise it raises a fresh, generic BadRequest with the original attached as __cause__. If the superclass does not raise, its return value is returned.

**Uncertainties.**

- What the superclass handler returns/does when it does not raise is Werkzeug behavior not shown

<a id="u-351422557d75"></a>
### `Response.max_cookie_size`

`def max_cookie_size(self) -> int: # type: ignore` · [src/flask/wrappers.py:L246-L257][f1]

Read-only property returning current_app.config['MAX_COOKIE_SIZE'] when an app context is active, otherwise Werkzeug's base default.

Used to determine the size limit when setting cookies.

**Uncertainties.**

- Base fallback value is Werkzeug's, not shown

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/wrappers.py
