# File Serving Helpers

**Capability.** send_file and send_from_directory delegate to Werkzeug after _prepare_send_file_kwargs merges Flask-specific values (environ, USE_X_SENDFILE, response class, root path, per-app max_age).

Use these to serve files with Flask defaults; both funnels pass through _prepare_send_file_kwargs, so behavior changes apply to both entry points.

**Depends on.**

- [Request and Response Wrappers](r2-request-response-objects.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Concrete Blueprint Runtime](r2-blueprint-runtime.md) · graph-confirmed · 1 edge(s) · Blueprint.send_static_file delegates static file delivery to send_from_directory.
- [URL Building, Redirects, and Resources](r1-url-building-resources.md) · graph-only · 1 edge(s)

Parent: [Shared Helpers](r2-helpers-utilities.md)

## Units (3)

<a id="u-93a20210ed51"></a>
### `send_file`

`def send_file( path_or_file: os.PathLike[t.AnyStr] | str | t.BinaryIO, mimetype: str …` · [src/flask/helpers.py:L400-L523][f1]

Sends a file path or binary file object to the client by delegating to werkzeug.utils.send_file with Flask defaults merged in via _prepare_send_file_kwargs (environ, USE_X_SENDFILE, response class, root path, and per-app max_age when none given).

Paths are trusted; user-supplied paths are unsafe and send_from_directory should be used instead. Conditional responses, etag computation, and mimetype inference from path are documented Werkzeug behaviors; text-mode file objects raise ValueError in Werkzeug.

calls: [_prepare_send_file_kwargs](r2-file-serving-helpers.md#u-6855621e8eaf)

**Uncertainties.**

- All validation and response construction is in werkzeug.utils.send_file, not supplied

<a id="u-b61c28e0e520"></a>
### `send_from_directory`

`def send_from_directory( directory: os.PathLike[str] | str, path: os.PathLike[str] | …` · [src/flask/helpers.py:L526-L567][f1]

Safely serves a file from a directory, forwarding to werkzeug.utils.send_from_directory with _prepare_send_file_kwargs supplying Flask-specific values.

The directory must not come from the client; Werkzeug's safe_join guards against path traversal, and a missing or non-regular file raises a 404 NotFound. All kwargs are passed through to send_file semantics.

calls: [_prepare_send_file_kwargs](r2-file-serving-helpers.md#u-6855621e8eaf)

**Uncertainties.**

- safe_join and 404 behavior are Werkzeug implementation details not shown here

<a id="u-6855621e8eaf"></a>
### `_prepare_send_file_kwargs`

`def _prepare_send_file_kwargs(**kwargs: t.Any) -> dict[str, t.Any]:` · [src/flask/helpers.py:L387-L397][f1]

Augments send-file keyword arguments with Flask-specific values before Werkzeug handles them.

If max_age is absent or None it is set to current_app.get_send_file_max_age (a callable, resolved per file later). Always adds request.environ, current_app.config['USE_X_SENDFILE'], current_app.response_class, and current_app.root_path. Requires active request and app contexts.

**Uncertainties.**

- Whether callers may pass their own environ/use_x_sendfile and how update ordering resolves conflicts: update() would overwrite caller-supplied values

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/helpers.py
