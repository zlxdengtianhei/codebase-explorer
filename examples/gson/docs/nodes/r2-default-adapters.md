# Built-in Type Adapter Factories

**Capability.** The stock TypeAdapterFactories Gson assembles by default: JDK primitive/wrapper/utility types, collections/maps and the JsonElement tree itself, and date/time families; each factory claims a type family and defers by returning null otherwise.

Use this subtree to find where a given Java type's default JSON mapping is implemented. Children split the families: primitive/utility adapters in TypeAdapters, container and tree adapters, and the date/time adapters including java.sql support.

**Children.**

- [Primitive and Utility Type Adapters](r2-primitive-adapters.md) `r2-primitive-adapters` · 8 unit(s)
- [Collection, Map, and Tree Adapters](r2-collection-map-adapters.md) `r2-collection-map-adapters` · 15 unit(s)
- [Date and Time Adapters](r2-date-time-adapters.md) `r2-date-time-adapters` · 15 unit(s)

**Depends on.**

- [Builder and Naming Configuration](r2-configuration.md) · model-inferred · 0 edge(s)
- [JSON DOM Tree](r2-dom-tree.md) · graph-confirmed · 21 edge(s)
- [Internal Utilities and Data Structures](r2-infrastructure.md) · graph-confirmed · 5 edge(s)
- [Object Construction Strategy](r2-object-construction.md) · graph-confirmed · 2 edge(s) · Collection, map, and @JsonAdapter factories create their container instances through ConstructorConstructor.get.
- [Streaming JSON Writer and Lexical Model](r2-streaming.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [JSON DOM Tree](r2-dom-tree.md) · model-inferred · 0 edge(s)
- [Internal Utilities and Data Structures](r2-infrastructure.md) · graph-confirmed · 2 edge(s) · Streams.parse and Streams.write convert between JsonElement trees and streams via JsonElementTypeAdapter.

Parent: [Gson JSON Library](r2-gson.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
