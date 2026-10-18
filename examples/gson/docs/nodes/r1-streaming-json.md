# Streaming JSON Reading

**Capability.** Token-level JSON reading: JsonReader is the streaming RFC 8259 tokenizer with strictness and nesting control; JsonTreeReader reimplements the same contract over an in-memory JsonElement tree; JsonParser and JsonStreamParser are the static and iterator facades built on them.

Use this subtree for parsing behavior: tokenization, leniency rules, error locations/paths, and how tree-based and stream-based reading share one reader contract.

**Depends on.**

- [Internal Support Utilities](r1-internal-support.md) · model-inferred · 0 edge(s)
- [JSON DOM Tree](r2-dom-tree.md) · graph-only · 6 edge(s)
- [Internal Utilities and Data Structures](r2-infrastructure.md) · graph-only · 4 edge(s)

**Depended on by.**

- [Gson Facade and Conversion API](r1-facade-api.md) · graph-confirmed · 6 edge(s) · The facade creates and configures JsonReader instances that parsing facades and conversions read through.

Parent: [Gson JSON Binding Library](r1-gson-root.md)

## Units (69)

<a id="u-92ec22311967"></a>
### `JsonReader`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L212-L323][f1]

A streaming RFC 8259 JSON token reader over a java.io.Reader, with configurable strictness and nesting limit.

State lives in a 1024-char buffer (pos/limit), a peeked-token slot (`peeked`) with side data (`peekedLong`, `peekedNumberLength`, `peekedString`), a scope stack starting as EMPTY_DOCUMENT, and parallel pathNames/pathIndices arrays for JSON-path reporting. Folded members: the constructor rejects a null Reader; `setLenient(true|false)` maps to Strictness.LENIENT|LEGACY_STRICT; `setStrictness` rejects null; `setNestingLimit` throws IllegalArgumentException for negative limits (default 255); `isLenient`/`getStrictness`/`getNestingLimit` are plain getters; `hasNext` peeks and returns false only for END_OBJECT, END_ARRAY or EOF; `toString` is the class name plus the location string; `getPreviousPath` delegates to the private path builder with usePreviousPath=true; `getCharacterOffset` returns bufferStart+pos. The initializer pushes EMPTY_DOCUMENT onto the stack. Instances are single-use and not thread safe. Most methods call `doPeek` when nothing is peeked, then consume or reject the peeked token.

calls: [JsonReader.doPeek](r1-streaming-json.md#u-3b54c0cc7f1f)

**Uncertainties.**

- Exact nesting-limit enforcement point is in push(); the interaction between setNestingLimit and stack growth beyond the initial 32 slots is verified only through push()'s source.

<a id="u-599a8f46d311"></a>
### `JsonReader.beginArray`

`public void beginArray() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L467-L479][f1]

Consumes BEGIN_ARRAY, pushing EMPTY_ARRAY onto the scope stack and resetting the array index.

If nothing is peeked it first calls doPeek(); if the peeked token is not PEEKED_BEGIN_ARRAY it throws IllegalStateException via unexpectedTokenError without consuming.

calls: [JsonReader.doPeek](r1-streaming-json.md#u-3b54c0cc7f1f)

<a id="u-c4b0d7bdb69d"></a>
### `JsonReader.beginObject`

`public void beginObject() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L507-L518][f1]

Consumes BEGIN_OBJECT by pushing EMPTY_OBJECT onto the scope stack.

Peeks via doPeek when necessary; any token other than PEEKED_BEGIN_OBJECT causes IllegalStateException from unexpectedTokenError, leaving state unchanged.

calls: [JsonReader.doPeek](r1-streaming-json.md#u-3b54c0cc7f1f)

<a id="u-d1a160a67c89"></a>
### `JsonReader.checkLenient`

`private void checkLenient() throws MalformedJsonException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1728-L1733][f1]

Throws MalformedJsonException (via syntaxError, advising Strictness.LENIENT) whenever strictness is anything other than LENIENT; returns silently in lenient mode.

calls: [JsonReader.syntaxError](r1-streaming-json.md#u-35b40f9e0a3f)

<a id="u-d2a060c9f8fd"></a>
### `JsonReader.close`

`@Override public void close() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1482-L1488][f1]

Marks the reader CLOSED (stack reset to a single CLOSED scope, peek cleared) and closes the underlying Reader.

Subsequent reads typically hit the CLOSED scope and throw IllegalStateException.

<a id="u-cbdf14e282c8"></a>
### `JsonReader.consumeNonExecutePrefix`

`private void consumeNonExecutePrefix() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1963-L1984][f1]

Under lenient parsing, consumes the anti-XSS prefix ")]}'\n" at the start of a stream.

It reads and pushes back the first non-whitespace character, returns quietly if fewer than five characters are available or the buffer does not match the exact prefix, and otherwise advances pos by five. Any other content is left untouched for normal parsing.

<a id="u-3b54c0cc7f1f"></a>
### `JsonReader.doPeek`

`@SuppressWarnings("fallthrough") int doPeek() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L590-L756][f1]

Core tokenizer: determines the peeked-token code from the current scope and the next non-whitespace character.

Per scope: EMPTY_ARRAY flips to NONEMPTY_ARRAY; NONEMPTY_ARRAY requires a separator, where ']' returns PEEKED_END_ARRAY, a lenient ';' (falling through) or ',' continues, anything else is a syntax error; EMPTY/NONEMPTY_OBJECT flips to DANGLING_NAME, requires a ','/lenient ';' before the next name in a nonempty object (with '}' returning PEEKED_END_OBJECT), then dispatches on the name opener: '"' double-quoted, lenient '\'' single-quoted, '}' only legal for EMPTY_OBJECT (else 'Expected name'), else lenient unquoted name when isLiteral; DANGLING_NAME becomes NONEMPTY_OBJECT and requires ':' or a lenient '=' optionally followed by '>'; EMPTY_DOCUMENT consumes the non-execute prefix only under LENIENT and becomes NONEMPTY_DOCUMENT; NONEMPTY_DOCUMENT returns PEEKED_EOF at end of input, otherwise requires leniency to continue (multiple top-level values); CLOSED throws IllegalStateException. The final character switch: ']' yields PEEKED_END_ARRAY only when peekStack is EMPTY_ARRAY; otherwise it falls through to the ';'/',' case, which inside an array yields a lenient PEEKED_NULL placeholder (for ",]" or ';'), or throws 'Unexpected value' elsewhere. '\''/'"'/'['/'{' dispatch directly; any other character is pushed back and classified by peekKeyword, then peekNumber, then as a lenient unquoted value if isLiteral, else 'Expected value'.

**Notes.**

- failure: Separator mismatches, missing names/colons and non-literal value starts throw MalformedJsonException via syntaxError before any token is produced.

calls: [JsonReader.nextNonWhitespace](r1-streaming-json.md#u-69e493fd77d3), [JsonReader.peekKeyword](r1-streaming-json.md#u-ad2aa37646a0), [JsonReader.peekNumber](r1-streaming-json.md#u-23b6c480859e), [JsonReader.consumeNonExecutePrefix](r1-streaming-json.md#u-cbdf14e282c8)

**Uncertainties.**

- The ';'-separator path in NONEMPTY_ARRAY marks the character consumed by nextNonWhitespace but relies on the later value scan to re-detect it; behavior of consecutive ';' separators follows the final switch's lenient-null path.

<a id="u-c030bc85d2a5"></a>
### `JsonReader.endArray`

`public void endArray() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L487-L499][f1]

Consumes END_ARRAY: pops the scope stack and increments the path index of the enclosing scope.

Requires the peeked token to be PEEKED_END_ARRAY (peeking first via doPeek if needed); otherwise throws IllegalStateException via unexpectedTokenError.

calls: [JsonReader.doPeek](r1-streaming-json.md#u-3b54c0cc7f1f)

<a id="u-896228d10b3f"></a>
### `JsonReader.endObject`

`public void endObject() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L526-L539][f1]

Consumes END_OBJECT: pops the scope, nulls the freed path name for garbage collection, and increments the enclosing scope's path index.

Non-END_OBJECT peeked tokens raise IllegalStateException via unexpectedTokenError.

calls: [JsonReader.doPeek](r1-streaming-json.md#u-3b54c0cc7f1f)

<a id="u-4016252b3ee8"></a>
### `JsonReader.fillBuffer`

`private boolean fillBuffer(int minimum) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1604-L1632][f1]

Compacts the buffer so at least `minimum` characters are available past pos, returning true on success and false at end of input.

It folds pos into bufferStart and lineStart, copies any unconsumed suffix to the front, then loops on in.read; the first read of the stream skips a leading byte-order mark (U+FEFF) by advancing pos, lineStart and the minimum. False is returned once the reader yields -1 before the minimum is met.

<a id="u-dca8da0d3ced"></a>
### `JsonReader.getPath`

`private String getPath(boolean usePreviousPath)` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1785-L1816][f1]

Builds the dot-notation JSONPath from the scope stack.

Array scopes append '[index]'; with usePreviousPath and a nonzero index at the innermost level, the index is decremented to point at the last consumed element. Object scopes append '.name' from pathNames (just a '.' when null). Document and CLOSED scopes add nothing; an unknown scope value raises AssertionError. The public getPath() delegates with usePreviousPath=false (pointing at the next element), and getPreviousPath() delegates with true.

<a id="u-8a8870e0318f"></a>
### `JsonReader.isLiteral`

`@SuppressWarnings("fallthrough") private boolean isLiteral(char c) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L927-L951][f1]

Reports whether a character can be part of an unquoted literal.

Structural characters, whitespace and line breaks are not literal; '/', '\', ';', '#', '=' first pass through checkLenient, so under STRICT or LEGACY_STRICT an unquoted literal containing them terminates the literal there instead of throwing here, while the character itself still returns false.

calls: [JsonReader.checkLenient](r1-streaming-json.md#u-d1a160a67c89)

<a id="u-5532d9fa4924"></a>
### `JsonReader.locationString`

`String locationString()` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1779-L1783][f1]

Builds a ' at line L column C path P' suffix from 1-based line/column arithmetic (lineNumber+1, pos-lineStart+1) and the current JSON path; used in all error messages.

<a id="u-06be89fb5948"></a>
### `JsonReader.nextBoolean`

`public boolean nextBoolean() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1037-L1054][f1]

Consumes PEEKED_TRUE or PEEKED_FALSE and returns the boolean, clearing the peek slot and incrementing the path index; other tokens raise IllegalStateException via unexpectedTokenError.

<a id="u-0fb0249b3a63"></a>
### `JsonReader.nextDouble`

`public double nextDouble() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1084-L1131][f1]

Consumes the next token as a double, coercing strings and number literals through Double.parseDouble.

The PEEKED_LONG case converts peekedLong directly and returns early without calling recordPromotedName. PEEKED_NUMBER and quoted/unquoted cases capture the literal into peekedString; PEEKED_BUFFERED reuses it. After parsing: a NumberFormatException is rethrown with a message including the literal and location, chaining the cause; under any strictness other than LENIENT, NaN or infinite results throw MalformedJsonException. On success the literal is cleared, the path index incremented, and recordPromotedName(literal) called (a no-op unless the name was promoted).

calls: [JsonReader.nextQuotedValue](r1-streaming-json.md#u-5d122bcf2105), [JsonReader.nextUnquotedValue](r1-streaming-json.md#u-3d5641cab95c)

<a id="u-d167b245e9d0"></a>
### `JsonReader.nextInt`

`public int nextInt() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1414-L1474][f1]

Consumes the next token as an int with exactness checks.

PEEKED_LONG narrows peekedLong to int and throws NumberFormatException with location context if precision was lost (this early return skips recordPromotedName). PEEKED_NUMBER captures the literal; quoted/unquoted literals are ASCII-validated and parsed with Integer.parseInt, returning on success (also skipping recordPromotedName) or falling through on NumberFormatException. The fallback parses as double: parse failure rethrows NumberFormatException with cause chained; a lossy cast to int throws NumberFormatException. Success clears peekedString, increments the path index, and calls recordPromotedName.

calls: [JsonReader.validateAscii](r1-streaming-json.md#u-b2f12d026de5)

<a id="u-62a6af2e4b35"></a>
### `JsonReader.nextLong`

`public long nextLong() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1142-L1200][f1]

Consumes the next token as a long, preferring exact parsing.

PEEKED_LONG returns peekedLong directly, skipping recordPromotedName. PEEKED_NUMBER captures the literal; quoted/unquoted literals are validated as ASCII and parsed with Long.parseLong, and on success return immediately (also skipping recordPromotedName here); on NumberFormatException the code falls through. The fallback parses the literal as a double: parse failure rethrows NumberFormatException with location context and chained cause; if casting to long loses precision ('result != asDouble') it throws NumberFormatException. Success clears peekedString, advances the path index, and calls recordPromotedName.

**Notes.**

- failure: Literals that fit a double but not a long exactly (e.g. '1.5' or huge values) throw NumberFormatException rather than truncating.
- condition: Quoted and unquoted literals passed to Long.parseLong must be all-ASCII (validateAscii) or MalformedJsonException is thrown first.

<a id="u-34790b43ed59"></a>
### `JsonReader.nextName`

`public String nextName() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L958-L980][f1]

Consumes and returns the next property name.

Accepts PEEKED_UNQUOTED_NAME (via nextUnquotedValue), PEEKED_SINGLE_QUOTED_NAME (nextQuotedValue with '\''), or PEEKED_DOUBLE_QUOTED_NAME (nextQuotedValue with '"'); any other peeked token throws IllegalStateException from unexpectedTokenError. On success it clears the peek slot and records the name in pathNames at the current stack level.

calls: [JsonReader.nextQuotedValue](r1-streaming-json.md#u-5d122bcf2105), [JsonReader.nextUnquotedValue](r1-streaming-json.md#u-3d5641cab95c)

<a id="u-69e493fd77d3"></a>
### `JsonReader.nextNonWhitespace`

`private int nextNonWhitespace(boolean throwOnEof) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1639-L1726][f1]

Returns the next non-whitespace, non-comment character, leaving it consumed at buffer[pos-1] so callers can push it back with pos--.

Newlines update line tracking; space, CR and TAB are skipped. On '/': if the buffer boundary splits the slash the character is pushed back for a refill; then checkLenient() is called before the peek switch, so in STRICT or LEGACY_STRICT any '/' not beginning an accepted comment throws MalformedJsonException rather than being returned — a lone '/' is returned only in LENIENT mode. '*' starts a C-style comment skipped via skipTo (unterminated comments throw); '/' starts a line comment skipped via skipToEndOfLine; otherwise the '/' itself is returned. '#' begins a lenient line comment. On EOF, throws EOFException with location when throwOnEof is true, otherwise returns -1.

calls: [JsonReader.checkLenient](r1-streaming-json.md#u-d1a160a67c89), [JsonReader.skipTo](r1-streaming-json.md#u-3fbdb57a1e36), [JsonReader.skipToEndOfLine](r1-streaming-json.md#u-7903207168d8)

<a id="u-0ac036678021"></a>
### `JsonReader.nextNull`

`public void nextNull() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1061-L1072][f1]

Consumes a literal null, returning void.

Only PEEKED_NULL is accepted (including the lenient placeholder produced for empty array slots); anything else throws IllegalStateException via unexpectedTokenError. Increments the path index on success.

<a id="u-5d122bcf2105"></a>
### `JsonReader.nextQuotedValue`

`private String nextQuotedValue(char quote) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1209-L1263][f1]

Reads a quoted string value or name up to the given quote character, unescaping as it goes; the opening quote is already consumed and the closing quote is consumed but not returned.

Under STRICT, unescaped control characters below 0x20 throw MalformedJsonException. A quote ends the value and the result is validated for unpaired surrogates via validateString; a backslash switches to StringBuilder accumulation plus readEscapeCharacter; newlines update line tracking; exhausting input before the closing quote throws 'Unterminated string'.

calls: [JsonReader.readEscapeCharacter](r1-streaming-json.md#u-8e7b6659bda7), [JsonReader.validateString](r1-streaming-json.md#u-d34335f3ccb8)

<a id="u-b01b055cf02f"></a>
### `JsonReader.nextString`

`public String nextString() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L996-L1030][f1]

Consumes the next token as a string, coercing numbers to their string form.

Unquoted/single-quoted/double-quoted values come from the corresponding scanners; PEEKED_BUFFERED returns and clears peekedString; PEEKED_LONG returns Long.toString(peekedLong) without touching recordPromotedName beyond its no-op path; PEEKED_NUMBER copies the literal from the buffer and advances pos. Any other token throws IllegalStateException. Always increments the current array index and calls recordPromotedName, which only records if the name was promoted.

**Notes.**

- contract: peekedString is set to null after a buffered read, so a second string read cannot reuse stale data.

<a id="u-3d5641cab95c"></a>
### `JsonReader.nextUnquotedValue`

`@SuppressWarnings("fallthrough") private String nextUnquotedValue() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1286-L1343][f1]

Scans an unquoted literal until a delimiter.

Characters '/', '\', ';', '#', '=' first pass checkLenient before terminating the scan, so under non-lenient strictness such a literal cannot contain them; structural characters and whitespace terminate without checkLenient. The buffer is refilled to capture the whole literal at once; values longer than the buffer fall back to StringBuilder accumulation. Returns the literal and advances pos past it.

calls: [JsonReader.checkLenient](r1-streaming-json.md#u-d1a160a67c89)

<a id="u-d3cbfd4ae24f"></a>
### `JsonReader.peek`

`public JsonToken peek() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L551-L588][f1]

Returns the next JsonToken without consuming it.

Peeks via doPeek when the slot is empty, then maps each internal PEEKED_* constant to its JsonToken; quoted/unquoted names map to NAME, quoted/unquoted/buffered map to STRING, LONG/NUMBER map to NUMBER, EOF maps to END_DOCUMENT. An unmapped constant raises AssertionError. The peeked token stays buffered for the next nextX call.

calls: [JsonReader.doPeek](r1-streaming-json.md#u-3b54c0cc7f1f)

<a id="u-ad2aa37646a0"></a>
### `JsonReader.peekKeyword`

`private int peekKeyword() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L758-L813][f1]

Matches true/false/null keywords at the buffer position.

Chooses the keyword by first character (t/T, f/F, n/N), returning PEEKED_NONE otherwise; uppercased spellings match unless strictness is STRICT. If the buffer runs out mid-match or a character mismatches, it returns PEEKED_NONE without consuming. A longer literal such as 'trues' does not match. On success it advances pos past the keyword, stores the peek code in the field, and returns it.

**Notes.**

- side_effect: On success both the buffer position and the peeked field are updated; on any mismatch neither changes.

<a id="u-23b6c480859e"></a>
### `JsonReader.peekNumber`

`private int peekNumber() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L815-L925][f1]

Scans a numeric literal through a small state machine and decides between PEEKED_LONG, PEEKED_NUMBER, or no number.

Handles a leading '-', 'e'/'E' exponents with optional +/-, and '.' after digits; any other shape returns PEEKED_NONE. A literal filling the whole 1024-char buffer is abandoned as PEEKED_NONE so it can be handled as an unquoted literal. Integer rules: a leading '0' prefix (possible octal) is rejected; -0 is not stored as a long; Long.MIN_VALUE is kept negative to avoid overflow. When the value fits in a long it stores peekedLong, advances pos by the literal length, and returns PEEKED_LONG; otherwise a digit-terminated or exponent/fraction-terminated literal stores peekedNumberLength and returns PEEKED_NUMBER; malformed endings return PEEKED_NONE.

**Notes.**

- side_effect: peekedLong or peekedNumberLength fields are written only when a number classification succeeds.

<a id="u-6e29514879a1"></a>
### `JsonReader.promoteNameToValue`

`@Override public void promoteNameToValue(JsonReader reader) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1995-L2020][f1]

Implements JsonReaderInternalAccess.promoteNameToValue via the static initializer: it lets a property name be read by value methods instead of nextName.

JsonTreeReader instances are delegated to their own override. Otherwise the next token is peeked; *_NAME codes are rewritten to the corresponding value code, reader.promotedName is set so recordPromotedName fixes the JSON path once the value is consumed, and any other token yields an IllegalStateException via unexpectedTokenError (thrown by the caller-side lambda wrapper).

calls: [JsonReader.doPeek](r1-streaming-json.md#u-3b54c0cc7f1f), [JsonReader.unexpectedTokenError](r1-streaming-json.md#u-96a70375a8c6)

**Uncertainties.**

- The static block delegates to JsonTreeReader.promoteNameToValue() for tree readers; that override's behavior is outside this file.

<a id="u-67b460aa2789"></a>
### `JsonReader.push`

`private void push(int newTop) throws MalformedJsonException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1584-L1598][f1]

Pushes a new scope onto the nesting stack after enforcement and growth.

If the current depth (stackSize - 1, excluding the document scope) is at or above nestingLimit it throws MalformedJsonException reporting the limit and location. When the stack arrays are full, stack, pathIndices and pathNames are all doubled via Arrays.copyOf before the push.

**Notes.**

- failure: The limit check uses stackSize - 1, so a limit of 0 still permits reading scalar top-level values but no arrays or objects.

<a id="u-8e7b6659bda7"></a>
### `JsonReader.readEscapeCharacter`

`@SuppressWarnings("fallthrough") private char readEscapeCharacter() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1872-L1937][f1]

Decodes the character(s) after a backslash.

'u' requires four hexadecimal digits (malformed digits throw with the offending text); t/b/n/r/f map to their control characters; a '\n' escape updates line tracking and is rejected in STRICT mode; '\'' is rejected in STRICT but allowed otherwise; '"', '\\' and '/' return themselves; end of input mid-escape throws 'Unterminated escape sequence'; any other character throws 'Invalid escape sequence'. All errors are MalformedJsonException via syntaxError.

<a id="u-4411014b0d44"></a>
### `JsonReader.recordPromotedName`

`private void recordPromotedName(String name)` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L983-L988][f1]

Records a property name that promoteNameToValue consumed as a value into pathNames, then clears the promotedName flag; does nothing when no promotion happened.

<a id="u-7153c19980d9"></a>
### `JsonReader.skipQuotedValue`

`private void skipQuotedValue(char quote) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1345-L1370][f1]

Discards a quoted value up to the given quote without building a string, consuming escapes via readEscapeCharacter and tracking newlines.

Reaching end of input before the closing quote throws 'Unterminated string'.

calls: [JsonReader.readEscapeCharacter](r1-streaming-json.md#u-8e7b6659bda7)

<a id="u-3fbdb57a1e36"></a>
### `JsonReader.skipTo`

`private boolean skipTo(String toFind) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1755-L1772][f1]

Searches the buffer for the literal string `toFind` (expected comment terminator, no newlines), refilling as needed.

Newlines encountered during the scan update line tracking. Returns true with pos at the match start when found; false when input is exhausted. The caller then skips past the terminator itself.

<a id="u-7903207168d8"></a>
### `JsonReader.skipToEndOfLine`

`private void skipToEndOfLine() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1739-L1750][f1]

Advances past characters until after a newline: '\n' updates line tracking and stops (having consumed it), '\r' stops leaving '\n' for the caller as whitespace.

Returns quietly at end of input.

<a id="u-64add9d78a58"></a>
### `JsonReader.skipUnquotedValue`

`@SuppressWarnings("fallthrough") private void skipUnquotedValue() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1372-L1403][f1]

Advances pos past an unquoted value until a delimiter.

'/', '\', ';', '#', '=' trigger checkLenient before terminating; other delimiters and whitespace terminate directly. Refills the buffer as needed and simply returns at end of input.

<a id="u-0f6dd79edc39"></a>
### `JsonReader.skipValue`

`public void skipValue() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1506-L1582][f1]

Skips the next value, recursing through nested arrays and objects using a local depth counter.

BEGIN_ARRAY/BEGIN_OBJECT push scopes and increment count; END_ARRAY/END_OBJECT pop and decrement, with END_OBJECT also clearing the path name when the skip is at depth 0; quoted/unquoted values and names are discarded by the scanners, with names at depth 0 recorded as '<skipped>' in pathNames; PEEKED_NUMBER advances pos by the literal length; PEEKED_EOF returns without consuming; other peeked codes need no work since the token was already consumed. The loop repeats while count > 0, so an opening delimiter causes the whole nested structure to be skipped. Afterwards the enclosing path index is incremented and recordPromotedName('<skipped>') applies only if a name was promoted.

calls: [JsonReader.skipQuotedValue](r1-streaming-json.md#u-7153c19980d9), [JsonReader.skipUnquotedValue](r1-streaming-json.md#u-64add9d78a58)

<a id="u-35b40f9e0a3f"></a>
### `JsonReader.syntaxError`

`private MalformedJsonException syntaxError(String message) throws MalformedJsonException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1943-L1946][f1]

Always throws a MalformedJsonException whose message appends the location string and a TroubleshootingGuide 'malformed-json' URL; declared to return so callers can use it as a throwing expression.

calls: [TroubleshootingGuide](r2-infrastructure.md#u-9bcd073a2728)

<a id="u-96a70375a8c6"></a>
### `JsonReader.unexpectedTokenError`

`private IllegalStateException unexpectedTokenError(String expected) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1948-L1960][f1]

Builds and returns (not throws) an IllegalStateException for a token mismatch: it calls peek() for the token name, appends the location, and links to TroubleshootingGuide under 'adapter-not-null-safe' when the token is NULL, otherwise 'unexpected-json-structure'.

Callers throw the returned instance.

calls: [JsonReader.peek](r1-streaming-json.md#u-d3cbfd4ae24f), [TroubleshootingGuide](r2-infrastructure.md#u-9bcd073a2728)

<a id="u-b2f12d026de5"></a>
### `JsonReader.validateAscii`

`private void validateAscii(String s) throws MalformedJsonException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1986-L1990][f1]

Throws MalformedJsonException when the given string contains non-ASCII characters, delegating the check to the static JsonTreeReader.isAllAscii helper; silent for pure-ASCII strings.

calls: [JsonTreeReader.isAllAscii](r1-streaming-json.md#u-120b1e545450)

<a id="u-d34335f3ccb8"></a>
### `JsonReader.validateString`

`@CanIgnoreReturnValue private String validateString(String value) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1266-L1283][f1]

Under STRICT only, rejects strings containing unpaired UTF-16 surrogates with MalformedJsonException; a valid high surrogate followed by a low surrogate is accepted, anything else throws.

Non-strict modes return the value unchanged.

<a id="u-ac3d9969ee05"></a>
### `gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:JsonTreeReader`

`class JsonTreeReader extends JsonReader` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L50-L76][f2]

A JsonReader that walks a JsonElement tree as if it came from a character stream, backed by an UNREADABLE_READER whose read/close throw AssertionError so character-level access is impossible.

State lives in a manual object stack (initially 32 slots) holding JsonElements and iterators, plus parallel pathNames/pathIndices arrays tracking the JSON path; stackSize may exceed nesting depth because each container pushes both itself and its iterator. Constructor pushes the root element. read::1408 and the first close::1539 override JsonReader methods by throwing UnsupportedOperationException, so this reader cannot be used for char-stream reading or base-class closing.

calls: [JsonReader](r1-streaming-json.md#u-92ec22311967)

<a id="u-62a3e3be6a37"></a>
### `JsonTreeReader.beginArray`

`@Override public void beginArray() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L81-L87][f2]

After expect(BEGIN_ARRAY), casts the stack top to JsonArray and pushes its iterator, resetting the path index at the new top to 0.

ClassCastException if the top is not a JsonArray is not caught here, though expect normally guarantees the token.

<a id="u-5a1a12d364f7"></a>
### `JsonTreeReader.beginObject`

`@Override public void beginObject() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L99-L104][f2]

After expect(BEGIN_OBJECT), casts the top to JsonObject and pushes its entry-set iterator; the object itself remains beneath the iterator on the stack.

calls: [jsonobject-class](r2-dom-tree.md#u-5c0ff73487b7)

<a id="u-8348c8baf1fc"></a>
### `JsonTreeReader.close`

`@Override public void close() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L324-L328][f2]

Replaces the stack with a single SENTINEL_CLOSED entry (stackSize 1); subsequent peek() calls throw IllegalStateException because of the sentinel.

No underlying stream exists to close.

<a id="u-8af6271f5663"></a>
### `JsonTreeReader.endArray`

`@Override public void endArray() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L89-L97][f2]

After expect(END_ARRAY), pops the exhausted iterator and then the array itself, and increments the parent scope's path index when a parent remains.

<a id="u-1cb6796d83a4"></a>
### `JsonTreeReader.endObject`

`@Override public void endObject() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L106-L115][f2]

After expect(END_OBJECT), clears the last path name (freeing it for garbage collection), pops the iterator and the object, and increments the parent scope's path index when a parent remains.

<a id="u-db82f0f2e853"></a>
### `JsonTreeReader.expect`

`private void expect(JsonToken expected) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L184-L189][f2]

Throws IllegalStateException("Expected X but was Y" plus the path) when the peeked token differs from the expected one.

<a id="u-ea0e189b3381"></a>
### `JsonTreeReader.getCharacterOffset`

`@Override public long getCharacterOffset()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L418-L421][f2]

Always returns -1L since there is no character stream.

<a id="u-9d3629730116"></a>
### `JsonTreeReader.getPath`

`private String getPath(boolean usePreviousPath)` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L382-L406][f2]

The private getPath(usePreviousPath) builds a $-rooted path: where the stack holds a JsonArray followed by an Iterator it appends the array index, decrementing it by one when usePreviousPath is set, the index is positive, and the iterator is one of the last two stack entries (peek may already have pushed the next element).

Where it holds a JsonObject followed by an Iterator it appends '.' plus the recorded name if non-null. Public getPath::12680 returns getPath(false) and getPreviousPath::12752 returns getPath(true).

<a id="u-88f3a25125c5"></a>
### `JsonTreeReader.hasNext`

`@Override public boolean hasNext() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L117-L123][f2]

Returns true unless the peeked token is END_OBJECT, END_ARRAY, or END_DOCUMENT.

<a id="u-120b1e545450"></a>
### `JsonTreeReader.isAllAscii`

`public static boolean isAllAscii(String s)` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L428-L435][f2]

Static helper returning true when every char of the string has code point at most 127, false on the first violation.

<a id="u-079b7b13ffd6"></a>
### `JsonTreeReader.locationString`

`private String locationString()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L423-L425][f2]

Formats ' at path ' plus the current path, appended by error messages.

<a id="u-f92936b65f6f"></a>
### `JsonTreeReader.nextBoolean`

`@Override public boolean nextBoolean() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L220-L228][f2]

Requires BOOLEAN, pops the primitive, returns getAsBoolean, and advances the path index.

<a id="u-e949c4e113cb"></a>
### `JsonTreeReader.nextDouble`

`@Override public double nextDouble() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L239-L261][f2]

Accepts NUMBER or STRING tokens, else IllegalStateException with path.

Converts the peeked primitive with getAsDouble; a NumberFormatException is rethrown via numberFormatException with path context. When the reader is not lenient, NaN or infinite results raise MalformedJsonException("JSON forbids NaN and infinities"). Then pops the value and advances the path index.

calls: [JsonReader](r1-streaming-json.md#u-92ec22311967)

<a id="u-62468b74494b"></a>
### `JsonTreeReader.nextInt`

`@Override public int nextInt() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L287-L309][f2]

Same structure as nextLong but converts with getAsInt and messages 'Expected an int'; ASCII validation applies to string tokens and NumberFormatException carries path context.

<a id="u-37a8966bfb18"></a>
### `JsonTreeReader.nextJsonElement`

`JsonElement nextJsonElement() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L311-L322][f2]

Package-private: returns the whole upcoming element.

Peeking NAME, END_ARRAY, END_OBJECT, or END_DOCUMENT raises IllegalStateException; otherwise it captures the stack top, calls skipValue to consume it, and returns the captured element.

<a id="u-e24233c4c0e4"></a>
### `JsonTreeReader.nextLong`

`@Override public long nextLong() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L263-L285][f2]

Accepts NUMBER or STRING, else IllegalStateException with path.

For string tokens the text must be all-ASCII or MalformedJsonException is thrown by validateAscii. getAsLong conversion failure becomes a NumberFormatException carrying path and cause. Pops the value and advances the path index.

<a id="u-6f8d5a4aadee"></a>
### `JsonTreeReader.nextName`

`private String nextName(boolean skipName) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L191-L199][f2]

The private nextName(skipName) requires a NAME token, takes the next entry from the iterator, records the name in pathNames (as "<skipped>" when skipping), pushes the entry's value onto the stack, and returns the key.

The public nextName::6415 delegates with skipName=false.

<a id="u-3151588a9d9d"></a>
### `JsonTreeReader.nextNull`

`@Override public void nextNull() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L230-L237][f2]

Requires NULL, pops the value, and advances the path index; returns void.

<a id="u-8e749cfd855b"></a>
### `JsonTreeReader.nextString`

`@Override public String nextString() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L206-L218][f2]

Accepts STRING or NUMBER tokens (anything else raises IllegalStateException with the path), pops the primitive and returns its getAsString, then increments the parent scope's path index.

<a id="u-eacc2c653e08"></a>
### `JsonTreeReader.numberFormatException`

`private NumberFormatException numberFormatException(String message, NumberFormatExcep…` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L445-L449][f2]

Builds a NumberFormatException with the message plus path and attaches the original exception as cause.

<a id="u-4c8bc46181ff"></a>
### `JsonTreeReader.peek`

`@SuppressWarnings("ReferenceEquality") @Override public JsonToken peek() throws IOExc…` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L127-L171][f2]

Maps the stack top to a JsonToken.

Empty stack returns END_DOCUMENT. For an Iterator, isObject is determined by whether the element beneath is a JsonObject: if the iterator has more elements, an object iterator yields NAME (the caller consumes the entry), while an array iterator pushes the next element and recurses so the element's own token is returned; an exhausted iterator yields END_OBJECT or END_ARRAY. JsonObject/JsonArray map to BEGIN_OBJECT/BEGIN_ARRAY; JsonPrimitive maps to STRING, BOOLEAN, or NUMBER by isString/isBoolean/isNumber, with AssertionError for a primitive that is none of these. JsonNull maps to NULL. The SENTINEL_CLOSED marker triggers IllegalStateException("JsonReader is closed"), and any custom JsonElement subclass raises MalformedJsonException naming the unsupported class.

calls: [JsonPrimitive](r2-dom-tree.md#u-1c779c98f5ee)

**Uncertainties.**

- peek() mutates stack state when an array iterator has a next element (it pushes the element); a later structural change to the underlying tree between peeks is not guarded.

<a id="u-8372afaad9ad"></a>
### `JsonTreeReader.peekStack`

`private Object peekStack()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L173-L175][f2]

Returns the top stack entry without removing it.

<a id="u-cfeea5861c07"></a>
### `JsonTreeReader.popStack`

`@CanIgnoreReturnValue private Object popStack()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L177-L182][f2]

Decrements stackSize, nulls the vacated slot, and returns the removed entry.

<a id="u-714b59883760"></a>
### `JsonTreeReader.promoteNameToValue`

`public void promoteNameToValue() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L361-L370][f2]

Requires a NAME token, takes the next entry without emitting it, records the name in pathNames so the path includes it after promotion (issue 1768), pushes the entry's value, then pushes a JsonPrimitive of the name so a subsequent scalar read returns the name.

**Uncertainties.**

- The entry value pushed first means the name primitive sits on top; reading it as a value then leaves the value on the stack, an ordering that is not further verified here.

<a id="u-f525a65badc2"></a>
### `JsonTreeReader.push`

`private void push(Object newTop)` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L372-L380][f2]

Grows stack, pathIndices, and pathNames to double length together when stackSize reaches capacity, then appends the new top.

<a id="u-5f1e3eb36679"></a>
### `JsonTreeReader.skipValue`

`@Override public void skipValue() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L330-L354][f2]

Consumes one value by token: NAME delegates to nextName(true) recording '<skipped>'; END_ARRAY/END_OBJECT delegate to endArray/endObject; END_DOCUMENT does nothing; every other token pops the value and advances the parent path index.

<a id="u-2e16d40670d0"></a>
### `JsonTreeReader.validateAscii`

`private void validateAscii(String s) throws MalformedJsonException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java:L437-L442][f2]

Throws MalformedJsonException quoting the string and path when isAllAscii is false; used before numeric parsing of string tokens.

<a id="u-9491af816173"></a>
### `jsonparser-java`

`@Deprecated public JsonParser()` · [gson/src/main/java/com/google/gson/JsonParser.java:L77-L78][f3]

Static facade parsing JSON into a JsonElement tree, always in lenient mode unless the caller supplies a stricter JsonReader.

parseString wraps the text in a StringReader and delegates to parseReader(Reader). parseReader(Reader) creates a JsonReader, parses via parseReader(JsonReader), and enforces a complete document: if the result is not JsonNull and the reader's next token is not END_DOCUMENT, it throws JsonSyntaxException("Did not consume the entire document."). MalformedJsonException and NumberFormatException are wrapped as JsonSyntaxException; other IOExceptions as JsonIOException. parseReader(JsonReader) reads the current strictness; if it is LEGACY_STRICT it temporarily switches to LENIENT, then parses through Streams.parse. StackOverflowError and OutOfMemoryError from deep or huge inputs are converted to JsonParseException, and the finally block restores the reader's original strictness, so strictness is unchanged on both success and failure. The three deprecated instance parse methods are InlineMe shims delegating to the corresponding static methods.

**Notes.**

- failure: parseReader(JsonReader) does not itself reject trailing data; that check exists only in parseReader(Reader).
- condition: For a reader already in STRICT strictness, the strictness is used as-is and no lenient switch occurs.

calls: [Streams.parse](r2-infrastructure.md#u-60dc50371529), [jsonelement-class](r2-dom-tree.md#u-103ba2beeebe)

**Uncertainties.**

- Behavior of Streams.parse itself (e.g. exact error token details) is outside this file's source.

<a id="u-78d58349ebd3"></a>
### `jsonstreamparser-java`

`public JsonStreamParser(String json)` · [gson/src/main/java/com/google/gson/JsonStreamParser.java:L59-L61][f4]

Iterator over a stream of concatenated top-level JSON elements, parsed lazily in lenient mode.

Constructors accept a String or Reader, wrap it in a JsonReader with Strictness.LENIENT, and create a private lock object; the class is only conditionally thread-safe, so callers must externally synchronize (the sample uses synchronized on the parser). hasNext() under the lock peeks the reader: any token other than END_DOCUMENT yields true; MalformedJsonException becomes JsonSyntaxException and other IOException becomes JsonIOException. next() first calls hasNext(), throwing NoSuchElementException when exhausted, then parses one element with Streams.parse; StackOverflowError or OutOfMemoryError are converted to JsonParseException. Because parsing happens inside next(), a partially consumed element can remain on the reader if an error is thrown. remove() always throws UnsupportedOperationException. Note next() itself does not hold the lock, so hasNext()+next() sequences need external synchronization across threads.

calls: [Streams.parse](r2-infrastructure.md#u-60dc50371529), [JsonReader](r1-streaming-json.md#u-92ec22311967)

**Uncertainties.**

- The exact peek target (JsonReader vs JsonTreeReader) is not resolvable from this file; graph lists two candidates for hasNext().

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonReader.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JsonTreeReader.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonParser.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonStreamParser.java