# Bigint fallback algorithm

**Capability.** Implements the (FPP)^2 arbitrary-precision fallback for exact float formatting using a bigit-based bigint and boundary computation.

When the fast Dragonbox path cannot handle a case, this module computes exact decimal output with a base-2^32 bigint and the classic dragon algorithm. It is only reached from the float conversion layer.

**Depends on.**

- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-confirmed · 9 edge(s) · The bigint fallback uses the numeric core's arithmetic helpers and assertion handler for exact float formatting.
- [Binary and float primitives](binary-and-float-primitives.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Float conversion entry points](float-conversion-entry-points.md) · graph-confirmed · 1 edge(s)

Parent: [Float to decimal conversion](float-to-decimal-conversion.md)

## Units (3)

<a id="u-a27bd695403b"></a>
### `format.h-bigint`

`class bigint` · [include/fmt/format.h:L2925-L2930][f1]

An arbitrary-precision integer as base-2^32 bigits with a shared exponent exp_ (value = bigits * 32^exp_), stored in a memory_buffer; non-copyable.

Core operations: get_bigit returns a bigit or 0 outside the stored range; subtract_bigits subtracts with borrow; remove_leading_zeros trims high zero bigits; subtract_aligned subtracts an aligned smaller-or-equal operand (asserting alignment and ordering, and final zero borrow) then trims. multiply(uint32_t) is a carry loop; the 64/128-bit multiply splits the multiplier into halves and propagates carry, pushing bigits while carry remains. assign stores an integer's 32-bit chunks. operator= from Int asserts positivity and assigns. operator<<= adds whole-bigit shifts to exp_ and shifts remaining bits with carry. operator*= asserts a positive multiplier and dispatches by width. compare orders by bigit count then bigits; add_compare returns compare(lhs1+lhs2, rhs) using a borrow-based scan with early -1/1 exits. assign_pow10 computes 5^exp by repeated squaring (with conditional *5 per bit) then shifts by exp. square computes the full cross-product square via two half loops with a running uint128 carry, doubling exp_. align pads a larger-exponent bigint with low zero bigits so exponents match. divmod_assert-style divmod_assign aligns to the divisor, then repeatedly subtracts while counting, returning the quotient and leaving the remainder; it returns 0 without work when the value is already smaller.

<a id="u-95334ca55893"></a>
### `FMT_BEGIN_EXPORT.size_padding.adjust_precision`

`inline FMT_CONSTEXPR20 void adjust_precision(int& precision, int exp10)` · [include/fmt/format.h:L2917-L2923][f1]

Adjusts fixed-notation precision by a decimal exponent, throwing format_error("number is too big") when the addition would overflow int.

<a id="u-3321a7773df0"></a>
### `FMT_BEGIN_EXPORT.size_padding.format_dragon`

`FMT_CONSTEXPR20 inline void format_dragon(basic_fp<uint128_t> value, unsigned flags, …` · [include/fmt/format.h:L3175-L3307][f1]

Implements the (FPP)^2 dragon algorithm: builds numerator/denominator and lower/upper boundary bigints from the binary value (shifting by one extra bit, two when the predecessor is closer), scaling by pow(10, exp10) in whichever direction avoids negative exponents.

With the fixup flag it may decrement exp10 and scale numerator (and boundaries in shortest mode) when rounding demands; with fixed it adjusts precision by the exponent. Shortest mode loops dividing by the denominator, emitting digits and stopping when the value is within the lower or upper boundary, rounding up on high-only, and half-to-even when both. Fixed-digit mode emits num_digits-1 digits then rounds the last by half-to-even, propagating a 9-overflow carry (rewriting to '1' and bumping exp10, or appending '0' in fixed mode). exp10 is updated to be relative to the first digit.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
