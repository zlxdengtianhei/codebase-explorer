# Item Utility Toolkit

**Capability.** Provides core cJSON item manipulation: detaching, indexing, replacing, comparing, looking up, and duplicating trees.

Come here for generic item-level operations shared across the library. Core manipulation handles structural edits and allocator hooks, comparison helpers handle equality and lookup, and duplication covers copying and replacing trees.

**Children.**

- [Core item manipulation utilities](core-item-manipulation-utilities.md) `core-item-manipulation-utilities` · 15 unit(s)
- [Comparison and lookup helpers](comparison-and-lookup-helpers.md) `comparison-and-lookup-helpers` · 6 unit(s)
- [Duplication and replacement](duplication-and-replacement.md) `duplication-and-replacement` · 5 unit(s)

**Depends on.**

- [JSON Patch generation](json-patch-generation.md) · graph-confirmed · 2 edge(s)
- [JSON printing and serialization](json-printing-and-serialization.md) · graph-confirmed · 3 edge(s)
- [Node construction and linking](node-construction-and-linking.md) · graph-confirmed · 5 edge(s) · Item utilities such as duplication and array growth depend on node constructors and linking helpers.
- [Pointer and Patch Engine](pointer-and-patch-engine.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [JSON parser](json-parser.md) · graph-confirmed · 2 edge(s)
- [JSON Patch generation](json-patch-generation.md) · graph-confirmed · 1 edge(s)
- [JSON printing and serialization](json-printing-and-serialization.md) · graph-confirmed · 1 edge(s) · Serialization uses shared item utilities while walking and rendering trees.
- [Node construction and linking](node-construction-and-linking.md) · graph-confirmed · 3 edge(s)
- [Object membership and merge patch](object-membership-and-merge-patch.md) · graph-confirmed · 7 edge(s)
- [Pointer and Patch Engine](pointer-and-patch-engine.md) · graph-confirmed · 5 edge(s)

Parent: [cJSON JSON Library](cjson-json-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
