# JSON parser

**Capability.** Parses JSON text into cJSON trees, handling values, arrays, objects, strings, numbers, and literals.

The recursive-descent parsing core: buffer setup, BOM skipping, whitespace handling, and per-type parse routines. Public Parse wrappers delegate to the length-delimited core here.

**Depends on.**

- [Item Utility Toolkit](item-utility-toolkit.md) · graph-confirmed · 2 edge(s)
- [Node construction and linking](node-construction-and-linking.md) · graph-confirmed · 6 edge(s) · The parser builds trees by calling the typed node constructors and linking helpers.
- [Comparison and lookup helpers](comparison-and-lookup-helpers.md) · graph-only · 1 edge(s)
- [Core item manipulation utilities](core-item-manipulation-utilities.md) · graph-only · 1 edge(s)

Parent: [cJSON JSON Library](cjson-json-library.md)

## Units (9)

<a id="u-7df91d7724e7"></a>
### `buffer_skip_whitespace`

`static parse_buffer *buffer_skip_whitespace(parse_buffer * const buffer)` · [cJSON.c:L1090-L1113][f1]

Advances the parse buffer offset past bytes <= 32 (whitespace, control chars).

NULL buffer or content returns NULL; an already-exhausted buffer is returned unchanged. If skipping reaches the end, the offset is stepped back by one so the terminator position stays accessible.

<a id="u-eb694a324479"></a>
### `cJSON_ParseWithLengthOpts`

`CJSON_PUBLIC(cJSON *) cJSON_ParseWithLengthOpts(const char *value, size_t buffer_leng…` · [cJSON.c:L1147-L1224][f1]

Core length-delimited parser: builds a parse_buffer over the given bytes, resets the global error, allocates a root item, and parses one value after skipping whitespace and an optional BOM.

With require_null_terminated it then skips trailing whitespace and fails unless the buffer is exhausted or a NUL is reached. On success it stores the end pointer in *return_parse_end if provided and returns the item. On any failure (NULL/empty input, allocation failure, parse failure, or the null-terminated check) it deletes the partial item, sets global_error to the input with the failing offset (or length-1 if past the end), writes the error position to *return_parse_end if provided, and returns NULL.

<a id="u-30a4b7f9acd5"></a>
### `parse_array`

`static cJSON_bool parse_array(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L1497-L1592][f1]

Parses a bracket-delimited, comma-separated value list into an array item.

It enforces CJSON_NESTING_LIMIT on depth (failure without consuming), consumes '[', and accepts ']' immediately for an empty array. Otherwise it loops: allocates a child, links it into the next/prev chain, skips whitespace, and parses a value; any allocation or value-parse failure, or a missing ']' terminator, deletes the whole child list and returns false. On success it decrements depth, sets head->prev to the last item (the tail pointer used for O(1) appends), marks the item cJSON_Array with child=head, and advances past ']'.

<a id="u-760302b8669d"></a>
### `parse_number`

`static cJSON_bool parse_number(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L307-L408][f1]

Parses a JSON number at the buffer offset into item.

It first scans digits, signs, exponent letters and '.', stopping at the first other character, then copies that span into a heap buffer (allocation failure returns false), rewrites '.' to the locale decimal point, and calls strtod. If strtod consumes nothing (after_end equals the start) it frees the buffer and returns false. On success it sets valuedouble, saturates valueint to INT_MAX/INT_MIN on overflow, sets type cJSON_Number, advances the buffer offset by the consumed length, frees the temp buffer, and returns true. Note the scan accepts characters strtod may reject (e.g. 'e' without digits), in which case the strtod-no-consumption path fails the parse.

<a id="u-1a792e084df9"></a>
### `parse_object`

`static cJSON_bool parse_object(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L1662-L1777][f1]

Parses a brace-delimited object.

It enforces the nesting limit, consumes '{', and accepts '}' for an empty object. Per member it allocates a child, parses a string name, moves it from valuestring to the string field, requires ':' and then parses the value; any failure (allocation, name, colon, value, or missing '}') deletes the accumulated children and returns false. On success it decrements depth, sets head->prev to the tail, marks the item cJSON_Object with child=head, and advances past '}'.

<a id="u-79bc6a512446"></a>
### `parse_string`

`static cJSON_bool parse_string(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L824-L951][f1]

Parses a double-quoted JSON string at the buffer offset into a heap-allocated, unescaped, NUL-terminated valuestring.

It first measures the literal, rejecting a trailing lone backslash or a missing closing quote, and allocates an overestimated output size (escape bytes are skipped in the estimate); allocation failure fails. The copy loop passes plain bytes through and decodes \b \f \n \r \t \" \\ \/ and \u via utf16_literal_to_utf8; any other escape or a zero-length conversion fails. On success it sets type cJSON_String, stores valuestring, and moves the offset past the closing quote. On any failure it frees the partial output and rewinds the offset to the input pointer (or leaves it at the opening quote position), returning false.

<a id="u-cbca5889a6b8"></a>
### `parse_value`

`static cJSON_bool parse_value(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L1368-L1420][f1]

Dispatches on the first readable character(s) of the buffer: literal "null"/"true"/"false" (bounds-checked with can_read) set the type and advance; '"' delegates to parse_string; '-' or a digit to parse_number; '[' to parse_array; '{' to parse_object.

A NULL buffer/content or no matching case returns false without consuming input.

<a id="u-84f93c6ae406"></a>
### `skip_utf8_bom`

`static parse_buffer *skip_utf8_bom(parse_buffer * const buffer)` · [cJSON.c:L1116-L1129][f1]

Skips a UTF-8 BOM at the very start of a parse buffer by advancing the offset 3 bytes when the EF BB BF prefix is present; returns NULL for a NULL buffer/content or a non-zero offset, otherwise the buffer.

<a id="u-0d57b2c47d88"></a>
### `cJSON.c-parse-entrypoints`

`CJSON_PUBLIC(cJSON *) cJSON_ParseWithOpts(const char *value, const char **return_pars…` · [cJSON.c:L1131-L1144][f1]

Convenience wrappers around the length-based core: cJSON_ParseWithOpts strlen's the input (plus terminator) and delegates; cJSON_Parse calls it with no end pointer and no null-termination requirement; cJSON_ParseWithLength passes the explicit length through.

All failure semantics come from the core parser.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c
