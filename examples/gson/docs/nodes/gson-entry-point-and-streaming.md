# Gson Entry Point and Streaming

**Capability.** Implements the thread-safe Gson facade for toJson/fromJson, adapter caching and delegation, and reader/writer configuration.

This is the main runtime module: it resolves adapters per type token, guards against cyclic type graphs, and configures JsonReader/JsonWriter strictness and HTML safety. Readers tracing a serialization call end-to-end should begin at Gson.

**Depends on.**

- [Generic Type Reflection](generic-type-reflection.md) · graph-confirmed · 5 edge(s) · The Gson facade resolves generic types via TypeToken and GsonTypes utilities to look up adapters.
- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-confirmed · 2 edge(s)
- [Tree Element Bridge](tree-element-bridge.md) · graph-only · 3 edge(s)

**Depended on by.**

- [Generic Type Reflection](generic-type-reflection.md) · graph-confirmed · 2 edge(s)
- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-confirmed · 3 edge(s)
- [In-memory tree writer](in-memory-tree-writer.md) · graph-only · 4 edge(s)
- [Map Serialization](map-serialization.md) · graph-only · 4 edge(s)
- [Exclusion Strategies and Builder](exclusion-strategies-and-builder.md) · graph-only · 3 edge(s)
- [JSON Parsing Facades](json-parsing-facades.md) · graph-only · 3 edge(s)
- [Reflective type adapter factory](reflective-type-adapter-factory.md) · graph-only · 3 edge(s)
- [Core Adapter Abstractions and Time](core-adapter-abstractions-and-time.md) · graph-only · 2 edge(s)
- [Enum, Number Policy, Runtime Dispatch](enum-number-policy-runtime-dispatch.md) · graph-only · 2 edge(s)
- [Instance construction utilities](instance-construction-utilities.md) · graph-only · 2 edge(s)
- [Annotations and Module Declaration](annotations-and-module-declaration.md) · graph-only · 1 edge(s)

Parent: [Core Gson Contracts and Facade](core-gson-contracts-and-facade.md)

## Units (22)

<a id="u-98730f495f37"></a>
### `Gson.java-configuration-accessors`

`@Deprecated public Excluder excluder()` · [gson/src/main/java/com/google/gson/Gson.java:L295-L298][f1]

Trivial accessors exposing the excluder (deprecated because it leaks an internal class), field naming strategy, serializeNulls flag, and htmlSafe flag of this instance.

<a id="u-635b9670d8f3"></a>
### `Gson.java-fromjson-from-jsonelement`

`public <T> T fromJson(JsonElement json, Class<T> classOfT) throws JsonSyntaxException` · [gson/src/main/java/com/google/gson/Gson.java:L1159-L1161][f1]

Deserialize a JsonElement tree.

The Class and Type variants convert to a TypeToken (Type variant unchecked); the TypeToken variant returns null for a null tree and otherwise reads through a JsonTreeReader, inheriting the JsonReader overload's type-check and exception-wrapping behavior.

<a id="u-66db6039b2cd"></a>
### `Gson.java-fromjson-from-jsonreader`

`@SuppressWarnings({"unchecked", "TypeParameterUnusedInFormals"}) public <T> T fromJso…` · [gson/src/main/java/com/google/gson/Gson.java:L1045-L1049][f1]

Read the next JSON value from a caller-supplied JsonReader and convert it.

The Type variant converts to a TypeToken (unchecked); the TypeToken variant is the core: it saves the reader's strictness, forces the instance's explicit strictness or switches a LEGACY_STRICT reader to LENIENT, peeks (marking the document non-empty), obtains the adapter, and reads. If the adapter returns a non-null object that is not an instance of the wrapped expected raw type, a descriptive ClassCastException is thrown. EOFException before any token yields null (legacy empty-document behavior); EOFException after content, IllegalStateException, and other IOExceptions are rethrown as JsonSyntaxException; AssertionError is rewrapped with the Gson version. Unlike the Reader overloads, trailing data is not rejected. The reader's original strictness is restored in finally.

<a id="u-655c28b6aebc"></a>
### `Gson.java-fromjson-from-reader`

`public <T> T fromJson(Reader json, Class<T> classOfT) throws JsonSyntaxException, Jso…` · [gson/src/main/java/com/google/gson/Gson.java:L940-L943][f1]

Deserialize JSON from a Reader.

The Class and Type variants convert to a TypeToken (Type variant unchecked); the TypeToken variant creates a reader via newJsonReader, delegates to the JsonReader overload, then calls assertFullConsumption so multiple top-level elements or trailing data throw JsonSyntaxException. Returns null when the reader is at EOF.

<a id="u-445271d3318b"></a>
### `Gson.java-fromjson-from-string`

`public <T> T fromJson(String json, Class<T> classOfT) throws JsonSyntaxException` · [gson/src/main/java/com/google/gson/Gson.java:L850-L852][f1]

Deserialize a JSON string by wrapping it in a StringReader and delegating to the Reader-based overloads.

The Class and Type variants convert their argument to a TypeToken (the Type variant is unchecked and not type-safe); the TypeToken variant returns null for a null json string. All inherit the trailing-data check of the Reader path.

<a id="u-5288a15a4d49"></a>
### `Gson.java-futuretypeadapter`

`class FutureTypeAdapter<T> extends SerializationDelegatingTypeAdapter<T>` · [gson/src/main/java/com/google/gson/Gson.java:L1239-L1240][f1]

A proxy TypeAdapter for cyclic type graphs, returned by getAdapter while the real adapter is still being constructed.

setDelegate wires the real adapter exactly once; a second call throws AssertionError. All of read, write, and getSerializationDelegate go through delegate(), which throws IllegalStateException if the delegate has not been set yet — possible if the proxy leaks to another thread or is used inside the factory that requested it. Setting the delegate is not thread-safe, so instances must not be published before the delegate is set.

<a id="u-2b1cda4fd264"></a>
### `Gson.java-gson-class-and-configuration-state`

`class Gson` · [gson/src/main/java/com/google/gson/Gson.java:L156-L158][f1]

Gson is the main thread-safe entry class for converting Java objects to JSON and back, delegating actual (de)serialization to TypeAdapters produced by a factory list.

Its configuration (excluder, field naming strategy, serializeNulls, htmlSafe, formatting style, strictness, date settings, number strategies, reflection filters, and the factory lists) is copied from a GsonBuilder at construction and is effectively immutable afterwards. Adapter resolution state lives in a ConcurrentHashMap shared across threads and a ThreadLocal map used only during in-flight getAdapter calls to break cycles. The package-private constructor reuses shared default singletons when built from GsonBuilder.DEFAULT; otherwise it creates a fresh ConstructorConstructor, JsonAdapterAnnotationTypeAdapterFactory, and factory list.

<a id="u-587fba776514"></a>
### `Gson.java-tojson-jsonelement-to-string-or-appendable`

`public String toJson(JsonElement jsonElement)` · [gson/src/main/java/com/google/gson/Gson.java:L708-L712][f1]

Convert a JsonElement tree to JSON text.

The string overload builds into a StringBuilder; the Appendable overload wraps it via Streams.writerForAppendable and newJsonWriter. IOException is rethrown as JsonIOException.

<a id="u-0197cdc39c28"></a>
### `Gson.java-tojson-to-string-or-appendable`

`public String toJson(Object src)` · [gson/src/main/java/com/google/gson/Gson.java:L565-L570][f1]

Serialize an object to a JSON string or Appendable.

toJson(Object) maps null to JsonNull and otherwise uses the runtime class; toJson(Object,Type) builds into a StringBuilder and returns its text. The Appendable overloads wrap the target via Streams.writerForAppendable and a newJsonWriter; the single-arg version handles null src by serializing JsonNull. Any IOException from writing is rethrown as JsonIOException.

<a id="u-9a9029e0e7c3"></a>
### `JsonReader.java-strictness-accessors`

`public final void setStrictness(Strictness strictness)` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L411-L414][f2]

setStrictness replaces the parser strictness (STRICT, LEGACY_STRICT, LENIENT) after a non-null check that throws NullPointerException; getStrictness returns the current value.

The strictness value gates leniency checks, keyword casing, control-character and surrogate validation, and NaN/Infinity acceptance throughout the parser.

<a id="u-67180c2c82d6"></a>
### `JsonWriter.java-html-safe-and-null-serialization-flags`

`public final void setHtmlSafe(boolean htmlSafe)` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L367-L369][f3]

setHtmlSafe toggles escaping of <, >, &, = and ' in strings (isHtmlSafe reads it back).

setSerializeNulls controls whether object members with null values are emitted; when false, nullValue() skips both the deferred name and the literal, and this has no effect on array elements. Both default to false/true respectively; accessors are trivial.

<a id="u-30ace827aea2"></a>
### `JsonWriter.java-strictness-configuration`

`@Deprecated // Don't specify @InlineMe, so caller with setLenient(false) becomes aw…` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L309-L315][f3]

Deprecated setLenient maps true to Strictness.LENIENT and false to LEGACY_STRICT; isLenient reports whether the current strictness is LENIENT.

setStrictness requires non-null (NPE otherwise); under LENIENT the writer permits NaN/infinity values and multiple top-level values, while STRICT and LEGACY_STRICT behave identically and reject both. getStrictness returns the current value.

<a id="u-aba635b1ca2a"></a>
### `TypeToken.java-typetoken-factories`

`public static TypeToken<?> get(Type type)` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L355-L357][f4]

Static factories producing TypeToken instances via the private canonicalizing constructor.

get(Type) and get(Class) wrap the given type directly. getParameterized requires a non-null Class raw type and non-null arguments array; it throws IllegalArgumentException if rawType is not a Class, if the argument count differs from the class's type-parameter count, or if the raw type requires an owner type; with zero arguments it delegates to get(Class) for legacy behavior; otherwise each argument must be non-null and satisfy every bound of the corresponding type variable (checked via raw-type assignability, else IllegalArgumentException), and the result wraps GsonTypes.newParameterizedTypeWithOwner(null, rawClass, typeArguments). getArray wraps GsonTypes.arrayOf(componentType).

<a id="u-3e77e2a78ca8"></a>
### `Gson.assertFullConsumption`

`private static void assertFullConsumption(Object obj, JsonReader reader)` · [gson/src/main/java/com/google/gson/Gson.java:L1219-L1229][f1]

Guards the Reader-based fromJson path: if a non-null result was produced but the reader's next token is not END_DOCUMENT, throws JsonSyntaxException("JSON document was not fully consumed.").

MalformedJsonException from the peek is rethrown as JsonSyntaxException; other IOExceptions as JsonIOException. A null result (empty document) skips the check.

<a id="u-276006924613"></a>
### `Gson.getAdapter`

`public <T> TypeAdapter<T> getAdapter(TypeToken<T> type)` · [gson/src/main/java/com/google/gson/Gson.java:L340-L399][f1]

Returns the type adapter for a type, caching results per type token.

A cache hit returns immediately. On a miss it uses a ThreadLocal map of in-progress lookups: a reentrant request for the same type returns the FutureTypeAdapter placeholder registered earlier, preventing stack overflow on cyclic type graphs. Otherwise it registers a FutureTypeAdapter, iterates the factories in order, and wires the first non-null candidate into the placeholder and the thread-local map. If no factory matches, it throws IllegalArgumentException naming the Gson version and the type. Only the outermost (initial) request removes the ThreadLocal and publishes all resolved adapters from that call into the shared cache; publishing only at the outer level avoids caching adapters that still reference unresolved placeholders in cyclic graphs (issue 625). Concurrent lookups may produce different adapter instances, which is acceptable because adapters are expected to be stateless.

**Notes.**

- failure: type == null throws NullPointerException via Objects.requireNonNull.

calls: [Gson.java-futuretypeadapter](gson-entry-point-and-streaming.md#u-5288a15a4d49); group: [gson/src/main/java/com/google/gson/Gson.java:Gson.getAdapter](core-adapter-abstractions-and-time.md#u-0f01c122fbe8)

<a id="u-1551dc685e3f"></a>
### `Gson.getDelegateAdapter`

`public <T> TypeAdapter<T> getDelegateAdapter(TypeAdapterFactory skipPast, TypeToken<T…` · [gson/src/main/java/com/google/gson/Gson.java:L472-L503][f1]

Returns an adapter for a type from the first factory after skipPast in the factory list, letting a custom factory delegate to the default handling.

If the type carries a class-level @JsonAdapter whose factory is skipPast, skipPast is replaced by the annotation factory so the annotated factory itself is skipped. Factories before skipPast are ignored; the first subsequent factory returning a non-null adapter wins. If skipPast was found but no factory matched, IllegalArgumentException is thrown; if skipPast is not in the list at all (e.g. a field-level @JsonAdapter factory), it falls back to plain getAdapter, which may return the very adapter the caller intended to bypass.

**Notes.**

- failure: null skipPast or type throws NullPointerException.

calls: [Gson.getAdapter](gson-entry-point-and-streaming.md#u-276006924613)

<a id="u-c2edc8d38fa9"></a>
### `Gson.newBuilder`

`public GsonBuilder newBuilder()` · [gson/src/main/java/com/google/gson/Gson.java:L287-L289][f1]

Returns a new GsonBuilder pre-populated with this instance's custom factories and configuration, allowing derived configurations.

<a id="u-baefedbf0e0d"></a>
### `Gson.newJsonReader`

`public JsonReader newJsonReader(Reader reader)` · [gson/src/main/java/com/google/gson/Gson.java:L821-L825][f1]

Creates a JsonReader over the given Reader with this instance's strictness, defaulting to LEGACY_STRICT when no explicit strictness was configured.

<a id="u-faaa0b004821"></a>
### `Gson.newJsonWriter`

`public JsonWriter newJsonWriter(Writer writer) throws IOException` · [gson/src/main/java/com/google/gson/Gson.java:L797-L807][f1]

Creates a JsonWriter over the given Writer configured with this instance's settings: formatting style, htmlSafe, serializeNulls, and strictness (LEGACY_STRICT when none was set).

If generateNonExecutableJson is enabled, the four-byte prefix )}'\n is written to the underlying writer first, which can throw IOException.

<a id="u-2af0f7a3d0f7"></a>
### `gson/src/main/java/com/google/gson/Gson.java:Gson.toJson (4)`

`public void toJson(Object src, Type typeOfSrc, JsonWriter writer) throws JsonIOException` · [gson/src/main/java/com/google/gson/Gson.java:L670-L699][f1]

Writes src of the given type to a caller-supplied JsonWriter using the adapter for typeOfSrc.

Strictness handling: if this instance has an explicit strictness it is forced onto the writer; otherwise a writer at default LEGACY_STRICT is switched to LENIENT for backward compatibility, and other writer strictness values are left alone. The instance's htmlSafe and serializeNulls settings are applied, and all three writer settings are restored in a finally block. IOException from adapter.write becomes JsonIOException; AssertionError is rethrown wrapped with the Gson version. The adapter is looked up via TypeToken.get(typeOfSrc), so a null type would fail there.

<a id="u-d2d843f1faaf"></a>
### `gson/src/main/java/com/google/gson/Gson.java:Gson.toJson (7)`

`public void toJson(JsonElement jsonElement, JsonWriter writer) throws JsonIOException` · [gson/src/main/java/com/google/gson/Gson.java:L751-L778][f1]

Writes a JsonElement tree to a caller-supplied JsonWriter via Streams.write, with the same strictness/htmlSafe/serializeNulls save-apply-restore protocol as the object overload: explicit instance strictness is forced, otherwise LEGACY_STRICT writers are switched to LENIENT, and all settings are restored in finally.

IOException becomes JsonIOException; AssertionError is rewrapped with the Gson version.

<a id="u-53176d7706d4"></a>
### `Gson.toString`

`@Override public String toString()` · [gson/src/main/java/com/google/gson/Gson.java:L1278-L1287][f1]

Returns a debug string showing serializeNulls, the factory list, and the instance creators (via the ConstructorConstructor's toString).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/Gson.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonReader.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonWriter.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/reflect/TypeToken.java
