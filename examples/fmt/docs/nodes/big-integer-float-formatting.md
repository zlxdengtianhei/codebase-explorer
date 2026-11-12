# Big Integer Float Formatting

**Capability.** Implements arbitrary-precision integer storage and Steele-White fixed-precision floating-point formatting with rounding thresholds.

Use this module for big-integer-backed floating-point formatting. The units describe limb storage, precision adjustment, fixed-precision formatting, and rounding thresholds.

**Depends on.**

- [Low-Level Formatting Primitives](low-level-formatting-primitives.md) · graph-confirmed · 3 edge(s)
- [Platform and Dragonbox Support](platform-and-dragonbox-support.md) · graph-confirmed · 12 edge(s) · big-integer-float-formatting depends on platform-and-dragonbox-support for Dragonbox and platform support.
- [Dragonbox Cache and Assertions](dragonbox-cache-and-assertions.md) · graph-only · 12 edge(s)
- [Format Core Utilities](format-core-utilities.md) · graph-only · 2 edge(s)
- [Buffer and Core Integer Writer](buffer-and-core-integer-writer.md) · graph-only · 1 edge(s)

Parent: [Core Formatting Internals](core-formatting-internals.md)

## Units (5)

<a id="u-71f364c589ce"></a>
### `format.h-big-integer`

`class bigint` · [include/fmt/format.h:L2925-L2930][f1]

This class stores an arbitrary-precision unsigned integer as base-2^32 limbs plus an exponent.

Limb access returns zero outside the stored range. Subtraction borrows across limbs; leading zeros are trimmed. Aligned subtraction asserts alignment and sufficient value. Multiplication supports 32-bit and 64/128-bit factors with carry propagation. Assignment supports integer and big-integer sources; integer assignment asserts positivity. Left shift adjusts the exponent and limb shift. Multiply-assign asserts a positive factor. Comparison orders by limb count then limbs. Addition comparison compares a sum against a third value. Power-of-ten assignment uses repeated squaring and a final shift. Squaring computes cross-products and doubles the exponent. Alignment inserts zero limbs to equalize exponents. Division by repeated aligned subtraction returns the quotient and leaves the remainder.

<a id="u-95334ca55893"></a>
### `FMT_BEGIN_EXPORT.size_padding.adjust_precision`

`inline FMT_CONSTEXPR20 void adjust_precision(int& precision, int exp10)` · [include/fmt/format.h:L2917-L2923][f1]

This function adds a decimal exponent to a precision.

If the addition would overflow an integer, it throws a format error.

<a id="u-3321a7773df0"></a>
### `FMT_BEGIN_EXPORT.size_padding.format_dragon`

`FMT_CONSTEXPR20 inline void format_dragon(basic_fp<uint128_t> value, unsigned flags, …` · [include/fmt/format.h:L3175-L3307][f1]

This function formats a floating value using the Steele and White fixed-precision algorithm.

It builds numerator, denominator, and lower/upper boundary big integers according to the exponent and flags, optionally applies fixup to correct the decimal exponent, then generates either the shortest representation or a requested number of digits. It rounds half to even, propagates carry, and updates the decimal exponent.

<a id="u-be687077ca67"></a>
### `FMT_BEGIN_EXPORT.size_padding.format_float`

`template <typename Float> FMT_CONSTEXPR20 auto format_float(Float value, int precisio…` · [include/fmt/format.h:L3408-L3711][f1]

This function formats a floating value into a character buffer and returns the decimal exponent.

Zero is special-cased for fixed precision. Fast binary floating types outside constant evaluation use a Dragonbox fast path with subnormal normalization, first-segment extraction, precision adjustment, and optional rounding; otherwise Dragon4 is used. Fixed formatting adjusts precision, trailing zeros are removed when not fixed and not alternate, and the final exponent is returned.

<a id="u-fe34c02e203c"></a>
### `FMT_BEGIN_EXPORT.size_padding.fractional_part_rounding_thresholds`

`constexpr auto fractional_part_rounding_thresholds(int index) -> uint32_t` · [include/fmt/format.h:L3396-L3406][f1]

This function returns a precomputed rounding threshold for a fractional-part index, packed from a string literal.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
