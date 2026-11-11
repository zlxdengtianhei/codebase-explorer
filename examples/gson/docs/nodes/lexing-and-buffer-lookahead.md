# Lexing and buffer lookahead

**Capability.** Provides the low-level character machinery: buffer filling, whitespace/comment skipping, literal classification, and the core one-token peek.

Come here for how raw characters become peeked token codes: doPeek, fillBuffer, nextNonWhitespace, literal scanning, and leniency checks. These units are the shared substrate the consumption and structural layers call into.

**Depends on.**

- [Token consumption and value decoding](token-consumption-and-value-decoding.md) · graph-confirmed · 9 edge(s) · Value decoding builds on the lexer's buffer filling and token peeking machinery.

**Depended on by.**

- [JsonReader public API and docs](jsonreader-public-api-and-docs.md) · graph-confirmed · 1 edge(s)
- [Structural navigation and skipping](structural-navigation-and-skipping.md) · graph-confirmed · 8 edge(s)
- [Token consumption and value decoding](token-consumption-and-value-decoding.md) · graph-confirmed · 14 edge(s)

Parent: [Streaming JsonReader](streaming-jsonreader.md)

## Units (9)

<a id="u-6ceb8f05b17a"></a>
### `JsonReader.java-comment-scanning-helpers`

`private void skipToEndOfLine() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1739-L1750][f1]

skipToEndOfLine advances until '\n' (updating line tracking) or '\r', relying on the caller to treat a following '\n' as whitespace.

skipTo searches for a non-newline-containing delimiter, refilling as needed, updating line tracking on newlines, and returning false if input ends first.

<a id="u-d1a160a67c89"></a>
### `JsonReader.checkLenient`

`private void checkLenient() throws MalformedJsonException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1728-L1733][f1]

Throws MalformedJsonException (with a troubleshooting URL) unless the strictness is LENIENT; used at every leniency-only construct in the parser.

<a id="u-cbdf14e282c8"></a>
### `JsonReader.consumeNonExecutePrefix`

`private void consumeNonExecutePrefix() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1963-L1984][f1]

In lenient mode, consumes the non-execute prefix ")]}'\n" if present: skips leading whitespace (pushing the character back), returns early if fewer than 5 chars remain or the buffer does not match the exact sequence, otherwise advances pos by 5.

<a id="u-3b54c0cc7f1f"></a>
### `JsonReader.doPeek`

`@SuppressWarnings("fallthrough") int doPeek() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L590-L756][f1]

Core one-token lookahead that classifies the next input based on the top of the scope stack and caches the result in peeked.

Per scope: EMPTY_ARRAY promotes to NONEMPTY_ARRAY; NONEMPTY_ARRAY requires ']', ';', or ',' (else "Unterminated array"), with ';' requiring leniency; object scopes promote to DANGLING_NAME, and in NONEMPTY_OBJECT first require '}', ';', or ',' (else "Unterminated object"), then read a name: '"' gives a double-quoted name, '\'' a single-quoted name (lenient only), '}' ends the object only for EMPTY_OBJECT (else "Expected name"), anything else is an unquoted name (lenient, must pass isLiteral). DANGLING_NAME requires ':' or, leniently, '=' (optionally followed by '>'), else "Expected ':'". EMPTY_DOCUMENT consumes the non-execute prefix only in lenient mode; NONEMPTY_DOCUMENT returns EOF at end of input, otherwise requires leniency for a second top-level value; CLOSED throws IllegalStateException. Then the value character is classified: ']' in EMPTY_ARRAY ends the array; ';'/',' in array scopes yield a lenient PEEKED_NULL (pushed back), otherwise "Unexpected value"; '\'' is a lenient single-quoted string; '"' double-quoted; '['/'{' begin tokens; otherwise the character is pushed back and peekKeyword, then peekNumber, then isLiteral+checkLenient (unquoted, lenient only) decide, with "Expected value" if the character is not a literal starter.

<a id="u-4016252b3ee8"></a>
### `JsonReader.fillBuffer`

`private boolean fillBuffer(int minimum) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1604-L1632][f1]

Compacts the buffer (shifting remaining chars to index 0, adjusting lineStart and bufferStart) and reads from the underlying Reader until at least 'minimum' chars are available, returning true, or input is exhausted, returning false.

On the very first read it consumes a UTF-8 BOM (\ufeff) if present, bumping pos, lineStart, and the effective minimum.

<a id="u-8a8870e0318f"></a>
### `JsonReader.isLiteral`

`@SuppressWarnings("fallthrough") private boolean isLiteral(char c) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L927-L951][f1]

Classifies a character as a literal character: '/', '\\', ';', '#', '=' are non-literal and additionally require leniency (throwing otherwise); structural characters, colon, comma, and whitespace are non-literal without a leniency check; everything else is a literal.

<a id="u-69e493fd77d3"></a>
### `JsonReader.nextNonWhitespace`

`private int nextNonWhitespace(boolean throwOnEof) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1639-L1726][f1]

Returns the next non-whitespace, non-comment character, positioned so the caller can push it back by decrementing pos; whitespace (space, \r, tab) is skipped and newlines update line/lineStart tracking.

For '/': if input ends right after the '/', it tries to load more and returns '/' as data only when nothing more can be loaded; otherwise checkLenient() runs before the comment/data distinction, so in non-lenient mode any '/' with following input throws MalformedJsonException even if it does not start a comment. In lenient mode, '/*' skips to '*/' (unterminated throws "Unterminated comment"), '//' skips to end of line, and any other following character returns '/' as data. '#' starts a lenient-only end-of-line comment. At end of input, throws EOFException with location when throwOnEof is true, otherwise returns -1.

<a id="u-ad2aa37646a0"></a>
### `JsonReader.peekKeyword`

`private int peekKeyword() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L758-L813][f1]

Matches the literals true/false/null (case-insensitively unless STRICT, where only lowercase matches) starting from the first character; returns PEEKED_NONE if the buffer runs out, any character mismatches, or the keyword is followed by another literal character (e.g. 'trues').

On success advances pos by the keyword length and caches PEEKED_TRUE/FALSE/NULL.

<a id="u-23b6c480859e"></a>
### `JsonReader.peekNumber`

`private int peekNumber() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L815-L925][f1]

Scans a numeric literal with a small state machine, accumulating the integer part into a negative long.

Returns PEEKED_NONE on any syntax deviation (misplaced sign/plus/'e'/'.', a non-literal terminator is fine but a literal terminator is not, leading zero after a digit, or a literal longer than the buffer). If the literal is a pure integer that fits in a long and is not -0 or Long.MIN_VALUE-as-positive, it caches peekedLong and returns PEEKED_LONG; otherwise, if it ends in a digit/fraction-digit/exponent-digit state, it caches peekedNumberLength and returns PEEKED_NUMBER; otherwise PEEKED_NONE.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonReader.java
