# Calendar & Time-Point Formatters

**Capability.** Public formatters for weekday/day/month/year/year_month_day and for sys_time/utc_time/local_time, all layered on formatter<std::tm>, with fallback calendar types when C++20 chrono is absent.

Use these to format calendar and time-point types; they reuse the std::tm formatting pipeline rather than implementing their own writers.

**Depends on.**

- [std::tm Formatting](chrono-tm.md) · model-inferred · 0 edge(s)

Parent: [Chrono Formatting](chrono-h.md)

## Units (3)

<a id="u-048a8bc6bb6a"></a>
### `chrono-calendar-formatters`

`template <typename Char> struct formatter<weekday, Char> : private formatter<std::tm,…` · [include/fmt/chrono.h:L1921-L1927][f1]

Formatters for weekday, day, month, year and year_month_day, each privately inheriting formatter<std::tm, Char>.

parse installs a default tm format spec (%a, %d, %b, %Y, %F respectively), then treats any non-empty custom spec as a full tm-format string by delegating to the base parse, remembering the choice in use_tm_formatter_. format builds a std::tm holding just the relevant fields (tm_wday from the weekday encoding, tm_mday from day, tm_mon as value-1 from month, tm_year as value-1900 from year, all three from year_month_day) and either runs the full tm formatter or calls a single tm_writer callback (on_abbr_weekday, on_day_of_month, on_abbr_month, on_year, on_iso_date) with a default (non-localized, classic) locale. Invalid ranges are not rejected here; they surface as the tm_writer assert/format behavior.

inherits: [formatter<std::tm, Char>](chrono-tm.md#u-8d74ea35751d); calls: [tm_writer](chrono-tm.md#u-39b546d6bcc2)

<a id="u-edc55a05dc68"></a>
### `chrono-fallback-calendar-types`

`class weekday` · [include/fmt/chrono.h:L1862-L1867][f1]

Minimal calendar types used when C++20 chrono is unavailable.

weekday stores an unsigned char, mapping an input of 7 to 0 and otherwise truncating; day, month and year store the raw value with explicit conversion operators back to unsigned/int; year_month_day aggregates the fmt year/month/day with getters. None validate ranges — out-of-range inputs are silently truncated to the underlying type.

<a id="u-4f0f4d845217"></a>
### `chrono-time-point-formatters`

`template <typename Char, typename Duration> struct formatter<sys_time<Duration>, Char…` · [include/fmt/chrono.h:L2180-L2182][f1]

Formatters for sys_time, utc_time and local_time, building on formatter<std::tm, Char>.

The sys_time formatter parses with timezone specs allowed (has_timezone true) and formats by converting the point with gmtime: for whole non-floating seconds it stamps the tm with the 'UTC' zone name; for finer durations it computes the subsecond remainder and, when it is negative (pre-epoch times), borrows one second — decrementing tm_sec or recomputing gmtime of the preceding second — before adding the borrowed second to the remainder, then formats with the subsecond pointer so %S includes fractions. The utc_time formatter is deprecated-parameter-order sys_time's subclass and simply converts via utc_clock::to_sys before delegating (when std::chrono::utc_clock is unavailable this branch cannot function). The local_time formatter parses with timezone specs disallowed (has_timezone false, so %z/%Z throw "no timezone") and formats by converting the epoch seconds with gmtime(time_t) to avoid zone conversion, attaching subseconds the same way when the duration is finer than a second.

inherits: [formatter<std::tm, Char>](chrono-tm.md#u-8d74ea35751d); calls: [gmtime](chrono-tm.md#u-1e179dcfcd29)

**Uncertainties.**

- When FMT_USE_UTC_TIME is 0, detail::utc_clock is a stub with only a to_sys member template, so utc_time formatting compiles only against that stub and real utc_time types are not usable — the practical behavior in that configuration is not visible here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/chrono.h