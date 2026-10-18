# Template Rendering

**Capability.** Jinja integration: the Flask-aware Environment, a DispatchingJinjaLoader that searches app and blueprint loaders (with an explained-failure path feeding diagnostics), render_template/render_template_string with signal dispatch and context processors, and streaming variants.

Use this subtree to trace how a template name resolves across app and blueprint folders and how context processors inject variables. Streaming variants return iterators; loader failures get the explained diagnostic path.

**Depends on.**

- [Diagnostics and Debug Errors](debug-helpers.md) · model-inferred · 0 edge(s)

Parent: [Flask App Region](flask-app-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
