# JSON Element Tree Model

**Capability.** Models parsed JSON as an in-memory tree of elements: objects, arrays, primitives, plus the ordered map and adapters that operate on them.

Come here for the JsonElement class hierarchy and tree manipulation. The nested group covers the element types and their adapters; the sibling implements JsonObject and its backing ordered map.

**Children.**

- [Element Types and Tree Adapters](element-types-and-tree-adapters.md) `element-types-and-tree-adapters` · 49 unit(s)
- [JSON Object and Ordered Map](json-object-and-ordered-map.md) `json-object-and-ordered-map` · 30 unit(s)

**Depends on.**

- [JSON Reading Infrastructure](json-reading-infrastructure.md) · graph-confirmed · 1 edge(s)
- [Public API and Type Resolution](public-api-and-type-resolution.md) · graph-confirmed · 8 edge(s)
- [Reflective Object Binding](reflective-object-binding.md) · graph-confirmed · 1 edge(s)
- [Type Adapter Framework](type-adapter-framework.md) · graph-confirmed · 3 edge(s)

**Depended on by.**

- [JSON Reading Infrastructure](json-reading-infrastructure.md) · graph-confirmed · 5 edge(s) · The reading infrastructure materializes parsed input as JsonElement tree nodes.
- [JSON Writing Infrastructure](json-writing-infrastructure.md) · graph-confirmed · 3 edge(s) · The writing infrastructure emits JsonElement tree values as JSON output.
- [Public API and Type Resolution](public-api-and-type-resolution.md) · graph-confirmed · 10 edge(s)
- [Reflective Object Binding](reflective-object-binding.md) · graph-confirmed · 1 edge(s)
- [Type Adapter Framework](type-adapter-framework.md) · graph-confirmed · 1 edge(s)

Parent: [Gson JSON Serialization Library](gson-json-serialization-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
