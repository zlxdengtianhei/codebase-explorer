# Format Core Utilities

**Capability.** Provides low-level formatting utilities for allocation checks, byte order, log approximations, Dragonbox conversion, format_as dispatch, and named arguments.

Come here for foundational helpers used across fmt's formatting pipeline. The supplied units mix numeric conversion, iterator adaptation, compile-time traits, and small dispatch utilities.

**Depends on.**

- [Floating-Point Formatting Core](floating-point-formatting-core.md) · graph-confirmed · 7 edge(s)
- [Dragonbox Cache and Assertions](dragonbox-cache-and-assertions.md) · graph-only · 4 edge(s)

**Depended on by.**

- [Big Integer Float Formatting](big-integer-float-formatting.md) · graph-only · 2 edge(s)
- [Chrono Duration and Time Formatting](chrono-duration-and-time-formatting.md) · graph-only · 1 edge(s)

Parent: [Low-Level Formatting Primitives](low-level-formatting-primitives.md)

## Units (26)

<a id="u-d3e706aacc92"></a>
### `format.h-allocator-operations`

`FMT_CONSTEXPR20 auto allocate(size_t n) -> T*` · [include/fmt/format.h:L907-L914][f1]

Allocation asserts that the requested count does not overflow the element-size multiplication.

In constant evaluation it uses array new; otherwise it delegates to the library allocation hook. Deallocation uses array delete in constant evaluation and free otherwise.

<a id="u-714a43b1483f"></a>
### `format.h-bit-casts`

`template <typename To, typename From, FMT_ENABLE_IF(sizeof(To) == sizeof(From))> FMT_…` · [include/fmt/format.h:L261-L270][f1]

These overloads reinterpret object bytes.

The equal-size overload uses the standard bit cast in constant evaluation when available, otherwise copies bytes through a local object. The larger-result overload copies the source into an array of unsigned shorts, then assembles the result in endian order; it requires the destination to be larger than the source.

<a id="u-f49c411a8df3"></a>
### `format.h-buffered-writer`

`class writer` · [include/fmt/format.h:L1104-L1113][f1]

This writer holds either a character buffer or a file stream and does not own the stream.

Its print method formats arguments into the buffer through an appender when a buffer is present, otherwise forwards to the file-printing function.

<a id="u-7cbc0f7dce1c"></a>
### `format.h-clz-fallbacks`

`inline auto clz(uint32_t x) -> int` · [include/fmt/format.h:L209-L214][f1]

These helpers count leading zero bits for 32- and 64-bit values on compilers without usable builtins.

Both assert a nonzero input. The 32-bit helper returns 31 xor the bit-scan index; the 64-bit helper scans the high half first on 32-bit targets, then the low half, and returns 63 xor the index. They are used to define the builtin-count macros.

<a id="u-33feb2f24d21"></a>
### `format.h-copy-helpers`

`template <typename T, typename V, typename OutputIt> FMT_CONSTEXPR auto copy(basic_st…` · [include/fmt/format.h:L564-L567][f1]

The first overload copies a string view into an output iterator through the character-copy helper.

The second is a no-inline wrapper around the same copy operation, used to keep template code size down.

<a id="u-794751692d10"></a>
### `format.h-countl-zero`

`template <typename UInt> FMT_CONSTEXPR20 inline auto countl_zero_fallback(UInt n) -> int` · [include/fmt/format.h:L434-L440][f1]

countl_zero_fallback counts leading zero bits by shifting n left until the most significant bit is set; for n == 0 the loop never terminates because the MSB test never succeeds, so callers must not pass zero.

countl_zero(uint32_t) and countl_zero(uint64_t) use the corresponding compiler builtin when available and not constant-evaluated, otherwise fall back to countl_zero_fallback; the builtin path is skipped in constant evaluation.

<a id="u-f49227c90b86"></a>
### `format.h-escape-detection`

`inline auto needs_escape(uint32_t cp) -> bool` · [include/fmt/format.h:L1988-L1992][f1]

needs_escape returns true for control characters below 0x20, DEL, double quote, and backslash; when FMT_OPTIMIZE_SIZE is greater than 1 it returns false for other code points, otherwise it delegates to is_printable.

The generic find_escape scans code units: for narrow characters it skips every byte with value >= 0x80 (not only UTF-8 continuation bytes) and returns the first unit that needs escaping. The char overload, when UTF-8 is enabled, decodes code points with for_each_codepoint and returns the first code point that needs escaping, including its byte range.

<a id="u-4fe4010950ea"></a>
### `format.h-is-big-endian`

`inline auto is_big_endian() -> bool` · [include/fmt/format.h:L272-L280][f1]

is_big_endian determines host byte order at compile time via preprocessor branches: on _WIN32 it returns false; on __BIG_ENDIAN__ it returns true; when __BYTE_ORDER__ and __ORDER_BIG_ENDIAN__ are defined it compares them; otherwise it bit-casts the integer 1 to a byte array and checks whether the first byte is zero.

The function is a single definition with conditional compilation, not separate overloads.

<a id="u-d642a46a624f"></a>
### `format.h-log-approximations`

`inline auto floor_log10_pow2(int e) noexcept -> int` · [include/fmt/format.h:L1666-L1670][f1]

These functions approximate floor logarithms for powers of two and ten using integer multiplication and arithmetic shifts.

Each asserts its exponent is within the documented range.

<a id="u-c63b77c25d42"></a>
### `format.h-reserve-and-pointer-helpers`

`__attribute__((no_sanitize("undefined"))) #endif FMT_CONSTEXPR20 inline auto reserve(…` · [include/fmt/format.h:L471-L479][f1]

These overloads adapt output iterators for bulk writes.

A contiguous back-inserter is resized and returns a pointer to the new region; an appender tries to reserve and returns the appender. The generic pointer conversion returns null, the raw-pointer overload advances and returns the old pointer, and the back-inserter base-iterator overload returns the iterator unchanged.

<a id="u-8101026e2b24"></a>
### `format.h-wide-multiplication`

`FMT_INLINE auto umul128(uint64_t x, uint64_t y) noexcept -> uint128` · [include/fmt/format.h:L1635-L1661][f1]

These helpers compute wide unsigned products.

The first returns the full 128-bit product using native 128-bit arithmetic, an MSVC intrinsic, or 32-bit decomposition. The second returns only the upper 64 bits. The third multiplies a 64-bit value by a 128-bit value and returns the upper 128 bits by combining two products.

<a id="u-eaafa7b8a007"></a>
### `floor_log10_pow2_minus_log10_4_over_3`

`inline auto floor_log10_pow2_minus_log10_4_over_3(int e) noexcept -> int` · [include/fmt/format-inl.h:L230-L233][f2]

Computes a fast floor expression for log10(2^e) minus log10(4/3), asserting e is within the supported range before applying the fixed-point multiply and shift.

<a id="u-28ac98dc7fac"></a>
### `shorter_interval_case`

`template <typename T> FMT_INLINE auto shorter_interval_case(int exponent) noexcept ->…` · [include/fmt/format-inl.h:L1228-L1273][f2]

Computes the shorter-interval Dragonbox result.

It derives minus_k and beta, gets the cached power, computes left and right endpoints, increments the left endpoint when the exponent is not in the integer-left-endpoint range, and first tries a larger divisor by dividing the right endpoint by ten. If that quotient times ten still reaches the left endpoint, it returns with exponent minus_k+1 after removing trailing zeros. Otherwise it uses the rounded-up shorter-interval value with exponent minus_k; when the exponent is within the shorter-interval tie thresholds, it forces an even significand by decrementing an odd one, and outside those thresholds it increments when the significand is below the left endpoint.

<a id="u-2185fecae653"></a>
### `to_decimal`

`template <typename T> auto to_decimal(T x) noexcept -> decimal_fp<T>` · [include/fmt/format-inl.h:L1275-L1397][f2]

Converts a floating-point value to decimal significand and exponent using Dragonbox.

It extracts significand and exponent bits; normal values subtract bias and significand bits, zero-significand normals use the shorter-interval path, and subnormals use the minimum exponent with zero significand returning zero. Endpoint inclusion is true when the significand is even. It computes minus_k, cache, beta, deltai, and the center product, then tries the larger divisor: if r<deltai it normally succeeds, but when r==0 and the product is integer while the right endpoint is excluded it decrements the significand and falls to the small-divisor path; if r>deltai it falls to the small-divisor path; if r==deltai it compares parity and left-endpoint inclusion, falling to the small-divisor path unless the parity or included-integer condition holds. Larger-divisor success sets exponent minus_k+kappa+1 and removes trailing zeros. The small-divisor path multiplies the significand by ten, sets exponent minus_k+kappa, computes a distance and approximate parity, checks divisibility by the small divisor, adds the divided distance, and returns early when not divisible; when divisible it compares the center parity and integer flag, decrementing on parity mismatch or on an integer tie with an odd significand.

<a id="u-9e12a5658814"></a>
### `formatter<std::basic_string<Char, Traits, Allocator>, Char>`

`class formatter<std::basic_string<Char, Traits, Allocator>, Char> : public formatter<…` · [include/fmt/format.h:L4278-L4280][f1]

This formatter specialization makes standard strings format through the string-view formatter.

<a id="u-50c1515699cb"></a>
### `FMT_BEGIN_EXPORT`

`class fallback_digit_grouping { public: constexpr fallback_digit_grouping(locale_ref,…` · [include/fmt/format.h:L4161-L4177][f1]

has_format_as is a compile-time trait that detects whether a type provides a format_as_result alias, enabling the formatter specialization that delegates formatting to format_as.

<a id="u-4ccf5930fd4b"></a>
### `assume`

`FMT_INLINE void assume(bool condition)` · [include/fmt/format.h:L456-L463][f1]

This helper communicates an assumption to the compiler.

It is a no-op at runtime; when supported it emits a compiler assume or an unreachable branch for a false condition. It does not validate or throw.

<a id="u-8d91c9645112"></a>
### `include/fmt/format.h:format_as`

`template <typename Enum, FMT_ENABLE_IF(std::is_enum<Enum>::value)> constexpr auto for…` · [include/fmt/format.h:L4324-L4327][f1]

This function converts an enum to its underlying integer type for formatting.

<a id="u-cc687cdfcc2a"></a>
### `include/fmt/format.h:format (2)`

`template <typename... T> FMT_NODISCARD FMT_INLINE auto format(format_string<T...> fmt…` · [include/fmt/format.h:L4660-L4664][f1]

This function formats arguments into a string by building the argument pack and calling the non-locale string formatter.

<a id="u-4c08b8156b39"></a>
### `getsign`

`template <typename Char> constexpr auto getsign(sign s) -> Char` · [include/fmt/format.h:L1241-L1244][f1]

This function maps a sign enum to its character by selecting one byte from a packed literal.

It does not validate the enum value.

<a id="u-a1eeefdf2bf1"></a>
### `operator""_a`

`template <detail::fixed_string S> constexpr auto operator""_a()` · [include/fmt/format.h:L4460-L4463][f1]

This literal operator builds a named-argument wrapper from a compile-time string when non-type template arguments are available, otherwise from a runtime string pointer.

<a id="u-0b2c746650d7"></a>
### `maybe_set_debug_format`

`template <typename Formatter> FMT_CONSTEXPR auto maybe_set_debug_format(Formatter& f,…` · [include/fmt/format.h:L934-L938][f1]

This helper calls a formatter's debug-format setter when that member exists.

If the member is absent, the fallback overload does nothing. It is selected by expression SFINAE.

<a id="u-02541acd0c83"></a>
### `multiply`

`FMT_CONSTEXPR inline auto multiply(uint64_t lhs, uint64_t rhs) -> uint64_t` · [include/fmt/format.h:L1880-L1895][f1]

This function multiplies two 64-bit significands and returns the rounded high 64 bits.

It rounds half up using the top bit of the low product; it uses native 128-bit arithmetic when available, otherwise 32-bit partial products.

<a id="u-f2b0cc404380"></a>
### `system_error`

`template <typename... T> auto system_error(int error_code, format_string<T...> fmt, T…` · [include/fmt/format.h:L4585-L4589][f1]

This function constructs a system error by formatting the format string and arguments through the system-error formatter.

<a id="u-08b36af3e149"></a>
### `thousands_sep`

`template <typename Char> inline auto thousands_sep(locale_ref loc) -> thousands_sep_r…` · [include/fmt/format.h:L1369-L1373][f1]

This function obtains locale thousands-separator data.

It calls the narrow implementation and converts the separator to the requested character type; the wide specialization calls the wide implementation directly.

<a id="u-06ca74917d77"></a>
### `include/fmt/format.h:format (3)`

`template <typename FormatContext> FMT_CONSTEXPR auto format(const T& value, FormatCon…` · [include/fmt/format.h:L4290-L4295][f1]

This formatter calls the user-provided format-as function, binds the result to an lvalue, and delegates to the formatter for the result type.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format-inl.h
