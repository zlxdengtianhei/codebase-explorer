# Convenience Constructors & Setters

**Capability.** Typed value-building layer: basic item constructors, typed array builders, Add*ToObject helpers, and set-value helpers, all composing the mutation primitives into one-call creation APIs.

Use this subtree to create items concisely rather than wiring nodes manually. These units are pure composition over core-tree-mutation and core-memory-support and hold no independent state.

**Depends on.**

- [Memory & Shared Support](core-memory-support.md) · graph-confirmed · 16 edge(s) · Convenience constructors allocate new items and duplicate strings via the central memory/new-item helpers.
- [Tree Construction & Mutation](core-tree-mutation.md) · graph-confirmed · 31 edge(s) · Typed Add helpers install created items into trees through add_item_to_object/add_item_to_array and free on failure via cJSON_Delete.

**Depended on by.**

- [Diff & Merge Patches](utils-diff-merge.md) · graph-only · 10 edge(s)

Parent: [Core cJSON Engine](core-json.md)

## Units (5)

<a id="u-1b58c53937c3"></a>
### `cJSON.c-create-basic`

`CJSON_PUBLIC(cJSON *) cJSON_CreateNull(void)` · [cJSON.c:L2461-L2470][f1]

Basic item constructors.

CreateNull/CreateTrue/CreateFalse/CreateBool/CreateArray/CreateObject allocate one zeroed node via cJSON_New_Item and set the matching type (CreateBool picks True/False from its argument); allocation failure returns NULL. CreateNumber stores valuedouble and saturates valueint to INT_MAX/INT_MIN when out of range. CreateString and CreateRaw strdup their argument; when the strdup fails the item is deleted and NULL returned. CreateStringReference stores the caller's string pointer with type String|IsReference (never freed by cJSON_Delete); CreateObjectReference and CreateArrayReference store the child pointer with the matching type plus IsReference, so the referenced subtree is not owned.

calls: [cJSON_New_Item](core-memory-support.md#u-0840a192aac8), [cJSON_strdup](core-memory-support.md#u-e8a9f7d7fb70)

<a id="u-89d2c24c3f1b"></a>
### `cJSON.c-create-arrays`

`CJSON_PUBLIC(cJSON *) cJSON_CreateIntArray(const int *numbers, int count)` · [cJSON.c:L2621-L2659][f1]

Typed array builders (Int/Float/Double/String).

Each rejects a negative count or NULL input array with NULL, creates an empty array, then loops count times creating number or string items; a per-element creation failure deletes the whole array and returns NULL. Elements are linked with suffix_object, and after the loop the head's prev is pointed at the last element to maintain the tail convention. count == 0 yields an empty (non-NULL) array.

calls: [cJSON.c-create-basic](core-constructors.md#u-1b58c53937c3)

<a id="u-92ff4a7bc971"></a>
### `cJSON.c-add-typed-helpers`

`CJSON_PUBLIC(cJSON*) cJSON_AddNullToObject(cJSON * const object, const char * const n…` · [cJSON.c:L2150-L2160][f1]

Typed convenience adders (AddNull/AddTrue/AddFalse/AddBool/AddNumber/AddString/AddRaw/AddObject/AddArrayToObject).

Each creates a fresh item of the corresponding type via the matching cJSON_Create* call, adds it under a duplicated key with add_item_to_object, and returns the new item on success. On any add failure the created item is deleted and NULL is returned, so no partially attached node leaks. NULL creation results flow through add_item_to_object and fail the same way.

calls: [add_item_to_object](core-tree-mutation.md#u-14e9c6b81163)

<a id="u-421b01576cce"></a>
### `cJSON_SetNumberHelper`

`CJSON_PUBLIC(double) cJSON_SetNumberHelper(cJSON *object, double number)` · [cJSON.c:L411-L432][f1]

Stores a double into an existing number item and returns the stored value.

A NULL object returns NAN. valueint is saturated to INT_MAX or INT_MIN when out of range, otherwise truncated; valuedouble is assigned and returned.

<a id="u-a1c731bd85cb"></a>
### `cJSON_SetValuestring`

`CJSON_PUBLIC(char*) cJSON_SetValuestring(cJSON *object, const char *valuestring)` · [cJSON.c:L435-L476][f1]

Replaces the string of a non-reference cJSON_String item.

Returns NULL when object is NULL, the item is not a string or is flagged cJSON_IsReference, or either the existing or new valuestring is NULL. If the new string fits the existing buffer (v1_len <= v2_len): overlapping source and destination ranges return NULL, otherwise it strcpy's in place and returns object->valuestring. If the new string is longer it strdup's a fresh copy with global_hooks; strdup failure returns NULL leaving the item unchanged, otherwise the old buffer is cJSON_free'd, the new copy installed, and returned.

**Notes.**

- side_effect: When the string grows, the old valuestring buffer is freed, so previously returned pointers into it become dangling.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c