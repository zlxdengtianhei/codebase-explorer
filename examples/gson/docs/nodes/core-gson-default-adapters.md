# Core Gson default adapters

**Capability.** Provides Gson entry point and default adapters for dates, numbers, Object values, and serialization delegation.

Come here for top-level Gson serialization/deserialization and built-in adapter policies. Units cover the Gson facade, builder factory ordering, and date/number/Object adapters.

**Depends on.**

- [Null-safe atomic adapters](null-safe-atomic-adapters.md) · graph-only · 2 edge(s)
- [Basic Java type adapters](basic-java-type-adapters.md) · graph-only · 1 edge(s)
- [Gson serialization facade](gson-serialization-facade.md) · graph-only · 1 edge(s)
- [ISO-8601 date utility](iso-8601-date-utility.md) · graph-only · 1 edge(s)

Parent: [Gson setup and defaults](gson-setup-and-defaults.md)

## Units (25)

<a id="u-92b62bea454c"></a>
### `DefaultDateTypeAdapter.java-datetype`

`class DateType<T extends Date>` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L82-L85][f1]

Abstract nested date type parameterized by Date subclass.

DATE is an identity deserializer for Date. Subclasses implement deserialize(Date). createAdapterFactory(String) and createAdapterFactory(int,int) build a new DefaultDateTypeAdapter and wrap it with TypeAdapters.newFactory for the stored dateClass; createFactory is the private wrapper.

<a id="u-31014d40f336"></a>
### `DefaultDateTypeAdapter.java-default-style-factory`

`class DefaultDateTypeAdapter<T extends Date> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L56-L66][f1]

Anonymous TypeAdapterFactory for Date.class only.

create returns a new adapter using DateType.DATE and DateFormat.DEFAULT for both date and time styles when raw type is Date; otherwise null. toString returns a fixed label.

<a id="u-aa52e0f39437"></a>
### `DefaultDateTypeAdapter.java-defaultdatetypeadapter-class`

`class DefaultDateTypeAdapter<T extends Date> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L55-L56][f1]

Outer date adapter class; captures locale/timezone at construction and serializes/deserializes Date subclasses through a DateType and ordered DateFormat list.

Constructors require non-null DateType; pattern constructor adds US-locale SimpleDateFormat and, when default locale is not US, a default-locale format; style constructor adds US-locale DateFormat, default-locale format when not US, and on Java 9+ a pre-Java-9 US format. First format is used for writing; all formats are tried for reading.

<a id="u-03ce5923a467"></a>
### `Gson.java-gson-core`

`class Gson` · [gson/src/main/java/com/google/gson/Gson.java:L156-L158][f2]

Gson is the thread-safe entry point that serializes and deserializes Java objects through configured TypeAdapterFactory chains and caches.

The no-arg constructor delegates to the default builder. The builder constructor copies configuration and, for the default builder, reuses shared default constructor-constructor, JSON-adapter factory, and factory list; otherwise it creates a ConstructorConstructor, JsonAdapterAnnotationTypeAdapterFactory, and builder-created factories. Instances cache adapters in a concurrent map and use a thread-local map to break cyclic adapter lookups.

<a id="u-f3854e2f26bf"></a>
### `GsonBuilder.java-factory-assembly`

`List<TypeAdapterFactory> createFactories( ConstructorConstructor constructorConstruct…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L926-L1003][f3]

Builds the ordered TypeAdapterFactory list used by Gson and its private helpers.

- createFactories: adds built-in JSON_ELEMENT, ObjectTypeAdapter(objectToNumberStrategy), excluder, user-defined, date adapters, basic platform adapters, long/double/float/number/atomic adapters, optional javaTime, SQL, array/class, collection/map/jsonAdapter/enum/reflective; long adapter comes from longSerializationPolicy.typeAdapter() and is reused for atomic long adapters; returns an unmodifiable trimmed list.
- addUserDefinedAdapters: reverses this.factories and hierarchyFactories separately, appends reversed factories then reversed hierarchy factories; empty lists are skipped.
- addDateTypeAdapters: non-null non-blank datePattern creates DATE adapter with pattern and SQL timestamp/date if supported; else if dateStyle or timeStyle differs from DateFormat.DEFAULT, creates style adapters; else returns without adding. SQL factories only when SqlTypesSupport.SUPPORTS_SQL_TYPES.
- doubleAdapter/floatAdapter: choose non-strict DOUBLE/FLOAT when serializeSpecialFloatingPointValues is true, else DOUBLE_STRICT/FLOAT_STRICT.
- newImmutableList: empty returns emptyList; size one returns singletonList using List.get(0) if List else iterator; otherwise returns unmodifiable list from array.

<a id="u-a0cf646d64de"></a>
### `LongSerializationPolicy.java-long-serialization-policies`

`public enum LongSerializationPolicy` · [gson/src/main/java/com/google/gson/LongSerializationPolicy.java:L29-L38][f4]

Enum defining two long serialization policies.

DEFAULT serializes null as the null singleton and any other value as a numeric primitive; its adapter is the internal long adapter. STRING serializes null the same way and any other value as a string primitive from the value's string form; its adapter is the internal long-as-string adapter. The public serialize method is abstract; the adapter method is package-private abstract.

<a id="u-1beb7f9de7e4"></a>
### `NumberTypeAdapter.java-numbertypeadapter-class-and-constructor`

`class NumberTypeAdapter extends TypeAdapter<Number>` · [gson/src/main/java/com/google/gson/internal/bind/NumberTypeAdapter.java:L32-L34][f5]

NumberTypeAdapter is a TypeAdapter for Number that stores a ToNumberStrategy used when reading numeric tokens.

Its constructor is private and only retains the strategy; factory creation and read/write behavior are separate.

<a id="u-3ee32ee390c6"></a>
### `NumberTypeAdapter.java-numbertypeadapter-factories`

`private static TypeAdapterFactory newFactory(ToNumberStrategy toNumberStrategy)` · [gson/src/main/java/com/google/gson/internal/bind/NumberTypeAdapter.java:L43-L46][f5]

Creates and selects NumberTypeAdapter factories.

newFactory builds one adapter and returns an anonymous factory that supplies it only when the raw type is exactly Number.class, otherwise null. getFactory returns the cached LAZILY_PARSED_NUMBER_FACTORY when the strategy is ToNumberPolicy.LAZILY_PARSED_NUMBER, and otherwise creates a new factory for the supplied strategy.

<a id="u-fd66460acc54"></a>
### `NumberTypeAdapter.java-numbertypeadapter-read-and-write`

`@Override public Number read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/NumberTypeAdapter.java:L62-L76][f5]

Reads a Number according to the configured strategy and writes numbers directly to the JSON writer.

- NULL: consumes nextNull and returns null.
- NUMBER or STRING: delegates to the strategy's readNumber.
- other: throws JsonSyntaxException with the token and reader path.
On write, the value is passed to out.value.

<a id="u-5808c92f3f3f"></a>
### `ObjectTypeAdapter.java-objecttypeadapter-class-and-constructor`

`class ObjectTypeAdapter extends TypeAdapter<Object>` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L40-L42][f6]

ObjectTypeAdapter is a TypeAdapter for values whose static type is Object, storing a Gson instance and a ToNumberStrategy.

Its private constructor only retains those collaborators; factory creation, nesting helpers, read, and write are separate.

<a id="u-a85ff707b5b9"></a>
### `ObjectTypeAdapter.java-objecttypeadapter-factories`

`private static TypeAdapterFactory newFactory(ToNumberStrategy toNumberStrategy)` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L52-L54][f6]

Creates and selects ObjectTypeAdapter factories.

newFactory returns an anonymous factory that creates a new ObjectTypeAdapter only when the raw type is exactly Object.class, otherwise null. getFactory returns the cached DOUBLE_FACTORY when the strategy is ToNumberPolicy.DOUBLE, and otherwise creates a new factory for the supplied strategy.

<a id="u-32e175f2ca0e"></a>
### `SerializationDelegatingTypeAdapter.java-serializationdelegatingtypeadapter`

`class SerializationDelegatingTypeAdapter<T> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/SerializationDelegatingTypeAdapter.java:L22-L27][f7]

SerializationDelegatingTypeAdapter is an abstract TypeAdapter whose serialization may be delegated to another adapter.

getSerializationDelegate returns the adapter used for serialization, which may be this instance or another adapter that can itself also be a SerializationDelegatingTypeAdapter; this class provides no implementation.

<a id="u-096210813d42"></a>
### `ToNumberPolicy.java-long-or-double-policy`

`@Override public Number readNumber(JsonReader in) throws IOException, JsonParseException` · [gson/src/main/java/com/google/gson/ToNumberPolicy.java:L70-L82][f8]

Policy that reads a JSON number as Long when parseable as such, otherwise as Double.

It takes the raw string: if it contains '.', it goes straight to parseAsDouble; otherwise it tries Long.parseLong and falls back to parseAsDouble on NumberFormatException. parseAsDouble uses Double.valueOf; if the result is infinite or NaN and the reader is not lenient, it throws MalformedJsonException (JSON forbids these), and if the string is not parseable at all it throws JsonParseException with the reader's previous path.

<a id="u-3a2f35513b80"></a>
### `ToNumberPolicy.java-simple-tonumberpolicy-constants`

`@Override public Double readNumber(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/ToNumberPolicy.java:L43-L46][f8]

Enum constants implementing ToNumberStrategy for number deserialization.

DOUBLE reads via JsonReader.nextDouble(); LAZILY_PARSED_NUMBER wraps the raw string in a LazilyParsedNumber (default for numbers as Number); BIG_DECIMAL parses the string with NumberLimits.parseBigDecimal, converting NumberFormatException to JsonParseException including the reader's previous path.

<a id="u-467d1decfed2"></a>
### `ToNumberStrategy.java-number-reading-strategy`

`public interface ToNumberStrategy` · [gson/src/main/java/com/google/gson/ToNumberStrategy.java:L60-L69][f9]

Number-reading strategy interface.

Its single method reads one number from a JSON reader, may throw an I/O exception, and returns a non-null number by contract. No implementation is present here.

<a id="u-f0fc3870d3c5"></a>
### `TypeAdapters.java-boxed-unboxed-factory`

`@SuppressWarnings("TypeParameterNaming") public static <TT> TypeAdapterFactory newFac…` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L1020-L1024][f10]

Creates a factory matching either an unboxed or boxed class.

Its create returns the supplied adapter when the requested raw type equals either class, otherwise null; toString reports both classes and adapter.

<a id="u-e3f44a5271e9"></a>
### `TypeAdapters.java-raw-class-factory`

`@SuppressWarnings("TypeParameterNaming") public static <TT> TypeAdapterFactory newFac…` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L1004-L1007][f10]

Creates a factory matching an exact raw class.

Its create returns the supplied adapter when the requested raw type is that class, otherwise null; toString reports type and adapter.

<a id="u-c614e85d01c8"></a>
### `DefaultDateTypeAdapter.deserializeToDate`

`private Date deserializeToDate(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L165-L187][f1]

Parses a string into Date by trying configured DateFormats in order under synchronization, restoring each format's original time zone in finally.

If all fail, tries ISO8601Utils.parse; a final ParseException becomes JsonSyntaxException with the input and previous path.

<a id="u-d57c08724fc7"></a>
### `DefaultDateTypeAdapter.read`

`@Override public T read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L155-L163][f1]

Reads a Date: JSON null consumes null and returns null; otherwise parses via deserializeToDate and converts through the configured DateType.

<a id="u-e6e632fca8df"></a>
### `gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:DefaultDateTypeAdapter.toString`

`@Override public String toString()` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L189-L197][f1]

Returns a diagnostic name using the first DateFormat: SimpleDateFormat contributes its pattern, other formats contribute their class simple name.

<a id="u-360b787319e4"></a>
### `DefaultDateTypeAdapter.write`

`@Override public void write(JsonWriter out, Date value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java:L139-L153][f1]

Writes a Date using the first configured DateFormat.

Null writes JSON null; non-null formats under synchronization on the format list and emits the formatted string.

<a id="u-d55b0d86a0c2"></a>
### `ObjectTypeAdapter.read`

`@Override public Object read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L108-L167][f6]

Reads a JSON value into a List or Map tree, using ArrayList for arrays and LinkedHashMap for objects.

It peeks, starts nesting when possible, and otherwise reads a terminal value. For nesting it iterates with a stack, reading object member names when current is a Map, adding each value to the current List or Map, and descending into nested values; when the current container ends it pops the enclosing container until the root is returned. Reader calls may throw IOException, and readTerminal throws IllegalStateException for an unexpected token; the source does not establish an exclusive failure surface.

**Uncertainties.**

- The source does not establish that readTerminal's IllegalStateException is the only failure surface; reader and strategy calls may also fail.

<a id="u-9650c867d4f1"></a>
### `ObjectTypeAdapter.readTerminal`

`private Object readTerminal(JsonReader in, JsonToken peeked) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L91-L106][f6]

Reads a non-nested JSON value into a plain Java value.

- STRING: returns nextString.
- NUMBER: delegates to the configured ToNumberStrategy.
- BOOLEAN: returns nextBoolean.
- NULL: consumes nextNull and returns null.
- other: throws IllegalStateException with the unexpected token.
Reader and strategy calls may also fail, but the source does not specify their failure surface.

**Uncertainties.**

- The source does not establish that readTerminal's IllegalStateException is the only failure surface; reader and strategy calls may also fail.

<a id="u-6d26339c247e"></a>
### `ObjectTypeAdapter.tryBeginNesting`

`private Object tryBeginNesting(JsonReader in, JsonToken peeked) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L77-L88][f6]

Starts a nested JSON array or object when the peeked token is BEGIN_ARRAY or BEGIN_OBJECT, returning a new ArrayList or LinkedHashMap respectively.

For any other token it returns null without consuming input.

<a id="u-b459182808db"></a>
### `ObjectTypeAdapter.write`

`@Override public void write(JsonWriter out, Object value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L169-L185][f6]

Writes an Object by looking up the adapter for its runtime class and delegating, except that null is written as JSON null and an ObjectTypeAdapter result is written as an empty JSON object.

The empty-object branch prevents recursive delegation when the runtime class still resolves to ObjectTypeAdapter.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/DefaultDateTypeAdapter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/Gson.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/GsonBuilder.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/LongSerializationPolicy.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/NumberTypeAdapter.java
[f6]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java
[f7]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/SerializationDelegatingTypeAdapter.java
[f8]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/ToNumberPolicy.java
[f9]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/ToNumberStrategy.java
[f10]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java
