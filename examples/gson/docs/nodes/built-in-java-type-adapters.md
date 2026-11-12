# Built-in Java type adapters

**Capability.** Provides foundational TypeAdapter implementations for Java scalars, atomics, conversion helpers, and strict floating-point values.

Consult for built-in adapter behavior. Basic adapters cover common Java types; null-safe wrappers handle atomics and similar; conversion base supports adapter helpers; strict adapters validate floating-point JSON.

**Children.**

- [Basic Java type adapters](basic-java-type-adapters.md) `basic-java-type-adapters` · 25 unit(s)
- [Null-safe atomic adapters](null-safe-atomic-adapters.md) `null-safe-atomic-adapters` · 10 unit(s)
- [TypeAdapter conversion base](typeadapter-conversion-base.md) `typeadapter-conversion-base` · 8 unit(s)
- [Strict floating-point adapters](strict-floating-point-adapters.md) `strict-floating-point-adapters` · 3 unit(s)

**Depended on by.**

- [Gson setup and defaults](gson-setup-and-defaults.md) · graph-confirmed · 3 edge(s) · Gson setup and defaults use built-in Java type adapters for standard adapter registrations.

Parent: [Core configuration and adapters](core-configuration-and-adapters.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
