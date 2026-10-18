# Floating-Point Shortest Formatting

**Capability.** Dragonbox-based conversion of float/double to shortest decimal, with per-type cache tables, constant-time arithmetic kernels, and significand cleanup.

Consult when changing or debugging numeric output. The type-specific cache accessors and shared helpers cooperate inside to_decimal and shorter_interval_case.

**Depends on.**

- [Error Reporting](core-errors.md) · graph-only · 11 edge(s)

Parent: [Core Runtime & Engine](core-runtime.md)

## Units (8)

<a id="u-2185fecae653"></a>
### `to_decimal`

`template <typename T> auto to_decimal(T x) noexcept -> decimal_fp<T>` · [include/fmt/format-inl.h:L1275-L1397][f1]

Core Dragonbox conversion of a floating-point value x into its shortest decimal (significand and decimal exponent), noexcept.

It bit-casts x, splits significand and biased exponent: normal numbers (exponent != 0) rebias the exponent and, when the significand is zero, take the shorter-interval path via shorter_interval_case, else restore the implicit leading bit; subnormals with zero significand return {0,0}, other subnormals use min_exponent-derived exponent. Endpoint inclusion flags are the significand's parity. It computes minus_k = floor_log10_pow2(exponent) - kappa, the cache, beta, deltai = compute_delta, and z_mul = compute_mul((two_fc|1) << beta). If the remainder r < deltai, the larger divisor succeeded, except when r == 0 and the product is integral with the right endpoint excluded, which forces the small-divisor path. If r > deltai it always goes to the small-divisor path; if r == deltai it compares fractional parity via compute_mul_parity(two_fc-1) and falls through to the small-divisor path unless the parity condition holds. On success it returns exponent minus_k + kappa + 1 adjusted by remove_trailing_zeros. The small-divisor path multiplies the significand by 10, sets exponent minus_k + kappa, computes dist, determines approx_y_parity from its low bit, divides dist by 10^kappa with check_divisibility_and_divide_by_pow10, adds it to the significand, and if not divisible returns directly; otherwise compute_mul_parity(two_fc) decides whether to decrement once (parity mismatch) or round to even on a tie. Known binary32 counterexample inputs (29711844 * 2^-82/-81) are documented as harmless by the algorithm's own integer-check analysis.

calls: [shorter_interval_case](core-float.md#u-28ac98dc7fac), [floor_log10_pow2][f2], [grp:format-inl.h-remove-trailing-zeros][f1], [format-inl.h-dragonbox-arithmetic-helpers](core-float.md#u-9bdd93270877)

**Uncertainties.**

- umul192_upper128 used by compute_mul for double is not defined in this batch's source.

<a id="u-28ac98dc7fac"></a>
### `shorter_interval_case`

`template <typename T> FMT_INLINE auto shorter_interval_case(int exponent) noexcept ->…` · [include/fmt/format-inl.h:L1228-L1273][f1]

Produces the shortest decimal representation when the binary exponent's uncertainty interval is short (significand of the input is zero), for any floating type T.

It computes minus_k = floor_log10_pow2_minus_log10_4_over_3(exponent), beta = exponent + floor_log2_pow10(-minus_k), and fetches the cache for -minus_k; computes the interval endpoints xi (left) and zi (right). If the left endpoint is not known to be an integer (exponent outside [2,3] per is_left_endpoint_integer_shorter_interval) xi is incremented. It first tries the larger divisor: significand = zi/10; if significand*10 >= xi, the exponent is minus_k+1 plus any trailing zeros removed and the result returns immediately. Otherwise it takes the round-up value as significand with exponent minus_k and adjusts for ties: when exponent lies in float_info<T>'s tie thresholds an odd significand is decremented (round to even); otherwise it is incremented when below xi.

calls: [floor_log2_pow10][f2], [format-inl.h-dragonbox-arithmetic-helpers](core-float.md#u-9bdd93270877)

**Uncertainties.**

- Semantics of float_info<T> tie thresholds are defined in format.h, not in this batch.

<a id="u-9bdd93270877"></a>
### `format-inl.h-dragonbox-arithmetic-helpers`

`inline auto umul96_upper64(uint32_t x, uint64_t y) noexcept -> uint64_t` · [include/fmt/format-inl.h:L211-L213][f1]

Constant-time arithmetic kernels used by the Dragonbox conversion.

umul96_upper64 shifts a 32-bit value left by 32 and returns the upper 64 bits of the product with a 64-bit value; umul192_lower128 multiplies a 64-bit by a 128-bit cache entry and returns the low 128 bits (high times y.high plus the high half of umul128(x, y.low)); umul96_lower64 returns the plain 64-bit product. floor_log10_pow2_minus_log10_4_over_3 asserts e in [-2985, 2936] and computes a fixed-point floor via (e*631305 - 261663) >> 21. check_divisibility_and_divide_by_pow10<N> asserts n <= divisor*10, multiplies n by a magic constant ceil(2^k/d)+1, tests divisibility by d (10 or 100) via the low bits, and replaces n by floor(n/d), returning the divisibility flag. small_division_by_pow10<N> is the non-mutating division variant. The two divide_by_10_to_kappa_plus_1 overloads compute floor(n/10^(kappa+1)) for 32-bit n via a 64-bit multiply by ceil(2^37/100), and for 64-bit n via umul128_upper64 by ceil(2^71/1000) shifted right 7. All are noexcept but rely on FMT_ASSERT preconditions; violating them invokes assert_fail.

<a id="u-8c64638b39d1"></a>
### `format-inl.h-cache-accessor-double`

`static auto get_cached_power(int k) noexcept -> uint128` · [include/fmt/format-inl.h:L389-L393][f1]

Specialization of cache_accessor for double whose cache entries are uint128.

get_cached_power asserts k in [min_k, max_k] and indexes a pow10_significands table; with FMT_USE_FULL_CACHE_DRAGONBOX (the default unless __OPTIMIZE_SIZE__) the table is a large full cache and the entry is returned directly. Without the full cache, a compressed table of every 27th power is used: it computes the base index and offset, returns the base entry when the offset is zero, otherwise recovers the exact cache by multiplying the base by the corresponding power of 5 (umul128), shifting by alpha = floor_log2_pow10(kb+offset) - floor_log2_pow10(kb) - offset (asserted in (0,64)), and adding one to the low word. compute_mul uses umul192_upper128 (is_integer = low half zero), compute_delta takes the top of cache.high(), compute_mul_parity multiplies with umul192_lower128 and derives parity and is_integer from the 192-bit product, and the three shorter-interval helpers work on cache.high() with the same shift patterns as the float version. The shared free get_cached_power(int) simply forwards to cache_accessor<double>::get_cached_power.

**Uncertainties.**

- The exact sub-line structure of get_cached_power's three inventory fragments (table, full-cache return, compressed recovery) is inferred from the FMT_USE_FULL_CACHE_DRAGONBOX branches visible in the source.

<a id="u-ff2e2675f82c"></a>
### `format-inl.h-cache-accessor-float`

`static auto get_cached_power(int k) noexcept -> uint64_t` · [include/fmt/format-inl.h:L295-L326][f1]

Specialization of cache_accessor for float with a uint64_t cache table of 128 precomputed pow10 significands, indexed by k - float_info<float>::min_k with an asserted range check.

compute_mul multiplies the carrier by the cache with umul96_upper64, returning the shifted-down result and is_integer = (low 32 bits of the product are zero). compute_delta extracts beta+1 bits from the top of the cache as uint32_t. compute_mul_parity (asserting 1 <= beta < 64) multiplies via umul96_lower64 and returns the parity bit at position 64-beta and is_integer from the bits above. The shorter-interval endpoint helpers shift the cache (minus/plus a correction derived from the cache itself) right by 64 - significand_bits - 1 - beta, and compute_round_up averages the extracted top bits plus one. All static, noexcept; out-of-range k or beta triggers assert_fail.

<a id="u-8dfec47e7e96"></a>
### `format-inl.h-fp-helpers`

`template <typename F> inline auto operator==(basic_fp<F> x, basic_fp<F> y) -> bool` · [include/fmt/format-inl.h:L192-L195][f1]

Small floating-point comparison and bit-rotation helpers.

operator== compares two basic_fp values by both significand (f) and exponent (e). The two rotr overloads perform a rotate-right of a 32- or 64-bit value: the shift is first masked to the type's width (r &= 31 / 63), then implemented as (n >> r) | (n << (width - r)), which compilers are expected to lower to a ror instruction; both are noexcept.

<a id="u-d2696f29fb9f"></a>
### `format-inl.h-remove-trailing-zeros`

`FMT_INLINE auto remove_trailing_zeros(uint32_t& n, int s = 0) noexcept -> int` · [include/fmt/format-inl.h:L1172-L1190][f1]

Strips trailing decimal zeros from a significand and returns how many were removed.

The 32-bit version (asserting n != 0) repeatedly multiplies by the modular inverse of 25 modulo 2^32 and rotates right by 2; the loop continues while the rotated result is <= UINT32_MAX/100 (i.e. the value was divisible by 100), removing two zeros per iteration, then a single pass with the inverse of 5 removes a possible odd zero (setting bit 0 of the count). The 64-bit version first checks divisibility by 10^8: if divisible it divides by 10^8, delegates to the 32-bit variant seeded with s=8, and writes the quotient back; otherwise it runs the same inverse-of-25/inverse-of-5 loops with 64-bit constants. Both are noexcept and mutate n in place.

calls: [format-inl.h-fp-helpers](core-float.md#u-8dfec47e7e96)

<a id="u-ffc1f726f446"></a>
### `format-inl.h-formatter-bigint`

`FMT_CONSTEXPR auto parse(format_parse_context& ctx) -> format_parse_context::iterator` · [include/fmt/format-inl.h:L1402-L1405][f1]

Formats a detail::bigint as hexadecimal.

parse accepts no format specifiers and returns ctx.begin() unchanged, so any specifier text would remain unconsumed (the formatter ignores the rest of the spec). format iterates bigits_ from most significant to least: the first is written as {:x} without padding, subsequent ones as {:08x} (zero-padded to full bigit width), and if exp_ > 0 appends 'p' followed by exp_ * bigint::bigit_bits, giving a hex-mantissa/p-exponent form. Reads the bigint's private members directly (it is a friend or same-access context).

**Uncertainties.**

- Why format may access bigint::bigits_ and exp_ (friendship) is not shown in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format-inl.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h