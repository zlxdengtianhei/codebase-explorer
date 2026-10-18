# URL Building, Redirects, and Resources

**Capability.** Outbound URL construction and resource access: url_for builds URLs through a Werkzeug MapAdapter with injected defaults and a rescue hook for build errors, the app's redirect preserves subclassed response classes, and open_resource/open_instance_resource plus send_static_file serve package, instance, and static files with config-driven cache lifetimes.

Use this subtree whenever code needs a URL for an endpoint or a file from the app's folders. url_for delegates default injection and build-error rescue to hooks an app can extend; static serving derives max-age from SEND_FILE_MAX_AGE_DEFAULT.

**Depends on.**

- [Sans-I/O Application Core](r1-core-app-model.md) · model-inferred · 0 edge(s) · url_for calls the app's inject_url_defaults and handle_url_build_error hooks defined in the core model.
- [Environment and Path Helpers](r2-environment-helpers.md) · graph-only · 1 edge(s)
- [File Serving Helpers](r2-file-serving-helpers.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Application and Request Contexts](r2-app-context-and-globals.md) · graph-only · 2 edge(s)
- [Sans-I/O Application Core](r1-core-app-model.md) · graph-only · 1 edge(s)

Parent: [Concrete WSGI Application](r1-concrete-app.md)

## Units (10)

<a id="u-f591687825aa"></a>
### `Flask.url_for`

`def url_for( self, /, endpoint: str, *, _anchor: str | None = None, _method: str | No…` · [src/flask/app.py:L1003-L1127][f1]

Build a URL for an endpoint.

Adapter and externality depend on context: inside a request context, use the request context's url_adapter and the request's blueprint — an endpoint starting with '.' is prefixed with the current blueprint name (or has the dot stripped when no blueprint is active) — and _external defaults to (_scheme is not None). Outside a request, use the app context's url_adapter when present, else create one via create_url_adapter(None); if still None raise RuntimeError explaining that SERVER_NAME (plus APPLICATION_ROOT/PREFERRED_URL_SCHEME) is needed, and _external defaults to True. Passing _scheme with a falsey _external raises ValueError ('When specifying _scheme, _external must be True.') to avoid insecure URLs. Then inject_url_defaults mutates values, and url_adapter.build(...) generates the URL with method/_scheme/force_external. On BuildError, values is augmented with the _-prefixed options and handle_url_build_error(error, endpoint, values) is returned, which may return a replacement string or raise. A given _anchor is URL-quoted with a permissive safe set and appended as #anchor.

**Notes.**

- failure: Unknown endpoints or bad values become BuildError inside build and are routed to handle_url_build_error; outside any context without SERVER_NAME, a RuntimeError is raised instead.

calls: [App.inject_url_defaults](r1-url-building-resources.md#u-8bdea1636623), [App.handle_url_build_error](r1-url-building-resources.md#u-42ba1794dea3)

<a id="u-6afa91f86588"></a>
### `Flask.create_url_adapter`

`def create_url_adapter(self, request: Request | None) -> MapAdapter | None:` · [src/flask/app.py:L425-L476][f1]

Create the Werkzeug MapAdapter, with the request passed explicitly since no request context exists yet.

With a request: assign config TRUSTED_HOSTS to request.trusted_hosts, recompute request.host via get_host (raising on untrusted hosts), then bind to the environment. server_name passed to bind is None when url_map.host_matching is set (so the real host is honored); otherwise, when subdomain_matching is false, the current subdomain is forced to default_subdomain or the empty string to disable subdomain matching. Without a request, return url_map.bind(SERVER_NAME, script_name=APPLICATION_ROOT, url_scheme=PREFERRED_URL_SCHEME) only if SERVER_NAME is configured; otherwise None.

**Notes.**

- failure: A request whose host is not in TRUSTED_HOSTS fails in get_host before binding.

uses: [AppContext](r2-app-context-and-globals.md#u-9b040980ce77), [RequestContext](r2-app-context-and-globals.md#u-29aec47ecf61)

**Uncertainties.**

- Exact failure type raised by get_host for untrusted hosts is defined in Werkzeug, not here.

<a id="u-8bdea1636623"></a>
### `App.inject_url_defaults`

`def inject_url_defaults(self, endpoint: str, values: dict[str, t.Any]) -> None:` · [src/flask/sansio/app.py:L911-L930][f2]

Fills URL defaults into the values dict before endpoint building.

It starts with the app-level functions (None key in url_default_functions) and, when the endpoint is dotted (so url_for may be running outside a request context), chains in reversed results of _split_blueprint_path on the endpoint's parent path, covering each ancestor blueprint. Functions are called as func(endpoint, values) and mutate values in place.

calls: [_split_blueprint_path](r2-environment-helpers.md#u-03dadcbb1883)

<a id="u-42ba1794dea3"></a>
### `App.handle_url_build_error`

`def handle_url_build_error( self, error: BuildError, endpoint: str, values: dict[str,…` · [src/flask/sansio/app.py:L932-L964][f2]

Rescues a BuildError from url_for by offering it to each registered handler in url_build_error_handlers with (error, endpoint, values).

If a handler returns a non-None value, that value is returned and url_for uses it. A handler that raises BuildError is skipped and the raised error replaces the active one for later re-raising; a handler returning None is also skipped. If no handler produced a value, the method re-raises: bare 'raise' when the error is the currently active exception, otherwise 'raise error' to raise the passed (possibly handler-raised) error.

**Uncertainties.**

- Which handlers are registered is determined by application code; the callable signature is enforced only by the list's type annotation.

<a id="u-b737095e43e9"></a>
### `App.redirect`

`def redirect(self, location: str, code: int = 302) -> BaseResponse:` · [src/flask/sansio/app.py:L893-L909][f2]

Creates a redirect response by delegating to werkzeug's redirect with this app's response_class, so subclassed response types are preserved.

location is the target URL and code the status (default 302); flask.redirect calls this method.

uses: [App](r1-core-app-model.md#u-c945a7570d6a)

<a id="u-37e02c065230"></a>
### `App.make_aborter`

`def make_aborter(self) -> Aborter:` · [src/flask/sansio/app.py:L498-L508][f2]

Creates the object assigned to app.aborter, which flask.abort and direct callers invoke to raise HTTP errors.

Returns a new instance of aborter_class (default werkzeug Aborter); subclassing aborter_class changes what abort raises.

<a id="u-9555b369e50a"></a>
### `Flask.send_static_file`

`def send_static_file(self, filename: str) -> Response:` · [src/flask/app.py:L308-L328][f1]

View serving a file from the static folder.

Raises RuntimeError if has_static_folder is false. Otherwise computes max_age via self.get_send_file_max_age(filename) and delegates to send_from_directory(static_folder, filename, max_age=max_age), whose Response is returned; missing files or traversal attempts are handled by send_from_directory.

calls: [Flask.get_send_file_max_age](r1-url-building-resources.md#u-d3b42db1aa98), [send_from_directory](r2-file-serving-helpers.md#u-b61c28e0e520)

<a id="u-d3b42db1aa98"></a>
### `Flask.get_send_file_max_age`

`def get_send_file_max_age(self, filename: str | None) -> int | None:` · [src/flask/app.py:L281-L306][f1]

Return the cache max-age for a file path based on current_app.config['SEND_FILE_MAX_AGE_DEFAULT'].

None yields None (conditional requests instead of a timed cache); a timedelta is converted to int(total_seconds()); any other configured value is returned as-is. The filename parameter is unused.

**Notes.**

- contract: Reads config from current_app, not self, so the active app's configuration governs even on Blueprint-owned calls.

<a id="u-3cc6315b84aa"></a>
### `Flask.open_resource`

`def open_resource( self, resource: str, mode: str = "rb", encoding: str | None = None…` · [src/flask/app.py:L330-L361][f1]

Open a file relative to root_path for reading only.

Raises ValueError for any mode other than 'r', 'rt', or 'rb'. Binary mode opens without an encoding; text modes pass the encoding parameter (default None) to open. Propagates OS errors from open uncaught.

**Notes.**

- failure: Write modes are rejected with ValueError before touching the filesystem.

<a id="u-c85fda0d4f0c"></a>
### `Flask.open_instance_resource`

`def open_instance_resource( self, resource: str, mode: str = "rb", encoding: str | No…` · [src/flask/app.py:L363-L383][f1]

Open a file relative to instance_path; unlike open_resource, writing is allowed.

If 'b' is in the mode, open without encoding; otherwise open in text mode with the given encoding (default 'utf-8'). No mode validation and no error handling; OS errors propagate.

uses: [Flask.open_resource](r1-url-building-resources.md#u-3cc6315b84aa)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/app.py
[f2]: ../../../../../../eval/flask-85c5d93/src/flask/sansio/app.py
