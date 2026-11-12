# Streaming JSON reader core

**Capability.** Implements streaming JSON reader state, token queries, nesting limits, paths, and diagnostics.

Use for JsonReader configuration and core tokenizer/reader behavior. Units show path/location queries, nesting limits, token peeking, and reader initialization.

**Depends on.**

- [JSON token scanning](json-token-scanning.md) · graph-confirmed · 3 edge(s)

Parent: [Streaming JSON reader internals](streaming-json-reader-internals.md)

## Units (14)

<a id="u-1c90044749e1"></a>
### `JsonReader.java-character-offset-query`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1852-L1861][f1]

Character-offset query.

It returns the absolute buffer start plus the current buffer position.

<a id="u-b48a25324ace"></a>
### `JsonReader.java-container-continuation-check`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L539-L542][f1]

Container continuation check.

It peeks if needed and returns false only for END_OBJECT, END_ARRAY, or END_DOCUMENT; all other token types return true.

<a id="u-507a845868a5"></a>
### `JsonReader.java-internal-name-promotion-hook`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1990-L1995][f1]

Internal name-promotion hook.

The static initializer installs an access object; for a tree reader it delegates. Otherwise it peeks if needed, converts a quoted or unquoted name token into the corresponding value token, throws an unexpected-token error for non-names, and marks that the promoted name still needs path recording.

<a id="u-14bc6026e71b"></a>
### `JsonReader.java-jsonpath-rendering`

`private String getPath(boolean usePreviousPath)` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1785-L1816][f1]

JSONPath rendering.

The public query returns the current path. The private renderer starts at '$' and walks the scope stack: arrays append their path index, decrementing it for the previous-path variant only when it is positive and the last scope; objects append a dot and the stored name when present; document and closed scopes add nothing; an unknown scope triggers AssertionError.

<a id="u-4febcb999ce8"></a>
### `JsonReader.java-lenient-toggle-and-query`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L325-L340][f1]

Deprecated lenient toggle and query.

Setting true selects LENIENT; setting false selects LEGACY_STRICT. The query is true only when strictness equals LENIENT.

<a id="u-be4dfc5b49e4"></a>
### `JsonReader.java-nesting-limit-configuration`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L424-L444][f1]

Nesting-limit configuration and query.

The setter throws IllegalArgumentException for a negative limit and otherwise stores it; the getter returns it. The default is 255, and the limit is enforced when a new array or object scope is pushed.

<a id="u-cf6e711a3357"></a>
### `JsonReader.java-previous-location-path`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1834-L1850][f1]

Previous-location JSONPath query.

It returns the same rendering as the current path but uses the previous array index when applicable.

<a id="u-bcdc386021d7"></a>
### `JsonReader.java-reader-shutdown`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1474-L1482][f1]

Reader shutdown.

It clears the peeked token, replaces the scope stack with a single closed scope, and closes the underlying Reader; later use generally sees the closed scope.

<a id="u-37bc5bea00e1"></a>
### `JsonReader.java-token-type-query`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L548-L551][f1]

Token-type query without consumption.

It peeks if needed and maps internal peeked states to JsonToken values; an unknown internal state triggers AssertionError.

<a id="u-92ec22311967"></a>
### `JsonReader`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L212-L213][f1]

Streaming JSON tokenizer/reader over a Reader that exposes depth-first tokens and tracks a scope stack, strictness, nesting limit, and JSON path.

It is single-stream and not thread-safe; parsing methods consume or peek tokens and throw MalformedJsonException or IllegalStateException on malformed or unexpected input.

<a id="u-373336578118"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L299-L313][f1]

Initializes each reader's nesting stack with an empty-document scope so parsing starts at the document level.

After the stack and size fields are initialized, it stores the empty-document scope at index 0 and increments the stack size to 1; later push/pop and path reporting rely on this baseline. No input is read and no exception is thrown here.

<a id="u-5532d9fa4924"></a>
### `JsonReader.locationString`

`String locationString()` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1779-L1783][f1]

Location formatter.

It reports one-based line and column plus the current JSON path.

<a id="u-508b6f722f72"></a>
### `JsonReader.toString`

`@Override public String toString()` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1774-L1777][f1]

Diagnostic string.

It returns the runtime class simple name followed by the current location string.

<a id="u-b2f12d026de5"></a>
### `JsonReader.validateAscii`

`private void validateAscii(String s) throws MalformedJsonException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1986-L1990][f1]

ASCII validation for numeric strings.

It throws a malformed-JSON syntax error when the string contains any non-ASCII character.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonReader.java
