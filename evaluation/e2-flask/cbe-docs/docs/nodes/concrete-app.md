# Concrete WSGI Application

**Capability.** The flask.Flask class: it turns the sansio registry into a runnable WSGI application with a Click CLI, dev server, static folder serving, the full request dispatch pipeline, error handling, contexts, URL building, resource access, and test-client support.

Use this subtree for runtime behavior: what happens between an incoming environ and the returned response, and how the app is constructed and served. Registration itself lives under core-app-model; this subtree executes what was registered.

Parent: [Flask App Region](flask-app-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
