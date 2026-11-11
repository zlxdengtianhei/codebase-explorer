# Primitive tm emitters

**Capability.** Emits individual digits, years, English weekday and month names, and the on_* callback output for tm formatting.

The lowest-level output primitives used by the tm writer: digit and year emitters plus static English name tables. The on_* callbacks here produce the actual field output.

**Depended on by.**

- [Localized tm writer](localized-tm-writer.md) · model-inferred · 1 inferred relation(s) · The localized tm writer routes field output through the primitive emitters for digits and name tables.

Parent: [Chrono and time formatting](chrono-and-time-formatting.md)

## Units (3)

<a id="u-47017e069603"></a>
### `chrono.h-low-level-writers`

`void write1(int value)` · [include/fmt/chrono.h:L1172-L1174][f1]

Primitive emitters: write1/write2 emit one/two digits (write2 with pad emits a pad character then one digit for values < 10); write_year_extended emits a year in at least 4 characters, placing '-' before padding for zero padding and after for other pads; write_utc_offset emits ±HH[:]MM from a second-based offset (colon only for alternative numeric system); format_utc_offset uses tm_gmtoff when present else offset 0; format_tz_name writes tm_zone via locale_writer (throwing format_error("no timezone") on a null zone) or literal "UTC" when the member is absent; format_localized delegates a single conversion to locale_writer::write_time.

<a id="u-47fb760ce260"></a>
### `chrono.h-tm-name-tables`

`inline auto tm_wday_full_name(int wday) -> const char*` · [include/fmt/chrono.h:L917-L922][f1]

Return English weekday and month names by index: full and abbreviated lists for wday 0-6 and month 0-11, with "?"/"???" placeholders for out-of-range indices.

<a id="u-57be5ab8a532"></a>
### `chrono.h-tm-writer-spec-handlers`

`FMT_CONSTEXPR void on_text(const Char* begin, const Char* end)` · [include/fmt/chrono.h:L1260-L1262][f1]

The on_* callbacks producing output.

Classic/standard path: weekday/month names from the static tables; on_datetime composes "Wkd Mon D HH:MM:SS YYYY"; on_us_date/on_iso_date use write_digit2_separated (ISO date writes an extended year plus offset when outside [0,10000)); year specs use write_year/write2 with the split-year convention, on_century special-cases years in [-99,0) as "-0"; week-of-year specs apply the U/W/V formulas; hour/minute use write2 with pad. Localized or alternative-numeric paths delegate to format_localized with the matching conversion and 'E'/'O' modifier. on_second additionally appends subseconds: floating reps via write_floating_seconds (stripping the leading '0'), integral reps via write_fractional_seconds; the localized path formats only 'S' with no subseconds. on_duration_value/on_duration_unit are empty because durations don't apply to tm.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/chrono.h
