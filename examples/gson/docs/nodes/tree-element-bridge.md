# Tree Element Bridge

**Capability.** Defines the abstract JsonElement base and the Streams/adapter bridge between streaming readers/writers and element trees.

This module connects the tree model to the streaming API: JsonElement's type checks and default-throwing conversions, the Appendable-backed writer, and recursive tree writing. It is the shared foundation other tree modules call into.

**Depends on.**

- [Element Tree Adapter](element-tree-adapter.md) · graph-confirmed · 1 edge(s)
- [JSON Array Model](json-array-model.md) · graph-confirmed · 1 edge(s)
- [JSON Primitive Values](json-primitive-values.md) · graph-only · 2 edge(s)

**Depended on by.**

- [JSON Array Model](json-array-model.md) · graph-confirmed · 1 edge(s)
- [Map Serialization](map-serialization.md) · graph-only · 6 edge(s)
- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) · graph-only · 3 edge(s)
- [JSON Parsing Facades](json-parsing-facades.md) · graph-only · 3 edge(s)
- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-only · 3 edge(s)
- [Core Adapter Abstractions and Time](core-adapter-abstractions-and-time.md) · graph-only · 1 edge(s)

Parent: [Arrays and Stream Bridge](arrays-and-stream-bridge.md)

## Units (12)

<a id="u-554ad7f479b9"></a>
### `JsonElement.java-jsonelement`

`class JsonElement` · [gson/src/main/java/com/google/gson/JsonElement.java:L96-L102][f1]

Abstract base class for JSON tree nodes (object, array, primitive, null) providing type checks, checked casts, and default-throwing value conversions.

Its public constructor is deprecated because custom subclasses are unsupported. deepCopy is abstract: subclasses must return a copy of the element and its children, with immutable leaves allowed to return themselves. All getAsNumber/getAsString/getAsDouble and similar value conversions throw UnsupportedOperationException naming the concrete class by default; JsonPrimitive and JsonArray override them, so calling one on a JsonObject or JsonNull always fails with that exception.

<a id="u-7761c03eab7c"></a>
### `JsonElement.java-jsonelement-checked-casts`

`public JsonObject getAsJsonObject()` · [gson/src/main/java/com/google/gson/JsonElement.java:L159-L164][f1]

Each returns this cast to the requested subtype when the matching isJsonX check passes; otherwise it throws IllegalStateException whose message embeds this element's toString representation (e.g. 'Not a JSON Object: ...').

getAsJsonNull is annotated @CanIgnoreReturnValue because it is often called purely to validate the type.

<a id="u-83317f060b2f"></a>
### `JsonElement.java-jsonelement-default-getas-conversions`

`class JsonElement` · [gson/src/main/java/com/google/gson/JsonElement.java:L212-L223][f1]

These regions document the base-class defaults for all value conversions (boolean, Number, String, double, float, long, int, byte, character, BigDecimal, BigInteger, short): each unconditionally throws UnsupportedOperationException naming the concrete subclass, establishing the contract that subclasses must override the conversions they support.

getAsCharacter is deprecated as misleading. The javadocs note that JsonArray implementations may instead throw IllegalStateException for multi-element arrays and NumberFormatException for unparseable values, but that behavior lives in the subclasses.

<a id="u-52c4623b5888"></a>
### `JsonElement.java-jsonelement-default-value-conversions`

`public boolean getAsBoolean()` · [gson/src/main/java/com/google/gson/JsonElement.java:L223-L225][f1]

Base implementations for boolean, Number, String, double, float, long, int, byte, char, BigDecimal, BigInteger, and short; every one unconditionally throws UnsupportedOperationException with the concrete subclass's simple name.

Subclasses (JsonPrimitive, JsonArray) override these to perform real conversion, so on this base class the calls are pure failure paths. getAsCharacter is deprecated for being misleading (it is specified as the string's first character, not a char value).

<a id="u-881adfafe2ed"></a>
### `JsonElement.java-jsonelement-type-checks`

`public boolean isJsonArray()` · [gson/src/main/java/com/google/gson/JsonElement.java:L118-L120][f1]

Instanceof-based predicates: isJsonArray, isJsonObject, isJsonPrimitive, and isJsonNull return true exactly when this element is of the corresponding subtype, false otherwise.

They never throw and are the recommended guard before the getAsJsonX casts.

<a id="u-5459f9a2654d"></a>
### `JsonElement.java-jsonelement-type-checks-2`

`class JsonElement` · [gson/src/main/java/com/google/gson/JsonElement.java:L103-L111][f1]

These regions document the four instanceof-based predicates isJsonArray, isJsonObject, isJsonPrimitive, and isJsonNull, each returning true only when this element is of the corresponding subclass.

<a id="u-9b8ca9eef133"></a>
### `JsonElement.java-jsonelement-typed-casts`

`class JsonElement` · [gson/src/main/java/com/google/gson/JsonElement.java:L138-L146][f1]

These regions document getAsJsonObject, getAsJsonArray, getAsJsonPrimitive, and getAsJsonNull: each checks the matching predicate and casts this, otherwise throws IllegalStateException whose message embeds this element's toString.

getAsJsonNull is annotated @CanIgnoreReturnValue because it is often called just to validate the type.

<a id="u-a13f714357ac"></a>
### `Streams.java-appendablewriter-and-currentwrite`

`class AppendableWriter extends Writer` · [gson/src/main/java/com/google/gson/internal/Streams.java:L78-L79][f2]

Writer adapter over an arbitrary Appendable.

The char[]-based write routes through a reusable CurrentWrite CharSequence so the Appendable sees a subSequence view without copying; flush and close delegate only when the Appendable implements Flushable/Closeable, otherwise they are no-ops. Overridden single-char, String, and CharSequence writes avoid intermediate allocations; the String overload requires a non-null string because Appendable.append would turn null into "null". CurrentWrite is a mutable CharSequence over one char[] with a cached String built lazily by toString and invalidated by setChars; length/charAt read the array directly and subSequence copies into a new String.

<a id="u-ddcb29c1c6dc"></a>
### `Streams.java-streams`

`class Streams` · [gson/src/main/java/com/google/gson/internal/Streams.java:L37-L38][f2]

Static bridge between streams and JsonElement trees.

parse(reader) peeks first (marking the document non-empty), then reads via JsonElementTypeAdapter; an EOFException on the initial peek returns JsonNull.INSTANCE for empty documents (legacy compatibility), while a later EOF becomes JsonSyntaxException; MalformedJsonException and NumberFormatException become JsonSyntaxException, other IOException becomes JsonIOException. write delegates to JsonElementTypeAdapter. writerForAppendable returns the Appendable itself when it is already a Writer, else wraps it in AppendableWriter. The private constructor throws UnsupportedOperationException.

<a id="u-84e7ff17f8a4"></a>
### `gson/src/main/java/com/google/gson/JsonElement.java:JsonElement (15)`

`class JsonElement` · [gson/src/main/java/com/google/gson/JsonElement.java:L383-L420][f1]

This region documents JsonElement.toString, which serializes the element to compact JSON by writing through a lenient JsonWriter over a StringBuilder (lenient so NaN/Infinity values do not fail); the IOException from the underlying writer is caught and rethrown as AssertionError, which should never occur for a StringBuilder.

<a id="u-0310357cd012"></a>
### `JsonElement.toString`

`@Override public String toString()` · [gson/src/main/java/com/google/gson/JsonElement.java:L420-L433][f1]

Serializes this element to its JSON text form by writing through a lenient JsonWriter into a StringBuilder.

Strictness is set to LENIENT so serialization never fails on non-spec values like NaN or Infinity, which are written verbatim. The result is JSON with quoting/escaping, not the raw string value (getAsString is the counterpart for that). Any IOException from the underlying writer is impossible for a StringBuilder sink and is converted to AssertionError.

<a id="u-abc7bd1c85bd"></a>
### `JsonElementTypeAdapter.write`

`@Override public void write(JsonWriter out, JsonElement value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java:L138-L170][f3]

Writes a JsonElement tree to a writer, recursively.

null or JsonNull writes nullValue. A JsonPrimitive writes its number as a number, its boolean as a boolean, otherwise its string value. A JsonArray writes beginArray, recurses on each element, endArray; a JsonObject writes beginObject, then each entry's name and recursed value, endObject. Any other JsonElement subclass throws IllegalArgumentException("Couldn't write <class>").

calls: [JsonPrimitive.isNumber](../../catalog.json)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonElement.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/Streams.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java
