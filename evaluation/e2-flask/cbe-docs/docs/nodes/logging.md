# Application Logging

**Capability.** Per-app logger creation: create_logger attaches a handler only when none in the chain would process the effective level (has_level_handler), and wsgi_errors_stream routes output to the active request's error stream or stderr.

Use this subtree to explain why Flask apps log to werkzeug/dev servers without duplicating handlers, and where error output goes inside versus outside a request.

**Depended on by.**

- [Logging Test Suite](logging-tests.md) · model-inferred · 0 edge(s)

Parent: [Flask App Region](flask-app-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
