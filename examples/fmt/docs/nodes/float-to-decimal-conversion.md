# Float to decimal conversion

**Capability.** Converts floating-point numbers to shortest decimal representations using Dragonbox, with an arbitrary-precision bigint fallback and shared numeric utilities.

Come here for the algorithms that turn doubles into digits. Entry points orchestrate Dragonbox conversion, the numeric core supplies arithmetic and caches, and the bigint child covers exact fallback cases.

**Children.**

- [Numeric core and assertions](numeric-core-and-assertions.md) `numeric-core-and-assertions` · 9 unit(s)
- [Float conversion entry points](float-conversion-entry-points.md) `float-conversion-entry-points` · 6 unit(s)
- [Bigint fallback algorithm](bigint-fallback-algorithm.md) `bigint-fallback-algorithm` · 3 unit(s)

**Depends on.**

- [Float presentation rendering](float-presentation-rendering.md) · graph-confirmed · 8 edge(s) · Decimal conversion results feed the presentation rendering layer that lays out digits per format specs.
- [Value writing and drivers](value-writing-and-drivers.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Float presentation rendering](float-presentation-rendering.md) · graph-confirmed · 1 edge(s)
- [Inline implementation and stdio](inline-implementation-and-stdio.md) · graph-confirmed · 4 edge(s) · The out-of-line stdio implementation calls float conversion when producing compiled output.
- [Value writing and drivers](value-writing-and-drivers.md) · graph-confirmed · 9 edge(s) · The value writing layer invokes float-to-decimal conversion when formatting floating-point arguments.

Parent: [Core formatting implementation](core-formatting-implementation.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
