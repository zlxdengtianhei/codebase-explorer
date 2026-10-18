# Builder and Naming Configuration

**Capability.** Accumulates mutable configuration (custom adapters, naming policy, number strategy) and freezes it into an ordered, immutable factory list for a Gson instance.

Use GsonBuilder's fluent setters to register adapters and pick strategies; createFactories assembles the pipeline that the adapter layer consumes.

**Depends on.**

- [TypeAdapter Framework](adapter-framework.md) · model-inferred · 0 edge(s) · GsonBuilder freezes custom adapters into an ordered factory list that the adapter pipeline consumes.

Parent: [Public API, Facade and Builder Configuration](conversion-api.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
