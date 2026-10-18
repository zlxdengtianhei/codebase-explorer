# JSON Serialization

**Capability.** Renders a cJSON tree back to text: public print APIs over an internal print/printbuffer machinery, a per-type value writer recursing into array/object/number/string printers, and a growable printbuffer (ensure) backing all output.

Use this subtree for formatting, output-buffer, or preallocation questions. print_value is the type dispatch hub; ensure is the only place output buffers grow, so buffer bugs converge there.

**Depends on.**

- [Memory & Shared Support](core-memory-support.md) · graph-confirmed · 6 edge(s) · Printers use the shared internal utilities and allocate output buffers through the memory layer.

Parent: [Core cJSON Engine](core-json.md)

## Units (8)

<a id="u-f7cfd6dcdea2"></a>
### `cJSON.c-print-apis`

`CJSON_PUBLIC(char *) cJSON_Print(const cJSON *item)` · [cJSON.c:L1307-L1310][f1]

Public printing entries over the internal print/printbuffer machinery.

cJSON_Print and cJSON_PrintUnformatted call print with format true/false and return a caller-freed string, NULL on failure. cJSON_PrintBuffered rejects negative prebuffer, allocates a prebuffer-sized growing buffer, and on print_value failure frees it and returns NULL. cJSON_PrintPreallocated writes into a caller buffer: negative length or NULL buffer returns false, noalloc is set so ensure refuses any growth, and the print_value result is returned directly.

<a id="u-ebad7f4e168a"></a>
### `print`

`static unsigned char *print(const cJSON * const item, cJSON_bool format, const intern…` · [cJSON.c:L1239-L1304][f1]

Renders an item into a freshly allocated NUL-terminated string.

It allocates a 256-byte printbuffer through the hooks (allocation failure fails), prints via print_value (failure fails), then update_offset finalizes the length. If hooks->reallocate is available the buffer is shrunk in place with realloc to offset+1 (realloc failure fails); otherwise a new buffer of offset+1 bytes is allocated, the output is memcpy'd (min of length and offset+1), the NUL is forced, and the original buffer freed. The fail path frees any remaining buffer and printed pointer and returns NULL, so all failure returns are NULL without leaks.

calls: [print_value](core-printing.md#u-3f5cf3a5e49e), [cJSON.c-internal-utilities](core-memory-support.md#u-5c575837ef16)

<a id="u-3f5cf3a5e49e"></a>
### `print_value`

`static cJSON_bool print_value(const cJSON * const item, printbuffer * const output_bu…` · [cJSON.c:L1423-L1494][f1]

Writes one item as JSON text according to type & 0xFF.

NULL item or output_buffer returns false. cJSON_NULL/False/True reserve 5/6/5 bytes via ensure and strcpy the literal; ensure failure returns false. Numbers, strings, arrays, and objects delegate to print_number, print_string, print_array, print_object. cJSON_Raw fails when valuestring is NULL, otherwise reserves strlen+1 and memcpy's the raw text (including terminator) into the buffer. Any other type returns false.

calls: [print_number](core-printing.md#u-23f8c0af73d3), [print_string_ptr](core-printing.md#u-c6e0866b50b4), [print_array](core-printing.md#u-41f81398f144), [print_object](core-printing.md#u-bf98d244dfc4)

<a id="u-41f81398f144"></a>
### `print_array`

`static cJSON_bool print_array(const cJSON * const item, printbuffer * const output_bu…` · [cJSON.c:L1595-L1659][f1]

Writes an array's children as '[elem,elem]'.

NULL output_buffer or depth at/above CJSON_NESTING_LIMIT returns false. It writes '[', increments depth, then for each child prints via print_value (failure returns false immediately, leaving the buffer partially written), update_offset, and appends ',' plus an extra space when format is set. Finally it writes ']' and NUL and decrements depth. Elements are printed in child order with no size precomputation.

calls: [print_value](core-printing.md#u-3f5cf3a5e49e)

<a id="u-bf98d244dfc4"></a>
### `print_object`

`static cJSON_bool print_object(const cJSON * const item, printbuffer * const output_b…` · [cJSON.c:L1780-L1896][f1]

Writes object members as '{"key":value,...}'.

NULL output_buffer or depth at/above CJSON_NESTING_LIMIT returns false. It writes '{' (plus '\n' when format), then per child: when format, writes depth-many tabs; prints the key with print_string_ptr, then ':' (plus '\t' when format), the value with print_value, and ',' plus '\n' when formatted unless the item is last, calling update_offset after string and value prints. Any ensure/print failure returns false with partial output. The close writes depth-1 tabs when format, '}', and NUL, decrementing depth.

calls: [print_string_ptr](core-printing.md#u-c6e0866b50b4), [print_value](core-printing.md#u-3f5cf3a5e49e)

<a id="u-23f8c0af73d3"></a>
### `print_number`

`static cJSON_bool print_number(const cJSON * const item, printbuffer * const output_b…` · [cJSON.c:L596-L663][f1]

Renders an item's double into the printbuffer.

NULL output_buffer returns false. NaN or infinity prints 'null'. If d equals (double)valueint it prints as an integer with %d; otherwise it tries '%1.15g' and re-parses with sscanf plus compare_double; when the original value cannot be recovered it reprints with '%1.17g'. A negative sprintf length or a result longer than the 26-byte scratch buffer returns false. It then reserves length+1 bytes via ensure (NULL means failure), copies the bytes replacing the locale decimal point with '.', appends '\0', advances the offset, and returns true.

<a id="u-c6e0866b50b4"></a>
### `print_string_ptr`

`static cJSON_bool print_string_ptr(const unsigned char * const input, printbuffer * c…` · [cJSON.c:L954-L1073][f1]

Writes a C string into the printbuffer as an escaped JSON string literal.

NULL output_buffer returns false. A NULL input prints the two-character literal "". A first pass counts characters needing escapes: quote, backslash, and the five named control characters add one escape each; other bytes below 32 add five (a \uXXXX sequence). It reserves input length + escapes + 2 quotes via ensure (failure returns false). With no escapes it memcpy's directly between quotes; otherwise each special byte is written as a two-character escape, and bytes below 32 are written with sprintf "u%04x" advancing the write cursor four extra places. Ends with quote and NUL.

<a id="u-20e3fb2f41a7"></a>
### `ensure`

`static unsigned char* ensure(printbuffer * const p, size_t needed)` · [cJSON.c:L490-L573][f1]

Grows a printbuffer so at least 'needed' bytes plus a terminator are writable at the current offset, returning a write pointer there.

Returns NULL when p or p->buffer is NULL, when offset is already at or past length, or when needed exceeds INT_MAX. If offset+needed+1 fits the current length the existing buffer pointer is returned unchanged. In noalloc mode (caller-supplied buffer) any growth need returns NULL instead of reallocating. Otherwise the new size is needed*2, clamped to INT_MAX when doubling would overflow and returning NULL if even INT_MAX is insufficient. Reallocation via hooks->reallocate when available, else allocate+memcpy(offset+1 bytes)+deallocate; in both paths allocation failure frees the old buffer, zeroes length and buffer, and returns NULL.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c