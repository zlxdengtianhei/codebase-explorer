# Templates, Views and Wrappers

**Capability.** Groups the view-layer pieces: Jinja template rendering and loading with class-based views, request and response wrappers, signals and debugging aids.

Come here for how responses are rendered and how views and request objects are shaped. One child covers Jinja environment, loader and render functions, and the other covers class-based views, wrappers, signals and diagnostics.

**Children.**

- [Views, Wrappers, Signals and Debug Aids](views-wrappers-signals-and-debug-aids.md) `views-wrappers-signals-and-debug-aids` · 21 unit(s)
- [Template Rendering and Loading](template-rendering-and-loading.md) `template-rendering-and-loading` · 18 unit(s)

**Depends on.**

- [Command Line and Public Helpers](command-line-and-public-helpers.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Runtime App, Contexts and Testing](runtime-app-contexts-and-testing.md) · graph-confirmed · 1 edge(s)

Parent: [Flask Web Framework](flask-web-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
