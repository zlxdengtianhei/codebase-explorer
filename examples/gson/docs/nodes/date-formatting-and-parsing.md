# Date Formatting and Parsing

**Capability.** Implements Date serialization with configurable formats, ISO-8601 parsing, and JVM-version-dependent default date styles.

This module handles conversion between Date subclasses and JSON strings. It includes DefaultDateTypeAdapter, the ISO-8601 utility ported from Jackson, pre-Java-9 default formats, and JavaVersion detection.

**Depends on.**

- [Gson Configuration Assembly](gson-configuration-assembly.md) · graph-only · 1 edge(s)
- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-only · 1 edge(s)

Parent: [Adapter Abstractions and Dates](adapter-abstractions-and-dates.md)

## Units (13)

<a id="u-a57d7a704d90"></a>
### `DefaultDateTypeAdapter.java-datetype-abstraction`

`class DateType<T extends Date>` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L82-L85][f1]

Abstract per-Date-subclass strategy: DATE converts a parsed java.util.Date to itself.

Subclasses store their dateClass and implement deserialize(Date) to convert. createAdapterFactory(String) and createAdapterFactory(int,int) each build a DefaultDateTypeAdapter and wrap it via private createFactory using TypeAdapters.newFactory(dateClass, adapter), so the factory matches exactly that date class. Both are final; callers (e.g. GsonBuilder) obtain factories through these methods.

calls: [TypeAdapters.newFactory](../../catalog.json.gz)

<a id="u-8c5cc11e52d1"></a>
### `DefaultDateTypeAdapter.java-defaultdatetypeadapter-class-and-constructors`

`class DefaultDateTypeAdapter<T extends Date> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L56-L66][f1]

TypeAdapter that serializes Date subclasses to formatted strings and parses strings back into the DateType-specific subclass.

Two private constructors build an ordered list of DateFormat deserialization candidates: a pattern-based one uses SimpleDateFormat with Locale.US, plus a default-locale copy when the default locale is not US; a style-based one uses DateFormat.getDateTimeInstance(US), a default-locale copy, and, on Java 9+, a pre-Java-9 US format from PreJava9DateFormatProvider. The first format in the list is also the serialization format. dateType is null-checked. Because SimpleDateFormat captures default TimeZone/Locale at creation, instances are intentionally not cached statically.

calls: [JavaVersion.isJava9OrLater](../../catalog.json.gz), [PreJava9DateFormatProvider.getUsDateTimeFormat](../../catalog.json.gz)

<a id="u-adc983d0aea0"></a>
### `DefaultDateTypeAdapter.java-read-write-deserializetodate`

`@Override public void write(JsonWriter out, Date value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L139-L153][f1]

write emits nullValue for null, otherwise formats the value with dateFormats.get(0) under a synchronized block (DateFormat is not thread-safe) and writes the string.

read returns null on JSON null, else parses the string to a Date and converts via dateType.deserialize. deserializeToDate reads a string, then under synchronization tries each DateFormat in order, restoring each format's TimeZone in a finally and swallowing ParseException to try the next; if all fail it falls back to ISO8601Utils.parse, and on ParseException there throws JsonSyntaxException including the string and the reader's previous path.

calls: [ISO8601Utils.parse](../../catalog.json.gz)

<a id="u-92bb23ccfaeb"></a>
### `DefaultDateTypeAdapter.java-tostring`

`@Override public String toString()` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L76-L79][f1]

toString renders the adapter as SIMPLE_NAME plus the first format's SimpleDateFormat pattern, or that format's class simple name when it is not a SimpleDateFormat.

<a id="u-d6cea4fbdd6c"></a>
### `ISO8601Utils.java-format-overloads`

`public static String format(Date date)` · [gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java:L68-L70][f2]

Format a Date as an ISO-8601 string in a given timezone, optionally with millisecond precision.

The two-argument and one-argument overloads delegate to the three-argument form with the prefetched UTC zone, so they always end in 'Z'. The full version builds a GregorianCalendar in the target zone (Locale.US), zero-pads year/month/day and hh:mm:ss via padInt, appends '.sss' when millis is requested, then appends 'Z' when the zone's offset for that instant is zero, otherwise '+hh:mm' or '-hh:mm' with the absolute offset hours/minutes. Buffer capacity is pre-estimated from these choices. Note the offset check uses the actual offset at the instant, not raw offset used for capacity.

<a id="u-5c7827715844"></a>
### `ISO8601Utils.java-iso8601utils-class`

`class name public final class ISO8601Utils` · [gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java:L38-L40][f2]

Static utility class for fast, GC-friendly formatting and parsing of ISO-8601 date strings, ported from Jackson databind.

Private constructor prevents instantiation; holds a prefetched UTC TimeZone constant used as the default zone for both format and parse.

<a id="u-914c18b49aed"></a>
### `ISO8601Utils.java-parse-helpers`

`private static boolean checkOffset(String value, int offset, char expected)` · [gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java:L319-L321][f2]

Small private helpers used by parse.

checkOffset returns true only when offset is within the string and the char there equals the expected one. parseInt reads digits between two indices using Integer.parseInt-style accumulation (no negatives), throwing NumberFormatException on out-of-range indices or any non-digit. padInt zero-pads an integer to a target length in a StringBuilder. indexOfNonDigit returns the index of the first non-ASCII-digit char at or after offset, or the string length if none.

<a id="u-849ce39b3703"></a>
### `JavaVersion.java-javaversion`

`class JavaVersion` · [gson/src/main/java/com/google/gson/internal/JavaVersion.java:L20-L26][f3]

Utility that determines the current JVM's major Java version once at class initialization and exposes it via two static accessors.

At class load, determineMajorJavaVersion reads the `java.version` system property and parses it; the cached result backs getMajorJavaVersion and the `>= 9` test isJava9OrLater. Parsing first tries parseDotted: split on `.` or `_` with limit 3; if the first segment is `1` and a second segment exists (legacy 1.8 style) the second segment is the major version, otherwise the first segment is. Any NumberFormatException (e.g. a leading non-numeric string like `9-debian`) yields -1 and falls back to extractBeginningInt, which accumulates leading digits and parses them, again returning -1 on failure. If both fail, parseMajorJavaVersion returns 6 as the minimum supported version, so unknown version strings are treated as Java 6 and isJava9OrLater returns false.

<a id="u-73ee672d187b"></a>
### `JavaVersion.java-javaversion-accessors`

`class JavaVersion` · [gson/src/main/java/com/google/gson/internal/JavaVersion.java:L75-L82][f3]

These class regions carry the two public accessors of the JVM-version utility: one returns the cached major version determined once at class initialization from the 'java.version' system property, and the other reports whether that cached value is at least 9.

Both are pure reads of the static field; no re-parsing occurs per call.

<a id="u-6a7724ab5af0"></a>
### `PreJava9DateFormatProvider.java-prejava9dateformatprovider`

`class PreJava9DateFormatProvider` · [gson/src/main/java/com/google/gson/internal/PreJava9DateFormatProvider.java:L23-L24][f4]

Factory that reproduces the pre-Java-9 default US-locale date-time formats as SimpleDateFormat instances.

getUsDateTimeFormat concatenates a date pattern and a time pattern (separated by a space) and builds a SimpleDateFormat with Locale.US. getDatePartOfDateTimePattern maps SHORT/MEDIUM/LONG/FULL to "M/d/yy", "MMM d, yyyy", "MMMM d, yyyy", and "EEEE, MMMM d, yyyy"; getTimePartOfDateTimePattern maps SHORT and MEDIUM to "h:mm a" and "h:mm:ss a", treats FULL and LONG identically as "h:mm:ss a z", and any other style value in either switch throws IllegalArgumentException naming the offending style.

<a id="u-7f60251665e6"></a>
### `GsonBuilder.addDateTypeAdapters`

`private void addDateTypeAdapters(List<TypeAdapterFactory> factories)` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L1043-L1076][f5]

Adds custom date adapters based on configuration: if datePattern is non-null and not blank after trimming, creates pattern-based adapters for Date and, when the java.sql module is supported, Timestamp and sql Date; otherwise if dateStyle or timeStyle differs from DateFormat.DEFAULT, creates style-based adapters the same way; otherwise adds nothing.

Pattern/style selection is mutually exclusive with pattern taking precedence.

<a id="u-f4d4c26b6262"></a>
### `DefaultDateTypeAdapter.create`

`@SuppressWarnings("unchecked") // we use a runtime check to make sure the 'T's equal …` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L66-L74][f1]

DEFAULT_STYLE_FACTORY.create returns a new DefaultDateTypeAdapter<Date> with DEFAULT date/time styles only when the requested raw type is exactly Date.class, otherwise null so other factories can respond.

A new adapter instance is created per call so TimeZone behavior does not depend on class-load time; toString reports the factory name.

<a id="u-7f34211056a1"></a>
### `ISO8601Utils.parse`

`public static Date parse(String date, ParsePosition pos) throws ParseException` · [gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java:L147-L309][f2]

Parse an ISO-8601 date/time string starting at pos's index, returning a Date and advancing pos to where parsing stopped.

Accepts yyyy-MM-dd or yyyyMMdd, optional 'T' time as hh:mm[:ss[.sss]] or hhmm[ss[.sss]], and a mandatory timezone 'Z' or [+-]hh[:mm]. Date-only input (no 'T' and string exhausted) returns a non-lenient GregorianCalendar date immediately. With 'T', hours/minutes are parsed (colons optional); seconds are parsed only if the next char is not 'Z'/'+','-'; leap seconds 60-62 are truncated to 59; fractional seconds parse up to 3 digits, scaling 1- or 2-digit fractions by 100 or 10. Timezone: 'Z' uses UTC; '+'/'-' offsets shorter than 5 chars get '00' appended, '+0000'/'+00:00' maps to UTC, otherwise a 'GMT<offset>' TimeZone is looked up and an IndexOutOfBoundsException is thrown if the resolved zone ID (colons stripped) does not match the requested one. Missing timezone indicator throws IllegalArgumentException; any other char there throws IndexOutOfBoundsException. The final calendar is non-lenient, so out-of-range fields throw. All IndexOutOfBoundsException/IllegalArgumentException are caught and rethrown as a ParseException whose message embeds the quoted input and the cause's message (or cause class name if empty), with the original exception attached via initCause; pos is not advanced on failure.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/util/ISO8601Utils.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/JavaVersion.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/PreJava9DateFormatProvider.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/GsonBuilder.java
