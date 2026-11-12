# Map type adapter factory

**Capability.** Creates and operates TypeAdapters for Java Map types, including key adaptation and complex-key handling.

Use for map serialization/deserialization adapter behavior. Units show map adapter, factory selection, key conversion, and read/write paths.

**Depends on.**

- [JsonElement tree base](jsonelement-tree-base.md) · graph-confirmed · 5 edge(s)
- [Stream serialization helpers](stream-serialization-helpers.md) · graph-confirmed · 2 edge(s)
- [Generic type reflection](generic-type-reflection.md) · graph-only · 3 edge(s)
- [JSON primitive values](json-primitive-values.md) · graph-only · 3 edge(s)
- [Gson serialization facade](gson-serialization-facade.md) · graph-only · 2 edge(s)

Parent: [JSON element tree components](json-element-tree-components.md)

## Units (7)

<a id="u-356848b36c95"></a>
### `MapTypeAdapterFactory.java-map-adapter-construction`

`class Adapter<K, V> extends TypeAdapter<Map<K, V>>` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L161-L162][f1]

Inner map adapter that stores key/value adapters and a map constructor.

The constructor only assigns those collaborators; read and write implement the object/array map formats.

<a id="u-c13b4ff666ae"></a>
### `MapTypeAdapterFactory.java-map-factory-construction`

`class MapTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L115-L116][f1]

Factory for Java Map types that stores the constructor lookup and the complex-key-serialization flag.

The constructor only assigns those two fields; adapter creation and map I/O are handled by its other members.

<a id="u-3e92ab1bd324"></a>
### `MapTypeAdapterFactory.Adapter.keyToString`

`private String keyToString(JsonElement keyElement)` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L264-L281][f1]

Converts a non-complex key JSON element to an object name: numbers use String.valueOf(getAsNumber), booleans use Boolean.toString(getAsBoolean), strings use getAsString, and JSON null becomes "null".

Other element kinds throw AssertionError.

<a id="u-032b938cc3cb"></a>
### `MapTypeAdapterFactory.Adapter.read`

`@Override public Map<K, V> read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L175-L214][f1]

Reads a map from JSON.

Null returns null; otherwise constructs a map. If the next token begins an array, it reads entry arrays, reading key then checking duplicate before value; duplicate keys throw JsonSyntaxException. Otherwise it begins an object, promotes each name to a value, reads key then checks duplicate before value. Duplicate keys throw JsonSyntaxException in both forms.

<a id="u-6c0a8de982d0"></a>
### `MapTypeAdapterFactory.Adapter.write`

`@Override public void write(JsonWriter out, Map<K, V> map) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L216-L262][f1]

Writes a map.

Null writes JSON null. Without complex key serialization it writes an object using String.valueOf(key) and the value adapter. With complex key serialization it first builds key JSON trees and values; if any key tree is an array or object it writes an array of [key,value] entry arrays using Streams.write for keys, otherwise it writes an object using keyToString for names.

<a id="u-0aba687b7b01"></a>
### `MapTypeAdapterFactory.create`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> typeToken)` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L125-L152][f1]

Creates a map adapter only when the requested raw type is assignable to Map; otherwise returns null.

It resolves key and value types, obtains a key adapter (boolean keys use the boolean-as-string adapter), wraps both adapters for runtime type selection, forbids unsafe map construction, and returns an Adapter.

<a id="u-a077734da08f"></a>
### `MapTypeAdapterFactory.getKeyAdapter`

`private TypeAdapter<?> getKeyAdapter(Gson context, Type keyType)` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L155-L159][f1]

Chooses the key adapter for map serialization: boolean and Boolean keys use the boolean-as-string adapter, while all other key types use the Gson context adapter for that key type.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java
