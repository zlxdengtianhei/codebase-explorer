# Adapter Abstractions and Dates

**Capability.** Defines the TypeAdapter base class and lookup entry points, and implements java.time, java.sql, and java.util date serialization with configurable formats.

Readers extending TypeAdapter or handling date/time values should come here. One child holds the core abstractions and time adapters; the other handles Date formatting and ISO-8601 parsing.

**Children.**

- [Core Adapter Abstractions and Time](core-adapter-abstractions-and-time.md) `core-adapter-abstractions-and-time` · 20 unit(s)
- [Date Formatting and Parsing](date-formatting-and-parsing.md) `date-formatting-and-parsing` · 13 unit(s)

**Depends on.**

- [Adapter Configuration and Policies](adapter-configuration-and-policies.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Adapter Configuration and Policies](adapter-configuration-and-policies.md) · graph-confirmed · 3 edge(s)
- [Enum, Number Policy, Runtime Dispatch](enum-number-policy-runtime-dispatch.md) · graph-confirmed · 1 edge(s)

Parent: [Type Adapter Framework](type-adapter-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
