# Blinker Signals

**Capability.** Definition of Flask's ten named lifecycle signals on a private blinker Namespace; pure declaration with no behavioral logic.

Use this as the reference for signal names available for subscription (request_started, appcontext_popped, message_flashed, etc.). Emission points live in the dispatch, templating, and flashing code.

Parent: [Flask App Region](flask-app-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
