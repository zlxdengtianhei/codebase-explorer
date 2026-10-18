# Runtime Generic Type Model

**Capability.** Captures and manipulates generic Types despite erasure: TypeToken captures T from anonymous subclasses; GsonTypes builds, canonicalizes, resolves, and structurally compares parameterized, array, wildcard, and type-variable types, backed by immutable Type implementations.

Consult this subtree for generic type identity: what type an adapter is for, how type variables resolve against a context, and how supertype/collection/map element types are derived. Adapter creation and reflective binding both depend on it.

**Depended on by.**

- [TypeAdapter Framework](adapter-framework.md) · model-inferred · 0 edge(s) · Adapter factories claim and match types using TypeToken and the GsonTypes type model.
- [Public API, Facade and Builder Configuration](conversion-api.md) · model-inferred · 0 edge(s)
- [Object Construction Strategy](object-construction.md) · model-inferred · 0 edge(s)
- [Reflection Policy and Object Binding](reflective-binding.md) · model-inferred · 0 edge(s)

Parent: [Gson JSON Library](gson-json-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
