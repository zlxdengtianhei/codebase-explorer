# Public Header Types and Macros

**Capability.** Declares the public cJSON API, node structure, allocator hooks, iteration macro, and compile-time configuration.

Come here for the public header surface that defines cJSON types, macros, and API declarations. It groups node layout, allocator hooks, parse limits, calling convention, and value-changing macros.

Parent: [cJSON JSON Library](cjson-json-library.md)

## Units (7)

<a id="u-99598287dabf"></a>
### `cJSON.h module code (L297–L306)`

`module_region` · [cJSON.h:L297-L306][f1]

Declares the array iteration macro and allocator entry points.

cJSON_ArrayForEach initializes element to NULL when array is NULL, otherwise to array->child, and advances through next until NULL. cJSON_malloc and cJSON_free are declared to allocate and free using the hooks set by cJSON_InitHooks; their implementations are not in this header.

<a id="u-caa6a1d9b973"></a>
### `cJSON.h module code (L144–L280)`

`module_region` · [cJSON.h:L144-L280][f1]

Declares the main cJSON API for parsing, printing, traversal, creation, mutation, comparison, and minification.

The header documents these contracts:
- parse results: freed with cJSON_Delete.
- print results: freed with stdlib free, the configured free hook, or cJSON_free, except PrintPreallocated where the caller owns the buffer.
- ParseWithOpts: can require null termination and return the final parse pointer; on failure a supplied return_parse_end points to the error and matches cJSON_GetErrorPtr.
- PrintPreallocated: returns 1 on success and 0 on failure; size estimates are not exact, so about 5 extra bytes may be needed.
- PrintBuffered: takes a prebuffer guess and a format flag.
- GetArrayItem: returns NULL on failure.
- object lookup: case-insensitive unless the CaseSensitive variant is used.
- GetErrorPtr: defined when Parse returns 0 and 0 on success.
- reference creators: CreateStringReference, CreateObjectReference, and CreateArrayReference create nodes whose referenced data is not freed by cJSON_Delete.
- Create*Array: count must not exceed the input element count or access is out of bounds.
- AddItemToObjectCS: check cJSON_StringIsConst before writing item->string.
- Duplicate: returns new memory, duplicates children when recurse is nonzero, and always zeroes next and prev.
- Compare: treats NULL or invalid inputs as unequal and uses case_sensitive for object keys.
- Minify: removes blank characters and requires a writable input buffer.
- Add*ToObject helpers: return the added item or NULL on failure.
Implementations are not in this header, so exact failure paths beyond these comments are not established.

<a id="u-33a8584d726d"></a>
### `cJSON`

`struct cJSON struct cJSON cJSON` · [cJSON.h:L103-L123][f1]

Defines the JSON node structure used by the API.

next and prev link sibling nodes; child points to the first child of an array or object; type holds the node type flags; valuestring holds string or raw text; valueint is deprecated and valuedouble holds numeric value; string holds the object member name when the node is an object child. The header does not define ownership or mutation rules beyond these field comments.

<a id="u-eae46ee483e3"></a>
### `cJSON_Hooks`

`struct cJSON_Hooks` · [cJSON.h:L125-L130][f1]

Holds allocator hooks for cJSON.

malloc_fn and free_fn are function pointers using CJSON_CDECL, so Windows callers can pass CDECL malloc/free directly. The InitHooks comment mentions realloc, but this struct exposes only malloc and free hooks; no realloc field is present.

<a id="u-6717e127a40a"></a>
### `cJSON.h-limits-and-bool-type`

`#define CJSON_NESTING_LIMIT 1000` · [cJSON.h:L137-L137][f1]

Defines the boolean type and compile-time parse limits.

cJSON_bool is int. CJSON_NESTING_LIMIT defaults to 1000 and CJSON_CIRCULAR_LIMIT defaults to 10000 unless already defined; the comments say parsing rejects deeper nesting or longer circular references to prevent stack overflows. The header does not show the enforcement code.

<a id="u-349e0301ac9c"></a>
### `cJSON.h-platform-and-visibility-macros`

`#define __WINDOWS__` · [cJSON.h:L32-L32][f1]

Selects calling convention and symbol visibility for the public API.

__WINDOWS__ is auto-defined when not already set and any of WIN32, WIN64, _MSC_VER, or _WIN32 is defined. On Windows, CJSON_CDECL is __cdecl and CJSON_STDCALL is __stdcall; if none of CJSON_HIDE_SYMBOLS, CJSON_IMPORT_SYMBOLS, or CJSON_EXPORT_SYMBOLS is defined, CJSON_EXPORT_SYMBOLS is defined. CJSON_PUBLIC(type) is chosen in order: CJSON_HIDE_SYMBOLS gives type CJSON_STDCALL; else CJSON_EXPORT_SYMBOLS gives __declspec(dllexport) type CJSON_STDCALL; else CJSON_IMPORT_SYMBOLS gives __declspec(dllimport) type CJSON_STDCALL. Thus hide wins over import when both are defined, and export wins over import when both are defined. On non-Windows, CJSON_CDECL and CJSON_STDCALL are empty; CJSON_PUBLIC(type) is __attribute__((visibility("default"))) type when GCC or Sun compiler and CJSON_API_VISIBILITY are defined, otherwise plain type.

<a id="u-7d7b055d02a5"></a>
### `cJSON.h-value-setters`

`#define cJSON_SetIntValue(object, number) ((object) ? (object)->valueint = (object)->…` · [cJSON.h:L281-L281][f1]

Groups macros and declarations that change a node value.

cJSON_SetIntValue: if object is non-NULL, assigns both valueint and valuedouble to number and yields the assigned value; if NULL, yields number without assignment. cJSON_SetNumberValue: if object is non-NULL, calls cJSON_SetNumberHelper with the number cast to double and yields the helper result; if NULL, yields number. The header only declares cJSON_SetNumberHelper, so side effects such as whether valueint is updated are not established here. cJSON_SetValuestring is declared to change valuestring only when the object type is cJSON_String; its implementation and failure semantics are not in this header. cJSON_SetBoolValue: if object is non-NULL and its type has cJSON_False or cJSON_True set, clears those bits and sets cJSON_True for nonzero boolValue or cJSON_False otherwise, yielding the new type; otherwise yields cJSON_Invalid and does not modify the object.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.h
