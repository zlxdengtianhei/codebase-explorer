# Item Creation and Lifecycle

**Capability.** Creates, appends, references, and inserts cJSON items and typed object members with allocator hooks.

Use this module when constructing cJSON trees or managing item ownership. It contains allocation hooks, basic creators, array/object adders, references, and typed convenience constructors.

**Depended on by.**

- [Core JSON Parse and Print](core-json-parse-and-print.md) · graph-confirmed · 7 edge(s) · Core parsing and printing uses item creation and lifecycle helpers to build and manage cJSON nodes.
- [JSON Pointer Patch Utilities](json-pointer-patch-utilities.md) · graph-confirmed · 28 edge(s) · JSON Pointer and patch utilities use item creation and lifecycle helpers when constructing or changing nodes.
- [Public Utility API and Mutators](public-utility-api-and-mutators.md) · graph-confirmed · 11 edge(s)

Parent: [cJSON JSON Library](cjson-json-library.md)

## Units (7)

<a id="u-0fed687cc5a3"></a>
### `cJSON.c-allocation-hooks-and-item-lifecycle`

`static void * CJSON_CDECL internal_malloc(size_t size)` · [cJSON.c:L165-L168][f1]

Allocation hooks and item lifecycle.

The internal wrappers forward to malloc, free, and realloc. The duplicate helper returns NULL for NULL input, allocates strlen plus one through the supplied hooks, copies, and returns NULL on allocation failure. Hook initialization resets to malloc/free/realloc when given NULL; otherwise it uses supplied malloc/free or defaults and enables realloc only when both allocate and deallocate are the standard malloc and free. New item allocation zeroes a cJSON through hooks. Deletion walks the next chain, recursively deletes child unless the item is a reference, frees valuestring unless reference, frees string unless constant, then frees the node.

<a id="u-24b3ac6bd569"></a>
### `cJSON.c-array-append-and-references`

`static void suffix_object(cJSON *prev, cJSON *item)` · [cJSON.c:L1999-L2003][f1]

Array append and reference creation.

The suffix helper links a previous item to a new item. Reference creation returns NULL for a NULL item or allocation failure; otherwise it copies the item, clears its string, marks it as a reference, and clears next and prev. Array append returns false for NULL item or array or when they are the same. For an empty array it sets the child, makes the item its own prev, and clears next. For a non-empty array it appends only when the child tail pointer is non-NULL, then updates the tail; when that tail pointer is NULL it silently does not attach the item and still returns true. The public add wrapper delegates.

<a id="u-5add094197cb"></a>
### `cJSON.c-array-creators-from-c-arrays`

`CJSON_PUBLIC(cJSON *) cJSON_CreateIntArray(const int *numbers, int count)` · [cJSON.c:L2621-L2659][f1]

Creates arrays from C arrays of ints, floats, doubles, or strings.

Each returns NULL for a negative count or NULL source. It creates an array, then for each element creates a number or string item; creation failure deletes the array and returns NULL. The first item becomes the child, later items are linked by the suffix helper, and after the loop the child tail pointer is set to the last item. A NULL string element makes string creation fail, so the whole array is deleted and NULL is returned.

<a id="u-2b3995547026"></a>
### `cJSON.c-basic-item-creators`

`CJSON_PUBLIC(cJSON *) cJSON_CreateNull(void)` · [cJSON.c:L2461-L2470][f1]

Basic item creators.

Each allocates a zeroed item through global hooks and sets its type. Number also stores the double and a saturated integer. String and raw duplicate the input through the duplicate helper; if that returns NULL, including for NULL input or allocation failure, the creator deletes the item and returns NULL. Reference creators set the reference flag and store the supplied pointer without copying; a NULL supplied pointer is stored as NULL. Array and object creators set only the type.

<a id="u-57abb282e346"></a>
### `cJSON.c-object-insertion`

`static void* cast_away_const(const void* string)` · [cJSON.c:L2073-L2076][f1]

Object insertion with key ownership.

The const-cast helper returns a mutable pointer. The internal inserter returns false for NULL object, key, or item, or when object and item are the same. With a constant key it stores the supplied pointer and sets the constant-string flag; otherwise it duplicates the key through hooks, returns false on allocation failure, and clears the constant-string flag. It frees an old non-constant key, assigns the new key and type, and delegates to array append. The public wrappers choose non-constant or constant keys.

<a id="u-81503bfafc19"></a>
### `cJSON.c-reference-insertion`

`CJSON_PUBLIC(cJSON_bool) cJSON_AddItemReferenceToArray(cJSON *array, cJSON *item)` · [cJSON.c:L2130-L2138][f1]

Adds a reference copy of an item to an array or object.

Array insertion returns false for a NULL array, otherwise appends the created reference; a NULL reference makes the append fail. Object insertion returns false for a NULL object or key, otherwise inserts the created reference with a non-constant key.

<a id="u-ed8ae47b6c1d"></a>
### `cJSON.c-typed-object-adders`

`CJSON_PUBLIC(cJSON*) cJSON_AddNullToObject(cJSON * const object, const char * const n…` · [cJSON.c:L2150-L2160][f1]

Convenience adders for typed object members.

Each creates a null, true, false, bool, number, string, raw, object, or array item, inserts it with a non-constant key, and returns the created item on success. On insertion failure it deletes the created item and returns NULL. For string and raw creation, a NULL input or allocation failure makes creation return NULL, so insertion fails and the adder returns NULL.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c
