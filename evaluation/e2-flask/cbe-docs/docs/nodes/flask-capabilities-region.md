# Flask Capabilities Region

**Capability.** The second merged region: the framework decomposed into runtime contexts, CLI, configuration, blueprints, request/response objects, views, shared helpers, testing support, and the test suites and fixtures that pin their behavior.

Use this subtree to navigate the per-capability modules and the tests that exercise them. Source modules are kept separate from the tests that exercise them.

**Children.**

- [Flask Framework](r2-flask-framework.md) `r2-flask-framework` · 1 unit(s)
- [Application and Request Contexts](app-context-and-globals.md) `app-context-and-globals` · 0 unit(s)
- [Command-Line Interface](cli-system.md) `cli-system` · 0 unit(s)
- [Configuration Loading](configuration.md) `configuration` · 0 unit(s)
- [Blueprint System](blueprint-system.md) `blueprint-system` · 0 unit(s)
- [Request and Response Wrappers](request-response-objects.md) `request-response-objects` · 0 unit(s)
- [Class-Based Views](view-system.md) `view-system` · 0 unit(s)
- [Shared Helpers](helpers-utilities.md) `helpers-utilities` · 0 unit(s)
- [Testing Support](testing-support.md) `testing-support` · 0 unit(s)
- [JSON Test Suite](json-tests.md) `json-tests` · 0 unit(s)
- [Templating Test Suite](templating-tests.md) `templating-tests` · 0 unit(s)
- [Logging Test Suite](logging-tests.md) `logging-tests` · 0 unit(s)
- [Error Handler Tests](error-handling-tests.md) `error-handling-tests` · 0 unit(s)
- [Type-Checking Fixtures](type-check-fixtures.md) `type-check-fixtures` · 0 unit(s)

**Depends on.**

- [Flask App Region](flask-app-region.md) · graph-confirmed · 56 edge(s) · The capabilities region calls back into the app region for the application model and pipeline services (a reciprocal cross-region cycle).

**Depended on by.**

- [Flask App Region](flask-app-region.md) · graph-confirmed · 14 edge(s) · The app region calls into the capabilities region for shared capabilities such as contexts, helpers, and testing support used by the pipeline.

Parent: [Flask Framework](flask-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
