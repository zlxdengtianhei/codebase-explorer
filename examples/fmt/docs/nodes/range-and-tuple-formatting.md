# Range and Tuple Formatting

**Capability.** Supports range and tuple detection, access traits, formatter selection, and range formatter specializations.

Use this group for range and tuple formatting infrastructure. Infrastructure and access traits support detection and helpers, while specializations select formatters for map-like, string, debug, and sequence ranges.

**Children.**

- [Range and Tuple Formatting Infrastructure](range-and-tuple-formatting-infrastructure.md) `range-and-tuple-formatting-infrastructure` · 16 unit(s)
- [Range Access and Detection Traits](range-access-and-detection-traits.md) `range-access-and-detection-traits` · 9 unit(s)
- [Range Formatter Specializations](range-formatter-specializations.md) `range-formatter-specializations` · 6 unit(s)

**Depends on.**

- [Compiled Formatting Engine](compiled-formatting-engine.md) · graph-confirmed · 5 edge(s) · range-and-tuple-formatting depends on compiled-formatting-engine for formatting range and tuple elements.

Parent: [fmt Formatting Library](fmt-formatting-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
