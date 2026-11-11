# Core formatting implementation

**Capability.** Implements the main format.h layer: value writing, integer and float conversion algorithms, and out-of-line stdio/locale definitions.

Come here for how formatted values are actually produced. G3 handles general value writing, G4 float conversion, G5 float presentation, and the inline/stdio child supplies platform-specific definitions.

**Children.**

- [Value writing and drivers](value-writing-and-drivers.md) `value-writing-and-drivers` · 79 unit(s)
- [Inline implementation and stdio](inline-implementation-and-stdio.md) `inline-implementation-and-stdio` · 25 unit(s)
- [Float to decimal conversion](float-to-decimal-conversion.md) `float-to-decimal-conversion` · 18 unit(s)
- [Float presentation rendering](float-presentation-rendering.md) `float-presentation-rendering` · 15 unit(s)

**Depends on.**

- [Format argument infrastructure](format-argument-infrastructure.md) · graph-confirmed · 7 edge(s) · The core formatting layer uses the argument infrastructure's parsing and buffer abstractions to drive value output.
- [Printf implementation](printf-implementation.md) · graph-confirmed · 12 edge(s)

**Depended on by.**

- [Chrono and time formatting](chrono-and-time-formatting.md) · graph-confirmed · 14 edge(s) · Chrono formatting delegates to the core formatting implementation for writing parsed duration and time values.
- [Dynamic args, enums, ostream](dynamic-args-enums-ostream.md) · graph-confirmed · 1 edge(s)
- [Format argument infrastructure](format-argument-infrastructure.md) · graph-confirmed · 10 edge(s)
- [Wide text and styling](wide-text-and-styling.md) · graph-confirmed · 3 edge(s) · Wide and styled formatting reuse the core implementation's writing routines for their output paths.

Parent: [fmt formatting library](fmt-formatting-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
