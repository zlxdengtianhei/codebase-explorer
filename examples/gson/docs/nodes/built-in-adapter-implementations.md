# Built-in Adapter Implementations

**Capability.** Implements Gson's stock TypeAdapters for JDK types, numbers, floating-point values, and the ordered factory list that selects serialization policies.

Come here for concrete conversions of primitives, strings, atomics, and common JDK types. The children divide work by value category, with one child assembling the factory list.

**Children.**

- [Built-in JDK Type Adapters](built-in-jdk-type-adapters.md) `built-in-jdk-type-adapters` · 30 unit(s)
- [Gson Configuration Assembly](gson-configuration-assembly.md) `gson-configuration-assembly` · 8 unit(s)
- [Lazy Number Handling](lazy-number-handling.md) `lazy-number-handling` · 7 unit(s)
- [Floating-Point Adapters](floating-point-adapters.md) `floating-point-adapters` · 3 unit(s)
- [Number and Object Adapters](number-and-object-adapters.md) `number-and-object-adapters` · 3 unit(s)

**Depends on.**

- [Exclusion Strategies and Builder](exclusion-strategies-and-builder.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Exclusion Strategies and Builder](exclusion-strategies-and-builder.md) · graph-confirmed · 2 edge(s) · The builder and excluder assemble configuration that selects among the built-in adapter implementations.

Parent: [Adapter Configuration and Policies](adapter-configuration-and-policies.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
