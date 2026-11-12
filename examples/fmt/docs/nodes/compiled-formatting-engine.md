# Compiled Formatting Engine

**Capability.** Compiles format strings and supplies the argument, spec, buffer, and output machinery for compiled formatting.

Come here for compiled format-string handling and its supporting pipeline. The compiled engine child handles fragments and output, while G6 provides argument mapping, spec parsing, checking, and buffers.

**Children.**

- [Argument and Spec Pipeline](argument-and-spec-pipeline.md) `argument-and-spec-pipeline` · 65 unit(s)
- [Compiled Format String Engine](compiled-format-string-engine.md) `compiled-format-string-engine` · 27 unit(s)

**Depends on.**

- [Core Formatting Internals](core-formatting-internals.md) · graph-confirmed · 11 edge(s) · compiled-formatting-engine depends on core-formatting-internals for shared formatting primitives and internals.

**Depended on by.**

- [Character and Style Formatting](character-and-style-formatting.md) · graph-confirmed · 1 edge(s)
- [Core Formatting Internals](core-formatting-internals.md) · graph-confirmed · 12 edge(s)
- [Printf-Style Formatting Engine](printf-style-formatting-engine.md) · graph-confirmed · 13 edge(s) · printf-style-formatting-engine depends on compiled-formatting-engine for formatting output.
- [Range and Tuple Formatting](range-and-tuple-formatting.md) · graph-confirmed · 5 edge(s) · range-and-tuple-formatting depends on compiled-formatting-engine for formatting range and tuple elements.

Parent: [fmt Formatting Library](fmt-formatting-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
