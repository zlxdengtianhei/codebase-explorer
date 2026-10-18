# Internal Support Utilities

**Capability.** Small self-contained helpers consumed elsewhere: date formatting/parsing (ISO-8601 utility and pre-Java-9 DateFormat compatibility), numeric parse-limit enforcement, primitive/wrapper type relationships, and a null-rejecting list wrapper.

Use this subtree for cross-cutting utilities; consumers live in the adapter, streaming, and binding layers.

**Depended on by.**

- [Streaming JSON Reading](r1-streaming-json.md) · model-inferred · 0 edge(s)
- [Date and Time Adapters](r2-date-time-adapters.md) · graph-only · 2 edge(s)
- [JSON DOM Tree](r2-dom-tree.md) · graph-only · 2 edge(s)
- [Primitive and Utility Type Adapters](r2-primitive-adapters.md) · graph-only · 2 edge(s)
- [Gson Facade and Conversion API](r1-facade-api.md) · graph-only · 1 edge(s)

Parent: [Gson JSON Binding Library](r1-gson-root.md)

## Units (10)

<a id="u-19d078fce755"></a>
### `ISO8601Utils`

`class name public final class ISO8601Utils` · [gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java:L38-L40][f1]

Stateless utility class for formatting and parsing ISO-8601 dates, avoiding SimpleDateFormat for speed and GC friendliness.

Private constructor prevents instantiation; the class precomputes a UTC TimeZone constant shared by formatting and parsing. Supported parse grammar is [yyyy-MM-dd|yyyyMMdd][T(hh:mm[:ss[.sss]]|hhmm[ss[.sss]])]?[Z|[+-]hh[:]mm]], ported from Jackson databind.

<a id="u-6889a640a921"></a>
### `gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java:ISO8601Utils.format (2)`

`public static String format(Date date, boolean millis, TimeZone tz)` · [gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java:L91-L130][f1]

Formats a Date as yyyy-MM-ddThh:mm:ss[.sss] followed by 'Z' or a numeric UTC offset, using the caller-supplied time zone and Locale.US calendar.

The one- and two-argument overloads delegate here with UTC and millis=false by default (or the given millis flag). Milliseconds are appended only when the millis flag is true. Offset rendering: if tz.getOffset at the date's instant is zero, 'Z' is appended; otherwise the sign comes from the offset itself and absolute hours/minutes are zero-padded after a colon. All numeric fields are zero-padded via padInt.

calls: [iso8601utils-parse-helpers](r1-internal-support.md#u-8b1ce6accbf8)

<a id="u-7f34211056a1"></a>
### `ISO8601Utils.parse`

`public static Date parse(String date, ParsePosition pos) throws ParseException` · [gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java:L147-L309][f1]

Parses an ISO-8601 date starting at pos.getIndex() and returns a Date, updating pos to the consumed offset.

It reads a 4-digit year, then 2-digit month and day, accepting optional '-' separators. If there is no 'T' and the string ends after the day, a lenient=false GregorianCalendar in the default time zone yields the result. If 'T' is present it reads hours, minutes, optional seconds (values 60-62 are truncated to 59, i.e. up to three leap seconds), and an optional fractional-second field of 1-3 parsed digits, rescaled to milliseconds (1 digit *100, 2 digits *10, else as-is) and advancing past all fraction digits. A time zone is then mandatory: 'Z' selects UTC; '+' or '-' takes the rest of the string, appending "00" when shorter than 5 characters, mapping "+0000"/"+00:00" to UTC, otherwise constructing "GMT<offset>"; if TimeZone.getTimeZone returns an ID whose colon-stripped form differs from the requested ID, an IndexOutOfBoundsException is thrown, as for any other indicator character. The final calendar (lenient=false, in the parsed zone) is populated field by field. Any IndexOutOfBoundsException or IllegalArgumentException is caught and rethrown as a ParseException with message 'Failed to parse date [<input>]: <cause msg or class name>' at pos.getIndex(), cause attached; NumberFormatException from parseInt propagates uncaught.

**Notes.**

- failure: An input whose year/month/day digits run past the string end surfaces as NumberFormatException (from parseInt's range check), not ParseException.

calls: [iso8601utils-parse-helpers](r1-internal-support.md#u-8b1ce6accbf8)

**Uncertainties.**

- Whether the truncated leap-second handling (seconds 60-62 to 59) can produce a Date one second earlier than semantically intended is inherent to the code and unverified at runtime.

<a id="u-8b1ce6accbf8"></a>
### `iso8601utils-parse-helpers`

`private static boolean checkOffset(String value, int offset, char expected)` · [gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java:L319-L321][f1]

Private helpers shared by format and parse.

checkOffset returns true only if the offset is within the string and the character there equals the expected one. parseInt parses the digits between beginIndex and endIndex as a non-negative integer using negative accumulation (mirroring Integer.parseInt without sign support); it throws NumberFormatException for out-of-range indices, reversed bounds, or a non-digit character. padInt appends the decimal value to the builder, prefixed with zeros to reach the requested length. indexOfNonDigit scans from the given offset and returns the index of the first non-digit, or the string length if none exists.

<a id="u-182f417fef88"></a>
### `PreJava9DateFormatProvider`

`class PreJava9DateFormatProvider` · [gson/src/main/java/com/google/gson/internal/PreJava9DateFormatProvider.java:L23-L24][f2]

Supplies US-locale DateFormats matching Java 8's default patterns, for use on JVMs where JDK 9 changed locale data.

getUsDateTimeFormat(dateStyle, timeStyle) concatenates a date-part and a time-part pattern with a space and returns a SimpleDateFormat built with Locale.US. getDatePartOfDateTimePattern maps DateFormat.SHORT to "M/d/yy", MEDIUM to "MMM d, yyyy", LONG to "MMMM d, yyyy", and FULL to "EEEE, MMMM d, yyyy"; any other style throws IllegalArgumentException. getTimePartOfDateTimePattern maps SHORT to "h:mm a", MEDIUM to "h:mm:ss a", and both LONG and FULL to "h:mm:ss a z"; other values likewise throw IllegalArgumentException. The class is uninstantiable via a private constructor.

**Notes.**

- failure: Unsupported style constants raise IllegalArgumentException naming the offending style value.

<a id="u-10df2018ac06"></a>
### `NumberLimits`

`class NumberLimits` · [gson/src/main/java/com/google/gson/internal/NumberLimits.java:L10-L11][f3]

Static holder enforcing Gson's numeric parsing limits; fully covered by its parseBigDecimal and parseBigInteger units plus the 10,000-character MAX_NUMBER_STRING_LENGTH constant.

Uninstantiable private constructor.

group: [NumberLimits.parseBigDecimal](r1-internal-support.md#u-5f49b1496f23)

<a id="u-5f49b1496f23"></a>
### `NumberLimits.parseBigDecimal`

`public static BigDecimal parseBigDecimal(String s) throws NumberFormatException` · [gson/src/main/java/com/google/gson/internal/NumberLimits.java:L21-L30][f3]

Parses a string into a BigDecimal while enforcing Gson's number-parsing limits.

It first rejects strings longer than 10,000 characters with a NumberFormatException whose message contains the first 30 characters. After a successful BigDecimal construction, it rejects a scale whose absolute value is 10,000 or more, again with NumberFormatException; the scale is cast to long before abs to avoid overflow at Integer.MIN_VALUE. On success it returns the parsed BigDecimal.

**Notes.**

- failure: Malformed input also throws NumberFormatException, propagated from the BigDecimal constructor.

calls: [NumberLimits.parseBigDecimal](r1-internal-support.md#u-5f49b1496f23)

<a id="u-513e7aece357"></a>
### `NumberLimits.parseBigInteger`

`public static BigInteger parseBigInteger(String s) throws NumberFormatException` · [gson/src/main/java/com/google/gson/internal/NumberLimits.java:L32-L35][f3]

Parses a string into a BigInteger after checking the 10,000-character length limit.

Strings exceeding the limit trigger NumberFormatException via checkNumberStringLength; otherwise parsing is delegated to the BigInteger constructor, which throws NumberFormatException for malformed input. This is the only guard, so arbitrarily large digit counts up to the length cap are accepted.

calls: [NumberLimits.parseBigDecimal](r1-internal-support.md#u-5f49b1496f23)

<a id="u-0f3e35bbee8a"></a>
### `Primitives`

`class Primitives` · [gson/src/main/java/com/google/gson/internal/Primitives.java:L27-L28][f4]

Static utility class for primitive/wrapper type relationships; its private constructor prevents instantiation.

isPrimitive is true only for Class instances whose isPrimitive holds. isWrapperType matches exactly the nine wrapper classes Integer, Float, Byte, Double, Long, Character, Boolean, Short, Void. wrap maps each primitive class literal to its wrapper and returns any other type unchanged; unwrap is the exact inverse, mapping wrappers to primitives. Both are idempotent and use reference comparisons against class literals, so null or non-class Types fall outside isPrimitive/wrapper checks and wrap/unwrap return non-matching inputs untouched.

<a id="u-d7dcdd00cd2d"></a>
### `NonNullElementWrapperList`

`class NonNullElementWrapperList<E> extends AbstractList<E> implements RandomAccess` · [gson/src/main/java/com/google/gson/internal/NonNullElementWrapperList.java:L34-L38][f5]

A List view over a delegate ArrayList that rejects null element insertion while delegating all other operations unchanged.

The constructor stores the delegate after Objects.requireNonNull, so a null delegate throws immediately. The private nonNull helper throws NullPointerException("Element must be non-null") before set and add(int, E) mutate the delegate, so null elements never enter the list and the delegate is untouched on failure. Read/check operations (get, size, remove(int), remove(Object), clear, removeAll, retainAll, removeIf, contains, indexOf, lastIndexOf, both toArray overloads, sort, spliterator, equals, hashCode) forward directly to the delegate; per the class doc, check-only methods like contains tolerate null arguments rather than throwing. Most methods are overridden solely for efficiency over AbstractList defaults. Like other AbstractList subclasses, structural modification is not structurally thread-safe, and modCount behavior comes from AbstractList since this wrapper does not manage it itself.

**Notes.**

- failure: set and add throw NullPointerException when the element is null; other methods only propagate delegate exceptions such as IndexOutOfBoundsException.
- contract: The delegate is typed ArrayList to guarantee RandomAccess.

**Uncertainties.**

- ConcurrentModificationException behavior is inherited indirectly and cannot be fully established from this file alone, since the wrapper delegates mutation and does not track its own modCount.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/PreJava9DateFormatProvider.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/NumberLimits.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/Primitives.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/NonNullElementWrapperList.java