# Float presentation rendering

**Capability.** Renders converted float digits per format specs in fixed, exponential, or shortest notation, supported by bit-level binary and hexfloat primitives.

Come here once digits exist and must be laid out per spec. Binary and float primitives supply bit manipulation and hexfloat; presentation writers choose notation and handle signs and non-finite values.

**Children.**

- [Binary and float primitives](binary-and-float-primitives.md) `binary-and-float-primitives` · 8 unit(s)
- [Float presentation writers](float-presentation-writers.md) `float-presentation-writers` · 7 unit(s)

**Depends on.**

- [Float to decimal conversion](float-to-decimal-conversion.md) · graph-confirmed · 1 edge(s)
- [Value writing and drivers](value-writing-and-drivers.md) · graph-confirmed · 5 edge(s)

**Depended on by.**

- [Float to decimal conversion](float-to-decimal-conversion.md) · graph-confirmed · 8 edge(s) · Decimal conversion results feed the presentation rendering layer that lays out digits per format specs.
- [Value writing and drivers](value-writing-and-drivers.md) · graph-confirmed · 2 edge(s)

Parent: [Core formatting implementation](core-formatting-implementation.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
