# JSON DOM Tree

**Capability.** Models JSON data as an immutable in-memory tree: JsonElement is the abstract base, with JsonObject (insertion-ordered via LinkedTreeMap), JsonArray, and JsonPrimitive (with numerically normalized equals/hashCode) as concrete node types.

Use these classes to build, inspect, and transform JSON values programmatically; JsonPrimitive's cross-type numeric equality matters when comparing or hashing trees.

**Depends on.**

- [Internal Utilities and Data Structures](internal-infrastructure.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Streaming JSON Writer and Lexical Model](streaming.md) · model-inferred · 0 edge(s)
- [Streaming JSON Reading](streaming-json.md) · model-inferred · 0 edge(s) · JsonTreeReader reimplements the reader contract over an in-memory JsonElement tree.

Parent: [JSON Streaming and DOM Representation](json-representation.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
