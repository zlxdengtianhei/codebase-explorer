# JSON Pointer resolution

**Capability.** Parses and resolves RFC 6901 JSON Pointer paths against objects and arrays, honoring escape sequences.

This module implements pointer token decoding (~0/~1 escapes, decimal indices) and path traversal to detach, fetch, or insert items at a pointer address. Public case-sensitive and insensitive resolution entry points are provided.

**Depends on.**

- [JSON Patch application](json-patch-application.md) · graph-confirmed · 4 edge(s)
- [JSON Patch generation](json-patch-generation.md) · graph-only · 2 edge(s)
- [Node construction and linking](node-construction-and-linking.md) · graph-only · 1 edge(s)
- [Object membership and merge patch](object-membership-and-merge-patch.md) · graph-only · 1 edge(s)

**Depended on by.**

- [JSON Patch application](json-patch-application.md) · graph-confirmed · 8 edge(s) · Patch application resolves each operation's JSON Pointer path to locate its target.

Parent: [Pointer and Patch Engine](pointer-and-patch-engine.md)

## Units (9)

<a id="u-47610f0b20bf"></a>
### `compare_pointers`

`static cJSON_bool compare_pointers(const unsigned char *name, const unsigned char *po…` · [cJSON_Utils.c:L120-L154][f1]

Compares one path element of a JSON pointer (up to the next '/') against an object key, honoring ~0/~1 escapes.

Returns false if either argument is NULL. During the scan, a '~' in the pointer must be followed by '0' matching '~' in name, or '1' matching '/'; any other escape or character mismatch (case-insensitively when case_sensitive is false, byte-wise otherwise) returns false. After the loop, if exactly one of the two has ended (pointer not at NUL/'/' vs name not at NUL), returns false; otherwise true.

<a id="u-338db4acac6e"></a>
### `decode_array_index_from_pointer`

`static cJSON_bool decode_array_index_from_pointer(const unsigned char * const pointer…` · [cJSON_Utils.c:L274-L299][f1]

Decodes a decimal array index from a pointer token into *index, returning 1 on success and 0 on failure.

Fails if the token has a leading '0' followed by more digits (leading zeros forbidden), or if the digits are terminated by anything other than NUL or '/'. An empty token parses as index 0. Overflow of parsed_index is not detected.

<a id="u-4989d0e4e216"></a>
### `decode_pointer_inplace`

`static void decode_pointer_inplace(unsigned char *string)` · [cJSON_Utils.c:L359-L390][f1]

Decodes ~0 and ~1 escape sequences in place within a single pointer token.

NULL input is ignored. On '~' followed by '0' writes '~' to the decoded position; '~1' writes '/' (note: the code writes to decoded_string[1], which can clobber one byte ahead — an apparent bug); any other character after '~' aborts decoding and returns early, leaving the string partially decoded and NUL-terminated at the current decoded position.

<a id="u-176ca4b8e125"></a>
### `detach_item_from_array`

`static cJSON *detach_item_from_array(cJSON *array, size_t which)` · [cJSON_Utils.c:L393-L427][f1]

Detaches the which-th item from an array's linked list and returns it, or NULL if the index is past the end.

Fixes prev/next links of neighbors, updates array->child when detaching the head, and maintains the tail's prev pointer when detaching the last element; the detached item's prev/next are set to NULL.

<a id="u-04ebfb069f1f"></a>
### `detach_path`

`static cJSON *detach_path(cJSON *object, const unsigned char *path, const cJSON_bool …` · [cJSON_Utils.c:L430-L481][f1]

Detaches the item at a JSON pointer path and returns it, or NULL on any failure.

It strdup's the path (NULL on OOM → NULL), splits at the last '/' into parent and child tokens, resolves the parent with get_item_from_pointer, and decodes escapes in the child token. If the parent is an array it decodes a decimal index (failure → NULL) and calls detach_item_from_array; if an object it calls cJSON_DetachItemFromObject; otherwise NULL. The copied path buffer is always freed before returning.

<a id="u-644c521c4779"></a>
### `cJSON_Utils.c:get_array_item`

`static cJSON *get_array_item(const cJSON *array, size_t item)` · [cJSON_Utils.c:L262-L272][f1]

Returns the item-th child of an array by walking the linked list, or NULL if the array is NULL or the index is past the end.

<a id="u-1ab29902a15f"></a>
### `get_item_from_pointer`

`static cJSON *get_item_from_pointer(cJSON * const object, const char * pointer, const…` · [cJSON_Utils.c:L301-L346][f1]

Resolves a JSON pointer against an object, returning the addressed item or NULL.

NULL pointer input yields NULL. For each '/'-prefixed token: arrays require a valid decimal index (else NULL) resolved via get_array_item; objects scan children comparing keys with compare_pointers (which handles ~0/~1 escapes and case sensitivity); any other node type yields NULL. The token is then skipped up to the next '/' or NUL. A pointer not starting with '/' returns the object itself.

<a id="u-b2bc4833482f"></a>
### `insert_item_in_array`

`static cJSON_bool insert_item_in_array(cJSON *array, size_t which, cJSON *newitem)` · [cJSON_Utils.c:L693-L728][f1]

Inserts newitem into an array at index which, returning 1 on success and 0 if the index is past the end.

Walking stops at the target or the end; if past the end (which>0 remains) it fails; if at the end (child==NULL) it appends via cJSON_AddItemToArray. Otherwise it splices newitem before child, updating array->child when inserting at the head, and fixing prev/next links.

<a id="u-2462c35c7419"></a>
### `cJSON_Utils.c-getpointer-wrappers`

`CJSON_PUBLIC(cJSON *) cJSONUtils_GetPointer(cJSON * const object, const char *pointer)` · [cJSON_Utils.c:L348-L351][f1]

Public entry points resolving a JSON pointer on an object; the plain version is case-insensitive, the CaseSensitive variant compares keys byte-wise.

Both delegate to get_item_from_pointer.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.c
