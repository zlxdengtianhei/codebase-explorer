# Chrono formatting internals

**Capability.** Low-level chrono machinery: duration/tm spec parsing, checked conversions, time-point conversion, and numeric field writing helpers.

Come here for the detail-level building blocks that parse chrono format specs and render durations and time points. It contains spec parsing, checked casts, tm field accessors, and digit-writing primitives.

**Depends on.**

- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-only · 9 edge(s)
- [Binary and float primitives](binary-and-float-primitives.md) · graph-only · 3 edge(s)

Parent: [Chrono and time formatting](chrono-and-time-formatting.md)

## Units (29)

<a id="u-94bf379fbfb2"></a>
### `chrono.h-count-fractional-digits`

`template <long long Num, long long Den, int N = 0, bool Enabled = (N < 19) && (Num <=…` · [include/fmt/chrono.h:L990-L995][f1]

Compile-time computation of fractional digits needed for a period num/den in [0,18], per the C++20 spec: it multiplies num by 10 while divisible remainders persist; the terminating base case returns 6 (microsecond precision) when 19 digits would be needed or num would overflow.

<a id="u-ffb206b7839e"></a>
### `chrono.h-duration-formatter`

`template <typename Rep, typename Period, typename Char> struct formatter<std::chrono:…` · [include/fmt/chrono.h:L2049-L2058][f1]

Parses and applies chrono format specs to std::chrono::duration values.

parse handles optional alignment, static or dynamic width, optional precision (recording integral rep via the checker so %Q with precision throws), an 'L' localized flag, then validates the chrono spec body with chrono_format_checker and stores it. format resolves dynamic width/precision; with an empty spec it writes the count via format_duration_value followed by the unit suffix, otherwise it drives a duration_formatter through parse_chrono_format into a memory buffer, finally writing the buffer with the collected specs (width/alignment applied by detail::write).

<a id="u-843936aa2f16"></a>
### `chrono.h-format-duration-value`

`template <typename Char, typename Rep, typename OutputIt, FMT_ENABLE_IF(std::is_integ…` · [include/fmt/chrono.h:L1585-L1589][f1]

Writes a duration count: integral reps go through plain write; floating reps build format_specs with the given precision, choosing fixed presentation when precision ≥ 0 and general otherwise.

<a id="u-08634cb4cf99"></a>
### `chrono.h-formatbuf`

`class formatbuf : public StreamBuf` · [include/fmt/chrono.h:L279-L289][f1]

A streambuf adapter that forwards stream output into a fmt buffer, used to route std::time_put facets into fmt's memory.

The put area is intentionally always empty, so every character goes through overflow, which appends to the buffer unless the character is EOF; xsputn appends the whole range and returns count, keeping streambuf and buffer in sync at the cost of a virtual call per character.

<a id="u-6522cf8c6f29"></a>
### `chrono.h-gmtime`

`FMT_BEGIN_EXPORT /** * Converts given time since epoch as std::time_t value into ca…` · [include/fmt/chrono.h:L533-L541][f1]

Converts a time_t (or sys_time, via to_time_t) to a UTC std::tm, thread-safely where possible.

The dispatcher first tries the platform gmtime_r; if that symbol is unavailable (the variadic null-returning stubs), it tries gmtime_s, and on non-MSVC falls back to std::gmtime with a copy of the result. If every attempt fails (e.g. out-of-range time_t) it throws format_error("time_t value out of range"); on success it returns the filled tm by value.

<a id="u-39d8b8a377e8"></a>
### `chrono.h-local-time-formatter`

`template <typename Duration, typename Char> struct formatter<local_time<Duration>, Ch…` · [include/fmt/chrono.h:L2225-L2228][f1]

Formats local_time, whose time zone is unspecified, by using gmtime on the whole seconds since epoch to avoid any zone conversion.

parse defers to the tm formatter with timezone support disabled (so %z/%Z throw). For whole-second integral reps it uses the plain tm format; otherwise it computes subseconds as the remainder and formats via do_format with them.

<a id="u-5b5806096c18"></a>
### `chrono.h-lossless-integral-conversion`

`template <typename To, typename From, FMT_ENABLE_IF(!std::is_same<From, To>::value &&…` · [include/fmt/chrono.h:L42-L66][f1]

Converts an integral value to a possibly different integral type, reporting failure via an output error code instead of UB.

Three overloads: same-type returns the value with ec=0; same-signedness checks statically whether From's digit count fits To and otherwise dynamically rejects values outside [To::min, To::max] with ec=1 and a default-constructed result; mixed-signedness rejects negative-to-unsigned via detail::is_negative, and rejects values above To's max when the source has more (or equal, for unsigned→signed) digits. All are constexpr and usable at compile time.

<a id="u-59e1128400a8"></a>
### `chrono.h-make-unsigned-or-unchanged`

`template <typename T, bool INTEGRAL = std::is_integral<T>::value> struct make_unsigne…` · [include/fmt/chrono.h:L1555-L1558][f1]

Maps integral types to their unsigned counterpart while leaving floating and other types unchanged, used to make duration counts unsigned for arithmetic.

<a id="u-a138dab39b5d"></a>
### `chrono.h-mod`

`template <typename T, FMT_ENABLE_IF(std::is_integral<T>::value)> inline auto mod(T x,…` · [include/fmt/chrono.h:L1544-L1547][f1]

Modulo helper: integral reps use %, floating reps use std::fmod, both against an int y.

<a id="u-ba913c93453f"></a>
### `chrono.h-safe-duration-cast-floating`

`template <typename To, typename FromRep, typename FromPeriod, FMT_ENABLE_IF(std::is_f…` · [include/fmt/chrono.h:L157-L167][f1]

Casts a floating-point duration to another floating-point duration type without overflow/underflow, reporting failure via ec.

It converts from.count() to a common intermediate type via safe_float_conversion, multiplies by the ratio Factor::num after checking against max/lowest divided by that factor (ec=1, returns {} on violation), divides by Factor::den, then converts to To::rep via safe_float_conversion again, propagating any error. Static asserts require positive num and den.

<a id="u-73eec59f34ab"></a>
### `chrono.h-safe-float-conversion`

`template <typename To, typename From, FMT_ENABLE_IF(!std::is_same<From, To>::value)> …` · [include/fmt/chrono.h:L126-L146][f1]

Converts between floating-point types with range checking.

For finite input within [To::lowest, To::max] it returns the static_cast (possibly lossy in precision); finite input outside that range sets ec=1 and returns {}. NaN and infinities are passed through unchanged. The same-type overload is a trivial pass-through with ec=0.

<a id="u-130c847c5567"></a>
### `chrono.h-sys-time-formatter`

`template <typename Char, typename Duration> struct formatter<sys_time<Duration>, Char…` · [include/fmt/chrono.h:L2180-L2182][f1]

Formats system-clock time points as UTC.

parse defers to the tm formatter with timezone support enabled. format converts via gmtime; for whole-second integral-rep durations it sets tm_zone to "UTC" and uses the plain tm format. Otherwise it computes subseconds as the remainder of the epoch value; if negative (pre-epoch rounding) it borrows one second—decrementing tm_sec or re-calling gmtime on val minus one second—and then formats with subseconds via do_format. Note the deprecated reversed Char/Duration template parameter order.

<a id="u-8130a8b2e948"></a>
### `chrono.h-tm-field-accessors`

`auto tm_sec() const noexcept -> int` · [include/fmt/chrono.h:L1096-L1099][f1]

Bounds-checked accessors for tm fields: each returns the field with an FMT_ASSERT on its valid range (sec ≤ 61, min ≤ 59, hour ≤ 23, mday 1-31, mon 0-11, wday 0-6, yday 0-365); tm_year returns 1900 + tm_year as long long; tm_hour12 maps 0→12 and h≥12→h-12.

<a id="u-28de8ce38665"></a>
### `chrono.h-tm-zone-detection-helpers`

`template <typename T, typename = void> struct has_tm_gmtoff : std::false_type` · [include/fmt/chrono.h:L943-L944][f1]

Type traits detecting whether a tm-like struct has tm_gmtoff/tm_zone members, plus set_tm_zone which assigns the zone pointer and returns true when the member exists (false otherwise), and utc() returning a static "UTC" buffer usable as a stable tm_zone value.

<a id="u-d5c235f766e9"></a>
### `chrono.h-to-nonnegative-int`

`template <typename T, typename Int, FMT_ENABLE_IF(std::is_integral<T>::value)> inline…` · [include/fmt/chrono.h:L968-L975][f1]

Converts a value to Int, requiring it in [0, upper).

The integral overload throws format_error("chrono value is out of range") for negative values or values ≥ upper (unsigned Int skips the check); the floating overload throws format_error("invalid value") for value < 0 or value ≥ upper+1.

<a id="u-4a9e51802f91"></a>
### `chrono.h-utc-time-formatter`

`template <typename Duration, typename Char> struct formatter<utc_time<Duration>, Char…` · [include/fmt/chrono.h:L2214-L2217][f1]

Formats utc_time by converting to sys_time with detail::utc_clock::to_sys and delegating to the sys_time formatter; it inherits that formatter's parse.

<a id="u-fd33dd4b6b23"></a>
### `chrono.h-write-padding`

`template <typename OutputIt> auto write_padding(OutputIt out, pad_type pad, int width…` · [include/fmt/chrono.h:L657-L661][f1]

Emits padding characters for numeric fields: the width overload fills with '0' or ' ' per pad_type (returning immediately for pad_type::none); the single-character overload writes one pad character unless padding is none.

<a id="u-17401013d438"></a>
### `chrono.h-write-tm-locale`

`template <typename Char, typename OutputIt, FMT_ENABLE_IF(!std::is_same<Char, char>::…` · [include/fmt/chrono.h:L392-L399][f1]

Writes one localized tm field.

The non-char overload writes directly into a buffer obtained from the output iterator; the char overload formats into a temporary basic_memory_buffer and then re-encodes it via write_encoded_tm_str so the result is valid UTF-8 for non-classic locales.

<a id="u-5df09ed42955"></a>
### `chrono.h-write-tm-str`

`template <typename Char, typename OutputIt, FMT_ENABLE_IF(!std::is_same<Char, char>::…` · [include/fmt/chrono.h:L365-L372][f1]

Writes a tm string for non-char output: for non-char Char it runs the codecvt conversion (throwing on failure); for char it delegates to write_encoded_tm_str.

<a id="u-4017a28c60a5"></a>
### `do_write`

`template <typename Char> inline void do_write(buffer<Char>& buf, const std::tm& time,…` · [include/fmt/chrono.h:L381-L390][f1]

Formats a single tm field through the locale's std::time_put facet into a buffer via formatbuf, imbuing the stream with loc.

If facet.put reports failure it throws format_error("failed to format time").

<a id="u-d90c6850d4ba"></a>
### `get_milliseconds`

`template <typename Rep, typename Period, FMT_ENABLE_IF(std::is_integral<Rep>::value)>…` · [include/fmt/chrono.h:L1564-L1583][f1]

Extracts the millisecond remainder of an integral duration.

With FMT_SAFE_DURATION_CAST it casts to a common seconds type, subtracts whole seconds, and checked-casts the difference to duration<Rep, milli>, throwing on overflow; otherwise it uses unchecked casts of d - whole seconds.

<a id="u-ed77172c05fb"></a>
### `isfinite`

`template <typename T, FMT_ENABLE_IF(std::is_integral<T>::value&& has_isfinite<T>::val…` · [include/fmt/chrono.h:L1538-L1542][f1]

Returns true for integral types (enabled only when has_isfinite applies), letting duration code treat integral reps as always finite.

<a id="u-953b80d7c4a3"></a>
### `parse_chrono_format`

`template <typename Char, typename Handler> FMT_CONSTEXPR auto parse_chrono_format(con…` · [include/fmt/chrono.h:L670-L813][f1]

Parses a put_time-like chrono format string and dispatches each conversion to a handler, returning the position just before the closing '}'.

Empty input or a leading '}' returns immediately; a first character that is neither '%' nor '}' throws format_error("invalid format"). Literal runs are batched into on_text. '%' consumes the next character, with optional '_'/'-' prefix selecting space/none padding; %% %n %t produce literal text. Single-letter specs map to on_year/on_abbr_weekday/etc.; 'E' and 'O' prefixes consume one more character and dispatch alternative-numeric-system variants, throwing format_error("invalid format") for unknown combinations or a trailing '%'/'E'/'O' at end of input. A '}' terminates the scan; trailing literal text is flushed before returning.

<a id="u-e4c802b1a3ae"></a>
### `pow10`

`constexpr auto pow10(std::uint32_t n) -> long long` · [include/fmt/chrono.h:L983-L985][f1]

Recursive constexpr power of ten for n ≥ 0.

<a id="u-c16032e32644"></a>
### `to_time_t`

`template <typename Duration> auto to_time_t(sys_time<Duration> time_point) -> std::ti…` · [include/fmt/chrono.h:L521-L529][f1]

Converts a sys_time point to std::time_t by checked-casting its time-since-epoch to a duration<time_t>, avoiding a potentially overflowing cast to system_clock::time_point first.

<a id="u-3333da8c9d9f"></a>
### `write_codecvt`

`template <typename CodeUnit> void write_codecvt(codecvt_result<CodeUnit>& out, string…` · [include/fmt/chrono.h:L321-L334][f1]

Converts a UTF-8 string to a different code unit type using the locale's codecvt facet into a fixed 32-unit buffer.

If the conversion result is not std::codecvt_base::ok it throws format_error("failed to format time"); the output end pointer is set by the facet.

<a id="u-9f749ddcbd46"></a>
### `write_digit2_separated`

`inline void write_digit2_separated(char* buf, unsigned a, unsigned b, unsigned c, cha…` · [include/fmt/chrono.h:L585-L613][f1]

Writes three two-digit numbers separated by a separator into an 8-byte buffer using a branchless BCD bit trick (Pavel Novikov's method), then memcpy's the 64-bit result, reversing the bytes on big-endian machines.

<a id="u-bf21ca318716"></a>
### `write_floating_seconds`

`template <typename Duration> void write_floating_seconds(memory_buffer& buf, Duration…` · [include/fmt/chrono.h:L1057-L1081][f1]

Formats the seconds-and-fraction part of a floating-point duration into a memory buffer as "{:.Nf}" of fmod(value, 60).

If num_fractional_digits is negative it derives it from the period, bumping to 6 when the value isn't exactly representable at fewer digits. Asserts the rep is floating point.

<a id="u-53f08030e85d"></a>
### `write_fractional_seconds`

`template <typename Char, typename OutputIt, typename Duration> void write_fractional_…` · [include/fmt/chrono.h:L1006-L1052][f1]

Writes the subsecond part of a duration as '.digits'.

It computes the fractional remainder cast to a subsecond precision type (floating reps use the count directly), then: with precision < 0 (integral reps only, asserted) it writes '.' plus leading zeros and all digits when the period is finer than seconds; with precision > 0 it truncates or zero-pads to exactly that many digits, dropping the value entirely if truncation leaves zero. precision == 0 writes nothing.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/chrono.h
