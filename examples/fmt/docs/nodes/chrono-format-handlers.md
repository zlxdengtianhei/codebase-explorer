# Chrono Format Handlers

**Capability.** Validates chrono specs and renders duration and std::tm fields, including localized time strings and subseconds.

Come here for chrono format-spec handling. The units describe duration decomposition, std::tm field rendering, localization, and spec validation.

**Depends on.**

- [Dragonbox Cache and Assertions](dragonbox-cache-and-assertions.md) · graph-only · 7 edge(s)

Parent: [Chrono Formatting Support](chrono-formatting-support.md)

## Units (10)

<a id="u-65adc6c47289"></a>
### `chrono.h-calendar-name-lookups`

`inline auto tm_wday_full_name(int wday) -> const char*` · [include/fmt/chrono.h:L917-L922][f1]

Returns fixed English weekday and month names for valid indices.

Invalid weekday indices return "?" for full names and "???" for short names; invalid month indices return "?" for full names and "???" for short names.

<a id="u-7c128d80ebb7"></a>
### `chrono.h-chrono-format-checker`

`struct chrono_format_checker : null_chrono_spec_handler<chrono_format_checker>` · [include/fmt/chrono.h:L1515-L1518][f1]

Validates chrono format specifiers for duration formatting.

Unsupported callbacks throw a no-date error. Text and time-of-day callbacks are accepted as no-ops. The duration-value callback throws a precision-not-allowed error only when the checker was marked as having integral precision; the duration-unit callback is a no-op.

<a id="u-ffb206b7839e"></a>
### `chrono.h-duration-formatter`

`template <typename Char, typename Rep, typename Period> struct duration_formatter` · [include/fmt/chrono.h:L1629-L1648][f1]

Formats a duration by decomposing its count into days, hours, minutes, seconds, and subseconds.

It stores an unsigned-style representation for small integral types, tracks a negative flag, and computes whole seconds through a checked duration cast. Non-finite handling writes "nan", "inf", or "-inf" and reports that it handled the value. Field helpers derive days, hours, 12-hour hours, minutes, and seconds from whole seconds; 12-hour hours map zero or negative to 12. The time helper builds a tm with checked hour/minute/second fields. Writing a value emits the sign once, writes NaN when needed, converts to a nonnegative integer, pads to width, and writes decimal digits. Formatting through tm constructs a tm writer and invokes the requested callback. Text is copied. Date, weekday, month, year, zone, and similar callbacks are no-ops because durations lack date information. Day-of-year writes days. 24-hour, 12-hour, and minute handlers write numeric fields in standard mode and delegate to tm formatting in alternative mode. Seconds in standard mode write floating fractional seconds with precision or integral seconds plus fractional seconds; alternative mode delegates to tm formatting. 12-hour time and AM/PM delegate to tm formatting after non-finite handling. 24-hour time writes HH:MM, or on non-finite values writes a colon between two non-finite renderings. ISO time writes 24-hour time, a colon, then standard seconds. Duration value writes the sign and formatted count; duration unit writes the unit.

<a id="u-15e47e1324e3"></a>
### `chrono.h-locale-time-formatting-helpers`

`inline auto get_classic_locale() -> const std::locale&` · [include/fmt/chrono.h:L310-L313][f1]

Converts and writes localized time strings through codecvt and time_put facets.

The codecvt helper fills a fixed 32-unit result and throws a format error if conversion is not ok. The encoded writer transcodes through wchar_t or char32_t when UTF-8 is active and the locale is not classic, throwing on failed UTF-8 conversion; otherwise it copies bytes. The char writer delegates to that encoded path, while non-char writers use codecvt directly. The time_put helper imbues an ostream with the locale and throws if the facet reports failure. The write overloads route through a buffer and return the advanced output iterator.

<a id="u-82fba9190c0b"></a>
### `chrono.h-locale-writer-policy`

`template <bool UseLocale = FMT_USE_LOCALE != 0> struct locale_writer` · [include/fmt/chrono.h:L412-L413][f1]

Chooses classic versus localized time-string handling.

The primary template compares a locale reference with the classic locale, writes time through the locale-aware time_put path, and writes strings through the classic locale when not localized or through the referenced locale when localized. The false specialization always reports classic, returns output unchanged for time writing, and copies strings without transcoding.

<a id="u-bc843a7d488f"></a>
### `chrono.h-null-chrono-spec-handler`

`template <typename Derived> struct null_chrono_spec_handler` · [include/fmt/chrono.h:L815-L816][f1]

Base handler for chrono format parsing whose every callback delegates to unsupported.

Derived handlers override the callbacks they support and provide the unsupported behavior.

<a id="u-8281ad9bd365"></a>
### `chrono.h-timezone-helpers`

`template <typename T, FMT_ENABLE_IF(has_tm_zone<T>::value)> auto set_tm_zone(T& time,…` · [include/fmt/chrono.h:L952-L956][f1]

Sets a tm zone pointer when the type has a tm_zone member and reports success; otherwise it is a no-op returning false.

The UTC helper returns a static mutable "UTC" buffer.

<a id="u-f4e781a4bb31"></a>
### `chrono.h-tm-format-checker`

`class tm_format_checker : public null_chrono_spec_handler<tm_format_checker>` · [include/fmt/chrono.h:L864-L869][f1]

Validates chrono format specifiers for std::tm formatting.

Most date and time callbacks are accepted as no-ops; unsupported callbacks throw a no-format error. The constructor records whether the tm type has timezone information. UTC-offset and zone-name callbacks throw a no-timezone error when that flag is false.

<a id="u-754501178174"></a>
### `chrono.h-tm-writer-core-and-private-helpers`

`class tm_writer` · [include/fmt/chrono.h:L1083-L1096][f1]

Core of the std::tm formatter: stores locale, localization/classic state, output iterator, optional subseconds, and the tm reference.

Private accessors assert field ranges; the year accessor adds 1900. The 12-hour accessor maps hours below 12 to themselves and hours 12 and above to hour-12, then maps zero to 12, so 12 stays 12 and 13–23 become 1–11. Year splitting returns the absolute last two digits. ISO week helpers compute week number and ISO week-based year. Numeric writers emit one or two digits, with optional padding. Extended year writing uses at least four characters and places a negative sign before padding for zero padding, otherwise after padding. UTC-offset writing emits sign, hours, an optional colon for alternative numeric systems, and minutes. UTC-offset formatting uses tm_gmtoff when present, otherwise zero. Zone-name formatting throws when a present tm_zone is null, otherwise writes through the locale writer; without tm_zone it writes "UTC". Localized formatting delegates to the locale writer's time path.

<a id="u-f0a53f9cd2a7"></a>
### `chrono.h-tm-writer-format-handlers`

`FMT_CONSTEXPR void on_text(const Char* begin, const Char* end)` · [include/fmt/chrono.h:L1260-L1262][f1]

Public format-spec handlers render individual std::tm fields.

Text is copied directly. Weekday and month names use fixed English names in classic mode and localized time_put otherwise. Numeric weekday, month, week, day, hour, minute, and second handlers write numeric values in classic or standard mode and use localized alternative callbacks otherwise. UTC offset always uses the offset helper and does not switch to localized time_put; zone name always uses the zone helper, which may transcode through the locale writer. ISO week-based year and short year always write numeric values. 24-hour time always writes HH:MM. ISO time writes 24-hour time, a colon, then standard seconds. 12-hour time in classic mode writes HH:MM:SS, a space, and AM/PM; otherwise it uses localized time_put. AM/PM in classic mode writes A or P followed by M; otherwise it uses localized time_put. Datetime, local date, and local time compose classic fields or use localized time_put with the E modifier for alternative systems. US date writes MM/DD/YY; ISO date writes YYYY-MM-DD, using extended year output outside 0–9999. Century handling writes "-0" for years -99 through -1, two digits for upper 0–99, otherwise the full upper value; alternative mode uses localized time_put. Day-of-year writes the one-based day with padding. Seconds write the numeric second and, when subseconds are present, either floating or integral fractional seconds; localized seconds do not format subseconds. Duration value and unit callbacks are no-ops for tm.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/chrono.h
