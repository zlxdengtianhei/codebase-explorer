# Binary and float primitives

**Capability.** Provides bit-level primitives: leading-zero counting, endianness detection, float format traits, power-of-two digit formatting, and hexfloat rendering.

This module collects the numeric/bit manipulation helpers shared by float and integer formatting, including the widening bit_cast and hexfloat writer. Come here for low-level representation questions.

**Depends on.**

- [Value writing engine](value-writing-engine.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Float conversion entry points](float-conversion-entry-points.md) · graph-only · 7 edge(s)
- [Chrono formatting internals](chrono-formatting-internals.md) · graph-only · 3 edge(s)
- [Bigint fallback algorithm](bigint-fallback-algorithm.md) · graph-only · 1 edge(s)
- [Integer decimal formatting](integer-decimal-formatting.md) · graph-only · 1 edge(s)

Parent: [Float presentation rendering](float-presentation-rendering.md)

## Units (8)

<a id="u-758031c5a689"></a>
### `format.h-basic-fp`

`template <typename F> struct basic_fp` · [include/fmt/format.h:L1813-L1820][f1]

Represents f * 2^e with an unsigned significand.

The Float constructor calls assign, which bit_casts to the carrier type, splits significand and biased exponent, and returns true iff the predecessor is closer (f==0 and biased_e>1, i.e. a normalized power of two other than the smallest). Subnormals use biased exponent 1; formats with an implicit bit add it to f; e is derived from the bias and significand width (plus one when there is no implicit bit). The double-double overload delegates to the double assign.

<a id="u-794751692d10"></a>
### `format.h-countl-zero`

`template <typename UInt> FMT_CONSTEXPR20 inline auto countl_zero_fallback(UInt n) -> int` · [include/fmt/format.h:L434-L440][f1]

countl_zero_fallback counts leading zeros by shifting the input left until the MSB is set; for nonzero inputs it returns the shift count, and for zero input the loop never terminates (n stays 0 and the MSB test never succeeds), so there is no return value for zero.

The countl_zero overloads for uint32_t/uint64_t use the platform CLZ builtin at runtime when available (builtin CLZ is itself undefined for zero) and fall back to the fallback in constant evaluation or when no builtin exists; callers must therefore pass nonzero values.

<a id="u-a5975ed8659a"></a>
### `format.h-endianness-detection`

`inline auto is_big_endian() -> bool` · [include/fmt/format.h:L272-L280][f1]

Returns endianness: fixed false on _WIN32, true on __BIG_ENDIAN__, from __BYTE_ORDER__ when defined, otherwise probes by bit_casting int 1 to a char array and checking the first byte.

The second overload is the fallback branch body only.

<a id="u-b755542164d4"></a>
### `format.h-float-layout-helpers`

`template <typename Float> constexpr auto has_implicit_bit() -> bool` · [include/fmt/format.h:L1751-L1754][f1]

has_implicit_bit is false only for 80-bit formats (digits==64); num_significand_bits returns 112 for float128, otherwise digits minus the implicit bit; exponent_mask builds the biased-exponent mask from float_info's exponent_bits shifted over the significand; exponent_bias returns 16383 for float128, otherwise max_exponent-1.

<a id="u-9be007304ad2"></a>
### `format.h-format-base2e`

`template <typename Char, typename UInt> FMT_CONSTEXPR auto do_format_base2e(int base_…` · [include/fmt/format.h:L1502-L1513][f1]

Formats an unsigned value in a power-of-two base (binary/octal/hex) by repeatedly extracting base_bits-wide digits from the end of the buffer; digits below 10 map to '0'+digit, others to the hex alphabet (uppercase when requested).

The pointer wrapper returns out+num_digits; the back-insert iterator overload uses to_pointer when possible, else a stack buffer sized num_bits<UInt> and copy_noinline.

<a id="u-bae03cb4d834"></a>
### `format.h-format-hexfloat`

`template <typename Float, FMT_ENABLE_IF(!is_double_double<Float>::value)> FMT_CONSTEX…` · [include/fmt/format.h:L3310-L3388][f1]

Renders a float in hexfloat form: decomposes to significand/exponent (resetting the exponent for zero to print 0x0p+0), normalizes the leading hex digit (decrementing the exponent when it exceeds 1), applies precision by rounding the next hex digit (>=8 rounds up) with a long-double overflow fix when there is no implicit bit, formats hex digits, trims the zero tail, appends '.' when alt or digits remain or precision demands, pads to precision with zeros, and writes 'p'/'P' with a signed decimal exponent.

The double-double overload delegates via a cast to double.

<a id="u-e700fcb4434b"></a>
### `format.h-heterogeneous-bit-cast`

`template <typename To, typename From, FMT_ENABLE_IF(sizeof(To) > sizeof(From))> inlin…` · [include/fmt/format.h:L417-L420][f1]

Widening bit_cast for sizeof(To)>sizeof(From): reinterprets the source as an array of unsigned short, then assembles the result by shifting in the shorts, most-significant first on big-endian and least-significant first on little-endian.

Used for 96-bit long double and 128-bit pointers.

<a id="u-95e26e814ebc"></a>
### `format.h-limits-helpers`

`template <typename T> constexpr auto max_value() -> T` · [include/fmt/format.h:L404-L406][f1]

max_value returns std::numeric_limits<T>::max() (parenthesized to resist the max macro); num_bits returns numeric_limits digits, with specializations returning 128 for native and custom 128-bit integer types where digits may report 0.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
