# Tree-Bound Writer

**Capability.** Reimplements the JsonWriter API so that every write call assembles a JsonElement tree instead of emitting characters; structure stack, name deferral, leniency checks, and completion validation mirror the streaming contract.

Use JsonTreeWriter when an adapter must produce a parse tree rather than text. Its put/peek/name/value methods enforce the same structural rules as the streaming writer (closing completeness, pending names, NaN/Infinity restrictions under non-lenient strictness) and get() returns the finished tree.

**Depends on.**

- [JSON DOM Tree](r2-dom-tree.md) · containment · → 3 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r2-tree-writer ` → ` r2-dom-tree `) · JsonTreeWriter assembles JsonElement, JsonArray, and JsonObject nodes instead of emitting characters.
- [Streaming JSON Writer and Lexical Model](r2-streaming.md) · graph-confirmed · 5 edge(s) · JsonTreeWriter mirrors the streaming JsonWriter structural contract while building a tree.

**Depended on by.**

- [TypeAdapter Framework](r1-adapter-framework.md) · graph-only · 1 edge(s)
- [Gson Facade and Conversion API](r1-facade-api.md) · graph-only · 1 edge(s)

Parent: [JSON DOM Tree](r2-dom-tree.md)

## Units (22)

<a id="u-7c8be5507949"></a>
### `jsontreewriter-java-residual`

`module_region`

License header, package, and imports for JsonTreeWriter; non-behavioral material.

<a id="u-4ff89f614554"></a>
### `jsontreereader-java-residual`

`module_region`

License header, package, and imports for JsonTreeReader; non-behavioral material.

<a id="u-ee9339bf1bcc"></a>
### `gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:JsonTreeWriter (2)`

`class JsonTreeWriter extends JsonWriter` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L49-L64][f1]

A JsonWriter that builds a JsonElement instead of writing characters; it passes UNWRITABLE_WRITER to the super constructor, whose write/flush/close all throw AssertionError so character-level output is impossible.

State is a stack of in-progress JsonElements (outermost to innermost), a pendingName marking that the next value belongs to an object member, and product holding the finished top-level element (initially JsonNull.INSTANCE). The first write::1227 and flush::1362 and close::1459 overrides throw UnsupportedOperationException, reserving those operations.

calls: [JsonWriter](r2-streaming.md#u-d122b2c80531)

<a id="u-ad4b49b275af"></a>
### `JsonTreeWriter.beginArray`

`@CanIgnoreReturnValue @Override public JsonWriter beginArray() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L99-L106][f1]

Creates a JsonArray, places it via put (which appends it to an enclosing array or product), and pushes it so subsequent values nest inside it.

<a id="u-04cb11d6b990"></a>
### `JsonTreeWriter.beginObject`

`@CanIgnoreReturnValue @Override public JsonWriter beginObject() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L122-L129][f1]

Creates a JsonObject, places it via put, and pushes it so subsequent name/value pairs attach to it.

<a id="u-2305471cba94"></a>
### `gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:JsonTreeWriter.close`

`@Override public void close() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L247-L253][f1]

Throws IOException('Incomplete document') when the stack is non-empty; otherwise pushes SENTINEL_CLOSED so later operations encounter an unexpected stack top.

Unlike the UNWRITABLE_WRITER close, this does not throw AssertionError.

**Uncertainties.**

- After close, only the sentinel sits on the stack; the exact failure mode of subsequent write calls (IllegalStateException from put/endArray) is not re-verified here.

<a id="u-02198310bf04"></a>
### `JsonTreeWriter.endArray`

`@CanIgnoreReturnValue @Override public JsonWriter endArray() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L108-L120][f1]

Raises IllegalStateException when the stack is empty or a name is pending; if the top is a JsonArray pops it and returns, otherwise raises IllegalStateException for the mismatched structure.

<a id="u-5628e9cc718c"></a>
### `JsonTreeWriter.endObject`

`@CanIgnoreReturnValue @Override public JsonWriter endObject() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L131-L143][f1]

Raises IllegalStateException when the stack is empty or a name is pending; pops and returns when the top is a JsonObject, otherwise raises IllegalStateException.

<a id="u-5937818ae844"></a>
### `gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:JsonTreeWriter.flush`

`@Override public void flush() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L244-L245][f1]

No-op; there is no output stream to flush.

<a id="u-58a4de8f7ae3"></a>
### `JsonTreeWriter.get`

`public JsonElement get()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L69-L74][f1]

Returns product, but raises IllegalStateException quoting the open stack when elements are still being built.

<a id="u-a0e6bd873b1f"></a>
### `JsonTreeWriter.jsonValue`

`@Override public JsonWriter jsonValue(String value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L239-L242][f1]

Raw JSON value emission is unsupported for tree writing and always throws UnsupportedOperationException.

<a id="u-d25e72cadb38"></a>
### `JsonTreeWriter.name`

`@CanIgnoreReturnValue @Override public JsonWriter name(String name) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L145-L158][f1]

Requires a non-null name (NullPointerException on null), raises IllegalStateException('Did not expect a name') when the stack is empty or a name is already pending, and raises IllegalStateException('Please begin an object before writing a name.') when the top is not a JsonObject; otherwise stores the name for the next put.

<a id="u-4b472781fd97"></a>
### `JsonTreeWriter.nullValue`

`@CanIgnoreReturnValue @Override public JsonWriter nullValue() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L232-L237][f1]

Puts JsonNull.INSTANCE; per put's rules a null object member is stored only when serializeNulls is enabled, while nulls elsewhere are recorded.

<a id="u-6d21b6a049db"></a>
### `JsonTreeWriter.peek`

`private JsonElement peek()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L76-L78][f1]

Returns the innermost stack element without removing it.

<a id="u-0521bbc8fa1f"></a>
### `JsonTreeWriter.put`

`private void put(JsonElement value)` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L80-L97][f1]

Core placement of a built value.

With a pendingName: the value is added to the JsonObject under that name only when it is not JSON null or the writer's serializeNulls setting is true; pendingName resets to null either way. Without a pending name: an empty stack assigns product; a JsonArray top appends the value; any other top raises an unspecific IllegalStateException.

calls: [jsonobject-class](r2-dom-tree.md#u-5c0ff73487b7), [jsonwriter-config-accessors](r2-streaming.md#u-cccb91734698)

<a id="u-f66c4f4e7ec6"></a>
### `JsonTreeWriter.value`

`@CanIgnoreReturnValue @Override public JsonWriter value(String value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L160-L168][f1]

String value: null delegates to nullValue(); otherwise puts a JsonPrimitive of the string.

<a id="u-c5ac615c9dfa"></a>
### `gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:JsonTreeWriter.value`

`@CanIgnoreReturnValue @Override public JsonWriter value(boolean value) throws IOExcep…` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L170-L175][f1]

Primitive boolean value: puts a JsonPrimitive and returns the writer.

<a id="u-ce23827013ad"></a>
### `gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:JsonTreeWriter.value (2)`

`@CanIgnoreReturnValue @Override public JsonWriter value(Boolean value) throws IOExcep…` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L177-L185][f1]

Boxed Boolean value: null delegates to nullValue(); otherwise puts a JsonPrimitive.

<a id="u-0c4843dc7457"></a>
### `gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:JsonTreeWriter.value (3)`

`@CanIgnoreReturnValue @Override public JsonWriter value(float value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L187-L195][f1]

Float value: when not lenient, NaN or infinity raises IllegalArgumentException('JSON forbids NaN and infinities'); otherwise puts a JsonPrimitive.

calls: [jsonwriter-config-accessors](r2-streaming.md#u-cccb91734698)

<a id="u-d24baf879809"></a>
### `gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:JsonTreeWriter.value (4)`

`@CanIgnoreReturnValue @Override public JsonWriter value(double value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L197-L205][f1]

Double value: same leniency rule as the float overload, raising IllegalArgumentException for NaN/infinite values when not lenient, otherwise putting a JsonPrimitive.

calls: [jsonwriter-config-accessors](r2-streaming.md#u-cccb91734698)

<a id="u-58944ad00734"></a>
### `gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:JsonTreeWriter.value (5)`

`@CanIgnoreReturnValue @Override public JsonWriter value(long value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L207-L212][f1]

Long value: puts a JsonPrimitive; no range or leniency checks apply.

<a id="u-16be56cc217c"></a>
### `gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:JsonTreeWriter.value (6)`

`@CanIgnoreReturnValue @Override public JsonWriter value(Number value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L214-L230][f1]

Number value: null delegates to nullValue(); when not lenient, a doubleValue() that is NaN or infinite raises IllegalArgumentException; otherwise puts a JsonPrimitive wrapping the original Number.

calls: [jsonwriter-config-accessors](r2-streaming.md#u-cccb91734698)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java