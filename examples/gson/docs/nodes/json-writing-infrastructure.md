# JSON Writing Infrastructure

**Capability.** Emits JSON output: a streaming writer enforcing RFC 8259 well-formedness to a Writer, and a tree-building writer over in-memory elements.

Come here for all JSON output handling. One child writes characters token-by-token; the other constructs JsonElement trees through the same JsonWriter API.

**Children.**

- [Streaming JSON writer](streaming-json-writer.md) `streaming-json-writer` · 30 unit(s)
- [In-memory tree writer](in-memory-tree-writer.md) `in-memory-tree-writer` · 10 unit(s)

**Depends on.**

- [JSON Element Tree Model](json-element-tree-model.md) · graph-confirmed · 3 edge(s) · The writing infrastructure emits JsonElement tree values as JSON output.
- [Public API and Type Resolution](public-api-and-type-resolution.md) · graph-confirmed · 4 edge(s)

**Depended on by.**

- [Public API and Type Resolution](public-api-and-type-resolution.md) · graph-confirmed · 2 edge(s)
- [Type Adapter Framework](type-adapter-framework.md) · graph-confirmed · 1 edge(s)

Parent: [Gson JSON Serialization Library](gson-json-serialization-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
