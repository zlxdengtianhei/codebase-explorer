# JsonElement tree reader

**Capability.** Implements JsonReader over JsonElement trees, including token navigation, paths, skipping, and validation.

Use when reading tokens from an existing JSON tree. Units show tree-backed reader, path construction, token expectations, skipping, and ASCII validation.

**Depends on.**

- [Streaming JSON reader internals](streaming-json-reader-internals.md) · graph-confirmed · 1 edge(s)
- [JSON primitive values](json-primitive-values.md) · graph-only · 3 edge(s)

**Depended on by.**

- [Streaming JSON reader internals](streaming-json-reader-internals.md) · graph-confirmed · 1 edge(s)
- [JsonElement tree adapter](jsonelement-tree-adapter.md) · graph-only · 1 edge(s)

Parent: [Streaming and tree reading](streaming-and-tree-reading.md)

## Units (24)

<a id="u-d9fd30c98c40"></a>
### `JsonTreeReader.java-container-navigation`

`@Override public void beginArray() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L81-L87][f1]

beginArray expects BEGIN_ARRAY, pushes the array iterator, and resets its path index.

endArray expects END_ARRAY, pops iterator and array, then increments parent index if any. beginObject expects BEGIN_OBJECT and pushes the object entry-set iterator. endObject expects END_OBJECT, clears the last path name, pops iterator and object, then increments parent index if any.

<a id="u-51ef4845bc4b"></a>
### `JsonTreeReader.java-jsontreereader-class`

`class JsonTreeReader extends JsonReader` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L39-L42][f1]

JsonReader over a JsonElement tree.

Maintains a manual stack of elements/iterators plus parallel path name/index arrays; constructor pushes the root element. close replaces stack with closed sentinel. Path and location helpers report tree position; character offset is always -1.

<a id="u-89ab517088a6"></a>
### `JsonTreeReader.java-location-helpers`

`@Override public long getCharacterOffset()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L418-L421][f1]

getCharacterOffset always returns -1.

locationString returns ' at path ' plus the current path.

<a id="u-10b43c360d3d"></a>
### `JsonTreeReader.java-nextlong-and-nextint`

`@Override public long nextLong() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L263-L285][f1]

Both accept NUMBER or STRING; other tokens throw IllegalStateException.

For STRING input they first validate ASCII and throw MalformedJsonException on non-ASCII. They then call getAsLong/getAsInt, wrap NumberFormatException with path, pop, and increment parent index if any.

<a id="u-e3585375e799"></a>
### `JsonTreeReader.java-nextname`

`private String nextName(boolean skipName) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L191-L199][f1]

nextName(boolean) expects NAME, advances the object iterator, records the key in pathNames (or '<skipped>' when skipping), pushes the value, and returns the key.

Public nextName calls it without skipping.

<a id="u-1e48e76d8c69"></a>
### `JsonTreeReader.java-path-reporting`

`private String getPath(boolean usePreviousPath)` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L382-L406][f1]

getPath(boolean) builds a '$' path by scanning stack pairs: arrays append [index], objects append .name when known.

getPath uses current indices; getPreviousPath decrements the last/next array index when appropriate. getPath and getPreviousPath are the public wrappers.

<a id="u-33ce1c0e6652"></a>
### `JsonTreeReader.java-stack-helpers`

`private Object peekStack()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L173-L175][f1]

peekStack returns the top stack entry.

popStack decrements size, nulls the vacated slot, and returns the removed entry.

<a id="u-1c1c97e7ec5f"></a>
### `JsonTreeReader.java-unreadable-reader`

`@Override public int read(char[] buffer, int offset, int count)` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L42-L45][f1]

Anonymous Reader backing the superclass; read and close throw AssertionError because tree reading never uses character input.

<a id="u-8348c8baf1fc"></a>
### `JsonTreeReader.close`

`@Override public void close() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L324-L328][f1]

close replaces the stack with the closed sentinel and sets size to one, so later peeks report closed.

<a id="u-db82f0f2e853"></a>
### `JsonTreeReader.expect`

`private void expect(JsonToken expected) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L184-L189][f1]

expect compares peek to the expected token; mismatch throws IllegalStateException with expected, actual, and current path.

<a id="u-88f3a25125c5"></a>
### `JsonTreeReader.hasNext`

`@Override public boolean hasNext() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L117-L123][f1]

hasNext returns false for END_OBJECT, END_ARRAY, or END_DOCUMENT; true otherwise.

<a id="u-120b1e545450"></a>
### `JsonTreeReader.isAllAscii`

`public static boolean isAllAscii(String s)` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L428-L435][f1]

isAllAscii returns false if any char code exceeds 127; otherwise true.

<a id="u-f92936b65f6f"></a>
### `JsonTreeReader.nextBoolean`

`@Override public boolean nextBoolean() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L220-L228][f1]

nextBoolean expects BOOLEAN, pops the primitive, returns getAsBoolean, and increments the parent path index if any.

<a id="u-e949c4e113cb"></a>
### `JsonTreeReader.nextDouble`

`@Override public double nextDouble() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L239-L261][f1]

nextDouble accepts NUMBER or STRING; other tokens throw IllegalStateException.

It reads getAsDouble, wraps NumberFormatException with path, rejects NaN/Infinity when not lenient with MalformedJsonException, then pops and increments parent index. It does not ASCII-validate STRING input.

<a id="u-37a8966bfb18"></a>
### `JsonTreeReader.nextJsonElement`

`JsonElement nextJsonElement() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L311-L322][f1]

nextJsonElement rejects NAME, END_ARRAY, END_OBJECT, and END_DOCUMENT with IllegalStateException; otherwise returns the current element and advances past it with skipValue.

<a id="u-3151588a9d9d"></a>
### `JsonTreeReader.nextNull`

`@Override public void nextNull() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L230-L237][f1]

nextNull expects NULL, pops it, and increments the parent path index if any.

<a id="u-8e749cfd855b"></a>
### `JsonTreeReader.nextString`

`@Override public String nextString() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L206-L218][f1]

nextString accepts STRING or NUMBER; other tokens throw IllegalStateException.

It pops the primitive, returns getAsString, and increments the parent path index if any.

<a id="u-eacc2c653e08"></a>
### `JsonTreeReader.numberFormatException`

`private NumberFormatException numberFormatException(String message, NumberFormatExcep…` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L445-L449][f1]

numberFormatException builds a NumberFormatException with the message plus current path and initializes its cause to the supplied exception.

<a id="u-4c8bc46181ff"></a>
### `JsonTreeReader.peek`

`@SuppressWarnings("ReferenceEquality") @Override public JsonToken peek() throws IOExc…` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L127-L171][f1]

peek returns END_DOCUMENT when stack empty.

For an iterator, if it has next returns NAME for object or pushes next array element and recurses; if exhausted returns END_OBJECT/END_ARRAY. For JsonObject/JsonArray returns BEGIN_OBJECT/BEGIN_ARRAY; for JsonPrimitive returns STRING/BOOLEAN/NUMBER or AssertionError; for JsonNull returns NULL; closed sentinel throws IllegalStateException; other element subclasses throw MalformedJsonException.

<a id="u-714b59883760"></a>
### `JsonTreeReader.promoteNameToValue`

`public void promoteNameToValue() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L361-L370][f1]

promoteNameToValue expects NAME, advances the object iterator, records the key in pathNames, pushes the value, then pushes a JsonPrimitive of the key so the name can be read as a value.

<a id="u-f525a65badc2"></a>
### `JsonTreeReader.push`

`private void push(Object newTop)` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L372-L380][f1]

push appends an object to the stack, doubling stack, pathIndices, and pathNames arrays when full.

<a id="u-5f1e3eb36679"></a>
### `JsonTreeReader.skipValue`

`@Override public void skipValue() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L330-L354][f1]

skipValue switches on peek: NAME consumes a name with skip flag; END_ARRAY/END_OBJECT call endArray/endObject; END_DOCUMENT does nothing; default pops the value and increments parent index if any.

<a id="u-f6881bf7e335"></a>
### `JsonTreeReader.toString`

`@Override public String toString()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L356-L359][f1]

toString returns the class simple name plus current path location.

<a id="u-2e16d40670d0"></a>
### `JsonTreeReader.validateAscii`

`private void validateAscii(String s) throws MalformedJsonException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L437-L442][f1]

validateAscii throws MalformedJsonException with the string and current path when isAllAscii is false.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java
