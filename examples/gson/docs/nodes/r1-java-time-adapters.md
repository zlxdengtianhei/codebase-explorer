# java.time Adapters

**Capability.** Composite, null-safe adapters for java.time types encoded compatibly with the JDK's reflective field layout, all funneled through one shared JAVA_TIME_FACTORY; composed adapters resolve sub-adapters via Gson.getAdapter and enforce required fields on deserialization.

Use this subtree for java.time serialization questions: which adapter handles which type, how composite types (OffsetDateTime, ZonedDateTime) compose from local and zone adapters, and how missing-field errors are reported.

**Depends on.**

- [TypeAdapter Framework](r1-adapter-framework.md) · graph-confirmed · 4 edge(s)
- [Built-in Type Adapters](r1-builtin-adapters.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-java-time-adapters ` → ` r1-builtin-adapters `)
- [Gson Facade and Conversion API](r1-facade-api.md) · graph-confirmed · 7 edge(s) · Composite java.time adapters resolve their sub-adapters via Gson.getAdapter.

Parent: [Built-in Type Adapters](r1-builtin-adapters.md)

## Units (9)

<a id="u-0a49ab62d7bc"></a>
### `javaTimeTypeAdapters-integer-field-adapters`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L49-L53][f1]

Defines eight TypeAdapter constants for Duration, Instant, LocalDate, LocalTime, MonthDay, Period, Year and YearMonth, each extending the (external) IntegerFieldsTypeAdapter base so the value is written as a JSON object of named integer fields matching the JDK 21 reflective field layout.

Each subclass supplies two hooks: create(long[]) rebuilds the value from the read integers, and integerValues(T) extracts them for writing. LocalDate, LocalTime, MonthDay, Period and YearMonth narrow longs with Math.toIntExact, so an out-of-int-range stored value during reconstruction surfaces as ArithmeticException; Duration and Instant use long seconds/nanos directly, and Instant extraction is annotated to allow getEpochSecond/getNano. Field-name matching, missing-field handling and null handling live in IntegerFieldsTypeAdapter, which is not part of this file.

**Uncertainties.**

- IntegerFieldsTypeAdapter's read/write loop, JSON member names per constant, null handling and exception mapping are not in the supplied source; behavior beyond the create/integerValues hooks is inferred from the class name and usage.

<a id="u-e3de4f5a1258"></a>
### `javaTimeTypeAdapters-javaTimeFactory`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L391-L395][f1]

Defines JAVA_TIME_FACTORY, a TypeAdapterFactory that maps raw types to java.time adapters.

Its create first reads the raw type; if the class name does not start with 'java.time.' it returns null immediately so the java.time classes are not loaded unnecessarily. Otherwise it selects an adapter by exact raw-type identity: Duration, Instant, LocalDate, LocalTime via constants; LocalDateTime, OffsetDateTime, OffsetTime, ZonedDateTime via factory methods taking Gson; and both ZoneId and ZoneOffset map to ZONE_ID. Deliberately not using isAssignableFrom for ZoneId keeps the non-public ZoneRegion from matching in TypeAdapterRuntimeTypeWrapper's runtime-type check, preserving user-registered ZoneId adapters. Any other java.time raw type yields null, so the factory declines it.

calls: [type-token-class](r1-type-model.md#u-55a9c25d6eea), [javaTimeTypeAdapters-localDateTime](r1-java-time-adapters.md#u-a4a2efd9265d), [javaTimeTypeAdapters-offsetDateTime](r1-java-time-adapters.md#u-db3846d0191f), [javaTimeTypeAdapters-offsetTime](r1-java-time-adapters.md#u-85d9c539db25), [javaTimeTypeAdapters-zonedDateTime](r1-java-time-adapters.md#u-cea5f806c146)

**Uncertainties.**

- ZoneOffset instances whose raw type is exactly ZoneOffset.class get the ZONE_ID adapter; behavior for subclasses of ZoneId other than ZoneOffset is not covered by the exact-identity checks.

<a id="u-a4a2efd9265d"></a>
### `javaTimeTypeAdapters-localDateTime`

`private static TypeAdapter<LocalDateTime> localDateTime(Gson gson)` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L113-L117][f1]

Builds a null-safe TypeAdapter for LocalDateTime composed of the Gson-resolved LocalDate and LocalTime adapters.

read consumes a JSON object, reading the 'date' member with the LocalDate adapter and 'time' with the LocalTime adapter; any other member is skipped with skipValue. After endObject both fields must be present, else requireNonNullField throws JsonSyntaxException naming the field and the previous path. write emits an object with 'date' then 'time'. The result is wrapped with nullSafe, so a JSON null yields null and a null value writes null.

calls: [JavaTimeTypeAdapters.requireNonNullField](r1-java-time-adapters.md#u-52ebee1d0241); uses: [javaTimeTypeAdapters-integer-field-adapters](r1-java-time-adapters.md#u-0a49ab62d7bc)

**Uncertainties.**

- gson.getAdapter may return a user-registered LocalDate/LocalTime adapter instead of the constants here; that resolution happens in Gson, not in this file.

<a id="u-db3846d0191f"></a>
### `javaTimeTypeAdapters-offsetDateTime`

`private static TypeAdapter<OffsetDateTime> offsetDateTime(Gson gson)` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L166-L170][f1]

Builds a null-safe TypeAdapter for OffsetDateTime from a locally constructed LocalDateTime adapter and the Gson-resolved ZoneOffset adapter.

read consumes a JSON object, reading 'dateTime' with the LocalDateTime adapter and 'offset' with the ZoneOffset adapter, skipping unknown members, then requires both or throws JsonSyntaxException via requireNonNullField. write emits 'dateTime' then 'offset'.

calls: [javaTimeTypeAdapters-localDateTime](r1-java-time-adapters.md#u-a4a2efd9265d), [JavaTimeTypeAdapters.requireNonNullField](r1-java-time-adapters.md#u-52ebee1d0241)

<a id="u-85d9c539db25"></a>
### `javaTimeTypeAdapters-offsetTime`

`private static TypeAdapter<OffsetTime> offsetTime(Gson gson)` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L207-L211][f1]

Builds a null-safe TypeAdapter for OffsetTime from the Gson-resolved LocalTime and ZoneOffset adapters.

read consumes a JSON object, reading 'time' and 'offset' members, skipping others, and requires both fields afterwards or throws JsonSyntaxException through requireNonNullField. write emits 'time' then 'offset'.

calls: [JavaTimeTypeAdapters.requireNonNullField](r1-java-time-adapters.md#u-52ebee1d0241)

<a id="u-c00b3e1bc88e"></a>
### `javaTimeTypeAdapters-zoneId`

`class JavaTimeTypeAdapters implements TypeAdapters.FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L284-L294][f1]

Defines ZONE_ID, a null-safe adapter encoding a ZoneId compatibly with the reflective JDK representation.

read reads a JSON object: an 'id' string is stored, a 'totalSeconds' int is stored, other members are skipped. After endObject, if id is non-null it returns ZoneId.of(id); otherwise if totalSeconds is non-null it returns ZoneOffset.ofTotalSeconds(totalSeconds); otherwise it throws JsonSyntaxException with the previous path. write branches on the value's runtime type: a ZoneOffset is written as an object with 'totalSeconds'; anything else (a ZoneRegion) is written as an object with 'id'. The class comment explains this dual encoding exists because ZoneRegion is non-public.

**Uncertainties.**

- If both 'id' and 'totalSeconds' are present, 'id' wins; no other conflict validation is visible in the source.

<a id="u-cea5f806c146"></a>
### `javaTimeTypeAdapters-zonedDateTime`

`private static TypeAdapter<ZonedDateTime> zonedDateTime(Gson gson)` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L340-L345][f1]

Builds a null-safe TypeAdapter for ZonedDateTime from a local LocalDateTime adapter plus Gson-resolved ZoneOffset and ZoneId adapters.

read consumes a JSON object reading 'dateTime', 'offset' and 'zone', skipping others, then requires all three via requireNonNullField and returns ZonedDateTime.ofInstant(dateTime, offset, zone). write handles a null value explicitly with out.nullValue() before the nullSafe wrapper applies, otherwise writes 'dateTime', 'offset' and 'zone'.

calls: [javaTimeTypeAdapters-localDateTime](r1-java-time-adapters.md#u-a4a2efd9265d); uses: [javaTimeTypeAdapters-zoneId](r1-java-time-adapters.md#u-c00b3e1bc88e)

<a id="u-bb3036ab80a7"></a>
### `JavaTimeTypeAdapters.get`

`@Override public TypeAdapterFactory get()` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L46-L49][f1]

Returns this factory supplier's TypeAdapterFactory, always the shared JAVA_TIME_FACTORY constant, so all java.time support funnels through one factory instance.

uses: [javaTimeTypeAdapters-javaTimeFactory](r1-java-time-adapters.md#u-e3de4f5a1258)

<a id="u-52ebee1d0241"></a>
### `JavaTimeTypeAdapters.requireNonNullField`

`private static <T> T requireNonNullField(T field, String fieldName, JsonReader reader)` · [gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java:L442-L448][f1]

Generic null check for deserialized optional members: if the parsed field is null it throws JsonSyntaxException reporting the missing field's name and the reader's previous path; otherwise it returns the field unchanged.

Used by the composite java.time adapters to enforce required members after reading an object.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JavaTimeTypeAdapters.java