# Type resolution and enums

**Capability.** Resolves generic Java types and selects runtime adapters for enums and type hierarchies.

Use for type-token, generic-type, and enum adapter behavior. Generic reflection handles type representation and assignability; enum selection implements enum and runtime type adapter selection.

**Children.**

- [Generic type reflection](generic-type-reflection.md) `generic-type-reflection` · 27 unit(s)
- [Enum runtime adapter selection](enum-runtime-adapter-selection.md) `enum-runtime-adapter-selection` · 9 unit(s)

**Depends on.**

- [Object binding adapters](object-binding-adapters.md) · graph-confirmed · 2 edge(s)
- [Serialization facade and writing](serialization-facade-and-writing.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Core configuration and adapters](core-configuration-and-adapters.md) · graph-confirmed · 4 edge(s)
- [Gson annotation adapter support](gson-annotation-adapter-support.md) · graph-confirmed · 2 edge(s)
- [JSON tree model](json-tree-model.md) · graph-confirmed · 3 edge(s)
- [Object binding adapters](object-binding-adapters.md) · graph-confirmed · 6 edge(s) · Object binding adapters use type resolution and enum handling when constructing and binding Java objects.
- [Serialization facade and writing](serialization-facade-and-writing.md) · graph-confirmed · 9 edge(s)

Parent: [Gson JSON library](gson-json-library.md)

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.
