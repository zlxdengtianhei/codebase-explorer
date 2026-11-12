# Chrono Duration and Time Formatting

**Capability.** Formats and parses chrono durations and time points, converting clocks, units, fractional seconds, and UTC/local times.

Use this module for chrono duration and time-point formatting. The units describe duration parsing, clock conversion, UTC/local formatting, and fractional seconds.

**Depends on.**

- [Dragonbox Cache and Assertions](dragonbox-cache-and-assertions.md) · graph-only · 2 edge(s)
- [Format Core Utilities](format-core-utilities.md) · graph-only · 1 edge(s)

Parent: [Chrono Formatting Support](chrono-formatting-support.md)

## Units (27)

<a id="u-ea00c0ae964b"></a>
### `chrono.h-chrono-availability-aliases`

`using utc_clock = std::chrono::utc_clock;` · [include/fmt/chrono.h:L235-L235][f1]

Selects standard chrono UTC/local clock types when the library feature macro is available, otherwise supplies fallback shims: a UTC clock with a to_sys template and an empty local-time tag.

The public time-point aliases bind system_clock, the selected UTC clock, and the selected local tag to a duration.

<a id="u-f5964269cf42"></a>
### `chrono.h-duration-cast-with-overflow-checks`

`FMT_NORETURN inline void throw_duration_error()` · [include/fmt/chrono.h:L457-L459][f1]

Casts durations between representations, throwing a format error when a checked conversion cannot be represented.

The integral overload uses the standard cast when safe casting is disabled; otherwise it applies the ratio factor with overflow checks, divides by the denominator, and uses lossless integral conversion, throwing on any error. The floating overload preserves non-finite counts directly when safe casting is enabled, otherwise uses the floating safe cast and throws on error; with safe casting disabled it uses the standard cast. The mixed integral/floating overload always uses the standard duration cast.

<a id="u-4421ea08eadf"></a>
### `chrono.h-duration-formatter-specialization`

`template <typename Rep, typename Period, typename Char> struct formatter<std::chrono:…` · [include/fmt/chrono.h:L2049-L2058][f1]

Parses and formats std::chrono::duration values.

Parsing handles alignment, width, precision, the localized flag, and chrono format specifiers; precision marks the checker as integral when the representation is not floating. Formatting copies the specs, resets the precision used for the final write, handles dynamic width and precision, and either writes the count plus unit when no chrono spec is present or constructs a duration formatter, sets precision/localized state, parses the stored format, and writes the resulting buffer with the original specs. Precision is rejected only when the duration-value specifier is parsed and the representation is integral.

<a id="u-ecd14fc48812"></a>
### `chrono.h-duration-unit-copying`

`template <typename Char, typename OutputIt> auto copy_unit(string_view unit, OutputIt…` · [include/fmt/chrono.h:L1601-L1604][f1]

Copies a unit string to the output.

The wchar_t overload converts the UTF-8 unit through a UTF-16 helper before copying; the generic overload copies characters directly.

<a id="u-4ca88a9c4ed3"></a>
### `chrono.h-duration-value-formatting`

`template <typename Char, typename Rep, typename OutputIt, FMT_ENABLE_IF(std::is_integ…` · [include/fmt/chrono.h:L1585-L1589][f1]

Writes a duration count.

Integral representations are written directly. Floating representations use a format specification with the requested precision and fixed presentation when precision is nonnegative, otherwise general presentation.

<a id="u-eaff2ac5efa0"></a>
### `chrono.h-finite-and-modulo-helpers`

`template <typename T, FMT_ENABLE_IF(std::is_integral<T>::value&& has_isfinite<T>::val…` · [include/fmt/chrono.h:L1538-L1542][f1]

Reports integral values as finite when the finite trait is available.

Modulo uses the remainder operator for integral types and fmod for floating-point types.

<a id="u-adff2bd857ea"></a>
### `chrono.h-floating-safe-duration-cast`

`template <typename To, typename FromRep, typename FromPeriod, FMT_ENABLE_IF(std::is_f…` · [include/fmt/chrono.h:L157-L167][f1]

Casts a floating-point duration to another floating-point duration using a ratio factor and an intermediate common representation.

It first safely converts the source count, then checks multiplication by the numerator against the intermediate max/min, multiplies, divides by the denominator, and safely converts to the target representation. Any failed check sets the error code and returns a value-initialized target; successful conversion returns the target duration. Static assertions require positive numerator and denominator.

<a id="u-96b962893de5"></a>
### `chrono.h-fractional-digit-count`

`template <long long Num, long long Den, int N = 0, bool Enabled = (N < 19) && (Num <=…` · [include/fmt/chrono.h:L990-L995][f1]

Counts decimal fractional digits for a ratio, up to 18 digits.

It stops early when the numerator becomes divisible by the denominator. If the recursion limit or overflow guard is reached before exact termination, the base case returns 6 unless the current numerator is already divisible.

<a id="u-3a6e044f198b"></a>
### `chrono.h-gmtime-dispatch-and-overloads`

`FMT_BEGIN_EXPORT /** * Converts given time since epoch as std::time_t value into ca…` · [include/fmt/chrono.h:L533-L541][f1]

Converts a time_t to UTC std::tm using a dispatcher that prefers the reentrant gmtime_r.

If gmtime_r is unavailable (null marker), it tries gmtime_s; if gmtime_s is unavailable, the non-MSVC fallback uses std::gmtime. A null pointer from gmtime_r or a nonzero gmtime_s result is a failure, not a fall-through. Failure throws a format error for an out-of-range time_t. The sys_time overload converts through to_time_t first.

<a id="u-147aca04640e"></a>
### `chrono.h-gmtime-fallbacks-and-format-buffer`

`inline auto gmtime_r(...) -> null<>` · [include/fmt/chrono.h:L274-L274][f1]

Provides unavailable gmtime overloads that return a null marker, plus a stream-buffer adapter that appends written characters into a fmt buffer.

The adapter keeps its put area empty: overflow appends a non-EOF character and returns it, while xsputn appends the whole range and returns the count.

<a id="u-39d8b8a377e8"></a>
### `chrono.h-local-time-formatter`

`template <typename Duration, typename Char> struct formatter<local_time<Duration>, Ch…` · [include/fmt/chrono.h:L2225-L2228][f1]

Formats a local time point without timezone conversion.

Parsing uses the tm parser with timezone disallowed. Formatting casts the time since epoch to seconds, converts those seconds with gmtime, and for a one-second non-floating period delegates to the tm formatter. Otherwise it computes subseconds and delegates to the tm formatter with subseconds.

<a id="u-5b5806096c18"></a>
### `chrono.h-lossless-integral-conversion`

`template <typename To, typename From, FMT_ENABLE_IF(!std::is_same<From, To>::value &&…` · [include/fmt/chrono.h:L42-L66][f1]

Converts an integral value to another integral type and reports loss in an error code.

Same-type conversion clears the code and returns the input. Same-signedness conversion skips a dynamic check when the source has no more digits than the target; otherwise it checks the target min/max and sets the code on failure. Mixed-signedness conversion rejects negative source values when the target is unsigned, rejects values above the target maximum when digit counts require it, and otherwise casts. On failure it returns a value-initialized result with the error code set.

<a id="u-39824673cacc"></a>
### `chrono.h-nonnegative-integer-conversion`

`template <typename T, typename Int, FMT_ENABLE_IF(std::is_integral<T>::value)> inline…` · [include/fmt/chrono.h:L968-L975][f1]

Converts a value to an integer and throws a format error when it is outside the accepted range.

The integral overload checks only when the target integer type is signed: it rejects negative values and values whose unsigned form exceeds the unsigned upper bound, so it rejects values greater than upper but not equal to upper. The non-integral overload rejects negative values and values at or above upper+1, so it allows values below upper+1.

<a id="u-456e7592e3e4"></a>
### `chrono.h-padding-writers`

`template <typename OutputIt> auto write_padding(OutputIt out, pad_type pad, int width…` · [include/fmt/chrono.h:L657-L661][f1]

Writes padding for numeric fields.

The width overload returns immediately for no padding, otherwise fills the requested width with spaces for space padding or zeros for zero padding. The single-character overload writes one space or zero unless padding is disabled.

<a id="u-183878736d48"></a>
### `chrono.h-safe-floating-conversion`

`template <typename To, typename From, FMT_ENABLE_IF(!std::is_same<From, To>::value)> …` · [include/fmt/chrono.h:L126-L146][f1]

Converts between floating-point types while preserving non-finite values.

For different types, finite values inside the target lowest/max range are cast; finite values outside that range set the error code and return a value-initialized result. NaN and infinity are cast through unchanged. Same-type conversion clears the code and returns the input.

<a id="u-130c847c5567"></a>
### `chrono.h-sys-time-formatter`

`template <typename Char, typename Duration> struct formatter<sys_time<Duration>, Char…` · [include/fmt/chrono.h:L2180-L2182][f1]

Formats a system time point as UTC.

Parsing uses the tm parser with timezone allowed. Formatting converts to tm via gmtime. For a one-second period with non-floating representation it sets the UTC zone and delegates to the tm formatter. Otherwise it computes subseconds; if negative, it borrows one second, decrementing tm_sec when possible or recomputing gmtime one second earlier, then adds the borrowed second back before delegating to the tm formatter with subseconds.

<a id="u-198fcf604dc1"></a>
### `chrono.h-unsigned-or-unchanged-mapping`

`template <typename T, bool INTEGRAL = std::is_integral<T>::value> struct make_unsigne…` · [include/fmt/chrono.h:L1555-L1558][f1]

Maps integral types to their unsigned counterpart and leaves non-integral types unchanged.

<a id="u-4a9e51802f91"></a>
### `chrono.h-utc-time-formatter`

`template <typename Duration, typename Char> struct formatter<utc_time<Duration>, Char…` · [include/fmt/chrono.h:L2214-L2217][f1]

Formats a UTC time point by converting it to the system clock through the UTC clock and delegating to the system-time formatter.

<a id="u-b5bcfaa11428"></a>
### `format_duration_unit`

`template <typename Char, typename Period, typename OutputIt> auto format_duration_uni…` · [include/fmt/chrono.h:L1614-L1627][f1]

Writes a duration unit.

Known periods use their mapped abbreviation; unknown periods write bracketed numerator, optional slash and denominator when the denominator is not one, then an 's'.

<a id="u-d90c6850d4ba"></a>
### `get_milliseconds`

`template <typename Rep, typename Period, FMT_ENABLE_IF(std::is_integral<Rep>::value)>…` · [include/fmt/chrono.h:L1564-L1583][f1]

Converts an integral duration to milliseconds.

With safe casting enabled it casts to a common seconds type, subtracts whole seconds, and casts the remainder to milliseconds; otherwise it subtracts whole seconds and casts the difference to milliseconds. The source notes possible overflow or target-type mismatch.

<a id="u-99aa377742f5"></a>
### `get_units`

`template <typename Period> FMT_CONSTEXPR inline auto get_units() -> const char*` · [include/fmt/chrono.h:L615-L639][f1]

Maps a duration period to its unit string.

Known SI and common time periods return fixed abbreviations; micro returns a UTF-8 micro sign when UTF-8 is active, otherwise "us". Unknown periods return null.

<a id="u-953b80d7c4a3"></a>
### `parse_chrono_format`

`template <typename Char, typename Handler> FMT_CONSTEXPR auto parse_chrono_format(con…` · [include/fmt/chrono.h:L670-L813][f1]

Parses a put_time-like chrono format string and dispatches each conversion to a handler.

Empty input or an immediate closing brace returns the start. A first character other than '%' throws an invalid-format error. Text runs are reported through on_text. After '%', an optional '_' selects space padding and '-' selects no padding; then the conversion character is dispatched. Truncated or unknown conversions throw invalid-format errors. The E and O prefixes select alternative numeric-system callbacks, with unsupported combinations throwing. The returned pointer stops at the closing brace or end.

<a id="u-e4c802b1a3ae"></a>
### `pow10`

`constexpr auto pow10(std::uint32_t n) -> long long` · [include/fmt/chrono.h:L983-L985][f1]

Computes 10 raised to a compile-time unsigned exponent recursively, returning 1 for exponent zero.

<a id="u-c16032e32644"></a>
### `to_time_t`

`template <typename Duration> auto to_time_t(sys_time<Duration> time_point) -> std::ti…` · [include/fmt/chrono.h:L521-L529][f1]

Converts a system time point to std::time_t by casting its duration to a time_t duration and returning the count, avoiding an intermediate system_clock time-point cast that could overflow.

<a id="u-9f749ddcbd46"></a>
### `write_digit2_separated`

`inline void write_digit2_separated(char* buf, unsigned a, unsigned b, unsigned c, cha…` · [include/fmt/chrono.h:L585-L613][f1]

Writes three two-digit decimal values separated by a separator into exactly eight bytes.

It uses a BCD-style arithmetic transform, inserts ASCII digits and separators, and reverses the byte order on big-endian targets.

<a id="u-bf21ca318716"></a>
### `write_floating_seconds`

`template <typename Duration> void write_floating_seconds(memory_buffer& buf, Duration…` · [include/fmt/chrono.h:L1057-L1081][f1]

Writes fractional seconds for a floating-point duration.

It asserts a floating representation, derives the digit count from the period when not supplied, raises the count to 6 when the value is not integral at the lower precision, and formats the value modulo 60 with fixed notation into a buffer.

<a id="u-53f08030e85d"></a>
### `write_fractional_seconds`

`template <typename Char, typename OutputIt, typename Duration> void write_fractional_…` · [include/fmt/chrono.h:L1006-L1052][f1]

Writes fractional seconds for an integral duration.

It derives the subsecond precision from the period, subtracts whole seconds, converts the remainder to that precision, and formats digits with leading zeros. With negative precision it asserts the representation is not floating and writes a decimal point only when the subsecond period is below seconds. With positive precision it writes a decimal point, limits leading zeros to the requested precision, truncates digits when the precision is shorter than the available digits, and pads remaining zeros. Zero precision writes nothing.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/chrono.h
