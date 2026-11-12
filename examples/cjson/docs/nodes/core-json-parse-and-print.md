# Core JSON Parse and Print

**Capability.** Implements cJSON parsing, rendering, minification, and public entrypoints/accessors for JSON values.

Come here for the core cJSON implementation that turns text into trees and trees into text. It contains parse dispatch, array/object/string/number handling, print buffering, and public parse/print/accessor entrypoints.

**Depends on.**

- [Item Creation and Lifecycle](item-creation-and-lifecycle.md) · graph-confirmed · 7 edge(s) · Core parsing and printing uses item creation and lifecycle helpers to build and manage cJSON nodes.
- [JSON Pointer Patch Utilities](json-pointer-patch-utilities.md) · graph-confirmed · 3 edge(s)
- [Public Utility API and Mutators](public-utility-api-and-mutators.md) · graph-confirmed · 2 edge(s)

Parent: [cJSON JSON Library](cjson-json-library.md)

## Units (26)

<a id="u-7df91d7724e7"></a>
### `buffer_skip_whitespace`

`static parse_buffer *buffer_skip_whitespace(parse_buffer * const buffer)` · [cJSON.c:L1090-L1113][f1]

Skips bytes up to and including whitespace at the current offset.

It returns NULL for a NULL buffer or content. If no byte is accessible it returns the buffer unchanged. It advances while the current byte is at most 32, then if the offset reached the length it decrements the offset by one. It returns the buffer.

<a id="u-ebaf707174c1"></a>
### `cJSON_Compare`

`CJSON_PUBLIC(cJSON_bool) cJSON_Compare(const cJSON * const a, const cJSON * const b, …` · [cJSON.c:L3072-L3195][f1]

Deep structural comparison.

It returns false for NULL inputs or differing low-byte types, and false for types outside the supported set. Identical pointers are equal. False, true, and null compare equal by type. Numbers use the tolerant double comparison. Strings and raw values require both valuestrings non-NULL and strcmp equality. Arrays compare element-wise recursively and fail if one ends before the other. Objects require every member of the first to be found in the second and recursively equal, then every member of the second to be found in the first and recursively equal, using the requested case sensitivity for lookup.

<a id="u-421b01576cce"></a>
### `cJSON_SetNumberHelper`

`CJSON_PUBLIC(double) cJSON_SetNumberHelper(cJSON *object, double number)` · [cJSON.c:L411-L432][f1]

Sets a number item's double and saturated integer fields.

A NULL object returns NAN. Values at or above INT_MAX saturate to INT_MAX; values at or below INT_MIN saturate to INT_MIN; otherwise the integer is the cast value. It returns the assigned double.

<a id="u-a1c731bd85cb"></a>
### `cJSON_SetValuestring`

`CJSON_PUBLIC(char*) cJSON_SetValuestring(cJSON *object, const char *valuestring)` · [cJSON.c:L435-L476][f1]

Replaces a string item's value under strict preconditions.

It returns NULL unless the object is a non-reference string with a non-NULL existing valuestring and the new string is non-NULL. If the new string is no longer than the old, it rejects overlapping source and destination ranges and returns NULL, otherwise copies in place and returns the existing buffer. If longer, it duplicates through global hooks, returns NULL on allocation failure, otherwise frees the old valuestring, assigns the copy, and returns it.

<a id="u-438dd0368a51"></a>
### `compare_double`

`static cJSON_bool compare_double(double a, double b)` · [cJSON.c:L589-L593][f1]

Compares two doubles using an absolute tolerance of the larger magnitude times DBL_EPSILON.

<a id="u-20e3fb2f41a7"></a>
### `ensure`

`static unsigned char* ensure(printbuffer * const p, size_t needed)` · [cJSON.c:L490-L573][f1]

Ensures a print buffer has room for a requested byte count.

It returns NULL for a NULL buffer state or NULL backing buffer. The offset-at-or-past-length guard applies only when length is greater than zero, so a zero-length buffer with offset zero is not rejected there. It also rejects requests above INT_MAX. It adds offset plus one to the request; if that fits it returns the current write pointer. If allocation is disabled it returns NULL. Otherwise it computes a doubled size, capped at INT_MAX when needed, and reallocates or allocates and copies. Allocation failure deallocates the old buffer, clears length and buffer, and returns NULL. Success updates length and buffer and returns the new write pointer.

<a id="u-ef3398f57b63"></a>
### `get_decimal_point`

`static unsigned char get_decimal_point(void)` · [cJSON.c:L279-L287][f1]

Returns the current locale decimal point first byte when locale support is enabled, otherwise a period.

<a id="u-30a4b7f9acd5"></a>
### `parse_array`

`static cJSON_bool parse_array(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L1497-L1592][f1]

Parses a JSON array into a linked child list.

It fails immediately when nesting depth is at the limit. It increments depth, requires a left bracket, skips whitespace, accepts an empty right bracket, and otherwise steps back and loops allocating items, linking them, parsing each value, and skipping whitespace after commas. It fails on allocation failure, value parse failure, or a missing right bracket. On success it decrements depth, sets the head tail pointer, sets the array type and child, advances past the bracket, and returns true. On failure it deletes any head list and returns false.

<a id="u-43d416e4aff6"></a>
### `parse_hex4`

`static unsigned parse_hex4(const unsigned char * const input)` · [cJSON.c:L666-L699][f1]

Parses exactly four hexadecimal digits.

It returns zero if any digit is invalid; otherwise it accumulates the four nibbles into an unsigned value.

<a id="u-760302b8669d"></a>
### `parse_number`

`static cJSON_bool parse_number(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L307-L408][f1]

Parses a numeric token from the parse buffer.

It returns false for a NULL buffer or content. It scans digits, signs, e/E, and period until another byte, allocates a temporary string, replaces periods with the locale decimal point, and calls strtod. If strtod consumes nothing it frees the temporary buffer and returns false. On success it stores the double, saturates the integer field to INT_MAX or INT_MIN when out of range, sets the number type, advances the offset by consumed bytes, frees the temporary buffer, and returns true. Allocation failure returns false.

<a id="u-1a792e084df9"></a>
### `parse_object`

`static cJSON_bool parse_object(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L1662-L1777][f1]

Parses a JSON object into a linked child list.

It fails immediately when nesting depth is at the limit. It increments depth, requires a left brace, skips whitespace, accepts an empty right brace, and otherwise loops allocating items, linking them, requiring a byte after the comma, parsing the key string, swapping key into the string field, requiring a colon, and parsing the value. It fails on allocation failure, missing key or colon, value parse failure, or a missing right brace. On success it decrements depth, sets the head tail pointer, sets the object type and child, advances past the brace, and returns true. On failure it deletes any head list and returns false.

<a id="u-79bc6a512446"></a>
### `parse_string`

`static cJSON_bool parse_string(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L824-L951][f1]

Parses a quoted JSON string into a newly allocated value.

It fails if the current byte is not an opening quote, if the closing quote is missing, if a trailing backslash runs past the buffer, on allocation failure, on an unknown escape, or on failed UTF-16 conversion. It decodes standard escapes and UTF-16 escapes, NUL-terminates, sets the string type and valuestring, advances past the closing quote, and returns true. On failure it frees any output and sets the offset to the input pointer, which starts one byte after the opening quote, then returns false.

<a id="u-cbca5889a6b8"></a>
### `parse_value`

`static cJSON_bool parse_value(cJSON * const item, parse_buffer * const input_buffer)` · [cJSON.c:L1368-L1420][f1]

Dispatches one JSON value from the parse buffer.

It returns false for a NULL buffer or content. It recognizes null, false, and true only when enough bytes are readable and the literal matches, setting the type and advancing the offset. It dispatches quote to string parsing, minus or digit to number parsing, left bracket to array parsing, and left brace to object parsing. Any other byte returns false.

<a id="u-41f81398f144"></a>
### `print_array`

`static cJSON_bool print_array(const cJSON * const item, printbuffer * const output_bu…` · [cJSON.c:L1595-L1659][f1]

Renders an array into a print buffer.

It returns false for a NULL output buffer or when nesting depth is at the limit. It writes a left bracket, increments depth, prints each child, updates the offset, and between children writes a comma plus a space only in formatted mode. It writes a right bracket, NUL-terminates, decrements depth, and returns true. Any ensure or child print failure returns false.

<a id="u-23f8c0af73d3"></a>
### `print_number`

`static cJSON_bool print_number(const cJSON * const item, printbuffer * const output_b…` · [cJSON.c:L596-L663][f1]

Renders a number item into a print buffer.

A NULL output buffer returns false. NaN or infinity writes null. If the double equals the integer field, it writes the integer. Otherwise it tries 15 significant digits, reparses, and if that does not round-trip or parsing fails, writes 17 significant digits. A negative or oversized sprintf result returns false. It ensures space, copies bytes while replacing the locale decimal point with a period, NUL-terminates, advances the offset, and returns true; ensure failure returns false.

<a id="u-bf98d244dfc4"></a>
### `print_object`

`static cJSON_bool print_object(const cJSON * const item, printbuffer * const output_b…` · [cJSON.c:L1780-L1896][f1]

Renders an object into a print buffer.

It returns false for a NULL output buffer or when nesting depth is at the limit. It writes a left brace and, in formatted mode, a newline, then increments depth. For each member it writes indentation tabs in formatted mode, prints the key, writes a colon plus a tab in formatted mode, prints the value, writes a comma only when a next member exists, and writes a newline after every member in formatted mode. It closes with indentation, a right brace, NUL termination, and decrements depth. Any ensure or print failure returns false.

<a id="u-d258aabdaf25"></a>
### `print_string`

`static cJSON_bool print_string(const cJSON * const item, printbuffer * const p)` · [cJSON.c:L1076-L1079][f1]

Delegates string printing to the string pointer printer using the item's valuestring.

<a id="u-c6e0866b50b4"></a>
### `print_string_ptr`

`static cJSON_bool print_string_ptr(const unsigned char * const input, printbuffer * c…` · [cJSON.c:L954-L1073][f1]

Writes a quoted, escaped string into a print buffer.

A NULL output buffer returns false. A NULL input writes an empty quoted string and returns true. Otherwise it counts escapes for quote, backslash, backspace, form feed, newline, carriage return, tab, and control bytes below 32, ensures space, then writes either a direct copy or an escaped copy with control bytes as u00xx. It NUL-terminates and returns true; ensure failure returns false. It does not advance the buffer offset itself.

<a id="u-3f5cf3a5e49e"></a>
### `print_value`

`static cJSON_bool print_value(const cJSON * const item, printbuffer * const output_bu…` · [cJSON.c:L1423-L1494][f1]

Dispatches one item to its printer.

It returns false for a NULL item or output buffer. Null, false, and true ensure space and copy their literals. Number delegates to number printing. Raw requires a non-NULL valuestring, ensures strlen plus one, and copies it. String, array, and object delegate to their printers. Any other type returns false.

<a id="u-84f93c6ae406"></a>
### `skip_utf8_bom`

`static parse_buffer *skip_utf8_bom(parse_buffer * const buffer)` · [cJSON.c:L1116-L1129][f1]

Skips a UTF-8 BOM at the start of a parse buffer.

It returns NULL for a NULL buffer or content or when the offset is not zero. It skips three bytes only when index four is accessible and the first three bytes are EF BB BF; a short BOM-prefixed buffer is therefore not skipped. It returns the buffer.

<a id="u-dd64117dae4e"></a>
### `update_offset`

`static void update_offset(printbuffer * const buffer)` · [cJSON.c:L576-L586][f1]

Advances a print buffer offset by the length of the NUL-terminated string at its current offset.

It does nothing for a NULL buffer state or NULL backing buffer.

<a id="u-267b81d4755c"></a>
### `utf16_literal_to_utf8`

`static unsigned char utf16_literal_to_utf8(const unsigned char * const input_pointer,…` · [cJSON.c:L703-L821][f1]

Converts one UTF-16 escape, or a surrogate pair, to UTF-8.

It fails with zero if fewer than six bytes remain, if the first code is a low surrogate, if a high surrogate lacks a following backslash-u sequence or valid low surrogate, or if the codepoint exceeds 0x10FFFF. It returns six for a single escape or twelve for a pair, writes one to four UTF-8 bytes, and advances the output pointer.

<a id="u-778089a6d869"></a>
### `cJSON.c-minification`

`static void skip_oneline_comment(char **input)` · [cJSON.c:L2875-L2886][f1]

Minifies JSON text in place.

The one-line comment skipper advances past two slashes and then through the newline or to NUL. The multiline skipper advances past slash-star and through star-slash or to NUL. The string minifier copies the opening quote and then copies bytes until an unescaped quote, preserving backslash-quote pairs. The public minifier returns immediately for NULL, otherwise compacts by skipping whitespace, skipping comments when slash is followed by slash or star, copying a lone slash, copying strings through the string minifier, and copying other bytes, then NUL-terminates.

<a id="u-0d57b2c47d88"></a>
### `cJSON.c-parse-entrypoints`

`CJSON_PUBLIC(cJSON *) cJSON_ParseWithOpts(const char *value, const char **return_pars…` · [cJSON.c:L1131-L1144][f1]

Public parse entrypoints.

The options wrapper returns NULL immediately for a NULL value before delegating, so that failure does not go through the core parser error handling; otherwise it passes strlen plus one to the length parser. The length parser resets the global error to NULL and zero, fails for NULL value or zero length, allocates an item, skips BOM and whitespace, and parses a value. With null-termination required it skips whitespace and fails when the offset is at or past the length or the current byte is not NUL, so success requires a NUL before the end. On success it optionally reports the parse end and returns the item. On failure it deletes the item; for non-NULL input it records an error position at the offset if in range, otherwise at length minus one when length is positive, optionally reports that pointer, and stores the global error; for NULL input the global error remains reset. The simple parse wrappers use default options.

<a id="u-c116fbae90f0"></a>
### `cJSON.c-print-entrypoints`

`static unsigned char *print(const cJSON * const item, cJSON_bool format, const intern…` · [cJSON.c:L1239-L1304][f1]

Public print entrypoints.

The core printer allocates a 256-byte buffer through hooks, records format and hooks, prints the value, updates the offset, then either reallocates to offset plus one or allocates a new buffer, copies the smaller of length and offset plus one, NUL-terminates, and frees the old buffer. Any failure frees the working and result buffers and returns NULL. The formatted and unformatted wrappers select format. The buffered wrapper rejects a negative prebuffer, allocates that size, prints with allocation enabled, frees and returns NULL on print failure, otherwise returns the buffer. The preallocated wrapper rejects negative length or NULL buffer and prints with allocation disabled, returning the print result.

<a id="u-e1f5f49449c1"></a>
### `cJSON.c-public-metadata-and-value-accessors`

`CJSON_PUBLIC(const char *) cJSON_GetErrorPtr(void)` · [cJSON.c:L94-L97][f1]

Public metadata and value accessors.

The error pointer returns the global error buffer plus its recorded position without a null guard. The string getter returns the stored string only for a string item, otherwise NULL; the number getter returns the stored double only for a number item, otherwise NAN. The version function formats major.minor.patch into a static 15-byte buffer and returns that buffer.

**Uncertainties.**

- The error pointer performs pointer arithmetic on the global error buffer even when no error has been recorded.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/DaveGamble/cJSON/blob/6d9f2443ab071f86e5d9b43025a40929ec41c46c/cJSON.c
