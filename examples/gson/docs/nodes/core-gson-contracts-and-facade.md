# Core Gson Contracts and Facade

**Capability.** Provides TypeToken generic-type resolution, the public serializer/deserializer contracts with their tree bridge, and the thread-safe Gson entry point.

Readers tracing a toJson/fromJson call or resolving generic types should start here. The three children split type reflection, public callback contracts, and the Gson facade with streaming configuration.

**Children.**

- [Generic Type Reflection](generic-type-reflection.md) `generic-type-reflection` · 29 unit(s)
- [Public API and Tree Bridge](public-api-and-tree-bridge.md) `public-api-and-tree-bridge` · 24 unit(s)
- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) `gson-entry-point-and-streaming` · 22 unit(s)

**Depends on.**

- [Annotations and Module Declaration](annotations-and-module-declaration.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Annotations and Module Declaration](annotations-and-module-declaration.md) · graph-confirmed · 5 edge(s)
- [JSON Parsing Facades](json-parsing-facades.md) · graph-confirmed · 3 edge(s) · JsonParser facades use the core Gson contracts to turn text into element trees.

Parent: [Public API and Type Resolution](public-api-and-type-resolution.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
