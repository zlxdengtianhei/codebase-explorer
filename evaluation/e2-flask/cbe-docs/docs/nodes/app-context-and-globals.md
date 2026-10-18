# Application and Request Contexts

**Capability.** Owns the runtime context machinery: AppContext and RequestContext push/pop, the `g` namespace, and the ContextVar-backed global proxies that make app and request state visible to application code.

Use this subtree to understand how app and request state is scoped and accessed via proxies. Readers handling concurrency, teardown, or custom state should start with AppContext and RequestContext, then globals.py for the public proxies.

Parent: [Flask Capabilities Region](flask-capabilities-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
