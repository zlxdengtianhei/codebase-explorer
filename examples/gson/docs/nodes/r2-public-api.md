# Public Contracts and Annotations

**Capability.** Defines the stable user-facing surface: marker and configuration annotations, callback interfaces for custom (de)serialization and instance creation, the factory SPI, the exposed field metadata view, and the module/package declarations that pin which packages are exported.

Read this subtree first to learn what users can implement or annotate without touching internals. Callbacks (InstanceCreator, JsonDeserializer, JsonDeserializationContext) and TypeAdapterFactory are the extension points registered on GsonBuilder; annotations (Expose, JsonAdapter, SerializedName, Since, Until) steer binding behavior; FieldAttributes exposes field metadata to exclusion strategies.

**Depends on.**

- [JSON Element Model and Exceptions](r1-json-element-model.md) · graph-only · 3 edge(s)

**Depended on by.**

- [Builder and Naming Configuration](r2-configuration.md) · model-inferred · 0 edge(s)
- [@JsonAdapter Annotation Handling](r2-jsonadapter-annotation-factory.md) · model-inferred · 0 edge(s)
- [Object Construction Strategy](r2-object-construction.md) · graph-confirmed · 1 edge(s) · ConstructorConstructor delegates instance creation to user-registered InstanceCreator implementations.

Parent: [Gson JSON Library](r2-gson.md)

## Units (18)

<a id="u-72f87f0ef005"></a>
### `fieldattributes-java`

`public FieldAttributes(Field f)` · [gson/src/main/java/com/google/gson/FieldAttributes.java:L43-L45][f1]

Immutable wrapper exposing annotation, type, and modifier information about a single reflected field, used by ExclusionStrategy implementations.

The constructor stores the given Field after a null check (Objects.requireNonNull throws NullPointerException for null). Every accessor delegates directly to the wrapped Field: getDeclaringClass returns the class containing the field, getName its name, getDeclaredType its generic type (preserving type parameters), getDeclaredClass its raw declared Class, getAnnotation returns the matching annotation or null, getAnnotations returns the field's annotations as a fixed-size list backed by Arrays.asList, and hasModifier returns true when the requested modifier bit is set via bitwise AND. toString delegates to Field.toString. Because the wrapper holds an immutable reference and never mutates state, instances are safe to share across threads; exceptions from the underlying reflection calls (e.g. for unavailable generic type information) propagate unchanged.

<a id="u-3d52eb1aa6c0"></a>
### `jsondeserializer-java`

`T deserialize(JsonElement json, Type typeOfT, JsonDeserializationContext context) thr…` · [gson/src/main/java/com/google/gson/JsonDeserializer.java:L94-L95][f2]

Callback interface for custom tree-based deserialization of type T, registered via GsonBuilder.registerTypeAdapter.

Gson calls deserialize with the parsed JsonElement, the target Type, and a JsonDeserializationContext; the implementation returns an object of typeOfT (a subtype of T). Implementations should delegate nested field construction to JsonDeserializationContext.deserialize, but must never invoke it on the same type with the same json element, since Gson would re-enter the callback indefinitely. JsonParseException may be thrown when the JSON does not match typeOfT. Deserializers should be stateless and thread-safe so Gson's thread-safety guarantees hold. Graph evidence shows TreeTypeAdapter.read invokes this callback.

uses: [TreeTypeAdapter.read](r1-tree-adapter-bridge.md#u-83e464255c1a)

<a id="u-4a0b49e9ec51"></a>
### `JsonDeserializationContext.deserialize`

`@SuppressWarnings("TypeParameterUnusedInFormals") <T> T deserialize(JsonElement json,…` · [gson/src/main/java/com/google/gson/JsonDeserializationContext.java:L42-L43][f3]

Lets a custom deserializer invoke Gson's default deserialization for a parse tree and target type.

Implementations receive a JsonElement and a Type and must return an object assignable to typeOfT; the declared JsonParseException propagates when the tree lacks expected data. The javadoc warns that calling it on the element handed to the custom deserializer recurses infinitely, since Gson re-dispatches to the custom deserializer. Behavior of the returned contract is defined by the implementation, which is not in this file.

**Uncertainties.**

- The implementing behavior (type resolution, exception wrapping) lives outside this interface; only the signature contract is observable here.

<a id="u-f5d6aed7d6b2"></a>
### `instancecreator-java`

`T createInstance(Type type);` · [gson/src/main/java/com/google/gson/InstanceCreator.java:L92-L92][f4]

Callback interface for constructing instances of types lacking a no-args constructor, registered via GsonBuilder.registerTypeAdapter.

Gson invokes createInstance(Type) during deserialization to obtain a fresh instance of type T, then overwrites its fields with JSON data, so implementations must return a newly created object rather than a shared one, or their prior contents will be destroyed. Graph evidence shows ConstructorConstructor's InstanceCreatorConstructor calls createInstance when building deserializers. The contract allows implementations to ignore the Type parameter (e.g. for raw generic types), but its value may matter for parameterized types.

uses: [constructorconstructor-java-instance-creator-constructor](r2-object-construction.md#u-0776c7c04887)

<a id="u-87115dd94d56"></a>
### `typeadapterfactory-java`

`<T> TypeAdapter<T> create(Gson gson, TypeToken<T> type);` · [gson/src/main/java/com/google/gson/TypeAdapterFactory.java:L170-L170][f5]

Factory interface creating TypeAdapters for related sets of types, registered on a GsonBuilder.

Gson calls create(Gson, TypeToken) for types it needs adapters for; a factory that does not support the given type must return null so Gson tries the next factory, and when several factories support the same type the one registered earlier wins. The returned adapter may be reused many times, so expensive setup (reflection, lookup tables) should happen in create, and delegate adapters for element types should be obtained via the passed Gson instance inside create so they are built once. The interface declares only this method; the extensive Javadoc gives enum-lowercasing and Guava-Multiset delegation examples.

<a id="u-93b1efdd72d3"></a>
### `jsonioexception-java`

`class name is part of the public API public final class JsonIOException extends JsonP…` · [gson/src/main/java/com/google/gson/JsonIOException.java:L24-L28][f6]

Unchecked-style exception (subclass of JsonParseException) signaling that Gson failed to read from or write to a stream.

It is final and adds three constructors: one with a message, one with message plus cause, and one with only a cause for cases where no description is available; all delegate directly to JsonParseException. Each holds only a serialVersionUID and no behavior beyond exception construction.

inherits: [JsonParseException](r1-json-element-model.md#u-ad7cb601b27d)

<a id="u-e9e2c0e20d07"></a>
### `Expose`

`@Documented @Retention(RetentionPolicy.RUNTIME) @Target(ElementType.FIELD) public @in…` · [gson/src/main/java/com/google/gson/annotations/Expose.java:L62-L84][f7]

Field annotation marking members for JSON serialization/deserialization under Gson's explicit-exposure mode.

Attributes: `serialize` (default true) controls whether the field is written to JSON; `deserialize` (default true) controls whether it is read back. Per the javadoc, the annotation only has effect when Gson is built via `GsonBuilder.excludeFieldsWithoutExposeAnnotation()`; with a default `new Gson()` unannotated fields are included anyway. When that exclusion mode is on, unannotated fields are skipped, fields with `serialize=false` are omitted from output, and fields with `deserialize=false` are skipped on input. Declared with `@Retention(RUNTIME)` and `@Target(FIELD)`, so it is readable reflectively and applies only to fields.

uses: [Expose.java module code (L1–L61)](r2-public-api.md#u-b77a307d7998)

**Uncertainties.**

- Actual exclusion logic lives outside this file; inclusion/exclusion behavior is taken from the javadoc, not from visible Gson runtime code.

<a id="u-b77a307d7998"></a>
### `Expose.java module code (L1–L61)`

`module_region` · [gson/src/main/java/com/google/gson/annotations/Expose.java:L1-L61][f7]

File header of Expose.java: license text, package declaration, and java.lang.annotation imports; no executable behavior beyond the annotation it hosts.

<a id="u-0d36a15236ec"></a>
### `JsonAdapter`

`@Retention(RetentionPolicy.RUNTIME) @Target({ElementType.TYPE, ElementType.FIELD}) pu…` · [gson/src/main/java/com/google/gson/annotations/JsonAdapter.java:L116-L135][f8]

Annotation binding a custom adapter class to a type or field for Gson (de)serialization.

`value()` is required and must be a `TypeAdapter`, a `TypeAdapterFactory`, or implement `JsonDeserializer` and/or `JsonSerializer`. `nullSafe()` defaults to true, meaning Gson handles Java nulls and JSON nulls without invoking the adapter; setting it to false delegates null handling to the adapter. Per javadoc precedence: field annotations override GsonBuilder-registered adapters, which override type-level annotations. The adapter class is instantiated like Gson creates custom classes during deserialization: registered `InstanceCreator` first, else any-visibility no-args constructor, else JDK Unsafe (see `GsonBuilder#disableJdkUnsafe()`). Gson may cache the created adapter, so a new instance is not guaranteed per use. Runtime retention; targets TYPE and FIELD.

uses: [JsonAdapter.java module code (L1–L115)](r2-public-api.md#u-9f29817c01be)

**Uncertainties.**

- Adapter instantiation, caching, and precedence are enforced by Gson runtime code not supplied here; statements rely on the javadoc.

<a id="u-9f29817c01be"></a>
### `JsonAdapter.java module code (L1–L115)`

`module_region` · [gson/src/main/java/com/google/gson/annotations/JsonAdapter.java:L1-L115][f8]

File header of JsonAdapter.java: license, package declaration, and imports including com.google.gson types (Gson, GsonBuilder, TypeAdapter, etc.) used in the annotation's javadoc contract; no executable behavior of its own.

<a id="u-5147dddafce3"></a>
### `SerializedName`

`@Documented @Retention(RetentionPolicy.RUNTIME) @Target({ElementType.FIELD, ElementTy…` · [gson/src/main/java/com/google/gson/annotations/SerializedName.java:L83-L101][f9]

Annotation giving a member an explicit JSON name, overriding any `FieldNamingPolicy` on the Gson instance.

Required `value()` supplies the name used both when serializing and deserializing. Optional `alternate()` (default empty array) lists extra names accepted only during deserialization: JSON containing any alternate name populates the field, while serialization always emits `value()`. Retained at runtime; targets FIELD and METHOD, so it can name serialized getters too. The javadoc notes the value must be a valid JSON field name.

**Uncertainties.**

- Duplicate-name conflict resolution among `value` and `alternate` names is implemented in Gson runtime code not shown here.

<a id="u-8eb3728986df"></a>
### `SerializedName.java module code (L1–L82)`

`module_region` · [gson/src/main/java/com/google/gson/annotations/SerializedName.java:L1-L82][f9]

File header of SerializedName.java: license, package declaration, and java.lang.annotation imports; no behavior beyond hosting the annotation.

<a id="u-93bde83abf23"></a>
### `Since`

`@Documented @Retention(RetentionPolicy.RUNTIME) @Target({ElementType.FIELD, ElementTy…` · [gson/src/main/java/com/google/gson/annotations/Since.java:L56-L65][f10]

Versioning annotation recording the version number from which a field or type exists.

Required `value()` is an inclusive lower bound: when Gson is configured via `GsonBuilder.setVersion(double)`, the member is included only if the configured version is >= value. Per javadoc, it has no effect on a Gson created without `setVersion`, where all fields participate. Runtime retention; targets FIELD and TYPE. Complements `Until`, which supplies the exclusive upper bound.

uses: [Until](r2-public-api.md#u-a60d0a91c7f6)

**Uncertainties.**

- Version comparison and exclusion logic reside in Gson internals not supplied here.

<a id="u-6a0e6349925b"></a>
### `Since.java module code (L1–L55)`

`module_region` · [gson/src/main/java/com/google/gson/annotations/Since.java:L1-L55][f10]

File header of Since.java: license, package declaration, imports including GsonBuilder referenced in javadoc; no behavior beyond hosting the annotation.

<a id="u-a60d0a91c7f6"></a>
### `Until`

`@Documented @Retention(RetentionPolicy.RUNTIME) @Target({ElementType.FIELD, ElementTy…` · [gson/src/main/java/com/google/gson/annotations/Until.java:L60-L70][f11]

Versioning annotation recording the version number up to which a field or type should be present.

Required `value()` is an exclusive upper bound: with `GsonBuilder.setVersion(double)` configured, the member is excluded when the configured version is >= value, i.e. included only when gsonVersion < value. Without `setVersion` the annotation has no effect and all fields participate. Runtime retention; targets FIELD and TYPE. Since 1.3. Complements `Since` (inclusive lower bound).

uses: [Since](r2-public-api.md#u-93bde83abf23)

**Uncertainties.**

- Version comparison and exclusion logic reside in Gson internals not supplied here.

<a id="u-d7eca72d2f80"></a>
### `Until.java module code (L1–L59)`

`module_region` · [gson/src/main/java/com/google/gson/annotations/Until.java:L1-L59][f11]

File header of Until.java: license, package declaration, imports including GsonBuilder referenced in javadoc; no behavior beyond hosting the annotation.

<a id="u-e4f37ffcb336"></a>
### `package-info.java module code (L1–L28)`

`module_region` · [gson/src/main/java/com/google/gson/package-info.java:L1-L28][f12]

Package documentation for com.google.gson describing Gson/GsonBuilder as the entry points for JSON conversion; declares an Error Prone @CheckReturnValue annotation for the package.

No executable code.

<a id="u-a76a3a49ccfe"></a>
### `module-info.java module code (L1–L36)`

`module_region` · [gson/src/main/java/module-info.java:L1-L36][f13]

Declares the com.google.gson JPAG module: exports four public API packages and declares three optional static dependencies.

The module exports com.google.gson, com.google.gson.annotations, com.google.gson.reflect, and com.google.gson.stream; all other packages of the artifact remain unexported. It requires static (compile-time-only, optional at runtime) com.google.errorprone.annotations, java.sql, and jdk.unsupported, matching the source comments that these are optional dependencies for Error Prone annotations, java.sql types, and sun.misc.Unsafe access respectively. Because requires static does not force these modules to be present at runtime, code relying on them must tolerate their absence; how Gson handles missing java.sql or jdk.unsupported at runtime is outside this file. No executable logic, state, or exception paths exist here.

**Uncertainties.**

- Whether consumers can run with these modules absent depends on runtime class loading elsewhere; not verifiable from this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/FieldAttributes.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonDeserializer.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonDeserializationContext.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/InstanceCreator.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/TypeAdapterFactory.java
[f6]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonIOException.java
[f7]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/Expose.java
[f8]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/JsonAdapter.java
[f9]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/SerializedName.java
[f10]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/Since.java
[f11]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/annotations/Until.java
[f12]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/package-info.java
[f13]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/module-info.java