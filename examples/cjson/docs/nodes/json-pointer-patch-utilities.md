# JSON Pointer Patch Utilities

**Capability.** Provides JSON Pointer resolution, patch generation/application, merge-patch, sorting, and structural comparison helpers.

Use this module for cJSON_Utils operations that locate, compare, sort, and transform JSON trees. It includes pointer token handling, patch construction/application, merge patch, and tree equality helpers.

**Depends on.**

- [Item Creation and Lifecycle](item-creation-and-lifecycle.md) · graph-confirmed · 28 edge(s) · JSON Pointer and patch utilities use item creation and lifecycle helpers when constructing or changing nodes.
- [Public Utility API and Mutators](public-utility-api-and-mutators.md) · graph-confirmed · 5 edge(s) · JSON Pointer and patch utilities use public utility mutators and lookup helpers for object and array operations.

**Depended on by.**

- [Core JSON Parse and Print](core-json-parse-and-print.md) · graph-confirmed · 3 edge(s)
- [Public Utility API and Mutators](public-utility-api-and-mutators.md) · graph-confirmed · 5 edge(s) · Public utility API and mutators use JSON Pointer and patch utilities for merge-patch wrappers.

Parent: [cJSON JSON Library](cjson-json-library.md)

## Units (25)

<a id="u-394cc13a634e"></a>
### `cJSONUtils_FindPointerFromObjectTo`

`CJSON_PUBLIC(char *) cJSONUtils_FindPointerFromObjectTo(const cJSON * const object, c…` · [cJSON_Utils.c:L198-L259][f1]

Builds a JSON pointer from an ancestor object to a descendant target by recursive child search.

- NULL input or target not found: NULL.
- Ancestor equals target: allocated empty string.
- Array ancestor: prepend slash plus decimal child index.
- Object ancestor: prepend slash plus the child key escaped as a pointer token.
- Found target under a non-container leaf: free partial pointer and return NULL.
Searches children in list order and returns the first path. Array index overflow beyond ULONG_MAX aborts with NULL after freeing temporaries. Allocation failures are not consistently checked before formatting.

<a id="u-d0535f9d8f45"></a>
### `cJSONUtils_strdup`

`static unsigned char* cJSONUtils_strdup(const unsigned char* const string)` · [cJSON_Utils.c:L66-L80][f1]

Allocates a NUL-terminated copy of a byte string using the project allocator.

Returns NULL if allocation fails; otherwise copies length plus terminator. It does not check for a NULL input before strlen and memcpy, so that input is outside its handled boundary.

<a id="u-e92617c961f5"></a>
### `cJSON_Utils.c:compare_double`

`static cJSON_bool compare_double(double a, double b)` · [cJSON_Utils.c:L112-L116][f1]

Tests floating-point equality within a relative epsilon.

Computes max absolute operand, then returns whether absolute difference is at most that max times DBL_EPSILON. Both zero compare equal; NaN operands make the comparison false.

<a id="u-5316b1a86a7c"></a>
### `compare_json`

`static cJSON_bool compare_json(cJSON *a, cJSON *b, const cJSON_bool case_sensitive)` · [cJSON_Utils.c:L604-L690][f1]

Compares two cJSON trees for structural equality, optionally folding object-key case.

- NULL operand or differing low-byte type: false.
- Numbers: compare integer and epsilon-double values.
- Strings: case-sensitive strcmp regardless of the flag.
- Arrays: compare children in order and require equal length.
- Objects: sort both in place, compare keys with the flag, recurse, and require equal length.
- Other same-type values, including null and booleans: true.
Sorting mutates both object trees.

<a id="u-47610f0b20bf"></a>
### `compare_pointers`

`static cJSON_bool compare_pointers(const unsigned char *name, const unsigned char *po…` · [cJSON_Utils.c:L120-L154][f1]

Matches one JSON-pointer path token against an object key, honoring ~0 and ~1 escapes and optional case folding.

- NULL operand: false.
- Invalid escape: false.
- Character mismatch: false.
- One side ends before the other: false.
A token ends at NUL or slash; case-sensitive mode uses exact bytes, otherwise tolower.

<a id="u-53f8c3ba705f"></a>
### `compare_strings`

`static int compare_strings(const unsigned char *string1, const unsigned char *string2…` · [cJSON_Utils.c:L83-L109][f1]

Compares two byte strings with optional case folding and treats any NULL operand as unequal.

- Either pointer NULL: return 1.
- Identical pointers: return 0.
- Case-sensitive: return strcmp result.
- Case-insensitive: scan with tolower until terminator, returning 0 if both end together, otherwise the tolower difference.
Because NULL returns 1 even for two NULLs, callers cannot use it as a total order for missing keys.

<a id="u-338db4acac6e"></a>
### `decode_array_index_from_pointer`

`static cJSON_bool decode_array_index_from_pointer(const unsigned char * const pointer…` · [cJSON_Utils.c:L274-L299][f1]

Parses a decimal array index from the start of a pointer token.

- Leading zero unless token is exactly 0 or followed by slash: reject.
- Non-digit before NUL or slash: reject.
- Empty token: accepted as index 0.
- Overflow: not checked.
Writes the parsed size_t on success.

<a id="u-4989d0e4e216"></a>
### `decode_pointer_inplace`

`static void decode_pointer_inplace(unsigned char *string)` · [cJSON_Utils.c:L359-L390][f1]

Decodes ~0 and ~1 escapes in place in a mutable pointer token.

- NULL input: return immediately.
- ~0: write tilde.
- ~1: writes slash at the next decoded byte rather than the current one, so the result is not the standard decoded token.
- Invalid escape: return early without writing the final NUL terminator.
Ordinary bytes are left in place; the final terminator is written only after a complete scan.

<a id="u-176ca4b8e125"></a>
### `detach_item_from_array`

`static cJSON *detach_item_from_array(cJSON *array, size_t which)` · [cJSON_Utils.c:L393-L427][f1]

Detaches the zero-based child from an array-like cJSON list and returns it, or NULL if the position does not exist.

It unlinks the node from the doubly linked list, updates the head and tail links, and clears the detached node's next and prev pointers. The array argument is dereferenced without a NULL check.

<a id="u-04ebfb069f1f"></a>
### `detach_path`

`static cJSON *detach_path(cJSON *object, const unsigned char *path, const cJSON_bool …` · [cJSON_Utils.c:L430-L481][f1]

Splits a path at its last slash, resolves the parent, and detaches the final child.

- Copy failure, no slash, parent resolution failure, non-container parent, invalid array index, or absent child: NULL.
- Array parent: detach by decoded index.
- Object parent: detach with the case-insensitive object detach call, so the case-sensitivity flag affects only parent resolution.
Frees the temporary path copy.

<a id="u-090f135fbb3f"></a>
### `encode_string_as_pointer`

`static void encode_string_as_pointer(unsigned char *destination, const unsigned char …` · [cJSON_Utils.c:L173-L196][f1]

Writes a JSON-pointer-escaped copy of a source string into caller-provided storage.

Slash becomes ~1, tilde becomes ~0, other bytes are copied, and a NUL terminator is appended. No bounds checking is performed.

<a id="u-644c521c4779"></a>
### `cJSON_Utils.c:get_array_item`

`static cJSON *get_array_item(const cJSON *array, size_t item)` · [cJSON_Utils.c:L262-L272][f1]

Returns the child at a zero-based position in an array-like cJSON list by walking next links.

A NULL array or an index past the end yields NULL; no bounds or type check is performed.

<a id="u-b2bc4833482f"></a>
### `insert_item_in_array`

`static cJSON_bool insert_item_in_array(cJSON *array, size_t which, cJSON *newitem)` · [cJSON_Utils.c:L693-L728][f1]

Inserts a new item before the zero-based position in an array-like cJSON list.

- Position equals current length: append via the array add helper.
- Position beyond end: return false without inserting.
- Position zero: update head.
- Other position: link after previous node.
Returns true on success and mutates the list.

<a id="u-6f8d816b150a"></a>
### `overwrite_item`

`static void overwrite_item(cJSON * const root, const cJSON replacement)` · [cJSON_Utils.c:L784-L805][f1]

Replaces a cJSON node's contents with a supplied struct value, freeing the old owned string, value string, and child tree first.

A NULL root is ignored. The function then copies the replacement struct over the root, transferring ownership of the replacement's pointers; it does not free the root node itself.

<a id="u-4023d70cec38"></a>
### `pointer_encoded_length`

`static size_t pointer_encoded_length(const unsigned char *string)` · [cJSON_Utils.c:L157-L170][f1]

Computes the encoded length of a string as a JSON-pointer token, counting one extra byte for each tilde or slash.

It excludes the terminating NUL and assumes a non-NULL input.

<a id="u-2d1cb7e0ee82"></a>
### `cJSON.c-cjson-malloc`

`CJSON_PUBLIC(void *) cJSON_malloc(size_t size)` · [cJSON.c:L3197-L3200][f2]

Allocation wrappers.

The malloc wrapper delegates to the global allocate hook. The free wrapper delegates to the global deallocate hook and then clears its local pointer copy, which does not affect the caller's pointer.

<a id="u-27623c3e6c1b"></a>
### `cJSON.c-duplication`

`CJSON_PUBLIC(cJSON *) cJSON_Duplicate(const cJSON *item, cJSON_bool recurse)` · [cJSON.c:L2784-L2787][f2]

Duplicates a cJSON tree.

The public wrapper starts recursion at depth zero. The recursive worker returns NULL for a NULL item or allocation failure. It copies type without the reference flag, integer and double values, duplicates valuestring when present, and duplicates string when present unless the constant-string flag is set, in which case it shares the pointer. Without recursion it returns the new item. With recursion it walks the child chain, fails when depth reaches the circular limit, recursively duplicates each child, links them, and sets the child tail pointer. Any failure deletes the partial copy and returns NULL.

<a id="u-533c658ff3f4"></a>
### `cJSON.c-type-predicates`

`CJSON_PUBLIC(cJSON_bool) cJSON_IsInvalid(const cJSON * const item)` · [cJSON.c:L2972-L2980][f2]

Type predicates.

Each returns false for a NULL item. The specific predicates compare the low byte of the type to invalid, false, true, null, number, string, array, object, or raw. The bool predicate returns true when either the true or false bit is set.

<a id="u-015368511c69"></a>
### `cJSON_Utils.c-merge-patch-generation`

`static cJSON *generate_merge_patch(cJSON * const from, cJSON * const to, const cJSON_…` · [cJSON_Utils.c:L1395-L1475][f1]

Generates a merge patch that would transform from into to; public wrappers choose case-insensitive or case-sensitive top-level handling.

- NULL to: return a null patch.
- Either input not an object: return a deep duplicate of to, even when the inputs are equal.
- Two objects: sort both, then walk keys; from-only keys add null, to-only keys add a duplicate, and common keys add a recursive patch only when comparison finds a difference.
Key matching uses strcmp, so case-insensitive mode still treats keys differing only by case as distinct. The recursive call uses the case-insensitive public wrapper, so nested common keys are not case-sensitive even from the case-sensitive entry point. If no patch members are produced, the empty patch is deleted and NULL is returned.

<a id="u-23ac1a30a937"></a>
### `cJSON_Utils.c-object-sorting`

`static cJSON *sort_list(cJSON *list, const cJSON_bool case_sensitive)` · [cJSON_Utils.c:L484-L593][f1]

Sorts a cJSON child list by key using recursive merge sort; public wrappers sort objects case-insensitively or case-sensitively.

- NULL or single-node list: returned unchanged.
- Already strictly increasing list: left unchanged.
- Merge: choose first sublist only when comparator is negative, otherwise choose second.
- NULL key: comparator returns 1, so NULL is not consistently ordered as greater; placement depends on which sublist is second.
- Equal keys: second sublist is chosen first.
The sort mutates next and prev links and returns the new head; the object wrapper assigns that head to the object's child pointer and returns immediately for a NULL object.

<a id="u-a83c7fb55263"></a>
### `cJSON_Utils.c-patch-application`

`static int apply_patch(cJSON *object, const cJSON *patch, const cJSON_bool case_sensi…` · [cJSON_Utils.c:L807-L1036][f1]

Applies one JSON Patch operation to a target tree and returns a status code; public wrappers iterate patches and stop at the first nonzero status.

- Non-array patch list: return 1.
- Missing or non-string path: status 2.
- Invalid op: status 3.
- Test: status 0 when addressed value equals patch value, otherwise 1.
- Root-path remove: overwrite target with an invalid node and succeed.
- Root-path add or replace: require value (7), duplicate it (8), overwrite target, clear root key, succeed.
- Remove or replace: detach and delete old target; missing target gives 13; remove stops successfully, replace continues.
- Move or copy: require string from (4), resolvable source (5), and for copy a successful duplicate (6).
- Add or replace: require value (7) and successful duplicate (8).
- Final path split: missing parent or child gives 9.
- Array parent with child -: append.
- Array parent with other child: invalid index gives 11; out-of-range insert gives 10.
- Object parent: delete existing key using selected case mode, then add new value.
- Other parent: status 9.
Cleanup deletes an unconsumed value and frees the temporary path. The operation is not transactional: earlier detach or delete changes can remain when a later step fails.

<a id="u-aebd83aa2676"></a>
### `cJSON_Utils.c-patch-composition`

`static void compose_patch(cJSON * const patches, const unsigned char * const operatio…` · [cJSON_Utils.c:L1096-L1134][f1]

Builds a patch object and appends it to a patch array; the public wrapper supplies no suffix.

- NULL patch array, operation, or path: return without action.
- Patch object creation failure: return without action.
- Suffix NULL: add path directly.
- Suffix non-NULL: append slash plus pointer-escaped suffix.
- Value non-NULL: add a deep duplicate; value NULL: omit the value field.
Allocation and add failures are not checked.

<a id="u-c1c23171a074"></a>
### `cJSON_Utils.c-patch-generation`

`static void create_patches(cJSON * const patches, const unsigned char * const path, c…` · [cJSON_Utils.c:L1141-L1279][f1]

Recursively compares from and to trees and appends JSON Patch operations; public wrappers create the array and choose case-insensitive or case-sensitive key handling.

- NULL from or to: no patches.
- Differing low-byte types: emit replace.
- Numbers: emit replace when integer or epsilon-double values differ.
- Strings: emit replace when strcmp differs.
- Arrays: compare common positions recursively; leftover from elements emit remove; leftover to elements emit add. The leftover-from loop does not increment its index, so all such removes use the same index. Index overflow beyond ULONG_MAX aborts the current array walk.
- Objects: sort both in place, then merge by key; equal keys recurse, from-only keys emit remove, to-only keys emit add.
The public wrappers return NULL if either input is NULL, otherwise return the created array.

<a id="u-677e2123ffca"></a>
### `cJSON_Utils.c-patch-operation-decoding`

`static cJSON *get_object_item(const cJSON * const object, const char* name, const cJS…` · [cJSON_Utils.c:L730-L738][f1]

Looks up a patch field with the selected key-case mode and decodes the operation name.

- Lookup delegates to case-sensitive or case-insensitive cJSON object access.
- Operation value not a string: INVALID.
- Exact lowercase add, remove, replace, move, copy, or test: corresponding opcode.
- Missing or unknown value: INVALID.
Operation-name matching itself is always case-sensitive.

<a id="u-3ae8925204a7"></a>
### `cJSON_Utils.c-pointer-lookup`

`static cJSON *get_item_from_pointer(cJSON * const object, const char * pointer, const…` · [cJSON_Utils.c:L301-L346][f1]

Resolves a slash-separated JSON pointer against an object or array, returning the addressed node or NULL; public wrappers select case-insensitive or case-sensitive key matching.

- NULL pointer: NULL.
- Pointer not starting with slash: return starting node unchanged.
- Array token: require a decodable index.
- Object token: scan children for the first key matching the token with pointer escapes.
- Non-container: NULL.
After a token it skips to the next slash or NUL. A trailing slash on an array is decoded as index 0, while on an object it fails to match.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.c
[f2]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c
