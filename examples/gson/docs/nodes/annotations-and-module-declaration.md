# Annotations and Module Declaration

**Capability.** Defines Gson's user-facing annotations and the factory that resolves @JsonAdapter on types and fields.

Come here to understand how Expose, SerializedName, Since, and Until shape serialization, and how @JsonAdapter-annotated adapter classes are instantiated and cached. The module also declares the JPMS module exports.

**Depends on.**

- [Core Gson Contracts and Facade](core-gson-contracts-and-facade.md) · graph-confirmed · 5 edge(s)
- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-only · 4 edge(s)
- [Core Adapter Abstractions and Time](core-adapter-abstractions-and-time.md) · graph-only · 1 edge(s)
- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) · graph-only · 1 edge(s)
- [Instance construction utilities](instance-construction-utilities.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Core Gson Contracts and Facade](core-gson-contracts-and-facade.md) · graph-confirmed · 1 edge(s)

Parent: [Public API and Type Resolution](public-api-and-type-resolution.md)

## Units (15)

<a id="u-568550b47d05"></a>
### `Expose.java-expose-annotation`

`@Documented @Retention(RetentionPolicy.RUNTIME) @Target(ElementType.FIELD) public @in…` · [gson/src/main/java/com/google/gson/annotations/Expose.java:L62-L84][f1]

Field-level runtime annotation that opts a member into Gson serialization/deserialization, with independent serialize and deserialize flags defaulting to true.

It has no effect unless the Gson instance was built with GsonBuilder.excludeFieldsWithoutExposeAnnotation(); with that setting, unannotated fields are excluded, and a field with serialize=false is skipped in output while deserialize=false is skipped on input. Retention is RUNTIME, target is FIELD only.

<a id="u-2315baa94279"></a>
### `JsonAdapter.java-jsonadapter-annotation`

`@Retention(RetentionPolicy.RUNTIME) @Target({ElementType.TYPE, ElementType.FIELD}) pu…` · [gson/src/main/java/com/google/gson/annotations/JsonAdapter.java:L116-L135][f2]

Runtime annotation on a type or field naming the adapter class Gson should use for it.

value() must be a TypeAdapter, TypeAdapterFactory, or a class implementing JsonDeserializer and/or JsonSerializer; the instance is created like Gson creates deserialization targets (registered InstanceCreator, else any no-args constructor, else JDK Unsafe). nullSafe() defaults to true, meaning Gson handles null without invoking the adapter; setting it false makes the adapter handle nulls. Field annotations take precedence over GsonBuilder-registered adapters, which take precedence over annotated types. Adapter instances may be cached by Gson, so a new one per operation is not guaranteed.

<a id="u-89d2cd9dbfbf"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.java-jsonadapterannotationtypeadapterfactory`

`class JsonAdapterAnnotationTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L37-L38][f3]

TypeAdapterFactory that resolves the @JsonAdapter annotation on a type's raw class and builds the requested adapter.

Holds a ConstructorConstructor for instantiating adapter classes and a ConcurrentHashMap keyed by raw class caching TypeAdapterFactory instances created for class-level annotations (thread-safety per Gson's guarantee).

<a id="u-848e67066a8b"></a>
### `SerializedName.java-serializedname-annotation`

`@Documented @Retention(RetentionPolicy.RUNTIME) @Target({ElementType.FIELD, ElementTy…` · [gson/src/main/java/com/google/gson/annotations/SerializedName.java:L83-L101][f4]

Runtime annotation on a field or method that fixes the JSON name used for serialization and deserialization, overriding any FieldNamingPolicy including the default.

value() is the required primary name; alternate() (default empty) lists additional names accepted during deserialization only — the field is populated from any of them. The specified names must be valid JSON field names.

<a id="u-74eb89058977"></a>
### `Since.java-since-annotation`

`@Documented @Retention(RetentionPolicy.RUNTIME) @Target({ElementType.FIELD, ElementTy…` · [gson/src/main/java/com/google/gson/annotations/Since.java:L56-L65][f5]

Runtime annotation on a field or type giving the version at which it became present; the value is inclusive, so the element is included when the configured Gson version is >= value.

Inert unless Gson was built with GsonBuilder.setVersion(double).

<a id="u-31fae59ed348"></a>
### `Until.java-until-annotation`

`@Documented @Retention(RetentionPolicy.RUNTIME) @Target({ElementType.FIELD, ElementTy…` · [gson/src/main/java/com/google/gson/annotations/Until.java:L60-L70][f6]

Runtime annotation on a field or type giving the version until which it is present; the value is exclusive, so the element is included only when the configured Gson version is < value, and ignored at or above it.

Inert unless Gson was built with GsonBuilder.setVersion(double). It is the counterpart of @Since for deprecating members.

<a id="u-bc3d6e70a1c6"></a>
### `package-info.java module code (L1–L23)`

`module_region` · [gson/src/main/java/com/google/gson/annotations/package-info.java:L1-L23][f7]

Declares the com.google.gson.annotations package, which provides annotations usable with Gson, and marks the package with Error Prone's @CheckReturnValue.

<a id="u-08e5581156f0"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.DummyTypeAdapterFactory.create`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> type)` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L39-L42][f3]

DummyTypeAdapterFactory.create always throws AssertionError; instances exist only as identity markers used as skipPast sentinels for TreeTypeAdapter delegate lookup, never to produce adapters.

<a id="u-48d34d08cb9e"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.areSameFactories`

`@SuppressWarnings("ReferenceEquality") private static boolean areSameFactories(TypeAd…` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L164-L168][f3]

areSameFactories compares two factories by reference equality (==), mirroring Gson.getDelegateAdapter semantics.

<a id="u-e7e41a8c2740"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.create`

`@SuppressWarnings("unchecked") @Override public <T> TypeAdapter<T> create(Gson gson, …` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L75-L85][f3]

create returns null when the target's raw type has no @JsonAdapter annotation; otherwise delegates to getTypeAdapter with isClassAnnotation=true, casting the result unchecked (the annotation value's correctness is the user's responsibility).

<a id="u-e6f8ee07b4c5"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.createAdapter`

`private static Object createAdapter( ConstructorConstructor constructorConstructor, C…` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L88-L97][f3]

createAdapter instantiates the annotation's adapter class via ConstructorConstructor.get(...).construct() with allowUnsafe=true, so classes without accessible constructors may be created through Unsafe, potentially in a broken state; exception messages come from the deserialization context and may be misleading for @JsonAdapter use (noted in TODOs).

<a id="u-b06bd194e1b8"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.getTypeAdapter`

`TypeAdapter<?> getTypeAdapter( ConstructorConstructor constructorConstructor, Gson gs…` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L105-L162][f3]

getTypeAdapter instantiates the annotation value and branches on its type: a TypeAdapter is used directly; a TypeAdapterFactory is registered first for class annotations (putFactoryAndGetCurrent) then asked to create the adapter; a JsonSerializer and/or JsonDeserializer (either may be null) is wrapped in a TreeTypeAdapter with a class- or field-specific dummy skipPast factory, and nullSafe is then cleared because TreeTypeAdapter handles it; anything else throws IllegalArgumentException naming the instance class and the allowed interfaces.

If the resulting adapter is non-null and nullSafe is still set, it is wrapped with nullSafe().

<a id="u-182401855dac"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.isClassJsonAdapterFactory`

`public boolean isClassJsonAdapterFactory(TypeToken<?> type, TypeAdapterFactory factory)` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L174-L209][f3]

isClassJsonAdapterFactory reports whether the given factory is the one created for a @JsonAdapter annotation on the type's raw class.

Null arguments throw NPE. Returns true immediately if the factory is the class-level dummy sentinel. Otherwise it checks the cache map; a hit is decided by reference equality. On a miss it re-reads the annotation: absent or not naming a TypeAdapterFactory yields false; otherwise it constructs the factory, registers it via putFactoryAndGetCurrent, and compares by reference — keeping results consistent whether or not the adapter was requested before this call.

<a id="u-32b102824858"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.putFactoryAndGetCurrent`

`private TypeAdapterFactory putFactoryAndGetCurrent(Class<?> rawType, TypeAdapterFacto…` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L99-L103][f3]

putFactoryAndGetCurrent stores a class-level factory with putIfAbsent and returns the pre-existing factory if another thread won the race, otherwise the newly stored one; ensures one shared factory instance per raw class.

<a id="u-a76a3a49ccfe"></a>
### `module-info.java module code (L1–L36)`

`module_region` · [gson/src/main/java/module-info.java:L1-L36][f8]

Declares the `com.google.gson` module, exporting the public API packages com.google.gson, com.google.gson.annotations, com.google.gson.reflect, and com.google.gson.stream.

All three dependencies (Error Prone Annotations, java.sql, and jdk.unsupported for sun.misc.Unsafe) are `requires static`, so they are optional at runtime and the module works without them; internal packages are not exported and thus encapsulated.

**Uncertainties.**

- Whether any code in the module actually uses the optional dependencies at runtime cannot be established from this file alone.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/Expose.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/JsonAdapter.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/SerializedName.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/Since.java
[f6]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/Until.java
[f7]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/package-info.java
[f8]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/module-info.java
