# Integer and Pointer Formatting

**Capability.** Formats integers, characters, pointers, exponents, and grouped digits using digit tables, locale grouping, and stack buffers.

This module contains integer and pointer formatting helpers. Readers find digit counting, grouping, prefix construction, and pointer/character writers.

**Depends on.**

- [Buffer and Core Integer Writer](buffer-and-core-integer-writer.md) · graph-confirmed · 2 edge(s)
- [Dragonbox Cache and Assertions](dragonbox-cache-and-assertions.md) · graph-only · 2 edge(s)
- [Format Spec Parser](format-spec-parser.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Platform File and Locale Internals](platform-file-and-locale-internals.md) · graph-only · 1 edge(s)

Parent: [Low-Level Formatting Primitives](low-level-formatting-primitives.md)

## Units (13)

<a id="u-940176bf2d96"></a>
### `format.h-digit-counting`

`template <typename T> FMT_CONSTEXPR auto count_digits_fallback(T n) -> int` · [include/fmt/format.h:L1246-L1259][f1]

These helpers count decimal or power-of-two digits.

The fallback divides by 10000 in groups of four. The 64-bit fast path uses a leading-zero table and a power-of-ten comparison; the public 64-bit counter uses it outside constant evaluation unless size optimization is requested. The 128-bit counter splits by 10^19 into 64-bit chunks. The bit-width template uses a leading-zero estimate for 32-bit values or a shift loop. The 32-bit fast path uses a packed increment table; the public 32-bit counter uses it outside constant evaluation unless size optimization is requested.

<a id="u-9f8eda7ff970"></a>
### `format.h-digit-grouping`

`auto next(next_state& state) const -> int` · [include/fmt/format.h:L2139-L2146][f1]

This grouping helper stores a grouping pattern and separator.

The locale constructor loads separator data only when localized. The next-position method returns the next separator position, using the last group repeatedly, or the maximum integer when no separator or an invalid group is present. Separator counting advances until the digit count is reached. Applying builds separator positions and inserts the separator while copying digits.

<a id="u-537957b50b38"></a>
### `format.h-integer-formatting-helpers`

`template <typename UInt> FMT_CONSTEXPR20 auto format_unsigned(UInt value) -> char*` · [include/fmt/format.h:L4488-L4492][f1]

The unsigned helper formats an integer into the object buffer and returns the first digit.

The signed helper computes the absolute value, formats it unsigned, and prepends a minus sign when negative.

<a id="u-a5b3abf8a3a4"></a>
### `format.h-locale-facet`

`class format_facet : public Locale::facet` · [include/fmt/format.h:L4228-L4242][f1]

This locale facet stores separator, grouping, and decimal-point strings.

Its constructor initializes them from arguments, and its put method delegates to the virtual implementation.

<a id="u-3429a4ca3390"></a>
### `format.h-localized-integer-writing`

`template <typename OutputIt> inline auto write_loc(OutputIt, const loc_value&, const …` · [include/fmt/format.h:L2261-L2265][f1]

make_write_int_arg converts a signed or unsigned integer to an absolute value and a packed prefix.

Negative values always get a '-' prefix and their absolute value. Non-negative values use the sign enum: sign::plus yields '+', sign::space yields ' ', and sign::none or sign::minus yield no prefix. loc_writer formats integers with digit grouping using the stored separator and grouping, and returns false for non-integer types.

<a id="u-0c61a0f0f103"></a>
### `format.h-to-string-overloads`

`template <typename T, FMT_ENABLE_IF(std::is_integral<T>::value)> FMT_NODISCARD FMT_CO…` · [include/fmt/format.h:L4673-L4679][f1]

The integral overload writes into a stack buffer sized for digits, sign, or false.

The format-as overload delegates to the converted value. The generic overload writes into a memory buffer and returns its contents.

<a id="u-a71f66b41fa1"></a>
### `format.h-two-digit-tables`

`inline auto digits2(size_t value) noexcept -> const char*` · [include/fmt/format.h:L1213-L1223][f1]

These functions return pointers into static two-character tables for values in [0, 100).

The first table is the ordinary decimal pair table; the second is a special table used by the optimized decimal writer. Neither checks the range.

<a id="u-e080db30c992"></a>
### `format.h-two-digit-writers`

`extern template FMT_API auto thousands_sep_impl<wchar_t>(locale_ref) -> thousands_sep…` · [include/fmt/format.h:L1392-L1417][f1]

These functions write exactly two decimal digits.

The first uses a table copy for narrow characters outside constant evaluation and size optimization, otherwise arithmetic. The second uses the special table for narrow characters outside size optimization, otherwise copies the table characters.

<a id="u-3711a0552c6d"></a>
### `ptr`

`template <typename T> auto ptr(T p) -> const void*` · [include/fmt/format.h:L4305-L4308][f1]

This function converts a pointer to a const void pointer for pointer formatting.

It statically rejects non-pointer arguments and uses a bit cast.

<a id="u-966bef007bf1"></a>
### `write_exponent`

`template <typename Char, typename OutputIt> FMT_CONSTEXPR auto write_exponent(int exp…` · [include/fmt/format.h:L1786-L1810][f1]

This function writes an exponent as a sign and at least two decimal digits.

It asserts the exponent is between -10000 and 10000. In constant evaluation it uses the general decimal writer; otherwise it uses the two-digit table and emits a third digit when the value is at least 100.

<a id="u-a9215ab79308"></a>
### `write_int`

`template <typename OutputIt, typename UInt, typename Char> auto write_int(OutputIt ou…` · [include/fmt/format.h:L2206-L2252][f1]

This function writes an integer with digit grouping.

It formats the value into a temporary buffer according to presentation type, adding alternate prefixes for hex, octal, and binary; octal prefixing depends on precision and nonzero value. It counts separators, computes total size, and right-pads while emitting prefix, grouped digits, and padding.

<a id="u-86a1209de1be"></a>
### `write_int_chr`

`template <typename Char, typename OutputIt, typename UInt> FMT_CONSTEXPR auto write_i…` · [include/fmt/format.h:L2197-L2203][f1]

This function writes an integer as a character.

It reports an error if the value is negative or exceeds the maximum unsigned value of the character type; otherwise it delegates to character writing.

<a id="u-c9ca3ef9cfab"></a>
### `write_ptr`

`template <typename Char, typename OutputIt, typename UIntPtr> auto write_ptr(OutputIt…` · [include/fmt/format.h:L1971-L1983][f1]

This function writes a pointer as 0x followed by hexadecimal digits.

With format specs it right-pads; without specs it writes directly after reserving the exact size.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
