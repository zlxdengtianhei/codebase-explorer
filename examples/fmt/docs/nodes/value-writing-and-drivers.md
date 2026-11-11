# Value writing and drivers

**Capability.** Shared low-level helpers, spec-aware writing routines for strings and integers, locale-aware specs, and the formatting driver connecting arguments to writers.

Come here for the mechanics of turning arguments into output characters. Children split into utilities, the writing engine, integer decimal formatting, locale/dynamic specs, stream output, character/pointer writers, and the driver/contexts.

**Children.**

- [Core formatting utilities](core-formatting-utilities.md) `core-formatting-utilities` · 29 unit(s)
- [Value writing engine](value-writing-engine.md) `value-writing-engine` · 18 unit(s)
- [Integer decimal formatting](integer-decimal-formatting.md) `integer-decimal-formatting` · 10 unit(s)
- [Locale and dynamic specs](locale-and-dynamic-specs.md) `locale-and-dynamic-specs` · 7 unit(s)
- [String and stream output](string-and-stream-output.md) `string-and-stream-output` · 5 unit(s)
- [Character and pointer writers](character-and-pointer-writers.md) `character-and-pointer-writers` · 5 unit(s)
- [Formatting driver and contexts](formatting-driver-and-contexts.md) `formatting-driver-and-contexts` · 5 unit(s)

**Depends on.**

- [Float presentation rendering](float-presentation-rendering.md) · graph-confirmed · 2 edge(s)
- [Float to decimal conversion](float-to-decimal-conversion.md) · graph-confirmed · 9 edge(s) · The value writing layer invokes float-to-decimal conversion when formatting floating-point arguments.

**Depended on by.**

- [Float presentation rendering](float-presentation-rendering.md) · graph-confirmed · 5 edge(s)
- [Float to decimal conversion](float-to-decimal-conversion.md) · graph-confirmed · 2 edge(s)
- [Inline implementation and stdio](inline-implementation-and-stdio.md) · graph-confirmed · 4 edge(s)

Parent: [Core formatting implementation](core-formatting-implementation.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
