# Character and pointer writers

**Capability.** Writes single characters (with debug escaping), integers with grouping or character presentation, and pointers as hex.

Come here for the specialized writers for chars, grouped integers, char-presented integers, and pointers. Each writer applies specs, padding, and debug escaping around a small formatting core.

**Depends on.**

- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-only · 1 edge(s)
- [Printf implementation](printf-implementation.md) · graph-only · 1 edge(s)

Parent: [Value writing and drivers](value-writing-and-drivers.md)

## Units (5)

<a id="u-e60458520ac9"></a>
### `format.h-escaped-writing`

`template <size_t width, typename Char, typename OutputIt> auto write_codepoint(Output…` · [include/fmt/format.h:L2026-L2034][f1]

write_codepoint emits a backslash, a prefix char, and a fixed-width zero-padded hex value.

write_escaped_cp maps \n, \r, \t, quote and backslash to two-char escapes; other values below 0x100/0x10000/0x110000 become \x/\u/\U escapes of width 2/4/8; anything larger (invalid code points) is emitted as a sequence of \x escapes of its raw units. write_escaped_string wraps the string in quotes, copying runs between escapes found by find_escape until the end or a null escape-end signals none left. write_escaped_char wraps a single char in single quotes, escaping it when it needs escape (except a double quote, which stays literal) or is a single quote.

<a id="u-600cb696f99e"></a>
### `write_char`

`template <typename Char, typename OutputIt> FMT_CONSTEXPR auto write_char(OutputIt ou…` · [include/fmt/format.h:L2105-L2125][f1]

Writes a single character, optionally in debug presentation (escaped via write_escaped_char into a stack buffer), then pads per specs with the raw or escaped content.

<a id="u-a9215ab79308"></a>
### `write_int`

`template <typename OutputIt, typename UInt, typename Char> auto write_int(OutputIt ou…` · [include/fmt/format.h:L2206-L2252][f1]

Writes an integer with digit grouping: formats the value into a memory_buffer per presentation type (dec; hex/oct/bin with alt prefixes, octal '0' only when precision does not exceed the digit count and the value is nonzero; chr delegates to write_int_chr), computes size including prefix length and separator count, then right-pads and writes prefix bytes followed by the grouped digits.

The default presentation case asserts false and falls through to decimal.

<a id="u-86a1209de1be"></a>
### `write_int_chr`

`template <typename Char, typename OutputIt, typename UInt> FMT_CONSTEXPR auto write_i…` · [include/fmt/format.h:L2197-L2203][f1]

Writes an integer in character presentation: reports "character value out of range" when negative or exceeding the char type's range, otherwise delegates to write_char.

<a id="u-c9ca3ef9cfab"></a>
### `write_ptr`

`template <typename Char, typename OutputIt, typename UIntPtr> auto write_ptr(OutputIt…` · [include/fmt/format.h:L1971-L1983][f1]

Writes a pointer as 0x followed by lowercase hex digits (count_digits<4>), right-padded when specs are given, otherwise written directly after reserving.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
