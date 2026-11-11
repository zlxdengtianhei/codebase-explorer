# Adapter Configuration and Policies

**Capability.** Assembles Gson's adapter factories and configuration while deciding which fields and types participate via exclusion strategies and the fluent builder.

Readers configuring Gson or controlling field visibility should look here. The nested group holds the built-in adapters; the sibling module owns exclusion rules and the GsonBuilder configuration.

**Children.**

- [Built-in Adapter Implementations](built-in-adapter-implementations.md) `built-in-adapter-implementations` · 51 unit(s)
- [Exclusion Strategies and Builder](exclusion-strategies-and-builder.md) `exclusion-strategies-and-builder` · 20 unit(s)

**Depends on.**

- [Adapter Abstractions and Dates](adapter-abstractions-and-dates.md) · graph-confirmed · 3 edge(s)
- [Enum, Number Policy, Runtime Dispatch](enum-number-policy-runtime-dispatch.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Adapter Abstractions and Dates](adapter-abstractions-and-dates.md) · graph-confirmed · 1 edge(s)

Parent: [Type Adapter Framework](type-adapter-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
