# Gson JSON Library

**Capability.** Owns end-to-end conversion between Java objects and JSON: the public facade and contracts, builder-driven configuration, the runtime generic-type model, an adapter pipeline, streaming and DOM JSON representations, reflection-based binding, and shared internal infrastructure. Both region units describe the same library from complementary navigation angles, so both root here.

Start here to navigate the library. Conversion requests enter via the facade and builder, are dispatched through the adapter pipeline using the type model, and read/write JSON through the streaming and DOM layers; reflection policy and construction strategy shape object binding.

**Children.**

- [Gson JSON Binding Library](r1-gson-root.md) `r1-gson-root` · 0 unit(s)
- [Gson JSON Library](r2-gson.md) `r2-gson` · 0 unit(s)
- [Public API, Facade and Builder Configuration](conversion-api.md) `conversion-api` · 0 unit(s)
- [Runtime Generic Type Model](type-model.md) `type-model` · 0 unit(s)
- [Type Adapter Pipeline and Object Construction](adapter-pipeline.md) `adapter-pipeline` · 0 unit(s)
- [JSON Streaming and DOM Representation](json-representation.md) `json-representation` · 0 unit(s)
- [Reflection Policy and Object Binding](reflective-binding.md) `reflective-binding` · 0 unit(s)
- [Internal Utilities and Data Structures](internal-infrastructure.md) `internal-infrastructure` · 0 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
