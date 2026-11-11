# Parsing and buffer foundations

**Capability.** Provides the core.h base: buffer classes, argument type encoding, format-string parsing, spec parsing, and iterator/pointer buffer adapters.

Come here for the lowest layer of format machinery. Children divide into core argument/buffer definitions, spec parsing, iterator adapters, truncated formatting, format_as mapping, packed specs, and raw pointer buffers.

**Children.**

- [Core argument and buffer base](core-argument-and-buffer-base.md) `core-argument-and-buffer-base` · 30 unit(s)
- [Spec parsing and printf mapping](spec-parsing-and-printf-mapping.md) `spec-parsing-and-printf-mapping` · 14 unit(s)
- [Iterator buffer adapters](iterator-buffer-adapters.md) `iterator-buffer-adapters` · 9 unit(s)
- [Truncated formatting](truncated-formatting.md) `truncated-formatting` · 5 unit(s)
- [format\_as type mapping](format-as-type-mapping.md) `format-as-type-mapping` · 4 unit(s)
- [Packed format specs](packed-format-specs.md) `packed-format-specs` · 3 unit(s)
- [Raw pointer buffers](raw-pointer-buffers.md) `raw-pointer-buffers` · 3 unit(s)

Parent: [Format argument infrastructure](format-argument-infrastructure.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
