# Sorting and deep comparison

**Capability.** Deep-compares cJSON values and sorts object members by key using merge sort.

Utils-side equality checks (doubles, strings, whole trees) and key-based sorting of object children live here. Use it when comparing trees or canonicalizing object member order.

**Depended on by.**

- [JSON Patch application](json-patch-application.md) · graph-confirmed · 1 edge(s) · Patch application uses deep comparison to evaluate test operations.
- [JSON Patch generation](json-patch-generation.md) · graph-only · 4 edge(s)
- [Object membership and merge patch](object-membership-and-merge-patch.md) · graph-only · 3 edge(s)

Parent: [Pointer and Patch Engine](pointer-and-patch-engine.md)

## Units (6)

<a id="u-e92617c961f5"></a>
### `cJSON_Utils.c:compare_double`

`static cJSON_bool compare_double(double a, double b)` · [cJSON_Utils.c:L112-L116][f1]

Compares two doubles for near-equality: |a-b| must be at most max(|a|,|b|)*DBL_EPSILON.

Note this accepts 0 vs 0 as equal and is a relative-tolerance comparison, not exact.

<a id="u-5316b1a86a7c"></a>
### `compare_json`

`static cJSON_bool compare_json(cJSON *a, cJSON *b, const cJSON_bool case_sensitive)` · [cJSON_Utils.c:L604-L690][f1]

Deep-compares two cJSON values for equality, returning false on any mismatch.

NULL on either side, or differing low-byte types, is false. Numbers compare both valueint and valuedouble (via compare_double's relative tolerance). Strings use strcmp. Arrays compare children pairwise recursively and require equal lengths. Objects first sort both in place (a side effect on the inputs) via sort_object, then compare keys with compare_strings (nonzero means missing member) and values recursively, requiring equal member counts. All other types (null, true, false) are considered equal when types match; the case_sensitive flag only affects key comparisons.

<a id="u-53f8c3ba705f"></a>
### `compare_strings`

`static int compare_strings(const unsigned char *string1, const unsigned char *string2…` · [cJSON_Utils.c:L83-L109][f1]

Compares two strings, treating any NULL as unequal (returns 1).

Identical pointers compare equal (0). Case-sensitive mode uses strcmp; otherwise compares via tolower character by character, returning 0 at simultaneous NUL or the lowercased difference at the first mismatch.

<a id="u-e92c66f838ea"></a>
### `sort_list`

`static cJSON *sort_list(cJSON *list, const cJSON_bool case_sensitive)` · [cJSON_Utils.c:L484-L593][f1]

Sorts a doubly linked list of cJSON items by their string keys using merge sort, relinking prev/next pointers and returning the new head.

Lists of length 0 or 1 are returned as-is; an already-sorted list (detected by a forward scan with compare_strings < 0) is returned unmodified. Otherwise it finds the middle with a two-pointer walk, splits the list, recursively sorts both halves, and merges them picking the smaller head each time (ties take the second list's head), appending any remaining tail. Comparison uses compare_strings, so NULL keys sort as 'greater' (compare_strings returns 1 for NULL).

<a id="u-6547cae15f80"></a>
### `sort_object`

`static void sort_object(cJSON * const object, const cJSON_bool case_sensitive)` · [cJSON_Utils.c:L595-L602][f1]

Sorts an object's children by key via sort_list; NULL object is a no-op.

<a id="u-aaef6897e411"></a>
### `cJSON_Utils.c-sortobject-entry-points`

`CJSON_PUBLIC(void) cJSONUtils_SortObject(cJSON * const object)` · [cJSON_Utils.c:L1311-L1314][f1]

Sort an object's members by key in place; the plain version case-insensitively, the CaseSensitive variant byte-wise.

NULL is a no-op.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.c
