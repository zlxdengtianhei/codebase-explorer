# fmt formatting library

**Capability.** Complete C++ formatting system: core format/argument machinery, float conversion, chrono, wide-char, styling, printf compatibility, and C API integration.

Start here for the whole library. Core formatting and argument handling dominate; specialized areas (chrono, wide characters, styling, printf, OS files) build on them.

**Children.**

- [Core formatting implementation](core-formatting-implementation.md) `core-formatting-implementation` · 137 unit(s)
- [Format argument infrastructure](format-argument-infrastructure.md) `format-argument-infrastructure` · 114 unit(s)
- [Chrono and time formatting](chrono-and-time-formatting.md) `chrono-and-time-formatting` · 51 unit(s)
- [Wide text and styling](wide-text-and-styling.md) `wide-text-and-styling` · 44 unit(s)
- [Standard library type formatters](standard-library-type-formatters.md) `standard-library-type-formatters` · 31 unit(s)
- [OS file and C API](os-file-and-c-api.md) `os-file-and-c-api` · 27 unit(s)
- [Ranges and tuples formatting](ranges-and-tuples-formatting.md) `ranges-and-tuples-formatting` · 25 unit(s)
- [Printf implementation](printf-implementation.md) `printf-implementation` · 24 unit(s)
- [Dynamic args, enums, ostream](dynamic-args-enums-ostream.md) `dynamic-args-enums-ostream` · 21 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
