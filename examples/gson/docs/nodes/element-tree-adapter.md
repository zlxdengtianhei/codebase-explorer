# Element Tree Adapter

**Capability.** Provides the singleton TypeAdapter that reads any JSON value into a JsonElement tree.

A focused module containing the public ADAPTER that materializes reader content as JsonArray, JsonObject, or JsonPrimitive. Readers tracing how trees are produced during deserialization should look here.

**Depends on.**

- [JSON Array Model](json-array-model.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Tree Element Bridge](tree-element-bridge.md) · graph-confirmed · 1 edge(s)

Parent: [Arrays and Stream Bridge](arrays-and-stream-bridge.md)

## Units (3)

<a id="u-13e77020c94c"></a>
### `JsonElementTypeAdapter.java-jsonelement-terminal-nesting-helpers`

`private JsonElement tryBeginNesting(JsonReader in, JsonToken peeked) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java:L44-L55][f1]

tryBeginNesting consumes a BEGIN_ARRAY or BEGIN_OBJECT token and returns a new empty JsonArray or JsonObject respectively, or null for any other token (leaving the reader untouched).

readTerminal converts a non-nesting token to a JsonElement: STRING→JsonPrimitive(string), NUMBER→JsonPrimitive wrapping a LazilyParsedNumber of the raw text (preserving the original lexical form), BOOLEAN→JsonPrimitive(boolean), NULL→JsonNull.INSTANCE with the token consumed; any other token throws IllegalStateException("Unexpected token: ..."), which occurs only when the reader is in an invalid state.

uses: [LazilyParsedNumber](../../catalog.json)

<a id="u-0c16ea9ccdd9"></a>
### `JsonElementTypeAdapter.java-jsonelementtypeadapter-class-and-instance`

`class JsonElementTypeAdapter extends TypeAdapter<JsonElement>` · [gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java:L35-L36][f1]

Singleton adapter for JsonElement and its subclasses, exposed as the public static ADAPTER; the constructor is private so the singleton is the only instance.

It carries no state — all behavior lives in read/write and their helpers.

<a id="u-c4c57a1e0198"></a>
### `JsonElementTypeAdapter.read`

`@Override public JsonElement read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java:L76-L136][f1]

Reads any JSON value into an equivalent JsonElement tree.

Fast path: if the reader is a JsonTreeReader, it returns nextJsonElement() directly, reusing an existing tree. Otherwise it starts with tryBeginNesting; a null result means the whole value is terminal and readTerminal supplies it. For arrays/objects it runs an explicit stack loop: while hasNext, an object reads a member name (arrays skip names), peeks, and gets the child via tryBeginNesting or readTerminal; the child is added to the current JsonArray or JsonObject, and if it nests, the current element is pushed and the child becomes current. When a level is exhausted it ends the array/object, then either returns the current (root) element or pops the enclosing element from the Deque. Malformed structure surfaces as reader IOExceptions; the IllegalStateException path comes only from readTerminal on an invalid reader state.

calls: [JsonTreeReader.nextJsonElement](../../catalog.json)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java
