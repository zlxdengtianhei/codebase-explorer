# Command Line and Public Helpers

**Capability.** Provides the user-facing command line interface together with public helper functions, the WSGI-aware Blueprint and the app run method that developers call directly.

Use this for the flask command and the everyday public API. The CLI subgroup handles options, groups, app discovery and the server command, while the helpers module offers functions like url_for and redirect plus Blueprint and run.

**Children.**

- [Flask CLI Implementation](flask-cli-implementation.md) `flask-cli-implementation` · 38 unit(s)
- [Helpers, Flask Blueprint and Run](helpers-flask-blueprint-and-run.md) `helpers-flask-blueprint-and-run` · 20 unit(s)

**Depended on by.**

- [Runtime App, Contexts and Testing](runtime-app-contexts-and-testing.md) · graph-confirmed · 2 edge(s) · 1 inferred relation(s)
- [Sansio App and Scaffold Foundations](sansio-app-and-scaffold-foundations.md) · graph-confirmed · 3 edge(s)
- [Templates, Views and Wrappers](templates-views-and-wrappers.md) · graph-confirmed · 2 edge(s)

Parent: [Flask Web Framework](flask-web-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
