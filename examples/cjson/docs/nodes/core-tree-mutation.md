# Tree Construction & Mutation

**Capability.** Owns structural changes to trees: appending/inserting children, key-based object installation, detaching, replacement, deep duplication, reference nodes, whole-tree deletion, and structural comparison.

Use this subtree when code links, unlinks, copies, or frees cJSON nodes. All higher layers (constructors, utilities) ultimately rest on add_item_to_array/add_item_to_object, cJSON_Delete, and cJSON_Duplicate_rec here.

**Depends on.**

- [Lookup, Predicates & Accessors](core-accessors.md) · graph-confirmed · 8 edge(s) · Mutation reads existing members: replace and compare resolve targets via object lookup and shared utilities.
- [Memory & Shared Support](core-memory-support.md) · graph-confirmed · 8 edge(s) · Deep duplication and object installation allocate via new-item/strdup and free replaced items via cJSON_Delete.

**Depended on by.**

- [Convenience Constructors & Setters](core-constructors.md) · graph-confirmed · 31 edge(s) · Typed Add helpers install created items into trees through add_item_to_object/add_item_to_array and free on failure via cJSON_Delete.
- [Diff & Merge Patches](utils-diff-merge.md) · graph-confirmed · 21 edge(s) · Merge-patch generation and application deep-copy and free subtrees via the core mutation primitives.
- [JSON Patch Application \(RFC 6902\)](utils-patching.md) · graph-confirmed · 12 edge(s) · apply_patch mutates documents via core add/detach/delete/duplicate primitives.
- [JSON Text Parsing](core-parsing.md) · graph-only · 3 edge(s)

Parent: [Core cJSON Engine](core-json.md)

## Units (12)

<a id="u-16f393dc2dba"></a>
### `add_item_to_array`

`static cJSON_bool add_item_to_array(cJSON *array, cJSON *item)` · [cJSON.c:L2027-L2058][f1]

Appends item to an array/object child list in amortized constant time using child->prev as the tail pointer.

NULL item, NULL array, or array == item returns false. An empty list sets array->child to item with item->prev = item (self-pointer marks the tail) and next NULL. Otherwise, when child->prev exists, it links the item after the tail and updates the head's prev to the new tail; if child->prev is somehow NULL the item is silently not linked while the function still returns true.

<a id="u-14e9c6b81163"></a>
### `add_item_to_object`

`static cJSON_bool add_item_to_object(cJSON * const object, const char * const string,…` · [cJSON.c:L2082-L2117][f1]

Installs an item into an object under a key.

NULL object/string/item or object == item returns false. In constant-key mode the key pointer is stored as-is (const cast away) and the item's type gains the cJSON_StringIsConst bit so deletion never frees it. In duplicating mode the key is strdup'd with the supplied hooks (strdup failure returns false) and the StringIsConst bit is cleared from the item's type. Before overwriting, an existing non-const item->string is freed. Finally the key and updated type are assigned and the item is appended via add_item_to_array, whose result is returned.

calls: [cJSON_strdup](core-memory-support.md#u-e8a9f7d7fb70), [add_item_to_array](core-tree-mutation.md#u-16f393dc2dba)

<a id="u-abbfa67dd8a4"></a>
### `cJSON_DetachItemViaPointer`

`CJSON_PUBLIC(cJSON *) cJSON_DetachItemViaPointer(cJSON *parent, cJSON * const item)` · [cJSON.c:L2258-L2292][f1]

Unlinks item from parent's child list without freeing it and returns it.

Returns NULL when parent or item is NULL, or when item is neither the head nor has a prev pointer (a corrupted/foreign node). For a middle node it splices prev->next and next->prev; a head node advances parent->child; a non-head tail node updates the head's prev to keep the tail pointer valid. Finally the item's prev and next are nulled and the item itself is returned for the caller to reuse or delete.

<a id="u-38b9b193a8bd"></a>
### `cJSON_InsertItemInArray`

`CJSON_PUBLIC(cJSON_bool) cJSON_InsertItemInArray(cJSON *array, int which, cJSON *newi…` · [cJSON.c:L2334-L2366][f1]

Inserts newitem so that it takes the position of the current element at index which.

Negative which or NULL newitem returns false. If no element exists at which the item is appended via add_item_to_array. If the located element is neither the head nor has a prev pointer (corrupted list) it returns false. Otherwise newitem is linked before after_inserted via next/prev updates, with the head pointer replaced when inserting at position 0 and newitem->prev->next fixed otherwise. Returns true after linking.

calls: [add_item_to_array](core-tree-mutation.md#u-16f393dc2dba)

<a id="u-c02d50dcaae9"></a>
### `cJSON_ReplaceItemViaPointer`

`CJSON_PUBLIC(cJSON_bool) cJSON_ReplaceItemViaPointer(cJSON * const parent, cJSON * co…` · [cJSON.c:L2368-L2415][f1]

Swaps item with replacement in parent's list and deletes item.

Returns false when parent, parent->child, replacement, or item is NULL; replacing an item by itself returns true without changes. Replacement inherits item's next/prev, neighbors are re-pointed, and the head case preserves the tail self-pointer convention (replacement->prev = replacement when the sole element was replaced); in the non-head branch prev->next is fixed when replacement->prev is set and the head's prev is updated when replacement becomes the tail. item is nulled on both sides and freed with cJSON_Delete. Returns true.

calls: [cJSON_Delete](core-tree-mutation.md#u-5ca539d2c8db)

<a id="u-71a5552634af"></a>
### `replace_item_in_object`

`static cJSON_bool replace_item_in_object(cJSON *object, const char *string, cJSON *re…` · [cJSON.c:L2427-L2448][f1]

Replaces the item stored under a key, renaming replacement to that key first.

NULL replacement or string returns false. An existing non-const replacement->string is cJSON_free'd, then the key is re-strdup'd with global_hooks (failure returns false, possibly having already freed the old key) and the StringIsConst bit cleared, so the replacement always owns its new key. The underlying item to replace is located with get_object_item using the given case sensitivity; a missing key yields a NULL target and cJSON_ReplaceItemViaPointer returns false.

calls: [cJSON_ReplaceItemViaPointer](core-tree-mutation.md#u-c02d50dcaae9), [get_object_item](core-accessors.md#u-a500ccd1b1a7)

**Uncertainties.**

- If the key strdup fails after the old replacement->string was freed, the replacement is left with a freed/NULL key and the function returns false; the exact state of replacement->string at that point depends on strdup's contract.

<a id="u-1a2121646559"></a>
### `cJSON.c-add-item-wrappers`

`CJSON_PUBLIC(cJSON_bool) cJSON_AddItemToObject(cJSON *object, const char *string, cJS…` · [cJSON.c:L2119-L2122][f1]

Public add-entry wrappers.

cJSON_AddItemToObject and cJSON_AddItemToObjectCS call add_item_to_object with constant_key false and true respectively (the CS variant stores the caller's key pointer and marks it const). cJSON_AddItemReferenceToArray validates array, creates a reference via create_reference, and appends with add_item_to_array; cJSON_AddItemReferenceToObject validates object and string, creates the reference, and adds it under a duplicated key. All return the underlying call's boolean.

calls: [add_item_to_object](core-tree-mutation.md#u-14e9c6b81163), [create_reference](core-tree-mutation.md#u-b24a8e16fef0)

<a id="u-b717b0a176e7"></a>
### `cJSON.c-detach-delete-wrappers`

`CJSON_PUBLIC(cJSON *) cJSON_DetachItemFromArray(cJSON *array, int which)` · [cJSON.c:L2294-L2302][f1]

Index- and key-based removal wrappers.

cJSON_DetachItemFromArray rejects negative indexes and otherwise detaches get_array_item(array, which) via pointer. cJSON_DeleteItemFromArray detaches then cJSON_Delete's the result (detaching NULL deletes nothing). cJSON_DetachItemFromObject and its CaseSensitive variant look the key up with the case-insensitive or case-sensitive getter and detach via pointer; the two DeleteItemFromObject variants wrap those with cJSON_Delete. Missing items yield NULL from detach and are no-ops for delete.

calls: [cJSON_DetachItemViaPointer](core-tree-mutation.md#u-abbfa67dd8a4), [cJSON_Delete](core-tree-mutation.md#u-5ca539d2c8db)

<a id="u-b24a8e16fef0"></a>
### `create_reference`

`static cJSON *create_reference(const cJSON *item, const internal_hooks * const hooks)` · [cJSON.c:L2006-L2025][f1]

Creates a shallow reference node: NULL item or allocation failure returns NULL.

Otherwise it memcpy's the whole source item into the new node, clears string, ORs cJSON_IsReference into the type, and NULLs next and prev, so the reference shares valuestring/child pointers with the source while remaining unlinkable on its own.

calls: [cJSON_New_Item](core-memory-support.md#u-0840a192aac8)

<a id="u-5ca539d2c8db"></a>
### `cJSON_Delete`

`CJSON_PUBLIC(void) cJSON_Delete(cJSON *item)` · [cJSON.c:L253-L276][f1]

Frees an item and its entire ->next sibling chain.

For each node: it recurses into ->child only when the node is not flagged cJSON_IsReference (reference children are never followed or freed); frees ->valuestring only when not a reference and non-NULL; frees ->string only when cJSON_StringIsConst is not set (constant/static keys are left alone). Each pointer is nulled before the node itself is deallocated. NULL input is a no-op.

**Notes.**

- failure: There is no cycle detection; a structure reachable from its own child recurses indefinitely.

<a id="u-a1efa4a6ba11"></a>
### `cJSON_Duplicate_rec`

`cJSON * cJSON_Duplicate_rec(const cJSON *item, size_t depth, cJSON_bool recurse)` · [cJSON.c:L2789-L2873][f1]

Recursive deep copy.

A NULL item fails. The copy clears the cJSON_IsReference flag from the type and copies valueint/valuedouble; valuestring is strdup'd (failure fails). A non-const key is strdup'd, while a StringIsConst key pointer is shared as-is; string duplication failure fails. With recurse false the shallow copy is returned immediately. With recurse true, each child is copied recursively; if depth reaches CJSON_CIRCULAR_LIMIT the copy fails, which is the only recursion guard. Copies are linked in order and the child list's tail is closed into head->prev. The fail path deletes the partially built newitem and returns NULL.

calls: [cJSON_New_Item](core-memory-support.md#u-0840a192aac8), [cJSON_strdup](core-memory-support.md#u-e8a9f7d7fb70), [cJSON_Delete](core-tree-mutation.md#u-5ca539d2c8db)

<a id="u-ebaf707174c1"></a>
### `cJSON_Compare`

`CJSON_PUBLIC(cJSON_bool) cJSON_Compare(const cJSON * const a, const cJSON * const b, …` · [cJSON.c:L3072-L3195][f1]

Recursive structural equality.

NULL arguments or differing low-byte types return false; unknown types return false. Identical pointers return true. True/False/NULL compare by type alone. Numbers use compare_double (relative epsilon tolerance). Strings and Raw require non-NULL valuestrings and strcmp equality. Arrays compare element-wise in order via recursion and require equal lengths (both chains must end together). Objects are symmetric: for every key in a, b must contain a key matched by get_object_item with the given case sensitivity and the values must compare equal, and then the same check is run with a and b swapped, so neither side may have an unmatched key; the code notes this is O(n^2).

calls: [cJSON.c-internal-utilities](core-memory-support.md#u-5c575837ef16), [get_object_item](core-accessors.md#u-a500ccd1b1a7)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c