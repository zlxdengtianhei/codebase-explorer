# Reflective Object Binding

**Capability.** Binds JSON to object fields via reflection: field-based adapter factories, record support, instance construction, and access filtering.

Come here for how Gson serializes arbitrary classes without explicit adapters. The nested groups split field binding and reflection utilities from instance creation and access filtering.

**Children.**

- [Field Binding and Introspection](field-binding-and-introspection.md) `field-binding-and-introspection` · 26 unit(s)
- [Instance Creation and Access Control](instance-creation-and-access-control.md) `instance-creation-and-access-control` · 23 unit(s)

**Depends on.**

- [JSON Element Tree Model](json-element-tree-model.md) · graph-confirmed · 1 edge(s)
- [Public API and Type Resolution](public-api-and-type-resolution.md) · graph-confirmed · 19 edge(s) · Reflective binding relies on the public API and type resolution to obtain adapters for field types.
- [Type Adapter Framework](type-adapter-framework.md) · graph-confirmed · 4 edge(s)

**Depended on by.**

- [JSON Element Tree Model](json-element-tree-model.md) · graph-confirmed · 1 edge(s)
- [Public API and Type Resolution](public-api-and-type-resolution.md) · graph-confirmed · 1 edge(s)
- [Type Adapter Framework](type-adapter-framework.md) · graph-confirmed · 2 edge(s)

Parent: [Gson JSON Serialization Library](gson-json-serialization-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
