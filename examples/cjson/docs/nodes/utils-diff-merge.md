# Diff & Merge Patches

**Capability.** Compares trees and produces RFC 6902 patch arrays or RFC 7396 merge patches transforming one tree into another: deep comparison with tolerance-based doubles, recursive patch emission, merge-patch application and generation, plus their public case-variant wrappers.

Use this subtree to understand how differences between documents are computed and expressed. create_patches and generate_merge_patch sort objects first and depend on pointer encoding for emitted paths, and merge_patch applies patches in place via core mutation calls.

**Depends on.**

- [Tree Construction & Mutation](core-tree-mutation.md) · graph-confirmed · 21 edge(s) · Merge-patch generation and application deep-copy and free subtrees via the core mutation primitives.
- [JSON Pointer \(RFC 6901\)](utils-json-pointer.md) · graph-confirmed · 4 edge(s) · Diff encodes emitted patch paths using pointer-encoding and length helpers.
- [JSON Patch Application \(RFC 6902\)](utils-patching.md) · model-inferred · 0 edge(s)
- [Object Sorting](utils-sorting.md) · graph-confirmed · 6 edge(s) · Comparison and patch generation sort objects first so diff output is deterministic.
- [Convenience Constructors & Setters](core-constructors.md) · graph-only · 10 edge(s)
- [Memory & Shared Support](core-memory-support.md) · graph-only · 8 edge(s)
- [Lookup, Predicates & Accessors](core-accessors.md) · graph-only · 5 edge(s)

**Depended on by.**

- [Object Sorting](utils-sorting.md) · graph-only · 2 edge(s)
- [JSON Patch Application \(RFC 6902\)](utils-patching.md) · graph-only · 1 edge(s)

Parent: [cJSON Utilities \(RFC Layer\)](json-utils.md)

## Units (14)

<a id="u-5316b1a86a7c"></a>
### `compare_json`

`static cJSON_bool compare_json(cJSON *a, cJSON *b, const cJSON_bool case_sensitive)` · [cJSON_Utils.c:L604-L690][f1]

Deep structural comparison of two cJSON trees.

NULL on either side or a mismatched low-byte type returns false. Numbers compare valueint plus compare_double on valuedouble; strings compare with strcmp; arrays compare children pairwise recursively and require equal length; objects first sort both by sort_object, then require equal-length children whose keys match with compare_strings and whose values compare recursively. Any other type (null, true, false) compares equal when types match. Side effect: object comparison reorders both inputs' children.

**Notes.**

- side_effect: Comparing objects sorts both input objects in place, an observable mutation.

calls: [cJSON_Utils.c:compare_double](utils-diff-merge.md#u-e92617c961f5), [sort_object](utils-sorting.md#u-6547cae15f80), [compare_strings](utils-diff-merge.md#u-53f8c3ba705f)

<a id="u-e92617c961f5"></a>
### `cJSON_Utils.c:compare_double`

`static cJSON_bool compare_double(double a, double b)` · [cJSON_Utils.c:L112-L116][f1]

Tolerance-based double comparison: returns true when the absolute difference is within max(|a|,|b|) * DBL_EPSILON, i.e. relative machine-epsilon equality rather than bitwise equality.

**Notes.**

- condition: When both operands are zero, maxVal is 0, so only exactly equal values pass; there is no absolute floor for near-zero comparisons.

<a id="u-53f8c3ba705f"></a>
### `compare_strings`

`static int compare_strings(const unsigned char *string1, const unsigned char *string2…` · [cJSON_Utils.c:L83-L109][f1]

Three-way string comparison used for sorting and key matching.

If either pointer is NULL it returns 1 (NULLs are unequal, never equal). Identical pointers return 0. When case_sensitive it delegates to strcmp; otherwise it walks both strings comparing tolower() of each character, returning 0 on end-of-string agreement or the tolower difference at the first mismatch.

**Uncertainties.**

- Ordering of non-ASCII bytes depends on the tolower locale, which is not established here.

<a id="u-69f40589690a"></a>
### `compose_patch`

`static void compose_patch(cJSON * const patches, const unsigned char * const operatio…` · [cJSON_Utils.c:L1096-L1134][f1]

Appends one patch object {op, path[, value]} to the patches array.

Returns silently if patches, operation, or path is NULL, or if cJSON_CreateObject fails. It always adds the op string; with a NULL suffix the path is added verbatim, otherwise the full path is path + '/' + pointer_encoded encoding of suffix, built in a cJSON_malloc buffer and freed after cJSON_CreateString. A non-NULL value is deep-duplicated into the patch. The patch is appended with cJSON_AddItemToArray.

calls: [pointer_encoded_length](utils-json-pointer.md#u-4023d70cec38), [encode_string_as_pointer](utils-json-pointer.md#u-090f135fbb3f), [add_item_to_array](core-tree-mutation.md#u-16f393dc2dba), [cJSON_Duplicate_rec](core-tree-mutation.md#u-a1efa4a6ba11)

**Uncertainties.**

- Failure of intermediate cJSON_CreateString/AddItemToObject calls is not checked; a partial patch could be appended.

<a id="u-60447c860ede"></a>
### `create_patches`

`static void create_patches(cJSON * const patches, const unsigned char * const path, c…` · [cJSON_Utils.c:L1141-L1279][f1]

Recursively emits JSON Patch operations turning 'from' into 'to'.

NULL inputs return with no patches. Mismatched types emit a single 'replace' of the whole 'to' value. Numbers emit replace when valueint differs or compare_double fails; strings emit replace when strcmp differs. Arrays: corresponding children recurse with '<path>/<index>' paths; leftover 'from' tail elements emit 'remove' with the index as suffix; leftover 'to' tail elements emit 'add' with '-' suffix and the new value. Objects: both sides are sorted, then keys are merged in compare_strings order — equal keys recurse with the escaped key appended to the path; a from-only key emits 'remove'; a to-only key emits 'add' with that child's value. Temporary path buffers are cJSON_malloc'd and freed; index-vs-ULONG_MAX guards free the buffer and abort early.

**Notes.**

- side_effect: Object comparison sorts both from and to in place before diffing.

calls: [compose_patch](utils-diff-merge.md#u-69f40589690a), [sort_object](utils-sorting.md#u-6547cae15f80), [compare_strings](utils-diff-merge.md#u-53f8c3ba705f), [cJSON_Utils.c:compare_double](utils-diff-merge.md#u-e92617c961f5), [encode_string_as_pointer](utils-json-pointer.md#u-090f135fbb3f), [pointer_encoded_length](utils-json-pointer.md#u-4023d70cec38)

**Uncertainties.**

- Array diffing is positional; element moves are emitted as remove/add pairs rather than move operations.

<a id="u-e25b21c18fc7"></a>
### `cJSONUtils_GeneratePatches`

`CJSON_PUBLIC(cJSON *) cJSONUtils_GeneratePatches(cJSON * const from, cJSON * const to)` · [cJSON_Utils.c:L1281-L1294][f1]

Public case-insensitive diff: returns NULL if either tree is NULL, otherwise creates a patches array and fills it via create_patches from the empty root path, returning the array (empty when trees are equal).

calls: [create_patches](utils-diff-merge.md#u-60447c860ede), [cJSON.c-create-basic](core-constructors.md#u-1b58c53937c3)

<a id="u-34c3e0393c64"></a>
### `cJSONUtils_GeneratePatchesCaseSensitive`

`CJSON_PUBLIC(cJSON *) cJSONUtils_GeneratePatchesCaseSensitive(cJSON * const from, cJS…` · [cJSON_Utils.c:L1296-L1309][f1]

Case-sensitive variant of cJSONUtils_GeneratePatches, passing case_sensitive=true to create_patches; same NULL-input and empty-array behavior.

calls: [create_patches](utils-diff-merge.md#u-60447c860ede), [cJSON.c-create-basic](core-constructors.md#u-1b58c53937c3)

<a id="u-4cfbcd96323a"></a>
### `cJSONUtils_AddPatchToArray`

`CJSON_PUBLIC(void) cJSONUtils_AddPatchToArray(cJSON * const array, const char * const…` · [cJSON_Utils.c:L1136-L1139][f1]

Public helper that appends a manually specified patch (operation, path, value) to an array by delegating to compose_patch with no suffix.

calls: [compose_patch](utils-diff-merge.md#u-69f40589690a)

<a id="u-a9c96ec5af71"></a>
### `merge_patch`

`static cJSON *merge_patch(cJSON *target, const cJSON * const patch, const cJSON_bool …` · [cJSON_Utils.c:L1321-L1383][f1]

Applies an RFC 7396 merge patch recursively and returns the merged target.

When patch is not an object, it deep-duplicates the patch first, deletes the old target, and returns the duplicate (duplicating before deleting prevents freeing memory the patch may share with the target). When target is not an object it is deleted and replaced by a fresh object. For each patch child: a null value deletes the key from target (case-sensitively or not); otherwise the existing value at that key is detached and recursively merged, with a NULL recursive result deleting the whole target and propagating NULL; the replacement is added back under the key. Returns the merged target.

calls: [cJSON_Duplicate_rec](core-tree-mutation.md#u-a1efa4a6ba11), [cJSON_Delete](core-tree-mutation.md#u-5ca539d2c8db), [cJSON.c-add-item-wrappers](core-tree-mutation.md#u-1a2121646559), [cJSON.c-type-predicates](core-accessors.md#u-533c658ff3f4)

**Uncertainties.**

- Whether every early-exit path has freed or transferred all detached intermediates cannot be fully verified from this function alone.

<a id="u-fc05c0d0ffc4"></a>
### `generate_merge_patch`

`static cJSON *generate_merge_patch(cJSON * const from, cJSON * const to, const cJSON_…` · [cJSON_Utils.c:L1395-L1475][f1]

Produces an RFC 7396 patch transforming 'from' into 'to', or NULL when they are equal.

A NULL 'to' yields cJSON_CreateNull (delete everything). When either side is not an object, a deep duplicate of 'to' is the patch. Otherwise both objects are sorted, and their children are merged in strcmp key order: a from-only key adds a null entry (removal), a to-only key adds a deep copy (addition), and shared keys recurse via the public cJSONUtils_GenerateMergePatch only when compare_json reports a difference. An empty resulting patch object is deleted and NULL returned; cJSON_CreateObject failure also returns NULL.

**Notes.**

- condition: Key comparison in the merge loop uses case-sensitive strcmp regardless of the case_sensitive flag; the flag only affects compare_json inside recursion and the sort order.

calls: [sort_object](utils-sorting.md#u-6547cae15f80), [compare_json](utils-diff-merge.md#u-5316b1a86a7c), [cJSONUtils_GenerateMergePatch](utils-diff-merge.md#u-cd61e48bebc5), [cJSON_Duplicate_rec](core-tree-mutation.md#u-a1efa4a6ba11), [cJSON.c-create-basic](core-constructors.md#u-1b58c53937c3)

**Uncertainties.**

- NULL from_child->string or to_child->string passed to strcmp is unguarded; behavior there is undefined by this code.

<a id="u-2bad9e619f07"></a>
### `cJSONUtils_MergePatch`

`CJSON_PUBLIC(cJSON *) cJSONUtils_MergePatch(cJSON *target, const cJSON * const patch)` · [cJSON_Utils.c:L1385-L1388][f1]

Public case-insensitive merge patch; returns merge_patch(target, patch, false) directly.

calls: [merge_patch](utils-diff-merge.md#u-a9c96ec5af71)

<a id="u-a2ae16456ec3"></a>
### `cJSONUtils_MergePatchCaseSensitive`

`CJSON_PUBLIC(cJSON *) cJSONUtils_MergePatchCaseSensitive(cJSON *target, const cJSON *…` · [cJSON_Utils.c:L1390-L1393][f1]

Public case-sensitive merge patch; returns merge_patch(target, patch, true) directly.

calls: [merge_patch](utils-diff-merge.md#u-a9c96ec5af71)

<a id="u-cd61e48bebc5"></a>
### `cJSONUtils_GenerateMergePatch`

`CJSON_PUBLIC(cJSON *) cJSONUtils_GenerateMergePatch(cJSON * const from, cJSON * const…` · [cJSON_Utils.c:L1477-L1480][f1]

Public case-insensitive merge-patch generation; returns generate_merge_patch(from, to, false) directly.

calls: [generate_merge_patch](utils-diff-merge.md#u-fc05c0d0ffc4)

<a id="u-41e56f6995e2"></a>
### `cJSONUtils_GenerateMergePatchCaseSensitive`

`CJSON_PUBLIC(cJSON *) cJSONUtils_GenerateMergePatchCaseSensitive(cJSON * const from, …` · [cJSON_Utils.c:L1482-L1485][f1]

Public case-sensitive merge-patch generation; returns generate_merge_patch(from, to, true) directly.

calls: [generate_merge_patch](utils-diff-merge.md#u-fc05c0d0ffc4)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.c