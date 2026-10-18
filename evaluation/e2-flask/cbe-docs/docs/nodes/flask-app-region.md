# Flask App Region

**Capability.** The first merged region: the sans-I/O application core, the concrete WSGI app, and the per-concern subsystems (templating, JSON, sessions, logging, signals, diagnostics) plus the test suites that pin them.

Use this subtree to navigate the application model and the request pipeline it feeds, then the self-contained subsystems consumed by that pipeline. Test subtrees here document expected behavior.

**Children.**

- [Flask Framework](r1-flask-framework.md) `r1-flask-framework` · 2 unit(s)
- [Sans-I/O Application Core](core-app-model.md) `core-app-model` · 0 unit(s)
- [Concrete WSGI Application](concrete-app.md) `concrete-app` · 0 unit(s)
- [Template Rendering](templating.md) `templating` · 0 unit(s)
- [JSON Serialization](json-support.md) `json-support` · 0 unit(s)
- [Session Support](sessions.md) `sessions` · 0 unit(s)
- [Application Logging](logging.md) `logging` · 0 unit(s)
- [Blinker Signals](signals.md) `signals` · 0 unit(s)
- [Diagnostics and Debug Errors](debug-helpers.md) `debug-helpers` · 0 unit(s)
- [Test Suites and Fixture Apps](tests.md) `tests` · 0 unit(s)

**Depends on.**

- [Flask Capabilities Region](flask-capabilities-region.md) · graph-confirmed · 14 edge(s) · The app region calls into the capabilities region for shared capabilities such as contexts, helpers, and testing support used by the pipeline.

**Depended on by.**

- [Flask Capabilities Region](flask-capabilities-region.md) · graph-confirmed · 56 edge(s) · The capabilities region calls back into the app region for the application model and pipeline services (a reciprocal cross-region cycle).

Parent: [Flask Framework](flask-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
