# Object membership and merge patch

**Capability.** Adds and removes object members, and generates or applies RFC 7396 JSON Merge Patches.

This module covers adding items under object keys, detaching/deleting members by key, and the merge-patch generate/apply operations with case-sensitivity variants. The cJSON_Utils header declaring this API is included.

**Depends on.**

- [Item Utility Toolkit](item-utility-toolkit.md) · graph-confirmed · 7 edge(s)
- [Node construction and linking](node-construction-and-linking.md) · graph-confirmed · 12 edge(s) · Membership edits and merge patch allocate and link new nodes via the constructors.
- [Pointer and Patch Engine](pointer-and-patch-engine.md) · graph-confirmed · 8 edge(s)
- [JSON Patch application](json-patch-application.md) · graph-only · 5 edge(s)
- [Duplication and replacement](duplication-and-replacement.md) · graph-only · 3 edge(s)
- [Sorting and deep comparison](sorting-and-deep-comparison.md) · graph-only · 3 edge(s)
- [Comparison and lookup helpers](comparison-and-lookup-helpers.md) · graph-only · 2 edge(s)
- [Core item manipulation utilities](core-item-manipulation-utilities.md) · graph-only · 2 edge(s)

**Depended on by.**

- [JSON Patch generation](json-patch-generation.md) · graph-confirmed · 4 edge(s)
- [Pointer and Patch Engine](pointer-and-patch-engine.md) · graph-confirmed · 4 edge(s)
- [JSON Patch application](json-patch-application.md) · graph-only · 3 edge(s)
- [JSON Pointer resolution](json-pointer-resolution.md) · graph-only · 1 edge(s)

Parent: [cJSON JSON Library](cjson-json-library.md)

## Units (7)

<a id="u-fc05c0d0ffc4"></a>
### `generate_merge_patch`

`static cJSON *generate_merge_patch(cJSON * const from, cJSON * const to, const cJSON_…` · [cJSON_Utils.c:L1395-L1475][f1]

Generates an RFC 7396 merge patch transforming 'from' into 'to', returning NULL when no changes are needed or on allocation failure.

If 'to' is NULL it returns a null node (delete-everything patch). If either side is not an object, it returns a deep duplicate of 'to'. Otherwise both objects are sorted in place (side effect) and walked in key order: keys only in 'from' get a null entry (removal), keys only in 'to' get a duplicate of the value, and common keys are compared with compare_json — differing values recurse via cJSONUtils_GenerateMergePatch (note: this public wrapper is case-insensitive regardless of the case_sensitive flag, a likely bug), identical values are skipped. If the resulting patch object has no children it is deleted and NULL returned.

<a id="u-a9c96ec5af71"></a>
### `merge_patch`

`static cJSON *merge_patch(cJSON *target, const cJSON * const patch, const cJSON_bool …` · [cJSON_Utils.c:L1321-L1383][f1]

Applies an RFC 7396 merge patch to a target tree, returning the new/updated target (possibly a fresh object) or NULL on allocation failure.

If the patch is not an object, the patch is deep-duplicated first (guarding against the patch being a subtree of target), the old target is deleted, and the duplicate is returned. If the target is not an object it is deleted and replaced by a new object. Then each patch member is applied: a null value deletes the matching key from the target (case-sensitively per flag); otherwise the existing member is detached and merge_patch is applied recursively to it — a NULL result deletes the whole target and returns NULL (propagating failure) — and the result is added under the patch key. The input target is consumed (deleted or mutated) even on failure paths.

<a id="u-6066e0ad6abd"></a>
### `cJSON.c-object-add-wrappers`

`CJSON_PUBLIC(cJSON_bool) cJSON_AddItemToObject(cJSON *object, const char *string, cJS…` · [cJSON.c:L2119-L2122][f2]

Public wrappers over add_item_to_object: cJSON_AddItemToObject duplicates the key, cJSON_AddItemToObjectCS stores it as a constant (non-owned) key.

<a id="u-64306fcf4538"></a>
### `cJSON.c-object-detach-delete-by-key`

`CJSON_PUBLIC(cJSON *) cJSON_DetachItemFromObject(cJSON *object, const char *string)` · [cJSON.c:L2309-L2314][f2]

Look up a key (insensitive for cJSON_DetachItemFromObject/cJSON_DeleteItemFromObject, sensitive for the CaseSensitive variants) and detach the found item via the pointer routine; the Delete variants then free it.

A missing key yields a NULL detach and a harmless delete.

<a id="u-ccdc2d5dadd0"></a>
### `cJSON_Utils.c-generatemergepatch-entry-points`

`CJSON_PUBLIC(cJSON *) cJSONUtils_GenerateMergePatch(cJSON * const from, cJSON * const…` · [cJSON_Utils.c:L1477-L1480][f1]

Public wrappers generating a merge patch from 'from' to 'to'; the plain version is case-insensitive, the CaseSensitive variant case-sensitive.

Both return NULL when the trees are equal or on failure.

<a id="u-c315f149ff90"></a>
### `cJSON_Utils.c-mergepatch-entry-points`

`CJSON_PUBLIC(cJSON *) cJSONUtils_MergePatch(cJSON *target, const cJSON * const patch)` · [cJSON_Utils.c:L1385-L1388][f1]

Public wrappers applying an RFC 7396 merge patch; the plain version is case-insensitive, the CaseSensitive variant case-sensitive.

Both consume the target and return the merged result or NULL on failure.

<a id="u-2155544b78cf"></a>
### `cJSON_Utils.h-cjson-utils-public-header`

`#define cJSON_Utils__h` · [cJSON_Utils.h:L24-L24][f3]

Declares the cJSON_Utils C API: RFC 6901 JSON Pointer resolution, RFC 6902 JSON Patch generation/application, RFC 7396 JSON Merge Patch, pointer construction, and object sorting.

All functions use the CJSON_PUBLIC macro for linkage and are wrapped in extern "C" for C++ consumers; each case-sensitive variant has a case-insensitive counterpart. Documented contracts from comments: GeneratePatches and GenerateMergePatch sort members of 'from' and 'to' by key (mutating inputs); ApplyPatches returns 0 on success and is explicitly NOT atomic on failure (a comment sketches a duplicate-then-swap atomic wrapper, omitted for performance); MergePatch modifies 'target' and returns a new pointer for it; AddPatchToArray appends an operation/path/value entry to a patch array; FindPointerFromObjectTo builds a JSON Pointer from a root to a target; SortObject alphabetizes object members. Behavior of these declarations is not implemented here; only signatures and comments are observable.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.c
[f2]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c
[f3]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.h
