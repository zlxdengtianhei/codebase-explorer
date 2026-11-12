# Gson builder configuration

**Capability.** Accumulates Gson settings and registers custom tree/type adapters, producing configured Gson instances.

Use when configuring Gson or registering serializer/deserializer adapters. Units show mutable builder setters, validation, factory registration, and tree adapter bridging.

**Depends on.**

- [Generic type reflection](generic-type-reflection.md) · graph-only · 4 edge(s)
- [Stream serialization helpers](stream-serialization-helpers.md) · graph-only · 2 edge(s)
- [Gson serialization facade](gson-serialization-facade.md) · graph-only · 1 edge(s)
- [JsonElement tree base](jsonelement-tree-base.md) · graph-only · 1 edge(s)

Parent: [Gson setup and defaults](gson-setup-and-defaults.md)

## Units (27)

<a id="u-0fa0e7b041b9"></a>
### `GsonBuilder.java-boolean-flag-setters`

`@CanIgnoreReturnValue public GsonBuilder generateNonExecutableJson()` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L242-L246][f1]

These setters flip one boolean field and return this; they perform no validation and throw no exception.

- generateNonExecutableJson: sets true.
- serializeNulls: sets true.
- enableComplexMapKeySerialization: sets true.
- disableHtmlEscaping: sets escapeHtmlChars false.
- serializeSpecialFloatingPointValues: sets true.
- disableJdkUnsafe: sets useJdkUnsafe false.

<a id="u-d1e201ae64d5"></a>
### `GsonBuilder.java-date-style-setters`

`@Deprecated @CanIgnoreReturnValue public GsonBuilder setDateFormat(int dateStyle)` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L672-L678][f1]

checkDateFormatStyle accepts 0 through 3 and throws IllegalArgumentException otherwise.

- one-arg setDateFormat: stores dateStyle, clears datePattern, leaves timeStyle unchanged.
- two-arg setDateFormat: stores dateStyle then timeStyle, clears datePattern; if timeStyle is invalid, dateStyle has already been updated before the throw.

<a id="u-fb2a532ec476"></a>
### `GsonBuilder.java-field-naming`

`@CanIgnoreReturnValue public GsonBuilder setFieldNamingPolicy(FieldNamingPolicy namin…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L412-L415][f1]

setFieldNamingPolicy delegates to setFieldNamingStrategy; setFieldNamingStrategy requires non-null and stores it; null throws NPE.

<a id="u-8b842683df52"></a>
### `GsonBuilder.java-formatting-style`

`@CanIgnoreReturnValue public GsonBuilder setPrettyPrinting()` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L548-L551][f1]

setPrettyPrinting delegates to setFormattingStyle(PRETTY); setFormattingStyle requires non-null and stores it; null throws NPE.

<a id="u-6194cedfbb21"></a>
### `GsonBuilder.java-gsonbuilder-state`

`class GsonBuilder` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L93-L94][f1]

Mutable builder that accumulates Gson configuration and produces a Gson via create; it owns excluder, policies, flags, user factories, hierarchy factories, and reflection filters.

Configuration methods mutate fields and return this; create passes the builder to Gson, and createFactories assembles built-in and user factories in a fixed order.

<a id="u-aea6641bbdd1"></a>
### `GsonBuilder.java-number-strategies`

`@CanIgnoreReturnValue public GsonBuilder setObjectToNumberStrategy(ToNumberStrategy o…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L443-L447][f1]

Each setter requires a non-null strategy, stores it, and returns this; null throws NPE.

<a id="u-83bccca959d5"></a>
### `GsonBuilder.java-strictness`

`@Deprecated @InlineMe( replacement = "this.setStrictness(Strictness.LENIENT)", import…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L578-L585][f1]

setLenient delegates to setStrictness(LENIENT); setStrictness requires non-null and stores it; null throws NPE.

<a id="u-b29f0ef1580e"></a>
### `GsonBuilder.java-type-adapter-registration-and-guard`

`@CanIgnoreReturnValue public GsonBuilder registerTypeAdapter(Type type, Object typeAd…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L739-L771][f1]

registerTypeAdapter validates and registers adapters; hasNonOverridableAdapter only returns whether the type is Object.class and does not throw.

- registerTypeAdapter: null type or adapter throws NPE; unsupported adapter type throws IllegalArgumentException; if hasNonOverridableAdapter is true, registerTypeAdapter throws IllegalArgumentException; otherwise registers InstanceCreator, serializer/deserializer tree factory, and/or TypeAdapter factory, so multiple interfaces cause multiple registrations; returns this.
- hasNonOverridableAdapter: returns type == Object.class; JsonElement subclasses are not rejected despite the doc.

<a id="u-243bce65dabd"></a>
### `JsonSerializer.java-custom-serializer`

`public interface JsonSerializer<T>` · [gson/src/main/java/com/google/gson/JsonSerializer.java:L75-L91][f2]

Custom serializer interface for one type.

Its callback receives the source object, its fully genericized type, and a serialization context, and returns an element tree. The documentation says Gson invokes it when it encounters a field of the specified type, and warns not to call the context on the source itself because that would re-enter the callback and loop. No implementation is present here.

<a id="u-5ccead45ffbc"></a>
### `TreeTypeAdapter.java-singletypefactory`

`class SingleTypeFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L153-L154][f3]

Factory for one serializer/deserializer.

Constructor casts the adapter to JsonSerializer/JsonDeserializer and throws IllegalArgumentException if it implements neither. create matches exact type (or raw type when enabled) or hierarchy assignability; on match returns a TreeTypeAdapter with this factory as skipPast, otherwise null.

<a id="u-26bbb9a491f3"></a>
### `TreeTypeAdapter.java-treetypeadapter-class`

`class TreeTypeAdapter<T> extends SerializationDelegatingTypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L41-L42][f3]

Streaming TypeAdapter bridging tree-style JsonSerializer/JsonDeserializer.

Stores serializer, deserializer, Gson, TypeToken, skipPast factory, nullSafe flag, and a lazily created volatile delegate. Constructors set these fields; the shorter constructor defaults nullSafe to true.

<a id="u-a6cff69ab3f5"></a>
### `TypeAdapters.java-type-hierarchy-factory`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L1066-L1072][f4]

Creates a factory for a class and its subtypes.

Its create returns null when the requested raw type is not assignable to the captured class; otherwise it returns an adapter that delegates writing and, on reading, delegates then throws JsonSyntaxException if a non-null result is not an instance of the requested type. toString reports the hierarchy class and adapter.

<a id="u-ae45df6df1fc"></a>
### `TypeAdapters.java-typetoken-factory`

`@SuppressWarnings("TypeParameterNaming") public static <TT> TypeAdapterFactory newFac…` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L992-L996][f4]

Creates a factory matching an exact TypeToken.

Its create returns the supplied adapter when the requested TypeToken equals the captured token, otherwise null.

<a id="u-1e26ab3621a4"></a>
### `GsonBuilder.addReflectionAccessFilter`

`@CanIgnoreReturnValue public GsonBuilder addReflectionAccessFilter(ReflectionAccessFi…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L909-L914][f1]

Requires a non-null filter, adds it to the front of reflectionFilters, and returns this; null throws NPE.

Most recently added filters are first.

<a id="u-8b8e14159201"></a>
### `GsonBuilder.create`

`public Gson create()` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L922-L924][f1]

Returns a new Gson built from this builder; the builder itself is not mutated.

<a id="u-29edeadb7eb3"></a>
### `GsonBuilder.registerTypeAdapterFactory`

`@CanIgnoreReturnValue public GsonBuilder registerTypeAdapterFactory(TypeAdapterFactor…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L795-L800][f1]

Requires a non-null factory, appends it to factories, and returns this; null throws NPE.

<a id="u-52a0d7037a42"></a>
### `GsonBuilder.registerTypeHierarchyAdapter`

`@CanIgnoreReturnValue public GsonBuilder registerTypeHierarchyAdapter(Class<?> baseTy…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L818-L841][f1]

Validates and registers a hierarchy adapter, returning this.

- null baseType or adapter throws NPE; unsupported adapter type throws IllegalArgumentException.
- serializer/deserializer: adds a hierarchy factory to hierarchyFactories.
- TypeAdapter: adds a hierarchy factory to factories.
No JsonElement check is performed despite the doc. Because createFactories reverses factories and hierarchyFactories separately and places reversed factories before reversed hierarchyFactories, a later-registered hierarchy TypeAdapter can precede an earlier exact-type adapter; the doc's specific-type precedence is not guaranteed by this ordering.

<a id="u-39e89e1c9f69"></a>
### `GsonBuilder.setDateFormat`

`@CanIgnoreReturnValue public GsonBuilder setDateFormat(String pattern)` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L638-L650][f1]

Validates a non-null pattern by constructing SimpleDateFormat, rethrows IllegalArgumentException with message and cause on invalid pattern, then stores the pattern; null resets it.

Returns this; on invalid pattern the stored pattern is unchanged.

<a id="u-bbe8830ff9a2"></a>
### `GsonBuilder.setLongSerializationPolicy`

`@CanIgnoreReturnValue public GsonBuilder setLongSerializationPolicy(LongSerialization…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L400-L404][f1]

Requires a non-null policy, stores it, and returns this; null throws NPE.

<a id="u-434476d86159"></a>
### `JsonDeserializer.deserialize`

`T deserialize(JsonElement json, Type typeOfT, JsonDeserializationContext context) thr…` · [gson/src/main/java/com/google/gson/JsonDeserializer.java:L94-L95][f5]

Callback interface for custom tree-based deserialization: deserialize(JsonElement, Type, JsonDeserializationContext) converts a JSON subtree into an object of the requested type, typically delegating nested conversion to the context.

Implementations may throw JsonParseException for unexpected input, should be stateless and thread-safe, and must not recursively deserialize the same json with the same type (infinite loop). TreeTypeAdapter invokes this method; new code should prefer the streaming TypeAdapter API.

<a id="u-55d4a1a7ac2e"></a>
### `TreeTypeAdapter.delegate`

`private TypeAdapter<T> delegate()` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L112-L120][f3]

delegate lazily obtains and caches the delegate adapter via Gson.getDelegateAdapter using the skipPast factory and type; concurrent races may assign multiple times but the last assignment remains.

<a id="u-79ad1e7ebb16"></a>
### `TreeTypeAdapter.getSerializationDelegate`

`@Override public TypeAdapter<T> getSerializationDelegate()` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L126-L129][f3]

getSerializationDelegate returns this when a serializer exists; otherwise returns the lazily created delegate.

<a id="u-847456dbc116"></a>
### `TreeTypeAdapter.newFactory`

`public static TypeAdapterFactory newFactory(TypeToken<?> exactType, Object typeAdapter)` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L132-L134][f3]

newFactory returns a SingleTypeFactory matching the exact type, with raw-type matching disabled and no hierarchy type.

<a id="u-ac1820337c5b"></a>
### `TreeTypeAdapter.newFactoryWithMatchRawType`

`public static TypeAdapterFactory newFactoryWithMatchRawType( TypeToken<?> exactType, …` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L137-L142][f3]

newFactoryWithMatchRawType enables raw-type matching only when the exact type is itself a raw type, then returns a SingleTypeFactory.

<a id="u-48ebb4829b63"></a>
### `TreeTypeAdapter.newTypeHierarchyFactory`

`public static TypeAdapterFactory newTypeHierarchyFactory( Class<?> hierarchyType, Obj…` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L148-L151][f3]

newTypeHierarchyFactory returns a SingleTypeFactory matching by raw-type assignability to the supplied hierarchy class.

<a id="u-83e464255c1a"></a>
### `TreeTypeAdapter.read`

`@Override public T read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L86-L96][f3]

read delegates to delegate().read when no deserializer; otherwise parses the reader into a JsonElement, returns null for null tree when nullSafe, and calls deserializer.deserialize with the type and context.

<a id="u-34a4da1a6f8f"></a>
### `TreeTypeAdapter.write`

`@Override public void write(JsonWriter out, T value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L98-L110][f3]

write delegates to delegate().write when no serializer; otherwise writes JSON null for null value when nullSafe, or serializes to a tree and streams it to the writer.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/GsonBuilder.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonSerializer.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonDeserializer.java
