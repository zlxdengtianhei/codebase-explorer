# Request and Response Helpers

**Capability.** url_for forwarding to current_app.url_for, make_response and redirect for building responses, abort for HTTPExceptions, flash/get_flashed_messages over the session, and get_template_attribute for calling macros from Python.

These are the functions application code calls most. url_for is deliberately thin so apps can override URL building; flashed messages are cached per request to keep repeat calls consistent.

**Depends on.**

- [Application and Request Contexts](r2-app-context-and-globals.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [View and Async Dispatch Tests](r2-view-tests.md) · model-inferred · 0 edge(s)

Parent: [Shared Helpers](r2-helpers-utilities.md)

## Units (7)

<a id="u-221362c3f2fb"></a>
### `url_for`

`def url_for( endpoint: str, *, _anchor: str | None = None, _method: str | None = None…` · [src/flask/helpers.py:L188-L239][f1]

Thin wrapper generating a URL for an endpoint, forwarding endpoint plus _anchor, _method, _scheme, _external, and all keyword values to current_app.url_for, so apps can override URL building.

Endpoint names starting with '.' are resolved against the current blueprint by the app implementation. Requires an active request or app context; errors propagate from current_app.url_for.

**Uncertainties.**

- Actual endpoint resolution, external-URL defaults, and build-error handling live in Flask.url_for, not supplied

<a id="u-132e9804ecee"></a>
### `make_response`

`def make_response(*args: t.Any) -> Response:` · [src/flask/helpers.py:L139-L185][f1]

Builds a Response from view-return-style arguments so headers or status can be attached.

With no arguments it returns a fresh current_app.response_class(); with exactly one argument it unwraps it; otherwise it passes the argument tuple to current_app.make_response, letting the app apply its conversion rules (e.g. (body, 404)). Errors for invalid argument shapes come from the app's make_response.

uses: [globals.py module code (L1–L51)](r2-app-context-and-globals.md#u-6371f70e8a7d)

<a id="u-8a60c1d60c8b"></a>
### `redirect`

`def redirect( location: str, code: int = 302, Response: type[BaseResponse] | None = N…` · [src/flask/helpers.py:L242-L263][f1]

Creates a redirect response.

When the current_app proxy is truthy (an app context is active) it uses current_app.redirect with the given code, ignoring the Response parameter; otherwise it falls back to Werkzeug's redirect with the supplied Response class. Falls back outside an app context, unlike most helpers.

uses: [globals.py module code (L1–L51)](r2-app-context-and-globals.md#u-6371f70e8a7d)

**Uncertainties.**

- Truthiness of the LocalProxy outside app context (raising vs False) depends on Werkzeug proxy semantics; the code assumes a usable falsy value

<a id="u-3a4f71214dc8"></a>
### `abort`

`def abort(code: int | BaseResponse, *args: t.Any, **kwargs: t.Any) -> t.NoReturn:` · [src/flask/helpers.py:L266-L286][f1]

Raises an HTTPException for a status code or aborts with a Response.

With an active app it calls current_app.aborter(code, *args, **kwargs); outside an app context it calls Werkzeug's abort instead. Returns NoReturn in either path; the app aborter decides which exception is raised for the code.

**Uncertainties.**

- Whether current_app.aborter ever returns normally (which would still reach the Werkzeug call) is determined by aborter code not supplied

<a id="u-e1f4c98caba1"></a>
### `get_template_attribute`

`def get_template_attribute(template_name: str, attribute: str) -> t.Any:` · [src/flask/helpers.py:L289-L308][f1]

Loads a template by name from current_app.jinja_env and returns the named attribute of its rendered module, typically a macro, so macros can be invoked from Python.

Template-not-found and attribute errors propagate from Jinja/getattr.

**Uncertainties.**

- Whether attribute lookup on .module caches evaluated lazily is Jinja behavior not shown

<a id="u-880145f6d7d9"></a>
### `flash`

`def flash(message: str, category: str = "message") -> None:` · [src/flask/helpers.py:L311-L342][f1]

Stores a message with a category in the session's '_flashes' list for display on a later request via get_flashed_messages.

It deliberately rewrites the list (session.get, append, then session['_flashes'] = flashes) so session implementations backed by external storage see the change, rather than mutating a nested list in place. Then it sends the message_flashed signal with the real current app object, app.ensure_sync as async wrapper, message, and category. Requires an active request (session) and app context.

**Notes.**

- side_effect: Mutates session['_flashes'] and emits message_flashed each call.

<a id="u-993c1b0209f4"></a>
### `get_flashed_messages`

`def get_flashed_messages( with_categories: bool = False, category_filter: t.Iterable[…` · [src/flask/helpers.py:L345-L384][f1]

Consumes flashed messages from the session, caching them on request_ctx.flashes so repeat calls in the same request return the same data without popping again.

On first call, if the cache is None it pops '_flashes' from the session (empty list if absent) and stores it. category_filter, when non-empty, restricts the result to entries whose category is in the filter; with_categories=False returns only message strings, True returns (category, message) tuples.

**Notes.**

- side_effect: '_flashes' is removed from the session even if a category_filter hides some entries this call.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/helpers.py
