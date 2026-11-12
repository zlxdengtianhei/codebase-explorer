# JSON token scanning

**Capability.** Scans JSON input for tokens, literals, numbers, comments, escapes, and malformed-input errors.

Use for low-level JsonReader lookahead and scanning. Units show buffer refill, escape decoding, comment skipping, keyword/number lookahead, and error creation.

**Depends on.**

- [Reflective adapter support](reflective-adapter-support.md) · graph-only · 1 edge(s)

**Depended on by.**

- [JSON structure navigation](json-structure-navigation.md) · graph-confirmed · 10 edge(s) · JSON structure navigation uses token scanning to consume structural tokens and skip nested values.
- [JSON value consumption](json-value-consumption.md) · graph-confirmed · 16 edge(s) · JSON value consumption uses token scanning to parse scalar values, strings, and property names.
- [Streaming JSON reader core](streaming-json-reader-core.md) · graph-confirmed · 3 edge(s)

Parent: [Streaming JSON reader internals](streaming-json-reader-internals.md)

## Units (12)

<a id="u-b6d127686d1f"></a>
### `JsonReader.java-buffer-refill`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1598-L1604][f1]

Buffer refill.

It compacts unread characters, adjusts line and absolute offsets, and reads from the underlying Reader until at least the requested minimum is available or EOF is reached. On the first read it consumes a leading BOM and adjusts the minimum. It returns true when enough characters are buffered, false on exhaustion.

<a id="u-c6465b47476c"></a>
### `JsonReader.java-delimiter-search`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1750-L1755][f1]

Delimiter search.

It scans for the requested string, updating line tracking on newlines, and returns true when found or false at EOF; the search string is assumed not to contain a newline.

<a id="u-79d7e38fa69b"></a>
### `JsonReader.java-escape-sequence-decoder`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1863-L1872][f1]

Escape-sequence decoder.

It reads the character after a backslash and decodes Unicode \uXXXX escapes and the standard two-character escapes. EOF or a short/invalid Unicode escape is a syntax error. In STRICT mode an escaped newline or escaped single quote is a syntax error; otherwise the newline updates line tracking. Any other escape is a syntax error.

<a id="u-c03982b675a7"></a>
### `JsonReader.java-line-comment-skipper`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1733-L1739][f1]

Line-comment skipper.

It advances until a newline or carriage return; a newline increments the line number and resets the line start, while a carriage return stops without consuming a following newline.

<a id="u-014db7eff845"></a>
### `JsonReader.java-malformed-json-error-factory`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1937-L1943][f1]

Malformed-JSON error factory.

It throws MalformedJsonException with the supplied message, current location, and a troubleshooting URL.

<a id="u-a607a6b5e686"></a>
### `JsonReader.java-next-non-whitespace-reader`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1632-L1639][f1]

Next non-whitespace/comment character reader.

It skips spaces, tabs, carriage returns, and newlines, updating line tracking. For '/', it first ensures a following character is available; if none is available it returns '/'. With following input it always calls the lenient check before deciding whether the slash starts a comment, so in non-lenient mode any such '/' throws MalformedJsonException even when it is not a comment. In lenient mode '/*' skips a C-style comment (unterminated is a syntax error), '//' skips a line comment, and other following characters return '/'. '#' requires lenient and skips a line comment. EOF throws EOFException when requested, otherwise returns -1.

<a id="u-6932f1a3901f"></a>
### `JsonReader.java-non-execute-prefix-consumer`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1960-L1963][f1]

Non-execute-prefix consumer.

It skips leading whitespace, then checks for the five-character prefix; if fewer than five characters are available or the prefix does not match, it leaves the position unchanged; on a match it advances past the prefix.

<a id="u-d1a160a67c89"></a>
### `JsonReader.checkLenient`

`private void checkLenient() throws MalformedJsonException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1728-L1733][f1]

Lenient-mode guard.

It throws a malformed-JSON syntax error unless the reader's strictness is LENIENT.

<a id="u-3b54c0cc7f1f"></a>
### `JsonReader.doPeek`

`@SuppressWarnings("fallthrough") int doPeek() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L590-L756][f1]

Core lookahead state machine that determines the next token and advances the scope stack and input position as needed.

It first handles the current scope:
- empty array: marks it nonempty and continues to value parsing.
- nonempty array: reads the next non-whitespace; ']' yields END_ARRAY; ';' requires lenient then acts like ','; ',' continues; anything else is an unterminated-array syntax error.
- empty or nonempty object: marks dangling-name; for nonempty object, '}' yields END_OBJECT, ';' requires lenient then acts like ',', ',' continues, anything else is an unterminated-object syntax error; then reads a name: double quote yields double-quoted name, single quote requires lenient, '}' yields END_OBJECT only for an empty object else expected-name error, and other characters require lenient and a literal start for an unquoted name else expected-name error.
- dangling name: marks nonempty object; ':' continues; '=' requires lenient and optionally consumes '>'; anything else is expected-colon error.
- empty document: in lenient mode consumes the non-execute prefix, then marks nonempty document.
- nonempty document: reads non-whitespace without EOF throwing; EOF yields END_DOCUMENT; otherwise requires lenient and pushes back the character.
- closed: throws IllegalStateException; unknown scope: AssertionError.
It then reads a value character: ']' in an empty array yields END_ARRAY; ']' in a nonempty array at value position, ';', or ',' in an array requires lenient, pushes back, and yields NULL; those separators outside an array are an unexpected-value error. Single quote requires lenient and yields single-quoted string; double quote yields double-quoted string; '[' yields BEGIN_ARRAY; '{' yields BEGIN_OBJECT; other characters are pushed back. It then tries keyword and number recognition; if neither matches and the character is not a literal start it is an expected-value error; otherwise it requires lenient and yields an unquoted string.

<a id="u-8a8870e0318f"></a>
### `JsonReader.isLiteral`

`@SuppressWarnings("fallthrough") private boolean isLiteral(char c) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L927-L951][f1]

Literal-character test used by token scanning.

Structural characters and whitespace return false. The characters '/', backslash, ';', '#', and '=' first require lenient mode and then also return false, so in non-lenient mode they throw MalformedJsonException instead of being treated as data.

<a id="u-ad2aa37646a0"></a>
### `JsonReader.peekKeyword`

`private int peekKeyword() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L758-L813][f1]

Keyword lookahead for true, false, and null.

It selects a keyword by first character, allows uppercase letters except in STRICT mode, fills the buffer as needed, and rejects a match when the following character is still a literal. A complete match advances the position and sets the peeked keyword; otherwise it reports no match.

<a id="u-23b6c480859e"></a>
### `JsonReader.peekNumber`

`private int peekNumber() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L815-L925][f1]

Number lookahead state machine.

It scans sign, digits, decimal point, and exponent, rejecting leading zeroes and invalid transitions. A complete integer that fits in long, is not negative zero, and is not positive Long.MIN_VALUE becomes a long peek; other complete numeric forms become a number peek with a length; incomplete or invalid forms report no match. Overlong numbers that exceed the buffer report no match.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonReader.java
