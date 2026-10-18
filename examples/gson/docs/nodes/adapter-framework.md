# TypeAdapter Framework

**Capability.** Defines the abstract TypeAdapter contract (read/write, nullSafe wrapping, conveniences), the serialization-delegation marker and runtime-type wrapper used by the factory chain, and factory plumbing shared by custom adapters.

Use this subtree to understand how adapters compose and delegate and how the runtime-type wrapper picks the serialization adapter.

**Depends on.**

- [JSON Streaming and DOM Representation](json-representation.md) · model-inferred · 0 edge(s) · Adapters read and write via JsonReader/JsonWriter and produce JsonElement trees via toJsonTree.
- [Runtime Generic Type Model](type-model.md) · model-inferred · 0 edge(s) · Adapter factories claim and match types using TypeToken and the GsonTypes type model.

**Depended on by.**

- [Builder and Naming Configuration](configuration.md) · model-inferred · 0 edge(s) · GsonBuilder freezes custom adapters into an ordered factory list that the adapter pipeline consumes.
- [Gson Facade and Conversion API](facade-api.md) · model-inferred · 0 edge(s)

Parent: [Type Adapter Pipeline and Object Construction](adapter-pipeline.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
