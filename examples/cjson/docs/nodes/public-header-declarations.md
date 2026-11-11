# Public header declarations

**Capability.** Declares the cJSON API: node structure, type bits, macros, allocator hooks, and version constants.

This is the interface contract: the cJSON node layout, type and flag constants, convenience macros, iteration macro, and all function declarations. No behavior lives here, only documented signatures and defaults.

Parent: [cJSON JSON Library](cjson-json-library.md)

## Units (14)

<a id="u-2231cef66d00"></a>
### `cJSON_Invalid`

`#define cJSON_Invalid (0) #define cJSON_False (1 << 0) #define cJSON_True (1 << 1) #d…` · [cJSON.h:L89-L100][f1]

Defines the cJSON type bit constants (Invalid=0, False, True, NULL, Number, String, Array, Object, Raw as distinct bits) plus the internal flags cJSON_IsReference (256) and cJSON_StringIsConst (512) that mark items whose memory or key string is not owned by cJSON.

<a id="u-993bf480c818"></a>
### `cJSON_SetBoolValue`

`#define cJSON_SetBoolValue(object, boolValue) ( \ (object != NULL && ((object)->type …` · [cJSON.h:L289-L296][f1]

Macro that flips an item's boolean type in place: if object is non-NULL and its type has the cJSON_False or cJSON_True bit, it clears both bits and sets cJSON_True when boolValue is truthy, else cJSON_False, yielding the new type.

If object is NULL or not boolean-typed, nothing is changed and the expression evaluates to cJSON_Invalid.

<a id="u-5f685b1f2825"></a>
### `cJSON_SetIntValue`

`#define cJSON_SetIntValue(object, number) ((object) ? (object)->valueint = (object)->…` · [cJSON.h:L281-L281][f1]

Macro that assigns an integer to a cJSON item, writing both valueint and valuedouble so the two stay consistent; if object is NULL it evaluates to the number with no assignment.

Note it does not change the item's type.

<a id="u-8c8d898be57c"></a>
### `cJSON_SetNumberValue`

`#define cJSON_SetNumberValue(object, number) ((object != NULL) ? cJSON_SetNumberHelpe…` · [cJSON.h:L284-L284][f1]

Macro that sets a numeric value via cJSON_SetNumberHelper: when object is non-NULL it calls the helper with the value cast to double (which per the header also updates valueint); when object is NULL it evaluates to the number unchanged.

The helper's exact side effects are not visible in this header.

<a id="u-da5ad250c69f"></a>
### `cJSON_bool`

`typedef int cJSON_bool;` · [cJSON.h:L132-L132][f1]

Aliases cJSON_bool to int, the return type used for all predicate and success/failure APIs in this header.

<a id="u-5f50da753c86"></a>
### `cJSON.h module code (L282–L283)`

`module_region` · [cJSON.h:L282-L283][f1]

Declares the remaining API surface without implementation: type predicates (cJSON_IsInvalid through cJSON_IsRaw), value getters (GetStringValue/GetNumberValue), item constructors including reference variants (CreateStringReference/ObjectReference/ArrayReference create items that do not own their contents, so cJSON_Delete will not free them), typed array builders (count must not exceed the source array length or access goes out of bounds), add/insert/replace/detach/delete mutators, cJSON_Duplicate (with recurse!=0 duplicating children; next/prev are always NULL on the returned copy), cJSON_Compare (NULL or invalid items compare unequal; case_sensitive controls key matching), and cJSON_Minify, which strips whitespace in place and therefore must not receive a read-only buffer such as a string literal.

cJSON_AddItemToObjectCS requires the key string to outlive the object and callers must check the cJSON_StringIsConst flag before writing item->string.

<a id="u-dd467cb80c8e"></a>
### `cJSON.h module code (L285–L288)`

`module_region` · [cJSON.h:L285-L288][f1]

Declares cJSON_SetValuestring(object, valuestring), documented to replace the valuestring of a cJSON_String item only; it has no effect when the item's type is not cJSON_String.

Return and ownership semantics are not visible here.

<a id="u-99598287dabf"></a>
### `cJSON.h module code (L297–L306)`

`module_region` · [cJSON.h:L297-L306][f1]

cJSON_ArrayForEach(element, array) is a C99 for-loop header that starts element at array->child (or NULL if array is NULL) and advances via element->next, so it walks array elements or object members uniformly.

Also declares cJSON_malloc/cJSON_free, which allocate using the hooks installed via cJSON_InitHooks, letting callers allocate memory with the same allocator cJSON itself uses.

<a id="u-caa6a1d9b973"></a>
### `cJSON.h module code (L144–L280)`

`module_region` · [cJSON.h:L144-L280][f1]

Declares the parse/print/delete and access API surface only; behavior is documented in comments, not implemented here.

Contract highlights from the comments: callers own results of cJSON_Parse* (free with cJSON_Delete) and cJSON_Print* (free with stdlib free, hooks free_fn, or cJSON_free), except cJSON_PrintPreallocated where the caller fully owns the supplied buffer and must allocate about 5 bytes more than needed because cJSON's size estimate is not always exact. cJSON_ParseWithOpts can require null termination and report the final parsed byte; on failure a supplied return_parse_end receives the error pointer matching cJSON_GetErrorPtr. cJSON_GetObjectItem is documented as case insensitive; GetArrayItem returns NULL on failure; cJSON_GetErrorPtr is meaningful only when a parse returned 0.

<a id="u-33a8584d726d"></a>
### `cJSON`

`struct cJSON struct cJSON cJSON` · [cJSON.h:L103-L123][f1]

The core tree node: doubly-linked siblings via next/prev, a child chain head for array/object contents, an int type holding one of the type bits plus internal flags, and value fields.

valuestring holds the string for cJSON_String and cJSON_Raw items; valueint is a deprecated direct-write field (use cJSON_SetNumberValue instead); valuedouble stores numbers; string is the item's key when it is a member of an object. Ownership semantics are governed by the IsReference/StringIsConst flags, which tell cJSON_Delete to skip freeing that memory.

<a id="u-eae46ee483e3"></a>
### `cJSON_Hooks`

`struct cJSON_Hooks` · [cJSON.h:L125-L130][f1]

Structure of two function pointers for custom allocation: malloc_fn(size_t) returning void* and free_fn(void*), both declared with CJSON_CDECL so plain stdlib malloc/free can be passed directly on Windows regardless of the compiler's default calling convention.

Passed to cJSON_InitHooks.

<a id="u-fdcd328b32f1"></a>
### `cJSON.h-parse-limits`

`#define CJSON_NESTING_LIMIT 1000` · [cJSON.h:L137-L137][f1]

Guarded defaults for parser safety limits: CJSON_NESTING_LIMIT (1000) caps array/object nesting depth and CJSON_CIRCULAR_LIMIT (10000) caps circular-reference length, both to prevent stack overflows; each is only defined if not already defined, so builds can override either via compiler flags.

<a id="u-349e0301ac9c"></a>
### `cJSON.h-platform-and-visibility-macros`

`#define __WINDOWS__` · [cJSON.h:L32-L32][f1]

These preprocessor regions define calling-convention and symbol-export macros so the same header builds on Windows and non-Windows toolchains.

__WINDOWS__ is auto-defined when WIN32, WIN64, _MSC_VER, or _WIN32 is defined and __WINDOWS__ is not already set. On Windows, CJSON_CDECL/CJSON_STDCALL become __cdecl/__stdcall; CJSON_EXPORT_SYMBOLS is defined by default unless CJSON_HIDE_SYMBOLS or CJSON_IMPORT_SYMBOLS is already defined, and CJSON_PUBLIC(type) then expands to plain type, __declspec(dllexport) type, or __declspec(dllimport) type respectively (hide+import together leaves CJSON_PUBLIC undefined, a real configuration hazard). Off Windows the cdecl/stdcall macros are empty, and CJSON_PUBLIC adds __attribute__((visibility("default"))) only for GCC/Sun compilers when CJSON_API_VISIBILITY is defined, otherwise it is just the type.

<a id="u-fff8a8c97ad7"></a>
### `cJSON.h-version-macros`

`#define CJSON_VERSION_MAJOR 1 #define CJSON_VERSION_MINOR 7 #define CJSON_VERSION_PAT…` · [cJSON.h:L82-L84][f1]

Defines the library version as three integer macros: major 1, minor 7, patch 19; cJSON_Version() returns these as a string.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.h
