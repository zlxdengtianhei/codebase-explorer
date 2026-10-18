# Tree-Style Serializer Bridge

**Capability.** Bridges Gson 1.x tree-style JsonSerializer/JsonDeserializer into the streaming TypeAdapter world via TreeTypeAdapter, with SingleTypeFactory binding them to types and GsonContextImpl providing nested serialize/deserialize contexts backed by the shared Gson instance.

Use this subtree when integrating custom (de)serializers: it shows factory matching (exact, raw, hierarchy), lazy delegate fallback, and how the serialization context forwards to the facade.

**Depends on.**

- [Gson Facade and Conversion API](r1-facade-api.md) · graph-confirmed · 4 edge(s) · TreeTypeAdapter's GsonContextImpl forwards nested serialize/deserialize requests to the Gson facade overloads.
- [Runtime Generic Type Model](r1-type-model.md) · graph-only · 8 edge(s)
- [Internal Utilities and Data Structures](r2-infrastructure.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Builder and Naming Configuration](r2-configuration.md) · graph-only · 2 edge(s)

Parent: [TypeAdapter Framework](r1-adapter-framework.md)

## Units (13)

<a id="u-bfcdf89b8b0c"></a>
### `TreeTypeAdapter`

`class TreeTypeAdapter<T> extends SerializationDelegatingTypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L41-L62][f1]

Bridges Gson 1.x tree-style JsonSerializer/JsonDeserializer into the streaming TypeAdapter world.

Stores serializer, deserializer, gson, typeToken, a skipPastForGetDelegateAdapter factory (valid only as skipPast for Gson.getDelegateAdapter), a per-instance GsonContextImpl, and nullSafe. delegate is volatile and lazily created because its construction can fail and Gson promises thread safety; a race may assign it multiple times with the last write winning. Two constructors: the six-argument one sets all fields; the five-argument one delegates with nullSafe=true.

group: [SingleTypeFactory](r1-tree-adapter-bridge.md#u-ffc0a5cc63e4)

<a id="u-ffc0a5cc63e4"></a>
### `SingleTypeFactory`

`class SingleTypeFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L153-L160][f1]

A TypeAdapterFactory binding one serializer/deserializer to a type condition.

Its constructor extracts JsonSerializer/JsonDeserializer roles from the supplied adapter object; if the object is neither, Objects.requireNonNull passes only for non-null and then IllegalArgumentException('Type adapter ... must implement JsonSerializer or JsonDeserializer') is thrown. create computes matches three ways: with exactType set, exactType.equals(type), or when matchRawType also exactType.getType() == type.getRawType(); with exactType null, hierarchyType.isAssignableFrom(type.getRawType()). On match it returns a new TreeTypeAdapter with this factory as skipPast and default nullSafe=true; otherwise null so later factories apply.

calls: [type-token-class](r1-type-model.md#u-55a9c25d6eea)

**Uncertainties.**

- The unchecked cast of serializer/deserializer to the requested T is guarded by the equals/assignability check, per the source comment.

<a id="u-8461cb3ae54f"></a>
### `GsonContextImpl`

`class GsonContextImpl implements JsonSerializationContext, JsonDeserializationContext` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L191-L193][f1]

Implements JsonSerializationContext and JsonDeserializationContext for the enclosing adapter, forwarding to the shared Gson instance.

serialize(Object) returns gson.toJsonTree(src); serialize(Object, Type) returns gson.toJsonTree(src, typeOfSrc); deserialize(JsonElement, Type) returns gson.fromJson(json, typeOfT), so nested conversions use full Gson resolution including other registered adapters.

calls: [gson-fromjson-overloads](r1-facade-api.md#u-0ec60cedf37f), [gson-tojsontree-overloads](r1-facade-api.md#u-0629a3d214ce)

**Uncertainties.**

- deserialize's generic R is unchecked; the caller must supply a matching typeOfT, as the suppression indicates.

<a id="u-55d4a1a7ac2e"></a>
### `TreeTypeAdapter.delegate`

`private TypeAdapter<T> delegate()` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L112-L120][f1]

Lazily resolves the streaming adapter to fall back on via gson.getDelegateAdapter(skipPastForGetDelegateAdapter, typeToken); repeated calls reuse the cached volatile field, and concurrent first calls may compute it redundantly with the last assignment sticking.

calls: [Gson.getDelegateAdapter](r1-facade-api.md#u-1551dc685e3f)

<a id="u-79ad1e7ebb16"></a>
### `TreeTypeAdapter.getSerializationDelegate`

`@Override public TypeAdapter<T> getSerializationDelegate()` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L126-L129][f1]

Returns this when the adapter has a serializer (so serialization goes through the tree path); otherwise returns the lazily resolved delegate.

<a id="u-847456dbc116"></a>
### `TreeTypeAdapter.newFactory`

`public static TypeAdapterFactory newFactory(TypeToken<?> exactType, Object typeAdapter)` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L132-L134][f1]

Returns a SingleTypeFactory matching exactly the given TypeToken (no raw-type or hierarchy matching).

<a id="u-ac1820337c5b"></a>
### `TreeTypeAdapter.newFactoryWithMatchRawType`

`public static TypeAdapterFactory newFactoryWithMatchRawType( TypeToken<?> exactType, …` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L137-L142][f1]

Enables raw-type matching only when exactType.getType() == exactType.getRawType(), i.e. the token itself is a raw type, then wraps in SingleTypeFactory.

<a id="u-48ebb4829b63"></a>
### `TreeTypeAdapter.newTypeHierarchyFactory`

`public static TypeAdapterFactory newTypeHierarchyFactory( Class<?> hierarchyType, Obj…` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L148-L151][f1]

Returns a SingleTypeFactory that matches by assignability to hierarchyType rather than an exact token.

<a id="u-83e464255c1a"></a>
### `TreeTypeAdapter.read`

`@Override public T read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L86-L96][f1]

With no deserializer, reading is fully delegated to delegate().read.

Otherwise Streams.parse turns the stream into a JsonElement; when nullSafe and the tree is JSON null it returns null without invoking user code; otherwise it calls deserializer.deserialize(value, typeToken.getType(), context), whose result is returned as T (unchecked by design).

calls: [jsondeserializer-java](r2-public-api.md#u-3d52eb1aa6c0)

<a id="u-34a4da1a6f8f"></a>
### `TreeTypeAdapter.write`

`@Override public void write(JsonWriter out, T value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java:L98-L110][f1]

With no serializer, writing is fully delegated to delegate().write.

When nullSafe and value is null it writes a JSON null directly. Otherwise serializer.serialize(value, typeToken.getType(), context) produces a JsonElement written via Streams.write; a serializer may return null, and Streams.write then determines what is emitted for a null tree.

calls: [JsonSerializer.serialize](r1-tree-adapter-bridge.md#u-949e1c27fb73)

**Uncertainties.**

- Behavior when serializer.serialize returns null depends on Streams.write, which is outside this file.

<a id="u-67171074cbff"></a>
### `treetypeadapter-java-residual`

`module_region`

License header, package, and imports for TreeTypeAdapter; non-behavioral material.

<a id="u-949e1c27fb73"></a>
### `JsonSerializer.serialize`

`JsonElement serialize(T src, Type typeOfSrc, JsonSerializationContext context);` · [gson/src/main/java/com/google/gson/JsonSerializer.java:L91-L91][f2]

Callback invoked by Gson during serialization for fields of type T, returning a JsonElement representing src.

Implementations should build non-trivial field values via JsonSerializationContext.serialize(Object, Type) but must not call it on src itself, which loops back into this callback. The graph shows TreeTypeAdapter.write invoking this method, bridging the tree API to Gson's streaming adapters. Serializers should be stateless and thread-safe; the class javadoc recommends TypeAdapter for new code because streaming is more efficient.

contract: [JsonSerializationContext.serialize](r1-tree-adapter-bridge.md#u-b2074f6d8748); uses: [TreeTypeAdapter.write](r1-tree-adapter-bridge.md#u-34a4da1a6f8f)

**Uncertainties.**

- Exact behavior of the TreeTypeAdapter bridge is outside this file.

<a id="u-b2074f6d8748"></a>
### `JsonSerializationContext.serialize`

`JsonElement serialize(Object src);` · [gson/src/main/java/com/google/gson/JsonSerializationContext.java:L36-L36][f3]

Requests Gson's default serialization of an object, producing a JsonElement tree.

This one-argument overload serializes src using its runtime type; the two-argument sibling (serialize(Object, Type)) does the same but with explicitly supplied, possibly genericized type information. Both are contract-only here: like the deserialization context, calling it on the src object passed to a custom serializer recurses infinitely because Gson re-invokes that serializer. Returned trees are built by the unseen implementation.

**Uncertainties.**

- Implementation-specific behavior (null handling, recursion detection) is not in this interface source.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TreeTypeAdapter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonSerializer.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonSerializationContext.java