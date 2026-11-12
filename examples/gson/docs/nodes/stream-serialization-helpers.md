# Stream serialization helpers

**Capability.** Provides stream adapters and helpers for serializing JsonElement trees and adapting readers/writers.

Use for internal stream bridging and JsonElement string serialization. Units show internal reader access, Appendable writer adapter, stream helpers, and element serialization.

**Depends on.**

- [JsonElement tree adapter](jsonelement-tree-adapter.md) · graph-confirmed · 1 edge(s)
- [JsonElement tree base](jsonelement-tree-base.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Map type adapter factory](map-type-adapter-factory.md) · graph-confirmed · 2 edge(s)
- [Gson serialization facade](gson-serialization-facade.md) · graph-only · 3 edge(s)
- [Gson builder configuration](gson-builder-configuration.md) · graph-only · 2 edge(s)
- [Public API utility classes](public-api-utility-classes.md) · graph-only · 2 edge(s)

Parent: [JSON element tree components](json-element-tree-components.md)

## Units (4)

<a id="u-e6c60baceb30"></a>
### `JsonReaderInternalAccess.java-internal-reader-access`

`class JsonReaderInternalAccess` · [gson/src/main/java/com/google/gson/internal/JsonReaderInternalAccess.java:L23-L26][f1]

Abstract internal bridge exposing a reader operation and a volatile singleton slot.

The slot is expected to be initialized by the reader class during loading; this source does not implement it. The abstract operation changes the current property-name token into a string value and may throw IOException.

<a id="u-7d1d8ec2c5d4"></a>
### `Streams.java-appendable-writer-and-current-write`

`class AppendableWriter extends Writer` · [gson/src/main/java/com/google/gson/internal/Streams.java:L78-L79][f2]

Writer adapter over an Appendable, plus a mutable CharSequence view for char-array writes.

Char-array writes set the current char array and call append with that view and the offset range; whether the Appendable copies or calls subSequence is implementation-dependent, and this source does not show that append invokes subSequence. The view's subSequence returns a new String, and toString caches a new String of the whole array. Flush and close act only when the Appendable implements Flushable or Closeable. Single-char writes append a char; string writes require non-null and append the requested range; append methods delegate and return this.

**Uncertainties.**

- The source does not show whether Appendable.append(CharSequence,int,int) copies the sequence or calls subSequence; CurrentWrite.subSequence itself returns a new String.

<a id="u-6bc714ade6ec"></a>
### `Streams.java-stream-parse-and-write-helpers`

`class Streams` · [gson/src/main/java/com/google/gson/internal/Streams.java:L37-L38][f2]

Stream helpers for parse trees and writer adaptation.

Parse peeks first; an EOF before any token returns JsonNull.INSTANCE, while EOF after peeking becomes JsonSyntaxException. Malformed JSON and number-format failures become JsonSyntaxException; other IO failures become JsonIOException. Write delegates to the element adapter. Writer adaptation returns the same object when it is already a Writer, otherwise wraps the Appendable.

<a id="u-0310357cd012"></a>
### `JsonElement.toString`

`@Override public String toString()` · [gson/src/main/java/com/google/gson/JsonElement.java:L420-L433][f3]

Serializes this element to a JSON string using a StringBuilder, a JsonWriter over an appendable writer, and the internal stream writer.

The writer is set to lenient strictness so values such as NaN and Infinity are emitted. Any IOException is wrapped in AssertionError; the method returns the accumulated JSON text.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/JsonReaderInternalAccess.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/Streams.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonElement.java
