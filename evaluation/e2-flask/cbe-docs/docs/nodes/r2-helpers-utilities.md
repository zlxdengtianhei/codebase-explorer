# Shared Helpers

**Capability.** Owns the module-level helpers views call directly: URL building, response construction, abort, flashing, template attributes, file streaming and serving, and environment/path introspection.

Use this subtree as the utility reference. It is deliberately separate from its consumers (blueprints, CLI, wrappers) which call into it.

**Children.**

- [File Serving Helpers](r2-file-serving-helpers.md) `r2-file-serving-helpers` · 3 unit(s)
- [stream\_with\_context](r2-streaming-helpers.md) `r2-streaming-helpers` · 7 unit(s)
- [Request and Response Helpers](r2-request-response-helpers.md) `r2-request-response-helpers` · 7 unit(s)
- [Environment and Path Helpers](r2-environment-helpers.md) `r2-environment-helpers` · 4 unit(s)

**Depends on.**

- [Application and Request Contexts](r2-app-context-and-globals.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Request and Response Wrappers](r2-request-response-objects.md) · graph-confirmed · 1 edge(s) · Request.blueprints uses helpers._split_blueprint_path to expand the blueprint parent chain.

Parent: [Flask Framework](r2-flask-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
