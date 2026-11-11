# Pointer and Patch Engine

**Capability.** Implements RFC 6901 JSON Pointer resolution, RFC 6902 patch application, and deep comparison and sorting used by patch semantics.

Come here when working with JSON Pointers or applying patches to documents. Pointer resolution locates targets, patch application dispatches operations, and sorting/deep comparison supports deterministic and equality-based behavior.

**Children.**

- [JSON Pointer resolution](json-pointer-resolution.md) `json-pointer-resolution` · 9 unit(s)
- [Sorting and deep comparison](sorting-and-deep-comparison.md) `sorting-and-deep-comparison` · 6 unit(s)
- [JSON Patch application](json-patch-application.md) `json-patch-application` · 6 unit(s)

**Depends on.**

- [Item Utility Toolkit](item-utility-toolkit.md) · graph-confirmed · 5 edge(s)
- [JSON Patch generation](json-patch-generation.md) · graph-confirmed · 8 edge(s)
- [Node construction and linking](node-construction-and-linking.md) · graph-confirmed · 5 edge(s)
- [Object membership and merge patch](object-membership-and-merge-patch.md) · graph-confirmed · 4 edge(s)

**Depended on by.**

- [Item Utility Toolkit](item-utility-toolkit.md) · graph-confirmed · 2 edge(s)
- [JSON Patch generation](json-patch-generation.md) · graph-confirmed · 6 edge(s) · Patch generation computes pointer paths and reuses engine helpers when emitting diff operations.
- [Object membership and merge patch](object-membership-and-merge-patch.md) · graph-confirmed · 8 edge(s)

Parent: [cJSON JSON Library](cjson-json-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
