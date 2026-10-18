# Exclusion and Reflection Policy

**Capability.** Decides what Gson may reflect on and serialize: the ExclusionStrategy contract and its Excluder implementation, the FieldNamingStrategy contract, ReflectionAccessFilter with platform detection, and low-level reflection helpers (accessibility, member descriptions, record support, constructor-less instantiation).

Use this subtree to understand which fields/classes are omitted, how member names are derived, and how reflection access is filtered or performed across JVM versions.

**Depended on by.**

- [Reflection-Based Object Binding](reflective-type-adapter-factory.md) · model-inferred · 0 edge(s)

Parent: [Reflection Policy and Object Binding](reflective-binding.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
