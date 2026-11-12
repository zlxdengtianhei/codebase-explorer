# JSON structure navigation

**Capability.** Consumes array/object structure tokens and skips nested values while maintaining reader scopes.

Use for JsonReader structural token handling and skipping. Units show array/object consumers, recursive skipper, scope push, and quoted/unquoted skippers.

**Depends on.**

- [JSON token scanning](json-token-scanning.md) · graph-confirmed · 10 edge(s) · JSON structure navigation uses token scanning to consume structural tokens and skip nested values.
- [JSON value consumption](json-value-consumption.md) · graph-confirmed · 5 edge(s)

Parent: [Streaming JSON reader internals](streaming-json-reader-internals.md)

## Units (6)

<a id="u-1181d2bf28bc"></a>
### `JsonReader.java-array-structure-tokens`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L459-L467][f1]

Array structure token consumers.

The begin method peeks if needed; on BEGIN_ARRAY it pushes an empty-array scope, resets the path index for that newly pushed array to 0, and clears the peeked token; otherwise it throws an unexpected-token IllegalStateException. The end method accepts END_ARRAY, pops the scope, increments the parent path index, and clears the peeked token; otherwise it throws.

<a id="u-f4fdada67760"></a>
### `JsonReader.java-object-structure-tokens`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L499-L507][f1]

Object structure token consumers.

The begin method peeks if needed; on BEGIN_OBJECT it pushes an empty-object scope and clears the peeked token; otherwise it throws an unexpected-token IllegalStateException. The end method accepts END_OBJECT, pops the scope, clears the freed path-name slot, increments the parent path index, and clears the peeked token; otherwise it throws.

<a id="u-9297b13277e1"></a>
### `JsonReader.java-recursive-value-skipper`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1488-L1506][f1]

Recursive value skipper.

It loops while nested begin tokens are open: begin array/object pushes a scope and increases depth; end array/object pops and decreases depth, with an object end at depth zero also clearing the freed path name. Primitive tokens are skipped, names are skipped and at depth zero recorded as skipped in the path, numbers advance by their length, and EOF returns immediately. After the loop it increments the current path index and records a skipped promoted name.

<a id="u-67b460aa2789"></a>
### `JsonReader.push`

`private void push(int newTop) throws MalformedJsonException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1584-L1598][f1]

Scope push.

It first enforces the nesting limit, throwing MalformedJsonException with location when the number of open containers would exceed it. It doubles the stack and path arrays when full, then appends the new scope and increments the stack size.

<a id="u-7153c19980d9"></a>
### `JsonReader.skipQuotedValue`

`private void skipQuotedValue(char quote) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1345-L1370][f1]

Quoted-value skipper.

It advances past a quoted string, handling backslash escapes and line tracking, and throws an unterminated-string syntax error if EOF arrives before the closing quote.

<a id="u-64add9d78a58"></a>
### `JsonReader.skipUnquotedValue`

`@SuppressWarnings("fallthrough") private void skipUnquotedValue() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1372-L1403][f1]

Unquoted-value skipper.

It advances until a structural or whitespace character, requiring lenient mode for '/', backslash, ';', '#', and '=' before treating them as terminators, and refills the buffer as needed.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonReader.java
