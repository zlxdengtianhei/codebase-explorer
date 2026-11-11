# JSON Parsing Facades

**Capability.** Provides JsonParser and JsonStreamParser for turning JSON text or readers into JsonElement trees.

This module covers tree parsing: single-document parsing that rejects trailing data, and lenient iteration over concatenated JSON values. Readers converting raw JSON text into element trees should look here.

**Depends on.**

- [Core Gson Contracts and Facade](core-gson-contracts-and-facade.md) · graph-confirmed · 3 edge(s) · JsonParser facades use the core Gson contracts to turn text into element trees.
- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) · graph-only · 3 edge(s)
- [Tree Element Bridge](tree-element-bridge.md) · graph-only · 3 edge(s)

Parent: [Public API and Type Resolution](public-api-and-type-resolution.md)

## Units (6)

<a id="u-7c09129e5edc"></a>
### `JsonParser.java-jsonparser-entry-points-and-deprecated-methods`

`class JsonParser` · [gson/src/main/java/com/google/gson/JsonParser.java:L73-L77][f1]

Static facade for parsing JSON into JsonElement trees.

parseString wraps the string in a StringReader and delegates to parseReader(Reader). The class's public constructor and the three instance parse methods are deprecated; each parse overload simply forwards to its static counterpart (parseString, parseReader(Reader), parseReader(JsonReader)).

<a id="u-331ccd417571"></a>
### `JsonParser.java-jsonparser-parsereader-variants`

`class JsonParser` · [gson/src/main/java/com/google/gson/JsonParser.java:L78-L91][f1]

These class regions of JsonParser contain the two parseReader implementations plus the deprecated parse(Reader) bridge.

parseReader(Reader) wraps the reader in a JsonReader, delegates to parseReader(JsonReader), and then enforces single-document input: if the parsed element is not JSON null and the reader's next token is not END_DOCUMENT it throws JsonSyntaxException for trailing data; MalformedJsonException and NumberFormatException are converted to JsonSyntaxException and IOException to JsonIOException. parseReader(JsonReader) reads one value from an existing reader via Streams.parse: if the reader's strictness is LEGACY_STRICT it temporarily switches to LENIENT, catches StackOverflowError/OutOfMemoryError as JsonParseException, and restores the original strictness in finally. The deprecated parse(Reader) simply forwards to parseReader(Reader).

<a id="u-5cdbb7a14ba5"></a>
### `JsonStreamParser.java-jsonstreamparser`

`class JsonStreamParser implements Iterator<JsonElement>` · [gson/src/main/java/com/google/gson/JsonStreamParser.java:L51-L52][f2]

Iterator<JsonElement> that reads multiple concatenated JSON values from a Reader or String in lenient mode; conditionally thread-safe, requiring external synchronization across threads.

hasNext() synchronizes on an internal lock, peeks the reader, and returns true unless the token is END_DOCUMENT; MalformedJsonException becomes JsonSyntaxException and IOException becomes JsonIOException. next() first checks hasNext() and throws NoSuchElementException when exhausted, then parses one element via Streams.parse, converting StackOverflowError/OutOfMemoryError to JsonParseException. remove() always throws UnsupportedOperationException.

<a id="u-b6102efda8ea"></a>
### `JsonStreamParser.java-jsonstreamparser-iterator-core`

`class JsonStreamParser implements Iterator<JsonElement>` · [gson/src/main/java/com/google/gson/JsonStreamParser.java:L71-L82][f2]

These class regions of JsonStreamParser contain the iterator core.

next() first checks hasNext(); if no element remains it throws NoSuchElementException, otherwise it parses one value via Streams.parse, converting StackOverflowError/OutOfMemoryError to JsonParseException. hasNext() synchronizes on an internal lock and returns whether the reader's peek is not END_DOCUMENT, converting MalformedJsonException to JsonSyntaxException and IOException to JsonIOException. remove() is unconditionally unsupported and throws UnsupportedOperationException. Note next() calls hasNext() (which locks) but its own parse is not synchronized, so cross-thread use still requires external synchronization as documented.

<a id="u-ec3cb47a826f"></a>
### `JsonParser.parseReader`

`public static JsonElement parseReader(Reader reader) throws JsonIOException, JsonSynt…` · [gson/src/main/java/com/google/gson/JsonParser.java:L107-L120][f1]

Parses an entire Reader into a JsonElement, rejecting trailing or multiple top-level elements.

It wraps the reader in a JsonReader, delegates to parseReader(JsonReader), and if the result is not JSON null and the reader's next token is not END_DOCUMENT, throws JsonSyntaxException("Did not consume the entire document."). MalformedJsonException and NumberFormatException are converted to JsonSyntaxException; IOException is converted to JsonIOException.

<a id="u-a100555ee735"></a>
### `gson/src/main/java/com/google/gson/JsonParser.java:JsonParser.parseReader`

`public static JsonElement parseReader(JsonReader reader) throws JsonIOException, Json…` · [gson/src/main/java/com/google/gson/JsonParser.java:L136-L150][f1]

Parses the next value from a JsonReader as a tree, allowing multiple top-level elements and trailing data.

If the reader's strictness is LEGACY_STRICT it temporarily switches to LENIENT for backward compatibility; other strictness values (including STRICT) are used as-is. It delegates to Streams.parse, converts StackOverflowError/OutOfMemoryError to JsonParseException, and in a finally block restores the reader's original strictness.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonParser.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonStreamParser.java
