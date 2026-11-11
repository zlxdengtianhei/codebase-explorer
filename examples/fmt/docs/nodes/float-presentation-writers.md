# Float presentation writers

**Capability.** Renders floats per specs in fixed, exponential, or shortest form, choosing notation by exponent and handling signs and non-finite values.

The final float rendering layer lives here: do_write_float, write_float with specs, the fast no-specs IEC559 path, and fixed-notation writing. Readers debugging float output formatting should start here.

**Depends on.**

- [Value writing engine](value-writing-engine.md) · graph-only · 4 edge(s)
- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-only · 1 edge(s)
- [Printf implementation](printf-implementation.md) · graph-only · 1 edge(s)

Parent: [Float presentation rendering](float-presentation-rendering.md)

## Units (7)

<a id="u-15e4b84a2e0a"></a>
### `format.h-do-write-float-write-float`

`template <typename Char, typename Grouping, typename OutputIt, typename DecimalFP> FM…` · [include/fmt/format.h:L2824-L2863][f1]

do_write_float picks the decimal point (locale or '.'), computes the decimal exponent, and either delegates to write_fixed (fixed presentation, or default presentation when use_fixed holds with precision or exp_upper) or writes exponential form: one leading digit, a point (omitted when the significand is a single digit and alt is off), alt-requested trailing zeros, then 'e'/'E' and write_exponent; it pads when width is set, otherwise reserves and writes directly.

write_float selects the grouping policy: fallback_digit_grouping under constant evaluation or when locale is disabled, digit_grouping otherwise.

<a id="u-7b76b2da5b5e"></a>
### `format.h-exponent-writing`

`FMT_CONSTEXPR inline auto compute_exp_size(int exp) -> int` · [include/fmt/format.h:L1778-L1783][f1]

compute_exp_size returns the size of a signed exponent rendering (sign + 'e' + 2, 3, or 4 digits by magnitude).

write_exponent asserts the exponent is within (-10000,10000), writes '+' or '-', then at least two digits: under constant evaluation it zero-pads a single digit and uses format_decimal; at runtime it emits the hundreds (and thousands) digit via digits2 when present, then the final two digits.

<a id="u-742bd93f080e"></a>
### `format.h-notation-choice`

`template <typename T> FMT_CONSTEVAL auto exp_upper() -> int` · [include/fmt/format.h:L2733-L2737][f1]

exp_upper returns the largest exponent (relative to the first digit) for which fixed notation is used: min(16, digits10+1), or 16 when digits10 is 0.

use_fixed selects fixed notation when exp is in [-4, exp_upper).

<a id="u-5daad04cb911"></a>
### `abort_fuzzing_if`

`FMT_CONSTEXPR inline void abort_fuzzing_if(bool condition)` · [include/fmt/format.h:L234-L239][f1]

No-op unless FMT_FUZZ is defined, in which case it throws std::runtime_error when the condition holds; used to bound fuzzing workloads.

<a id="u-4a047e978d6a"></a>
### `FMT_BEGIN_EXPORT.size_padding.write`

`template <typename Char, typename OutputIt, typename T, FMT_ENABLE_IF(is_floating_poi…` · [include/fmt/format.h:L3713-L3783][f1]

Writes a floating-point value per specs: localized output is tried first; the sign comes from signbit (so NaN keeps its sign) or the spec sign; non-finite values go to write_nonfinite; numeric alignment emits the sign before padding and shrinks the width.

Default presentation with fast floats at runtime uses dragonbox::to_decimal for the shortest form. Hexfloat builds a 0x/0X prefix (moved before padding under numeric alignment) and pads. Exp/fixed presentations bump precision (exp checks INT_MAX and reports "number is too big"), set alt when precision is nonzero, and default precision 0 becomes 1; the digits come from format_float into a memory_buffer and are written via write_float as a big_decimal_fp.

<a id="u-f0a111434adf"></a>
### `include/fmt/format.h:FMT_BEGIN_EXPORT.size_padding.write`

`template <typename Char, typename OutputIt, typename T, FMT_ENABLE_IF(is_fast_float<T…` · [include/fmt/format.h:L3785-L3849][f1]

Fast no-specs write for IEC559 float/double: non-finite values (full exponent mask) go to write_nonfinite; otherwise dragonbox::to_decimal gives the shortest digits, written in fixed notation when use_fixed holds, else in exponential form — via a raw pointer when the output supports it (writing sign, digits with '.' after the first, e+/e- and two-or-three exponent digits), else through reserve and write_significand/write_exponent.

<a id="u-b5f06841c2d6"></a>
### `FMT_BEGIN_EXPORT.size_padding.write_fixed`

`template <typename Char, typename Grouping, typename OutputIt, typename DecimalFP> FM…` · [include/fmt/format.h:L2759-L2822][f1]

Writes a decimal floating-point value in fixed notation, branching on the exponent: non-negative exponent writes the significand then trailing zeros (count from precision, or precision minus exp when not fixed), with an alt '.' plus zeros when requested; a small negative exponent with exp>0 writes integral digits, a decimal point, then fraction digits and trailing zeros; otherwise it writes '0.', num_zeros zeros (clamped to precision when the significand is empty), then the significand.

Sizes include the sign, separators (via the Grouping policy), point and zeros, and output is right-padded. A fuzzing guard aborts above 5000 zeros.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
