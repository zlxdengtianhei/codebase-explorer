# Range Formatting

**Capability.** Formats ranges, maps, tuples, strings, container adaptors, and join views, driven by compile-time classification of the range's format kind and element formattability.

Detection traits classify a type; the matching formatter specialization renders it. Join utilities offer separator-based, bracket-free output.

**Children.**

- [Range Detection Traits](ranges-traits.md) `ranges-traits` · 1 unit(s)
- [Range Formatters](ranges-formatters.md) `ranges-formatters` · 6 unit(s)
- [Join Formatting](ranges-join.md) `ranges-join` · 3 unit(s)

Parent: [fmt Formatting Library](fmt-lib.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
