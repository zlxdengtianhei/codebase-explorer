# Chrono Calendar Fallback Types

**Capability.** Provides fallback day, month, weekday, year, and date types and their formatters for chrono calendar formatting.

This module contains fallback calendar component types. Readers find day, month, weekday, year, and date storage plus their formatters.

Parent: [Chrono Formatting Support](chrono-formatting-support.md)

## Units (10)

<a id="u-0e7cf70e031f"></a>
### `chrono.h-day-formatter`

`template <typename Char> struct formatter<day, Char> : private formatter<std::tm, Char>` · [include/fmt/chrono.h:L1946-L1952][f1]

Formats a day.

Parsing sets the default format to day-of-month and records whether a non-empty user format exists; if so it delegates to the tm formatter parser. Formatting builds a tm with the day value and either delegates to the tm formatter or writes the day-of-month with standard numeric system and zero padding.

<a id="u-ce7293be008f"></a>
### `chrono.h-fallback-day`

`class day` · [include/fmt/chrono.h:L1873-L1878][f1]

Fallback day type storing an unsigned char.

Construction stores the value and explicit conversion returns it.

<a id="u-39c99b98afdd"></a>
### `chrono.h-fallback-month`

`class month` · [include/fmt/chrono.h:L1884-L1889][f1]

Fallback month type storing an unsigned char.

Construction stores the value and explicit conversion returns it.

<a id="u-630d720aacbc"></a>
### `chrono.h-fallback-weekday`

`class weekday` · [include/fmt/chrono.h:L1862-L1867][f1]

Fallback weekday type storing an unsigned char.

Construction maps value 7 to 0; c_encoding returns the stored value.

<a id="u-5b7e2770592d"></a>
### `chrono.h-fallback-year`

`class year` · [include/fmt/chrono.h:L1895-L1900][f1]

Fallback year type storing an int.

Construction stores the value and explicit conversion returns it.

<a id="u-4215208b98ab"></a>
### `chrono.h-fallback-year-month-day`

`class year_month_day` · [include/fmt/chrono.h:L1905-L1912][f1]

Fallback calendar date type storing year, month, and day components.

Construction stores the three values and accessors return them.

<a id="u-8d2e63fe2a78"></a>
### `chrono.h-month-formatter`

`template <typename Char> struct formatter<month, Char> : private formatter<std::tm, C…` · [include/fmt/chrono.h:L1971-L1977][f1]

Formats a month.

Parsing sets the default format to abbreviated month and records whether a non-empty user format exists; if so it delegates to the tm formatter parser. Formatting builds a tm with the month index and either delegates to the tm formatter or writes the abbreviated month.

<a id="u-27c7a902e920"></a>
### `chrono.h-weekday-formatter`

`template <typename Char> struct formatter<weekday, Char> : private formatter<std::tm,…` · [include/fmt/chrono.h:L1921-L1927][f1]

Formats a weekday.

Parsing sets the default format to abbreviated weekday and records whether the user supplied a non-empty format; if so it delegates to the tm formatter parser. Formatting builds a tm with the weekday encoding and either delegates to the tm formatter or writes the abbreviated weekday through a tm writer.

<a id="u-78e4d590fa6a"></a>
### `chrono.h-year-formatter`

`template <typename Char> struct formatter<year, Char> : private formatter<std::tm, Char>` · [include/fmt/chrono.h:L1996-L2002][f1]

Formats a year.

Parsing sets the default format to full year and records whether a non-empty user format exists; if so it delegates to the tm formatter parser. Formatting builds a tm with the year offset and either delegates to the tm formatter or writes the year with standard numeric system and zero padding.

<a id="u-c6d7328e070e"></a>
### `chrono.h-year-month-day-formatter`

`template <typename Char> struct formatter<year_month_day, Char> : private formatter<s…` · [include/fmt/chrono.h:L2021-L2027][f1]

Formats a calendar date.

Parsing sets the default format to ISO date and records whether a non-empty user format exists; if so it delegates to the tm formatter parser. Formatting builds a tm from the date components and either delegates to the tm formatter or writes the ISO date.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/chrono.h
