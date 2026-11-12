# Format Spec Parser

**Capability.** Parses replacement fields, argument ids, widths, precisions, alignment, and standard format specs into packed specs.

Come here for parsing standard format strings and specs. The units describe replacement-field parsing, dynamic width/precision, alignment, and spec packing.

**Depends on.**

- [Dragonbox Cache and Assertions](dragonbox-cache-and-assertions.md) · graph-only · 3 edge(s)

**Depended on by.**

- [Compile-Time Format Checking](compile-time-format-checking.md) · graph-confirmed · 7 edge(s) · compile-time-format-checking depends on format-spec-parser for parsing and validating format specs.
- [Format Argument Type Mapping](format-argument-type-mapping.md) · graph-confirmed · 2 edge(s)
- [Printf-Style Formatting Engine](printf-style-formatting-engine.md) · graph-only · 13 edge(s)
- [Format Spec Parsing and Writing](format-spec-parsing-and-writing.md) · graph-only · 9 edge(s)
- [Range Formatter Specializations](range-formatter-specializations.md) · graph-only · 4 edge(s)
- [ANSI Color Style Formatting](ansi-color-style-formatting.md) · graph-only · 1 edge(s)
- [Integer and Pointer Formatting](integer-and-pointer-formatting.md) · graph-only · 1 edge(s)
- [Range and Tuple Formatting Infrastructure](range-and-tuple-formatting-infrastructure.md) · graph-only · 1 edge(s)

Parent: [Argument and Spec Pipeline](argument-and-spec-pipeline.md)

## Units (14)

<a id="u-b219b6242ac3"></a>
### `core.h-basic-specs-setters`

`FMT_CONSTEXPR void set_type(presentation_type t)` · [include/fmt/core.h:L735-L737][f1]

Setters for type, align, dynamic width/precision, and sign clear their field's mask before OR-ing the new value.

set_upper, set_alt, and set_localized only set their bit; clear_alt clears the alternate bit. set_fill and copy_fill_from manage fill data and size.

<a id="u-99177ac3104e"></a>
### `core.h-basic-specs-storage-and-fill-unit`

`class basic_specs` · [include/fmt/core.h:L682-L701][f1]

Packs basic format specifiers into a masked unsigned plus a four-byte fill buffer.

The class stores type, alignment, dynamic width/precision kind, sign, uppercase, alternate, localized, and fill size; default fill size is one and the fill byte is space. fill_unit reconstructs the first code unit from the first three fill bytes in little-endian order, so it is meaningful for the stored fill encoding rather than arbitrary text.

<a id="u-f68ad6b640b3"></a>
### `core.h-dynamic-spec-handler`

`FMT_CONSTEXPR void on_index(int id)` · [include/fmt/core.h:L1376-L1381][f1]

Receives a parsed dynamic width or precision reference.

on_index stores the index reference, marks the kind as index, checks the argument id, and checks that the referenced argument is a valid dynamic spec. on_name stores the name reference, marks the kind as name, and checks the argument id but does not run the dynamic-spec type check.

<a id="u-4e5d5833117c"></a>
### `core.h-format-specifier-parser`

`template <typename Char> FMT_CONSTEXPR auto parse_format_specs(const Char* begin, con…` · [include/fmt/core.h:L1456-L1470][f1]

Parses standard format specifiers into dynamic specs and returns the position at the terminating '}' or end.

It first chooses the current character: with more than one character left, a second character that is an alignment marker makes the first character a fill candidate and the current character is treated as NUL; otherwise the first character is current. The state helper rejects a state that goes backwards or a transition marked invalid with invalid format specifier. Presentation parsing checks the argument type against the allowed type set, reports invalid format specifier on mismatch, stores the presentation type, and advances one character. The loop handles alignment, sign, '#', zero padding, width, precision, locale, and presentation characters; uppercase X/B/E/F/G/A set the uppercase flag before parsing the corresponding presentation. '0' requires an arithmetic argument and, when no alignment is set, selects numeric alignment with fill '0'. 'c' rejects bool. A default character is treated as fill plus alignment: the fill length comes from code_point_length, a missing alignment or a '{' fill reports an error, and the fill view and alignment are stored. A '}' returns immediately; end of input returns the current position.

<a id="u-cc7a96c7256d"></a>
### `core.h-parse-replacement-field`

`template <typename Char, typename Handler> FMT_CONSTEXPR FMT_INLINE auto parse_replac…` · [include/fmt/core.h:L1594-L1612][f1]

Parses a replacement field.

If the format string ends immediately after '{', it calls on_error("invalid format string") and returns end. Otherwise it handles '}', '{{', ':', and argument ids, reporting missing '}' or unknown specifiers.

<a id="u-b3f92dd2532a"></a>
### `format-inl.h-error-reporting-helpers`

`FMT_FUNC void format_error_code(detail::buffer<char>& out, int error_code, string_vie…` · [include/fmt/format-inl.h:L92-L112][f2]

These helpers format and emit error text without letting reporting failures escape.

format_error_code clears the buffer, reserves space for the separator, error prefix, sign, and digits, includes the message only when it fits within the inline buffer budget, then appends the error code and asserts the final size stays within the inline buffer. do_report_error formats into a memory buffer and writes it to stderr; it writes a newline only when fwrite returns greater than zero, so a failed write emits no newline. fwrite_all writes the full count and throws system_error with errno when fewer bytes are written. report_error throws format_error with the supplied message, with an unreachable guard for MSVC/NVCC.

<a id="u-338962b2ecbb"></a>
### `parse_align`

`FMT_CONSTEXPR inline auto parse_align(char c) -> align` · [include/fmt/core.h:L1330-L1337][f1]

Maps '<', '>', and '^' to left, right, and center alignment; any other character maps to none.

<a id="u-7f42b5d1d97e"></a>
### `include/fmt/core.h:parse_arg_id`

`template <typename Char, typename Handler> FMT_CONSTEXPR auto parse_arg_id(const Char…` · [include/fmt/core.h:L1343-L1369][f1]

Parses an argument id at the current position and dispatches it to a handler.

A leading digit is parsed as an index: a nonzero digit goes through nonnegative-int parsing with INT_MAX as the error value, while a leading zero consumes only that zero; the next character must be '}' or ':' or it reports an invalid format string, otherwise it calls on_index. A non-digit must be a name start unless size optimization disables names, in which case it reports an invalid format string; a name is scanned as name-start or digit characters and passed to on_name. Returns the position after the parsed id.

<a id="u-c663fb857996"></a>
### `parse_dynamic_spec`

`template <typename Char> FMT_CONSTEXPR auto parse_dynamic_spec(const Char* begin, con…` · [include/fmt/core.h:L1395-L1426][f1]

Parses a dynamic width or precision value, either a literal integer or a braced argument id.

A leading digit is parsed as a nonnegative int; -1 from that parser reports number is too big and stores the value. A leading '{' consumes the brace; an empty or ':'-terminated braced id uses the next automatic argument id and checks it as a dynamic spec; otherwise it parses an argument id through the dynamic-spec handler. The closing '}' is required and consumed; any other path reports an invalid format string. Returns the end position and the reference kind, with none for a literal.

<a id="u-5d9d46fd9c7e"></a>
### `include/fmt/core.h:parse_format_specs (2)`

`template <typename Char> FMT_CONSTEXPR auto parse_format_specs(const Char* begin, con…` · [include/fmt/core.h:L1491-L1592][f1]

Parses standard format specifiers.

Uppercase is set for X, B, E, F, G, and A before parsing the corresponding presentation type. Other branches enforce state ordering and type compatibility, reporting errors for invalid specifiers.

<a id="u-50df9b1fecbb"></a>
### `parse_format_string`

`template <typename Char, typename Handler> FMT_CONSTEXPR void parse_format_string(bas…` · [include/fmt/core.h:L1641-L1659][f1]

Scans a format string and dispatches text and replacement fields to a handler.

On '{' it emits preceding text and parses a replacement field. On '}' it requires a doubled '}}'; otherwise it reports unmatched '}' and stops. Doubled braces emit the text including both braces and are skipped. At the end it emits the remaining text.

<a id="u-823edae0034b"></a>
### `parse_precision`

`template <typename Char> FMT_CONSTEXPR auto parse_precision(const Char* begin, const …` · [include/fmt/core.h:L1437-L1451][f1]

Parses a precision field after the dot.

If the dot is the last character it reports invalid precision and returns the current position; otherwise it parses a dynamic spec, stores the dynamic-precision kind, and returns the end position.

<a id="u-1190fb70526d"></a>
### `parse_width`

`template <typename Char> FMT_CONSTEXPR auto parse_width(const Char* begin, const Char…` · [include/fmt/core.h:L1428-L1435][f1]

Parses a width field, stores the resulting dynamic-width kind in the specs, and returns the position after the field.

<a id="u-3c540a60f3cf"></a>
### `include/fmt/core.h:FMT_END_EXPORT (32)`

`FMT_END_EXPORT namespace detail` · [include/fmt/core.h:L1281-L1285][f1]

A union holding either an integer argument index or a string-view argument name for dynamic width or precision.

Constructors initialize one active member; no tag is stored, so callers track which kind is active separately.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format-inl.h
