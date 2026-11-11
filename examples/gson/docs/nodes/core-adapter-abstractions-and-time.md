# Core Adapter Abstractions and Time

**Capability.** Houses the TypeAdapter base class, java.time and java.sql date/time adapters, and adapter lookup entry points.

Readers implementing custom adapters or adding temporal type support should look here. The module includes the nullSafe wrapper, tree conversion, java.time adapters composed from integer-field adapters, and optional java.sql date/time adapters.

**Depends on.**

- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-only · 4 edge(s)
- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) · graph-only · 2 edge(s)
- [In-memory tree writer](in-memory-tree-writer.md) · graph-only · 1 edge(s)
- [Tree Element Bridge](tree-element-bridge.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Gson Configuration Assembly](gson-configuration-assembly.md) · graph-only · 2 edge(s)
- [Annotations and Module Declaration](annotations-and-module-declaration.md) · graph-only · 1 edge(s)

Parent: [Adapter Abstractions and Dates](adapter-abstractions-and-dates.md)

## Units (20)

<a id="u-d8f2550a0d29"></a>
### `JavaTimeTypeAdapters.java-factory-supplier-entry`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L43-L46][f1]

Supplier that hands the shared java.time TypeAdapterFactory to TypeAdapters; the single get method just returns the static JAVA_TIME_FACTORY.

<a id="u-4a13354deaef"></a>
### `JavaTimeTypeAdapters.java-integer-fields-java-time-adapters`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L49-L53][f1]

Anonymous IntegerFieldsTypeAdapter subclasses freezing the JDK-21 reflective representation of Duration, Instant, LocalDate, LocalTime, MonthDay, Period, Year and YearMonth as JSON objects of named integer fields.

Each create(long[]) rebuilds the value from the read integers (Duration.ofSeconds, Instant.ofEpochSecond, LocalDate.of with toIntExact narrowing, LocalTime.of, MonthDay.of, Period.of, Year.of, YearMonth.of); each integerValues extracts the same components on write. toIntExact throws ArithmeticException if a JSON integer exceeds int range, and the java.time factories throw DateTimeException for out-of-range components, so malformed input surfaces as runtime exceptions rather than JsonSyntaxException. Field names and order are fixed per type (e.g. Duration: seconds, nanos; LocalTime: hour, minute, second, nano).

<a id="u-4dc0092c7a58"></a>
### `JavaTimeTypeAdapters.java-java-time-factory`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> typeToken)` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L395-L439][f1]

TypeAdapterFactory dispatching java.time types to the adapters above.

It first returns null unless the raw type's name starts with "java.time." (avoids class loading otherwise), then an if/else chain on rawType selects the shared static adapters or builds gson-dependent ones (LocalDateTime, OffsetDateTime, OffsetTime, ZonedDateTime). ZoneId and ZoneOffset both map to ZONE_ID deliberately by exact class equality (not isAssignableFrom) so the non-public ZoneRegion is not captured during runtime-type checks and a user-registered ZoneId adapter keeps precedence. Unmatched java.time types yield null (no adapter).

<a id="u-6564ad02523c"></a>
### `JavaTimeTypeAdapters.java-localdatetime-adapter`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L110-L113][f1]

Builds a nullSafe LocalDateTime adapter composing the registered LocalDate and LocalTime adapters (fetched via gson.getAdapter, so user overrides win).

Read expects an object with "date" and "time" members, skipping unknown names; a missing member triggers JsonSyntaxException via requireNonNullField, and duplicate members let the last one win. Write emits exactly {"date":...,"time":...} using value.toLocalDate()/toLocalTime().

<a id="u-8e70e06ea014"></a>
### `JavaTimeTypeAdapters.java-offsetdatetime-and-offsettime-adapters`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L163-L166][f1]

Builds nullSafe adapters composing the LocalDateTime/LocalTime adapter with the ZoneOffset adapter.

OffsetDateTime reads "dateTime" and "offset" (unknown names skipped, missing member → JsonSyntaxException from requireNonNullField, last duplicate wins) and writes {"dateTime","offset"}; OffsetTime reads/writes {"time","offset"} the same way. Values are assembled with OffsetDateTime.of / OffsetTime.of from the non-null parts.

<a id="u-67795c80173a"></a>
### `JavaTimeTypeAdapters.java-zoneddatetime-adapter`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L337-L340][f1]

Builds a nullSafe adapter composing the LocalDateTime, ZoneOffset and ZoneId adapters.

Read expects "dateTime", "offset" and "zone" members (unknown names skipped; any missing member throws JsonSyntaxException via requireNonNullField; duplicates let the last value win) and reconstructs with ZonedDateTime.ofInstant(localDateTime, offset, zone). Write has an explicit null fast path (redundant under nullSafe) then emits {"dateTime","offset","zone"} from toLocalDateTime/getOffset/getZone.

<a id="u-59815bc7d9ca"></a>
### `JavaTimeTypeAdapters.java-zoneid-adapter`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L284-L294][f1]

NullSafe adapter distinguishing ZoneOffset from other ZoneIds (ZoneRegion) for compatibility with the old reflection-based format.

Read accepts an object with "id" (string → ZoneId.of) or "totalSeconds" (int → ZoneOffset.ofTotalSeconds), skipping other names; if both appear id wins; if neither, throws JsonSyntaxException naming the previous path. Write emits {"totalSeconds": n} for ZoneOffset instances, otherwise {"id": zoneId.getId()}. ZoneId.of / ZoneOffset.ofTotalSeconds can throw runtime exceptions for invalid ids or out-of-range seconds.

<a id="u-230571bab25f"></a>
### `SqlDateTypeAdapter.java-sqldatetypeadapter`

`class SqlDateTypeAdapter extends TypeAdapter<java.sql.Date>` · [gson/src/main/java/com/google/gson/internal/sql/SqlDateTypeAdapter.java:L39-L43][f2]

TypeAdapter for java.sql.Date using a shared, non-thread-safe SimpleDateFormat 'MMM d, yyyy'.

The static FACTORY returns a new adapter instance only when the requested raw type is exactly java.sql.Date, else null. read returns null for JSON null; otherwise it reads a string and, under synchronization on the adapter, saves the format's timezone, parses, converts the util Date to java.sql.Date, and restores the timezone in finally; a ParseException becomes a JsonSyntaxException quoting the string and the reader's previous path. write emits null for a null value, else formats under synchronization and writes the string. The class is stateful through the DateFormat, hence the locking.

<a id="u-6d132abb7775"></a>
### `SqlTimeTypeAdapter.java-sqltimetypeadapter`

`class SqlTimeTypeAdapter extends TypeAdapter<Time>` · [gson/src/main/java/com/google/gson/internal/sql/SqlTimeTypeAdapter.java:L40-L44][f3]

TypeAdapter for java.sql.Time using a shared SimpleDateFormat 'hh:mm:ss a'.

The static FACTORY matches only raw type java.sql.Time. read returns null on JSON null; otherwise parses the string under synchronization, saving and restoring the format's timezone in finally, and wraps a ParseException in a JsonSyntaxException with the input and previous path. write emits null for null, else formats under synchronization and writes the result. Same statefulness/thread-safety rationale as the Date adapter.

<a id="u-dccc9b84b3dc"></a>
### `SqlTimestampTypeAdapter.java-sqltimestamptypeadapter`

`class SqlTimestampTypeAdapter extends TypeAdapter<Timestamp>` · [gson/src/main/java/com/google/gson/internal/sql/SqlTimestampTypeAdapter.java:L29-L33][f4]

TypeAdapter for java.sql.Timestamp that delegates entirely to a Date TypeAdapter supplied at construction.

The static FACTORY matches only raw type Timestamp and obtains the Date adapter via gson.getAdapter(Date.class), so timestamp formatting/parsing follows the user's configured Date format. read delegates and converts a non-null Date to a Timestamp (null passes through as null); write delegates directly, letting the Date adapter handle null. No synchronization is needed here since it holds no mutable format state.

<a id="u-b682576fd46b"></a>
### `SqlTypesSupport.java-sqltypessupport`

`class SqlTypesSupport` · [gson/src/main/java/com/google/gson/internal/sql/SqlTypesSupport.java:L38-L41][f5]

Static holder that isolates Gson from an absent java.sql module.

A static initializer probes Class.forName("java.sql.Date"): if present, SUPPORTS_SQL_TYPES is true and it builds DateType instances for java.sql.Date and Timestamp (each deserializing a util Date by copying its millis), exposes the three adapter factories, and publishes an unmodifiable SQL_TYPE_FACTORIES list ordered Time, Date, Timestamp; if the probe throws ClassNotFoundException, the flag is false, all factory/DateType constants are null, and SQL_TYPE_FACTORIES is an empty list. Per the class contract, no ClassNotFoundException escapes. Private constructor; all state is static final.

<a id="u-37280fc94386"></a>
### `TypeAdapter.java-fromjson`

`public final T fromJson(Reader in) throws IOException` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L211-L214][f6]

Deserializes JSON to T.

The Reader overload wraps the input in a default-configured JsonReader (LEGACY_STRICT) and delegates to read; the String overload wraps the string in a StringReader and reuses it. Neither checks for trailing or multiple top-level values, so extra data is silently ignored. fromJsonTree wraps a JsonElement in a JsonTreeReader, converts IOException from read into JsonIOException, and accepts JsonNull input.

<a id="u-460b95ad335d"></a>
### `TypeAdapter.java-nullsafetypeadapter`

`class NullSafeTypeAdapter extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L299-L300][f6]

Private inner class wrapping the outer adapter.

write emits nullValue for a null value, otherwise delegates to the outer write. read consumes a JSON null token (peek == NULL, then nextNull) and returns null, otherwise delegates to the outer read. toString names the wrapper and includes the wrapped adapter.

<a id="u-429a346c6234"></a>
### `TypeAdapter.java-tojson`

`public final void toJson(Writer out, T value) throws IOException` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L143-L146][f6]

Serializes value to JSON.

The Writer overload wraps out in a default-configured JsonWriter and delegates to write, propagating IOException. The String overload builds into a StringBuilder via Streams.writerForAppendable and converts any IOException from write into a JsonIOException.

<a id="u-e906d1d9cbdd"></a>
### `TypeAdapter.java-typeadapter-abstract-contract`

`class TypeAdapter<T>` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L122-L124][f6]

Abstract base class converting Java objects of type T to and from JSON.

Subclasses implement write(JsonWriter, T), which must emit exactly one JSON value (including handling or delegating null), and read(JsonReader), which must consume exactly one value and return the converted object (possibly null). Adapters are expected to be stateless and thread-safe; failing to read/write exactly one value can crash the application.

<a id="u-34e8a2faa3d0"></a>
### `TypeAdapter.java-typeadapter-javadoc-wrapper-regions`

`class TypeAdapter<T>` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L124-L131][f6]

These class regions contain only the Javadoc surrounding members that already have their own units (abstract write, toJson(Writer), toJson(String) via Streams.writerForAppendable, toJsonTree, abstract read, fromJson(Reader), fromJson(String), fromJsonTree, nullSafe); they add no separate behavior.

The Javadoc pins contracts worth knowing: write/read must each convert exactly one value; toJson(Writer) and the Reader-based fromJson use a default-configured JsonWriter/JsonReader, so customization requires calling write/read directly; the fromJson variants do not reject multiple top-level elements or trailing data; toJson(String), toJsonTree and fromJsonTree wrap any IOException in JsonIOException; toJsonTree may return JsonNull and fromJsonTree accepts JsonNull input.

<a id="u-0f01c122fbe8"></a>
### `gson/src/main/java/com/google/gson/Gson.java:Gson.getAdapter`

`public <T> TypeAdapter<T> getAdapter(Class<T> type)` · [gson/src/main/java/com/google/gson/Gson.java:L407-L409][f7]

Returns the adapter for a raw class by converting it to a TypeToken and delegating to the main getAdapter; inherits its caching and IllegalArgumentException-on-no-match behavior.

<a id="u-c7dd40fc556f"></a>
### `TypeAdapter.nullSafe`

`public final TypeAdapter<T> nullSafe()` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L292-L297][f6]

Returns a null-tolerant wrapper unless this adapter is already a NullSafeTypeAdapter, in which case it returns itself to avoid double wrapping.

<a id="u-1c904480f4f6"></a>
### `TypeAdapter.toJsonTree`

`public final JsonElement toJsonTree(T value)` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L179-L187][f6]

Converts value into a JsonElement tree by writing through a JsonTreeWriter and returning its result; any IOException from write is wrapped in a JsonIOException.

The result may be JsonNull.

<a id="u-52ebee1d0241"></a>
### `JavaTimeTypeAdapters.requireNonNullField`

`private static <T> T requireNonNullField(T field, String fieldName, JsonReader reader)` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L442-L448][f1]

Throws JsonSyntaxException reporting the missing field name and the reader's previous path when a required object member was absent; otherwise returns the value unchanged.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/sql/SqlDateTypeAdapter.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/sql/SqlTimeTypeAdapter.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/sql/SqlTimestampTypeAdapter.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/sql/SqlTypesSupport.java
[f6]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/TypeAdapter.java
[f7]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/Gson.java
