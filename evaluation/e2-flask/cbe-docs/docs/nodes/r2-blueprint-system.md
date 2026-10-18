# Blueprint System

**Capability.** Owns blueprints end to end: the sansio deferred-setup model that records routes, hooks, and template registrations without an app; the registration machinery that applies them; the concrete runtime class; and the test suite.

Use this subtree to understand how a blueprint defers configuration until register() and how nested blueprints merge into an app. The sansio layer is framework-independent; the runtime layer adds static files, resources, and CLI.

**Children.**

- [Blueprint Deferred Setup](r2-sansio-blueprint-core.md) `r2-sansio-blueprint-core` · 9 unit(s)
- [Blueprint Registration](r2-blueprint-registration.md) `r2-blueprint-registration` · 5 unit(s)
- [App-Scope Blueprint Hooks](r2-blueprint-app-integrations.md) `r2-blueprint-app-integrations` · 13 unit(s)
- [Concrete Blueprint Runtime](r2-blueprint-runtime.md) `r2-blueprint-runtime` · 5 unit(s)
- [Blueprint Test Suite](r2-blueprint-tests.md) `r2-blueprint-tests` · 18 unit(s)

**Depended on by.**

- [Templating Test Suite](r2-templating-tests.md) · model-inferred · 0 edge(s)

Parent: [Flask Framework](r2-flask-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
