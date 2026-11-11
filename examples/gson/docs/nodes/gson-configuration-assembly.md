# Gson Configuration Assembly

**Capability.** Assembles the ordered TypeAdapterFactory list and selects serialization policies, including reflective loading of optional java.time support.

This module turns builder configuration into the final factory chain used by a Gson instance. Readers interested in adapter ordering, long-serialization policy, or how optional java.time adapters are loaded should start here.

**Depends on.**

- [Number and Object Adapters](number-and-object-adapters.md) · graph-confirmed · 2 edge(s)
- [Core Adapter Abstractions and Time](core-adapter-abstractions-and-time.md) · graph-only · 2 edge(s)
- [Exclusion Strategies and Builder](exclusion-strategies-and-builder.md) · graph-only · 2 edge(s)
- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Date Formatting and Parsing](date-formatting-and-parsing.md) · graph-only · 1 edge(s)

Parent: [Built-in Adapter Implementations](built-in-adapter-implementations.md)

## Units (8)

<a id="u-29db0b72dffe"></a>
### `GsonBuilder.java-floating-point-adapter-selection`

`private TypeAdapter<Number> doubleAdapter()` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L1020-L1022][f1]

Return the lenient DOUBLE/FLOAT adapters when serializeSpecialFloatingPointValues is set, otherwise the strict variants that reject NaN and infinities.

<a id="u-845a3fc680bf"></a>
### `LongSerializationPolicy.java-longserializationpolicy`

`@Override public JsonElement serialize(Long value)` · [gson/src/main/java/com/google/gson/LongSerializationPolicy.java:L38-L44][f2]

Enum selecting how long/Long values are serialized.

DEFAULT emits a JSON number via new JsonPrimitive(value) and maps to TypeAdapters.LONG; STRING emits a quoted string via value.toString() and maps to TypeAdapters.LONG_AS_STRING. Both serialize(Long) overloads return JsonNull.INSTANCE for a null input, so null never becomes a number or string. The package-private typeAdapter() supplies the corresponding streaming TypeAdapter<Number> used internally (e.g., by GsonBuilder).

<a id="u-789ba3b4df7f"></a>
### `TypeAdapters.java-atomiclongadapter`

`public static TypeAdapter<AtomicLong> atomicLongAdapter(TypeAdapter<Number> longAdapter)` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L309-L312][f3]

Builds a nullSafe AtomicLong adapter delegating to a supplied Number adapter: read converts the read Number via longValue into an AtomicLong, write passes value.get() to the delegate.

The delegate must be non-null (requireNonNull).

<a id="u-c88d0c04a528"></a>
### `TypeAdapters.java-atomiclongarrayadapter`

`public static TypeAdapter<AtomicLongArray> atomicLongArrayAdapter( TypeAdapter<Number…` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L375-L379][f3]

Builds a nullSafe AtomicLongArray adapter over a required Number delegate: read collects elements via the delegate, throwing JsonSyntaxException if the delegate yields null for an element, then fills an AtomicLongArray; write delegates each element.

<a id="u-2c01e1890926"></a>
### `TypeAdapters.java-newfactory-class`

`@SuppressWarnings("TypeParameterNaming") public static <TT> TypeAdapterFactory newFac…` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L1004-L1007][f3]

Returns a factory matching on raw type identity (typeToken.getRawType() == type) that returns the adapter or null; toString names the type and adapter for debugging.

<a id="u-c5f23d9ccf01"></a>
### `TypeAdapters.java-newfactory-unboxed-boxed`

`@SuppressWarnings("TypeParameterNaming") public static <TT> TypeAdapterFactory newFac…` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L1016-L1018][f3]

Returns a factory matching either the unboxed or boxed raw type and returning the shared adapter, else null; toString lists both type names.

<a id="u-f54ca5b55863"></a>
### `GsonBuilder.createFactories`

`List<TypeAdapterFactory> createFactories( ConstructorConstructor constructorConstruct…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L926-L1003][f1]

Assembles the full ordered TypeAdapterFactory list for a Gson instance.

Order: non-overridable built-ins (JsonElement, Object with the object-to-number strategy), then the excluder (must precede user adapters), then user-defined adapters (reversed so later registrations are tried first), then custom date adapters, then built-in adapters for all platform types (long adapter chosen by the long serialization policy, double/float adapters chosen by the special-floats flag, Number via the number-to-number strategy, AtomicLong(Array) wrapping the long adapter), then sql types if available, then composite/user types (collections, maps with the complex-key flag, @JsonAdapter annotation factory, enums, and the reflective factory carrying naming strategy, excluder, and an immutable copy of the reflection filters). Returns an unmodifiable, size-trimmed list.

<a id="u-f9f1ea7218e2"></a>
### `TypeAdapters.javaTimeTypeAdapterFactory`

`public static TypeAdapterFactory javaTimeTypeAdapterFactory()` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L980-L990][f3]

Attempts to load com.google.gson.internal.bind.JavaTimeTypeAdapters reflectively, instantiate it as a FactorySupplier, and return its factory; any ReflectiveOperationException or LinkageError (e.g., missing java.time on old JVMs) yields null instead of throwing.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/GsonBuilder.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/LongSerializationPolicy.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java
