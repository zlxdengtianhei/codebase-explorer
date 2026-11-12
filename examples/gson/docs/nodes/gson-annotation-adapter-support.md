# Gson annotation adapter support

**Capability.** Defines Gson runtime annotations and resolves @JsonAdapter annotations into type adapter factories.

Come here when you need the semantics of Gson annotations or how @JsonAdapter is turned into an adapter. It contains annotation definitions plus factory logic for annotated types and fields.

**Depends on.**

- [Core configuration and adapters](core-configuration-and-adapters.md) · graph-confirmed · 1 edge(s)
- [Object binding adapters](object-binding-adapters.md) · graph-confirmed · 1 edge(s)
- [Type resolution and enums](type-resolution-and-enums.md) · graph-confirmed · 2 edge(s)
- [Generic type reflection](generic-type-reflection.md) · graph-only · 2 edge(s)
- [Null-safe atomic adapters](null-safe-atomic-adapters.md) · graph-only · 1 edge(s)
- [Object construction adapters](object-construction-adapters.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Object binding adapters](object-binding-adapters.md) · graph-confirmed · 1 edge(s)
- [Serialization facade and writing](serialization-facade-and-writing.md) · graph-confirmed · 1 edge(s)
- [Gson serialization facade](gson-serialization-facade.md) · graph-only · 1 edge(s)

Parent: [Gson JSON library](gson-json-library.md)

## Units (13)

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

<a id="u-e89d40805bee"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.java-annotation-lookup-and-create`

`private static JsonAdapter getAnnotation(Class<?> rawType)` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L70-L72][f3]

getAnnotation returns the raw type's @JsonAdapter annotation.

create returns null if absent; otherwise calls getTypeAdapter with the constructor constructor, Gson, target type, annotation, and class-annotation true.

<a id="u-c60bb9761911"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.java-class-factory-recognition`

`@SuppressWarnings("ReferenceEquality") private static boolean areSameFactories(TypeAd…` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L164-L168][f3]

areSameFactories uses reference equality.

isClassJsonAdapterFactory returns true for the class dummy factory; otherwise checks cached factory for raw type, then if absent inspects @JsonAdapter, returns false if no annotation or value is not TypeAdapterFactory, else creates/caches factory and compares by reference.

<a id="u-6069b5ce18d2"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.java-dummytypeadapterfactory`

`class DummyTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L38-L39][f3]

Sentinel TypeAdapterFactory used as skipPast for class/field TreeTypeAdapters.

Its create always throws AssertionError because it must never be used.

<a id="u-a8fb6cc991b2"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.java-jsonadapterannotationtypeadapterfactory-class`

`class JsonAdapterAnnotationTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L37-L38][f3]

Factory that reads @JsonAdapter on a raw type and builds the annotated adapter.

Holds a ConstructorConstructor and a concurrent map of class-level TypeAdapterFactory instances; constructor stores both. create returns null when no annotation is present, otherwise delegates to getTypeAdapter with class-annotation flag true.

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

<a id="u-e6f8ee07b4c5"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.createAdapter`

`private static Object createAdapter( ConstructorConstructor constructorConstructor, C…` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L88-L97][f3]

Creates the annotated adapter instance through ConstructorConstructor using TypeToken.get(adapterClass) and allowUnsafe true.

<a id="u-b06bd194e1b8"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.getTypeAdapter`

`TypeAdapter<?> getTypeAdapter( ConstructorConstructor constructorConstructor, Gson gs…` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L105-L162][f3]

Builds the adapter for an @JsonAdapter annotation.

Instantiates annotation.value(); if TypeAdapter uses it directly; if TypeAdapterFactory calls create (and for class annotations caches via putFactoryAndGetCurrent); if JsonSerializer/JsonDeserializer wraps in TreeTypeAdapter with class/field dummy skipPast and disables extra nullSafe; otherwise throws IllegalArgumentException. Applies nullSafe() when requested and adapter non-null.

<a id="u-32b102824858"></a>
### `JsonAdapterAnnotationTypeAdapterFactory.putFactoryAndGetCurrent`

`private TypeAdapterFactory putFactoryAndGetCurrent(Class<?> rawType, TypeAdapterFacto…` · [gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java:L99-L103][f3]

Atomically stores a class-level factory in the map and returns the existing factory if another thread already inserted one; otherwise returns the supplied factory.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/Expose.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/JsonAdapter.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JsonAdapterAnnotationTypeAdapterFactory.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/SerializedName.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/Since.java
[f6]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/Until.java
[f7]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/package-info.java
