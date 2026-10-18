# Flask Framework

**Capability.** Root capability: a WSGI micro-framework whose application object, extension points, and bundled helpers together turn view functions into routed, templated, session-backed HTTP responses. Children split the framework into its core app model, its concrete request pipeline, and the per-concern subsystems (templating, JSON, sessions, logging, signals, diagnostics, test support) plus the test suites that pin their behavior.

Start here to navigate the framework. The core-app-model subtree covers registration and configuration shared by apps and blueprints; the concrete-app subtree covers the WSGI request lifecycle. Subsystem subtrees are self-contained and consumed by the pipeline; test subtrees document expected behavior.

**Children.**

- [Sans-I/O Application Core](r1-core-app-model.md) `r1-core-app-model` · 12 unit(s)
- [Concrete WSGI Application](r1-concrete-app.md) `r1-concrete-app` · 6 unit(s)
- [Template Rendering](r1-templating.md) `r1-templating` · 16 unit(s)
- [JSON Serialization](r1-json-support.md) `r1-json-support` · 11 unit(s)
- [Session Support](r1-sessions.md) `r1-sessions` · 6 unit(s)
- [Application Logging](r1-logging.md) `r1-logging` · 4 unit(s)
- [Blinker Signals](r1-signals.md) `r1-signals` · 1 unit(s)
- [Diagnostics and Debug Errors](r1-debug-helpers.md) `r1-debug-helpers` · 5 unit(s)
- [Test Suites and Fixture Apps](r1-tests.md) `r1-tests` · 0 unit(s)

**Depends on.**

- [Application Logging](r1-logging.md) · within containment · 1 edge(s)
- [Scaffold Registration Base](r1-scaffold-shared-base.md) · within containment · 1 edge(s)

Parent: [Flask App Region](flask-app-region.md)

## Units (2)

<a id="u-c935356c3924"></a>
### `App.logger`

`def logger(self) -> logging.Logger:` · [src/flask/sansio/app.py:L442-L467][f1]

Cached logging.Logger for the app, created by delegating to flask.logging.create_logger(self).

Per create_logger's contract, the logger is named from app.name, its level is set to DEBUG in debug mode, and a default handler is added only when no handlers are configured. Because it is a cached_property, that configuration happens only at first access.

calls: [create_logger](r1-logging.md#u-185f96e08a34)

**Uncertainties.**

- Exact level and handler behavior is implemented in create_logger, outside this file.

<a id="u-94836406bd81"></a>
### `App.shell_context_processor`

`def shell_context_processor( self, f: T_shell_context_processor ) -> T_shell_context_…` · [src/flask/sansio/app.py:L812-L821][f1]

Registers a shell context processor function by appending it to shell_context_processors and returning f unchanged, so it also works as a decorator; the processors run when a shell context is created.

Guarded by @setupmethod, so it raises AssertionError after the first request.

uses: [setupmethod](r1-scaffold-shared-base.md#u-81ccd06c4290)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/sansio/app.py
