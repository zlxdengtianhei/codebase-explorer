# JSON Reading Infrastructure

**Capability.** Implements JsonReader's streaming contract and its in-memory variant that reads token-by-token from a JsonElement tree.

Come here for all JSON input handling. The nested group implements the character-streaming reader; the sibling mirrors its API over element trees.

**Children.**

- [Streaming JsonReader](streaming-jsonreader.md) `streaming-jsonreader` · 56 unit(s)
- [In-memory tree reader](in-memory-tree-reader.md) `in-memory-tree-reader` · 20 unit(s)

**Depends on.**

- [JSON Element Tree Model](json-element-tree-model.md) · graph-confirmed · 5 edge(s) · The reading infrastructure materializes parsed input as JsonElement tree nodes.
- [Public API and Type Resolution](public-api-and-type-resolution.md) · graph-confirmed · 1 edge(s)
- [Type Adapter Framework](type-adapter-framework.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [JSON Element Tree Model](json-element-tree-model.md) · graph-confirmed · 1 edge(s)

Parent: [Gson JSON Serialization Library](gson-json-serialization-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
