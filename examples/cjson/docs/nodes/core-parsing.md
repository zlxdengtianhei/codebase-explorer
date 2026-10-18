# JSON Text Parsing

**Capability.** Converts JSON text into a cJSON tree: entry points that set up the parse buffer, a value dispatcher recursing into string/number/array/object parsers, UTF-16 escape decoding, buffer-position skip helpers, and in-place minification of JSON text.

Use this subtree to understand how bytes become a tree, or to fix parser bugs (encoding, numbers, whitespace/comment handling). Entry points delegate to the dispatcher; failure paths free partially built trees via cJSON_Delete.

**Depends on.**

- [Memory & Shared Support](core-memory-support.md) · graph-confirmed · 4 edge(s) · Parsing allocates nodes and frees partially built trees on parse failure through the memory layer.
- [Tree Construction & Mutation](core-tree-mutation.md) · graph-only · 3 edge(s)

Parent: [Core cJSON Engine](core-json.md)

## Units (13)

<a id="u-eb694a324479"></a>
### `cJSON_ParseWithLengthOpts`

`CJSON_PUBLIC(cJSON *) cJSON_ParseWithLengthOpts(const char *value, size_t buffer_leng…` · [cJSON.c:L1147-L1224][f1]

Core parser entry: builds a parse_buffer over value/buffer_length and returns a parsed tree or NULL.

It first resets global_error to NULL. NULL value, zero length, root allocation failure, or a failed parse_value all go to fail. When require_null_terminated is set, it skips trailing whitespace and fails unless a '\0' is then accessible. On success it stores the stop position in *return_parse_end when requested and returns the tree. The fail path deletes any partial tree and, when value is non-NULL, records a global_error at the buffer offset (clamped to length-1 when offset reached length), also reporting it through return_parse_end, and returns NULL.

calls: [parse_value](core-parsing.md#u-cbca5889a6b8); uses: [cJSON.c-skip-utilities](core-parsing.md#u-ed9faa82e850)

<a id="u-98f055b96b34"></a>
### `cJSON_ParseWithOpts`

`CJSON_PUBLIC(cJSON *) cJSON_ParseWithOpts(const char *value, const char **return_pars…` · [cJSON.c:L1131-L1144][f1]

Parses a NUL-terminated string: NULL value returns NULL; otherwise it computes buffer_length as strlen(value)+1 (including the terminator so require_null_terminated can check it) and delegates to cJSON_ParseWithLengthOpts with the same return_parse_end and require_null_terminated arguments.

calls: [cJSON_ParseWithLengthOpts](core-parsing.md#u-eb694a324479)

<a id="u-0d57b2c47d88"></a>
### `cJSON.c-parse-entrypoints`

`CJSON_PUBLIC(cJSON *) cJSON_Parse(const char *value)` · [cJSON.c:L1227-L1230][f1]

Convenience wrappers: cJSON_Parse parses a NUL-terminated string with no return_parse_end and no null-termination requirement; cJSON_ParseWithLength parses exactly buffer_length bytes with the same defaults.

Both forward to cJSON_ParseWithLengthOpts and inherit its failure semantics.

<a id="u-ed9faa82e850"></a>
### `cJSON.c-skip-utilities`

`static parse_buffer *buffer_skip_whitespace(parse_buffer * const buffer)` · [cJSON.c:L1090-L1113][f1]

Input-position helpers for the parser.

buffer_skip_whitespace advances a parse_buffer past bytes <= 32; a NULL or NULL-content buffer returns NULL, an already-unreadable position returns the buffer unchanged, and if skipping consumes to the end of the buffer the offset is decremented by one so the final byte stays accessible. skip_utf8_bom returns NULL unless the buffer is valid and at offset 0; when five bytes are accessible and the content begins with the UTF-8 BOM it advances the offset by three; otherwise the buffer is returned unmodified.

<a id="u-cbca5889a6b8"></a>
### `parse_value`

`static cJSON_bool parse_value(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L1368-L1420][f1]

Dispatches on the byte at the buffer offset to parse one JSON value into item.

NULL or NULL-content buffer returns false. Literal matching uses can_read with the exact literal length, so 'null' (4), 'false' (5), and 'true' (4) all match when that many bytes remain, including documents that end exactly at the literal; matched literals set the item type (true also sets valueint 1) and advance the offset by the literal length. A leading quote dispatches to parse_string; '-' or a digit to parse_number; '[' to parse_array; '{' to parse_object. Any other byte returns false with the offset unchanged.

calls: [parse_string](core-parsing.md#u-79bc6a512446), [parse_number](core-parsing.md#u-760302b8669d), [parse_array](core-parsing.md#u-30a4b7f9acd5), [parse_object](core-parsing.md#u-1a792e084df9)

<a id="u-30a4b7f9acd5"></a>
### `parse_array`

`static cJSON_bool parse_array(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L1497-L1592][f1]

Builds a doubly linked cJSON list for a JSON array.

Depth at or above CJSON_NESTING_LIMIT returns false before incrementing depth. A first byte other than '[' fails. After '[' and whitespace, ']' yields the empty array success path. The comma-separated loop allocates each element via cJSON_New_Item (allocation failure fails), links it as next/prev, skips whitespace, and parses the element with parse_value, looping while a ',' follows. If the byte after the list is not ']' (or the buffer ended), it fails. Success clears depth, closes the list (head->prev = last), sets type cJSON_Array and child, advances past ']', and returns true. The fail path deletes the partially built head list and returns false.

calls: [parse_value](core-parsing.md#u-cbca5889a6b8), [cJSON_New_Item](core-memory-support.md#u-0840a192aac8), [cJSON_Delete](core-tree-mutation.md#u-5ca539d2c8db)

<a id="u-1a792e084df9"></a>
### `parse_object`

`static cJSON_bool parse_object(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L1662-L1777][f1]

Builds an object as a linked list of key/value items.

Depth at or above CJSON_NESTING_LIMIT returns false; a missing '{' fails. After '{' and whitespace, '}' gives the empty-object success path. Each loop iteration allocates and links a new item (allocation failure fails), requires at least one byte after the delimiter, parses the key with parse_string, then moves the parsed name from valuestring to string and NULLs valuestring, requires ':', and parses the value with parse_value; whitespace is skipped at each step and iteration continues while a ',' follows. A missing '}' fails. Success closes the list, sets type cJSON_Object and child, advances past '}', returns true. Fail deletes the built head list.

calls: [parse_string](core-parsing.md#u-79bc6a512446), [parse_value](core-parsing.md#u-cbca5889a6b8), [cJSON_Delete](core-tree-mutation.md#u-5ca539d2c8db)

<a id="u-79bc6a512446"></a>
### `parse_string`

`static cJSON_bool parse_string(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L824-L951][f1]

Parses a JSON string literal at the buffer offset into item.

A first byte other than '"' fails immediately. It first scans for the closing quote, counting skipped escape characters (a trailing backslash at buffer end fails) and allocating output of (distance - skipped) + 1 bytes; allocation failure fails. It then walks the literal: ordinary bytes are copied; escapes map b/f/n/r/t/"/\\// to their characters; \u delegates to utf16_literal_to_utf8, whose 0 return fails; any other escape fails. On success it NUL-terminates, sets type to cJSON_String and valuestring, and sets the offset just past the closing quote. The fail path frees the output buffer and rewinds the offset to input_pointer, returning false.

calls: [utf16_literal_to_utf8](core-parsing.md#u-267b81d4755c)

<a id="u-760302b8669d"></a>
### `parse_number`

`static cJSON_bool parse_number(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L307-L408][f1]

Parses a JSON number at the buffer offset into item via strtod.

NULL buffer or content returns false. It copies the maximal run of digits, '+', '-', 'e', 'E' and '.' characters (stopping at any other byte or buffer end) into a hook-allocated temporary buffer, replacing '.' with the locale decimal point when a '.' was seen. Allocation failure returns false with the offset unmoved. If strtod consumes nothing (after_end equals the buffer start) it frees the temporary buffer and returns false. On success it sets valuedouble, saturates valueint to INT_MAX or INT_MIN when out of int range, sets type to cJSON_Number, advances the offset by the consumed length, frees the temporary buffer, and returns true.

**Notes.**

- failure: The accepted character run may include sequences strtod parses only partially; the after_end consumed-length comparison is the only guard, and the offset then advances by strtod's consumption only.

<a id="u-43d416e4aff6"></a>
### `parse_hex4`

`static unsigned parse_hex4(const unsigned char * const input)` · [cJSON.c:L666-L699][f1]

Parses exactly four hexadecimal digits into an unsigned int, accumulating nibbles left to right.

Any byte outside 0-9, A-F, a-f returns 0 immediately, so 0 is both a possible value and the error sentinel; the caller cannot distinguish '\u0030' from an invalid digit by return value alone.

<a id="u-267b81d4755c"></a>
### `utf16_literal_to_utf8`

`static unsigned char utf16_literal_to_utf8(const unsigned char * const input_pointer,…` · [cJSON.c:L703-L821][f1]

Converts a \uXXXX escape (or a surrogate pair \uXXXX\uXXXX) at input_pointer into UTF-8 bytes written through *output_pointer, returning the consumed escape length (6 or 12) or 0 on failure.

Failure cases, all returning 0 via the fail label: fewer than 6 bytes to input_end, a lone low surrogate first (0xDC00-0xDFFF), a high surrogate (0xD800-0xDBFF) whose second half is missing, not \u, or outside 0xDC00-0xDFFF, a codepoint above 0x10FFFF, and truncated input for pairs (second_sequence within 6 bytes of input_end). Valid codepoints encode as 1-4 UTF-8 bytes; the output pointer is advanced by the encoded length. Does not validate the hex digits itself beyond parse_hex4 returning 0.

**Notes.**

- failure: An escape whose hex digits are invalid yields parse_hex4 == 0, which is encoded as U+0000 rather than rejected.

calls: [parse_hex4](core-parsing.md#u-43d416e4aff6)

<a id="u-e90caa1ab832"></a>
### `cJSON_Minify`

`CJSON_PUBLIC(void) cJSON_Minify(char *json)` · [cJSON.c:L2924-L2970][f1]

Strips whitespace and comments from a JSON string in place.

NULL input returns immediately. In the scan loop: space, tab, CR, and LF advance the read cursor without writing; a '/' starting '//' or '/*' is skipped by skip_oneline_comment or skip_multiline_comment, while a lone '/' hits the else branch, which only advances the read cursor, so that character is silently dropped from the output; a '"' copies the whole literal via minify_string; any other byte is copied to the write cursor and both cursors advance. After the loop the write cursor is NUL-terminated, so the minified text is shorter than or equal to the input and lives in the same buffer.

**Notes.**

- side_effect: The input buffer is modified in place and NUL-terminated at the new length; a dropped lone '/' changes the JSON semantics of the remaining text.

calls: [cJSON.c-comment-skippers](core-parsing.md#u-7d1ab97a6d22)

<a id="u-7d1ab97a6d22"></a>
### `cJSON.c-comment-skippers`

`static void skip_oneline_comment(char **input)` · [cJSON.c:L2875-L2886][f1]

In-place scanning helpers for cJSON_Minify.

skip_oneline_comment advances past '//' to (and beyond) the terminating newline, or to the string's NUL if none occurs. skip_multiline_comment advances past '/*' to (and beyond) a closing '*/', or to the NUL if unterminated. minify_string copies a JSON string literal from input to output, preserving the quotes; it copies bytes verbatim, steps over an escaped quote pair by copying both bytes, and stops after copying the unescaped closing quote.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c