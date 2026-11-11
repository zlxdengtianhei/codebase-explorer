# Wide text and styling

**Capability.** Extends formatting to wide and exotic character types and adds ANSI color and emphasis styling to formatted output.

Come here for non-narrow character formatting and colored text. G11 provides wide/exotic format entry points; the styling child supplies text_style, color types, and styled print functions.

**Children.**

- [Wide character formatting](wide-character-formatting.md) `wide-character-formatting` · 31 unit(s)
- [Text styling and colors](text-styling-and-colors.md) `text-styling-and-colors` · 13 unit(s)

**Depends on.**

- [Core formatting implementation](core-formatting-implementation.md) · graph-confirmed · 3 edge(s) · Wide and styled formatting reuse the core implementation's writing routines for their output paths.
- [Format argument infrastructure](format-argument-infrastructure.md) · graph-confirmed · 1 edge(s)
- [Printf implementation](printf-implementation.md) · graph-confirmed · 1 edge(s)

Parent: [fmt formatting library](fmt-formatting-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
