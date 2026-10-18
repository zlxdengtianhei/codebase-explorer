# Testing Support

**Capability.** Owns Flask's test tooling: an app-aware EnvironBuilder, FlaskClient preserving contexts across requests, FlaskCliRunner binding ScriptInfo for CLI tests, and shared pytest fixtures in conftest.

Use these when writing tests for Flask apps. conftest fixtures provide environment isolation, app/client fixtures, import-path sandboxes, and context-leak detection for the suite itself.

Parent: [Flask Capabilities Region](flask-capabilities-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
