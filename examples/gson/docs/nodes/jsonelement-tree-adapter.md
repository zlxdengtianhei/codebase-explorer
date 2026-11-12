# JsonElement tree adapter

**Capability.** Reads and writes JsonElement trees through a singleton TypeAdapter, including nested arrays and objects.

Use when converting between JSON streams and JsonElement trees. Units show singleton adapter, tree-reader fast path, scalar reads, and nested container starts.

**Depends on.**

- [Ordered JSON array](ordered-json-array.md) · graph-confirmed · 1 edge(s)
- [JsonElement tree reader](jsonelement-tree-reader.md) · graph-only · 1 edge(s)
- [Ordered JSON object map](ordered-json-object-map.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Stream serialization helpers](stream-serialization-helpers.md) · graph-confirmed · 1 edge(s)

Parent: [JSON element tree components](json-element-tree-components.md)

## Units (4)

<a id="u-6c234d95377f"></a>
### `JsonElementTypeAdapter.java-jsonelementtypeadapter-class`

`class JsonElementTypeAdapter extends TypeAdapter<JsonElement>` · [gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java:L35-L36][f1]

JsonElementTypeAdapter is a TypeAdapter for JsonElement trees, exposed as a singleton and constructed privately.

It reads and writes arrays, objects, primitives, and nulls; the read and write methods are separate.

<a id="u-c4c57a1e0198"></a>
### `JsonElementTypeAdapter.read`

`@Override public JsonElement read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java:L76-L136][f1]

Reads a JsonElement tree from a JsonReader, using JsonTreeReader.nextJsonElement directly when the reader is a JsonTreeReader.

Otherwise it peeks, starts a nested array or object when possible, and otherwise reads a terminal value. For nesting it iterates with a stack, reading object member names when current is a JsonObject, adding each value to the current array or object, and descending into nested values; when the current container ends it pops the enclosing container until the root is returned. Reader calls may throw IOException, and readTerminal throws IllegalStateException for an unexpected token; the source does not establish an exclusive failure surface for malformed structure.

**Uncertainties.**

- The source does not establish that malformed structure surfaces only as reader IOExceptions or readTerminal IllegalStateException.

<a id="u-313b5df333fa"></a>
### `JsonElementTypeAdapter.readTerminal`

`private JsonElement readTerminal(JsonReader in, JsonToken peeked) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java:L58-L74][f1]

Reads a non-nested JSON value into a JsonElement.

- STRING: returns a JsonPrimitive from nextString.
- NUMBER: returns a JsonPrimitive wrapping a LazilyParsedNumber from nextString.
- BOOLEAN: returns a JsonPrimitive from nextBoolean.
- NULL: consumes nextNull and returns JsonNull.INSTANCE.
- other: throws IllegalStateException with the unexpected token.

<a id="u-7bc09c8eaaa4"></a>
### `JsonElementTypeAdapter.tryBeginNesting`

`private JsonElement tryBeginNesting(JsonReader in, JsonToken peeked) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java:L44-L55][f1]

Starts a nested JSON array or object when the peeked token is BEGIN_ARRAY or BEGIN_OBJECT, returning a new JsonArray or JsonObject respectively.

For any other token it returns null without consuming input.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java
