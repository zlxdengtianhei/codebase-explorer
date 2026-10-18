# Shared core infrastructure

**Capability.** Generic, transfer-agnostic utilities reused across the whole codebase: a self-contained printf engine and its formatter families, locale-independent case-insensitive string handling, and a debug-checked doubly linked list.

Treat these as leaf dependencies: protocol backends, authentication, progress, and the tool all call into them, but they never call back into consumers. Each child is independent of the others.

**Children.**

- [printf engine \(mprintf\)](r9-mprintf.md) `r9-mprintf` · 0 unit(s)
- [Case-insensitive strings](r9-caseless-strings.md) `r9-caseless-strings` · 4 unit(s)
- [Doubly linked list \(llist\)](r9-linked-list.md) `r9-linked-list` · 14 unit(s)

Parent: [curl codebase](r9-curl-source.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
