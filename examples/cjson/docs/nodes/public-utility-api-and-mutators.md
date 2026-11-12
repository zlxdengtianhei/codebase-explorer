# Public Utility API and Mutators

**Capability.** Exposes cJSON utility declarations and provides array/object mutation, lookup, comparison, and merge-patch wrappers.

Come here for public utility API declarations plus core mutation and lookup helpers used by utilities. It includes case-insensitive string comparison, array/object member operations, and merge-patch wrappers.

**Depends on.**

- [Item Creation and Lifecycle](item-creation-and-lifecycle.md) · graph-confirmed · 11 edge(s)
- [JSON Pointer Patch Utilities](json-pointer-patch-utilities.md) · graph-confirmed · 5 edge(s) · Public utility API and mutators use JSON Pointer and patch utilities for merge-patch wrappers.

**Depended on by.**

- [Core JSON Parse and Print](core-json-parse-and-print.md) · graph-confirmed · 2 edge(s)
- [JSON Pointer Patch Utilities](json-pointer-patch-utilities.md) · graph-confirmed · 5 edge(s) · JSON Pointer and patch utilities use public utility mutators and lookup helpers for object and array operations.

Parent: [cJSON JSON Library](cjson-json-library.md)

## Units (7)

<a id="u-dc674c51daff"></a>
### `case_insensitive_strcmp`

`static int case_insensitive_strcmp(const unsigned char *string1, const unsigned char …` · [cJSON.c:L133-L154][f1]

Case-insensitive comparison of two byte strings.

It returns 1 if either pointer is NULL, so two NULL pointers are not equal; returns 0 for the same pointer; otherwise compares lowercased bytes until a difference or the terminating NUL and returns the lowercased byte difference.

<a id="u-1e5753c7e485"></a>
### `cJSON_Utils.h module code (L25–L88)`

`module_region` · [cJSON_Utils.h:L25-L88][f2]

Declares the public cJSON utility API for JSON Pointer, JSON Patch, JSON Merge Patch, pointer construction, and object sorting.

Because only declarations and comments are present, exact runtime behavior is not established; comments state that patch generation sorts members of both inputs, patch application returns 0 on success and is not atomic on failure, merge patch modifies the target and returns a replacement pointer, and sorting orders members alphabetically. Case-sensitive variants are declared alongside default variants. The patch-array helper is described only as a utility for generating patch array entries; append semantics are not stated.

**Notes.**

- failure: ApplyPatches is documented as non-atomic on failure; an atomic wrapper is shown only as commented example code.

**Uncertainties.**

- Header-only declarations: exact error codes, pointer escaping rules, patch operation ordering, and case-sensitivity behavior are not proven by this file.
- The comment for the patch-array helper does not specify whether it appends, replaces, or otherwise mutates the array.

<a id="u-64a0d9ed33a8"></a>
### `cJSON.c-array-accessors`

`CJSON_PUBLIC(int) cJSON_GetArraySize(const cJSON *array)` · [cJSON.c:L1899-L1920][f1]

Array size and item access.

Size returns zero for a NULL array, otherwise counts the child chain and casts to int, with possible overflow. The internal item getter returns NULL for a NULL array, walks next links index times, and returns the reached child or NULL. The public getter returns NULL for a negative index and otherwise delegates.

<a id="u-3b0b66502dc2"></a>
### `cJSON.c-detach-and-delete-items`

`CJSON_PUBLIC(cJSON *) cJSON_DetachItemViaPointer(cJSON *parent, cJSON * const item)` · [cJSON.c:L2258-L2292][f1]

Detaches or deletes array and object members.

Pointer detach returns NULL for NULL parent or item, or when the item is not the first child and has no prev. It unlinks from neighbors, updates the parent child when first, updates the tail pointer when last, clears the item links, and returns the item. Array detach rejects negative indices and otherwise detaches the indexed item. Object detach uses case-insensitive or case-sensitive lookup. Delete variants detach and then delete the result.

<a id="u-0f58250a204b"></a>
### `cJSON.c-insert-and-replace-items`

`CJSON_PUBLIC(cJSON_bool) cJSON_InsertItemInArray(cJSON *array, int which, cJSON *newi…` · [cJSON.c:L2334-L2366][f1]

Inserts and replaces array or object members.

Array insert rejects negative index or NULL new item, appends when the index is past the end, rejects a non-first item with no prev, otherwise links before the found item and updates the child when needed. Pointer replace rejects NULL parent, parent child, replacement, or item; replacing an item with itself succeeds. Otherwise it links the replacement into the item's neighbors, updates the parent child and tail pointer, clears the old item links, deletes it, and returns true. Array replace rejects negative index and delegates. Object replace rejects NULL replacement or key, frees an old non-constant key, duplicates the new key through global hooks, returns false on allocation failure, clears the constant flag, and delegates with case-sensitive or insensitive lookup.

<a id="u-9d23662e76d7"></a>
### `cJSON.c-object-lookup`

`static cJSON *get_object_item(const cJSON * const object, const char * const name, co…` · [cJSON.c:L1951-L1981][f1]

Object member lookup.

The internal lookup returns NULL for a NULL object or name, walks the child chain, and compares names either case-sensitively with strcmp or case-insensitively with the case-insensitive comparator. It returns NULL when no match is found or the matched child has a NULL string, otherwise the child. The public getters select case sensitivity, and the has-item wrapper returns one when lookup is non-NULL and zero otherwise.

<a id="u-215a69823a93"></a>
### `cJSON_Utils.c-merge-patch-application`

`static cJSON *merge_patch(cJSON *target, const cJSON * const patch, const cJSON_bool …` · [cJSON_Utils.c:L1321-L1383][f3]

Applies an RFC 7396-style merge patch to a target and returns the resulting tree; public wrappers choose case-insensitive or case-sensitive key handling.

- Patch not an object: deep-duplicate the patch first, delete the target, return the duplicate.
- Target not an object: delete target and start a new object.
- Patch member null: delete that key from target.
- Patch member non-null: detach existing target member, recursively merge, add replacement under the patch key.
- NULL replacement: delete target and return NULL.
Key lookup and deletion use the selected case mode, but the added key uses the patch spelling. The function mutates and may replace the target pointer.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c
[f2]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.h
[f3]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.c
