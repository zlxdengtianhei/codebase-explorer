# Duration unit suffixes

**Capability.** Maps chrono period types to SI unit suffix strings and copies them to output, including UTF-8 to UTF-16 conversion.

Responsible for emitting the unit text after a duration value, using a table of known periods and a fallback [num/den]s form. Wide-character output is handled via UTF conversion.

Parent: [Chrono and time formatting](chrono-and-time-formatting.md)

## Units (4)

<a id="u-a57b3d5a0ced"></a>
### `chrono.h-copy-unit`

`template <typename Char, typename OutputIt> auto copy_unit(string_view unit, OutputIt…` · [include/fmt/chrono.h:L1601-L1604][f1]

Copies a unit suffix to the output; for wchar_t it converts the UTF-8 unit via utf8_to_utf16 (valid because unit characters share UTF-16/UTF-32 representations), otherwise copies verbatim.

<a id="u-0bd04dc2e879"></a>
### `format.h-utf8-to-utf16`

`class utf8_to_utf16` · [include/fmt/format.h:L1540-L1546][f2]

Converts UTF-8 to UTF-16 stored in a wchar_t memory_buffer (conversion itself is FMT_API, defined out of line).

size() is buffer size minus the trailing NUL; c_str points at the buffer; str() returns a wstring; the conversion operator yields a string_view over the buffer.

<a id="u-b5bcfaa11428"></a>
### `format_duration_unit`

`template <typename Char, typename Period, typename OutputIt> auto format_duration_uni…` · [include/fmt/chrono.h:L1614-L1627][f1]

Writes a duration's unit suffix: known periods use the get_units table via copy_unit; unknown periods emit "[num/den]s" (denominator omitted when 1).

<a id="u-99aa377742f5"></a>
### `get_units`

`template <typename Period> FMT_CONSTEXPR inline auto get_units() -> const char*` · [include/fmt/chrono.h:L615-L639][f1]

Maps a chrono period type to its SI unit suffix string ("ns", "µs" or "us" depending on use_utf8, "min", "h", "d", etc.), returning nullptr for unrecognized periods so callers can fall back to a [num/den]s representation.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/chrono.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
