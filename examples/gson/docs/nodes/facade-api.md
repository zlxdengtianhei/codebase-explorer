# Gson Facade and Conversion API

**Capability.** Owns the public Gson entry points: immutable configuration applied to JsonReader/JsonWriter, adapter lookup and caching (including cyclic-type and delegate resolution), and the toJson/fromJson/toJsonTree overload families funneling into the core reader/writer paths; also holds output-formatting and Long serialization policy value objects.

Use this subtree for every top-level object-to-JSON conversion and to see how configuration propagates into the streaming layer.

**Depends on.**

- [TypeAdapter Framework](adapter-framework.md) · model-inferred · 0 edge(s)
- [JSON Streaming and DOM Representation](json-representation.md) · model-inferred · 0 edge(s)

Parent: [Public API, Facade and Builder Configuration](conversion-api.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
