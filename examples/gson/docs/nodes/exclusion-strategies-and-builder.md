# Exclusion Strategies and Builder

**Capability.** Decides which fields and types Gson omits via version, modifier, and user ExclusionStrategy checks, and accumulates all Gson configuration in a fluent builder.

Come here to understand why a field or class is skipped during (de)serialization, or to see how GsonBuilder options like naming policy, date format, and custom adapters are stored and assembled. The Excluder provides the actual skip logic while the builder collects configuration and produces configured Gson instances.

**Depends on.**

- [Built-in Adapter Implementations](built-in-adapter-implementations.md) · graph-confirmed · 2 edge(s) · The builder and excluder assemble configuration that selects among the built-in adapter implementations.
- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) · graph-only · 3 edge(s)
- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-only · 3 edge(s)
- [Built-in JDK Type Adapters](built-in-jdk-type-adapters.md) · graph-only · 2 edge(s)
- [Reflection and record support](reflection-and-record-support.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Built-in Adapter Implementations](built-in-adapter-implementations.md) · graph-confirmed · 2 edge(s)
- [Gson Configuration Assembly](gson-configuration-assembly.md) · graph-only · 2 edge(s)

Parent: [Adapter Configuration and Policies](adapter-configuration-and-policies.md)

## Units (20)

<a id="u-07e898a1898f"></a>
### `Excluder.java-adapter-factory`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> type)` · [gson/src/main/java/com/google/gson/internal/Excluder.java:L110-L128][f1]

Creates a TypeAdapter only when the raw type is excluded in at least one direction; otherwise returns null so other factories apply.

When both directions are allowed the factory declines; when both are excluded the adapter reads null after skipping the JSON value and writes nullValue(). If only one direction is excluded, the other delegates lazily via gson.getDelegateAdapter with this factory, memoized in a volatile field — a benign race may create multiple delegates, the last assignment wins. Delegate creation is deferred because it may fail or be unneeded.

<a id="u-67895cfb9862"></a>
### `Excluder.java-class-exclusion`

`public boolean excludeClass(Class<?> clazz, boolean serialize)` · [gson/src/main/java/com/google/gson/internal/Excluder.java:L199-L234][f1]

Returns true if a class is excluded for the given direction, checking in order: version annotations on the class (valid means version >= Since.value and version < Until.value, absent annotations pass); non-static member classes when inner-class serialization is disabled; anonymous or non-static local classes — only for deserialization and never for enum subclasses, since built-in enum adapters handle them and Unsafe-based fallbacks would fail on captured values; and any direction-matching ExclusionStrategy returning shouldSkipClass.

isInnerClass is member-class && not static per ReflectionHelper.isStatic.

<a id="u-830ea9c15a32"></a>
### `Excluder.java-excluder-configuration`

`class Excluder implements TypeAdapterFactory, Cloneable` · [gson/src/main/java/com/google/gson/internal/Excluder.java:L49-L50][f1]

Configurable, cloneable TypeAdapterFactory that decides which fields and types Gson omits; its withers return modified copies, leaving the receiver untouched.

Default state ignores versions, excludes transient and static fields, serializes inner classes, does not require @Expose, and has no custom strategies. clone() uses super.clone() and converts CloneNotSupportedException to AssertionError. withVersion sets the version; withModifiers replaces the modifier mask with the OR of the given values; disableInnerClassSerialization and excludeFieldsWithoutExposeAnnotation flip the respective booleans; withExclusionStrategy appends the strategy to a copy of the serialization and/or deserialization strategy lists (only the selected lists are copied).

<a id="u-751cf8a7f437"></a>
### `Excluder.java-field-exclusion`

`public boolean excludeField(Field field, boolean serialize)` · [gson/src/main/java/com/google/gson/internal/Excluder.java:L158-L165][f1]

Returns true if a field is excluded for the given direction by any of six checks, short-circuiting in order: modifier mask overlap with the field's modifiers; version (only when a version is set and the field's @Since/@Until range does not contain it); synthetic fields; @Expose requirement (when requireExpose, excluded if the annotation is absent or its serialize/deserialize flag for this direction is false); exclusion of the field's declared type per excludeClass; or any direction-matching ExclusionStrategy returning shouldSkipField on a FieldAttributes wrapper.

<a id="u-569a3dd65df7"></a>
### `ExclusionStrategy.java-exclusionstrategy`

`boolean shouldSkipField(FieldAttributes f);` · [gson/src/main/java/com/google/gson/ExclusionStrategy.java:L102-L102][f2]

Callback interface letting users decide whether a field or class is skipped during serialization or deserialization; implementors return true from shouldSkipField(FieldAttributes) or shouldSkipClass(Class<?>) to exclude the given target.

Gson's Excluder consults these methods when applying exclusion strategies registered on GsonBuilder.

<a id="u-749a76fde0e8"></a>
### `FieldAttributes.java-fieldattributes`

`class FieldAttributes` · [gson/src/main/java/com/google/gson/FieldAttributes.java:L35-L36][f3]

Immutable, thread-safe wrapper exposing reflective attributes of a single java.lang.reflect.Field.

The constructor rejects a null field via Objects.requireNonNull. Accessors delegate directly to the wrapped Field: getDeclaringClass/getName return identity metadata, getDeclaredType returns the generic type (parameterized types preserved), getDeclaredClass returns the raw Class, getAnnotation returns the annotation of the given type or null, getAnnotations returns a fixed-size list wrapper over the field's annotations, hasModifier tests a bitmask against the field's modifiers, and toString returns the field's own string.

<a id="u-0f6f712f347f"></a>
### `FieldAttributes.java-fieldattributes-reflective-accessors`

`class FieldAttributes` · [gson/src/main/java/com/google/gson/FieldAttributes.java:L63-L84][f3]

These class regions of FieldAttributes each wrap one reflective accessor that delegates to the stored java.lang.reflect.Field: getDeclaredType returns the field's generic type (preserving parameterization, e.g. List<String>), getDeclaredClass returns the raw Class, getAnnotation returns the field's annotation of the requested type or null, getAnnotations returns a fixed-size list view of all field annotations, and hasModifier tests the field's modifier bits against the given mask with a non-zero bitwise AND.

All are pure queries over the immutable field reference; none validate or transform beyond the underlying reflection call.

<a id="u-42fc0e44b68d"></a>
### `GsonBuilder.java-date-format-configuration`

`@CanIgnoreReturnValue public GsonBuilder setDateFormat(String pattern)` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L638-L650][f4]

setDateFormat(String) validates a non-null pattern by constructing a SimpleDateFormat; an invalid pattern rethrows IllegalArgumentException with a descriptive message wrapping the cause, and a null pattern simply resets it.

The int variants validate styles via checkDateFormatStyle, which accepts only 0–3 (FULL/LONG/MEDIUM/SHORT) and throws IllegalArgumentException otherwise; both clear datePattern so the last invocation wins. The single-arg variant changes only dateStyle, leaving the previous timeStyle in effect (deprecated for this reason).

<a id="u-48638f4852b6"></a>
### `GsonBuilder.java-exclusion-strategy-registration`

`@CanIgnoreReturnValue public GsonBuilder setExclusionStrategies(ExclusionStrategy... …` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L488-L495][f4]

setExclusionStrategies requires a non-null array and registers each strategy for both serialization and deserialization; addSerializationExclusionStrategy and addDeserializationExclusionStrategy each require a non-null strategy and register for only one direction.

All three accumulate strategies (disjunction: any strategy skipping a field/class wins) by deriving a new excluder; existing strategies are kept.

<a id="u-4d6027fe6c85"></a>
### `GsonBuilder.java-gsonbuilder-class-and-state`

`class GsonBuilder` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L93-L94][f4]

Fluent builder that accumulates Gson configuration and produces configured Gson instances via create().

It holds mutable configuration fields (excluder, long serialization policy, field naming strategy, instance creators, factory lists, flags for nulls/complex map keys/special floats/HTML escaping/non-executable JSON, formatting style, strictness, JDK-unsafe usage, number strategies, date pattern/styles, and a deque of reflection filters). The no-arg constructor uses defaults; the package-private Gson-based constructor copies every setting from an existing Gson, including factories, hierarchy factories, and reflection filters. Most configuration methods return this and are order-independent; several delegate to an immutable Excluder (each call replaces the field with a derived copy). A static DEFAULT builder backs the default Gson constructor and must not be leaked.

<a id="u-6e1f8673feb0"></a>
### `GsonBuilder.java-registertypeadapter-and-override-guard`

`@CanIgnoreReturnValue public GsonBuilder registerTypeAdapter(Type type, Object typeAd…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L739-L771][f4]

Registers a custom adapter for an exact type.

Requires non-null type and adapter (NPE) and the adapter must implement at least one of TypeAdapter, InstanceCreator, JsonSerializer, JsonDeserializer, else IllegalArgumentException. hasNonOverridableAdapter rejects Object.class with IllegalArgumentException (JsonElement subclasses are deliberately allowed for backward compatibility). An InstanceCreator is stored in instanceCreators; JsonSerializer/JsonDeserializer add a TreeTypeAdapter factory; a TypeAdapter adds a TypeAdapters.newFactory entry — multiple interfaces register multiple entries. Later registrations for the same type are appended, so they can override earlier ones by factory ordering in createFactories.

<a id="u-b1564f2b1537"></a>
### `GsonBuilder.java-simple-flag-setters`

`@CanIgnoreReturnValue public GsonBuilder generateNonExecutableJson()` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L242-L246][f4]

One-line fluent toggles: generateNonExecutableJson, serializeNulls, enableComplexMapKeySerialization, serializeSpecialFloatingPointValues, disableHtmlEscaping, and disableJdkUnsafe set their boolean flags true/false respectively; disableInnerClassSerialization delegates to the excluder; setLongSerializationPolicy, setFieldNamingStrategy, setStrictness, setFormattingStyle, and addReflectionAccessFilter store a required non-null value (NPE from Objects.requireNonNull on null).

setFieldNamingPolicy delegates to setFieldNamingStrategy; setPrettyPrinting delegates to setFormattingStyle(PRETTY); deprecated setLenient delegates to setStrictness(LENIENT). addReflectionAccessFilter prepends to the filter deque so the most recent filter runs first.

<a id="u-6bd79e3ed531"></a>
### `GsonBuilder.java-strategy-setters`

`@CanIgnoreReturnValue public GsonBuilder setFieldNamingPolicy(FieldNamingPolicy namin…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L412-L415][f4]

setFieldNamingPolicy delegates to setFieldNamingStrategy, which stores a non-null FieldNamingStrategy (NPE on null).

setObjectToNumberStrategy and setNumberToNumberStrategy store non-null ToNumberStrategy instances (NPE on null) used for Object and Number deserialization respectively.

<a id="u-a977527b7c1f"></a>
### `GsonBuilder.addUserDefinedAdapters`

`private void addUserDefinedAdapters(List<TypeAdapterFactory> all)` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L1028-L1041][f4]

Inserts the builder's user-registered factories into the target list in reverse registration order, followed by hierarchy factories also reversed, so the most recently registered adapter wins during lookup.

<a id="u-8b8e14159201"></a>
### `GsonBuilder.create`

`public Gson create()` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L922-L924][f4]

Creates a new Gson from the current builder state; side-effect free on the builder, so it can be called repeatedly, though later configuration changes affect subsequent creates.

<a id="u-b61c19e2a648"></a>
### `GsonBuilder.excludeFieldsWithModifiers`

`@CanIgnoreReturnValue public GsonBuilder excludeFieldsWithModifiers(int... modifiers)` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L227-L232][f4]

Replaces the default transient/static field exclusion with exclusion of the given java.lang.reflect.Modifier constants; requires a non-null modifiers array (NPE otherwise) and delegates to the excluder.

<a id="u-8784c7046129"></a>
### `GsonBuilder.newImmutableList`

`static <E> List<E> newImmutableList(Collection<E> collection)` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L1005-L1018][f4]

Returns an immutable list from a collection: empty input yields Collections.emptyList, a single element yields a singletonList (fetched by index for Lists, else via iterator), and anything larger yields an unmodifiable list over an array copy.

<a id="u-29edeadb7eb3"></a>
### `GsonBuilder.registerTypeAdapterFactory`

`@CanIgnoreReturnValue public GsonBuilder registerTypeAdapterFactory(TypeAdapterFactor…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L795-L800][f4]

Appends a non-null TypeAdapterFactory (NPE on null) to the user factory list; factories are later reversed and inserted before built-in adapters in createFactories.

<a id="u-52a0d7037a42"></a>
### `GsonBuilder.registerTypeHierarchyAdapter`

`@CanIgnoreReturnValue public GsonBuilder registerTypeHierarchyAdapter(Class<?> baseTy…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L818-L841][f4]

Registers an adapter for a whole class hierarchy.

Requires non-null baseType and adapter (NPE) and at least one of TypeAdapter, JsonSerializer, JsonDeserializer, else IllegalArgumentException. Json(De)Serializer implementations add a TreeTypeAdapter hierarchy factory to hierarchyFactories; a TypeAdapter adds a TypeAdapters.newTypeHierarchyFactory to factories. Unlike registerTypeAdapter, InstanceCreator is not supported here. Exact-type registrations take precedence over hierarchy ones by factory ordering.

<a id="u-0fa91bf420d0"></a>
### `GsonBuilder.setVersion`

`@CanIgnoreReturnValue public GsonBuilder setVersion(double version)` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L204-L211][f4]

Enables @Since/@Until version-based exclusion by storing the version in the excluder.

Rejects NaN or negative versions with IllegalArgumentException before mutating state.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/Excluder.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/ExclusionStrategy.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/FieldAttributes.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/GsonBuilder.java
