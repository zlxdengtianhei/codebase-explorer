# std::tm Formatting

**Capability.** Renders std::tm values: the tm_writer walks parsed spec callbacks, choosing fixed English output or locale-aware std::time_put via formatbuf/codecvt transcoding, plus gmtime conversion and tm field helpers.

Use for std::tm output and time_t-to-tm conversion. The formatter<std::tm> drives parse_chrono_format then tm_writer; locale-writer gates between classic and localized paths.

**Depends on.**

- [Duration Formatting](chrono-duration.md) · model-inferred · 0 edge(s)
- [Chrono Spec Parsing](chrono-parse.md) · model-inferred · 0 edge(s)
- [Error Reporting](core-errors.md) · graph-confirmed · 7 edge(s)

**Depended on by.**

- [Calendar & Time-Point Formatters](chrono-calendar.md) · model-inferred · 0 edge(s)

Parent: [Chrono Formatting](chrono-h.md)

## Units (12)

<a id="u-a64f82e80e7b"></a>
### `chrono-locale-writer`

`template <bool UseLocale = FMT_USE_LOCALE != 0> struct locale_writer` · [include/fmt/chrono.h:L412-L413][f1]

Compile-time gate between localized and locale-free tm formatting.

The primary template (enabled when FMT_USE_LOCALE) compares a locale_ref against the classic locale; write_time forwards to the locale-aware detail::write, and write_str writes via the classic locale when not localized or via loc's std::locale when localized — an empty locale_ref means the global locale. The locale_writer<false> specialization exists for builds without locale support: is_classic always returns true, write_time is never called and returns out unchanged, and write_str just copies the (assumed ASCII) bytes, so no locale-dependent branch is instantiated.

calls: [chrono-tm-str-write](chrono-tm.md#u-101b95ff05cb)

<a id="u-101b95ff05cb"></a>
### `chrono-tm-str-write`

`template <typename Char, typename OutputIt, FMT_ENABLE_IF(!std::is_same<Char, char>::…` · [include/fmt/chrono.h:L365-L372][f1]

Writes std::tm text through either direct transcoding or stream-based locale formatting.

write_tm_str for non-char character types converts the string_view through the locale's codecvt into a codecvt_result and copies the code units; the char overload delegates to write_encoded_tm_str, which transcodes only when a non-classic locale is active under UTF-8. do_write renders a std::tm through std::time_put: it wraps the target buffer in formatbuf, builds an ostream imbued with the locale, calls facet.put with the given format/modifier, and throws format_error("failed to format time") if put reports failure. The two write overloads both buffer through do_write; the non-char version returns the iterator from the buffer, while the char version re-encodes the produced bytes with write_encoded_tm_str.

calls: [write_codecvt](chrono-tm.md#u-3333da8c9d9f), [write_encoded_tm_str](chrono-tm.md#u-226585ad9fdf); uses: [formatbuf](chrono-tm.md#u-79807d9a0e31)

<a id="u-434caa51333d"></a>
### `chrono-tm-field-detection`

`template <typename T, typename = void> struct has_tm_gmtoff : std::false_type` · [include/fmt/chrono.h:L943-L944][f1]

Traits and helpers for optional std::tm timezone fields.

has_tm_gmtoff and has_tm_zone detect the corresponding members via void_t detection; set_tm_zone assigns tm_zone when present (returning true) or does nothing and returns false otherwise. utc() returns a static "UTC" buffer used as a synthetic zone name on platforms lacking tm_zone.

<a id="u-8e2fa5eaaa2c"></a>
### `chrono-tm-name-helpers`

`inline auto tm_wday_full_name(int wday) -> const char*` · [include/fmt/chrono.h:L917-L922][f1]

Return fixed English names for tm field values.

tm_wday_full_name/short_name index Sunday-based names for 0..6, and tm_mon_full_name/short_name index month names for 0..11; any out-of-range input yields '?' or '???' instead of throwing or indexing out of bounds.

<a id="u-39b546d6bcc2"></a>
### `tm_writer`

`class tm_writer` · [include/fmt/chrono.h:L1083-L1096][f1]

Renders a std::tm (optionally with a subsecond duration) by walking the callbacks of parse_chrono_format, writing into an output iterator and honoring locale settings chosen at construction: is_classic_ is true when not localized or the locale equals the classic one, in which case fixed English/ASCII output is produced; otherwise the corresponding spec is delegated to std::time_put through locale_writer/format_localized.

Accessors tm_sec..tm_yday FMT_ASSERT their documented ranges (seconds allow 0-61, yday 0-365) before use. Year output keeps %C+%y consistent with %Y (negative years get absolute lower digits), and ISO week year/week use the ISO week-date algorithm. Notable branches: on_second appends fractional seconds from subsecs_ (floating reps via write_floating_seconds with the leading '0' stripped; integer reps via write_fractional_seconds) only in the classic/standard path — locale-formatted seconds never get subseconds; %z uses tm_gmtoff when present else 0, and %Z writes tm_zone (throwing format_error("no timezone") if null) or the literal 'UTC' when the field does not exist; %j writes yday+1 with the pad policy controlling the leading digit. Date/time composition callbacks (%c, %x, %X, %F, %r) recombine the primitive callbacks in the right order, using write_digit2_separated for %D and %r. on_duration_value/on_duration_unit are intentionally empty since durations are not tm values.

**Notes.**

- failure: Out-of-range tm fields trip FMT_ASSERT in the accessors (e.g. tm_mon outside 0-11); a null tm_zone in format_tz_name raises format_error("no timezone").

uses: [parse_chrono_format](chrono-parse.md#u-953b80d7c4a3); calls: [chrono-locale-writer](chrono-tm.md#u-a64f82e80e7b), [write_digit2_separated](chrono-tm.md#u-9f749ddcbd46), [write_floating_seconds](chrono-duration.md#u-bf21ca318716), [write_fractional_seconds](chrono-duration.md#u-53f08030e85d), [chrono-tm-name-helpers](chrono-tm.md#u-8e2fa5eaaa2c)

<a id="u-79807d9a0e31"></a>
### `formatbuf`

`class formatbuf : public StreamBuf` · [include/fmt/chrono.h:L279-L289][f1]

Adapts a fmt buffer<char_type> as a streambuf so std::ostream-style formatting (e.g. std::time_put) writes directly into it.

The constructor stores a reference to the buffer. overflow pushes a single character unless it is the traits eof value, and always returns ch. xsputn appends the [s, s+count) range and returns count. Because the put area is never set, every sputc funnels through overflow; sputn funnels through xsputn, keeping the streambuf and buffer in sync.

<a id="u-3333da8c9d9f"></a>
### `write_codecvt`

`template <typename CodeUnit> void write_codecvt(codecvt_result<CodeUnit>& out, string…` · [include/fmt/chrono.h:L321-L334][f1]

Transcodes a multibyte input string into fixed-size code units using the locale's std::codecvt facet, filling a caller-provided codecvt_result.

It obtains the facet, resets the mbstate, and calls f.in over the whole input into the 32-unit buffer, writing the end pointer. If the conversion result is anything other than codecvt_base::ok it throws format_error("failed to format time"); otherwise out.buf/out.end hold the converted text. Inputs needing more than 32 code units fail via that error path.

**Notes.**

- failure: Any codecvt result other than ok, including overflow of the 32-element buffer, becomes format_error.

uses: [chrono-safe-duration-cast](chrono-duration.md#u-404dbc12e204)

<a id="u-226585ad9fdf"></a>
### `write_encoded_tm_str`

`template <typename OutputIt> auto write_encoded_tm_str(OutputIt out, string_view in, …` · [include/fmt/chrono.h:L336-L363][f1]

Writes a tm-derived string to out, transcoding through the locale when UTF-8 output is expected.

When detail::use_utf8 and the locale differs from the classic locale, it transcodes the input with write_codecvt into wchar_t or char32_t code units (wchar_t on MSVC or a non-dual-ABI libstdc++, char32_t otherwise), converts the result back to UTF-8 with to_utf8, and throws format_error("failed to format time") if that conversion fails; success copies the UTF-8 bytes to out. Otherwise it copies the input bytes unchanged.

calls: [write_codecvt](chrono-tm.md#u-3333da8c9d9f), [get_classic_locale][f1]

**Uncertainties.**

- Behavior of to_utf8 conversion failures beyond the throw is determined elsewhere in format.h.

<a id="u-9f749ddcbd46"></a>
### `write_digit2_separated`

`inline void write_digit2_separated(char* buf, unsigned a, unsigned b, unsigned c, cha…` · [include/fmt/chrono.h:L585-L613][f1]

Writes three two-digit decimal numbers separated by a character into an 8-byte buffer using bit tricks.

The values are packed into a 64-bit word (a at bits 0-23, b at 24-47, c at 48+), converted to BCD by adding floor(x/10)*6 computed with the (x*205)>>11 trick per 16-bit lane, nibbles are swapped to place digits in bytes, ASCII '0' and the separator are ORed in, and the word is memcpy'd to buf — byte-reversed on big-endian machines so the digit order is preserved. Inputs are expected to be below 100; larger values would produce garbage digits rather than an error.

calls: [is_big_endian][f2]

**Uncertainties.**

- Values >= 100 per field are outside the documented use (tm fields) and the numeric outcome of the BCD packing for them is not established.

<a id="u-8d74ea35751d"></a>
### `formatter<std::tm, Char>`

`template <typename Char> struct formatter<std::tm, Char>` · [include/fmt/chrono.h:L2115-L2123][f1]

Formats a std::tm from a chrono format spec, defaulting to "%F %T".

do_parse accepts alignment, an optional dynamic width, 'L' for localized output, then validates the chrono spec with tm_format_checker constructed with the has_timezone flag (true only when std::tm has tm_gmtoff, allowing %z/%Z); a non-empty spec replaces the default. do_format resolves dynamic width, runs tm_writer over the stored spec into a buffer, and emits the result with the parsed specs through the generic write. parse passes the tm_gmtoff detection result; format uses whole-second precision with no subsecond pointer. set_format lets derived formatters (calendar types, time points) substitute their own default spec.

uses: [tm_format_checker](chrono-parse.md#u-7121bda37a95), [tm_writer](chrono-tm.md#u-39b546d6bcc2); calls: [parse_chrono_format](chrono-parse.md#u-953b80d7c4a3)

<a id="u-1e179dcfcd29"></a>
### `gmtime`

`FMT_BEGIN_EXPORT /** * Converts given time since epoch as std::time_t value into ca…` · [include/fmt/chrono.h:L533-L541][f1]

Converts a time_t to std::tm in UTC, preferring thread-safe platform APIs over std::gmtime.

A local dispatcher tries gmtime_r first (success when it returns a non-null tm*); if that resolves to the null<> overload it tries gmtime_s (success on return 0), whose null<> fallback on non-MSVC calls std::gmtime and copies the result. If every attempt fails, it throws format_error("time_t value out of range"); otherwise it returns the filled tm. The sys_time overload converts its epoch via detail::to_time_t and forwards, so cast failures propagate as format_error too.

**Notes.**

- failure: Unsupported time_t values raise format_error("time_t value out of range"), and on non-MSVC where gmtime_r/gmtime_s are absent std::gmtime returning null triggers the same error.

calls: [to_time_t](chrono-tm.md#u-c16032e32644)

<a id="u-c16032e32644"></a>
### `to_time_t`

`template <typename Duration> auto to_time_t(sys_time<Duration> time_point) -> std::ti…` · [include/fmt/chrono.h:L521-L529][f1]

Converts a sys_time point to std::time_t by casting its time-since-epoch duration to a duration<std::time_t> with the checked detail::duration_cast rather than system_clock::to_time_t, avoiding an intermediate cast that could overflow; returns the resulting count.

Overflow in the cast propagates as format_error from duration_cast.

calls: [duration_cast](chrono-duration.md#u-14f9ff77d424)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/chrono.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h