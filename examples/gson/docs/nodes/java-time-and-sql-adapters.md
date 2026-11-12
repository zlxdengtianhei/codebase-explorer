# Java time and SQL adapters

**Capability.** Provides TypeAdapter factories and adapters for java.time and java.sql date/time values.

Come here when serializing or deserializing temporal values with Gson. It contains java.time factory wiring, null-safe composite adapters, SQL date/time adapters, and SQL availability detection.

**Depends on.**

- [Core configuration and adapters](core-configuration-and-adapters.md) · graph-confirmed · 4 edge(s)
- [Serialization facade and writing](serialization-facade-and-writing.md) · graph-confirmed · 8 edge(s)
- [Gson serialization facade](gson-serialization-facade.md) · graph-only · 8 edge(s)
- [Null-safe atomic adapters](null-safe-atomic-adapters.md) · graph-only · 4 edge(s)

Parent: [Gson JSON library](gson-json-library.md)

## Units (13)

<a id="u-77ea11ac043d"></a>
### `JavaTimeTypeAdapters.java-integer-field-java-time-adapters`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L49-L53][f1]

These anonymous IntegerFieldsTypeAdapter subclasses convert java.time values to and from long arrays using configured field names.

Duration and Instant use seconds/nanos; LocalDate uses year/month/day; LocalTime uses hour/minute/second/nano; MonthDay uses month/day; Period uses years/months/days; Year uses year; YearMonth uses year/month. The create methods use toIntExact for int-valued components, so overflow throws ArithmeticException. The base adapter's read/write loop is not in the supplied source, so exact JSON object field order and malformed-input exception surface are unproven.

**Uncertainties.**

- The base IntegerFieldsTypeAdapter read/write loop is not in the supplied source, so exact JSON object field order and malformed-input exception surface are unproven.

<a id="u-4dc0092c7a58"></a>
### `JavaTimeTypeAdapters.java-java-time-factory`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L391-L395][f1]

TypeAdapterFactory for java.time types.

create returns null immediately when the raw type name does not start with 'java.time.' to avoid loading those classes. For exact matches it returns the corresponding adapter, constructing LocalDateTime, OffsetDateTime, OffsetTime, and ZonedDateTime adapters on demand; ZoneId and ZoneOffset both use the ZoneId adapter, and other types return null. It deliberately does not match ZoneId subclasses to avoid intercepting the non-public ZoneRegion runtime type.

<a id="u-2b77e36a74d7"></a>
### `JavaTimeTypeAdapters.java-java-time-factory-supplier`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L43-L46][f1]

JavaTimeTypeAdapters is a factory supplier that exposes a TypeAdapterFactory for java.time types, freezing the reflective JSON representation without reflection.

<a id="u-6564ad02523c"></a>
### `JavaTimeTypeAdapters.java-localdatetime-adapter`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L110-L113][f1]

Builds a null-safe adapter for LocalDateTime using the Gson adapters for LocalDate and LocalTime.

read begins an object, reads 'date' and 'time', skips unknown fields, then requires both fields non-null and constructs LocalDateTime.of. A missing field leaves its slot null and requireNonNullField throws JsonSyntaxException; a present null depends on the nested LocalDate/LocalTime adapter's null handling, which is not in the supplied source. write emits an object with 'date' and 'time'.

**Uncertainties.**

- Present null for 'date' or 'time' depends on the nested IntegerFieldsTypeAdapter null handling, which is not in the supplied source.

<a id="u-70743b3cc9d7"></a>
### `JavaTimeTypeAdapters.java-offsetdatetime-adapter`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L163-L166][f1]

Builds a null-safe adapter for OffsetDateTime using the LocalDateTime adapter and the Gson ZoneOffset adapter.

read begins an object, reads 'dateTime' and 'offset', skips unknown fields, then requires both non-null and calls OffsetDateTime.of. Missing fields and present nulls both leave slots null and trigger JsonSyntaxException from requireNonNullField because the nested adapters are null-safe. write emits 'dateTime' and 'offset'.

<a id="u-92f88e8eeb6b"></a>
### `JavaTimeTypeAdapters.java-offsettime-adapter`

`private static TypeAdapter<OffsetTime> offsetTime(Gson gson)` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L207-L211][f1]

Builds a null-safe adapter for OffsetTime using the Gson LocalTime and ZoneOffset adapters.

read begins an object, reads 'time' and 'offset', skips unknown fields, then requires both non-null and calls OffsetTime.of. A missing field triggers JsonSyntaxException; a present null for 'offset' also triggers because the ZoneOffset adapter is null-safe, while a present null for 'time' depends on the LocalTime adapter's null handling, which is not in the supplied source. write emits 'time' and 'offset'.

**Uncertainties.**

- Present null for 'time' depends on the LocalTime adapter's null handling, which is not in the supplied source.

<a id="u-67795c80173a"></a>
### `JavaTimeTypeAdapters.java-zoneddatetime-adapter`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L337-L340][f1]

Builds a null-safe adapter for ZonedDateTime using the LocalDateTime, ZoneOffset, and ZoneId adapters.

read begins an object, reads 'dateTime', 'offset', and 'zone', skips unknown fields, then requires all three non-null and calls ZonedDateTime.ofInstant. Missing fields and present nulls both trigger JsonSyntaxException from requireNonNullField because the nested adapters are null-safe. write emits 'dateTime', 'offset', and 'zone'.

<a id="u-59815bc7d9ca"></a>
### `JavaTimeTypeAdapters.java-zoneid-adapter`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L284-L294][f1]

Null-safe adapter for ZoneId.

read begins an object, reads 'id' as a string and 'totalSeconds' as an int, skips unknown fields, then returns ZoneId.of(id) if id was seen, else ZoneOffset.ofTotalSeconds(totalSeconds) if totalSeconds was seen, else throws JsonSyntaxException with the previous path. write emits totalSeconds for a ZoneOffset and id otherwise.

<a id="u-9d27aa518566"></a>
### `SqlDateTypeAdapter.java-sql-date-adapter-and-factory`

`class SqlDateTypeAdapter extends TypeAdapter<java.sql.Date>` · [gson/src/main/java/com/google/gson/internal/sql/SqlDateTypeAdapter.java:L39-L43][f2]

Adapts java.sql.Date to and from JSON using a shared SimpleDateFormat with pattern 'MMM d, yyyy'.

The factory returns a new adapter only when the raw type is exactly java.sql.Date, otherwise null. read returns null for JSON null; otherwise it reads a string, synchronizes on the adapter, saves the format's time zone, parses, returns a new java.sql.Date from the parsed millis, and restores the saved time zone in finally. A ParseException becomes JsonSyntaxException with the input and previous path. write emits null for null, otherwise synchronizes while formatting and writes the string. Synchronization serializes access to the shared DateFormat.

<a id="u-6de79f843a51"></a>
### `SqlTimeTypeAdapter.java-sql-time-adapter-and-factory`

`class SqlTimeTypeAdapter extends TypeAdapter<Time>` · [gson/src/main/java/com/google/gson/internal/sql/SqlTimeTypeAdapter.java:L40-L44][f3]

Adapts java.sql.Time to and from JSON using a shared SimpleDateFormat with pattern 'hh:mm:ss a'.

The factory returns a new adapter only when the raw type is exactly java.sql.Time, otherwise null. read returns null for JSON null; otherwise it reads a string, synchronizes on the adapter, saves the format's time zone, parses, returns a new Time from the parsed millis, and restores the saved time zone in finally. A ParseException becomes JsonSyntaxException with the input and previous path. write emits null for null, otherwise synchronizes while formatting and writes the string. Synchronization serializes access to the shared DateFormat.

<a id="u-a07e97e81092"></a>
### `SqlTimestampTypeAdapter.java-sql-timestamp-adapter-and-factory`

`class SqlTimestampTypeAdapter extends TypeAdapter<Timestamp>` · [gson/src/main/java/com/google/gson/internal/sql/SqlTimestampTypeAdapter.java:L29-L33][f4]

Adapts java.sql.Timestamp by delegating to a Date adapter.

The factory returns a new adapter only when the raw type is exactly java.sql.Timestamp, obtaining the Date adapter from Gson; otherwise it returns null. read delegates to the Date adapter and returns null when that result is null, otherwise wraps the millis in a new Timestamp. write delegates directly to the Date adapter, so null handling and JSON shape follow that adapter.

<a id="u-638bef5869ab"></a>
### `SqlTypesSupport.java-sql-type-support-detection`

`class SqlTypesSupport` · [gson/src/main/java/com/google/gson/internal/sql/SqlTypesSupport.java:L38-L41][f5]

Detects whether java.sql types are available and exposes the corresponding date types, adapter factories, and factory list.

The static initializer tries Class.forName('java.sql.Date'); ClassNotFoundException sets SUPPORTS_SQL_TYPES to false, while success sets it true. When true, it creates DateType instances for java.sql.Date and Timestamp whose deserialize methods wrap the input Date millis, assigns the three adapter factories, and builds an unmodifiable list ordered TIME, DATE, TIMESTAMP. When false, SUPPORTS_SQL_TYPES is false, the date-type and factory constants are null, and the factory list is empty. No ClassNotFoundException escapes.

<a id="u-52ebee1d0241"></a>
### `JavaTimeTypeAdapters.requireNonNullField`

`private static <T> T requireNonNullField(T field, String fieldName, JsonReader reader)` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L442-L448][f1]

Returns the field if non-null; otherwise throws JsonSyntaxException naming the missing field and the reader's previous path.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/sql/SqlDateTypeAdapter.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/sql/SqlTimeTypeAdapter.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/sql/SqlTimestampTypeAdapter.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/sql/SqlTypesSupport.java
