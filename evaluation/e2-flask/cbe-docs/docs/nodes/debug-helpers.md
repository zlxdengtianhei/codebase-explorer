# Diagnostics and Debug Errors

**Capability.** Developer-experience aids: FormDataRoutingRedirect and DebugFilesKeyError turn common form/routing mistakes into clear assertions, attach_enctype_error_multidict patches file lookups with better errors, and explain_template_loading_attempts/_dump_loader_info report template lookup attempts.

Use this subtree when interpreting Flask's debug-mode assertions and template-loading diagnostics. Consumed by the dispatch pipeline and the template loader.

**Depended on by.**

- [Template Rendering](templating.md) · model-inferred · 0 edge(s)

Parent: [Flask App Region](flask-app-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
