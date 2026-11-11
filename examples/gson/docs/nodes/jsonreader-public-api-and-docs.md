# JsonReader public API and docs

**Capability.** Defines JsonReader's documented contract and configuration: token-consumption methods, path tracking, strictness, nesting limits, and lifecycle.

Readers wanting the pull parser's public surface — nextX methods, JSONPath helpers, strictness and nesting configuration — should start here. It pairs javadoc regions with the corresponding configuration and state plumbing, including the internal name-promotion hook.

**Depends on.**

- [Lexing and buffer lookahead](lexing-and-buffer-lookahead.md) · graph-confirmed · 1 edge(s)
- [Token consumption and value decoding](token-consumption-and-value-decoding.md) · graph-confirmed · 1 edge(s)

Parent: [Streaming JsonReader](streaming-jsonreader.md)

## Units (29)

<a id="u-11c476feeb26"></a>
### `JsonReader.java-boolean-and-null-contracts`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1030-L1037][f1]

Documentation regions for nextBoolean and nextNull: nextBoolean returns and consumes the boolean value (IllegalStateException otherwise); nextNull consumes the next token and asserts it is the literal null, also throwing IllegalStateException on mismatch.

<a id="u-87e7f0ae40d8"></a>
### `JsonReader.java-json-path-accessors`

`private String getPath(boolean usePreviousPath)` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1785-L1816][f1]

getPath(boolean) builds a '$'-rooted dot-notation path from the scope stack: arrays append [index] (the previous-path variant decrements the last array index when positive so it points at the last consumed element), objects append '.' plus the recorded name when present, and document/closed scopes contribute nothing; an unknown scope raises AssertionError.

getPath() points at the next/current location, getPreviousPath() at the previous/current one for use after a value is consumed.

<a id="u-29f0b9f09d23"></a>
### `JsonReader.java-jsonpath-accessor-docs`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1816-L1832][f1]

Documentation regions for getPath and getPreviousPath: both return a dot-notation JSONPath.

getPath points at the next array element index (even absent ones) and the current or last object property, useful before consuming a value; getPreviousPath points at the previous array element (index 0 if none consumed yet) and the last or current property, useful after consumption.

<a id="u-9ce7e32ae6f7"></a>
### `JsonReader.java-jsonreader-class-and-constructor`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L212-L213][f1]

Pull parser that reads a JSON document from a Reader as a depth-first token stream, tracking scope on a manual stack and the current JSON path.

The constructor requires a non-null Reader (NullPointerException otherwise via Objects.requireNonNull). State: a 1024-char buffer with pos/limit and bufferStart for character offsets, line/lineStart for locations, a peeked token code with peekedLong/peekedNumberLength/peekedString payloads, an int scope stack initialized with EMPTY_DOCUMENT (grown by push), parallel pathNames/pathIndices arrays, strictness defaulting to LEGACY_STRICT, nestingLimit defaulting to 255, and a promotedName flag. Not thread-safe; one stream per instance.

<a id="u-2a90810d2794"></a>
### `JsonReader.java-lenient-mode-documentation-regions`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L325-L340][f1]

Documentation regions for the deprecated lenient toggle and its query.

The setLenient javadoc directs callers to setStrictness, mapping true to LENIENT and false to LEGACY_STRICT, and notes that former setLenient(false) users may prefer STRICT. The isLenient javadoc specifies it returns true only when the strictness equals LENIENT.

<a id="u-2fcdc7d8fe65"></a>
### `JsonReader.java-lenient-toggle`

`@Deprecated // Don't specify @InlineMe, so caller with setLenient(false) becomes aw…` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L340-L346][f1]

Deprecated pair: setLenient(true) maps to Strictness.LENIENT, false to LEGACY_STRICT by delegating to setStrictness; isLenient reports whether the current strictness is exactly LENIENT.

No @InlineMe so callers of setLenient(false) notice STRICT.

<a id="u-d18a478b9e14"></a>
### `JsonReader.java-location-reporting`

`@Override public String toString()` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1774-L1777][f1]

locationString renders " at line L column C path P" using 1-based line and column and the current JSON path; toString prefixes the simple class name to it.

Used throughout exception messages.

<a id="u-c21b8aa528b7"></a>
### `JsonReader.java-nesting-limit-accessors`

`public final void setNestingLimit(int limit)` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L444-L449][f1]

setNestingLimit stores the maximum number of simultaneously open arrays/objects, throwing IllegalArgumentException for a negative limit; getNestingLimit returns it.

The limit is enforced by push, protecting recursive adapters from StackOverflowError.

<a id="u-8aba65d52817"></a>
### `JsonReader.java-strictness-and-nesting-limit-accessor-docs`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L414-L422][f1]

Documentation regions for the getStrictness and getNestingLimit accessors, each stating it returns the corresponding configured value.

<a id="u-2f741fd7c747"></a>
### `JsonReader.java-structure-token-contracts`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L459-L467][f1]

Documentation regions for beginArray/endArray and beginObject/endObject: each consumes the next token and asserts it is the matching structural delimiter, throwing IllegalStateException when the next token does not match.

hasNext's contract (another element in the current array or object) is covered by its own region elsewhere.

<a id="u-9447bb1c759a"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader (7)`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L951-L958][f1]

Documentation region for nextName: returns and consumes the next property-name token, throwing IllegalStateException when the next token is not a name.

<a id="u-3aed3d461a41"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader (10)`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L988-L996][f1]

Documentation region for nextString: returns the string value of the next token, and for a number token returns its string form; IllegalStateException when the next token is not a string.

<a id="u-895059664679"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader (13)`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1072-L1084][f1]

Documentation region for nextDouble: returns the next token as double, parsing string tokens via Double.parseDouble; documents IllegalStateException for non-number/non-string tokens, NumberFormatException for unparseable literals, and MalformedJsonException for NaN or Infinity when the reader is not lenient.

<a id="u-0b91e6ee7c12"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader (14)`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1131-L1142][f1]

Documentation region for nextLong: returns the next token as long, attempting to parse string tokens; throws IllegalStateException for wrong token types and NumberFormatException when the literal cannot be parsed or exactly represented as a long.

<a id="u-ebde7e2f129b"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader (15)`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1200-L1209][f1]

Documentation region for nextQuotedValue: documents that it returns the text up to but excluding the closing quote, unescaping escape sequences, that the opening quote is already consumed, and that the closing quote is consumed but not included in the result.

<a id="u-f5fd2bfac6e0"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader (19)`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1403-L1414][f1]

Documentation region for nextInt: mirrors nextLong's contract at int precision — string tokens are parsed as int, and NumberFormatException is thrown when the value cannot be parsed or exactly represented as an int; IllegalStateException for other token types.

<a id="u-9e7e3d10ede8"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader (20)`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1474-L1482][f1]

Documentation region for close: closes this reader and the underlying Reader, and warns that using the reader afterwards throws IllegalStateException in most cases.

<a id="u-472d04c4329d"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader (21)`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1488-L1506][f1]

Documentation region for skipValue: recursively skips the next value, with per-token behavior enumerated — begin tokens skip the whole nested structure, primitives are skipped, a property name is skipped alone (the value needs a second call), end tokens are skipped singly, and end-of-document makes the call a no-op.

<a id="u-db89b48e3980"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader (23)`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1632-L1639][f1]

Documentation region for fillBuffer: states it returns true once at least the requested minimum characters are buffered, and false if input is exhausted before that many are available.

<a id="u-5a7f6884773a"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader (24)`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1733-L1739][f1]

Documentation region for skipToEndOfLine: documents that it advances past the next newline, and that for a "\r\n" terminator the caller must consume the '\n' as whitespace.

<a id="u-800702d35a63"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader (29)`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1852-L1861][f1]

Documentation region for getCharacterOffset: returns the 0-based character offset of the current position in the stream, or -1 when not reading from a character stream.

<a id="u-f0c753509107"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader (30)`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1863-L1872][f1]

Documentation region for readEscapeCharacter: documents that it unescapes the character(s) following an already-consumed backslash, supporting both \uXXXX Unicode escapes and two-character escapes, and throwing MalformedJsonException for malformed sequences.

<a id="u-36157895397c"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader (33)`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L355-L411][f1]

Documentation region for setStrictness: enumerates the accepted input per Strictness level.

STRICT accepts only RFC 8259 JSON; LEGACY_STRICT (the default) additionally tolerates any-capitalization literals, the \' escape, escaped LF, and unescaped control characters; LENIENT further accepts the non-execute prefix, multiple top-level values, NaN/Infinity, //, # and /* */ comments, unquoted or single-quoted names and strings, ';' array separators, omitted array elements as null, '=' or '=>' name/value separators, and ';' between pairs.

<a id="u-6b0d134e0b60"></a>
### `gson/src/main/java/com/google/gson/stream/JsonReader.java:JsonReader (37)`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L424-L444][f1]

Documentation region for setNestingLimit: defines the limit as the number of simultaneously open arrays/objects (0 forbids any), explains it guards recursive TypeAdapters against StackOverflowError, states the default of 255, and documents IllegalArgumentException for a negative limit.

<a id="u-d2a060c9f8fd"></a>
### `JsonReader.close`

`@Override public void close() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1482-L1488][f1]

Closes the underlying Reader and resets the parser to a CLOSED state with a single-element stack, so subsequent parsing operations throw IllegalStateException in most cases.

<a id="u-a44a34a22011"></a>
### `JsonReader.getCharacterOffset`

`public long getCharacterOffset()` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1861-L1863][f1]

Returns the 0-based character offset of the current position as bufferStart + pos; per the javadoc, -1 when not reading from a character stream, though this implementation always computes from the buffer.

<a id="u-8f7ae6baf6aa"></a>
### `JsonReader.hasNext`

`public boolean hasNext() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L542-L548][f1]

Reports whether the current array or object has another element by peeking: false only for END_OBJECT, END_ARRAY, or EOF; true otherwise.

<a id="u-6e29514879a1"></a>
### `JsonReader.promoteNameToValue`

`@Override public void promoteNameToValue(JsonReader reader) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1995-L2020][f1]

Static initializer that installs a JsonReaderInternalAccess whose promoteNameToValue retypes a peeked name token (double/single-quoted or unquoted) into the corresponding value token so the next next* call reads the name as a value; JsonTreeReader instances are delegated to their own implementation, and any non-name token throws unexpectedTokenError.

Sets promotedName so the path is updated once the name is consumed as a value.

<a id="u-b2f12d026de5"></a>
### `JsonReader.validateAscii`

`private void validateAscii(String s) throws MalformedJsonException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1986-L1990][f1]

Throws MalformedJsonException (with the offending string) if the argument contains non-ASCII characters, delegating the check to JsonTreeReader.isAllAscii; used before parsing quoted/unquoted strings as numbers.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonReader.java
