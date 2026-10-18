# Templating Test Suite

**Capability.** Pins Jinja integration: rendering context and streaming, autoescaping, app and blueprint template filters/tests/globals, custom environments and loaders, iterable template loading, loader-explain logging, and auto_reload resolution versus debug mode.

Read these to confirm how filters and tests register (decorator vs add_ methods), how TEMPLATES_AUTO_RELOAD interacts with debug, and what EXPLAIN_TEMPLATE_LOADING logs for blueprint template lookup.

**Depends on.**

- [Blueprint System](r2-blueprint-system.md) · model-inferred · 0 edge(s)

Parent: [Flask Framework](r2-flask-framework.md)

## Units (11)

<a id="u-24527f9376de"></a>
### `test-templating-context-and-rendering`

`def test_context_processing(app, client):` · [tests/test_templating.py:L11-L12][f1]

These tests cover rendering context and streaming.

test_context_processing injects injected_value=42 via app.context_processor and renders context_template.html with value=23, yielding '<p>23|42'. test_original_win shows that an explicit template variable (config=42) overrides the app's config global of the same name. test_simple_stream shows flask.stream_template_string producing the same body as render_template_string. test_request_less_rendering (using the app_ctx fixture, no request) shows render_template_string sees config (WORLD_NAME='Special World') and context-processor values (foo=42) outside a request. test_standard_context renders request.args.foo (42 from the query string), g.foo (23), config.DEBUG (False), and session.test ('aha') in one template.

imports: [test_templating.py module code (L1–L10)][f1]

**Uncertainties.**

- Whether session persistence between requests matters here is untested; each test issues one request

<a id="u-6ce83cb7ced9"></a>
### `test-templating-escaping`

`def test_escaping(app, client):` · [tests/test_templating.py:L71-L74][f1]

These tests cover autoescaping behavior.

test_escaping renders an HTML template with text='<p>Hello World!' both as a plain string and as Markup(text): the plain string is escaped in all six output lines where autoescaping applies (plain variants escaped, Markup variants raw) — the exact pattern depends on the template file, not supplied. test_no_escaping renders a .txt template (autoescape off) so plain strings pass through raw on most lines, with one escaped line indicating a conditional or explicit escape in the template. test_escaping_without_template_filename asserts render_template_string escapes '<test>' to '&lt;test&gt;' (string templates autoescape), while render_template('mail.txt', ...) does not (txt files don't autoescape). test_macros fetches the 'hello' macro from _macro.html via get_template_attribute and asserts its output.

imports: [test_templating.py module code (L1–L10)][f1]

**Uncertainties.**

- The template files' contents are not supplied, so which line of each expected list corresponds to which template construct cannot be determined

<a id="u-67f08d249127"></a>
### `test-templating-filters`

`def test_template_filter(app):` · [tests/test_templating.py:L123-L124][f1]

These tests register a reversing filter on the app via @app.template_filter() or app.add_template_filter(fn), with and without an explicit name ('strrev' or 'super_reverse').

The filter lands in app.jinja_env.filters under the explicit name when given, else the function name, and reverses strings. The *_with_template variants render template_filter.html through a client request ('abcd' -> 'dcba'), confirming the filter is active during rendering in both decorator and explicit-call registration forms.

<a id="u-39633285e859"></a>
### `test-templating-tests`

`def test_template_test(app):` · [tests/test_templating.py:L217-L218][f1]

These tests register a template test via @app.template_test() or app.add_template_test(fn), with and without the explicit name 'boolean' (function may be named boolean or is_boolean).

The test appears in app.jinja_env.tests under the given or function name and is isinstance(value, bool). The *_with_template variants render template_test.html with value=False through a client request and assert 'Success!' in the body, showing the test is active during rendering in all registration forms.

<a id="u-91a6864a03f4"></a>
### `test_add_template_global`

`def test_add_template_global(app, app_ctx):` · [tests/test_templating.py:L311-L312][f1]

Registers get_stuff via @app.template_global() and asserts it appears in app.jinja_env.globals and is callable, then renders '{{ get_stuff() }}' inside an app context expecting '42'.

One assertion is written as `assert app.jinja_env.globals["get_stuff"](), 42` — a tuple assertion that is always truthy, so it does not actually verify the return value; only the final render does.

**Notes.**

- contract: the tuple-form assert on line with globals["get_stuff"]\(), 42 never fails regardless of return value; the rendered-string check is the real value assertion

imports: [test_templating.py module code (L1–L10)][f1]

<a id="u-2dff69a444bb"></a>
### `test_custom_jinja_env`

`def test_custom_jinja_env():` · [tests/test_templating.py:L443-L444][f1]

Defines CustomEnvironment subclassing flask.templating.Environment and a CustomFlask whose jinja_environment attribute is that class.

Instantiating CustomFlask and reading app.jinja_env asserts it is an instance of CustomEnvironment, showing the Jinja environment class is selected via the jinja_environment class attribute.

imports: [test_templating.py module code (L1–L10)][f1]

<a id="u-edc5cd19d0dc"></a>
### `test_custom_template_loader`

`def test_custom_template_loader(client):` · [tests/test_templating.py:L324-L325][f1]

Subclasses flask.Flask overriding create_global_jinja_loader to return a DictLoader serving only 'index.html' with 'Hello Custom World!'.

A route renders index.html through the test client, and the custom loader's body is returned, showing the global Jinja loader is fully replaceable. The fixture 'client' argument is unused; a fresh MyFlask test client is created locally.

imports: [test_templating.py module code (L1–L10)][f1]

**Uncertainties.**

- Whether blueprint loaders still compose with this custom loader is not tested here

<a id="u-771ce00e5315"></a>
### `test_iterable_loader`

`def test_iterable_loader(app, client):` · [tests/test_templating.py:L342-L343][f1]

Passes a list of template names to render_template — 'no_template.xml' (missing, skipped), 'simple_template.html' (present, chosen), 'context_template.html' (present but never reached).

A context processor injects whiskey='Jameson'; the rendered output is '<h1>Jameson</h1>', showing render_template tries names in order, uses the first that loads, and applies context processors. The route also passes value=23, unused by the chosen template.

imports: [test_templating.py module code (L1–L10)][f1]

<a id="u-6611ed78a83a"></a>
### `test_template_loader_debugging`

`def test_template_loader_debugging(test_apps, monkeypatch):` · [tests/test_templating.py:L407-L412][f1]

Enables EXPLAIN_TEMPLATE_LOADING on the blueprintapp fixture app and attaches a logging.Handler subclass that asserts a single log record contains the numbered loader-attempt messages ('1: trying loader of application', blueprint loader attempts for admin and frontend, the not-found error, the note about looking up from a frontend-blueprint endpoint, and the docs URL).

Requesting /missing raises TemplateNotFound whose message names missing_template.html, and the handler fired exactly once, showing template-load debugging produces one explanatory log per failed lookup.

imports: [test_templating.py module code (L1–L10)][f1]

**Uncertainties.**

- The fixture app's blueprint/template layout (which would establish exact loader order) is not supplied

<a id="u-1a2578f12104"></a>
### `test_templates_auto_reload`

`def test_templates_auto_reload(app): # debug is False, config option is None` · [tests/test_templating.py:L362-L391][f1]

Exhaustively checks the jinja_env.auto_reload truth table across fresh Flask instances: with debug False, auto_reload is False when TEMPLATES_AUTO_RELOAD is None or False and True when True; with debug True, auto_reload is True when TEMPLATES_AUTO_RELOAD is None or True and False when the config option is explicitly False — i.e. the config option overrides debug, and debug is the default when the option is None.

imports: [test_templating.py module code (L1–L10)][f1]

**Uncertainties.**

- Whether auto_reload is derived at jinja_env creation or lazily is not visible; each assertion reads a fresh app's jinja_env

<a id="u-7ce0aaf1a786"></a>
### `test_templates_auto_reload_debug_run`

`def test_templates_auto_reload_debug_run(app, monkeypatch):` · [tests/test_templating.py:L394-L395][f1]

Monkeypatches werkzeug.serving.run_simple to a no-op so app.run() starts no server, then asserts jinja_env.auto_reload is falsy after app.run() and truthy after app.run(debug=True), confirming debug mode at run time enables template auto-reload.

contract: [test_templates_auto_reload](r2-templating-tests.md#u-1a2578f12104)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/tests/test_templating.py
