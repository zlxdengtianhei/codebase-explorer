# Arrays and Stream Bridge

**Capability.** Implements JsonArray, the abstract JsonElement base, and the Streams/adapter bridge between streaming readers/writers and element trees.

Come here for array nodes and the machinery connecting trees to streaming. The children divide array modeling, the element base and bridge, and the tree-reading adapter.

**Children.**

- [JSON Array Model](json-array-model.md) `json-array-model` · 16 unit(s)
- [Tree Element Bridge](tree-element-bridge.md) `tree-element-bridge` · 12 unit(s)
- [Element Tree Adapter](element-tree-adapter.md) `element-tree-adapter` · 3 unit(s)

**Depends on.**

- [Primitives and Map Adapters](primitives-and-map-adapters.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Primitives and Map Adapters](primitives-and-map-adapters.md) · graph-confirmed · 6 edge(s)

Parent: [Element Types and Tree Adapters](element-types-and-tree-adapters.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
