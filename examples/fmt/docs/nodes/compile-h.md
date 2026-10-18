# Compile-Time Format Strings

**Capability.** Turns string literals into a tree of compiled format pieces parsed at compile time, exposed through checked format/format_to/print entry points.

Use when a format string is known at compile time and speed matters. Representation nodes describe the piece tree; the parser builds it; entry points consume it.

**Children.**

- [Compiled Piece Representation](compile-repr.md) `compile-repr` · 6 unit(s)
- [Compile-Time Parser](compile-parser.md) `compile-parser` · 3 unit(s)
- [Compiled Format Entry Points](compile-entry.md) `compile-entry` · 6 unit(s)

Parent: [fmt Formatting Library](fmt-lib.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
