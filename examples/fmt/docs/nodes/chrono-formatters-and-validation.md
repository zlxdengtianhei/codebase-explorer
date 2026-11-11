# Chrono formatters and validation

**Capability.** Public chrono formatter classes plus compile-time validation of duration and tm format strings and calendar math helpers.

This module holds the user-facing chrono formatters (durations, calendar types) and the parse-time validators that reject bad format strings. Calendar math helpers for ISO week/year computations also live here.

Parent: [Chrono and time formatting](chrono-and-time-formatting.md)

## Units (10)

<a id="u-0c83253a34b2"></a>
### `chrono.h-calendar-type-formatters`

`template <typename Char> struct formatter<weekday, Char> : private formatter<std::tm,…` · [include/fmt/chrono.h:L1921-L1927][f1]

Formatters for weekday/day/month/year/year_month_day, all following the same pattern: they privately inherit formatter<std::tm, Char> and pre-seed its format with the default spec (%a, %d, %b, %Y, %F respectively).

parse marks use_tm_formatter_ when the user supplied any spec and then defers to the tm formatter's parse; otherwise it returns immediately. format fills a std::tm with the single relevant field (month stored as 1-based minus 1, year as value minus 1900) and either delegates to the tm formatter or directly invokes the matching tm_writer callback for the default rendering.

<a id="u-7c128d80ebb7"></a>
### `chrono.h-chrono-format-checker`

`struct chrono_format_checker : null_chrono_spec_handler<chrono_format_checker>` · [include/fmt/chrono.h:L1515-L1518][f1]

Parse-time validator for duration format strings.

It accepts time-of-day specs (hours, minutes, seconds, am/pm, day-of-year, time compositions) and duration unit/value specs as no-ops, but any date, weekday, month, year, or timezone spec falls through to unsupported(), throwing format_error("no date"). on_duration_value throws format_error("precision not allowed for this argument type") when a precision was specified for an integral rep.

<a id="u-8de5846bdc3d"></a>
### `chrono.h-duration-cast-overloads`

`template <typename To, typename FromRep, typename FromPeriod, FMT_ENABLE_IF(std::is_i…` · [include/fmt/chrono.h:L462-L492][f1]

Checked casts between chrono durations, selected by rep types.

Integral→integral (with FMT_SAFE_DURATION_CAST) multiplies by the ratio numerator after overflow checks against max/min divided by it (throwing via throw_duration_error), divides by the denominator, then losslessly converts to To::rep, throwing on any error; without the macro it falls back to std::chrono::duration_cast. Floating→floating preserves non-finite counts by direct cast, otherwise uses safe_duration_cast and throws on error. Mixed integral/floating falls back to the standard cast, which may overflow.

<a id="u-17984e118e06"></a>
### `chrono.h-duration-formatter-core`

`template <typename Char, typename Rep, typename Period> struct duration_formatter` · [include/fmt/chrono.h:L1629-L1648][f1]

Stateful formatter that renders a duration according to chrono specs.

The constructor stores the absolute value in an unsigned-friendly rep, records negativity, and checked-casts to seconds (which may overflow or throw). handle_nan_inf writes "nan" or "±inf" and returns true for non-finite values. Field getters derive days/hours/minutes/seconds from the seconds count via mod; hour12 maps 0→12. time() builds a std::tm from hour/minute/second using to_nonnegative_int (throwing on out-of-range). write_sign emits '-' once and clears the flag; write pads a nonnegative value to a width (NaN goes to write_nan); format_tm delegates a single tm_writer callback for locale-dependent output, short-circuiting NaN.

<a id="u-31bd43971efb"></a>
### `chrono.h-duration-formatter-spec-handlers`

`void on_text(const Char* begin, const Char* end)` · [include/fmt/chrono.h:L1728-L1730][f1]

Spec callbacks for durations.

Date/weekday/month/year/timezone specs are empty no-ops (durations carry no dates). Time specs first short-circuit non-finite values via handle_nan_inf; standard numeric-system paths write the derived field with padding, while alternative numeric systems build a std::tm and delegate to tm_writer with the 'O' modifier. on_second is the richest: floating reps format via write_floating_seconds honoring precision (emitting '-' and padding as needed), integral reps write two-digit seconds plus write_fractional_seconds. on_24_hour_time and on_iso_time handle NaN specially to still emit ':' separators; on_duration_value writes sign plus the raw count with precision; on_duration_unit writes the unit suffix.

<a id="u-b5d51dc755ea"></a>
### `chrono.h-fallback-calendar-types`

`class weekday` · [include/fmt/chrono.h:L1862-L1867][f1]

Minimal replacements for std::chrono weekday/day/month/year/year_month_day used when __cpp_lib_chrono < 201907 (otherwise aliases to the std types).

Each stores its value (weekday normalizes 7→0) and exposes it via c_encoding or an explicit conversion operator; year_month_day aggregates the three with year()/month()/day() accessors. No validation is performed on stored values.

<a id="u-bc843a7d488f"></a>
### `chrono.h-null-chrono-spec-handler`

`template <typename Derived> struct null_chrono_spec_handler` · [include/fmt/chrono.h:L815-L816][f1]

CRTP base for chrono spec handlers whose default reaction to every conversion spec is to call the derived class's unsupported(); derived checkers and writers override only the specs they support, so any unhandled spec surfaces as an error in the derived implementation.

<a id="u-f4e781a4bb31"></a>
### `chrono.h-tm-format-checker`

`class tm_format_checker : public null_chrono_spec_handler<tm_format_checker>` · [include/fmt/chrono.h:L864-L869][f1]

Compile-time/format-parse-time validator for std::tm format strings.

It accepts all date/time specs as no-ops but throws format_error("no timezone") from on_utc_offset and on_tz_name when the tm type lacks timezone support (has_timezone_ false); any spec not overridden (duration specs) reaches unsupported(), which throws format_error("no format").

<a id="u-1dac752eb312"></a>
### `chrono.h-year-iso-week-helpers`

`auto split_year_lower(long long year) const noexcept -> int` · [include/fmt/chrono.h:L1136-L1140][f1]

Calendar math helpers: split_year_lower returns year % 100 clamped to [0,99] (negative years yield the absolute lower digits); iso_year_weeks computes 52 or 53 weeks from year-position formulas; iso_week_num derives the ISO week from yday/wday (Sunday counted as 7); tm_iso_week_year shifts to the previous/next year when the week number falls outside [1, weeks-in-year]; tm_iso_week_of_year correspondingly returns the last week of the previous year or week 1.

<a id="u-648af92b95dd"></a>
### `throw_duration_error`

`FMT_NORETURN inline void throw_duration_error()` · [include/fmt/chrono.h:L457-L459][f1]

Throws format_error("cannot format duration"); the single failure path for checked duration conversions.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/chrono.h
