# Object Sorting

**Capability.** Deterministically orders object members via a stable mergesort over the child list, parameterized by case-sensitive or insensitive three-way string comparison, exposed through public SortObject wrappers.

Use this subtree when output ordering or diff stability matters: diff and merge-patch generation call sort_object before comparing, so ordering semantics here shape patch output.

**Depends on.**

- [Lookup, Predicates & Accessors](core-accessors.md) · model-inferred · 0 edge(s)
- [Diff & Merge Patches](utils-diff-merge.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Diff & Merge Patches](utils-diff-merge.md) · graph-confirmed · 6 edge(s) · Comparison and patch generation sort objects first so diff output is deterministic.

Parent: [cJSON Utilities \(RFC Layer\)](json-utils.md)

## Units (4)

<a id="u-6547cae15f80"></a>
### `sort_object`

`static void sort_object(cJSON * const object, const cJSON_bool case_sensitive)` · [cJSON_Utils.c:L595-L602][f1]

Sorts an object's children by replacing object->child with sort_list's result; NULL objects are ignored.

calls: [sort_list](utils-sorting.md#u-e92c66f838ea)

<a id="u-e92c66f838ea"></a>
### `sort_list`

`static cJSON *sort_list(cJSON *list, const cJSON_bool case_sensitive)` · [cJSON_Utils.c:L484-L593][f1]

Stable mergesort over a cJSON child list ordered by compare_strings on the string fields.

A NULL or single-node list returns unchanged. It first scans for an already-sorted list and returns it unmodified if no inversion is found. Otherwise two pointers find the middle, the list is split, both halves sort recursively, and a merge splices the smaller-headed sublist first, threading next/prev links as it goes; the remaining half is appended (returning it directly if the merged result is still empty).

calls: [compare_strings](utils-diff-merge.md#u-53f8c3ba705f)

**Uncertainties.**

- Whether the merged list's final node's ->next is guaranteed NULL after appending the remainder is not explicitly set in the visible code for the appended tail's next field.

<a id="u-c31045fe64d2"></a>
### `cJSONUtils_SortObject`

`CJSON_PUBLIC(void) cJSONUtils_SortObject(cJSON * const object)` · [cJSON_Utils.c:L1311-L1314][f1]

Public case-insensitive object sort; delegates to sort_object(object, false).

calls: [sort_object](utils-sorting.md#u-6547cae15f80)

<a id="u-f89e615dde07"></a>
### `cJSONUtils_SortObjectCaseSensitive`

`CJSON_PUBLIC(void) cJSONUtils_SortObjectCaseSensitive(cJSON * const object)` · [cJSON_Utils.c:L1316-L1319][f1]

Public case-sensitive object sort; delegates to sort_object(object, true).

calls: [sort_object](utils-sorting.md#u-6547cae15f80)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON_Utils.c