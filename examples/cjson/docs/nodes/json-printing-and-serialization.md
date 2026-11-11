# JSON printing and serialization

**Capability.** Renders cJSON trees to strings, growing output buffers and escaping strings as needed.

Serialization lives here: buffer growth, per-type value rendering, array/object formatting, and string escaping. Print and PrintUnformatted entry points expose formatted and compact output.

**Depends on.**

- [Item Utility Toolkit](item-utility-toolkit.md) · graph-confirmed · 1 edge(s) · Serialization uses shared item utilities while walking and rendering trees.
- [Comparison and lookup helpers](comparison-and-lookup-helpers.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Item Utility Toolkit](item-utility-toolkit.md) · graph-confirmed · 3 edge(s)
- [Core item manipulation utilities](core-item-manipulation-utilities.md) · graph-only · 2 edge(s)
- [Comparison and lookup helpers](comparison-and-lookup-helpers.md) · graph-only · 1 edge(s)

Parent: [cJSON JSON Library](cjson-json-library.md)

## Units (8)

<a id="u-20e3fb2f41a7"></a>
### `ensure`

`static unsigned char* ensure(printbuffer * const p, size_t needed)` · [cJSON.c:L490-L573][f1]

Grows a printbuffer so at least 'needed' bytes are writable at the current offset, returning a pointer there.

It returns NULL for a NULL buffer/buffer, when offset is already at or past length, when needed exceeds INT_MAX, when the request already fits is fine (returns in-buffer pointer), or when the buffer is noalloc and growth is required. New size is needed*2 clamped to INT_MAX (returns NULL if even that is insufficient). If hooks.reallocate exists it reallocs; otherwise it allocates, copies offset+1 bytes, and frees the old buffer. On any allocation failure it frees the old buffer, sets buffer NULL and length 0, and returns NULL, so the printbuffer is unusable afterwards.

<a id="u-ebad7f4e168a"></a>
### `print`

`static unsigned char *print(const cJSON * const item, cJSON_bool format, const intern…` · [cJSON.c:L1239-L1304][f1]

Renders an item tree to a freshly allocated NUL-terminated string.

It allocates a 256-byte printbuffer, runs print_value, then update_offset, and shrinks: with hooks.reallocate it reallocs to offset+1 bytes; otherwise it allocates a new buffer of offset+1, copies min(length, offset+1) bytes, forces a terminator, and frees the old buffer. Any failure (initial allocation, print_value, or a later allocation) frees both the working buffer and any partial result and returns NULL.

<a id="u-41f81398f144"></a>
### `print_array`

`static cJSON_bool print_array(const cJSON * const item, printbuffer * const output_bu…` · [cJSON.c:L1595-L1659][f1]

Prints an array as '[' elements separated by ',' (plus a space when formatted) ']'.

It enforces the nesting limit, ensures one byte for '[', increments depth, and for each child calls print_value and update_offset, ensuring and emitting the separator when a next element exists. Any ensure or print failure returns false; on success it emits ']', decrements depth, and returns true. An empty array prints as "[]".

<a id="u-bf98d244dfc4"></a>
### `print_object`

`static cJSON_bool print_object(const cJSON * const item, printbuffer * const output_b…` · [cJSON.c:L1780-L1896][f1]

Prints an object with '{', then per child: a depth-count of tabs when formatted, the escaped key via print_string_ptr, ':' (plus a tab when formatted), the value via print_value, and ',' plus a newline when formatted and another member follows.

It enforces the nesting limit and returns false on any ensure or print failure; on success it emits depth-1 tabs (formatted), '}', and decrements depth.

<a id="u-3f5cf3a5e49e"></a>
### `print_value`

`static cJSON_bool print_value(const cJSON * const item, printbuffer * const output_bu…` · [cJSON.c:L1423-L1494][f1]

Renders one item according to its low type byte: null/false/true are strcpy'd after ensure; Number delegates to print_number; Raw requires a non-NULL valuestring and memcpy's it including the terminator; String delegates to print_string; Array and Object to their printers.

NULL item or output buffer, an unknown type, or any ensure/print failure returns false.

<a id="u-dd64117dae4e"></a>
### `update_offset`

`static void update_offset(printbuffer * const buffer)` · [cJSON.c:L576-L586][f1]

Advances a printbuffer's offset by the strlen of the NUL-terminated text at the current offset; a no-op for a NULL buffer or buffer pointer.

<a id="u-c116fbae90f0"></a>
### `cJSON.c-print-entrypoints`

`CJSON_PUBLIC(char *) cJSON_Print(const cJSON *item)` · [cJSON.c:L1307-L1310][f1]

cJSON_Print and cJSON_PrintUnformatted render an item via the shared print routine with formatting (newlines/tabs) on and off respectively, using the global hooks.

<a id="u-e38c755019ce"></a>
### `cJSON.c-string-printing`

`static cJSON_bool print_string_ptr(const unsigned char * const input, printbuffer * c…` · [cJSON.c:L954-L1073][f1]

print_string_ptr renders a C string as a quoted, escaped JSON string into the printbuffer; print_string applies it to an item's valuestring.

A NULL input prints as an empty "" string. Otherwise it counts escapes: the seven short escapes add 1 character each, other bytes below 32 add 5 (\uXXXX form). It ensures length+3 bytes (failure returns false); with no escapes it wraps the raw bytes in quotes, otherwise it copies, emitting backslash escapes for \ " and control characters, with control characters not in the short list printed as \u%04x via sprintf. Always NUL-terminates and returns true unless ensure fails or the output buffer is NULL.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c
