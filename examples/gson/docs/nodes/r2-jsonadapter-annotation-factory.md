# @JsonAdapter Annotation Handling

**Capability.** Implements the @JsonAdapter SPI: locates the annotation, instantiates the annotated adapter class via ConstructorConstructor, dispatches on whether it is a TypeAdapter, TypeAdapterFactory, or JsonSerializer/Deserializer, and caches factories per raw class with race-safe putIfAbsent.

Consult this subtree to see how user-annotated adapters take precedence and how getDelegateAdapter-style reference comparisons (areSameFactories) interact with the factory chain.

**Depends on.**

- [Public Contracts and Annotations](r2-public-api.md) · model-inferred · 0 edge(s)
- [Runtime Generic Type Model](r1-type-model.md) · graph-only · 5 edge(s)

**Depended on by.**

- [ReflectiveTypeAdapterFactory](r2-reflective-type-adapter-factory.md) · graph-confirmed · 1 edge(s) · createBoundField resolves @JsonAdapter-annotated fields through JsonAdapterAnnotationTypeAdapterFactory.getTypeAdapter.
- [Gson Facade and Conversion API](r1-facade-api.md) · graph-only · 1 edge(s)

Parent: [Reflection-Based Object Binding](r2-reflective-binding.md)

## Units (8)

<a id="u-637578f857dc"></a>
### `gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:JsonAdapterAnnotationTypeAdapterFactory`

`class JsonAdapterAnnotationTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L43-L64][f1]

Implements the handling of @JsonAdapter: given a target type, it looks up the annotation and builds an adapter from the annotated class.

Constructor stores the ConstructorConstructor and creates a ConcurrentHashMap for caching factories created for class-level annotations; Gson's thread-safety requirement motivates the concurrent map. DummyTypeAdapterFactory instances (TREE_TYPE_CLASS_DUMMY_FACTORY, TREE_TYPE_FIELD_DUMMY_FACTORY) are placeholder skipPast factories whose create throws AssertionError("Factory should not be used"); they let TreeTypeAdapter distinguish class-level from field-level @JsonAdapter in Gson.getDelegateAdapter.

<a id="u-e7e41a8c2740"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.create`

`@SuppressWarnings("unchecked") @Override public <T> TypeAdapter<T> create(Gson gson, …` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L75-L85][f1]

Looks up @JsonAdapter on the target's raw type; if absent returns null so the next factory handles the type.

Otherwise delegates to getTypeAdapter with isClassAnnotation=true and casts the result to TypeAdapter<T>; the unchecked cast relies on the user supplying an adapter class matching the annotated type.

calls: [type-token-class](r1-type-model.md#u-55a9c25d6eea)

<a id="u-e6f8ee07b4c5"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.createAdapter`

`private static Object createAdapter( ConstructorConstructor constructorConstructor, C…` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L88-L97][f1]

Instantiates the annotated adapter class via constructorConstructor.get(TypeToken.get(adapterClass), allowUnsafe=true).construct().

allowUnsafe is hard-coded true, so Unsafe allocation is permitted; the source TODOs note resulting instances may be broken and exception messages may mislead.

calls: [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:ConstructorConstructor.get](r2-object-construction.md#u-2b1d12b84c2c)

<a id="u-3674883f9c33"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.getAnnotation`

`private static JsonAdapter getAnnotation(Class<?> rawType)` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L70-L72][f1]

Returns the @JsonAdapter annotation of the raw class, centralizing retrieval so callers do so consistently.

<a id="u-b06bd194e1b8"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.getTypeAdapter`

`TypeAdapter<?> getTypeAdapter( ConstructorConstructor constructorConstructor, Gson gs…` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L105-L162][f1]

Constructs the annotated adapter instance and dispatches by its runtime type.

If TypeAdapter, uses it directly. If TypeAdapterFactory, for a class-level annotation replaces it with the winner of putFactoryAndGetCurrent before calling factory.create(gson, type). If JsonSerializer and/or JsonDeserializer, builds a TreeTypeAdapter with skipPast set to the class or field dummy factory, and forces nullSafe=false because TreeTypeAdapter handles null handling itself. Any other type raises IllegalArgumentException describing the invalid bind. Finally, when nullSafe is still true and the adapter is non-null, wraps it with nullSafe(); the adapter may be null if a TypeAdapterFactory create returned null.

calls: [TypeAdapter.nullSafe](r1-adapter-framework.md#u-c7dd40fc556f); uses: [type-token-class](r1-type-model.md#u-55a9c25d6eea)

**Uncertainties.**

- Behavior when factory.create returns null for a class-level annotation: result can be null and is returned unwrapped.

<a id="u-182401855dac"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.isClassJsonAdapterFactory`

`public boolean isClassJsonAdapterFactory(TypeToken<?> type, TypeAdapterFactory factory)` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L174-L209][f1]

Reports whether factory was created for a @JsonAdapter on the type's class.

After null-checking both arguments: if factory is the class dummy factory it returns true immediately. Otherwise it looks up the raw type's cached factory and, if present, returns the reference-equality result. With no cache entry it inspects the annotation directly so behavior is consistent regardless of prior lookups: no annotation, or an annotation whose value does not implement TypeAdapterFactory, returns false. Otherwise it instantiates the factory, caches it via putFactoryAndGetCurrent, and returns whether the winning cached factory is the same instance as the queried one.

calls: [type-token-class](r1-type-model.md#u-55a9c25d6eea), [JsonAdapterAnnotationTypeAdapterFactory.createAdapter](r2-jsonadapter-annotation-factory.md#u-e6f8ee07b4c5)

**Uncertainties.**

- This method instantiates the annotated factory as a side effect even when the comparison returns false.

<a id="u-48d34d08cb9e"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.areSameFactories`

`@SuppressWarnings("ReferenceEquality") private static boolean areSameFactories(TypeAd…` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L164-L168][f1]

Reference-equality (==) check between factories, matching the comparison used by Gson.getDelegateAdapter.

<a id="u-32b102824858"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.putFactoryAndGetCurrent`

`private TypeAdapterFactory putFactoryAndGetCurrent(Class<?> rawType, TypeAdapterFacto…` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L99-L103][f1]

Caches a factory per raw class with putIfAbsent so concurrent creations race safely; returns the already-stored factory if one exists, otherwise the newly supplied one.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java