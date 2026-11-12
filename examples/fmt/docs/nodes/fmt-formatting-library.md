# fmt Formatting Library

**Capability.** Provides the fmt formatting library, spanning core formatting, compiled engines, character variants, chrono, ranges, and OS/stream integration.

This is the repository-level view of fmt. Core internals and compiled engines handle formatting; character, chrono, range, standard-type, and OS/stream groups extend it to specialized outputs and integrations.

**Children.**

- [Core Formatting Internals](core-formatting-internals.md) `core-formatting-internals` · 125 unit(s)
- [Compiled Formatting Engine](compiled-formatting-engine.md) `compiled-formatting-engine` · 92 unit(s)
- [Character and Style Formatting](character-and-style-formatting.md) `character-and-style-formatting` · 54 unit(s)
- [OS and Stream Integration](os-and-stream-integration.md) `os-and-stream-integration` · 49 unit(s)
- [Chrono Formatting Support](chrono-formatting-support.md) `chrono-formatting-support` · 47 unit(s)
- [Standard Library Formatters](standard-library-formatters.md) `standard-library-formatters` · 34 unit(s)
- [Range and Tuple Formatting](range-and-tuple-formatting.md) `range-and-tuple-formatting` · 31 unit(s)
- [Printf-Style Formatting Engine](printf-style-formatting-engine.md) `printf-style-formatting-engine` · 23 unit(s)
- [Dynamic Arguments, Enums, and C API](dynamic-arguments-enums-and-c-api.md) `dynamic-arguments-enums-and-c-api` · 17 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
