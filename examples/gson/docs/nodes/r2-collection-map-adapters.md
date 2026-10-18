# Collection, Map, and Tree Adapters

**Capability.** Adapts homogeneous Collections, Maps (with key-element-to-string conversion and internal reader access), and JsonElement itself between streams and objects, obtaining map/collection instances via ConstructorConstructor.

Use these factories to understand how arrays become Collections, JSON objects become Maps, and raw JSON becomes a JsonElement tree. keyToString and JsonReaderInternalAccess show the special handling needed for non-string map keys during deserialization.

**Depends on.**

- [JSON DOM Tree](r2-dom-tree.md) · graph-only · 21 edge(s)
- [Runtime Generic Type Model](r1-type-model.md) · graph-only · 9 edge(s)
- [Gson Facade and Conversion API](r1-facade-api.md) · graph-only · 3 edge(s)
- [Internal Utilities and Data Structures](r2-infrastructure.md) · graph-only · 2 edge(s)
- [Object Construction Strategy](r2-object-construction.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Internal Utilities and Data Structures](r2-infrastructure.md) · graph-only · 2 edge(s)

Parent: [Built-in Type Adapter Factories](r2-default-adapters.md)

## Units (15)

<a id="u-cc66736ed77d"></a>
### `collectiontypeadapterfactory.java-class`

`class CollectionTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/CollectionTypeAdapterFactory.java:L34-L37][f1]

CollectionTypeAdapterFactory is a final TypeAdapterFactory that adapts homogeneous collections.

It holds a ConstructorConstructor used to build collection instances without Unsafe, and its create() matches any raw type assignable to Collection. The nested Adapter extends TypeAdapter<Collection<E>>, pairing the wrapped element adapter with the instance constructor; its constructor merely stores both fields.

group: [CollectionTypeAdapterFactory.create](r2-collection-map-adapters.md#u-42f8907567ac)

<a id="u-42f8907567ac"></a>
### `CollectionTypeAdapterFactory.create`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> typeToken)` · [gson/src/main/java/com/google/gson/internal/bind/CollectionTypeAdapterFactory.java:L41-L62][f1]

Creates an adapter when the requested raw type is assignable to Collection, otherwise returns null.

It extracts the element type with GsonTypes.getCollectionElementType, resolves the element adapter via gson.getAdapter, and wraps it in a TypeAdapterRuntimeTypeWrapper for runtime-type dispatch. It obtains the collection instance factory via constructorConstructor.get(typeToken, false) with allowUnsafe deliberately false, so Unsafe is never used to instantiate a Collection that might be in a broken state. The resulting Adapter is returned via an unchecked cast.

calls: [Gson.getAdapter](r1-facade-api.md#u-276006924613), [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:ConstructorConstructor.get](r2-object-construction.md#u-2b1d12b84c2c)

**Uncertainties.**

- Concrete collection classes produced depend on ConstructorConstructor, not visible here.

<a id="u-8a9a3c647475"></a>
### `CollectionTypeAdapterFactory.Adapter.read`

`@Override public Collection<E> read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/CollectionTypeAdapterFactory.java:L74-L89][f1]

Reads a JSON array into a Collection.

A peeked NULL is consumed with nextNull() and null is returned. Otherwise constructor.construct() builds the target collection, and elements read one by one with elementTypeAdapter.read(in) between beginArray()/endArray() are added via collection.add; the populated collection is returned. An empty array produces an empty collection. IOExceptions from the reader or element adapter propagate uncaught.

uses: [CollectionTypeAdapterFactory.create](r2-collection-map-adapters.md#u-42f8907567ac)

<a id="u-2403ce181efc"></a>
### `CollectionTypeAdapterFactory.Adapter.write`

`@Override public void write(JsonWriter out, Collection<E> collection) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/CollectionTypeAdapterFactory.java:L91-L103][f1]

Writes a Collection as a JSON array.

A null collection is written as a JSON null and the method returns. Otherwise it opens an array, writes each element in the collection's own iteration order by delegating to elementTypeAdapter.write(out, element), and closes the array.

uses: [CollectionTypeAdapterFactory.create](r2-collection-map-adapters.md#u-42f8907567ac)

<a id="u-941df8b23c21"></a>
### `MapTypeAdapterFactory`

`class MapTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L115-L119][f2]

A TypeAdapterFactory that creates adapters converting Java Maps to JSON objects or arrays.

The constructor stores a ConstructorConstructor for instance creation and a complexMapKeySerialization flag that changes the JSON shape. getKeyAdapter returns TypeAdapters.BOOLEAN_AS_STRING when the key type is boolean or Boolean (booleans cannot be JSON object names directly), otherwise resolves an adapter via Gson.getAdapter for the key type.

calls: [Gson.getAdapter](r1-facade-api.md#u-276006924613)

<a id="u-5f58689d768c"></a>
### `gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:Adapter`

`class Adapter<K, V> extends TypeAdapter<Map<K, V>>` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L161-L166][f2]

The inner TypeAdapter for a concrete Map<K,V>, holding wrapped key and value adapters plus an ObjectConstructor that instantiates the map.

Its constructor simply stores the three collaborators; reading and writing behavior is defined by read and write.

<a id="u-0aba687b7b01"></a>
### `MapTypeAdapterFactory.create`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> typeToken)` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L125-L152][f2]

Creates a map adapter when the requested type is assignable to Map, returning null otherwise so other factories handle the type.

It splits the type into key and value types via GsonTypes.getMapKeyAndValueTypes, wraps both key and value adapters in TypeAdapterRuntimeTypeWrapper so serialization picks the runtime-type adapter, and obtains an ObjectConstructor with allowUnsafe=false, deliberately refusing Unsafe allocation so no broken Map instance is produced. The result is an unchecked cast of a new Adapter.

calls: [GsonTypes.getMapKeyAndValueTypes](r1-type-model.md#u-936f504373bc), [Gson.getAdapter](r1-facade-api.md#u-276006924613), [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:ConstructorConstructor.get](r2-object-construction.md#u-2b1d12b84c2c)

**Uncertainties.**

- Behavior of TypeAdapterRuntimeTypeWrapper and GsonTypes.getMapKeyAndValueTypes for exotic Map subtypes is outside the supplied source.

<a id="u-032b938cc3cb"></a>
### `MapTypeAdapterFactory.Adapter.read`

`@Override public Map<K, V> read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L175-L214][f2]

Deserializes a map, returning null for a JSON null.

If the next token is BEGIN_ARRAY it reads entries as two-element arrays (key then value), otherwise it reads a JSON object, using JsonReaderInternalAccess.INSTANCE.promoteNameToValue so a name can be consumed as a value by the key adapter. In both shapes a duplicate key throws JsonSyntaxException naming the key and the reader's previous path; endArray/endObject closes the container before returning the constructed map.

**Notes.**

- failure: Duplicate keys in either the array-entry or object form abort reading with JsonSyntaxException; nothing is removed from the partially filled map, but that map is discarded.

calls: [JsonReaderInternalAccess](r2-infrastructure.md#u-a3774963f70f)

**Uncertainties.**

- Exact behavior when the key adapter cannot consume a promoted name depends on that adapter and JsonReader, not shown here.

<a id="u-6c0a8de982d0"></a>
### `MapTypeAdapterFactory.Adapter.write`

`@Override public void write(JsonWriter out, Map<K, V> map) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L216-L262][f2]

Serializes a map, writing a JSON null for a null map.

With complexMapKeySerialization disabled it writes a JSON object using String.valueOf(entry.getKey()) as every name and the value adapter for values. When enabled, it first converts each key to a JsonElement via keyTypeAdapter.toJsonTree; if any key element is a JSON array or object, entries are written as two-element arrays [key, value], otherwise names come from keyToString(keyElement) in a JSON object. Streams.write emits complex key elements directly.

**Notes.**

- condition: The JSON shape therefore changes at runtime per map: object form for primitive keys, array-of-entries form only when at least one key serializes to an array or object and complex key serialization is on.

calls: [Streams](r2-infrastructure.md#u-931987e48ef4)

<a id="u-3e92ab1bd324"></a>
### `MapTypeAdapterFactory.Adapter.keyToString`

`private String keyToString(JsonElement keyElement)` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L264-L281][f2]

Converts a serialized key JsonElement back to a string usable as a JSON object name.

Number primitives become String.valueOf of the number, booleans Boolean.toString, strings their own text, and JSON null the literal "null". A primitive of any other kind, or a non-primitive non-null element, triggers AssertionError, though such elements should have routed the map to the array form in write.

calls: [jsonelement-class](r2-dom-tree.md#u-103ba2beeebe)

**Uncertainties.**

- Which getAsNumber/getAsBoolean/getAsString implementation runs is ambiguous between JsonElement and JsonPrimitive in the graph evidence; only the returned string matters here.

<a id="u-1bb0c8278cfd"></a>
### `jsonelementtypeadapter.java-class`

`class JsonElementTypeAdapter extends TypeAdapter<JsonElement>` · [gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java:L35-L38][f3]

JsonElementTypeAdapter adapts JsonElement and its subclasses between JSON streams and the in-memory tree.

It exposes a shared ADAPTER constant and a private constructor, so the single instance is the only adapter. Read reconstructs the tree iteratively (with a fast path for JsonTreeReader); write serializes the tree by kind. The class-level fields are just the ADAPTER constant.

group: [JsonElementTypeAdapter.read](r2-collection-map-adapters.md#u-c4c57a1e0198)

<a id="u-c4c57a1e0198"></a>
### `JsonElementTypeAdapter.read`

`@Override public JsonElement read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java:L76-L136][f3]

Reads an arbitrary JSON value into a JsonElement tree.

If the reader is a JsonTreeReader it short-circuits and returns the existing element via nextJsonElement() without reparsing. Otherwise it peeks; a non-container token is read as a terminal value. For a container it enters an iterative loop using a Deque stack: for each has-next member it reads the member name when current is a JsonObject, peeks the value, tries nesting (recursing into the loop by pushing current and descending) or reads a terminal, attaches the value via JsonArray.add or JsonObject.add(name, value), and when the current container is exhausted calls endArray()/endObject() and pops the parent from the stack, returning the root when the stack empties.

calls: [JsonTreeReader.nextJsonElement](r1-streaming-json.md#u-37a8966bfb18), [jsonarray-class](r2-dom-tree.md#u-d79acd357359), [jsonobject-class](r2-dom-tree.md#u-5c0ff73487b7), [JsonElementTypeAdapter.tryBeginNesting](r2-collection-map-adapters.md#u-7bc09c8eaaa4), [JsonElementTypeAdapter.readTerminal](r2-collection-map-adapters.md#u-313b5df333fa)

**Uncertainties.**

- nextJsonElement()'s contract for already-consumed readers is defined in JsonTreeReader, not here.

<a id="u-313b5df333fa"></a>
### `JsonElementTypeAdapter.readTerminal`

`private JsonElement readTerminal(JsonReader in, JsonToken peeked) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java:L58-L74][f3]

Reads a non-nested JSON value into a JsonElement based on the peeked token: STRING yields JsonPrimitive(nextString()); NUMBER yields a JsonPrimitive wrapping a LazilyParsedNumber over the raw string; BOOLEAN yields JsonPrimitive(nextBoolean()); NULL consumes the null and returns JsonNull.INSTANCE.

Any other token — a JsonReader in an invalid state — throws IllegalStateException("Unexpected token: " + peeked).

**Notes.**

- failure: IllegalStateException is thrown for unexpected tokens rather than an IOException or JsonSyntaxException.

<a id="u-7bc09c8eaaa4"></a>
### `JsonElementTypeAdapter.tryBeginNesting`

`private JsonElement tryBeginNesting(JsonReader in, JsonToken peeked) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java:L44-L55][f3]

Begins reading a nested container if the peeked token is one: for BEGIN_ARRAY it calls in.beginArray() and returns a new empty JsonArray; for BEGIN_OBJECT it calls in.beginObject() and returns a new empty JsonObject; for any other token it returns null without consuming anything, signaling the caller to read a terminal value instead.

uses: [JsonReader.beginArray](r1-streaming-json.md#u-599a8f46d311)

**Uncertainties.**

- Which JsonReader implementation performs beginArray/beginObject depends on the runtime reader.

<a id="u-abc7bd1c85bd"></a>
### `JsonElementTypeAdapter.write`

`@Override public void write(JsonWriter out, JsonElement value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java:L138-L170][f3]

Writes a JsonElement tree to the writer, dispatching on the element's kind.

A null reference or JsonNull writes a JSON null. A JsonPrimitive writes as number (getAsNumber), boolean (getAsBoolean), or falls back to string (getAsString). A JsonArray opens an array and recursively writes each element; a JsonObject opens an object, writing each entry's key with out.name before recursively writing its value. Any other JsonElement subclass, or an unhandled kind, throws IllegalArgumentException("Couldn't write " + value.getClass()).

**Notes.**

- failure: Unknown JsonElement subclasses cause IllegalArgumentException rather than silent output.

uses: [jsonarray-class](r2-dom-tree.md#u-d79acd357359), [jsonobject-class](r2-dom-tree.md#u-5c0ff73487b7)

**Uncertainties.**

- getAsString on a non-string primitive may throw inside JsonPrimitive; that behavior is not visible here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/CollectionTypeAdapterFactory.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java