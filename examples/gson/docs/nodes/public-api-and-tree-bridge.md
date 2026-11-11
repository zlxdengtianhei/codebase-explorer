# Public API and Tree Bridge

**Capability.** Defines Gson's core public contracts—exceptions, naming policies, serializer/deserializer callbacks—and the TreeTypeAdapter bridging them to streaming.

Readers extending Gson with custom tree-based serializers or implementing factories should start here. The module also includes field-name translation logic, Strictness, and the JsonElement-tree serialization entry on Gson.

**Depends on.**

- [Generic Type Reflection](generic-type-reflection.md) · graph-confirmed · 1 edge(s)
- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) · graph-confirmed · 3 edge(s)
- [Tree Element Bridge](tree-element-bridge.md) · graph-only · 3 edge(s)

**Depended on by.**

- [Generic Type Reflection](generic-type-reflection.md) · graph-confirmed · 2 edge(s)
- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) · graph-confirmed · 2 edge(s)
- [Reflective type adapter factory](reflective-type-adapter-factory.md) · graph-only · 6 edge(s)
- [Annotations and Module Declaration](annotations-and-module-declaration.md) · graph-only · 4 edge(s)
- [Core Adapter Abstractions and Time](core-adapter-abstractions-and-time.md) · graph-only · 4 edge(s)
- [Instance construction utilities](instance-construction-utilities.md) · graph-only · 4 edge(s)
- [Built-in JDK Type Adapters](built-in-jdk-type-adapters.md) · graph-only · 3 edge(s)
- [Exclusion Strategies and Builder](exclusion-strategies-and-builder.md) · graph-only · 3 edge(s)
- [Gson Configuration Assembly](gson-configuration-assembly.md) · graph-only · 2 edge(s)
- [Map Serialization](map-serialization.md) · graph-only · 2 edge(s)
- [Number and Object Adapters](number-and-object-adapters.md) · graph-only · 2 edge(s)
- [Date Formatting and Parsing](date-formatting-and-parsing.md) · graph-only · 1 edge(s)

Parent: [Core Gson Contracts and Facade](core-gson-contracts-and-facade.md)

## Units (24)

<a id="u-a7b32bf78ee8"></a>
### `FieldNamingPolicy.java-fieldnamingpolicy-enum-constants`

`@Override public String translateName(Field f)` · [gson/src/main/java/com/google/gson/FieldNamingPolicy.java:L35-L38][f1]

Each enum constant overrides translateName to map a Java field name to its JSON name: IDENTITY returns the name unchanged; UPPER_CAMEL_CASE upper-cases the first letter; UPPER_CAMEL_CASE_WITH_SPACES first separates camel-case words with spaces then upper-cases the first letter; UPPER_CASE_WITH_UNDERSCORES separates words with '_' and upper-cases with Locale.ENGLISH; LOWER_CASE_WITH_UNDERSCORES, LOWER_CASE_WITH_DASHES, and LOWER_CASE_WITH_DOTS separate words with '_', '-', or '.' respectively and lower-case with Locale.ENGLISH.

All rely on the shared helpers, so a name like aURL becomes a_u_r_l under the separator policies.

<a id="u-e7cf4de79bfe"></a>
### `Gson.java-tojsontree`

`public JsonElement toJsonTree(Object src)` · [gson/src/main/java/com/google/gson/Gson.java:L519-L524][f2]

Serializes an object into a JsonElement tree.

The no-type overload maps null to JsonNull.INSTANCE and otherwise uses the runtime class, losing generic type information; the typed overload accepts a Type and writes through a JsonTreeWriter, returning its result.

<a id="u-41ee997c9516"></a>
### `JsonIOException.java-jsonioexception`

`class name is part of the public API public final class JsonIOException extends JsonP…` · [gson/src/main/java/com/google/gson/JsonIOException.java:L24-L26][f3]

Unchecked exception (extends JsonParseException) signaling that Gson could not read an input stream or write to one.

Three constructors cover message-only, message-plus-cause, and cause-only; the cause-only form is discouraged in favor of the message+cause form. The class is final and carries serialVersionUID 1L.

<a id="u-db37f437caa5"></a>
### `JsonNull.java-jsonnull`

`class JsonNull extends JsonElement` · [gson/src/main/java/com/google/gson/JsonNull.java:L26-L32][f4]

Immutable value object representing a JSON null, extending JsonElement, with a public singleton INSTANCE (since 1.8).

The public constructor is deprecated and does nothing; new instances are still possible but all instances behave identically: deepCopy() returns the shared INSTANCE, hashCode() is JsonNull.class.hashCode(), and equals() is true for any other JsonNull instance (false for null or other types).

<a id="u-63c35942f609"></a>
### `JsonParseException.java-jsonparseexception`

`class JsonParseException extends RuntimeException` · [gson/src/main/java/com/google/gson/JsonParseException.java:L32-L33][f5]

Base unchecked exception for serious problems while parsing JSON, deliberately a RuntimeException so clients are not forced to catch and ignore it.

Three constructors: message-only, message+cause, and cause-only (the last discouraged when a description is possible). Package-visible serialVersionUID is -4086729973971783390L.

<a id="u-71bdf5e2a259"></a>
### `JsonSerializationContext.java-jsonserializationcontext`

`JsonElement serialize(Object src);` · [gson/src/main/java/com/google/gson/JsonSerializationContext.java:L36-L36][f6]

Interface passed to a custom serializer giving access to Gson's default serialization.

serialize(Object) converts an object to a JsonElement tree using its runtime shape; serialize(Object, Type) additionally supplies the genericized type. The Javadoc warns that calling the typed variant on the same object received by the custom serializer causes an infinite loop, since Gson re-dispatches to the custom serializer.

<a id="u-8eb015d9b871"></a>
### `JsonSyntaxException.java-jsonsyntaxexception`

`class JsonSyntaxException extends JsonParseException` · [gson/src/main/java/com/google/gson/JsonSyntaxException.java:L24-L26][f7]

Final unchecked exception (extends JsonParseException) raised when Gson reads or writes a malformed JSON element.

Three constructors: message-only, message+cause, and cause-only (discouraged). serialVersionUID is 1L.

<a id="u-612b3cafb234"></a>
### `TreeTypeAdapter.java-factory-constructors`

`public static TypeAdapterFactory newFactory(TypeToken<?> exactType, Object typeAdapter)` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L132-L134][f8]

newFactory matches only the exact TypeToken; newFactoryWithMatchRawType additionally matches a type whose raw type equals the exact type's Type when the exact type is itself raw (getType()==getRawType()); newTypeHierarchyFactory matches any type whose raw type is assignable to the given class.

All return a SingleTypeFactory configured accordingly.

<a id="u-c7be4ceef8fe"></a>
### `TreeTypeAdapter.java-gsoncontextimpl`

`class GsonContextImpl implements JsonSerializationContext, JsonDeserializationContext` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L191-L193][f8]

Inner context passed to user serializers/deserializers: serialize(Object) and serialize(Object, Type) delegate to gson.toJsonTree, and deserialize delegates to gson.fromJson, propagating JsonParseException as declared.

<a id="u-5ccead45ffbc"></a>
### `TreeTypeAdapter.java-singletypefactory`

`class SingleTypeFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L153-L154][f8]

Factory matching one exact type or a type hierarchy and producing TreeTypeAdapters.

The constructor extracts serializer/deserializer views of the adapter object and throws IllegalArgumentException if it implements neither (after a null check). create matches when exactType equals the requested token, or matchRawType and the exact type equals the requested raw type, or (no exactType) hierarchyType.isAssignableFrom(rawType); on match it returns a new TreeTypeAdapter with nullSafe defaulting true, otherwise null.

calls: [TypeToken.equals](../../catalog.json)

<a id="u-4e407330c43f"></a>
### `TypeToken.java-typetoken-accessors-and-equality`

`public final Class<? super T> getRawType()` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L161-L163][f9]

Expose the token's raw Class and Type (both final, precomputed), and define value semantics: hashCode returns the cached type hash, equals is true only for another TypeToken whose type is equal under GsonTypes.equals, and toString renders the type via GsonTypes.typeToString.

<a id="u-f62cb9a19af0"></a>
### `FieldNamingPolicy.separateCamelCase`

`static String separateCamelCase(String name, char separator)` · [gson/src/main/java/com/google/gson/FieldNamingPolicy.java:L179-L189][f1]

Inserts a separator before each upper-case character (except at position 0, where the builder is still empty), leaving the original characters otherwise intact.

Consecutive upper-case letters each get a preceding separator, which is why acronyms split per letter.

<a id="u-e1b81b3e2980"></a>
### `FieldNamingPolicy.upperCaseFirstLetter`

`static String upperCaseFirstLetter(String s)` · [gson/src/main/java/com/google/gson/FieldNamingPolicy.java:L192-L212][f1]

Finds the first letter in the string and upper-cases it, returning immediately: if that letter is already upper-case the string is returned as-is; otherwise the character is replaced in place (single-char substring when it is the first character).

If the string contains no letters at all, it is returned unchanged.

<a id="u-4a0b49e9ec51"></a>
### `JsonDeserializationContext.deserialize`

`@SuppressWarnings("TypeParameterUnusedInFormals") <T> T deserialize(JsonElement json,…` · [gson/src/main/java/com/google/gson/JsonDeserializationContext.java:L42-L43][f10]

Interface method that lets a custom deserializer delegate a JsonElement subtree to Gson's default deserialization for a target type, returning an object of that type.

The Javadoc warns against calling it on the same element passed to the custom deserializer, which would recurse infinitely because Gson would re-invoke the custom deserializer. Declared to throw JsonParseException when the tree does not match the expected data.

<a id="u-434476d86159"></a>
### `JsonDeserializer.deserialize`

`T deserialize(JsonElement json, Type typeOfT, JsonDeserializationContext context) thr…` · [gson/src/main/java/com/google/gson/JsonDeserializer.java:L94-L95][f11]

Callback interface for custom tree-based deserialization: deserialize(JsonElement, Type, JsonDeserializationContext) converts a JSON subtree into an object of the requested type, typically delegating nested conversion to the context.

Implementations may throw JsonParseException for unexpected input, should be stateless and thread-safe, and must not recursively deserialize the same json with the same type (infinite loop). TreeTypeAdapter invokes this method; new code should prefer the streaming TypeAdapter API.

<a id="u-949e1c27fb73"></a>
### `JsonSerializer.serialize`

`JsonElement serialize(T src, Type typeOfSrc, JsonSerializationContext context);` · [gson/src/main/java/com/google/gson/JsonSerializer.java:L91-L91][f12]

Callback interface for custom serialization of a type T: implementations convert src to a JsonElement, using the context for non-trivial fields.

Implementations should be stateless and thread-safe to preserve Gson's guarantees, must be registered via GsonBuilder.registerTypeAdapter, and must not re-serialize src through the context (infinite loop). New code is directed to the streaming TypeAdapter API for efficiency.

<a id="u-bfab23ee9e5a"></a>
### `Strictness`

`public enum Strictness` · [gson/src/main/java/com/google/gson/Strictness.java:L20-L29][f13]

Enum of reader/writer leniency modes: LENIENT allows large deviations from RFC 8259, LEGACY_STRICT allows small legacy deviations, and STRICT demands full specification compliance.

The enum carries no behavior itself; JsonReader/JsonWriter setStrictness and GsonBuilder.setStrictness interpret the values.

<a id="u-c58ad34373b0"></a>
### `TypeAdapterFactory.create`

`<T> TypeAdapter<T> create(Gson gson, TypeToken<T> type);` · [gson/src/main/java/com/google/gson/TypeAdapterFactory.java:L170-L170][f14]

Factory interface producing TypeAdapter instances for related types; create(Gson, TypeToken<T>) returns an adapter for the requested type or null when the factory does not support it.

Factories are called for many types and must return null for unsupported ones; they are registered with GsonBuilder, where earlier registrations take precedence, and should perform expensive reflection eagerly in create so the returned adapter's read/write stay fast.

<a id="u-bfcdf89b8b0c"></a>
### `TreeTypeAdapter`

`class TreeTypeAdapter<T> extends SerializationDelegatingTypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L41-L42][f8]

TypeAdapter that bridges 1.x tree-style JsonSerializer/JsonDeserializer pairs into the streaming API, delegating to a lazily resolved Gson adapter when only one direction (or neither) is provided.

Holds the serializer, deserializer, gson, typeToken, a skipPast factory used solely for getDelegateAdapter, a per-instance GsonContextImpl, a nullSafe flag, and a volatile lazily-created delegate (lazy because creation may fail and Gson is thread-safe; a benign race may assign it multiple times). The secondary constructor defaults nullSafe to true.

<a id="u-22224d9daf4f"></a>
### `gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:TreeTypeAdapter (2)`

`class TreeTypeAdapter<T> extends SerializationDelegatingTypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L120-L126][f8]

Convenience TreeTypeAdapter constructor that delegates to the full constructor with nullSafe=true, so reads of JSON null return null and writes of null emit a JSON null when a serializer or deserializer is present.

calls: [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:TreeTypeAdapter (7)][f8]

<a id="u-55d4a1a7ac2e"></a>
### `TreeTypeAdapter.delegate`

`private TypeAdapter<T> delegate()` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L112-L120][f8]

delegate lazily resolves and caches gson.getDelegateAdapter(skipPastForGetDelegateAdapter, typeToken); the skipPast factory is only intended for that call, and concurrent races may assign the field more than once with the last assignment winning.

calls: [Gson.getDelegateAdapter](../../catalog.json)

<a id="u-79ad1e7ebb16"></a>
### `TreeTypeAdapter.getSerializationDelegate`

`@Override public TypeAdapter<T> getSerializationDelegate()` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L126-L129][f8]

getSerializationDelegate returns this when a serializer is configured, otherwise the lazily resolved delegate, letting callers serialize with the effective adapter.

<a id="u-83e464255c1a"></a>
### `TreeTypeAdapter.read`

`@Override public T read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L86-L96][f8]

read delegates entirely to the delegate adapter when no deserializer is present; otherwise parses the whole reader into a JsonElement via Streams.parse, returns null when nullSafe and the tree is JSON null, and otherwise calls deserializer.deserialize with the type and the shared context.

calls: [Streams.parse](../../catalog.json), [JsonDeserializer.deserialize](../../catalog.json)

<a id="u-34a4da1a6f8f"></a>
### `TreeTypeAdapter.write`

`@Override public void write(JsonWriter out, T value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L98-L110][f8]

write delegates to the delegate adapter when no serializer is present; otherwise writes nullValue when nullSafe and value is null, or serializes the value to a JsonElement via serializer.serialize and streams it out with Streams.write.

calls: [Streams.write](../../catalog.json), [JsonSerializer.serialize](../../catalog.json)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/FieldNamingPolicy.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/Gson.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonIOException.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonNull.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonParseException.java
[f6]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonSerializationContext.java
[f7]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonSyntaxException.java
[f8]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java
[f9]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/reflect/TypeToken.java
[f10]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonDeserializationContext.java
[f11]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonDeserializer.java
[f12]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonSerializer.java
[f13]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/Strictness.java
[f14]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/TypeAdapterFactory.java
