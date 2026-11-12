# Application Logging Setup

**Capability.** Creates and configures the application's logger and default handler, writing to the WSGI error stream with a standard format.

Go here to see how the app logger is created and when a handler is attached. It contains the default handler, the lazy error stream proxy and the logger property.

Parent: [Sansio App Base and Logging](sansio-app-base-and-logging.md)

## Units (5)

<a id="u-185f96e08a34"></a>
### `create_logger`

`def create_logger(app: App) -> logging.Logger:` · [src/flask/logging.py:L58-L79][f1]

Returns the application's logger, configuring level and handler when needed.

The logger is named after app.name. If app.debug is true and the logger has no level of its own (level 0), the level is set to DEBUG. If no handler along its chain handles its effective level (per has_level_handler), the shared default handler is added. The same logger object is returned for repeated calls (standard logging registry), though the handler is added only when none exists, so repeated calls do not duplicate it.

calls: [has_level_handler](application-logging-setup.md#u-8f0ca5344429)

<a id="u-8f0ca5344429"></a>
### `has_level_handler`

`def has_level_handler(logger: logging.Logger) -> bool:` · [src/flask/logging.py:L31-L47][f1]

Reports whether any handler along a logger's propagation chain would handle the logger's effective level.

Walks from the logger up through parents; returns True at the first logger having a handler whose level is less than or equal to the effective level. It stops walking at a logger with propagate false (after checking its own handlers) and returns False if none matched, including when there are no handlers at all.

<a id="u-0c8797993dbe"></a>
### `wsgi_errors_stream`

`def wsgi_errors_stream() -> t.TextIO:` · [src/flask/logging.py:L15-L28][f1]

Lazy proxy for the error stream used by the default log handler.

When evaluated, it returns request.environ['wsgi.errors'] if a request context is active, otherwise sys.stderr. It is a LocalProxy, so the choice is made on each access rather than at import. A missing 'wsgi.errors' key would raise KeyError.

<a id="u-b3f3650edf6e"></a>
### `logging.py module code (L47–L57)`

`module_region` · [src/flask/logging.py:L47-L57][f1]

Module-level default logging handler writing to the lazy wsgi_errors_stream with the format '[time] LEVEL in module: message'.

It is attached to app loggers by create_logger when needed.

<a id="u-c935356c3924"></a>
### `App.logger`

`def logger(self) -> logging.Logger:` · [src/flask/sansio/app.py:L442-L467][f2]

Cached property returning the application's logging.Logger by delegating entirely to create_logger(self).

The first access creates and caches the logger; configuration such as level and default handler is done inside that helper, not here.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/logging.py
[f2]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/sansio/app.py
