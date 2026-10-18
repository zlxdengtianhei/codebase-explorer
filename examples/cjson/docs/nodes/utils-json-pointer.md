# JSON Pointer (RFC 6901)

**Capability.** Resolves pointer strings to nodes and builds pointer strings locating nodes: token matching, escape decoding, array-index parsing, encoding helpers, and public GetPointer/FindPointer entry points.

Use this subtree for any pointer parsing/formatting question. get_item_from_pointer is the resolution core that patching and consumers rely on; FindPointer and compose_patch share the encode/length helpers here.

**Depends on.**

- [Lookup, Predicates & Accessors](core-accessors.md) · graph-confirmed · 4 edge(s) · Pointer resolution inspects node types and fetches object members via core lookup wrappers and predicates.
- [Memory & Shared Support](core-memory-support.md) · graph-only · 7 edge(s)
- [cJSON Utilities \(RFC Layer\)](json-utils.md) · within containment · 1 edge(s) · Pointer units are contained within the json-utils subtree and use its internal helpers directly.

**Depended on by.**

- [Diff & Merge Patches](utils-diff-merge.md) · graph-confirmed · 4 edge(s) · Diff encodes emitted patch paths using pointer-encoding and length helpers.
- [JSON Patch Application \(RFC 6902\)](utils-patching.md) · graph-confirmed · 8 edge(s) · Every patch operation resolves its target path through pointer decoding and get_item_from_pointer.

Parent: [cJSON Utilities \(RFC Layer\)](json-utils.md)

## Units (10)

<a id="u-1ab29902a15f"></a>
### `get_item_from_pointer`

`static cJSON *get_item_from_pointer(cJSON * const object, const char * pointer, const…` · [cJSON_Utils.c:L301-L346][f1]

Resolves a JSON pointer against a cJSON tree, returning the designated node.

NULL pointer yields NULL. Each loop iteration requires pointer[0]=='/' and a non-NULL current element: it advances past '/', then either decodes an array index via decode_array_index_from_pointer and looks it up with get_array_item (returning NULL on decode failure), or scans the object's children comparing keys with compare_pointers; a scalar current element returns NULL. It then skips the pointer to the next '/' or end and repeats. When the pointer is exhausted, the current element is returned.

calls: [decode_array_index_from_pointer](utils-json-pointer.md#u-338db4acac6e), [cJSON_Utils.c:get_array_item](utils-json-pointer.md#u-644c521c4779), [compare_pointers](utils-json-pointer.md#u-47610f0b20bf), [cJSON.c-type-predicates](core-accessors.md#u-533c658ff3f4)

**Uncertainties.**

- Key matching here compares escaped pointer text against stored keys via compare_pointers; no in-place decoding happens on this path.

<a id="u-47610f0b20bf"></a>
### `compare_pointers`

`static cJSON_bool compare_pointers(const unsigned char *name, const unsigned char *po…` · [cJSON_Utils.c:L120-L154][f1]

Compares one JSON-pointer path token against an object key.

Returns false if either input is NULL. Loops while neither character is '\0' and the pointer char is not '/': a '~' in the pointer must be followed by '0' matching a '~' in the name or '1' matching a '/', otherwise false; any other character mismatch (case-folded when not case_sensitive) yields false. After the loop, false is returned when exactly one side has leftover characters before its next '/' or end; otherwise true.

**Notes.**

- failure: A '~' as the final byte reads pointer[1] (the terminator); both escape checks then fail and the function returns false without further over-read.

<a id="u-4989d0e4e216"></a>
### `decode_pointer_inplace`

`static void decode_pointer_inplace(unsigned char *string)` · [cJSON_Utils.c:L359-L390][f1]

Decodes JSON-pointer escapes in place, shortening the string.

Returns immediately for NULL. On '~': '~0' writes '~', '~1' writes '/' (one position ahead, compensated by the shared decoded_string cursor advancing once per iteration), any other escape aborts decoding by returning early. Both cursors advance together each iteration; escaping consumes an extra source byte. Finally a terminator is written at the decoded cursor.

**Notes.**

- failure: On an invalid escape the function returns early, leaving the buffer partially decoded and without a terminator write at that point.

**Uncertainties.**

- The '~1' case writes to decoded_string[1], relying on the decoded cursor lagging the source cursor by one at that point; exact buffer state after an early return is implementation-defined by this code only.

<a id="u-338db4acac6e"></a>
### `decode_array_index_from_pointer`

`static cJSON_bool decode_array_index_from_pointer(const unsigned char * const pointer…` · [cJSON_Utils.c:L274-L299][f1]

Parses a decimal array index from the start of a pointer token into *index.

Rejects a leading '0' unless the token is exactly that digit ('0' followed by neither '\0' nor '/'). Accumulates digits, then requires the next character to be '\0' or '/'; anything else returns 0 without touching *index. Returns 1 on success.

**Notes.**

- failure: Numeric overflow for very long digit runs is not detected; parsed_index wraps.

<a id="u-644c521c4779"></a>
### `cJSON_Utils.c:get_array_item`

`static cJSON *get_array_item(const cJSON *array, size_t item)` · [cJSON_Utils.c:L262-L272][f1]

Safe array-item lookup: starts at array->child (NULL when array is NULL) and advances next item-many times, returning the node reached or NULL when the index is past the end.

<a id="u-090f135fbb3f"></a>
### `encode_string_as_pointer`

`static void encode_string_as_pointer(unsigned char *destination, const unsigned char …` · [cJSON_Utils.c:L173-L196][f1]

Writes source into destination, escaping '/' as '~1' and '~' as '~0', then appends the terminator.

No bounds checking exists; callers must size destination as pointer_encoded_length(source)+1 bytes.

<a id="u-4023d70cec38"></a>
### `pointer_encoded_length`

`static size_t pointer_encoded_length(const unsigned char *string)` · [cJSON_Utils.c:L157-L170][f1]

Returns the encoded length of a string as a JSON-pointer token: one per ordinary character plus one extra for each '~' or '/', which expand to two-character escapes.

<a id="u-a7ca424fbf06"></a>
### `cJSONUtils_GetPointer`

`CJSON_PUBLIC(cJSON *) cJSONUtils_GetPointer(cJSON * const object, const char *pointer)` · [cJSON_Utils.c:L348-L351][f1]

Public case-insensitive pointer resolution; delegates to get_item_from_pointer with case_sensitive=false.

calls: [get_item_from_pointer](utils-json-pointer.md#u-1ab29902a15f)

<a id="u-e44c4f2adbd0"></a>
### `cJSONUtils_GetPointerCaseSensitive`

`CJSON_PUBLIC(cJSON *) cJSONUtils_GetPointerCaseSensitive(cJSON * const object, const …` · [cJSON_Utils.c:L353-L356][f1]

Public case-sensitive pointer resolution; delegates to get_item_from_pointer with case_sensitive=true.

calls: [get_item_from_pointer](utils-json-pointer.md#u-1ab29902a15f)

<a id="u-394cc13a634e"></a>
### `cJSONUtils_FindPointerFromObjectTo`

`CJSON_PUBLIC(char *) cJSONUtils_FindPointerFromObjectTo(const cJSON * const object, c…` · [cJSON_Utils.c:L198-L259][f1]

Builds a JSON pointer string locating target within the subtree rooted at object.

NULL object or target returns NULL; object==target returns a strdup of the empty string. It iterates children in order and recurses; when a child's call returns a pointer it prefixes the child's location: for arrays '/<index>' via sprintf with 64-bit headroom, freeing intermediates and returning NULL if child_index exceeds ULONG_MAX; for objects '/' plus the escaped key of current_child concatenated with the child's pointer via strcat. If the parent is neither array nor object, the child pointer is freed and NULL returned. Exhausting all children returns NULL.

calls: [cJSONUtils_strdup](json-utils.md#u-d0535f9d8f45), [pointer_encoded_length](utils-json-pointer.md#u-4023d70cec38), [encode_string_as_pointer](utils-json-pointer.md#u-090f135fbb3f), [cJSON.c-type-predicates](core-accessors.md#u-533c658ff3f4)

**Uncertainties.**

- For an object child with NULL key, pointer_encoded_length and encode_string_as_pointer would receive NULL; behavior is not defined by this code.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.c