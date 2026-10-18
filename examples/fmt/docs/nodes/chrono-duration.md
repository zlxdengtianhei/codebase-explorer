# Duration Formatting

**Capability.** Safe duration casts and value/unit output: overflow-checked integral and float-rep casts, fractional-second writing, SI unit names, and the duration formatter plus its callback handler.

Use for anything std::chrono::duration. The formatter parses specs via chrono-parse, then duration_formatter walks callbacks emitting sign, components, and unit suffix.

**Depends on.**

- [Chrono Spec Parsing](chrono-parse.md) · model-inferred · 0 edge(s)
- [Error Reporting](core-errors.md) · graph-only · 2 edge(s)

**Depended on by.**

- [std::tm Formatting](chrono-tm.md) · model-inferred · 0 edge(s)

Parent: [Chrono Formatting](chrono-h.md)

## Units (12)

<a id="u-404dbc12e204"></a>
### `chrono-safe-duration-cast`

`template <typename To, typename From, FMT_ENABLE_IF(!std::is_same<From, To>::value &&…` · [include/fmt/chrono.h:L42-L66][f1]

Converts std::chrono durations and scalars without overflow or undefined behavior, reporting failure via an int error code.

lossless_integral_conversion has three overloads selected by signedness: same-signedness only range-checks when the target is narrower (sets ec=1 and returns a default value on failure); mixed-signedness rejects negative sources when converting to unsigned and range-checks against the target maximum; the same-type overload just returns the value. safe_float_conversion preserves NaN and infinities; finite values outside the target range set ec=1. The floating-point safe_duration_cast multiplies the count by the ratio factor using a common intermediate type, checking both multiplication bounds before scaling, dividing by den, and converting back; any ec set at either float conversion aborts with an empty result.

uses: [max_value][f2], [chrono-duration-helpers](chrono-duration.md#u-5c7fa6c5abe2)

**Uncertainties.**

- The final comment questions whether the den division can fail; no check is performed there, so precision loss in that divide is unverified.

<a id="u-5c7fa6c5abe2"></a>
### `chrono-duration-helpers`

`template <typename T, FMT_ENABLE_IF(std::is_integral<T>::value&& has_isfinite<T>::val…` · [include/fmt/chrono.h:L1538-L1542][f1]

Small helpers used by duration formatting.

isfinite returns true unconditionally for integral types with an isfinite trait (so the name is callable generically). mod is x % y for integral reps and std::fmod for floating reps, giving consistent remainder behavior across rep kinds. make_unsigned_or_unchanged maps integral types to their unsigned counterpart but leaves floating types alone (unlike std::make_unsigned, which is UB on non-integrals). get_milliseconds, for integral reps, extracts the sub-second millisecond component by casting through a common seconds type and taking the difference; the code notes this may overflow, and with safe casts disabled it simply subtracts whole seconds and casts.

calls: [duration_cast](chrono-duration.md#u-14f9ff77d424)

<a id="u-9887111680d7"></a>
### `chrono-duration-value-unit`

`template <typename Char, typename Rep, typename OutputIt, FMT_ENABLE_IF(std::is_integ…` · [include/fmt/chrono.h:L1585-L1589][f1]

Formats the value and unit parts of a duration.

format_duration_value writes an integral rep plainly, and a floating rep with the given precision using fixed formatting when precision >= 0 and general otherwise. copy_unit copies the unit string; the wchar_t overload first converts UTF-8 to UTF-16 via utf8_to_utf16 (relying on unit characters being common to UTF-16/UTF-32). format_duration_unit looks up the period in get_units; on a hit it copies the unit string, otherwise it writes a synthesized '[num/den]s' (omitting '/den' when den is 1).

calls: [get_units](chrono-duration.md#u-99aa377742f5); uses: [utf8_to_utf16.c_str][f2]

<a id="u-f2843de1ea59"></a>
### `chrono-fractional-digit-count`

`constexpr auto pow10(std::uint32_t n) -> long long` · [include/fmt/chrono.h:L983-L985][f1]

Compile-time computation of how many fractional decimal digits a duration period needs.

pow10 is a constexpr 10^n helper. count_fractional_digits recurses multiplying Num by 10 until Num % Den == 0, counting steps; it is capped at 18 iterations (and guarded against long long overflow in the recursion condition), with the disabled base case returning 6 (microseconds) when exactness is not reached, matching the C++20 precision rule.

<a id="u-14f9ff77d424"></a>
### `duration_cast`

`template <typename To, typename FromRep, typename FromPeriod, FMT_ENABLE_IF(std::is_i…` · [include/fmt/chrono.h:L462-L492][f1]

Casts one integral-rep duration to another with overflow checking, throwing format_error instead of overflowing.

With FMT_SAFE_DURATION_CAST disabled it simply forwards to std::chrono::duration_cast. Otherwise it computes the ratio factor, widens the count to a common type, and multiplies by factor::num after checking the count against max/num and, for signed common types, min/num — either violation throws via throw_duration_error; division by factor::den then truncates. The final value goes through safe_duration_cast::lossless_integral_conversion, and a nonzero ec again throws.

**Notes.**

- failure: Every overflow path raises format_error("cannot format duration"); nothing is clamped.

calls: [chrono-safe-duration-cast](chrono-duration.md#u-404dbc12e204); uses: [include/fmt/chrono.h:duration_cast](chrono-duration.md#u-94a99758588e)

<a id="u-94a99758588e"></a>
### `include/fmt/chrono.h:duration_cast`

`template <typename To, typename FromRep, typename FromPeriod, FMT_ENABLE_IF(std::is_f…` · [include/fmt/chrono.h:L494-L511][f1]

Casts between floating-point-rep durations, preserving NaN and infinity.

With safe casts enabled it first checks isfinite: non-finite counts are static_cast directly so infinities and NaNs pass through unchanged. Finite values go through safe_duration_cast::safe_duration_cast, which scales by the period ratio with bound checks; a nonzero ec throws format_error("cannot format duration"). With safe casts disabled it delegates to std::chrono::duration_cast, which may overflow silently.

calls: [chrono-safe-duration-cast](chrono-duration.md#u-404dbc12e204)

<a id="u-99aa377742f5"></a>
### `get_units`

`template <typename Period> FMT_CONSTEXPR inline auto get_units() -> const char*` · [include/fmt/chrono.h:L615-L639][f1]

Maps a duration period type to its SI-suffixed unit string via a constexpr type-comparison chain: attoseconds through exaseconds, plus minutes ('min'), hours ('h') and days ('d').

For std::micro it returns "µs" when UTF-8 output is enabled and "us" otherwise. Unrecognized periods return nullptr, which callers interpret as an unnamed ratio to format as [num/den]s.

uses: [chrono-duration-value-unit](chrono-duration.md#u-9887111680d7)

<a id="u-f86f5d056849"></a>
### `to_nonnegative_int`

`template <typename T, typename Int, FMT_ENABLE_IF(std::is_integral<T>::value)> inline…` · [include/fmt/chrono.h:L968-L975][f1]

Converts a value to Int while enforcing that it lies in [0, upper).

For integral T, a negative value or one whose unsigned magnitude exceeds upper throws format_error("chrono value is out of range"); the check is skipped for unsigned Int. The floating-point T overload throws format_error("invalid value") when value < 0 or value >= upper+1. Both return static_cast<Int>(value).

<a id="u-bf21ca318716"></a>
### `write_floating_seconds`

`template <typename Duration> void write_floating_seconds(memory_buffer& buf, Duration…` · [include/fmt/chrono.h:L1057-L1081][f1]

Formats the seconds component (mod 60) of a floating-point-rep duration into a memory_buffer.

It asserts the rep is floating point. When num_fractional_digits is negative it derives the count from the period but widens it to 6 if the value is not exactly representable with fewer digits (checked via round). It then formats std::fmod(val * num / den, 60) with a fixed-precision '{:.{}f}' spec via format_to. Unlike write_fractional_seconds this always emits the seconds value including any leading '0', which callers strip or pad as needed.

uses: [write_fractional_seconds](chrono-duration.md#u-53f08030e85d)

<a id="u-53f08030e85d"></a>
### `write_fractional_seconds`

`template <typename Char, typename OutputIt, typename Duration> void write_fractional_…` · [include/fmt/chrono.h:L1006-L1052][f1]

Writes the sub-second part of an integer-rep duration to out, e.g. '.123456'.

It computes the period's fractional digit count (capped at 18, else 6), takes fractional = d minus whole seconds, and converts it to a subsecond duration — for floating-point reps it uses the raw count, otherwise the checked duration_cast (which can throw format_error on overflow). With the default precision (-1) it asserts the rep is not floating point and writes '.', leading zeros and digits only when the subsecond period is finer than a second. With precision > 0 it always writes '.', truncates digits to the precision (dividing n and discarding the value only if the truncated result is 0), and pads with trailing zeros; precision == 0 writes nothing. FMT_ASSERT guards are compiled per project settings; violation is a failed assertion rather than format_error.

**Notes.**

- failure: A negative default precision with a floating-point rep trips FMT_ASSERT, an abort-style failure distinct from format_error.

uses: [chrono-fractional-digit-count](chrono-duration.md#u-f2843de1ea59); calls: [duration_cast](chrono-duration.md#u-14f9ff77d424)

<a id="u-d56f682dce38"></a>
### `duration_formatter`

`template <typename Char, typename Rep, typename Period> struct duration_formatter` · [include/fmt/chrono.h:L1629-L1648][f1]

Implements duration chrono-format callbacks over an unsigned rep derived from the duration's rep (small integral reps widen to unsigned int) so negative durations are handled by a pending sign rather than unsigned wraparound; the constructor negates the count when negative and precomputes whole seconds via the checked detail::duration_cast.

handle_nan_inf short-circuits every callback: non-finite values are written as 'nan', 'inf' or '-inf' and the callback returns. Component accessors compute days/hours/minutes/seconds by division and mod on the seconds count; time() assembles a std::tm validated by to_nonnegative_int, which throws format_error for impossible components. write() emits a sign, handles NaN, and pads/formats a decimal value; format_tm() routes a field through tm_writer for locale/alternative-numeric handling, but writes 'nan' when the total value is NaN. Time callbacks honor numeric_system: standard output uses the fast path, alternative output builds a tm and delegates. on_second for standard numeric formatting writes floating reps via write_floating_seconds (sign then padding when the buffer starts with '0' or '.') and integral reps via write plus write_fractional_seconds, both honoring the stored precision; precision 0 suppresses the fractional part. All date-like callbacks are empty no-ops since durations carry no calendar data; on_24_hour_time writes its own ':' even when handle_nan_inf already emitted 'inf', producing doubled separators on the second call — on_iso_time avoids this by checking handle_nan_inf after the colon. on_duration_value writes the signed value with precision; on_duration_unit writes the unit.

**Notes.**

- failure: Impossible components (negative or over the field bound) raise format_error via to_nonnegative_int; the constructor's seconds cast can also throw format_error on overflow.

uses: [tm_writer](chrono-tm.md#u-39b546d6bcc2); calls: [write_floating_seconds](chrono-duration.md#u-bf21ca318716), [write_fractional_seconds](chrono-duration.md#u-53f08030e85d), [chrono-duration-value-unit](chrono-duration.md#u-9887111680d7), [to_nonnegative_int](chrono-duration.md#u-f86f5d056849), [duration_cast](chrono-duration.md#u-14f9ff77d424)

<a id="u-c5102e7b6118"></a>
### `formatter<std::chrono::duration<Rep, Period>, Char>`

`template <typename Rep, typename Period, typename Char> struct formatter<std::chrono:…` · [include/fmt/chrono.h:L2049-L2058][f1]

Formats any std::chrono::duration from a chrono format spec.

parse parses alignment, an optional (possibly dynamic) width, then an optional precision — setting checker.has_precision_integral when a precision appears with a non-floating rep, so chrono_format_checker later throws for it — then 'L' for localized output, and finally parse_chrono_format with the checker, storing the consumed chrono spec. format renders into a temporary buffer: it resolves dynamic width/precision from format arguments; if the chrono spec is empty it writes the plain value plus unit, otherwise it drives duration_formatter over the spec with the resolved precision and localized flag; finally it writes the buffered text with alignment/width through the generic write. Note precision is applied to value output and seconds fractions but is cleared on the outer specs so it does not re-truncate the buffered string.

uses: [chrono_format_checker](chrono-parse.md#u-0d3f26ea6de0), [duration_formatter](chrono-duration.md#u-d56f682dce38); calls: [parse_chrono_format](chrono-parse.md#u-953b80d7c4a3)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/chrono.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h