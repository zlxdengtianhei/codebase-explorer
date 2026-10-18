# Streaming JSON Writer and Lexical Model

**Capability.** Emits RFC 8259 JSON token by token through a scope-stack state machine (JsonScope), with a Strictness policy, the JsonToken vocabulary, and MalformedJsonException defining the lexical contract shared with reading.

Use JsonWriter for direct character output; JsonScope and Strictness explain the state and validation rules, and JsonToken names the stream's token types.

**Depends on.**

- [JSON DOM Tree](dom-tree.md) · model-inferred · 0 edge(s)

Parent: [JSON Streaming and DOM Representation](json-representation.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
