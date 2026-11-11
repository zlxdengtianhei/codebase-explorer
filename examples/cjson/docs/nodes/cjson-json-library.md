# cJSON JSON Library

**Capability.** Parses, builds, prints, and manipulates JSON data as cJSON trees, plus RFC 6901/6902/7396 pointer, patch, and merge-patch support.

Come here for the whole cJSON system: the public API, node construction, parsing, printing, and item utilities. The pointer/patch engine group handles RFC 6901/6902 operations, while the remaining children cover construction, parsing, serialization, membership edits, merge patch, and patch generation.

**Children.**

- [Item Utility Toolkit](item-utility-toolkit.md) `item-utility-toolkit` · 26 unit(s)
- [Pointer and Patch Engine](pointer-and-patch-engine.md) `pointer-and-patch-engine` · 21 unit(s)
- [Node construction and linking](node-construction-and-linking.md) `node-construction-and-linking` · 15 unit(s)
- [Public header declarations](public-header-declarations.md) `public-header-declarations` · 14 unit(s)
- [JSON parser](json-parser.md) `json-parser` · 9 unit(s)
- [JSON printing and serialization](json-printing-and-serialization.md) `json-printing-and-serialization` · 8 unit(s)
- [Object membership and merge patch](object-membership-and-merge-patch.md) `object-membership-and-merge-patch` · 7 unit(s)
- [JSON Patch generation](json-patch-generation.md) `json-patch-generation` · 7 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
