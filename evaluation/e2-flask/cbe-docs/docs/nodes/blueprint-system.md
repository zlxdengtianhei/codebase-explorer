# Blueprint System

**Capability.** Owns blueprints end to end: the sansio deferred-setup model that records routes, hooks, and template registrations without an app; the registration machinery that applies them; the concrete runtime class; and the test suite.

Use this subtree to understand how a blueprint defers configuration until register() and how nested blueprints merge into an app. The sansio layer is framework-independent; the runtime layer adds static files, resources, and CLI.

Parent: [Flask Capabilities Region](flask-capabilities-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
