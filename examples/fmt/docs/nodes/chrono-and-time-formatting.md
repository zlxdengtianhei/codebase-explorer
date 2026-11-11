# Chrono and time formatting

**Capability.** Formats chrono durations, time points, and std::tm values, with spec parsing, calendar math, locale-aware writing, and unit suffixes.

Come here for all date and time formatting. Internals handle parsing and conversions, formatter classes and validation, a localized tm writer, unit suffix mapping, and primitive tm emitters.

**Children.**

- [Chrono formatting internals](chrono-formatting-internals.md) `chrono-formatting-internals` · 29 unit(s)
- [Chrono formatters and validation](chrono-formatters-and-validation.md) `chrono-formatters-and-validation` · 10 unit(s)
- [Localized tm writer](localized-tm-writer.md) `localized-tm-writer` · 5 unit(s)
- [Duration unit suffixes](duration-unit-suffixes.md) `duration-unit-suffixes` · 4 unit(s)
- [Primitive tm emitters](primitive-tm-emitters.md) `primitive-tm-emitters` · 3 unit(s)

**Depends on.**

- [Core formatting implementation](core-formatting-implementation.md) · graph-confirmed · 14 edge(s) · Chrono formatting delegates to the core formatting implementation for writing parsed duration and time values.

Parent: [fmt formatting library](fmt-formatting-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
