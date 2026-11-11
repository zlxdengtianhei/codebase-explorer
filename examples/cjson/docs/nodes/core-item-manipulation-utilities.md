# Core item manipulation utilities

**Capability.** Detaching, indexing, replacing, and inspecting cJSON items, plus allocator hooks, versioning, and minification.

Come here for structural operations on existing trees: detaching or deleting array elements, walking child chains, replacing via pointer, and reading typed value payloads. It also hosts global allocator hook replacement, version string formatting, and in-place minification.

**Depends on.**

- [JSON Patch application](json-patch-application.md) · graph-only · 2 edge(s)
- [JSON printing and serialization](json-printing-and-serialization.md) · graph-only · 2 edge(s)
- [Node construction and linking](node-construction-and-linking.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Duplication and replacement](duplication-and-replacement.md) · graph-confirmed · 1 edge(s) · Tree duplication and replacement build on core structural manipulation routines.
- [Object membership and merge patch](object-membership-and-merge-patch.md) · graph-only · 2 edge(s)
- [JSON parser](json-parser.md) · graph-only · 1 edge(s)

Parent: [Item Utility Toolkit](item-utility-toolkit.md)

## Units (15)

<a id="u-abbfa67dd8a4"></a>
### `cJSON_DetachItemViaPointer`

`CJSON_PUBLIC(cJSON *) cJSON_DetachItemViaPointer(cJSON *parent, cJSON * const item)` · [cJSON.c:L2258-L2292][f1]

Unlinks item from parent's child list and returns it (caller owns it).

Returns NULL if parent or item is NULL, or if item is neither the first child nor has a prev link (a corrupted middle element). It patches prev->next and next->prev as needed; when the first element is removed parent->child advances, and when the last is removed the head's tail pointer (child->prev) is updated. The detached item's prev/next are cleared.

<a id="u-5ddd2870bfea"></a>
### `cJSON_GetArraySize`

`CJSON_PUBLIC(int) cJSON_GetArraySize(const cJSON *array)` · [cJSON.c:L1899-L1920][f1]

Counts an array's children by walking the ->next chain; returns 0 for NULL.

The size_t count is cast to int, so arrays with more than INT_MAX elements overflow (acknowledged FIXME).

<a id="u-bcdbba4a230e"></a>
### `cJSON_GetErrorPtr`

`CJSON_PUBLIC(const char *) cJSON_GetErrorPtr(void)` · [cJSON.c:L94-L97][f1]

Returns a pointer into the last parsed input at the recorded error position; computed as global_error.json + global_error.position, which is undefined arithmetic if no parse has recorded an error (json is NULL).

<a id="u-339dd175eeaa"></a>
### `cJSON_InitHooks`

`CJSON_PUBLIC(void) cJSON_InitHooks(cJSON_Hooks* hooks)` · [cJSON.c:L209-L238][f1]

Replaces the global allocator hooks.

A NULL argument resets to malloc/free/realloc. Otherwise each supplied non-NULL function replaces the default; reallocate is set to realloc only when both allocate and deallocate ended up as the libc malloc/free, otherwise it is NULL, which forces callers onto the allocate+copy+deallocate path.

<a id="u-38b9b193a8bd"></a>
### `cJSON_InsertItemInArray`

`CJSON_PUBLIC(cJSON_bool) cJSON_InsertItemInArray(cJSON *array, int which, cJSON *newi…` · [cJSON.c:L2334-L2366][f1]

Inserts newitem before the element at index which.

A negative index or NULL newitem returns false; an out-of-range index falls back to appending via add_item_to_array (inheriting its silent no-attach case). If the target is not the first child and has a NULL prev (corrupted list), it returns false. Otherwise it rewires newitem between the target's prev and the target, advancing array->child when inserting at position 0.

<a id="u-529691305d14"></a>
### `cJSON_PrintBuffered`

`CJSON_PUBLIC(char *) cJSON_PrintBuffered(const cJSON *item, int prebuffer, cJSON_bool…` · [cJSON.c:L1317-L1346][f1]

Prints an item into a caller-sized heap buffer: rejects a negative prebuffer, allocates that many bytes (NULL on failure), and runs print_value with the growable (noalloc=false) buffer, returning the buffer itself, which is not shrunk to the used size.

On print failure it frees the buffer and returns NULL.

<a id="u-416c0507751d"></a>
### `cJSON_PrintPreallocated`

`CJSON_PUBLIC(cJSON_bool) cJSON_PrintPreallocated(cJSON *item, char *buffer, const int…` · [cJSON.c:L1348-L1365][f1]

Prints an item into a caller-supplied fixed buffer of the given length, with noalloc=true so ensure never reallocs; returns false for a negative length or NULL buffer, and the boolean result of print_value, which fails as soon as the output does not fit.

<a id="u-421b01576cce"></a>
### `cJSON_SetNumberHelper`

`CJSON_PUBLIC(double) cJSON_SetNumberHelper(cJSON *object, double number)` · [cJSON.c:L411-L432][f1]

Sets a number item's valuedouble to the given number and saturates valueint to INT_MAX/INT_MIN on overflow; returns NAN for a NULL object, otherwise the newly assigned double.

<a id="u-d88ea811ab9b"></a>
### `cJSON_Version`

`CJSON_PUBLIC(const char*) cJSON_Version(void)` · [cJSON.c:L124-L130][f1]

Formats the compile-time version macros into a static 15-byte buffer with sprintf and returns it; successive calls overwrite the same buffer.

<a id="u-43d416e4aff6"></a>
### `parse_hex4`

`static unsigned parse_hex4(const unsigned char * const input)` · [cJSON.c:L666-L699][f1]

Parses exactly four hex digits into an unsigned value, shifting nibbles left; returns 0 on any non-hex digit, so 0 is ambiguous with a valid \u0000.

<a id="u-267b81d4755c"></a>
### `utf16_literal_to_utf8`

`static unsigned char utf16_literal_to_utf8(const unsigned char * const input_pointer,…` · [cJSON.c:L703-L821][f1]

Converts a \uXXXX escape (or surrogate pair \uXXXX\uXXXX) at the input to UTF-8 at *output_pointer, advancing it, and returns the consumed input length (6 or 12).

It fails (returns 0) if fewer than 6 bytes remain, the first code is a low surrogate, a high surrogate lacks a well-formed low-surrogate second half, or the codepoint exceeds 0x10FFFF. Codepoints are encoded as 1-4 UTF-8 bytes with the appropriate leading mark.

<a id="u-e2d32fb130cc"></a>
### `cJSON.c-array-detach-delete-by-index`

`CJSON_PUBLIC(cJSON *) cJSON_DetachItemFromArray(cJSON *array, int which)` · [cJSON.c:L2294-L2302][f1]

cJSON_DetachItemFromArray rejects a negative index and detaches via the pointer routine; cJSON_DeleteItemFromArray detaches and then frees the item, where cJSON_Delete(NULL) makes a failed detach a safe no-op.

<a id="u-aef586ff38b0"></a>
### `cJSON.c-array-item-access`

`static cJSON* get_array_item(const cJSON *array, size_t index)` · [cJSON.c:L1922-L1939][f1]

get_array_item walks the child chain index steps and returns the node or NULL (bad array or out of range).

cJSON_GetArrayItem adds a NULL result for a negative index before delegating.

<a id="u-c55ecb94fe2c"></a>
### `cJSON.c-minify`

`static void skip_oneline_comment(char **input)` · [cJSON.c:L2875-L2886][f1]

cJSON_Minify compacts JSON in place by dropping whitespace and comments.

Whitespace bytes are skipped; '//' starts a skip to end-of-line, '/*' a skip to '*/' (unterminated comments simply run to the string end); quoted strings are copied verbatim by minify_string, which also preserves escaped quotes; every other byte is copied from the read cursor to the write cursor. The result is NUL-terminated at the write cursor, so the string shrinks in place. A NULL input returns immediately. Note the comment-skipping helpers read past a NUL only up to the string end and assume well-formed input; minify_string assumes a closing quote exists.

<a id="u-51be6a91319c"></a>
### `cJSON.c-typed-value-getters`

`CJSON_PUBLIC(char *) cJSON_GetStringValue(const cJSON * const item)` · [cJSON.c:L99-L107][f1]

Return the value payload of an item with a type guard.

cJSON_GetStringValue returns NULL unless the item is a string; cJSON_GetNumberValue returns NAN unless the item is a number, otherwise the stored double.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c
