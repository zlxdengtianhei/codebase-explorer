# JSON Test Suite

**Capability.** Pins flask.json serialization, jsonify responses, custom JSON providers, and the tagged serializer: round-tripping special types, tag registration, duplicate/ordering rules, and the abstract JSONTag interface.

Read these to see expected serialization behavior and how custom tags extend TaggedJSONSerializer, including recursive tagging of wrapped values.

Parent: [Flask Capabilities Region](flask-capabilities-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
