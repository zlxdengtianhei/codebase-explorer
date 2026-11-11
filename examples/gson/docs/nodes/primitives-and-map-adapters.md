# Primitives and Map Adapters

**Capability.** Implements JsonPrimitive leaf values, adapters that serialize Map types as JSON objects, and internal reflection utilities shared by other classes.

Readers handling scalar values or map serialization should come here. One child models primitives, one produces map adapters, and one exposes internal helpers.

**Children.**

- [JSON Primitive Values](json-primitive-values.md) `json-primitive-values` · 11 unit(s)
- [Map Serialization](map-serialization.md) `map-serialization` · 4 unit(s)
- [Internal Reflection Utilities](internal-reflection-utilities.md) `internal-reflection-utilities` · 3 unit(s)

**Depends on.**

- [Arrays and Stream Bridge](arrays-and-stream-bridge.md) · graph-confirmed · 6 edge(s)

**Depended on by.**

- [Arrays and Stream Bridge](arrays-and-stream-bridge.md) · graph-confirmed · 2 edge(s)

Parent: [Element Types and Tree Adapters](element-types-and-tree-adapters.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
