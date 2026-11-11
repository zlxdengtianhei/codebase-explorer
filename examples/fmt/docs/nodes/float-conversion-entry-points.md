# Float conversion entry points

**Capability.** Converts doubles to shortest decimal digits via Dragonbox, computes log-based exponents, and exposes locale-aware vformat/vformat_to entry points.

Readers tracing how a double becomes digits plus an exponent should start with the Dragonbox core and its helpers here. The module also contains the public vformat/vformat_to wrappers that pack arguments and format into buffers.

**Depends on.**

- [Bigint fallback algorithm](bigint-fallback-algorithm.md) · graph-confirmed · 1 edge(s)
- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-confirmed · 7 edge(s) · Float conversion entry points rely on the shared numeric core for 128-bit arithmetic, pow10 caches, and assertions.
- [Binary and float primitives](binary-and-float-primitives.md) · graph-only · 7 edge(s)
- [Core argument and buffer base](core-argument-and-buffer-base.md) · graph-only · 1 edge(s)
- [Value writing engine](value-writing-engine.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-confirmed · 1 edge(s)

Parent: [Float to decimal conversion](float-to-decimal-conversion.md)

## Units (6)

<a id="u-1a06c24acc0f"></a>
### `format.h-dragonbox-log-approximations`

`inline auto floor_log10_pow2(int e) noexcept -> int` · [include/fmt/format.h:L1666-L1670][f1]

floor_log10_pow2 computes floor(log10(2^e)) for e in [-2620,2620] as (e*315653)>>20 with an assert on range; floor_log2_pow10 computes floor(log2(10^e)) for e in [-1233,1233] as (e*1741647)>>19, also range-asserted.

Both rely on arithmetic right shift.

<a id="u-41609d885cf1"></a>
### `format.h-format`

`inline auto vformat(locale_ref loc, string_view fmt, format_args args) -> std::string` · [include/fmt/format.h:L4611-L4616][f1]

vformat/format with a locale: format into a memory_buffer via detail::vformat_to and return a std::string built from it; the template wrapper packs the arguments.

The locale-less format (692) does the same without a locale.

<a id="u-88d292e63083"></a>
### `format.h-format-to`

`template <typename OutputIt, FMT_ENABLE_IF(detail::is_output_iterator<OutputIt, char>…` · [include/fmt/format.h:L4624-L4631][f1]

vformat_to obtains a buffer for the output iterator, formats into it, and returns the iterator obtained from the buffer; the template wrapper packs args and forwards.

<a id="u-2185fecae653"></a>
### `to_decimal`

`template <typename T> auto to_decimal(T x) noexcept -> decimal_fp<T>` · [include/fmt/format-inl.h:L1275-L1397][f2]

Core Dragonbox routine converting a floating value to the shortest decimal significand/exponent pair.

Zero returns {0,0}. Normal values with zero significand bits delegate to shorter_interval_case; otherwise the implicit bit is set. Subnormals get the min-exponent offset. It computes the cached power and beta, then tries the big divisor: the remainder r versus deltai decides acceptance — r < deltai accepts unless r==0 with an integer product and an excluded right endpoint (falls through to the small-divisor path with r reset to big_divisor); r > deltai falls through; r == deltai accepts only if the left endpoint's fractional-part parity permits. The accepted path sets exponent minus_k+kappa+1 and strips trailing zeros. The small-divisor path multiplies the significand by 10, computes dist, checks divisibility by 10^kappa, and adjusts the significand downward on parity mismatch or odd tie. A source comment notes two known binary32 inputs where the integer check is theoretically wrong but the affected branch is never executed for them.

<a id="u-be687077ca67"></a>
### `FMT_BEGIN_EXPORT.size_padding.format_float`

`template <typename Float> FMT_CONSTEXPR20 auto format_float(Float value, int precisio…` · [include/fmt/format.h:L3408-L3711][f1]

Formats a double (floats are widened) into a digit buffer, returning the decimal exponent.

Zero is special-cased ('0' or precision zeros in fixed mode). Non-fast floats (or constant evaluation) estimate exp10 from log2 and set the dragon fixup flag; fast floats extract significand/exponent (normalizing subnormals with an asserted shift), compute the first 18–19-digit segment via umul192_upper128 with a cached power, adjust fixed precision, and, when the segment has enough digits, take a fast path that prints 9-digit subsegments with magic-number division and rounds using the threshold table (round-half-even, with carry propagation that may bump exp or append a zero in fixed mode); otherwise dragon4 handles it with a precision cap (767, or a computed bound under fixup). Finally, non-fixed non-alt output has trailing zeros stripped back into the exponent.

<a id="u-fe34c02e203c"></a>
### `FMT_BEGIN_EXPORT.size_padding.fractional_part_rounding_thresholds`

`constexpr auto fractional_part_rounding_thresholds(int index) -> uint32_t` · [include/fmt/format.h:L3396-L3406][f1]

Returns a rounding threshold table entry for the fixed-precision fast path, packed in UTF-32 string literals because constexpr functions cannot have static arrays.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format-inl.h
