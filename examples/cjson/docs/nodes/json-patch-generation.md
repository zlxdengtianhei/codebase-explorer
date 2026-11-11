# JSON Patch generation

**Capability.** Diffs two cJSON trees and emits RFC 6902 JSON Patch operations with escaped pointer paths.

Come here to generate patches: recursive tree diffing, per-operation patch object construction, pointer path computation, and escaping. cJSON-compatible malloc/free forwarding also resides here.

**Depends on.**

- [Item Utility Toolkit](item-utility-toolkit.md) · graph-confirmed · 1 edge(s)
- [Node construction and linking](node-construction-and-linking.md) · graph-confirmed · 7 edge(s)
- [Object membership and merge patch](object-membership-and-merge-patch.md) · graph-confirmed · 4 edge(s)
- [Pointer and Patch Engine](pointer-and-patch-engine.md) · graph-confirmed · 6 edge(s) · Patch generation computes pointer paths and reuses engine helpers when emitting diff operations.
- [Sorting and deep comparison](sorting-and-deep-comparison.md) · graph-only · 4 edge(s)
- [JSON Patch application](json-patch-application.md) · graph-only · 2 edge(s)
- [Duplication and replacement](duplication-and-replacement.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Item Utility Toolkit](item-utility-toolkit.md) · graph-confirmed · 2 edge(s)
- [Pointer and Patch Engine](pointer-and-patch-engine.md) · graph-confirmed · 8 edge(s)
- [JSON Patch application](json-patch-application.md) · graph-only · 6 edge(s)
- [Duplication and replacement](duplication-and-replacement.md) · graph-only · 2 edge(s)
- [JSON Pointer resolution](json-pointer-resolution.md) · graph-only · 2 edge(s)

Parent: [cJSON JSON Library](cjson-json-library.md)

## Units (7)

<a id="u-394cc13a634e"></a>
### `cJSONUtils_FindPointerFromObjectTo`

`CJSON_PUBLIC(char *) cJSONUtils_FindPointerFromObjectTo(const cJSON * const object, c…` · [cJSON_Utils.c:L198-L259][f1]

Finds the JSON pointer string from an object to a target node, returning a malloc'd string the caller must free.

Returns NULL if either argument is NULL or the target is not found. If object==target returns a strdup'd empty string. Otherwise it recursively searches each child; on a hit, if the object is an array it prefixes '/<index>' (rejecting child_index > ULONG_MAX by freeing and returning NULL), if an object it prefixes '/' plus the pointer-encoded child key, and if neither (a scalar leaf) it frees the partial pointer and returns NULL. Allocation failures are not checked for the array/object full_pointer paths, so a NULL deref is possible under OOM.

<a id="u-d0535f9d8f45"></a>
### `cJSONUtils_strdup`

`static unsigned char* cJSONUtils_strdup(const unsigned char* const string)` · [cJSON_Utils.c:L66-L80][f1]

Duplicates a NUL-terminated string into cJSON's allocator.

Returns NULL when allocation fails; otherwise returns a heap copy of length strlen+1 bytes.

<a id="u-60447c860ede"></a>
### `create_patches`

`static void create_patches(cJSON * const patches, const unsigned char * const path, c…` · [cJSON_Utils.c:L1141-L1279][f1]

Recursively diffs two cJSON trees and emits JSON Patch operations into the patches array.

NULL on either side is a no-op. Differing types emit a single "replace" with the 'to' value. Numbers diff on valueint or compare_double; strings on strcmp; both emit "replace" on mismatch. Arrays: a buffer for element paths is allocated (unchecked for NULL); common elements are recursed with path '/<index>' (aborting silently if index exceeds ULONG_MAX); leftover 'from' elements emit "remove" with the index as suffix; leftover 'to' elements each emit "add" with suffix "-". Objects: both are sorted in place (side effect), then a merge-like walk over sorted keys — key only in 'from' emits "remove", only in 'to' emits "add" with the 'to' value, common keys recurse with the pointer-encoded key appended. Other scalar types produce no patches.

<a id="u-9fde835abe67"></a>
### `cJSON.c-hook-exposed-allocation`

`CJSON_PUBLIC(void *) cJSON_malloc(size_t size)` · [cJSON.c:L3197-L3200][f2]

cJSON_malloc and cJSON_free forward to the current global hooks' allocate/deallocate, letting external code allocate memory with the same allocator cJSON will use to free it.

cJSON_free's NULL-ing of its local pointer has no effect on the caller.

<a id="u-286ed63ce391"></a>
### `cJSON_Utils.c-generatepatches-entry-points`

`CJSON_PUBLIC(cJSON *) cJSONUtils_GeneratePatches(cJSON * const from, cJSON * const to)` · [cJSON_Utils.c:L1281-L1294][f1]

Generate a JSON Patch array transforming 'from' into 'to', returning NULL if either input is NULL, otherwise a new cJSON array filled by create_patches from the root path "".

The plain version is case-insensitive, the CaseSensitive variant case-sensitive; note create_patches' NULL check makes a NULL patches array silently produce nothing.

<a id="u-aebd83aa2676"></a>
### `cJSON_Utils.c-patch-composition`

`static void compose_patch(cJSON * const patches, const unsigned char * const operatio…` · [cJSON_Utils.c:L1096-L1134][f1]

Build one patch object {op, path, value} and append it to a patches array.

compose_patch silently does nothing if patches, operation, or path is NULL or the patch object allocation fails. With a NULL suffix the path is used verbatim; otherwise the path is extended with '/' plus the pointer-encoded suffix. A non-NULL value is deep-duplicated into the patch. cJSONUtils_AddPatchToArray is the public wrapper with no suffix.

<a id="u-221b695a1c43"></a>
### `cJSON_Utils.c-pointer-encoding-helpers`

`static size_t pointer_encoded_length(const unsigned char *string)` · [cJSON_Utils.c:L157-L170][f1]

Compute and produce the JSON-pointer escaped form of a string: '~' becomes ~0 and '/' becomes ~1.

pointer_encoded_length returns the strlen plus one extra per '~' or '/'; encode_string_as_pointer writes the escaped bytes into a caller-supplied buffer assumed large enough (per pointer_encoded_length) and NUL-terminates.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.c
[f2]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c
