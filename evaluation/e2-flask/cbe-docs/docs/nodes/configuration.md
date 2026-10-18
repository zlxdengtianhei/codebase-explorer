# Configuration Loading

**Capability.** Owns the Config dict and its loaders: Python files, objects, mappings, environment variables and prefixed env vars, plus namespace queries and the ConfigAttribute descriptor forwarding App attributes to config.

Use this to learn every supported way to populate app config and how keys are filtered (uppercase only). The instance-path tests cover how the app locates its instance folder.

Parent: [Flask Capabilities Region](flask-capabilities-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
