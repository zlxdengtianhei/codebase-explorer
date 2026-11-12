# JSON value consumption

**Capability.** Consumes JSON scalar values, property names, strings, and unquoted values with strict validation.

Use for JsonReader methods that read scalar and name tokens. Units show boolean/number/null consumers, string reading/validation, and unexpected-token errors.

**Depends on.**

- [JSON token scanning](json-token-scanning.md) · graph-confirmed · 16 edge(s) · JSON value consumption uses token scanning to parse scalar values, strings, and property names.
- [Reflective adapter support](reflective-adapter-support.md) · graph-only · 1 edge(s)

**Depended on by.**

- [JSON structure navigation](json-structure-navigation.md) · graph-confirmed · 5 edge(s)

Parent: [Streaming JSON reader internals](streaming-json-reader-internals.md)

## Units (12)

<a id="u-98001a02792f"></a>
### `JsonReader.java-boolean-consumer`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1030-L1037][f1]

Boolean consumer.

It peeks if needed; TRUE and FALSE clear the peeked token, increment the current path index, and return the corresponding value; any other token type throws an unexpected-token IllegalStateException.

<a id="u-73acbbf14cf2"></a>
### `JsonReader.java-double-consumer`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1072-L1084][f1]

Double consumer.

It peeks if needed; a long is returned directly after clearing and incrementing, while number, quoted, unquoted, and buffered tokens are converted to a string for parsing. Parse failure is rethrown as NumberFormatException with location and cause. In non-lenient mode NaN or infinity is a syntax error. Success clears the buffered string and peeked token, increments the path index, records a promoted name, and returns the value.

<a id="u-a07b7a097600"></a>
### `JsonReader.java-int-consumer`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1403-L1414][f1]

Int consumer.

It peeks if needed; a long is cast to int and rejected with NumberFormatException if precision is lost. Number, quoted, and unquoted tokens are converted to a string; quoted/unquoted strings are ASCII-validated and tried with Integer.parseInt. Direct success clears the peeked token, increments the path index, records the promoted name, and returns. If direct parsing fails, it parses as double, rethrows parse failure with location and cause, rejects a cast that loses precision, then clears the buffered string and peeked token, increments, records, and returns. Other token types throw an unexpected-token IllegalStateException.

<a id="u-786248d42cf2"></a>
### `JsonReader.java-long-consumer`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1131-L1142][f1]

Long consumer.

It peeks if needed; a long is returned directly after clearing and incrementing. Number, quoted, and unquoted tokens are converted to a string; quoted/unquoted strings are ASCII-validated and tried with Long.parseLong. That direct success clears the peeked token, increments the path index, records the promoted name, and returns without clearing the buffered string. If direct parsing fails, it parses as double, rethrows parse failure with location and cause, rejects a cast that loses precision, then clears the buffered string and peeked token, increments, records, and returns. Other token types throw an unexpected-token IllegalStateException.

<a id="u-bdf6b449e5b8"></a>
### `JsonReader.java-null-consumer`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1054-L1061][f1]

Null consumer.

It peeks if needed; NULL clears the peeked token and increments the current path index; any other token type throws an unexpected-token IllegalStateException.

<a id="u-321946c0df31"></a>
### `JsonReader.java-promoted-name-path-fixup`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L980-L983][f1]

Promoted-name path fixup.

If a name was promoted to a value, it writes that name into the current object path slot and clears the flag; otherwise it does nothing.

<a id="u-b767757dba91"></a>
### `JsonReader.java-property-name-consumer`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L951-L958][f1]

Property-name consumer.

It peeks if needed, reads an unquoted, single-quoted, or double-quoted name, clears the peeked token, records the name in the current object path slot, and returns it; any other token type throws an unexpected-token IllegalStateException.

<a id="u-47226c938ab5"></a>
### `JsonReader.java-quoted-string-reader`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1200-L1209][f1]

Quoted-string reader.

It reads until the closing quote, unescaping backslash sequences and updating line tracking on newlines. In STRICT mode an unescaped control character below U+0020 is a syntax error. It returns the validated string and consumes the closing quote; EOF before the quote is an unterminated-string syntax error.

<a id="u-91c05cd50052"></a>
### `JsonReader.java-strict-string-validation`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1263-L1266][f1]

Strict-mode string validation.

Outside STRICT it returns the value unchanged. In STRICT it scans UTF-16 characters, allows a high surrogate only when immediately followed by a low surrogate, and throws a syntax error for any unpaired surrogate.

<a id="u-e36ba2776d40"></a>
### `JsonReader.java-string-consumer`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L988-L996][f1]

String consumer.

It peeks if needed and accepts unquoted, single-quoted, double-quoted, buffered, long, and number tokens, converting numbers to their string form. It clears the peeked token, increments the current path index, records a promoted name if pending, and returns the string; other token types throw an unexpected-token IllegalStateException.

<a id="u-9d3432715686"></a>
### `JsonReader.java-unquoted-value-reader`

`class JsonReader implements Closeable` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1283-L1286][f1]

Unquoted-value reader.

It scans until a structural or whitespace character, treating '/', backslash, ';', '#', and '=' as terminators only after requiring lenient mode. It builds a string across buffer refills when needed, advances the position, and returns the value.

<a id="u-96a70375a8c6"></a>
### `JsonReader.unexpectedTokenError`

`private IllegalStateException unexpectedTokenError(String expected) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonReader.java:L1948-L1960][f1]

Unexpected-token error factory.

It peeks the current token, chooses a null-safety troubleshooting id for NULL and a general structure id otherwise, and returns an IllegalStateException naming the expected token, actual token, location, and troubleshooting URL.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonReader.java
