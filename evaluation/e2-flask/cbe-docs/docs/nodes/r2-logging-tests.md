# Logging Test Suite

**Capability.** Pins Flask's logger behavior: default handler and naming, debug-level effects, existing-handler suppression, has_level_handler propagation rules, and routing of view exceptions and log errors to wsgi errors_stream.

Read alongside the reset_logging autouse fixture, which isolates root and flask_test logger state per test. Error output reaches the stream passed as errors_stream to the test client.

**Depends on.**

- [Request and Response Wrappers](r2-request-response-objects.md) · model-inferred · 0 edge(s)
- [Scaffold Registration Base](r1-scaffold-shared-base.md) · graph-only · 2 edge(s)
- [App and Request Contexts](r1-contexts-teardown.md) · graph-only · 1 edge(s)

Parent: [Flask Framework](r2-flask-framework.md)

## Units (8)

<a id="u-01322c27912b"></a>
### `test_logging.py module code (L1–L11)`

`module_region` · [tests/test_logging.py:L1-L11][f1]

Imports logging, sys, StringIO, pytest, and Flask logging helpers default_handler, has_level_handler, and wsgi_errors_stream used by the tests.

<a id="u-697d538cfbd3"></a>
### `reset_logging`

`def reset_logging(pytestconfig):` · [tests/test_logging.py:L12-L33][f1]

Autouse fixture isolating logging state for each test: it saves root handlers and level, clears root handlers, resets the flask_test logger's handlers and sets it to NOTSET, and unregisters pytest's logging plugin.

After the test (yield) it restores root handlers and level, re-clears the flask_test logger, and re-registers the plugin if it had been unregistered.

**Notes.**

- side_effect: Mutates global logging.root and the flask_test logger; restoration happens on teardown
- condition: Plugin re-registration only occurs if unregister returned a truthy plugin

<a id="u-22a4c521cea6"></a>
### `test_existing_handler`

`def test_existing_handler(app):` · [tests/test_logging.py:L48-L51][f1]

Adding a StreamHandler to the root logger means Flask's logger adds no handlers of its own: app.logger.handlers is empty and level stays NOTSET, because an effective handler already exists.

<a id="u-cca7de57b0c3"></a>
### `test_has_level_handler`

`def test_has_level_handler():` · [tests/test_logging.py:L70-L83][f1]

Checks has_level_handler for logger 'flask.app' under four states: with no handlers anywhere it is False; after adding a root StreamHandler it is True; with logger.propagate = False it is False again (propagation is required); and after restoring propagation but setting the handler level to ERROR, it is False because the effective level is too high.

**Notes.**

- condition: Both an existing handler on the propagation chain and an adequate effective level are required

<a id="u-33102eb5b416"></a>
### `test_log_view_exception`

`def test_log_view_exception(app, client):` · [tests/test_logging.py:L86-L87][f1]

With app.testing = False, a route raising Exception('test') yields a 500 response whose body is non-empty, and the errors_stream contains a traceback headed 'Exception on / [GET]' including 'Exception: test', showing unhandled view exceptions are logged to the request error stream in non-testing mode.

<a id="u-246fbfce6f02"></a>
### `test_logger`

`def test_logger(app):` · [tests/test_logging.py:L36-L39][f1]

Asserts the default app logger is named 'flask_test', has level NOTSET, and carries exactly Flask's default_handler.

<a id="u-26226a640858"></a>
### `test_logger_debug`

`def test_logger_debug(app):` · [tests/test_logging.py:L42-L45][f1]

Setting app.debug = True makes app.logger.level become logging.DEBUG while the handler list remains [default_handler].

<a id="u-84f17f96f47e"></a>
### `test_wsgi_errors_stream`

`def test_wsgi_errors_stream(app, client):` · [tests/test_logging.py:L54-L55][f1]

A route logs an error; the test passes errors_stream=stream to client.get and asserts 'ERROR in test_logging: test' appears in the StringIO, showing error output routes to the request's errors_stream.

Outside a request, wsgi_errors_stream._get_current_object() is sys.stderr; inside a test_request_context with errors_stream=stream it is that stream.

group: [test_wsgi_errors_stream](r2-logging-tests.md#u-84f17f96f47e); uses: [reset_logging](r2-logging-tests.md#u-697d538cfbd3)

**Uncertainties.**

- Exact lookup mechanism of wsgi_errors_stream is defined in flask.logging, not shown

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/tests/test_logging.py
