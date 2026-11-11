# Integer decimal formatting

**Capability.** Formats integers as decimal digits using digit tables, digit counting, and stack-buffered writers, including to_string-style conversion.

This module owns fast decimal conversion: two-digit lookup tables, count_digits, and the standalone int_writer that formats into a fixed stack buffer. Use it when optimizing or debugging integer output.

**Depends on.**

- [Value writing engine](value-writing-engine.md) · graph-confirmed · 3 edge(s)
- [Binary and float primitives](binary-and-float-primitives.md) · graph-only · 1 edge(s)
- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Inline implementation and stdio](inline-implementation-and-stdio.md) · graph-only · 1 edge(s)

Parent: [Value writing and drivers](value-writing-and-drivers.md)

## Units (10)

<a id="u-f9abd84dec9d"></a>
### `format.h-count-digits`

`template <typename T> FMT_CONSTEXPR auto count_digits_fallback(T n) -> int` · [include/fmt/format.h:L1246-L1259][f1]

Count decimal digits of an unsigned value (1 for zero).

The fallback divides by 10000 per iteration with early returns at 10/100/1000/10000. The uint64_t and uint32_t overloads use CLZ-based table lookups (bsr2log10 and the Willets increment table) at runtime unless constant-evaluated or FMT_OPTIMIZE_SIZE. The 128-bit overload reduces via division by 10^19 chunks to avoid slow 128-bit division. The BITS template counts digits in a power-of-two radix, using a CLZ shortcut for 32-bit types at runtime and otherwise shifting by BITS until zero.

<a id="u-c83be13a1767"></a>
### `format.h-digits10`

`template <typename Int> constexpr auto digits10() noexcept -> int` · [include/fmt/format.h:L1354-L1356][f1]

Returns numeric_limits digits10, with 38 for both 128-bit integer types where numeric_limits may not report it.

<a id="u-74b878817418"></a>
### `format.h-digits2-tables`

`inline auto digits2(size_t value) noexcept -> const char*` · [include/fmt/format.h:L1213-L1223][f1]

Return a pointer into a static two-characters-per-entry table for values in [0,100): digits2 is the plain decimal table; digits2_i is a bit-hack table indexed by the first binary digits of i/100 used by the fast 32-bit formatting path.

<a id="u-65ad5d002fe4"></a>
### `format.h-fallback-digit-grouping`

`class fallback_digit_grouping` · [include/fmt/format.h:L2745-L2747][f1]

A constexpr no-op grouping used when locale support is unavailable or constant-evaluated: no separator, zero separator count, and apply returns the output iterator without writing anything.

<a id="u-7e8640e0aa5e"></a>
### `format.h-format-decimal`

`template <typename Char, typename UInt> FMT_CONSTEXPR20 auto do_format_decimal(Char* …` · [include/fmt/format.h:L1431-L1478][f1]

do_format_decimal writes an unsigned value's decimal digits right-aligned into a caller-sized buffer (asserting size >= count_digits).

For 128-bit values at runtime it formats 19-digit chunks via 10^19 division to avoid slow 128-bit division; for 32-bit values it uses a multiply-based two-digit extraction; otherwise it emits two digits at a time with a final one-digit tail. The pointer wrapper returns out+num_digits; the iterator overload writes via to_pointer when possible, else through a stack buffer of digits10+1 with copy_noinline.

<a id="u-3feca906a439"></a>
### `format.h-format-int`

`class format_int` · [include/fmt/format.h:L4480-L4484][f1]

A fast standalone integer formatter: constructors for each signed/unsigned integer type format into an internal buffer sized digits10+3 (digits, sign, NUL) via format_signed/format_unsigned (do_format_decimal into the tail of the buffer; negatives prepend '-').

size returns the written length; data returns the digits without a terminator; c_str NUL-terminates (via the mutable buffer) and returns the start; str returns a std::string of the content.

<a id="u-ac4e2b235515"></a>
### `format.h-is-negative`

`template <typename T, FMT_ENABLE_IF(is_signed<T>::value)> constexpr auto is_negative(…` · [include/fmt/format.h:L1187-L1190][f1]

Returns value<0 for signed types (including native int128) and constant false for unsigned types, avoiding comparison warnings.

<a id="u-5630b4c90898"></a>
### `format.h-significand-writing`

`struct big_decimal_fp` · [include/fmt/format.h:L2629-L2633][f1]

get_significand_size returns the stored size for big_decimal_fp or count_digits for dragonbox results.

The write_significand overloads write a significand (pointer or integer) with optional trailing zeros, optionally applying digit grouping (buffering digits plus zeros, then grouping.apply), or insert a decimal point after integral_size digits — the pointer variant writes digits backward from the end of the buffer, the iterator variant uses a stack buffer of digits10+2 and copy_noinline, and the pointer-significand variant copies the two halves around the point; the grouped variant groups only the integral part and then appends the fraction.

<a id="u-18567d0f3cf3"></a>
### `format.h-to-string`

`template <typename T, FMT_ENABLE_IF(std::is_integral<T>::value)> FMT_NODISCARD FMT_CO…` · [include/fmt/format.h:L4673-L4679][f1]

Integral values are written into a stack buffer sized digits10+2 (at least 5, covering bool's "false") and returned as a std::string; types with format_as recurse through the converted value; everything else is written into a memory_buffer and copied to a string.

<a id="u-bbbe5be3331c"></a>
### `format.h-write2digits`

`extern template FMT_API auto thousands_sep_impl<wchar_t>(locale_ref) -> thousands_sep…` · [include/fmt/format.h:L1392-L1417][f1]

Write a two-digit value: write2digits memcpy's from the digits2 table for char at runtime (or computes '0'+value/10, '0'+value%10 otherwise); write2digits_i uses the bit-hack table analogously.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
