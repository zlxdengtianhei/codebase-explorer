# Gson serialization facade

**Capability.** Provides Gson serialization/deserialization entry points, adapter lookup, reader/writer creation, and configuration round-tripping.

Use for top-level Gson conversion APIs and adapter resolution. Units show adapter caching, toJson/fromJson overloads, writer/reader creation, and builder round-trip.

**Depends on.**

- [JSON writer formatting](json-writer-formatting.md) · graph-confirmed · 2 edge(s) · The Gson serialization facade uses JSON writer formatting to emit serialized output.
- [Generic type reflection](generic-type-reflection.md) · graph-only · 9 edge(s)
- [Stream serialization helpers](stream-serialization-helpers.md) · graph-only · 3 edge(s)
- [Gson annotation adapter support](gson-annotation-adapter-support.md) · graph-only · 1 edge(s)
- [JSON primitive values](json-primitive-values.md) · graph-only · 1 edge(s)

**Depended on by.**

- [JSON writer formatting](json-writer-formatting.md) · graph-confirmed · 4 edge(s)
- [Java time and SQL adapters](java-time-and-sql-adapters.md) · graph-only · 8 edge(s)
- [Public API utility classes](public-api-utility-classes.md) · graph-only · 3 edge(s)
- [Map type adapter factory](map-type-adapter-factory.md) · graph-only · 2 edge(s)
- [Core Gson default adapters](core-gson-default-adapters.md) · graph-only · 1 edge(s)
- [Enum runtime adapter selection](enum-runtime-adapter-selection.md) · graph-only · 1 edge(s)
- [Generic type reflection](generic-type-reflection.md) · graph-only · 1 edge(s)
- [Gson builder configuration](gson-builder-configuration.md) · graph-only · 1 edge(s)

Parent: [Serialization facade and writing](serialization-facade-and-writing.md)

## Units (27)

<a id="u-cbbb13d974ba"></a>
### `Gson.java-adapter-and-configuration-accessor-documentation`

`class Gson` · [gson/src/main/java/com/google/gson/Gson.java:L278-L287][f1]

These documentation blocks state contracts for builder round-tripping, configuration queries, and adapter lookup.

The builder-returning block says the new builder carries current custom factories and configuration. The flag queries report serialize-null and HTML-safe settings. Adapter lookup returns an adapter for the type and throws IllegalArgumentException when no factory can handle it; concurrent calls for the same type may return different instances. Delegate lookup skips factories up to and including the supplied factory, throws IllegalArgumentException if that factory was found but no later factory matches, and falls back to ordinary adapter lookup when the supplied factory is not found, including field-level annotation cases.

<a id="u-4084f895620a"></a>
### `Gson.java-adapter-lookup`

`public <T> TypeAdapter<T> getAdapter(TypeToken<T> type)` · [gson/src/main/java/com/google/gson/Gson.java:L340-L399][f1]

Resolves and caches a TypeAdapter for a type, using a thread-local map to handle cyclic adapter creation.

The Class overload wraps the class in a TypeToken. The TypeToken overload rejects null, returns a cached adapter if present, and returns an in-progress adapter for the same type. Otherwise it installs a FutureTypeAdapter, asks each factory in order for an adapter, wires the first non-null result into the future adapter, and replaces the thread-local entry. If no factory matches it throws IllegalArgumentException naming the Gson version and type. Only the initial request publishes all thread-local results to the shared cache; concurrent requests for the same type may therefore see different adapter instances. The thread-local map is removed when the initial request finishes.

<a id="u-54ea9086393a"></a>
### `Gson.java-deserialization-overload-documentation`

`class Gson` · [gson/src/main/java/com/google/gson/Gson.java:L825-L850][f1]

These documentation blocks describe the fromJson overloads for strings, readers, JSON readers, and JSON trees.

String, Reader, and JsonElement overloads return null for null, empty, or EOF input and enforce full consumption, throwing JsonSyntaxException on trailing data; the JsonReader overload reads only the next value and does not enforce full consumption. Reader and JsonReader overloads may throw JsonIOException for read failures and JsonSyntaxException for malformed or mismatched JSON. The JsonReader overload applies the instance strictness and restores the reader's previous strictness.

<a id="u-5288a15a4d49"></a>
### `Gson.java-futuretypeadapter`

`class FutureTypeAdapter<T> extends SerializationDelegatingTypeAdapter<T>` · [gson/src/main/java/com/google/gson/Gson.java:L1239-L1240][f1]

FutureTypeAdapter is a proxy adapter used while resolving cyclic type-adapter dependencies.

setDelegate accepts one delegate and throws AssertionError if called again. delegate() throws IllegalStateException when no delegate has been set, covering leaked or prematurely used proxies. getSerializationDelegate, read, and write all forward to the resolved delegate. The class is not thread-safe until its delegate is set.

<a id="u-c3f7bf54fa87"></a>
### `Gson.java-json-appendable-serialization`

`public void toJson(Object src, Appendable writer) throws JsonIOException` · [gson/src/main/java/com/google/gson/Gson.java:L612-L618][f1]

Serializes an object to an Appendable, using runtime type when no explicit type is supplied.

A null source serializes JsonNull.INSTANCE. It wraps the Appendable with Streams.writerForAppendable, creates a configured JsonWriter, and delegates to the core writer overload. Any IOException is wrapped in JsonIOException.

<a id="u-e95a37885d40"></a>
### `Gson.java-json-element-string-appendable-serialization`

`public String toJson(JsonElement jsonElement)` · [gson/src/main/java/com/google/gson/Gson.java:L708-L712][f1]

Serializes a JsonElement to a string or Appendable using a configured JsonWriter.

The string overload writes into a StringBuilder. The Appendable overload wraps the target with Streams.writerForAppendable, creates a configured JsonWriter, and delegates to the JsonWriter overload. IOException is wrapped in JsonIOException.

<a id="u-3a9e20b98b94"></a>
### `Gson.java-json-reader-core-deserialization`

`@SuppressWarnings({"unchecked", "TypeParameterUnusedInFormals"}) public <T> T fromJso…` · [gson/src/main/java/com/google/gson/Gson.java:L1045-L1049][f1]

Reads one JSON value from a JsonReader into the requested type and restores reader strictness.

The Type overload wraps the target in TypeToken.get. It saves strictness, applies explicit strictness or converts LEGACY_STRICT to LENIENT, peeks to detect EOF, resolves an adapter, and reads. If the result is non-null, it verifies the result is an instance of the wrapped raw type and throws ClassCastException on mismatch; a null result skips that check. EOF on an empty document returns null; EOF after content, IllegalStateException, and IOException become JsonSyntaxException; AssertionError is wrapped with the Gson version. Old strictness is restored in finally.

<a id="u-f30ebbd8c05c"></a>
### `Gson.java-json-reader-deserialization`

`public <T> T fromJson(Reader json, Class<T> classOfT) throws JsonSyntaxException, Jso…` · [gson/src/main/java/com/google/gson/Gson.java:L940-L943][f1]

Deserializes JSON from a Reader into an object, using a Class, Type, or TypeToken target.

Class and Type overloads wrap the target in TypeToken.get. The TypeToken overload creates a configured JsonReader, calls the core JsonReader/TypeToken path, then asserts full consumption. A null result from EOF skips the full-consumption check.

<a id="u-ea25e4834c65"></a>
### `Gson.java-json-stream-factories`

`public JsonWriter newJsonWriter(Writer writer) throws IOException` · [gson/src/main/java/com/google/gson/Gson.java:L797-L807][f1]

Creates JsonWriter and JsonReader instances configured from this Gson instance.

The writer factory first writes the five-character prefix `)]}'` followed by a newline when non-executable JSON is enabled, then sets formatting style, HTML safety, strictness (explicit or LEGACY_STRICT), and serialize-null behavior. The reader factory sets strictness to explicit or LEGACY_STRICT. Writer prefix I/O failures propagate as IOException.

<a id="u-da3843c63191"></a>
### `Gson.java-json-string-deserialization`

`public <T> T fromJson(String json, Class<T> classOfT) throws JsonSyntaxException` · [gson/src/main/java/com/google/gson/Gson.java:L850-L852][f1]

Deserializes JSON text into an object, using a Class, Type, or TypeToken target.

Class and Type overloads wrap the target in TypeToken.get. The TypeToken overload returns null for null input, wraps the text in a StringReader, and delegates to the Reader/TypeToken path, which enforces full consumption.

<a id="u-69df3f5877d2"></a>
### `Gson.java-json-string-serialization`

`public String toJson(Object src)` · [gson/src/main/java/com/google/gson/Gson.java:L565-L570][f1]

Serializes an object to a JSON string, using runtime type when no explicit type is supplied.

A null source serializes JsonNull.INSTANCE. The explicit-type overload writes into a StringBuilder through the core toJson path and returns its contents.

<a id="u-e9cb088ce1e7"></a>
### `Gson.java-json-tree-deserialization`

`public <T> T fromJson(JsonElement json, Class<T> classOfT) throws JsonSyntaxException` · [gson/src/main/java/com/google/gson/Gson.java:L1159-L1161][f1]

Deserializes a JsonElement tree into an object, using a Class, Type, or TypeToken target.

Class and Type overloads wrap the target in TypeToken.get. The TypeToken overload returns null for null input, wraps the tree in a JsonTreeReader, and delegates to the core JsonReader/TypeToken path without an extra full-consumption check.

<a id="u-ecdf1c00d516"></a>
### `Gson.java-json-tree-serialization`

`public JsonElement toJsonTree(Object src)` · [gson/src/main/java/com/google/gson/Gson.java:L519-L524][f1]

Serializes an object into a JsonElement tree, using runtime type when no explicit type is supplied.

A null source returns JsonNull.INSTANCE. The explicit-type overload writes through a JsonTreeWriter via the core toJson path and returns the writer's root element.

<a id="u-05dce34bd362"></a>
### `Gson.java-reader-and-writer-factory-documentation`

`class Gson` · [gson/src/main/java/com/google/gson/Gson.java:L778-L797][f1]

These documentation blocks specify how newJsonWriter and newJsonReader apply instance settings.

The writer receives formatting style, HTML-safe, serialize-null, and strictness settings; if no explicit strictness is configured, the writer gets LEGACY_STRICT. The reader receives the configured strictness, or LEGACY_STRICT when none is set. The writer documentation also lists the non-executable prefix and pretty-printing options as considered settings.

<a id="u-7740a86957cf"></a>
### `Gson.java-serialization-overload-documentation`

`class Gson` · [gson/src/main/java/com/google/gson/Gson.java:L503-L519][f1]

These documentation blocks describe the toJsonTree and toJson overloads.

The no-type overloads use the runtime class, so generic type information is lost; explicit type overloads preserve it. Null source is represented as JsonNull. Appendable and Writer overloads report write failures as JsonIOException. The JsonWriter overload applies the instance's strictness, HTML-safe, and serialize-null settings and restores the writer's previous settings afterward; an explicit instance strictness overrides the writer, while an unset strictness turns a LEGACY_STRICT writer into LENIENT.

<a id="u-cdb72fb61d84"></a>
### `JsonReader.java-strictness-configuration`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L355-L411][f2]

Strictness configuration and query.

The setter rejects null with NullPointerException and otherwise stores the value; the getter returns it. The selected mode changes later parsing acceptance, including keyword case, escapes, comments, separators, and NaN/Infinity handling.

<a id="u-67180c2c82d6"></a>
### `JsonWriter.java-html-safe-and-null-serialization-flags`

`public final void setHtmlSafe(boolean htmlSafe)` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L367-L369][f3]

Toggles whether strings use HTML-safe escaping and whether object members with null values are written.

Both setters store the boolean directly; the getters return the stored flags. Null serialization affects object members only, not array elements.

<a id="u-30ace827aea2"></a>
### `JsonWriter.java-strictness-configuration`

`@Deprecated // Don't specify @InlineMe, so caller with setLenient(false) becomes aw…` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L309-L315][f3]

Configures and reports strictness.

The deprecated boolean setter maps true to LENIENT and false to LEGACY_STRICT; the direct setter null-checks and stores the value. The boolean query is true only for LENIENT, and the getter returns the stored strictness.

<a id="u-c7be4ceef8fe"></a>
### `TreeTypeAdapter.java-gsoncontextimpl`

`class GsonContextImpl implements JsonSerializationContext, JsonDeserializationContext` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L191-L193][f4]

Context implementation passed to tree serializers/deserializers.

serialize(src) calls Gson.toJsonTree(src); serialize(src,type) calls Gson.toJsonTree(src,type); deserialize(json,type) calls Gson.fromJson(json,type).

<a id="u-b379491c2fae"></a>
### `gson/src/main/java/com/google/gson/Gson.java:Gson`

`class Gson` · [gson/src/main/java/com/google/gson/Gson.java:L202-L243][f1]

This API documentation block enumerates the default settings of the no-argument constructor.

It states compact JSON, omitted null fields, built-in adapters for common types, default date formatting, ignored Expose and Since annotations, Java field naming, exclusion of transient and static fields, and no explicit strictness.

<a id="u-c32be3021027"></a>
### `gson/src/main/java/com/google/gson/Gson.java:Gson (27)`

`class Gson` · [gson/src/main/java/com/google/gson/Gson.java:L1229-L1239][f1]

This documentation block describes the FutureTypeAdapter proxy used for cyclic type graphs.

It states that setting the delegate is not thread-safe and instances must be published only after the delegate is set; using the proxy before resolution throws IllegalStateException.

<a id="u-3e77e2a78ca8"></a>
### `Gson.assertFullConsumption`

`private static void assertFullConsumption(Object obj, JsonReader reader)` · [gson/src/main/java/com/google/gson/Gson.java:L1219-L1229][f1]

Checks that a non-null deserialized result consumed the entire JSON document.

If the result is non-null and the reader's next token is not END_DOCUMENT, it throws JsonSyntaxException. MalformedJsonException becomes JsonSyntaxException; other IOException becomes JsonIOException. A null result skips the check.

<a id="u-1551dc685e3f"></a>
### `Gson.getDelegateAdapter`

`public <T> TypeAdapter<T> getDelegateAdapter(TypeAdapterFactory skipPast, TypeToken<T…` · [gson/src/main/java/com/google/gson/Gson.java:L472-L503][f1]

Finds the next adapter after a given factory, optionally falling back to normal adapter lookup.

It rejects null skipPast or type. If the JSON-adapter annotation factory identifies the type and skipPast, it substitutes that factory as the skip point. It scans factories in order, skips until the identity match, and returns the first non-null adapter after it. If the skip point was found but no later factory matches, it throws IllegalArgumentException; if the skip point was never found, it delegates to getAdapter(type).

<a id="u-c2edc8d38fa9"></a>
### `Gson.newBuilder`

`public GsonBuilder newBuilder()` · [gson/src/main/java/com/google/gson/Gson.java:L287-L289][f1]

Returns a new GsonBuilder initialized from this instance's configuration and custom factories.

<a id="u-2af0f7a3d0f7"></a>
### `gson/src/main/java/com/google/gson/Gson.java:Gson.toJson (4)`

`public void toJson(Object src, Type typeOfSrc, JsonWriter writer) throws JsonIOException` · [gson/src/main/java/com/google/gson/Gson.java:L670-L699][f1]

Writes an object of a given type to a supplied JsonWriter using the resolved adapter.

It saves the writer's strictness, HTML-safe, and serialize-null settings. If this instance has explicit strictness it applies it; otherwise a writer at LEGACY_STRICT is switched to LENIENT. It applies this instance's HTML-safe and serialize-null settings, writes through the adapter, wraps IOException in JsonIOException, wraps AssertionError with the Gson version, and restores all three writer settings in finally.

<a id="u-d2d843f1faaf"></a>
### `gson/src/main/java/com/google/gson/Gson.java:Gson.toJson (7)`

`public void toJson(JsonElement jsonElement, JsonWriter writer) throws JsonIOException` · [gson/src/main/java/com/google/gson/Gson.java:L751-L778][f1]

Writes a JsonElement to a supplied JsonWriter with this instance's settings.

It saves and then applies HTML-safe and serialize-null settings; explicit strictness overrides the writer, otherwise LEGACY_STRICT becomes LENIENT. It writes via Streams.write, wraps IOException in JsonIOException, wraps AssertionError with the Gson version, and restores the saved settings in finally.

<a id="u-53176d7706d4"></a>
### `Gson.toString`

`@Override public String toString()` · [gson/src/main/java/com/google/gson/Gson.java:L1278-L1287][f1]

Returns a diagnostic string containing serializeNulls, factories, and constructorConstructor.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/Gson.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonReader.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonWriter.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java
