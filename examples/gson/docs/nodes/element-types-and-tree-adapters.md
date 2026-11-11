# Element Types and Tree Adapters

**Capability.** Defines the JsonElement hierarchy—arrays, primitives, the abstract base—and the adapters and bridges that convert between trees and streams.

Readers working with individual tree node types should look here. The nested groups separate array/bridge infrastructure from primitives and map serialization.

**Children.**

- [Arrays and Stream Bridge](arrays-and-stream-bridge.md) `arrays-and-stream-bridge` · 31 unit(s)
- [Primitives and Map Adapters](primitives-and-map-adapters.md) `primitives-and-map-adapters` · 18 unit(s)

**Depends on.**

- [JSON Object and Ordered Map](json-object-and-ordered-map.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [JSON Object and Ordered Map](json-object-and-ordered-map.md) · graph-confirmed · 1 edge(s)

Parent: [JSON Element Tree Model](json-element-tree-model.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
