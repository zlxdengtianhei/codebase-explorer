# JSON Patch Application (RFC 6902)

**Capability.** Applies an array of patch operations to a document: op classification, per-operation dispatch in apply_patch, path-based detach, array insertion, in-place overwrite, and public ApplyPatches entry points in both case modes.

Use this subtree to trace how add/remove/replace/move/copy/test operations mutate a document. apply_patch depends on pointer resolution for every target lookup, so pointer-layer bugs surface as patch failures.

**Depends on.**

- [Lookup, Predicates & Accessors](core-accessors.md) · graph-confirmed · 11 edge(s) · Patch classification and dispatch test operation types through core type predicates.
- [Tree Construction & Mutation](core-tree-mutation.md) · graph-confirmed · 12 edge(s) · apply_patch mutates documents via core add/detach/delete/duplicate primitives.
- [JSON Pointer \(RFC 6901\)](utils-json-pointer.md) · graph-confirmed · 8 edge(s) · Every patch operation resolves its target path through pointer decoding and get_item_from_pointer.
- [Memory & Shared Support](core-memory-support.md) · graph-only · 6 edge(s)
- [Diff & Merge Patches](utils-diff-merge.md) · graph-only · 1 edge(s)
- [cJSON Utilities \(RFC Layer\)](json-utils.md) · within containment · 2 edge(s) · Patching units are contained within the json-utils subtree and use its internal helpers directly.

**Depended on by.**

- [Diff & Merge Patches](utils-diff-merge.md) · model-inferred · 0 edge(s)

Parent: [cJSON Utilities \(RFC Layer\)](json-utils.md)

## Units (10)

<a id="u-d542cfe663d7"></a>
### `patch_operation`

`enum patch_operation` · [cJSON_Utils.c:L740-L740][f1]

Declares enum patch_operation { INVALID, ADD, REMOVE, REPLACE, MOVE, COPY, TEST } used to classify patch 'op' strings.

<a id="u-59f98e7e5505"></a>
### `apply_patch`

`static int apply_patch(cJSON *object, const cJSON *patch, const cJSON_bool case_sensi…` · [cJSON_Utils.c:L807-L1036][f1]

Applies one JSON Patch operation to object and returns 0 on success or a nonzero code identifying the failure.

A non-string 'path' yields 2; an unrecognized 'op' yields 3. TEST compares the value at the path against the patch 'value' with compare_json and returns the inverted result. For an empty path: REMOVE overwrites the root with a static invalid node; REPLACE/ADD duplicate the patch 'value' (missing value -> 7, duplication failure -> 8), overwrite the root, free the duplicate wrapper, and clear the root's key. REMOVE/REPLACE first detach the old item via detach_path (NULL -> 13), deleting it; REMOVE then finishes. MOVE/COPY require a string 'from' (else 4): MOVE detaches from the source path (NULL -> 5), COPY resolves and deep-duplicates it (duplication failure -> 6). ADD/REPLACE duplicate 'value' (7/8). The path is split at its last '/'; the parent is resolved and the child token decoded. A missing parent or child token yields 9. Arrays: '-' appends via cJSON_AddItemToArray; otherwise a bad index gives 11 and a failed insert gives 10. Objects: the existing key is deleted (case-sensitively or not) then the value added. Any other parent yields 9. Cleanup deletes any unconsumed duplicated value and frees the parent-pointer copy.

calls: [decode_patch_operation](utils-patching.md#u-c5c112b4e69b), [cJSON_Utils.c:get_object_item](utils-patching.md#u-35776a4e0540), [compare_json](utils-diff-merge.md#u-5316b1a86a7c), [overwrite_item](utils-patching.md#u-6f8d816b150a), [detach_path](utils-patching.md#u-04ebfb069f1f), [get_item_from_pointer](utils-json-pointer.md#u-1ab29902a15f), [cJSONUtils_strdup](json-utils.md#u-d0535f9d8f45), [decode_pointer_inplace](utils-json-pointer.md#u-4989d0e4e216), [decode_array_index_from_pointer](utils-json-pointer.md#u-338db4acac6e), [insert_item_in_array](utils-patching.md#u-b2bc4833482f), [add_item_to_array](core-tree-mutation.md#u-16f393dc2dba), [cJSON.c-add-item-wrappers](core-tree-mutation.md#u-1a2121646559), [cJSON_Duplicate_rec](core-tree-mutation.md#u-a1efa4a6ba11)

**Uncertainties.**

- The numeric status codes' meanings beyond the in-file comments are internal only.
- Atomicity: failed operations partway through (e.g. REPLACE after successful detach) leave the earlier mutation in place, as the code has no rollback.

<a id="u-c5c112b4e69b"></a>
### `decode_patch_operation`

`static enum patch_operation decode_patch_operation(const cJSON * const patch, const c…` · [cJSON_Utils.c:L742-L781][f1]

Maps a patch object's 'op' string to a patch_operation value.

Looks up 'op' via get_object_item; if it is not a string, or its value matches none of add/remove/replace/move/copy/test (exact strcmp), INVALID is returned.

<a id="u-04ebfb069f1f"></a>
### `detach_path`

`static cJSON *detach_path(cJSON *object, const unsigned char *path, const cJSON_bool …` · [cJSON_Utils.c:L430-L481][f1]

Detaches and returns the item designated by the last token of a JSON-pointer path.

Copies the path, splits it at the last '/': the prefix resolves the parent via get_item_from_pointer; the suffix is decoded in place. If the parent is an array, the suffix must decode as an index for detach_item_from_array, else cleanup returns NULL; if an object, cJSON_DetachItemFromObject removes by key; any other parent (or strdup failure or no '/' in the path) yields NULL. The copied path is always freed.

calls: [cJSONUtils_strdup](json-utils.md#u-d0535f9d8f45), [get_item_from_pointer](utils-json-pointer.md#u-1ab29902a15f), [decode_pointer_inplace](utils-json-pointer.md#u-4989d0e4e216), [detach_item_from_array](utils-patching.md#u-176ca4b8e125), [cJSON.c-detach-delete-wrappers](core-tree-mutation.md#u-b717b0a176e7)

**Uncertainties.**

- cJSON_DetachItemFromObject matching semantics (case-insensitive) come from cJSON.c, not shown here.

<a id="u-176ca4b8e125"></a>
### `detach_item_from_array`

`static cJSON *detach_item_from_array(cJSON *array, size_t which)` · [cJSON_Utils.c:L393-L427][f1]

Detaches the item at index which from array's child list without freeing it.

Walks which steps; NULL at that point means the item does not exist and NULL is returned. Unlinks the node: adjusts c->prev->next when not first, c->next->prev when a successor exists, updates array->child when it was first, and when it was the last non-first element restores array->child->prev to the new tail. Clears the detached node's prev/next and returns it.

**Notes.**

- side_effect: The returned node is unlinked from the list but still owned by the caller; it is not freed here.

<a id="u-b2bc4833482f"></a>
### `insert_item_in_array`

`static cJSON_bool insert_item_in_array(cJSON *array, size_t which, cJSON *newitem)` · [cJSON_Utils.c:L693-L728][f1]

Inserts newitem at index which in array's child list.

Walks which steps; if which is still positive the index is past the end and it returns 0 without inserting. If the walk landed on NULL it appends via cJSON_AddItemToArray; otherwise it splices newitem before the landed child, updating array->child when inserting at the head. Returns 1 on success.

calls: [add_item_to_array](core-tree-mutation.md#u-16f393dc2dba)

<a id="u-6f8d816b150a"></a>
### `overwrite_item`

`static void overwrite_item(cJSON * const root, const cJSON replacement)` · [cJSON_Utils.c:L784-L805][f1]

Replaces the contents of an existing cJSON node in place.

Returns for NULL root. It frees root->string and root->valuestring when non-NULL, deletes root->child when present, then memcpy-copies the replacement node over root, adopting the replacement's pointers.

calls: [cJSON_Delete](core-tree-mutation.md#u-5ca539d2c8db)

**Uncertainties.**

- Whether the replacement was deep-copied beforehand is caller responsibility; shallow replacement fields would now alias.

<a id="u-35776a4e0540"></a>
### `cJSON_Utils.c:get_object_item`

`static cJSON *get_object_item(const cJSON * const object, const char* name, const cJS…` · [cJSON_Utils.c:L730-L738][f1]

Selects the object lookup variant: cJSON_GetObjectItemCaseSensitive when case_sensitive, else the case-insensitive cJSON_GetObjectItem; returns the found child or NULL.

<a id="u-ce5c3f4c6353"></a>
### `cJSONUtils_ApplyPatches`

`CJSON_PUBLIC(int) cJSONUtils_ApplyPatches(cJSON * const object, const cJSON * const p…` · [cJSON_Utils.c:L1038-L1065][f1]

Applies an array of patches case-insensitively.

Returns 1 if patches is not an array; otherwise iterates patches->child, calling apply_patch per element and returning its nonzero status immediately; returns 0 after all succeed.

calls: [apply_patch](utils-patching.md#u-59f98e7e5505), [cJSON.c-type-predicates](core-accessors.md#u-533c658ff3f4)

<a id="u-0a0192b27e3d"></a>
### `cJSONUtils_ApplyPatchesCaseSensitive`

`CJSON_PUBLIC(int) cJSONUtils_ApplyPatchesCaseSensitive(cJSON * const object, const cJ…` · [cJSON_Utils.c:L1067-L1094][f1]

Case-sensitive variant of cJSONUtils_ApplyPatches: identical loop and return codes, passing case_sensitive=true to apply_patch.

calls: [apply_patch](utils-patching.md#u-59f98e7e5505), [cJSON.c-type-predicates](core-accessors.md#u-533c658ff3f4)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.c