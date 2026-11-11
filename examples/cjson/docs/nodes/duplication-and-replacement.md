# Duplication and replacement

**Capability.** Duplicates cJSON trees, copies strings, and replaces items in objects or via pointers.

Readers needing to clone trees or swap nodes in place should start here. It covers deep duplication, string copying, key-preserving replacement, and pointer-based item replacement.

**Depends on.**

- [Comparison and lookup helpers](comparison-and-lookup-helpers.md) · graph-confirmed · 1 edge(s)
- [Core item manipulation utilities](core-item-manipulation-utilities.md) · graph-confirmed · 1 edge(s) · Tree duplication and replacement build on core structural manipulation routines.
- [Node construction and linking](node-construction-and-linking.md) · graph-only · 3 edge(s)
- [JSON Patch generation](json-patch-generation.md) · graph-only · 2 edge(s)

**Depended on by.**

- [JSON Patch application](json-patch-application.md) · graph-only · 3 edge(s)
- [Node construction and linking](node-construction-and-linking.md) · graph-only · 3 edge(s)
- [Object membership and merge patch](object-membership-and-merge-patch.md) · graph-only · 3 edge(s)
- [JSON Patch generation](json-patch-generation.md) · graph-only · 1 edge(s)

Parent: [Item Utility Toolkit](item-utility-toolkit.md)

## Units (5)

<a id="u-a1c731bd85cb"></a>
### `cJSON_SetValuestring`

`CJSON_PUBLIC(char*) cJSON_SetValuestring(cJSON *object, const char *valuestring)` · [cJSON.c:L435-L476][f1]

Replaces a string item's valuestring.

Fails (returns NULL) if the object is NULL, not a cJSON_String, is a reference, or either the old or new valuestring is NULL. If the new string fits in the old allocation, it strcpy's in place but only when the two ranges do not overlap (overlap returns NULL); otherwise it duplicates the new string, frees the old valuestring via cJSON_free, and installs the copy, returning the new pointer or NULL on allocation failure.

<a id="u-e8a9f7d7fb70"></a>
### `cJSON_strdup`

`static unsigned char* cJSON_strdup(const unsigned char* string, const internal_hooks …` · [cJSON.c:L188-L207][f1]

Allocates and returns a heap copy of a NUL-terminated string via the supplied hooks, or NULL for a NULL input or allocation failure; the copy includes the terminator.

<a id="u-3fb871c46ed3"></a>
### `cJSON.c-duplicate`

`CJSON_PUBLIC(cJSON *) cJSON_Duplicate(const cJSON *item, cJSON_bool recurse)` · [cJSON.c:L2784-L2787][f1]

cJSON_Duplicate delegates to cJSON_Duplicate_rec at depth 0.

The recursive copy duplicates a node's type (clearing cJSON_IsReference), valueint, valuedouble, and deep-copies valuestring and string (string is shared, not copied, when the source is StringIsConst); any strdup failure frees the partial copy and returns NULL. Without recurse it returns this shallow copy. With recurse it walks the child chain, copying each child recursively and linking the copies, failing when depth reaches CJSON_CIRCULAR_LIMIT (guarding against runaway/circular structures), and finally sets the copy's child->prev tail. On failure the whole new tree is deleted and NULL returned.

<a id="u-358885c226d6"></a>
### `cJSON.c-replace-in-object`

`static cJSON_bool replace_item_in_object(cJSON *object, const char *string, cJSON *re…` · [cJSON.c:L2427-L2448][f1]

replace_item_in_object gives replacement a duplicated copy of string as its key (freeing any owned old string first; allocation failure returns false, and the StringIsConst flag is cleared), then replaces the existing member found by the case-(in)sensitive lookup via the pointer routine.

The two public wrappers select the case sensitivity; replacing a missing key fails because the pointer routine receives a NULL item.

<a id="u-5920711b8663"></a>
### `cJSON.c-replace-via-pointer-array-index`

`CJSON_PUBLIC(cJSON_bool) cJSON_ReplaceItemViaPointer(cJSON * const parent, cJSON * co…` · [cJSON.c:L2368-L2415][f1]

cJSON_ReplaceItemViaPointer swaps item for replacement in parent's list and deletes the old item.

It returns false for NULL parent/item/replacement or an empty parent, and true immediately if replacement == item. It copies item's next/prev into replacement, fixes the neighbors' back-links, and handles the first-element case (including the single-element self-tail convention child->prev == child) and the last-element case (updating parent->child->prev). The old item's links are cleared before cJSON_Delete. cJSON_ReplaceItemInArray rejects a negative index and resolves the target with get_array_item before delegating.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c
