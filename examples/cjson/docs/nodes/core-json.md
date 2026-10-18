# Core cJSON Engine

**Capability.** Owns the cJSON data model (doubly linked tree nodes) and its full lifecycle: text-to-tree parsing, tree-to-text printing, structural construction and mutation, typed access and testing, and the memory plumbing shared by all of these.

Use this subtree for anything about the cJSON engine itself. Readers adding features to cJSON.c should check which capability node owns the touched code; consumers outside cJSON.c should rely only on what public-interface declares.

**Children.**

- [Public API & Data Model](core-public-interface.md) `core-public-interface` · 4 unit(s)
- [Memory & Shared Support](core-memory-support.md) `core-memory-support` · 6 unit(s)
- [JSON Text Parsing](core-parsing.md) `core-parsing` · 13 unit(s)
- [JSON Serialization](core-printing.md) `core-printing` · 8 unit(s)
- [Tree Construction & Mutation](core-tree-mutation.md) `core-tree-mutation` · 12 unit(s)
- [Lookup, Predicates & Accessors](core-accessors.md) `core-accessors` · 6 unit(s)
- [Convenience Constructors & Setters](core-constructors.md) `core-constructors` · 5 unit(s)

Parent: [cJSON Library](cjson.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
