# In-memory tree reader

**Capability.** Implements JsonReader over an in-memory JsonElement tree, mirroring the streaming reader's token API with a manual stack.

Readers who need to parse an existing JsonElement tree with the JsonReader interface should look here. It provides peek/next methods, path tracking, name promotion, and tree-specific validation like ASCII checks.

**Depends on.**

- [Streaming JsonReader](streaming-jsonreader.md) · graph-confirmed · 1 edge(s)
- [JSON Primitive Values](json-primitive-values.md) · graph-only · 3 edge(s)

**Depended on by.**

- [Streaming JsonReader](streaming-jsonreader.md) · graph-confirmed · 1 edge(s)

Parent: [JSON Reading Infrastructure](json-reading-infrastructure.md)

## Units (20)

<a id="u-dd9231369132"></a>
### `JsonTreeReader.java-getpath-and-getpreviouspath`

`private String getPath(boolean usePreviousPath)` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L382-L406][f1]

getPath builds a '$'-rooted path walking the stack: JsonArray scopes append [index] using pathIndices, JsonObject scopes append '.' plus the recorded name (or nothing if null).

With usePreviousPath (getPreviousPath), the last array index is decremented by one when it is positive and the iterator is the top or second-top stack entry, so the path points at the element just consumed rather than the next one.

<a id="u-f637dc7a2db1"></a>
### `JsonTreeReader.java-nextboolean-nextnull-nextint`

`@Override public boolean nextBoolean() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L220-L228][f1]

nextBoolean expects BOOLEAN and pops the primitive's boolean; nextNull expects NULL and pops.

nextInt accepts NUMBER or STRING (STRING values are first validated ASCII), converts via getAsInt, converting NumberFormatException into a path-annotated NumberFormatException; all increment the parent path index when present.

<a id="u-5126c8fd25ce"></a>
### `JsonTreeReader.java-nextdouble-and-nextlong`

`@Override public double nextDouble() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L239-L261][f1]

Both accept NUMBER or STRING tokens (IllegalStateException otherwise) and convert via getAsDouble/getAsLong, wrapping NumberFormatException with the current path; STRING inputs are ASCII-validated first.

nextDouble additionally rejects NaN/infinite results with MalformedJsonException when the reader is not lenient. Both pop the primitive and bump the parent path index.

calls: [JsonReader.isLenient](../../catalog.json)

<a id="u-e3585375e799"></a>
### `JsonTreeReader.java-nextname`

`private String nextName(boolean skipName) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L191-L199][f1]

nextName expects NAME, advances the object's entry iterator, records the key in pathNames (as "<skipped>" when skipName), pushes the entry's value, and returns the key.

<a id="u-f4364ad11b74"></a>
### `JsonTreeReader.java-stack-helpers-and-expect`

`private Object peekStack()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L173-L175][f1]

peekStack returns the top stack entry; popStack decrements stackSize, nulls the slot, and returns the removed value; expect throws IllegalStateException with the expected token, actual token, and location string when peek() differs.

<a id="u-76d71089e81b"></a>
### `JsonTreeReader.java-structure-navigation`

`@Override public void beginArray() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L81-L87][f1]

beginArray/beginObject verify the expected token via expect, then push the collection's iterator (beginArray also resets the enclosing path index).

endArray/endObject pop the iterator and the collection, null the last path name for objects, and increment the parent's path index if a parent exists. hasNext peeks and returns true unless the token is an END_OBJECT, END_ARRAY, or END_DOCUMENT.

<a id="u-3fac6d55e064"></a>
### `JsonTreeReader`

`class JsonTreeReader extends JsonReader` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L39-L42][f1]

JsonReader implementation that walks an in-memory JsonElement tree as if it were a character stream, using a manual Object[] nesting stack holding JsonElements and their iterators, plus parallel pathNames/pathIndices arrays for path tracking.

Constructed with the root element pushed onto the stack and an unreadable Reader stub passed to the superclass.

<a id="u-8348c8baf1fc"></a>
### `JsonTreeReader.close`

`@Override public void close() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L324-L328][f1]

close replaces the stack with a single SENTINEL_CLOSED entry so any subsequent peek throws IllegalStateException('JsonReader is closed'); it does not free the tree.

<a id="u-ea0e189b3381"></a>
### `JsonTreeReader.getCharacterOffset`

`@Override public long getCharacterOffset()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L418-L421][f1]

getCharacterOffset always returns -1 because there is no character stream.

<a id="u-120b1e545450"></a>
### `JsonTreeReader.isAllAscii`

`public static boolean isAllAscii(String s)` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L428-L435][f1]

isAllAscii returns whether every char has code point at most 127.

<a id="u-079b7b13ffd6"></a>
### `JsonTreeReader.locationString`

`private String locationString()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L423-L425][f1]

locationString returns ' at path ' followed by the current path, used in exception messages.

<a id="u-37a8966bfb18"></a>
### `JsonTreeReader.nextJsonElement`

`JsonElement nextJsonElement() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L311-L322][f1]

nextJsonElement rejects NAME, END_ARRAY, END_OBJECT, and END_DOCUMENT tokens with IllegalStateException, otherwise returns the current JsonElement from the top of stack and consumes it via skipValue.

<a id="u-8e749cfd855b"></a>
### `JsonTreeReader.nextString`

`@Override public String nextString() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L206-L218][f1]

nextString requires STRING or NUMBER tokens (else IllegalStateException with location), pops the JsonPrimitive and returns getAsString, incrementing the parent path index when a parent exists.

<a id="u-eacc2c653e08"></a>
### `JsonTreeReader.numberFormatException`

`private NumberFormatException numberFormatException(String message, NumberFormatExcep…` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L445-L449][f1]

numberFormatException creates a NumberFormatException whose message appends the current path and whose cause is the original exception.

<a id="u-4c8bc46181ff"></a>
### `JsonTreeReader.peek`

`@SuppressWarnings("ReferenceEquality") @Override public JsonToken peek() throws IOExc…` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L127-L171][f1]

peek maps the top of stack to a token: empty stack means END_DOCUMENT; an Iterator is either an object's entry iterator (NAME if it has a next entry, else END_OBJECT) or an array iterator (pushes the next element and recurses, else END_ARRAY), distinguishing by whether the stack entry below is a JsonObject; JsonObject/JsonArray yield BEGIN_OBJECT/BEGIN_ARRAY; JsonPrimitive yields STRING, BOOLEAN, or NUMBER by its content kind (AssertionError if none); JsonNull yields NULL; the closed sentinel throws IllegalStateException; any custom JsonElement subclass throws MalformedJsonException naming the class.

calls: [JsonPrimitive.isString](../../catalog.json), [JsonPrimitive.isBoolean](../../catalog.json), [JsonPrimitive.isNumber](../../catalog.json)

<a id="u-714b59883760"></a>
### `JsonTreeReader.promoteNameToValue`

`public void promoteNameToValue() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L361-L370][f1]

promoteNameToValue expects NAME, consumes the object entry, records the name in pathNames so the path reflects the promotion, then pushes both the entry's value and a JsonPrimitive of the name so a subsequent nextString reads the name as a value.

<a id="u-f525a65badc2"></a>
### `JsonTreeReader.push`

`private void push(Object newTop)` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L372-L380][f1]

push doubles stack, pathIndices, and pathNames arrays via Arrays.copyOf when full, then places the new entry on top.

<a id="u-5f1e3eb36679"></a>
### `JsonTreeReader.skipValue`

`@Override public void skipValue() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L330-L354][f1]

skipValue dispatches on the peeked token: NAME consumes the name recording '<skipped>' in the path; END_ARRAY/END_OBJECT close that scope; END_DOCUMENT does nothing; any value token is popped with the parent path index incremented.

<a id="u-f6881bf7e335"></a>
### `JsonTreeReader.toString`

`@Override public String toString()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L356-L359][f1]

toString returns the class simple name plus the current path location string.

<a id="u-2e16d40670d0"></a>
### `JsonTreeReader.validateAscii`

`private void validateAscii(String s) throws MalformedJsonException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L437-L442][f1]

validateAscii throws MalformedJsonException naming the offending string and location when the string contains any non-ASCII character.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java
