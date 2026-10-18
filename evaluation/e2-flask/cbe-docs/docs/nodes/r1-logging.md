# Application Logging

**Capability.** Per-app logger creation: create_logger attaches a handler only when none in the chain would process the effective level (has_level_handler), and wsgi_errors_stream routes output to the active request's error stream or stderr. App.logger caches the result.

Use this subtree to explain why Flask apps log to werkzeug/dev servers without duplicating handlers, and where error output goes inside versus outside a request.

**Depended on by.**

- [Sans-I/O Application Core](r1-core-app-model.md) · model-inferred · 0 edge(s) · App.logger obtains its logger through flask.logging.create_logger.
- [Exception and Error Handling](r1-error-handling.md) · model-inferred · 0 edge(s)
- [Flask Framework](r1-flask-framework.md) · within containment · 1 edge(s)

Parent: [Flask Framework](r1-flask-framework.md)

## Units (4)

<a id="u-185f96e08a34"></a>
### `create_logger`

`def create_logger(app: App) -> logging.Logger:` · [src/flask/logging.py:L58-L79][f1]

Returns the app's standard logger, named after app.name, configuring it only when needed.

In debug mode, if the logger has no explicit level it is set to logging.DEBUG. If has_level_handler finds no handler that would accept the logger's effective level, the shared default_handler (a StreamHandler over wsgi_errors_stream with the '[time] LEVEL in module: message' format) is added. The logger is then returned unchanged otherwise.

calls: [has_level_handler](r1-logging.md#u-8f0ca5344429)

<a id="u-8f0ca5344429"></a>
### `has_level_handler`

`def has_level_handler(logger: logging.Logger) -> bool:` · [src/flask/logging.py:L31-L47][f1]

Determines whether any handler in the logger chain would process records at the logger's effective level.

Starting at the given logger, it checks each logger's handlers for level <= the effective level, returning True on the first match; it stops at a logger with propagate False and returns False if nothing matched.

<a id="u-0c8797993dbe"></a>
### `wsgi_errors_stream`

`def wsgi_errors_stream() -> t.TextIO:` · [src/flask/logging.py:L15-L28][f1]

LocalProxy-resolved function returning the active request's 'wsgi.errors' stream when a request context is active, otherwise sys.stderr, so logging goes to the appropriate sink per context.

<a id="u-d4733f4c489d"></a>
### `logging.py module code (L1–L14)`

`module_region` · [src/flask/logging.py:L1-L14][f1]

Logging-module imports and TYPE_CHECKING-only App import; non-behavioral material already located by the inventory.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/logging.py
