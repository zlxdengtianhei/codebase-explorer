# Gson Facade and Conversion API

**Capability.** Owns the public Gson entry points: immutable configuration applied to JsonReader/JsonWriter, adapter lookup and caching (including cyclic-type and delegate resolution), and the toJson/fromJson/toJsonTree overload families funneling into the core reader/writer paths; also holds output-formatting and Long serialization policy value objects.

Use this subtree for every top-level object-to-JSON conversion and to see how configuration (strictness, FormattingStyle, LongSerializationPolicy) propagates into the streaming layer.

**Depends on.**

- [TypeAdapter Framework](r1-adapter-framework.md) · model-inferred · 0 edge(s) · The facade performs adapter lookup, caching, and delegate resolution through the TypeAdapter framework when running conversions.
- [Streaming JSON Reading](r1-streaming-json.md) · graph-confirmed · 6 edge(s) · The facade creates and configures JsonReader instances that parsing facades and conversions read through.
- [Runtime Generic Type Model](r1-type-model.md) · graph-confirmed · 11 edge(s) · fromJson/toJson/getAdapter resolve user-supplied generic types via TypeToken and GsonTypes.
- [Streaming JSON Writer and Lexical Model](r2-streaming.md) · graph-only · 26 edge(s)
- [Builder and Naming Configuration](r2-configuration.md) · graph-only · 4 edge(s)
- [Internal Utilities and Data Structures](r2-infrastructure.md) · graph-only · 3 edge(s)
- [Internal Support Utilities](r1-internal-support.md) · graph-only · 1 edge(s)
- [@JsonAdapter Annotation Handling](r2-jsonadapter-annotation-factory.md) · graph-only · 1 edge(s)
- [Tree-Bound Writer](r2-tree-writer.md) · graph-only · 1 edge(s)

**Depended on by.**

- [TypeAdapter Framework](r1-adapter-framework.md) · graph-confirmed · 5 edge(s)
- [Built-in Type Adapters](r1-builtin-adapters.md) · graph-confirmed · 9 edge(s)
- [java.time Adapters](r1-java-time-adapters.md) · graph-confirmed · 7 edge(s) · Composite java.time adapters resolve their sub-adapters via Gson.getAdapter.
- [Exclusion and Reflection Policy](r1-reflection-policy.md) · graph-confirmed · 1 edge(s) · Excluder.create delegates to Gson.getDelegateAdapter when wiring into the factory chain.
- [Tree-Style Serializer Bridge](r1-tree-adapter-bridge.md) · graph-confirmed · 4 edge(s) · TreeTypeAdapter's GsonContextImpl forwards nested serialize/deserialize requests to the Gson facade overloads.
- [Streaming JSON Writer and Lexical Model](r2-streaming.md) · graph-only · 7 edge(s)
- [Collection, Map, and Tree Adapters](r2-collection-map-adapters.md) · graph-only · 3 edge(s)

Parent: [Gson JSON Binding Library](r1-gson-root.md)

## Units (17)

<a id="u-e84909a2abed"></a>
### `Gson`

`class Gson` · [gson/src/main/java/com/google/gson/Gson.java:L156-L243][f1]

Main Gson facade converting Java objects to JSON and back, holding immutable builder configuration and a type-adapter cache.

Configuration (excluder, field naming, serializeNulls, htmlSafe, formattingStyle, strictness, number strategies, reflection filters, factory lists) is copied from a GsonBuilder at construction and never mutated afterward. A ConcurrentHashMap caches TypeAdapter instances per TypeToken, and a ThreadLocal map guards reentrant adapter creation. Trivial accessors newBuilder(), excluder(), fieldNamingStrategy(), serializeNulls(), htmlSafe() return the corresponding field or a new GsonBuilder(this); toString() reports serializeNulls, factories, and instanceCreators.

**Notes.**

- side_effect: Adapter lookups populate typeTokenCache, so reusing one Gson instance amortizes adapter creation.

calls: [gson/src/main/java/com/google/gson/Gson.java:Gson (35)](r1-facade-api.md#u-b738e22e796c)

<a id="u-b738e22e796c"></a>
### `gson/src/main/java/com/google/gson/Gson.java:Gson (35)`

`Gson(GsonBuilder builder)` · [gson/src/main/java/com/google/gson/Gson.java:L247-L278][f1]

Builds a Gson instance by copying every configuration field from the given GsonBuilder, wrapping instanceCreators in a HashMap and freezing factory lists into immutable lists.

The default-config branch (builder == GsonBuilder.DEFAULT) reuses shared static defaults for constructorConstructor, the @JsonAdapter annotation factory, and the factory list; otherwise it constructs a new ConstructorConstructor from instanceCreators, useJdkUnsafe and reflectionFilters, a new JsonAdapterAnnotationTypeAdapterFactory over it, and derives factories via builder.createFactories. The no-argument constructor simply delegates with GsonBuilder.DEFAULT.

uses: [Gson](r1-facade-api.md#u-e84909a2abed); calls: [GsonBuilder.createFactories](r2-configuration.md#u-f54ca5b55863)

<a id="u-2a2c3116185a"></a>
### `gson-tojson-convenience`

`public String toJson(Object src)` · [gson/src/main/java/com/google/gson/Gson.java:L565-L570][f1]

Convenience serialization entry points that reduce to the JsonWriter-based overload.

toJson(Object) returns toJson(JsonNull.INSTANCE) for null, else uses src.getClass() (erasure applies). toJson(Object, Type) writes into a StringBuilder and returns its string. toJson(Object, Appendable) branches on null and forwards to the typed overload. toJson(Object, Type, Appendable) wraps the Appendable via Streams.writerForAppendable, creates a JsonWriter with newJsonWriter, delegates to the JsonWriter overload, and converts any IOException into JsonIOException.

calls: [gson/src/main/java/com/google/gson/Gson.java:Gson.toJson (4)](r1-facade-api.md#u-2af0f7a3d0f7), [Streams](r2-infrastructure.md#u-931987e48ef4)

<a id="u-259ca2b9b721"></a>
### `gson-tojson-element`

`public String toJson(JsonElement jsonElement)` · [gson/src/main/java/com/google/gson/Gson.java:L708-L712][f1]

Serializes a JsonElement tree to text or an Appendable.

toJson(JsonElement) buffers into a StringBuilder and returns the string; toJson(JsonElement, Appendable) wraps the Appendable via Streams.writerForAppendable, creates a JsonWriter through newJsonWriter, and delegates to the JsonWriter overload, converting IOException to JsonIOException.

calls: [gson/src/main/java/com/google/gson/Gson.java:Gson.toJson (7)](r1-facade-api.md#u-d2d843f1faaf)

<a id="u-0629a3d214ce"></a>
### `gson-tojsontree-overloads`

`public JsonElement toJsonTree(Object src)` · [gson/src/main/java/com/google/gson/Gson.java:L519-L524][f1]

Serializes an object into a JsonElement tree instead of text.

toJsonTree(Object) returns JsonNull.INSTANCE for null and otherwise uses src.getClass(), losing generic type information; toJsonTree(Object, Type) accepts an explicit (possibly parameterized) type. Both run the normal toJson pipeline into a JsonTreeWriter and return writer.get(), so the resulting tree reflects this instance's exclusion, naming, and adapter configuration.

calls: [gson/src/main/java/com/google/gson/Gson.java:Gson.toJson (4)](r1-facade-api.md#u-2af0f7a3d0f7)

<a id="u-2af0f7a3d0f7"></a>
### `gson/src/main/java/com/google/gson/Gson.java:Gson.toJson (4)`

`public void toJson(Object src, Type typeOfSrc, JsonWriter writer) throws JsonIOException` · [gson/src/main/java/com/google/gson/Gson.java:L670-L699][f1]

Core serialization path: looks up the adapter for typeOfSrc, then temporarily applies this instance's writer settings before writing.

The adapter lookup uses getAdapter(TypeToken.get(typeOfSrc)). Strictness: if this.strictness is set it overrides the writer; otherwise a writer in default LEGACY_STRICT is switched to LENIENT for backward compatibility. htmlSafe and serializeNulls from this instance are applied; on IOException the method throws JsonIOException; AssertionError is rethrown with the Gson version prepended. A finally block restores the writer's original strictness, htmlSafe, and serializeNulls, so the writer's configuration is unchanged whether the write succeeds or fails.

**Notes.**

- side_effect: The provided JsonWriter's settings are mutated during the call and restored afterwards, even on exception.

calls: [Gson.getAdapter](r1-facade-api.md#u-276006924613), [type-token-class](r1-type-model.md#u-55a9c25d6eea)

<a id="u-d2d843f1faaf"></a>
### `gson/src/main/java/com/google/gson/Gson.java:Gson.toJson (7)`

`public void toJson(JsonElement jsonElement, JsonWriter writer) throws JsonIOException` · [gson/src/main/java/com/google/gson/Gson.java:L751-L778][f1]

Writes a JsonElement tree through the provided JsonWriter using Streams.write, applying the same settings handling as the object-typed core overload: this instance's strictness overrides the writer, otherwise LEGACY_STRICT writers are temporarily switched to LENIENT; htmlSafe and serializeNulls from this instance are applied.

IOException is rethrown as JsonIOException; AssertionError is rethrown with the Gson version prepended; the writer's original strictness, htmlSafe, and serializeNulls are restored in finally regardless of outcome.

calls: [Streams](r2-infrastructure.md#u-931987e48ef4)

<a id="u-0ec60cedf37f"></a>
### `gson-fromjson-overloads`

`public <T> T fromJson(String json, Class<T> classOfT) throws JsonSyntaxException` · [gson/src/main/java/com/google/gson/Gson.java:L850-L852][f1]

Deserialization convenience overloads that funnel into the JsonReader/TypeToken core.

String variants return null for a null string and wrap it in a StringReader; Class and raw-Type variants convert to TypeToken via TypeToken.get (the raw-Type variants are unchecked and can be type-unsafe); JsonElement variants return null for a null element and wrap it in a JsonTreeReader. Reader-based variants (fromJson(Reader, Class/Type/TypeToken)) create a reader with newJsonReader, deserialize, then call assertFullConsumption, so trailing data raises JsonSyntaxException. Per docs, String/Reader/JsonElement variants throw when the JSON has multiple top-level elements or trailing data; use the JsonReader variant to avoid that.

calls: [gson/src/main/java/com/google/gson/Gson.java:Gson.fromJson (7)](r1-facade-api.md#u-815b7d4cbb0d), [Gson.assertFullConsumption](r1-facade-api.md#u-3e77e2a78ca8)

<a id="u-815b7d4cbb0d"></a>
### `gson/src/main/java/com/google/gson/Gson.java:Gson.fromJson (7)`

`public <T> T fromJson(JsonReader reader, TypeToken<T> typeOfT) throws JsonIOException…` · [gson/src/main/java/com/google/gson/Gson.java:L1087-L1136][f1]

Core deserialization from a JsonReader into an object of typeOfT, returning null if the reader is at EOF.

Strictness handling mirrors serialization: this.strictness overrides the reader; otherwise a LEGACY_STRICT reader is temporarily switched to LENIENT. After peek() confirms a value exists (clearing the isEmpty flag), the adapter is looked up and read; a non-null result whose wrapped class does not match the requested raw type raises ClassCastException with a diagnostic message. Exception order: EOFException with an empty document returns null (legacy behavior); EOFException after data started, IllegalStateException, and IOException are rethrown as JsonSyntaxException; AssertionError is rethrown with the Gson version prepended. finally restores the reader's original strictness. Unlike other fromJson variants, trailing data is not rejected here.

**Notes.**

- failure: ClassCastException is thrown when a registered adapter returns an instance incompatible with the requested type, catching misregistered adapters.

calls: [Primitives](r1-internal-support.md#u-0f3e35bbee8a), [Gson.getAdapter](r1-facade-api.md#u-276006924613)

**Uncertainties.**

- fromJson(JsonReader, Class) deliberately does not exist (source comment); whether call sites relying on overloads compile is outside this file.

<a id="u-3e77e2a78ca8"></a>
### `Gson.assertFullConsumption`

`private static void assertFullConsumption(Object obj, JsonReader reader)` · [gson/src/main/java/com/google/gson/Gson.java:L1219-L1229][f1]

Verifies that a deserialization consumed the whole document: when the returned object is non-null and reader.peek() is not END_DOCUMENT, throws JsonSyntaxException("JSON document was not fully consumed.").

MalformedJsonException during the peek is rethrown as JsonSyntaxException; other IOException as JsonIOException.

<a id="u-baefedbf0e0d"></a>
### `Gson.newJsonReader`

`public JsonReader newJsonReader(Reader reader)` · [gson/src/main/java/com/google/gson/Gson.java:L821-L825][f1]

Creates a JsonReader over the given Reader whose strictness is this.strictness when explicitly set, otherwise LEGACY_STRICT, so default-configured instances read lenient-by-legacy JSON rather than fully strict JSON.

calls: [JsonReader](r1-streaming-json.md#u-92ec22311967)

<a id="u-faaa0b004821"></a>
### `Gson.newJsonWriter`

`public JsonWriter newJsonWriter(Writer writer) throws IOException` · [gson/src/main/java/com/google/gson/Gson.java:L797-L807][f1]

Creates a JsonWriter over the given Writer configured with this instance's settings, propagating IOException from the underlying writer.

If generateNonExecutableJson is set, the prefix ")]'\n" is written first, making the output safe against inline script execution. The new writer gets this instance's formattingStyle, htmlSafe, and serializeNulls, and its strictness is this.strictness when set, otherwise LEGACY_STRICT.

calls: [jsonwriter-config-accessors](r2-streaming.md#u-cccb91734698)

<a id="u-276006924613"></a>
### `Gson.getAdapter`

`public <T> TypeAdapter<T> getAdapter(TypeToken<T> type)` · [gson/src/main/java/com/google/gson/Gson.java:L340-L399][f1]

Returns the TypeAdapter for a TypeToken, caching it and resolving cyclic type dependencies.

Null argument rejected; cache hit in typeTokenCache returned directly. Otherwise a thread-local map is created for the initial request (or reused for a recursive one); if the recursive map already holds the token, that in-progress adapter (a FutureTypeAdapter placeholder) is returned to break cycles. Factories are probed in registration order; the first non-null adapter is set as the FutureTypeAdapter delegate and replaces it in the thread map. finally removes the thread-local only on the initial request. If no factory produced an adapter, IllegalArgumentException naming the Gson version and type is thrown. Only the initial request publishes all resolved thread-local entries into typeTokenCache, avoiding publication of partially resolved adapters from cycles.

**Notes.**

- condition: Concurrent first-time lookups of the same type may each build and return distinct adapter instances; cache publication happens only from the initial (outermost) call.

uses: [FutureTypeAdapter](r1-facade-api.md#u-0594c5572242); calls: [Gson.getAdapter](r1-facade-api.md#u-276006924613)

<a id="u-1551dc685e3f"></a>
### `Gson.getDelegateAdapter`

`public <T> TypeAdapter<T> getDelegateAdapter(TypeAdapterFactory skipPast, TypeToken<T…` · [gson/src/main/java/com/google/gson/Gson.java:L472-L503][f1]

Returns an adapter for type from the first factory after skipPast, letting callers wrap and delegate to the adapter their own factory would otherwise shadow.

Arguments are null-checked. If the type is itself a class annotated with @JsonAdapter (per jsonAdapterFactory.isClassJsonAdapterFactory), skipPast is advanced to jsonAdapterFactory so the annotation factory is not skipped. Iterating factories: those before skipPast (reference equality) are skipped; the first later factory whose create returns non-null wins. If skipPast was found but nothing matched, IllegalArgumentException is thrown; if skipPast was never found in the list (e.g. a factory only referenced via @JsonAdapter on a field), behavior falls back to getAdapter(type).

calls: [JsonAdapterAnnotationTypeAdapterFactory.isClassJsonAdapterFactory](r2-jsonadapter-annotation-factory.md#u-182401855dac), [Gson.getAdapter](r1-facade-api.md#u-276006924613)

<a id="u-0594c5572242"></a>
### `FutureTypeAdapter`

`class FutureTypeAdapter<T> extends SerializationDelegatingTypeAdapter<T>` · [gson/src/main/java/com/google/gson/Gson.java:L1239-L1242][f1]

Placeholder adapter used by getAdapter to survive cyclic type dependencies.

Until setDelegate is called, delegate is null and any use (read, write, getSerializationDelegate) throws IllegalStateException stating the adapter was used before its dependency resolved; setDelegate throws AssertionError if called twice. Setting the delegate is not thread-safe: it must complete before instances are published to other threads.

<a id="u-674df3655ab3"></a>
### `formattingstyle-java`

`private FormattingStyle(String newline, String indent, boolean spaceAfterSeparators)` · [gson/src/main/java/com/google/gson/FormattingStyle.java:L66-L80][f2]

Immutable value object controlling JSON output formatting: newline, indent, and whether a space follows ',' and ':'.

The only constructor is private and validates its arguments: null newline or indent throws NullPointerException; newline not matching [\r\n]* throws IllegalArgumentException (only \n and \r combinations allowed); indent not matching [ \t]* throws IllegalArgumentException (only spaces and tabs allowed). COMPACT is predefined as empty newline, empty indent, no separator space; PRETTY as "\n", two spaces, separator space true. The with* methods return new instances copying unmodified fields. Graph evidence shows JsonWriter reads getNewline, getIndent, and usesSpaceAfterSeparators when rendering, and that withSpaceAfterSeparators only adds a space after ':' when no newline is configured for ','. Accessors are trivial returns of the final fields.

**Notes.**

- contract: Because with* methods revalidate through the private constructor, any invalid string passed to withNewline or withIndent fails with the same exceptions as construction.

<a id="u-f02f3acb5dbc"></a>
### `LongSerializationPolicy`

`public enum LongSerializationPolicy` · [gson/src/main/java/com/google/gson/LongSerializationPolicy.java:L29-L38][f3]

Enum policy controlling how long/Long values are serialized, selectable via GsonBuilder.

Two constants: DEFAULT emits a JsonPrimitive holding the numeric value (e.g. {"f":123}); STRING emits a JsonPrimitive of the decimal string form (e.g. {"f":"123"}). Both overrides return JsonNull.INSTANCE when the Long argument is null. The abstract serialize(Long) exposes this per-policy formatting; the package-private abstract typeAdapter() returns the internal streaming adapter corresponding to the policy: TypeAdapters.LONG for DEFAULT and TypeAdapters.LONG_AS_STRING for STRING, consumed by GsonBuilder when building a Gson.

uses: [JsonNull](r1-json-element-model.md#u-e36f9a760083), [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java][f4]

**Uncertainties.**

- Behavior of TypeAdapters.LONG and LONG_AS_STRING is defined outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/Gson.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/FormattingStyle.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/LongSerializationPolicy.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java