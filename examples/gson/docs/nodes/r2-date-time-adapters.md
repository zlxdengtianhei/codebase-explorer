# Date and Time Adapters

**Capability.** Serializes date/time values through configurable DateFormat lists with US-locale primary formats and default-locale and pre-JDK9 fallbacks, extends to java.sql types via a compatibility shield, and optionally supplies java.time factories.

Use DefaultDateTypeAdapter and its DateType strategy to see how custom date formats are configured and how deserializeToDate tries formats in order under synchronization. SqlTypesSupport keeps Gson runnable without the java.sql module; SqlTimestampTypeAdapter delegates to the Date adapter.

**Depends on.**

- [Runtime Generic Type Model](r1-type-model.md) · graph-only · 4 edge(s)
- [Internal Support Utilities](r1-internal-support.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Builder and Naming Configuration](r2-configuration.md) · graph-confirmed · 7 edge(s) · GsonBuilder.addDateTypeAdapters installs DefaultDateTypeAdapter factories during configuration.

Parent: [Built-in Type Adapter Factories](r2-default-adapters.md)

## Units (15)

<a id="u-c62e215f5965"></a>
### `DefaultDateTypeAdapter`

`class DefaultDateTypeAdapter<T extends Date> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L55-L66][f1]

Serializes and deserializes Date subclasses via a configurable list of DateFormat objects, per a DateType strategy.

DEFAULT_STYLE_FACTORY is an anonymous factory whose create returns a new DefaultDateTypeAdapter(DateType.DATE, DEFAULT, DEFAULT) only when the raw type is exactly Date.class and null otherwise; its toString is constant. The javadoc warns SimpleDateFormat captures the default Locale/TimeZone at creation, so factories must not be cached statically; the factory builds fresh adapters which Gson then caches. Instances hold dateType and dateFormats, populated by the constructors below.

group: [DefaultDateTypeAdapter.create](r2-date-time-adapters.md#u-f4d4c26b6262)

<a id="u-af642623c40a"></a>
### `DateType`

`class DateType<T extends Date>` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L82-L85][f1]

DateType is an abstract strategy binding a Date subclass to how parsed values are post-processed.

DATE is a singleton for java.util.Date whose deserialize returns its argument unchanged. The protected constructor stores dateClass; the abstract deserialize(Date) lets subclasses convert or specialize the parsed value. createFactory wraps a DefaultDateTypeAdapter through TypeAdapters.newFactory keyed on dateClass; the two final createAdapterFactory methods build factories for an adapter configured either with a date pattern or with date/time style ints.

calls: [typeadapters-factory-helpers](r2-primitive-adapters.md#u-434284f4fe08)

<a id="u-4c2c7d185f99"></a>
### `gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:DefaultDateTypeAdapter (4)`

`private DefaultDateTypeAdapter(DateType<T> dateType, String datePattern)` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L120-L126][f1]

Pattern constructor: requires non-null DateType, adds a SimpleDateFormat for the pattern in Locale.US first (used for serialization), and when the default Locale is not US adds a second SimpleDateFormat with the default Locale as a deserialization fallback.

<a id="u-0fd09a25ee58"></a>
### `gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:DefaultDateTypeAdapter (5)`

`private DefaultDateTypeAdapter(DateType<T> dateType, int dateStyle, int timeStyle)` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L128-L137][f1]

Style constructor: requires non-null DateType, adds DateFormat.getDateTimeInstance(dateStyle, timeStyle, Locale.US) first; when the default Locale is not US adds a default-Locale variant; and when JavaVersion.isJava9OrLater() also adds the PreJava9 US date/time format to compensate for JDK 9+ format changes.

calls: [JavaVersion](r2-infrastructure.md#u-c939eb041613), [PreJava9DateFormatProvider](r1-internal-support.md#u-182f417fef88)

<a id="u-f4d4c26b6262"></a>
### `DefaultDateTypeAdapter.create`

`@SuppressWarnings("unchecked") // we use a runtime check to make sure the 'T's equal …` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L66-L74][f1]

Returns a new DefaultDateTypeAdapter over DateType.DATE with DateFormat.DEFAULT styles only when typeToken.getRawType() equals Date.class, cast to TypeAdapter<T>; for any other raw type, including Date subclasses, it returns null so later factories are consulted.

calls: [type-token-class](r1-type-model.md#u-55a9c25d6eea)

<a id="u-c614e85d01c8"></a>
### `DefaultDateTypeAdapter.deserializeToDate`

`private Date deserializeToDate(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L165-L187][f1]

Reads the next string and tries each DateFormat in order within synchronized(dateFormats); each attempt preserves and restores the format's TimeZone in a finally block so failed parses cannot leak mutated state, and a ParseException is ignored to try the next format.

If none match, ISO8601Utils.parse is attempted; its ParseException is wrapped in a JsonSyntaxException whose message includes the input string and the reader's previous path.

calls: [ISO8601Utils.parse](r1-internal-support.md#u-7f34211056a1)

**Uncertainties.**

- Whether partial parses that consumed input mutate state beyond the restored TimeZone is not established here.

<a id="u-d57c08724fc7"></a>
### `DefaultDateTypeAdapter.read`

`@Override public T read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L155-L163][f1]

If the next token is NULL it consumes the null and returns null; otherwise parses the string via deserializeToDate and passes the result through dateType.deserialize, which may convert or specialize it before return as T.

calls: [DefaultDateTypeAdapter.deserializeToDate](r2-date-time-adapters.md#u-c614e85d01c8)

<a id="u-e6e632fca8df"></a>
### `gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:DefaultDateTypeAdapter.toString`

`@Override public String toString()` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L189-L197][f1]

Returns 'DefaultDateTypeAdapter(<pattern>)' using the first format's pattern when it is a SimpleDateFormat, otherwise the first format's class simple name.

<a id="u-360b787319e4"></a>
### `DefaultDateTypeAdapter.write`

`@Override public void write(JsonWriter out, Date value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L139-L153][f1]

Writes a null Date as JSON null and returns.

Otherwise formats the value with the first DateFormat inside synchronized(dateFormats) because JDK DateFormat is not thread-safe, then writes the string as a JSON value.

<a id="u-ab9af62e5102"></a>
### `SqlTypesSupport`

`class SqlTypesSupport` · [gson/src/main/java/com/google/gson/internal/sql/SqlTypesSupport.java:L38-L65][f2]

Centralizes access to java.sql types so Gson can run without the java.sql module.

A static initializer probes Class.forName("java.sql.Date"): on success SUPPORTS_SQL_TYPES is true and DATE_DATE_TYPE and TIMESTAMP_DATE_TYPE are anonymous DateType subclasses converting a java.util.Date via new java.sql.Date(time) and new Timestamp(time) respectively, the three adapter factories are set to the Sql*TypeAdapter FACTORY constants, and SQL_TYPE_FACTORIES is an unmodifiable list of [TIME, DATE, TIMESTAMP] factories. When the probe fails, all those constants are null and SQL_TYPE_FACTORIES is an empty list. The two deserialize methods are the anonymous-class overrides described above. Private constructor prevents instantiation.

uses: [SqlDateTypeAdapter](r2-date-time-adapters.md#u-f04545e9dcd9), [SqlTimeTypeAdapter](r2-date-time-adapters.md#u-1bd986aeb8d2), [SqlTimestampTypeAdapter](r2-date-time-adapters.md#u-f4433e3a6968)

<a id="u-f04545e9dcd9"></a>
### `SqlDateTypeAdapter`

`class SqlDateTypeAdapter extends TypeAdapter<java.sql.Date>` · [gson/src/main/java/com/google/gson/internal/sql/SqlDateTypeAdapter.java:L39-L43][f3]

TypeAdapter for java.sql.Date, produced only by its FACTORY when the raw type is exactly java.sql.Date.

The adapter holds a per-instance SimpleDateFormat('MMM d, yyyy'), so despite looking stateless it carries DateFormat state and is not thread safe; read and write synchronize on the adapter instance. read consumes a JSON null as null, otherwise reads a string and parses it inside the lock, saving and restoring the format's time zone around the parse; a ParseException becomes JsonSyntaxException with the offending string and the reader's previous path. write emits null for a null value, otherwise formats inside the lock and writes the string. The private constructor means only FACTORY creates instances.

calls: [type-token-class](r1-type-model.md#u-55a9c25d6eea)

<a id="u-1bd986aeb8d2"></a>
### `SqlTimeTypeAdapter`

`class SqlTimeTypeAdapter extends TypeAdapter<Time>` · [gson/src/main/java/com/google/gson/internal/sql/SqlTimeTypeAdapter.java:L40-L44][f4]

TypeAdapter for java.sql.Time, created by its FACTORY only when the raw type is exactly java.sql.Time.

It wraps a SimpleDateFormat('hh:mm:ss a'), so it is stateful and not thread safe; read and write synchronize on this. read returns null for a JSON null token, otherwise parses the string under the lock with the format's original time zone saved and restored in finally; ParseException is converted to JsonSyntaxException carrying the input string and in.getPreviousPath(). write emits a JSON null for null values, otherwise formats under the lock and writes the resulting string. The private constructor restricts creation to the factory.

calls: [type-token-class](r1-type-model.md#u-55a9c25d6eea)

<a id="u-f4433e3a6968"></a>
### `SqlTimestampTypeAdapter`

`class SqlTimestampTypeAdapter extends TypeAdapter<Timestamp>` · [gson/src/main/java/com/google/gson/internal/sql/SqlTimestampTypeAdapter.java:L29-L33][f5]

TypeAdapter for java.sql.Timestamp that delegates timestamp formatting and parsing to Gson's Date adapter.

Its FACTORY matches only raw type Timestamp and obtains the Date adapter via gson.getAdapter(Date.class); other types yield null so another factory can handle them. read delegates and wraps a non-null result in a new Timestamp(date.getTime()), returning null when the delegate returns null. write delegates directly to the Date adapter, preserving Timestamp's millisecond value as a Date.

calls: [Gson.getAdapter](r1-facade-api.md#u-276006924613)

**Uncertainties.**

- Nanosecond precision beyond milliseconds of a Timestamp is not representable via the Date delegate and is silently lost; this follows from the Date conversion but the delegate's exact format is defined elsewhere.

<a id="u-f9f1ea7218e2"></a>
### `TypeAdapters.javaTimeTypeAdapterFactory`

`public static TypeAdapterFactory javaTimeTypeAdapterFactory()` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L980-L990][f6]

Optionally supplies java.time adapter factories without a hard dependency on the java.time-support class.

It reflectively loads com.google.gson.internal.bind.JavaTimeTypeAdapters, instantiates it, casts to FactorySupplier, and returns supplier.get(). Any ReflectiveOperationException or LinkageError — class missing, constructor inaccessible, or initialization failure — results in null, signaling the caller to skip java.time support.

uses: [typeadapters-factory-helpers](r2-primitive-adapters.md#u-434284f4fe08)

**Uncertainties.**

- What FactorySupplier.get returns for the loaded class is defined in code not supplied here.

<a id="u-fbbd026d9201"></a>
### `IntegerFieldsTypeAdapter`

`class IntegerFieldsTypeAdapter<T> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L851-L854][f6]

Abstract TypeAdapter for classes whose JSON form is a fixed set of integer-named fields (Calendar, legacy java.time types).

The constructor fixes the ordered field-name list. read returns null for JSON null, otherwise reads an object: known names fill values[index] via nextLong, unknown names are skipped, and the collected long array is passed to the abstract create. write returns null for a null value, else writes each field name with the corresponding long from the abstract integerValues.

**Notes.**

- contract: Subclasses must implement create(long[]) and integerValues(T); unspecified fields read as 0 because the values array starts zeroed.

**Uncertainties.**

- Behavior when a known field appears twice in the JSON (later value wins via array overwrite) is implied by array assignment, not documented.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/sql/SqlTypesSupport.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/sql/SqlDateTypeAdapter.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/sql/SqlTimeTypeAdapter.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/sql/SqlTimestampTypeAdapter.java
[f6]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java