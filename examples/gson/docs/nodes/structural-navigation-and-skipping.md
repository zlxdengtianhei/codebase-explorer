# Structural navigation and skipping

**Capability.** Handles begin/end container transitions, scope pushing with nesting-limit enforcement, and recursive value skipping.

This module covers the structural half of the parser: consuming array/object delimiters, skipping quoted strings and whole nested values, and pushing scopes under the nesting limit. It sits between the public API and the lexer.

**Depends on.**

- [Lexing and buffer lookahead](lexing-and-buffer-lookahead.md) · graph-confirmed · 8 edge(s)
- [Token consumption and value decoding](token-consumption-and-value-decoding.md) · graph-confirmed · 7 edge(s)

Parent: [Streaming JsonReader](streaming-jsonreader.md)

## Units (4)

<a id="u-ba1fa296c06c"></a>
### `JsonReader.java-structure-token-consumers`

`public void beginArray() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L467-L479][f1]

Each consumes the peeked token (running doPeek if none is buffered) and throws unexpectedTokenError (IllegalStateException) unless it matches the expected structure token.

beginArray/beginObject push EMPTY_ARRAY/EMPTY_OBJECT (subject to the nesting limit) and reset the parent path index for arrays; endArray/endObject pop the stack, null out the freed pathNames slot for objects, and increment the parent's pathIndices.

<a id="u-698ceeda949f"></a>
### `JsonReader.java-value-skippers`

`private void skipQuotedValue(char quote) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1345-L1370][f1]

skipQuotedValue advances past a quoted string without building it, decoding escapes (so escape errors still surface) and tracking newlines; unterminated input throws syntaxError.

skipUnquotedValue advances past an unquoted literal up to the first non-literal character, requiring leniency if '/', '\\', ';', '#', or '=' is hit; it silently stops at end of input.

<a id="u-67b460aa2789"></a>
### `JsonReader.push`

`private void push(int newTop) throws MalformedJsonException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1584-L1598][f1]

Pushes a new scope onto the stack, first throwing MalformedJsonException if the number of open containers (stackSize - 1) reaches the nesting limit.

Doubles stack, pathIndices, and pathNames together when full.

<a id="u-0f6dd79edc39"></a>
### `JsonReader.skipValue`

`public void skipValue() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1506-L1582][f1]

Skips the next value recursively: begin tokens push scopes and increment a counter, end tokens pop and decrement, so a nested structure is skipped entirely; EOF returns immediately with no effect.

Names are skipped without their values (pathNames gets "<skipped>" at the top scope when count is 0), quoted/unquoted values use the dedicated skippers, numbers advance by peekedNumberLength, and already-consumed tokens (booleans, null, buffered) need no action. Afterwards clears the peek cache, advances the parent path index, and records a promoted name as "<skipped>".

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonReader.java
