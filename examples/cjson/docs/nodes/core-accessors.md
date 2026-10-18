# Lookup, Predicates & Accessors

**Capability.** Read-side inspection of trees without mutation: object/array lookup (case-sensitive and insensitive), type predicates comparing type & 0xFF, typed value accessors with sentinel returns, and the case-insensitive key comparison underlying lookups.

Use this subtree for any read of a tree's contents or type. The utilities layer calls these predicates and lookup wrappers directly, so changes here affect RFC operations in cJSON_Utils.c.

**Depended on by.**

- [Tree Construction & Mutation](core-tree-mutation.md) · graph-confirmed · 8 edge(s) · Mutation reads existing members: replace and compare resolve targets via object lookup and shared utilities.
- [JSON Pointer \(RFC 6901\)](utils-json-pointer.md) · graph-confirmed · 4 edge(s) · Pointer resolution inspects node types and fetches object members via core lookup wrappers and predicates.
- [JSON Patch Application \(RFC 6902\)](utils-patching.md) · graph-confirmed · 11 edge(s) · Patch classification and dispatch test operation types through core type predicates.
- [Object Sorting](utils-sorting.md) · model-inferred · 0 edge(s)
- [Diff & Merge Patches](utils-diff-merge.md) · graph-only · 5 edge(s)

Parent: [Core cJSON Engine](core-json.md)

## Units (6)

<a id="u-64a0d9ed33a8"></a>
### `cJSON.c-array-accessors`

`CJSON_PUBLIC(int) cJSON_GetArraySize(const cJSON *array)` · [cJSON.c:L1899-L1920][f1]

Array lookup helpers.

cJSON_GetArraySize counts children by walking next and returns the count cast to int (an overflow is acknowledged as unfixable in the code comment). get_array_item walks the child chain index times, returning the node or NULL when array is NULL or the chain ends first. cJSON_GetArrayItem rejects negative indexes with NULL and forwards to get_array_item; out-of-range indexes yield NULL.

<a id="u-a500ccd1b1a7"></a>
### `get_object_item`

`static cJSON *get_object_item(const cJSON * const object, const char * const name, co…` · [cJSON.c:L1951-L1981][f1]

Finds the first child of object whose key matches name.

NULL object or name returns NULL. In case-sensitive mode it advances while strcmp differs (skipping children with NULL keys); otherwise it advances while case_insensitive_strcmp differs, which also treats NULL keys as non-matching. After the loop, a NULL element or an element whose key is NULL returns NULL, so a case-sensitive match never lands on a keyless child. The linear scan returns the first match.

calls: [case_insensitive_strcmp](core-accessors.md#u-dc674c51daff)

<a id="u-dc674c51daff"></a>
### `case_insensitive_strcmp`

`static int case_insensitive_strcmp(const unsigned char *string1, const unsigned char …` · [cJSON.c:L133-L154][f1]

Case-insensitive byte comparison used for object-key lookups.

If either pointer is NULL it returns 1 (so a NULL key never matches anything); identical pointers return 0. Otherwise it walks both strings while the tolower of the current bytes matches, returning 0 at the terminating NUL and the tolower difference of the first mismatching bytes otherwise.

<a id="u-e0c5e1195ba6"></a>
### `cJSON.c-object-lookup-wrappers`

`CJSON_PUBLIC(cJSON *) cJSON_GetObjectItem(const cJSON * const object, const char * co…` · [cJSON.c:L1983-L1986][f1]

Public object lookups: cJSON_GetObjectItem and cJSON_GetObjectItemCaseSensitive forward to get_object_item with case sensitivity false and true respectively; cJSON_HasObjectItem returns 1 exactly when the case-insensitive lookup finds a match, else 0.

calls: [get_object_item](core-accessors.md#u-a500ccd1b1a7)

<a id="u-533c658ff3f4"></a>
### `cJSON.c-type-predicates`

`CJSON_PUBLIC(cJSON_bool) cJSON_IsInvalid(const cJSON * const item)` · [cJSON.c:L2972-L2980][f1]

Type tests sharing one shape: NULL returns false, otherwise each compares (type & 0xFF) against one constant — cJSON_Invalid for IsInvalid, cJSON_False/True/NULL/Number/String/Array/Object/Raw for the others.

cJSON_IsBool differs: it returns true when either the cJSON_True or cJSON_False bit is set. Flag bits above the low byte (references, const strings) never affect the low-byte tests.

<a id="u-d6437d2df5f5"></a>
### `cJSON.c-value-accessors`

`CJSON_PUBLIC(const char *) cJSON_GetErrorPtr(void)` · [cJSON.c:L94-L97][f1]

Typed accessors and version reporting for cJSON items: each guards on item type and returns a sentinel when the type does not match.

cJSON_GetErrorPtr returns a pointer into the static global_error record (meaningful only right after a failed parse). cJSON_GetStringValue returns valuestring only when cJSON_IsString holds, else NULL. cJSON_GetNumberValue returns NAN for non-numbers, else valuedouble. cJSON_Version sprintfs the version triple into a static 15-char buffer.

**Notes.**

- side_effect: cJSON_Version writes into a static buffer, so concurrent calls race.

uses: [cJSON.c-type-predicates](core-accessors.md#u-533c658ff3f4)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c