# Streaming JSON Reading

**Capability.** Token-level JSON reading: JsonReader is the streaming RFC 8259 tokenizer with strictness and nesting control; JsonTreeReader reimplements the same contract over an in-memory JsonElement tree; JsonParser and JsonStreamParser are the static and iterator facades built on them.

Use this subtree for parsing behavior: tokenization, leniency rules, error locations/paths, and how tree-based and stream-based reading share one reader contract.

**Depends on.**

- [JSON DOM Tree](dom-tree.md) · model-inferred · 0 edge(s) · JsonTreeReader reimplements the reader contract over an in-memory JsonElement tree.

Parent: [JSON Streaming and DOM Representation](json-representation.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
