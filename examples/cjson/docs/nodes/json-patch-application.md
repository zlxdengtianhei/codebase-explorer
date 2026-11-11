# JSON Patch application

**Capability.** Applies RFC 6902 JSON Patch operation arrays to a target object, dispatching per-operation semantics.

This module decodes patch operation objects and applies add/remove/replace-style operations sequentially, aborting on the first failure with a status code. It also contains the cJSON_Is* type predicates shared by both files.

**Depends on.**

- [JSON Pointer resolution](json-pointer-resolution.md) · graph-confirmed · 8 edge(s) · Patch application resolves each operation's JSON Pointer path to locate its target.
- [Sorting and deep comparison](sorting-and-deep-comparison.md) · graph-confirmed · 1 edge(s) · Patch application uses deep comparison to evaluate test operations.
- [JSON Patch generation](json-patch-generation.md) · graph-only · 6 edge(s)
- [Node construction and linking](node-construction-and-linking.md) · graph-only · 4 edge(s)
- [Duplication and replacement](duplication-and-replacement.md) · graph-only · 3 edge(s)
- [Object membership and merge patch](object-membership-and-merge-patch.md) · graph-only · 3 edge(s)
- [Comparison and lookup helpers](comparison-and-lookup-helpers.md) · graph-only · 2 edge(s)

**Depended on by.**

- [JSON Pointer resolution](json-pointer-resolution.md) · graph-confirmed · 4 edge(s)
- [Object membership and merge patch](object-membership-and-merge-patch.md) · graph-only · 5 edge(s)
- [Core item manipulation utilities](core-item-manipulation-utilities.md) · graph-only · 2 edge(s)
- [JSON Patch generation](json-patch-generation.md) · graph-only · 2 edge(s)

Parent: [Pointer and Patch Engine](pointer-and-patch-engine.md)

## Units (6)

<a id="u-59f98e7e5505"></a>
### `apply_patch`

`static int apply_patch(cJSON *object, const cJSON *patch, const cJSON_bool case_sensi…` · [cJSON_Utils.c:L807-L1036][f1]

Applies a single JSON Patch operation to an object, returning 0 on success or a distinct positive status code per failure.

It reads "path" (must be a string, else 2) and decodes "op" (invalid, else 3). TEST compares the item at path with the patch's "value" via compare_json and returns 1 on mismatch. An empty path targets the root: REMOVE overwrites the object with an invalid node (status 0); ADD/REPLACE require "value" (missing → 7), duplicate it (OOM → 8), overwrite the root in place, free the duplicated wrapper and the root's key string. REMOVE/REPLACE on non-root paths detach via detach_path (failure → 13) and delete the old item; REMOVE then finishes. MOVE/COPY read "from" (must be a string, else 4); MOVE detaches the source (failure → 5), COPY resolves then duplicates it (OOM → 6). ADD/REPLACE otherwise duplicate "value" (missing → 7, OOM → 8). The path is then split at the last '/' into parent and child; the parent is resolved and child escapes decoded. Failure to find the parent, a missing '/', or a non-container parent yields 9. For an array parent, child "-" appends; otherwise a decimal index is decoded (failure → 11) and insert_item_in_array applied (failure → 10). For an object parent, the existing member with that key is deleted (case-sensitively per flag) and the value added. Cleanup deletes any unconsumed value and frees the path copy. Note: if cJSONUtils_strdup of the path fails, parent_pointer stays NULL and get_item_from_pointer is called with a NULL pointer, yielding status 9 rather than an OOM code.

<a id="u-c5c112b4e69b"></a>
### `decode_patch_operation`

`static enum patch_operation decode_patch_operation(const cJSON * const patch, const c…` · [cJSON_Utils.c:L742-L781][f1]

Decodes the "op" member of a patch object into the patch_operation enum.

Returns INVALID if the member is missing or not a string; otherwise maps the exact strings "add", "remove", "replace", "move", "copy", "test" to their enum values, and anything else to INVALID.

<a id="u-35776a4e0540"></a>
### `cJSON_Utils.c:get_object_item`

`static cJSON *get_object_item(const cJSON * const object, const char* name, const cJS…` · [cJSON_Utils.c:L730-L738][f1]

Looks up a named member of an object, dispatching to cJSON_GetObjectItemCaseSensitive or cJSON_GetObjectItem depending on the flag.

<a id="u-6f8d816b150a"></a>
### `overwrite_item`

`static void overwrite_item(cJSON * const root, const cJSON replacement)` · [cJSON_Utils.c:L784-L805][f1]

Replaces the contents of a cJSON node in place with a shallow copy of a replacement value, freeing the node's old string, valuestring, and entire child subtree first.

NULL root is a no-op. The replacement is memcpy'd, so the caller must ensure the replacement's fields (e.g. its string) are not shared or are managed separately; apply_patch frees object->string afterwards to drop an inherited key.

<a id="u-533c658ff3f4"></a>
### `cJSON.c-type-predicates`

`CJSON_PUBLIC(cJSON_bool) cJSON_IsInvalid(const cJSON * const item)` · [cJSON.c:L2972-L2980][f2]

A family of cJSON_Is* checks that return false for a NULL item and otherwise compare the item's low type byte against the specific type, except cJSON_IsBool, which is true when either the True or False bit is set.

cJSON_IsInvalid matches cJSON_Invalid.

<a id="u-977256d8365f"></a>
### `cJSON_Utils.c-applypatches-entry-points`

`CJSON_PUBLIC(int) cJSONUtils_ApplyPatches(cJSON * const object, const cJSON * const p…` · [cJSON_Utils.c:L1038-L1065][f1]

Apply a JSON Patch (an array of operation objects) to a target in sequence, returning 0 on full success, 1 if the patches argument is not an array, or the first nonzero status from apply_patch, aborting remaining operations at that point.

The plain version is case-insensitive, the CaseSensitive variant case-sensitive; both tolerate a NULL patches value only insofar as cJSON_IsArray(NULL) is false, returning 1.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.c
[f2]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c
