# JSON Serialization

**Capability.** App-pluggable JSON handling: module-level dumps/loads/dump/load/jsonify delegate to the current app's JSONProvider, and TaggedJSONSerializer with its JSONTag subclasses gives lossless round-trips for non-JSON Python types inside session serialization.

Use this subtree to customize serialization (subclass JSONProvider) or to understand tagged round-tripping of types like tuples and datetimes. The public functions are thin dispatch; behavior lives in the provider and tag classes.

Parent: [Flask App Region](flask-app-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
