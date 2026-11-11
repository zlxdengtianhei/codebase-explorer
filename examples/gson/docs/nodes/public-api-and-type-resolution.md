# Public API and Type Resolution

**Capability.** Exposes Gson's user-facing API: annotations, generic type resolution, serializer/deserializer contracts, the Gson facade, and JSON parsing entry points.

Come here for the classes most users touch directly. The nested group covers reflection types, public contracts, and the Gson facade; siblings add annotations and JsonParser facades.

**Children.**

- [Core Gson Contracts and Facade](core-gson-contracts-and-facade.md) `core-gson-contracts-and-facade` · 75 unit(s)
- [Annotations and Module Declaration](annotations-and-module-declaration.md) `annotations-and-module-declaration` · 15 unit(s)
- [JSON Parsing Facades](json-parsing-facades.md) `json-parsing-facades` · 6 unit(s)

**Depends on.**

- [JSON Element Tree Model](json-element-tree-model.md) · graph-confirmed · 10 edge(s)
- [JSON Writing Infrastructure](json-writing-infrastructure.md) · graph-confirmed · 2 edge(s)
- [Reflective Object Binding](reflective-object-binding.md) · graph-confirmed · 1 edge(s)
- [Type Adapter Framework](type-adapter-framework.md) · graph-confirmed · 3 edge(s) · 1 inferred relation(s)

**Depended on by.**

- [JSON Element Tree Model](json-element-tree-model.md) · graph-confirmed · 8 edge(s)
- [JSON Reading Infrastructure](json-reading-infrastructure.md) · graph-confirmed · 1 edge(s)
- [JSON Writing Infrastructure](json-writing-infrastructure.md) · graph-confirmed · 4 edge(s)
- [Reflective Object Binding](reflective-object-binding.md) · graph-confirmed · 19 edge(s) · Reflective binding relies on the public API and type resolution to obtain adapters for field types.
- [Type Adapter Framework](type-adapter-framework.md) · graph-confirmed · 23 edge(s) · Adapter machinery calls into the public API and type-resolution layer for adapter lookup and type tokens.

Parent: [Gson JSON Serialization Library](gson-json-serialization-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
