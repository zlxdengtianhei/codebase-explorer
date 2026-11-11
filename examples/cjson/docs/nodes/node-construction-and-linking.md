# Node construction and linking

**Capability.** Allocates cJSON nodes of every type and links them into arrays and objects, including reference and array-building helpers.

The factory layer of the library: all typed node creators, sibling linking, array append, and reference-copy creation are here. Any code building or growing a tree depends on these constructors.

**Depends on.**

- [Item Utility Toolkit](item-utility-toolkit.md) · graph-confirmed · 3 edge(s)
- [Duplication and replacement](duplication-and-replacement.md) · graph-only · 3 edge(s)

**Depended on by.**

- [Item Utility Toolkit](item-utility-toolkit.md) · graph-confirmed · 5 edge(s) · Item utilities such as duplication and array growth depend on node constructors and linking helpers.
- [JSON parser](json-parser.md) · graph-confirmed · 6 edge(s) · The parser builds trees by calling the typed node constructors and linking helpers.
- [JSON Patch generation](json-patch-generation.md) · graph-confirmed · 7 edge(s)
- [Object membership and merge patch](object-membership-and-merge-patch.md) · graph-confirmed · 12 edge(s) · Membership edits and merge patch allocate and link new nodes via the constructors.
- [Pointer and Patch Engine](pointer-and-patch-engine.md) · graph-confirmed · 5 edge(s)
- [JSON Patch application](json-patch-application.md) · graph-only · 4 edge(s)
- [Duplication and replacement](duplication-and-replacement.md) · graph-only · 3 edge(s)
- [Core item manipulation utilities](core-item-manipulation-utilities.md) · graph-only · 2 edge(s)
- [JSON Pointer resolution](json-pointer-resolution.md) · graph-only · 1 edge(s)

Parent: [cJSON JSON Library](cjson-json-library.md)

## Units (15)

<a id="u-14e9c6b81163"></a>
### `add_item_to_object`

`static cJSON_bool add_item_to_object(cJSON * const object, const char * const string,…` · [cJSON.c:L2082-L2117][f1]

Attaches item to an object under the given key.

It rejects NULL object/string/item or object==item. With constant_key it stores the caller's pointer and ORs cJSON_StringIsConst into the type; otherwise it duplicates the key (allocation failure returns false) and clears the StringIsConst flag. It frees the item's existing owned string (unless StringIsConst) before installing the new key, then delegates to add_item_to_array, so it inherits that function's silent no-attach behavior on a corrupted non-empty list.

<a id="u-32aea1d3eff6"></a>
### `cJSON_CreateNumber`

`CJSON_PUBLIC(cJSON *) cJSON_CreateNumber(double num)` · [cJSON.c:L2505-L2529][f1]

Creates a cJSON_Number node storing the double and saturating valueint to INT_MAX/INT_MIN on overflow, mirroring cJSON_SetNumberHelper; NULL on allocation failure.

<a id="u-5ca539d2c8db"></a>
### `cJSON_Delete`

`CJSON_PUBLIC(void) cJSON_Delete(cJSON *item)` · [cJSON.c:L253-L276][f1]

Recursively frees an item and its whole ->next sibling chain.

For each node it deletes the child subtree and frees valuestring and string unless the cJSON_IsReference (for child/valuestring) or cJSON_StringIsConst (for string) type flags say the memory is not owned; the node itself is always freed. Uses the global hooks, not the item's parse-time hooks.

<a id="u-0840a192aac8"></a>
### `cJSON_New_Item`

`static cJSON *cJSON_New_Item(const internal_hooks * const hooks)` · [cJSON.c:L241-L250][f1]

Internal node constructor: allocates a cJSON via the hooks and, on success, zero-initializes it; returns NULL on allocation failure.

<a id="u-43781263395f"></a>
### `cast_away_const`

`static void* cast_away_const(const void* string)` · [cJSON.c:L2073-L2076][f1]

Compile-warning-suppressed cast of a const pointer to void*, used to store caller-owned constant strings in items.

<a id="u-b24a8e16fef0"></a>
### `create_reference`

`static cJSON *create_reference(const cJSON *item, const internal_hooks * const hooks)` · [cJSON.c:L2006-L2025][f1]

Creates a shallow copy of an item marked cJSON_IsReference: it memcpy's the whole node, clears the string, ORs in the reference flag, and detaches next/prev, so the copy shares the original's valuestring/child memory that cJSON_Delete will not free.

Returns NULL for a NULL item or allocation failure.

<a id="u-5232101599db"></a>
### `suffix_object`

`static void suffix_object(cJSON *prev, cJSON *item)` · [cJSON.c:L1999-L2003][f1]

Links two nodes as siblings: prev->next = item and item->prev = prev; the array tail convention (head->prev = last) is maintained by callers.

<a id="u-1d5a36a9189e"></a>
### `cJSON.c-add-toobject-conveniences`

`CJSON_PUBLIC(cJSON*) cJSON_AddNullToObject(cJSON * const object, const char * const n…` · [cJSON.c:L2150-L2160][f1]

A family of helpers that create a typed child (null, true, false, bool, number, string, raw, object, array) and insert it under name via add_item_to_object with a duplicated key.

Each returns the new child on success; on insertion failure the freshly created child is deleted and NULL is returned, so no leaked node. Creation failures (allocation) also yield NULL.

<a id="u-161afc3fc294"></a>
### `cJSON.c-array-append`

`static cJSON_bool add_item_to_array(cJSON *array, cJSON *item)` · [cJSON.c:L2027-L2058][f1]

Appends item to array's child list in O(1) using the head->prev tail pointer.

It returns false only when item or array is NULL or the array is the item itself. If the list is empty, item becomes the child with item->prev = item (self-tail) and next NULL. If non-empty, it appends via suffix_object on child->prev and updates the tail. Failure surface: when the list is non-empty but child->prev is NULL (a corrupted or externally built list), the else branch does nothing — the item is silently not attached — yet the function still returns true, so callers cannot detect the lost append. cJSON_AddItemToArray is the public wrapper.

<a id="u-6cfae6afd692"></a>
### `cJSON.c-container-creators`

`CJSON_PUBLIC(cJSON *) cJSON_CreateArray(void)` · [cJSON.c:L2598-L2607][f1]

Allocate an empty node typed cJSON_Array or cJSON_Object with a NULL child; NULL on allocation failure.

<a id="u-1609ac37a0b9"></a>
### `cJSON.c-reference-adders`

`CJSON_PUBLIC(cJSON_bool) cJSON_AddItemReferenceToArray(cJSON *array, cJSON *item)` · [cJSON.c:L2130-L2138][f1]

Add a reference copy of an item (via create_reference) into an array or under an object key; they return false on NULL array/object/string or when reference creation fails, and otherwise inherit add_item_to_array/add_item_to_object semantics, including the silent no-attach case for a corrupted array list.

<a id="u-9e21adac3d89"></a>
### `cJSON.c-reference-creators`

`CJSON_PUBLIC(cJSON *) cJSON_CreateStringReference(const char *string)` · [cJSON.c:L2548-L2558][f1]

Create a node of type String/Object/Array ORed with cJSON_IsReference that stores the caller's pointer (cast_away_const) as valuestring or child without copying; cJSON_Delete will not free that memory.

NULL only on allocation failure.

<a id="u-210fb85a3b35"></a>
### `cJSON.c-scalar-creators`

`CJSON_PUBLIC(cJSON *) cJSON_CreateNull(void)` · [cJSON.c:L2461-L2470][f1]

Allocate a node and set its type: cJSON_CreateNull, cJSON_CreateTrue, cJSON_CreateFalse set the literal types, and cJSON_CreateBool picks True or False from the boolean.

All return NULL on allocation failure.

<a id="u-8cd276772310"></a>
### `cJSON.c-string-raw-creators`

`CJSON_PUBLIC(cJSON *) cJSON_CreateString(const char *string)` · [cJSON.c:L2531-L2546][f1]

cJSON_CreateString and cJSON_CreateRaw allocate a node and store a hooks-allocated duplicate of the input as valuestring; if the strdup fails the half-built item is deleted and NULL is returned.

NULL is a valid input to strdup, producing a NULL valuestring.

<a id="u-015550ed4e09"></a>
### `cJSON.c-typed-array-creators`

`CJSON_PUBLIC(cJSON *) cJSON_CreateIntArray(const int *numbers, int count)` · [cJSON.c:L2621-L2659][f1]

Build an array of count elements from a C array of int/float/double/string values: each element is created with the matching creator and linked with suffix_object, with head->prev set to the last element as the tail.

A negative count or NULL input returns NULL; any element-creation failure deletes the partial array and returns NULL. Floats are widened to double via cJSON_CreateNumber.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c
