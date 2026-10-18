# Shared Helpers

**Capability.** Owns the module-level helpers views call directly: URL building, response construction, abort, flashing, template attributes, file streaming and serving, and environment/path introspection.

Use this subtree as the utility reference. It is deliberately separate from its consumers (blueprints, CLI, wrappers) which call into it.

**Depended on by.**

- [Request and Response Wrappers](request-response-objects.md) · model-inferred · 0 edge(s)

Parent: [Flask Capabilities Region](flask-capabilities-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
