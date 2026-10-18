# Logging Test Suite

**Capability.** Pins Flask's logger behavior: default handler and naming, debug-level effects, existing-handler suppression, has_level_handler propagation rules, and routing of view exceptions and log errors to wsgi errors_stream.

Read alongside the reset_logging autouse fixture, which isolates root and flask_test logger state per test. Error output reaches the stream passed as errors_stream to the test client.

**Depends on.**

- [Application Logging](logging.md) · model-inferred · 0 edge(s)

Parent: [Flask Capabilities Region](flask-capabilities-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
