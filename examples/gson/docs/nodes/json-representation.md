# JSON Streaming and DOM Representation

**Capability.** Owns both JSON representations and the lexical contract shared between them: the immutable in-memory JsonElement tree, token-level streaming readers and writers with strictness and scope state machines, parser facades, and the runtime exception types callers catch when JSON is malformed.

Use this subtree to build, inspect, parse, and emit JSON. Adapters convert between tree and stream; the writer's scope stack and the reader's strictness rules define the shared RFC 8259 lexical model.

**Children.**

- [Streaming JSON Reading](streaming-json.md) `streaming-json` · 0 unit(s)
- [Streaming JSON Writer and Lexical Model](streaming.md) `streaming` · 0 unit(s)
- [JSON DOM Tree](dom-tree.md) `dom-tree` · 0 unit(s)
- [JSON Element Exceptions](json-element-model.md) `json-element-model` · 0 unit(s)

**Depended on by.**

- [TypeAdapter Framework](adapter-framework.md) · model-inferred · 0 edge(s) · Adapters read and write via JsonReader/JsonWriter and produce JsonElement trees via toJsonTree.
- [Gson Facade and Conversion API](facade-api.md) · model-inferred · 0 edge(s)

Parent: [Gson JSON Library](gson-json-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
