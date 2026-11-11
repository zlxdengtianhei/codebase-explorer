# In-memory tree writer

**Capability.** Implements JsonWriter over an in-memory JsonElement tree, building containers and primitives instead of writing characters.

Use this module when serialization output should be a JsonElement rather than text. It mirrors JsonWriter's structural rules — pending names, null handling, close validation — while accumulating the tree on a stack.

**Depends on.**

- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) · graph-only · 4 edge(s)

**Depended on by.**

- [Core Adapter Abstractions and Time](core-adapter-abstractions-and-time.md) · graph-only · 1 edge(s)

Parent: [JSON Writing Infrastructure](json-writing-infrastructure.md)

## Units (10)

<a id="u-a8d385011f00"></a>
### `JsonTreeWriter.java-container-begin-end`

`@CanIgnoreReturnValue @Override public JsonWriter beginArray() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L99-L106][f1]

beginArray/beginObject create the container, put it, and push it on the stack.

endArray/endObject throw IllegalStateException if the stack is empty or a name is pending, or if the top of stack is not the matching container type; on success they pop it.

<a id="u-d0502f1abbec"></a>
### `JsonTreeWriter.java-value-overloads`

`@CanIgnoreReturnValue @Override public JsonWriter value(String value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L160-L168][f1]

String, Boolean, and Number nulls delegate to nullValue; non-null values are wrapped in JsonPrimitive and put.

float, double, and Number overloads throw IllegalArgumentException for NaN/infinite values when the writer is not lenient (checked via doubleValue for Number); long and boolean primitives are put unconditionally.

calls: [JsonWriter.isLenient](../../catalog.json)

<a id="u-db2378e1844e"></a>
### `JsonTreeWriter`

`class JsonTreeWriter extends JsonWriter` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L33-L36][f1]

JsonWriter implementation that builds an in-memory JsonElement tree instead of writing characters, backed by an unwritable Writer stub, a List stack of open JsonElements, a pendingName for the next object member, and a product initialized to JsonNull.

<a id="u-2305471cba94"></a>
### `gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:JsonTreeWriter.close`

`@Override public void close() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L247-L253][f1]

close throws IOException('Incomplete document') if any container is still open; otherwise it pushes a SENTINEL_CLOSED primitive so subsequent operations fail via put's IllegalStateException path.

<a id="u-5937818ae844"></a>
### `gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:JsonTreeWriter.flush`

`@Override public void flush() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L244-L245][f1]

flush is a no-op since output is in memory.

<a id="u-58a4de8f7ae3"></a>
### `JsonTreeWriter.get`

`public JsonElement get()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L69-L74][f1]

get returns the completed top-level element but throws IllegalStateException if any container is still open (stack non-empty).

<a id="u-a0e6bd873b1f"></a>
### `JsonTreeWriter.jsonValue`

`@Override public JsonWriter jsonValue(String value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L239-L242][f1]

jsonValue always throws UnsupportedOperationException because raw JSON text cannot be represented in a tree.

<a id="u-d25e72cadb38"></a>
### `JsonTreeWriter.name`

`@CanIgnoreReturnValue @Override public JsonWriter name(String name) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L145-L158][f1]

name requires a non-null name (NPE otherwise) and an open JsonObject with no pending name; IllegalStateException is thrown if the stack is empty, a name is pending, or the top is not a JsonObject.

On success it stores the name as pendingName.

<a id="u-4b472781fd97"></a>
### `JsonTreeWriter.nullValue`

`@CanIgnoreReturnValue @Override public JsonWriter nullValue() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L232-L237][f1]

nullValue puts JsonNull.INSTANCE, which may be dropped by put when a member name is pending and serializeNulls is off.

<a id="u-0521bbc8fa1f"></a>
### `JsonTreeWriter.put`

`private void put(JsonElement value)` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L80-L97][f1]

put inserts a value: with a pendingName it adds the member to the enclosing JsonObject unless the value is JSON null and serializeNulls is off, then clears pendingName; with an empty stack it becomes the product; otherwise it is appended to the enclosing JsonArray, or IllegalStateException if the top is neither (i.e., a scalar was already written).

calls: [JsonWriter.getSerializeNulls](../../catalog.json), [JsonObject.add](../../catalog.json), [JsonArray.add](../../catalog.json)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java
