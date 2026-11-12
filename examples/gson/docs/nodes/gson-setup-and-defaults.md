# Gson setup and defaults

**Capability.** Builds configured Gson instances and provides default serialization adapters.

Relevant when creating or customizing Gson. Builder configuration accumulates settings and registrations; core defaults supply the entry point and standard date, number, Object, and delegation adapters.

**Children.**

- [Gson builder configuration](gson-builder-configuration.md) `gson-builder-configuration` · 27 unit(s)
- [Core Gson default adapters](core-gson-default-adapters.md) `core-gson-default-adapters` · 25 unit(s)

**Depends on.**

- [Built-in Java type adapters](built-in-java-type-adapters.md) · graph-confirmed · 3 edge(s) · Gson setup and defaults use built-in Java type adapters for standard adapter registrations.

Parent: [Core configuration and adapters](core-configuration-and-adapters.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
