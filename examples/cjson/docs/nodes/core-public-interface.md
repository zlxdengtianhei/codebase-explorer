# Public API & Data Model

**Capability.** Declares the library's contract: the cJSON node struct, hooks struct, calling-convention/export preprocessor setup, and every public function and macro of cJSON.h.

Read cJSON.h here first to learn the API surface. The struct defines the tree layout every other node operates on; the API region documents parse/print/manipulation entry points and their semantics (e.g. Duplicate's recurse behavior, Minify's in-place mutation).

Parent: [Core cJSON Engine](core-json.md)

## Units (4)

<a id="u-77d92a7a23a2"></a>
### `cJSON.h module code (L1–L103)`

`module_region` · [cJSON.h:L1-L103][f1]

Preprocessor setup for the cJSON header: MIT license text, include guard cJSON__h, C linkage for C++, Windows detection, calling-convention macros (CJSON_CDECL/CJSON_STDCALL), symbol-export selection via CJSON_HIDE/EXPORT/IMPORT_SYMBOLS, GNU visibility option, and version macros (1.7.19) before including stddef.h.

Boundary behavior: which CJSON_PUBLIC expansion applies depends entirely on these macros; on non-Windows without CJSON_API_VISIBILITY, CJSON_PUBLIC(type) expands to plain type.

**Notes.**

- condition: Export mode defaults to CJSON_EXPORT_SYMBOLS on Windows only when none of the three symbol-visibility macros is defined.

<a id="u-fa56703f0254"></a>
### `cJSON.h module code (L130–L306)`

`module_region` · [cJSON.h:L130-L306][f1]

Public API declarations plus utility macros: parse family (cJSON_Parse, ParseWithLength, ParseWithOpts, ParseWithLengthOpts with require_null_terminated and return_parse_end), print family (Print, PrintUnformatted, PrintBuffered, PrintPreallocated returning 1/0, Delete), array/object access and membership tests, type predicates (cJSON_Is*), constructors including reference-creating variants, add/detach/replace/insert/delete item operations, Duplicate (recurse!=0 copies children; next/prev NULL on return), Compare, Minify (mutates a writable buffer, in-place), Add*ToObject helpers, allocator wrappers cJSON_malloc/cJSON_free, and iteration/Set-value macros.

Memory contract per comments: callers free Parse results with cJSON_Delete and Print results with an appropriate free, except PrintPreallocated whose buffer is fully caller-owned; the header notes Print may need up to 5 extra bytes beyond its estimate. Nesting and circular-reference limits default to 1000 and 10000 when CJSON_NESTING_LIMIT / CJSON_CIRCULAR_LIMIT are undefined.

**Notes.**

- contract: cJSON_AddItemToObjectCS requires the key string to outlive the object and marks it cJSON_StringIsConst; cJSON_GetObjectItem is case-insensitive while the CaseSensitive variant is exact.
- condition: cJSON_SetBoolValue does nothing and yields cJSON_Invalid unless the object's type already has a True/False bit; cJSON_SetNumberValue returns the number unchanged for NULL objects.

**Uncertainties.**

- Runtime failure modes (NULL returns, parse-error pointer validity) are promised only by comments; implementations are in cJSON.c, not supplied.
- cJSON_CreateIntArray and siblings state out-of-bounds access if count exceeds the array length, but no validation is visible here.

<a id="u-33a8584d726d"></a>
### `cJSON`

`struct cJSON` · [cJSON.h:L103-L123][f1]

Core doubly linked-list node representing one JSON value.

Fields: next/prev walk sibling chains of an array or object; child points to the first item of a nested array/object; type is a bitmask combining one cJSON_* type flag (cJSON_Invalid..cJSON_Raw) plus optional cJSON_IsReference (256) and cJSON_StringIsConst (512) markers; valuestring holds string or raw content, valuedouble numbers, valueint a deprecated int view, and string the key when the item is an object member. Ownership semantics (deep vs. reference items) are governed by cJSON_IsReference but only implemented by cJSON.c functions not visible here.

**Notes.**

- field: Writing to valueint is documented as deprecated; cJSON_SetNumberValue is the sanctioned way to set numbers.
- field: cJSON_StringIsConst marks item->string as not owned, so writers must check it before modifying item->string.

**Uncertainties.**

- Exact type-mask encoding beyond the documented bit values, and memory-ownership behavior, depend on cJSON.c which is not supplied.

<a id="u-eae46ee483e3"></a>
### `cJSON_Hooks`

`struct cJSON_Hooks` · [cJSON.h:L125-L130][f1]

Struct of two allocator function pointers passed to cJSON_InitHooks to replace cJSON's malloc/free.

malloc_fn and free_fn are declared CDECL on Windows so standard malloc/free can be assigned directly regardless of the compiler's default calling convention. Effect of the hooks on actual allocation is implemented in cJSON.c, not here.

**Uncertainties.**

- Behavior when hooks are NULL or partially set is determined by cJSON_InitHooks' implementation, not visible in this header.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.h