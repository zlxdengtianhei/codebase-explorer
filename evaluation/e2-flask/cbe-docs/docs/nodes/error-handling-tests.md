# Error Handler Tests

**Capability.** Pins Flask's error-handler resolution and registration validation for app-level handlers, including which exceptions match which handlers and invalid registration forms.

Read this to understand handler lookup precedence and the validation errors raised for malformed registrations. Cross-reference blueprint-scoped handler tests in blueprint-tests.

Parent: [Flask Capabilities Region](flask-capabilities-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
