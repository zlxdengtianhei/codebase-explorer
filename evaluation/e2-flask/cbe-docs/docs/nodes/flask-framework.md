# Flask Framework

**Capability.** The WSGI micro-framework as a whole: a registry-driven application model, a concrete request pipeline, per-concern subsystems, shared helpers, and the tests that pin behavior. The two merged region subtrees are preserved intact and grafted under this root, which gives the framework a single navigation entry point.

Start here to navigate the framework. The flask-app-region subtree covers the app model, concrete pipeline, templating, JSON, sessions, logging, signals, diagnostics, and their tests; the flask-capabilities-region subtree covers contexts, CLI, configuration, blueprints, wrappers, views, helpers, testing support, and further test suites.

**Children.**

- [Flask App Region](flask-app-region.md) `flask-app-region` · 0 unit(s)
- [Flask Capabilities Region](flask-capabilities-region.md) `flask-capabilities-region` · 0 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
