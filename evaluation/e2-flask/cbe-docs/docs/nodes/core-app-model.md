# Sans-I/O Application Core

**Capability.** The framework-agnostic application model: a central registry for URL rules, blueprints, error handlers, hooks, and configuration, plus the Scaffold base shared by apps and blueprints for route, endpoint, error-handler, and request-hook registration. Concrete request handling is deliberately excluded and left to subclasses.

Use this subtree to understand how views, blueprints, and handlers get registered and how app configuration, paths, and shared state are initialized. Everything here is usable before any request arrives; subclasses (see concrete-app) consume these registries at dispatch time.

Parent: [Flask App Region](flask-app-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
