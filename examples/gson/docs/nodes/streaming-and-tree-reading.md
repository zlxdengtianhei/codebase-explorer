# Streaming and tree reading

**Capability.** Reads JSON from streams and JsonElement trees with token navigation and validation.

Use for JSON parsing and reading behavior. G9 implements streaming reader internals; the tree reader adapts JsonElement trees to JsonReader navigation.

**Children.**

- [Streaming JSON reader internals](streaming-json-reader-internals.md) `streaming-json-reader-internals` · 44 unit(s)
- [JsonElement tree reader](jsonelement-tree-reader.md) `jsonelement-tree-reader` · 24 unit(s)

**Depends on.**

- [JSON tree model](json-tree-model.md) · graph-confirmed · 5 edge(s) · Streaming and tree reading use the JSON tree model to read JsonElement trees.
- [Object binding adapters](object-binding-adapters.md) · graph-confirmed · 2 edge(s)
- [Serialization facade and writing](serialization-facade-and-writing.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [JSON tree model](json-tree-model.md) · graph-confirmed · 1 edge(s)

Parent: [Gson JSON library](gson-json-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
