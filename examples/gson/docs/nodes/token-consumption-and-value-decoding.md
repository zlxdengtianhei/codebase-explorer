# Token consumption and value decoding

**Capability.** Implements the typed nextX methods, peeking, escape decoding, and the malformed-JSON exception used when input violates the contract.

This module holds the concrete consumption logic behind the documented API: booleans, numbers, strings, names, and escape sequences. It also defines MalformedJsonException and STRICT-mode surrogate validation.

**Depends on.**

- [Lexing and buffer lookahead](lexing-and-buffer-lookahead.md) · graph-confirmed · 14 edge(s)
- [Built-in JDK Type Adapters](built-in-jdk-type-adapters.md) · graph-only · 2 edge(s)

**Depended on by.**

- [JsonReader public API and docs](jsonreader-public-api-and-docs.md) · graph-confirmed · 1 edge(s)
- [Lexing and buffer lookahead](lexing-and-buffer-lookahead.md) · graph-confirmed · 9 edge(s) · Value decoding builds on the lexer's buffer filling and token peeking machinery.
- [Structural navigation and skipping](structural-navigation-and-skipping.md) · graph-confirmed · 7 edge(s)

Parent: [Streaming JsonReader](streaming-jsonreader.md)

## Units (14)

<a id="u-ac716c6aef50"></a>
### `JsonReader.java-boolean-and-null-consumers`

`public boolean nextBoolean() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1037-L1054][f1]

nextBoolean consumes PEEKED_TRUE/PEEKED_FALSE, returning the value and advancing the path index; nextNull consumes PEEKED_NULL similarly.

Any other token throws unexpectedTokenError for "a boolean" or "null" respectively.

<a id="u-9c039e931bb5"></a>
### `JsonReader.java-error-factories`

`private MalformedJsonException syntaxError(String message) throws MalformedJsonException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1943-L1946][f1]

syntaxError throws MalformedJsonException with the message, location, and a troubleshooting URL.

unexpectedTokenError peeks the actual token and returns (does not throw) an IllegalStateException whose message names the expected token, the actual one, the location, and a URL chosen by whether the actual token is NULL (adapter-not-null-safe) — callers throw it.

<a id="u-a19533384685"></a>
### `MalformedJsonException.java-malformedjsonexception`

`class MalformedJsonException extends IOException` · [gson/src/main/java/com/google/gson/stream/MalformedJsonException.java:L26-L27][f2]

Checked exception extending IOException, thrown by the JSON reader (not this writer) on malformed JSON; some syntax errors can be tolerated under Strictness.LENIENT.

Three constructors build it from a message, a message plus cause, or a cause alone, all delegating to the IOException super constructors; serialVersionUID is 1.

<a id="u-0fb0249b3a63"></a>
### `JsonReader.nextDouble`

`public double nextDouble() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1084-L1131][f1]

Consumes the next token as a double.

PEEKED_LONG converts directly; numbers, quoted, and unquoted strings are materialized into peekedString and the state set to PEEKED_BUFFERED; other tokens throw unexpectedTokenError. The string is parsed with Double.parseDouble, rethrowing NumberFormatException with location context and the original as cause. If the result is NaN or infinite and strictness is not LENIENT, throws syntaxError. On success clears peekedString, advances the path index, and records a promoted name.

<a id="u-d167b245e9d0"></a>
### `JsonReader.nextInt`

`public int nextInt() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1414-L1474][f1]

Consumes the next token as an int, mirroring nextLong: PEEKED_LONG must fit exactly in an int (else NumberFormatException with location); PEEKED_NUMBER is buffered; quoted/unquoted strings are ASCII-validated and first tried with Integer.parseInt, falling back to Double.parseDouble with an exact-cast check (NumberFormatException on parse failure or precision loss); other tokens throw unexpectedTokenError.

Advances the path index and records a promoted name on success.

<a id="u-62a6af2e4b35"></a>
### `JsonReader.nextLong`

`public long nextLong() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1142-L1200][f1]

Consumes the next token as a long.

PEEKED_LONG returns the cached value directly; PEEKED_NUMBER is buffered as a string; quoted/unquoted strings are read (unquoted strings and quoted values are validated ASCII) and first tried with Long.parseLong, falling through to double parsing on NumberFormatException; other tokens throw unexpectedTokenError. The fallback parses with Double.parseDouble (rethrowing NumberFormatException with location and cause on failure) and requires the cast back to long to be exact, else NumberFormatException. On success clears peekedString, advances the path index, and records a promoted name.

<a id="u-34790b43ed59"></a>
### `JsonReader.nextName`

`public String nextName() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L958-L980][f1]

Consumes the next property name, dispatching on the peeked code to nextUnquotedValue or nextQuotedValue with the matching quote; any other token throws unexpectedTokenError.

Records the result in pathNames at the top of the stack and clears the peek cache.

<a id="u-5d122bcf2105"></a>
### `JsonReader.nextQuotedValue`

`private String nextQuotedValue(char quote) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1209-L1263][f1]

Reads a quoted string up to the closing quote, decoding escapes via readEscapeCharacter and tracking newlines for location reporting.

In STRICT mode any unescaped control character (below 0x20) throws syntaxError. Builds directly from the buffer when no escapes occurred, otherwise lazily allocates a StringBuilder; end of input before the closing quote throws "Unterminated string". The result is passed through validateString.

<a id="u-b01b055cf02f"></a>
### `JsonReader.nextString`

`public String nextString() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L996-L1030][f1]

Consumes the next token as a string, accepting quoted/unquoted strings, a buffered string, a long (via Long.toString), or a number literal sliced from the buffer; anything else throws unexpectedTokenError.

Advances the parent path index, clears the peek cache, and records a promoted name if applicable.

<a id="u-3d5641cab95c"></a>
### `JsonReader.nextUnquotedValue`

`@SuppressWarnings("fallthrough") private String nextUnquotedValue() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1286-L1343][f1]

Reads an unquoted literal up to the first non-literal character (same character set as isLiteral, with '/', '\\', ';', '#', '=' additionally requiring leniency when encountered).

Tries to keep the whole literal in the buffer; if it exceeds the buffer, switches to a StringBuilder and refills incrementally. Consumed only in lenient contexts since doPeek checks leniency before classifying unquoted values.

<a id="u-d3cbfd4ae24f"></a>
### `JsonReader.peek`

`public JsonToken peek() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L551-L588][f1]

Returns the JsonToken of the next token without consuming it, mapping the internal peeked code to the public token; buffered strings and quoted/unquoted forms map to STRING, longs and numbers to NUMBER, EOF to END_DOCUMENT.

Uses the cached peeked value if present, otherwise runs doPeek; an unknown code raises AssertionError.

<a id="u-8e7b6659bda7"></a>
### `JsonReader.readEscapeCharacter`

`@SuppressWarnings("fallthrough") private char readEscapeCharacter() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1872-L1937][f1]

Decodes the escape following a backslash: named escapes t, b, n, r, f map to control chars; 'u' requires four hex digits (malformed or short input throws syntaxError) and returns the code unit; '\n' as an escape is rejected in STRICT mode and otherwise counts a new line; '\'' is rejected in STRICT mode; '"', '\\', '/' return themselves; anything else throws "Invalid escape sequence".

Unterminated input throws "Unterminated escape sequence".

<a id="u-4411014b0d44"></a>
### `JsonReader.recordPromotedName`

`private void recordPromotedName(String name)` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L983-L988][f1]

After a name promoted to a value is consumed, records it in pathNames and clears the promotedName flag; a no-op when no promotion is pending.

<a id="u-d34335f3ccb8"></a>
### `JsonReader.validateString`

`@CanIgnoreReturnValue private String validateString(String value) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1266-L1283][f1]

In STRICT mode rejects strings containing unpaired UTF-16 surrogates with syntaxError, allowing properly paired high+low sequences; in other modes returns the value unchanged.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonReader.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/MalformedJsonException.java
