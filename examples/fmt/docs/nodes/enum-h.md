# Enum Formatting

**Capability.** Formats enums either as annotated enumerator names (via compile-time identifier tables) or as their underlying value, selected by compile-time predicates.

Annotate an enum with fmt::as_identifiers or fmt::as_underlying; the dispatch predicates pick the formatter specialization and the lookup subtree resolves names at runtime.

**Children.**

- [Enumerator Identifier Lookup](enum-lookup.md) `enum-lookup` · 8 unit(s)
- [Enum Formatter Dispatch](enum-dispatch.md) `enum-dispatch` · 5 unit(s)

Parent: [fmt Formatting Library](fmt-lib.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
