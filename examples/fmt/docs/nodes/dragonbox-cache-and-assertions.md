# Dragonbox Cache and Assertions

**Capability.** Provides Dragonbox power caches, decimal division helpers, trailing-zero removal, interval checks, and assertion abort reporting.

This module supports Dragonbox conversion and low-level numeric helpers. It also contains assertion failure reporting and cached-power access.

**Depended on by.**

- [Platform File and Locale Internals](platform-file-and-locale-internals.md) · graph-confirmed · 1 edge(s)
- [Big Integer Float Formatting](big-integer-float-formatting.md) · graph-only · 12 edge(s)
- [Chrono Format Handlers](chrono-format-handlers.md) · graph-only · 7 edge(s)
- [Buffer and Core Integer Writer](buffer-and-core-integer-writer.md) · graph-only · 4 edge(s)
- [Format Core Utilities](format-core-utilities.md) · graph-only · 4 edge(s)
- [ANSI Color Style Formatting](ansi-color-style-formatting.md) · graph-only · 3 edge(s)
- [Format Spec Parser](format-spec-parser.md) · graph-only · 3 edge(s)
- [Format Spec Parsing and Writing](format-spec-parsing-and-writing.md) · graph-only · 3 edge(s)
- [Chrono Duration and Time Formatting](chrono-duration-and-time-formatting.md) · graph-only · 2 edge(s)
- [Format Argument Type Mapping](format-argument-type-mapping.md) · graph-only · 2 edge(s)
- [Integer and Pointer Formatting](integer-and-pointer-formatting.md) · graph-only · 2 edge(s)
- [Dynamic Arguments, Enums, and C API](dynamic-arguments-enums-and-c-api.md) · graph-only · 1 edge(s)

Parent: [Platform and Dragonbox Support](platform-and-dragonbox-support.md)

## Units (7)

<a id="u-cf0870f1d313"></a>
### `format-inl.h-double-cache-accessor`

`static auto get_cached_power(int k) noexcept -> uint128` · [include/fmt/format-inl.h:L389-L393][f1]

Provides Dragonbox cache operations for double.

get_cached_power asserts k is within the double cache range; with the full cache it indexes the table directly, otherwise it recovers an entry from a compressed base using a power of five, asserts the shift is in range, asserts recovered_cache.low()+1 is nonzero, and returns the high word with the low word incremented. compute_mul returns only r.high() as the carrier and sets is_integer from r.low()==0. compute_delta extracts a shifted high-word field. compute_mul_parity asserts beta is between 1 and 63 and returns parity plus an integer flag from the lower 128-bit product. The endpoint helpers derive left, right, and rounded-up shorter-interval values from the high cache word and beta.

<a id="u-26ea9db6e1b7"></a>
### `format-inl.h-float-cache-accessor`

`static auto get_cached_power(int k) noexcept -> uint64_t` · [include/fmt/format-inl.h:L295-L326][f1]

Provides Dragonbox cache operations for float.

get_cached_power asserts k is within the float cache range and indexes the fixed significand table. compute_mul returns the upper 32 bits of the 96-bit product and marks integer when the low 32 bits are zero. compute_delta extracts a shifted cache field. compute_mul_parity asserts beta is between 1 and 63, computes the low 64-bit product, and returns parity plus an integer flag. The endpoint helpers derive left, right, and rounded-up shorter-interval values from the cache and beta.

<a id="u-c19bc8b6143d"></a>
### `format-inl.h-small-power-of-ten-division-helpers`

`template <int N> auto check_divisibility_and_divide_by_pow10(uint32_t& n) noexcept ->…` · [include/fmt/format-inl.h:L243-L265][f1]

Both helpers use a magic-number multiply and shift for division by 10 or 100, asserting the input is at most ten times the divisor.

check_divisibility_and_divide_by_pow10 also returns whether the original value was divisible by the divisor, using the low comparison mask before shifting; small_division_by_pow10 returns only the quotient.

<a id="u-8966b901068a"></a>
### `format-inl.h-trailing-zero-removal`

`FMT_INLINE auto remove_trailing_zeros(uint32_t& n, int s = 0) noexcept -> int` · [include/fmt/format-inl.h:L1172-L1190][f1]

Removes trailing decimal zeros from a nonzero value and returns the count removed.

The 32-bit version repeatedly divides by 100 using modular-inverse rotation, then optionally divides by 10 and sets the low count bit. The 64-bit version first handles divisibility by 10^8 by delegating the quotient to the 32-bit version and adding eight; otherwise it uses 64-bit modular inverses with the same divide-by-100 then divide-by-10 pattern.

<a id="u-51c7265a0ebb"></a>
### `assert_fail`

`FMT_FUNC void assert_fail(const char* file, int line, const char* message)` · [include/fmt/format-inl.h:L49-L54][f1]

Reports a failed assertion by writing file, line, and message to stderr with unchecked fprintf, then calls abort; it does not return.

<a id="u-f82123e8ff09"></a>
### `get_cached_power`

`FMT_FUNC auto get_cached_power(int k) noexcept -> uint128` · [include/fmt/format-inl.h:L1158-L1160][f1]

Delegates cached-power lookup to the double cache accessor.

<a id="u-674f825ec9f3"></a>
### `is_left_endpoint_integer_shorter_interval`

`template <typename T> auto is_left_endpoint_integer_shorter_interval(int exponent) no…` · [include/fmt/format-inl.h:L1163-L1169][f1]

Returns true only when the exponent is between the shorter-interval left-endpoint integer thresholds, inclusive.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format-inl.h
