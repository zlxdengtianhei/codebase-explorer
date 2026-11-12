# ISO-8601 date utility

**Capability.** Formats and parses ISO-8601 dates with UTC defaults and ParsePosition-aware parsing.

Use for ISO-8601 date formatting/parsing internals. Units show formatting overloads, private helpers, utility class, and parse behavior.

**Depended on by.**

- [Core Gson default adapters](core-gson-default-adapters.md) · graph-only · 1 edge(s)

Parent: [Public utilities and dates](public-utilities-and-dates.md)

## Units (4)

<a id="u-973954be5b91"></a>
### `ISO8601Utils.java-iso8601-formatting`

`public static String format(Date date)` · [gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java:L68-L70][f1]

Formats a Date as an ISO-8601 string, delegating the one- and two-argument overloads to the full form with UTC.

The full form builds a GregorianCalendar in the supplied time zone and Locale.US, writes yyyy-MM-dd'T'HH:mm:ss, appends .SSS only when millis is requested, then appends 'Z' when the zone offset at that instant is zero; otherwise it appends the sign and hh:mm using absolute hours and minutes. The offset used for output is the zone offset at the calendar instant, not merely the raw offset.

<a id="u-305f3c2773c3"></a>
### `ISO8601Utils.java-iso8601-parsing-helpers`

`private static boolean checkOffset(String value, int offset, char expected)` · [gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java:L319-L321][f1]

These private helpers support parsing and formatting.

checkOffset returns true only when the offset is in range and the character equals the expected one. parseInt parses a non-negative decimal integer between two indices and throws NumberFormatException for invalid indices or any non-digit. padInt left-pads an integer with zeros to the requested width, appending the full number if it is already longer. indexOfNonDigit returns the first index at or after the start whose character is outside '0'-'9', or the string length when all remaining characters are digits.

<a id="u-9191ffd91611"></a>
### `ISO8601Utils.java-iso8601-utility-class`

`class name public final class ISO8601Utils` · [gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java:L38-L40][f1]

This final utility class groups ISO-8601 date formatting and parsing with a private constructor and a prefetched UTC time zone.

It exposes only static methods; formatting and parsing behavior is described in the separate method units.

<a id="u-7f34211056a1"></a>
### `ISO8601Utils.parse`

`public static Date parse(String date, ParsePosition pos) throws ParseException` · [gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java:L147-L309][f1]

Parses an ISO-8601 date from the current ParsePosition index, updating the index on success and throwing ParseException on malformed input.

- Date part: four-digit year, optional '-' then two-digit month, optional '-' then two-digit day, so dashed, compact, and mixed dash variants are accepted.
- No 'T' and no trailing input: returns a non-lenient default-zone calendar date with zero time.
- No 'T' but trailing input: does not skip time fields; the next character is treated as the time-zone indicator.
- With 'T': parses hour, optional ':' then minute, optional ':' then seconds when the next character is not Z/+/-; time separators are independently optional, so mixed colon variants are accepted; seconds 60-62 truncate to 59; an optional '.' fraction parses up to three digits, scales one or two digits, and advances past all following digits.
- Time zone: 'Z' is UTC; '+'/'-' takes the remaining substring, appends '00' when shorter than five characters, advances by that length, maps +0000/+00:00 to UTC, otherwise builds a GMT zone and rejects a resolved ID that differs even after removing colons; +hh, +hhmm, and +hh:mm forms are accepted when they resolve; any other indicator is rejected.
- Failure: missing time zone, invalid zone, and numeric/range failures are wrapped in ParseException with the quoted input, a message, the current position, and the original cause.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java
