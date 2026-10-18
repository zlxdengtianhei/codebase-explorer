# Diagnostics and Debug Errors

**Capability.** Developer-experience aids: FormDataRoutingRedirect and DebugFilesKeyError turn common form/routing mistakes into clear assertions, attach_enctype_error_multidict patches file lookups with better errors, and explain_template_loading_attempts/_dump_loader_info report every template lookup attempt.

Use this subtree when interpreting Flask's debug-mode assertions and template-loading diagnostics. These are consumed by the dispatch pipeline (routing redirect case) and the template loader (explained lookups).

**Depended on by.**

- [Request Dispatch Pipeline](r1-request-dispatch.md) · graph-confirmed · 1 edge(s) · raise_routing_exception raises FormDataRoutingRedirect to give clear assertions for form-routing mistakes.
- [Template Rendering](r1-templating.md) · graph-confirmed · 1 edge(s) · The loader's explained-failure path calls explain_template_loading_attempts for template-loading diagnostics.
- [Request and Response Wrappers](r2-request-response-objects.md) · graph-only · 1 edge(s)

Parent: [Flask Framework](r1-flask-framework.md)

## Units (5)

<a id="u-8135e71c270a"></a>
### `FormDataRoutingRedirect`

`class FormDataRoutingRedirect(AssertionError):` · [src/flask/debughelpers.py:L50-L57][f1]

An AssertionError raised in debug mode when a routing redirect would make a browser drop form data.

__init__ asserts the request's routing_exception is a RequestRedirect (any other type fails the assertion), then builds a message naming the original URL and the canonical redirect target. If the redirect target (before the query string) equals the base URL plus a trailing slash, it adds an explanation about trailing-slash redirects; it always appends the advice to use 307/308 and a note that this is only raised in debug mode.

<a id="u-03735ad1c03b"></a>
### `DebugFilesKeyError`

`class DebugFilesKeyError(KeyError, AssertionError):` · [src/flask/debughelpers.py:L23-L28][f1]

A KeyError/AssertionError hybrid raised when request.files[key] misses because the form lacked multipart encoding.

__init__ reads request.form.getlist(key) to see what the browser actually submitted, builds a message naming the requested key, the request mimetype, and the fix (enctype="multipart/form-data"). If any form entries matched the key, it appends the submitted file names. __str__ returns the stored message; the message is built eagerly at construction time.

<a id="u-40a0a4a04dae"></a>
### `attach_enctype_error_multidict`

`def attach_enctype_error_multidict(request: Request) -> None:` · [src/flask/debughelpers.py:L81-L90][f1]

Patches a request's files multidict so failed lookups give a descriptive error.

It subclasses the current class of request.files as newcls whose __getitem__ first delegates to super().__getitem__; on KeyError it re-raises only if the key is absent from request.form, otherwise it raises DebugFilesKeyError with the original traceback chained (raise ... from None suppresses the implicit context). newcls copies the original class's __name__ and __module__, then request.files.__class__ is reassigned so existing instances use the patched class.

raises: [DebugFilesKeyError](r1-debug-helpers.md#u-03735ad1c03b)

**Uncertainties.**

- The per-request form lookup in __getitem__ may itself trigger form parsing whose failures are not handled here.

<a id="u-6856219e158f"></a>
### `explain_template_loading_attempts`

`def explain_template_loading_attempts( app: App, template: str, attempts: list[ tuple…` · [src/flask/debughelpers.py:L124-L178][f1]

Logs a human-readable report of every template-lookup attempt.

It records the request's blueprint (from request_ctx, if present) and, for each (loader, srcobj, triple) attempt, describes the source object as an application, a blueprint, or repr fallback, dumps loader details via _dump_loader_info, and marks each attempt as 'no match' or 'found (filename)'. Afterwards: total_found == 0 produces 'Error: the template could not be found.'; more than one match produces a multiple-match warning; either sets seems_fishy, and when a blueprint was active it adds hints about template placement and a documentation link. The joined report goes to app.logger.info.

calls: [_dump_loader_info](r1-debug-helpers.md#u-04e4b0740e24)

**Uncertainties.**

- request_ctx truthiness behavior outside an active context relies on the globals sentinel, not shown here.

<a id="u-04e4b0740e24"></a>
### `_dump_loader_info`

`def _dump_loader_info(loader: BaseLoader) -> t.Iterator[str]:` · [src/flask/debughelpers.py:L107-L121][f1]

Yields diagnostic lines describing a Jinja loader.

First line is the loader's qualified class name. It then iterates loader.__dict__ sorted by key, skipping underscore-prefixed attributes, tuple/list values containing non-strings, and values that are not str, int, float, or bool. Sequence values are emitted one item per '  - ' line; scalars are emitted as 'key: value!r'.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/debughelpers.py
