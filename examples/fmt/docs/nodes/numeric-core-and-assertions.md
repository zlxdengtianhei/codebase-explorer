# Numeric core and assertions

**Capability.** Supplies 128-bit arithmetic, pow10 caches, Dragonbox multiplication helpers, and the library-wide assertion failure handler.

This is the shared numeric foundation: fixed-width multiplication, the double/float pow10 caches, and assert_fail. Nearly every float or integer path depends on it, so it is the most-called module in the graph.

**Depends on.**

- [Float conversion entry points](float-conversion-entry-points.md) · graph-confirmed · 1 edge(s)
- [Value writing engine](value-writing-engine.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Bigint fallback algorithm](bigint-fallback-algorithm.md) · graph-confirmed · 9 edge(s) · The bigint fallback uses the numeric core's arithmetic helpers and assertion handler for exact float formatting.
- [Float conversion entry points](float-conversion-entry-points.md) · graph-confirmed · 7 edge(s) · Float conversion entry points rely on the shared numeric core for 128-bit arithmetic, pow10 caches, and assertions.
- [Chrono formatting internals](chrono-formatting-internals.md) · graph-only · 9 edge(s)
- [Inline implementation and stdio](inline-implementation-and-stdio.md) · graph-only · 4 edge(s)
- [Value writing engine](value-writing-engine.md) · graph-only · 4 edge(s)
- [Text styling and colors](text-styling-and-colors.md) · graph-only · 3 edge(s)
- [Core argument and buffer base](core-argument-and-buffer-base.md) · graph-only · 2 edge(s)
- [Formatting driver and contexts](formatting-driver-and-contexts.md) · graph-only · 2 edge(s)
- [Character and pointer writers](character-and-pointer-writers.md) · graph-only · 1 edge(s)
- [Core formatting utilities](core-formatting-utilities.md) · graph-only · 1 edge(s)
- [Dynamic args, enums, ostream](dynamic-args-enums-ostream.md) · graph-only · 1 edge(s)
- [Float presentation writers](float-presentation-writers.md) · graph-only · 1 edge(s)
- [Integer decimal formatting](integer-decimal-formatting.md) · graph-only · 1 edge(s)
- [Packed format specs](packed-format-specs.md) · graph-only · 1 edge(s)
- [Spec parsing and printf mapping](spec-parsing-and-printf-mapping.md) · graph-only · 1 edge(s)

Parent: [Float to decimal conversion](float-to-decimal-conversion.md)

## Units (9)

<a id="u-8c64638b39d1"></a>
### `format-inl.h-cache-accessor-double`

`static auto get_cached_power(int k) noexcept -> uint128` · [include/fmt/format-inl.h:L389-L393][f1]

Double specialization with 128-bit cache entries.

get_cached_power asserts k in range; with FMT_USE_FULL_CACHE_DRAGONBOX it indexes the full static table, otherwise it uses a compressed table (stride 27) and reconstructs the entry by multiplying the base cache by a power of five (asserting the shift amount alpha is in (0,64) and the low word doesn't wrap), returning the reconstructed value plus one in the low word. compute_mul/parity/delta and the shorter-interval helpers mirror the float specialization but operate on the 128-bit entry's high word via umul192 helpers; parity checks combine high and low words.

<a id="u-ff2e2675f82c"></a>
### `format-inl.h-cache-accessor-float`

`static auto get_cached_power(int k) noexcept -> uint64_t` · [include/fmt/format-inl.h:L295-L326][f1]

Float specialization of the pow10 cache: get_cached_power indexes a static 64-bit significand table for k in [min_k, max_k] (asserted).

compute_mul multiplies the carrier by the cache entry via umul96_upper64 and reports whether the low 32 bits are zero (integer result); compute_delta extracts the top beta+1 bits; compute_mul_parity (asserts 1<=beta<64) returns the parity of bit 64-beta of umul96_lower64(two_f, cache) and whether the product's relevant portion is zero; the three shorter-interval helpers derive left/right endpoints and a round-up value from the cache by shifting, using float's significand bit count.

<a id="u-9bdd93270877"></a>
### `format-inl.h-dragonbox-arithmetic-helpers`

`inline auto umul96_upper64(uint32_t x, uint64_t y) noexcept -> uint64_t` · [include/fmt/format-inl.h:L211-L213][f1]

Fixed-width multiplication and fast-log helpers for the Dragonbox algorithm: umul96_upper64/umul96_lower64 compute parts of a 32x64-bit product, umul192_lower128 the low 128 bits of a 64x128-bit product.

floor_log10_pow2_minus_log10_4_over_3 is a linear approximation valid only for exponents in [-2985, 2936] (asserted). check_divisibility_and_divide_by_pow10<N> replaces n in place with floor(n/10^N) using a magic-number multiply and reports divisibility via the remainder-mask trick (asserts n <= 10^(N+1)); small_division_by_pow10<N> is the non-mutating floor division. divide_by_10_to_kappa_plus_1 computes floor(n/10^(kappa+1)) for float (32-bit) and double (64-bit) via multiply-shift.

<a id="u-14afd4ab79e9"></a>
### `format.h-dragonbox-multiply-helpers`

`inline auto umul128_upper64(uint64_t x, uint64_t y) noexcept -> uint64_t` · [include/fmt/format.h:L1678-L1687][f2]

umul128_upper64 returns the high 64 bits of a 64x64 product (native shift, __umulh, or umul128().high()); umul192_upper128 returns the upper 128 bits of a 64x128 product by summing umul128(x, y.high()) and the upper-64 of umul128(x, y.low()).

<a id="u-618884d8e871"></a>
### `format.h-uint128`

`class uint128` · [include/fmt/format.h:L287-L292][f2]

A minimal 128-bit unsigned integer used when native __int128 is unavailable, storing high/low 64-bit halves.

Comparison operators compare halves (operator> falls back to low half when high halves are equal); bitwise ops apply per half; operator~ complements both halves; explicit operator T truncates to the low half. operator+ delegates to operator+=. operator*(uint128,uint32_t) asserts the left high half is zero and computes a 96-bit product with carry into the high half. operator-(uint128,uint64_t) borrows from the high half when the low half is smaller. Shifts handle shift==64 exactly and shift>64 by recursion on the remaining amount; other shifts splice halves with (hi_<<(64-shift))|(lo_>>shift) and symmetrically for left shift. operator>>= reassigns via operator>>. operator+=(uint128) adds halves with carry out of the low half and asserts the high-half addition did not overflow (FMT_ASSERT(new_hi >= hi_)), i.e. it traps on 128-bit wraparound. operator&= ANDs halves. operator+=(uint64_t) is noexcept and asserts nothing: under constant evaluation it adds with a manual carry; otherwise it uses __builtin_addcll, __builtin_ia32_addcarryx_u64, or MSVC _addcarry_u64 when available, falling back to plain addition with carry propagation. Note the overflow assert belongs to the uint128 overload, not this one.

<a id="u-51c7265a0ebb"></a>
### `assert_fail`

`FMT_FUNC void assert_fail(const char* file, int line, const char* message)` · [include/fmt/format-inl.h:L49-L54][f1]

Prints an assertion failure message to stderr with unchecked fprintf and calls abort; used as the library-wide FMT_ASSERT failure handler.

Unchecked I/O avoids recursive assertion failures when stderr writes fail.

<a id="u-f82123e8ff09"></a>
### `get_cached_power`

`FMT_FUNC auto get_cached_power(int k) noexcept -> uint128` · [include/fmt/format-inl.h:L1158-L1160][f1]

Forwards to cache_accessor<double>::get_cached_power, giving non-dragonbox-internal callers access to the double pow10 cache.

<a id="u-674f825ec9f3"></a>
### `is_left_endpoint_integer_shorter_interval`

`template <typename T> auto is_left_endpoint_integer_shorter_interval(int exponent) no…` · [include/fmt/format-inl.h:L1163-L1169][f1]

Returns true only when the exponent is 2 or 3, identifying the shorter-interval cases whose left endpoint is an integer.

<a id="u-28ac98dc7fac"></a>
### `shorter_interval_case`

`template <typename T> FMT_INLINE auto shorter_interval_case(int exponent) noexcept ->…` · [include/fmt/format-inl.h:L1228-L1273][f1]

Dragonbox shortcut for the shorter-interval case (power-of-two significands).

Computes k and beta, fetches the cached power, and derives left/right endpoints; the left endpoint is incremented unless the exponent is 2 or 3. It first tries significand = zi/10 with exponent minus_k+1, accepting if significand*10 >= xi (then stripping trailing zeros); otherwise it uses the round-up value with exponent minus_k, and in the tie-threshold exponent range rounds to even, else increments if still below xi.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format-inl.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
