# Type Adapter Framework

**Capability.** Provides Gson's TypeAdapter machinery: built-in JDK adapters, configuration assembly, date/time handling, and policy-driven serialization of enums, numbers, and objects.

Come here for how values are converted to and from JSON. The nested groups split core adapter infrastructure from date/time support and policy-based dispatch.

**Children.**

- [Adapter Configuration and Policies](adapter-configuration-and-policies.md) `adapter-configuration-and-policies` · 71 unit(s)
- [Adapter Abstractions and Dates](adapter-abstractions-and-dates.md) `adapter-abstractions-and-dates` · 33 unit(s)
- [Enum, Number Policy, Runtime Dispatch](enum-number-policy-runtime-dispatch.md) `enum-number-policy-runtime-dispatch` · 16 unit(s)

**Depends on.**

- [JSON Element Tree Model](json-element-tree-model.md) · graph-confirmed · 1 edge(s)
- [JSON Writing Infrastructure](json-writing-infrastructure.md) · graph-confirmed · 1 edge(s)
- [Public API and Type Resolution](public-api-and-type-resolution.md) · graph-confirmed · 23 edge(s) · Adapter machinery calls into the public API and type-resolution layer for adapter lookup and type tokens.
- [Reflective Object Binding](reflective-object-binding.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [JSON Element Tree Model](json-element-tree-model.md) · graph-confirmed · 3 edge(s)
- [JSON Reading Infrastructure](json-reading-infrastructure.md) · graph-confirmed · 2 edge(s)
- [Public API and Type Resolution](public-api-and-type-resolution.md) · graph-confirmed · 3 edge(s) · 1 inferred relation(s)
- [Reflective Object Binding](reflective-object-binding.md) · graph-confirmed · 4 edge(s)

Parent: [Gson JSON Serialization Library](gson-json-serialization-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
