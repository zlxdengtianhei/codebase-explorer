# Wide character formatting

**Capability.** Provides format, print, and format_to entry points for wchar_t and other exotic character types, including locale-aware variants.

Come here for wide-string formatting APIs. The core child holds the main wide entry points, the convenience child offers user-facing wrappers, and the exotic child covers character types beyond char and wchar_t.

**Children.**

- [Wide-character formatting core](wide-character-formatting-core.md) `wide-character-formatting-core` · 16 unit(s)
- [Wide convenience formatting API](wide-convenience-formatting-api.md) `wide-convenience-formatting-api` · 8 unit(s)
- [Exotic character formatting](exotic-character-formatting.md) `exotic-character-formatting` · 7 unit(s)

Parent: [Wide text and styling](wide-text-and-styling.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
