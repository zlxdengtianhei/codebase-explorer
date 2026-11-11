# Map Serialization

**Capability.** Produces adapters that read and write Map types as JSON objects or key-value pair arrays.

Come here for how maps become JSON, including complex-key serialization and boolean keys rendered as strings. The factory creates map adapters from a type token using a ConstructorConstructor.

**Depends on.**

- [Internal Reflection Utilities](internal-reflection-utilities.md) · graph-confirmed · 1 edge(s)
- [JSON Primitive Values](json-primitive-values.md) · graph-confirmed · 3 edge(s)
- [Tree Element Bridge](tree-element-bridge.md) · graph-only · 6 edge(s)
- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) · graph-only · 4 edge(s)
- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-only · 2 edge(s)

Parent: [Primitives and Map Adapters](primitives-and-map-adapters.md)

## Units (4)

<a id="u-5495487401be"></a>
### `MapTypeAdapterFactory.java-map-adapter`

`class Adapter<K, V> extends TypeAdapter<Map<K, V>>` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L161-L162][f1]

Inner TypeAdapter that reads and writes Map<K,V> as either JSON objects or arrays of [key, value] pairs.

read: null token yields null; a BEGIN_ARRAY is parsed as entry arrays, otherwise a JSON object is parsed with promoteNameToValue feeding the name to the key adapter; in both shapes a duplicate key throws JsonSyntaxException with the key and previous path. write: null map writes null; without complexMapKeySerialization it writes a JSON object using String.valueOf(key); with the flag it converts each key to a JsonElement and, if any key is an array or object, writes the array-of-pairs form, otherwise an object whose names come from keyToString. keyToString maps primitive numbers/booleans/strings via their string forms, JsonNull to "null", and throws AssertionError for any other element kind.

<a id="u-941df8b23c21"></a>
### `MapTypeAdapterFactory`

`class MapTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L115-L116][f1]

Factory that produces type adapters for Map types, configured with a ConstructorConstructor and a flag for complex map key serialization.

It only claims Map-assignable types; the flag is consulted later during writing.

<a id="u-0aba687b7b01"></a>
### `MapTypeAdapterFactory.create`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> typeToken)` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L125-L152][f1]

Creates a map adapter for the requested type token, or returns null for non-Map types.

Resolves key and value types via GsonTypes, wraps both adapters in TypeAdapterRuntimeTypeWrapper for runtime-type dispatch, and builds the map instance through the ConstructorConstructor with unsafe instantiation explicitly disallowed. Boolean keys get the special string-writing adapter.

<a id="u-a077734da08f"></a>
### `MapTypeAdapterFactory.getKeyAdapter`

`private TypeAdapter<?> getKeyAdapter(Gson context, Type keyType)` · [gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java:L155-L159][f1]

Returns BOOLEAN_AS_STRING for boolean/Boolean key types so map keys serialize as strings; otherwise delegates to Gson.getAdapter for the key type.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/MapTypeAdapterFactory.java
