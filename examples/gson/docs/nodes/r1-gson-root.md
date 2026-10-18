# Gson JSON Binding Library

**Capability.** End-to-end conversion between Java objects and JSON: a configurable facade, a runtime generic-type model, a pluggable adapter framework with built-in adapters, streaming JSON readers, exclusion/reflection policy, the JSON element model, and internal support utilities.

Start here to navigate the library. Conversion requests enter via the facade, are dispatched through the adapter framework using the type model, and read/write JSON through the streaming layer; exclusion and reflection policy shape which members participate.

**Children.**

- [Gson Facade and Conversion API](r1-facade-api.md) `r1-facade-api` · 17 unit(s)
- [Runtime Generic Type Model](r1-type-model.md) `r1-type-model` · 19 unit(s)
- [TypeAdapter Framework](r1-adapter-framework.md) `r1-adapter-framework` · 13 unit(s)
- [Built-in Type Adapters](r1-builtin-adapters.md) `r1-builtin-adapters` · 25 unit(s)
- [Streaming JSON Reading](r1-streaming-json.md) `r1-streaming-json` · 69 unit(s)
- [Exclusion and Reflection Policy](r1-reflection-policy.md) `r1-reflection-policy` · 26 unit(s)
- [JSON Element Model and Exceptions](r1-json-element-model.md) `r1-json-element-model` · 4 unit(s)
- [Internal Support Utilities](r1-internal-support.md) `r1-internal-support` · 10 unit(s)

Parent: [Gson JSON Library](gson-json-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
