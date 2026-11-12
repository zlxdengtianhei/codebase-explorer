# Floating-Point Formatting Core

**Capability.** Extracts floating-point components and writes fixed, exponential, and hexadecimal floating-point representations.

This module covers core floating-point formatting. It includes component extraction, normalization, fixed/exponential selection, and hexadecimal output.

**Depends on.**

- [Buffer and Core Integer Writer](buffer-and-core-integer-writer.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Format Core Utilities](format-core-utilities.md) · graph-confirmed · 7 edge(s)

Parent: [Low-Level Formatting Primitives](low-level-formatting-primitives.md)

## Units (7)

<a id="u-216259f96d7c"></a>
### `format.h-float-bit-layout`

`template <typename Float> constexpr auto has_implicit_bit() -> bool` · [include/fmt/format.h:L1751-L1754][f1]

These helpers describe floating-point storage.

The implicit-bit test is false only for 64-bit significands. Significand-bit count is 112 for the extended float type, otherwise digits minus the implicit bit. The exponent mask shifts a low-bit mask into place. The bias is 16383 for the extended type, otherwise maximum exponent minus one. Exponent text size is four for absolute exponents below 100, five below 1000, and six otherwise.

<a id="u-dab5c96cd227"></a>
### `format.h-float-decomposition`

`template <typename Float, FMT_ENABLE_IF(!is_double_double<Float>::value)> FMT_CONSTEX…` · [include/fmt/format.h:L1827-L1850][f1]

The main assignment extracts sign, exponent, and significand bits from a floating value, handles subnormals, adds the implicit bit when present, and returns whether the predecessor is closer.

The double-double overload delegates to double assignment.

<a id="u-6f3bd283527c"></a>
### `format.h-float-notation-selection`

`template <typename Char, typename Grouping, typename OutputIt, typename DecimalFP> FM…` · [include/fmt/format.h:L2824-L2863][f1]

The core writer chooses fixed notation when the presentation is fixed or when the exponent falls in the fixed range and the presentation is not exponential; otherwise it writes exponential notation with a point after the first digit and an exponent.

The wrapper selects fallback grouping in constant evaluation or when locale support is off, otherwise locale-aware grouping.

<a id="u-6de2932e7179"></a>
### `format.h-hexfloat-formatting`

`template <typename Float, FMT_ENABLE_IF(!is_double_double<Float>::value)> FMT_CONSTEX…` · [include/fmt/format.h:L3310-L3388][f1]

The main overload formats a floating value as hexadecimal floating point.

It extracts significand and exponent, resets zero exponent, rounds to requested precision, handles long-double overflow, writes hex digits, decimal point, and p exponent. The double-double overload delegates to double.

<a id="u-5daad04cb911"></a>
### `abort_fuzzing_if`

`FMT_CONSTEXPR inline void abort_fuzzing_if(bool condition)` · [include/fmt/format.h:L234-L239][f1]

This helper is a no-op unless fuzzing support is enabled.

When enabled and the condition is true it throws a runtime error; otherwise it returns normally. It has no other side effects.

<a id="u-c1733e051644"></a>
### `normalize`

`template <int SHIFT = 0, typename F> FMT_CONSTEXPR auto normalize(basic_fp<F> value) …` · [include/fmt/format.h:L1862-L1877][f1]

This function normalizes a floating significand by shifting left until the implicit bit is set, decrementing the exponent, then applying the fixed offset for the target significand width.

<a id="u-b5f06841c2d6"></a>
### `FMT_BEGIN_EXPORT.size_padding.write_fixed`

`template <typename Char, typename Grouping, typename OutputIt, typename DecimalFP> FM…` · [include/fmt/format.h:L2759-L2822][f1]

This function writes a decimal floating value in fixed notation.

For nonnegative exponents it appends zeros and optional fractional zeros, applying grouping to the integer part. For positive decimal point positions it writes the point and trailing zeros. For negative positions it writes a leading zero, optional point, leading zeros, significand, and trailing zeros. It handles sign, alternate form, precision, grouping, and right padding.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
