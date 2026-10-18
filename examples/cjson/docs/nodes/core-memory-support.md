# Memory & Shared Support

**Capability.** Centralizes allocation abstraction (internal_hooks/global_hooks, InitHooks, public cJSON_malloc/free, strdup) and small shared helpers, so parsing, printing, and manipulation all funnel through one swappable memory layer.

Use this node when tracing allocation behavior or installing custom hooks. Every other core node depends on it for node creation, string duplication, and tiny shared routines; replace the hooks here to change memory policy library-wide.

**Depended on by.**

- [Convenience Constructors & Setters](core-constructors.md) · graph-confirmed · 16 edge(s) · Convenience constructors allocate new items and duplicate strings via the central memory/new-item helpers.
- [JSON Text Parsing](core-parsing.md) · graph-confirmed · 4 edge(s) · Parsing allocates nodes and frees partially built trees on parse failure through the memory layer.
- [JSON Serialization](core-printing.md) · graph-confirmed · 6 edge(s) · Printers use the shared internal utilities and allocate output buffers through the memory layer.
- [Tree Construction & Mutation](core-tree-mutation.md) · graph-confirmed · 8 edge(s) · Deep duplication and object installation allocate via new-item/strdup and free replaced items via cJSON_Delete.
- [cJSON Utilities \(RFC Layer\)](json-utils.md) · graph-confirmed · 22 edge(s) · The utilities layer performs its allocations through cJSON's public malloc/free wrappers.
- [Diff & Merge Patches](utils-diff-merge.md) · graph-only · 8 edge(s)
- [JSON Pointer \(RFC 6901\)](utils-json-pointer.md) · graph-only · 7 edge(s)
- [JSON Patch Application \(RFC 6902\)](utils-patching.md) · graph-only · 6 edge(s)

Parent: [Core cJSON Engine](core-json.md)

## Units (6)

<a id="u-339dd175eeaa"></a>
### `cJSON_InitHooks`

`CJSON_PUBLIC(void) cJSON_InitHooks(cJSON_Hooks* hooks)` · [cJSON.c:L209-L238][f1]

Installs custom allocation hooks into global_hooks.

A NULL argument resets all three hooks to malloc/free/realloc. Otherwise allocate/deallocate start as malloc/free and are overridden by any non-NULL malloc_fn/free_fn. reallocate is set to realloc only when both final hooks are still plain malloc and free; if any custom hook is installed, reallocate becomes NULL, which forces ensure and print onto their allocate+memcpy+deallocate fallback paths. Side effect: mutates global state used by every later library call.

**Uncertainties.**

- Relies on pointer identity of malloc/free to decide whether custom hooks are installed; custom allocators that wrap the libc functions still disable realloc.

<a id="u-d81891a80458"></a>
### `cJSON.c-allocator-plumbing`

`struct internal_hooks` · [cJSON.c:L156-L161][f1]

Allocator abstraction for the whole library: an internal_hooks struct of allocate/deallocate/reallocate function pointers, MSVC-only thin wrappers (internal_malloc, internal_free, internal_realloc) satisfying the dllimport address-of restriction, and the global_hooks instance initialized to malloc/free/realloc.

On non-MSVC builds internal_malloc/free/realloc are macros expanding directly to the libc functions, so no wrapper symbols exist.

**Notes.**

- contract: Every library allocation goes through these hooks, so cJSON_InitHooks changes the behavior of all parsing, printing, and freeing.

<a id="u-185de959721c"></a>
### `cJSON.c-public-allocators`

`CJSON_PUBLIC(void *) cJSON_malloc(size_t size)` · [cJSON.c:L3197-L3200][f1]

Public allocator entry points forwarding to the currently installed hooks: cJSON_malloc returns global_hooks.allocate(size), cJSON_free calls global_hooks.deallocate(object).

The local 'object = NULL' in cJSON_free affects only the parameter copy, not the caller's pointer.

<a id="u-e8a9f7d7fb70"></a>
### `cJSON_strdup`

`static unsigned char* cJSON_strdup(const unsigned char* string, const internal_hooks …` · [cJSON.c:L188-L207][f1]

Duplicates a NUL-terminated byte string using the supplied hooks.

Returns NULL for a NULL input or allocation failure; otherwise allocates strlen+1 bytes, memcpy's the string including the terminator, and returns it. The caller must release the buffer with the same hooks' deallocate.

uses: [cJSON.c-allocator-plumbing](core-memory-support.md#u-d81891a80458)

<a id="u-0840a192aac8"></a>
### `cJSON_New_Item`

`static cJSON *cJSON_New_Item(const internal_hooks * const hooks)` · [cJSON.c:L241-L250][f1]

Allocates one cJSON node via the given hooks and memsets it to zero, so type is cJSON_Invalid and all pointers are NULL.

Returns NULL when allocation fails.

<a id="u-5c575837ef16"></a>
### `cJSON.c-internal-utilities`

`static unsigned char get_decimal_point(void)` · [cJSON.c:L279-L287][f1]

Small shared helpers.

get_decimal_point returns localeconv()->decimal_point[0] only when ENABLE_LOCALES is defined, otherwise always '.'. update_offset advances a printbuffer's offset by strlen of the string starting at the current offset, ignoring NULL buffers. compare_double treats doubles as equal when |a-b| <= max(|a|,|b|)*DBL_EPSILON, so values differing only in insignificant digits compare equal.

**Notes.**

- contract: compare_double's relative tolerance governs equality in cJSON_Compare and print_number's round-trip check.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c