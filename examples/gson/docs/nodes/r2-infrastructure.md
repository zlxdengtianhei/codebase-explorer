# Internal Utilities and Data Structures

**Capability.** Provides non-public support: tree/stream bridging (Streams with its zero-copy AppendableWriter), deferred numeric parsing (LazilyParsedNumber), JVM version detection, a doc-link helper, an internal JsonReader extension point, and the insertion-ordered AVL-backed LinkedTreeMap.

These classes are consumed across all layers and are not public API. LinkedTreeMap (child node) is the storage behind JsonObject; Streams.parse/write bridge between JsonElement trees and streams; JavaVersion and TroubleshootingGuide support adapters and diagnostics.

**Children.**

- [Insertion-Ordered AVL Map](r2-linkedtreemap.md) `r2-linkedtreemap` · 10 unit(s)

**Depends on.**

- [Built-in Type Adapter Factories](r2-default-adapters.md) · graph-confirmed · 2 edge(s) · Streams.parse and Streams.write convert between JsonElement trees and streams via JsonElementTypeAdapter.
- [Collection, Map, and Tree Adapters](r2-collection-map-adapters.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Built-in Type Adapter Factories](r2-default-adapters.md) · graph-confirmed · 5 edge(s)
- [JSON DOM Tree](r2-dom-tree.md) · graph-confirmed · 13 edge(s) · JsonObject stores its members insertion-ordered in LinkedTreeMap and elements use Streams for bridging.
- [Streaming JSON Reading](r1-streaming-json.md) · graph-only · 4 edge(s)
- [Gson Facade and Conversion API](r1-facade-api.md) · graph-only · 3 edge(s)
- [Tree-Style Serializer Bridge](r1-tree-adapter-bridge.md) · graph-only · 2 edge(s)
- [Runtime Generic Type Model](r1-type-model.md) · graph-only · 2 edge(s)
- [Collection, Map, and Tree Adapters](r2-collection-map-adapters.md) · graph-only · 2 edge(s)
- [Primitive and Utility Type Adapters](r2-primitive-adapters.md) · graph-only · 2 edge(s)
- [TypeAdapter Framework](r1-adapter-framework.md) · graph-only · 1 edge(s)

Parent: [Gson JSON Library](r2-gson.md)

## Units (8)

<a id="u-931987e48ef4"></a>
### `Streams`

`class Streams` · [gson/src/main/java/com/google/gson/internal/Streams.java:L37-L38][f1]

Static helpers for reading and writing Gson parse trees over streams; instantiation is blocked by a constructor throwing UnsupportedOperationException.

write is a one-line recursive delegation to JsonElementTypeAdapter.ADAPTER.write for a JsonElement into a JsonWriter, propagating IOException. writerForAppendable returns the argument unchanged when it already is a Writer, otherwise wraps it in an AppendableWriter, bridging Appendable sinks to Writer-based APIs. parse has its own unit.

<a id="u-60dc50371529"></a>
### `Streams.parse`

`public static JsonElement parse(JsonReader reader) throws JsonParseException` · [gson/src/main/java/com/google/gson/internal/Streams.java:L43-L66][f1]

Reads the next JSON value from a reader in any state and returns it as a JsonElement.

It peeks first (a peek succeeding marks the stream non-empty) and then reads via JsonElementTypeAdapter.ADAPTER. Failure mapping: EOFException before any token returns JsonNull.INSTANCE for empty-document compatibility; EOFException after a token becomes JsonSyntaxException as a premature-end syntax error; MalformedJsonException and NumberFormatException both become JsonSyntaxException; any other IOException becomes JsonIOException. All checked exceptions are wrapped and rethrown, never swallowed except the empty-document EOF case.

**Uncertainties.**

- JsonElementTypeAdapter.ADAPTER's exact acceptance rules are outside this batch.

<a id="u-f5c946a5049b"></a>
### `AppendableWriter`

`class AppendableWriter extends Writer` · [gson/src/main/java/com/google/gson/internal/Streams.java:L78-L82][f1]

Writer adapter forwarding all output to an underlying Appendable, sharing one mutable CurrentWrite CharSequence to avoid copies on array writes.

write(char[], off, len) installs the array in currentWrite and appends the sub-range; write(int) appends a single char; write(String, off, len) requires a non-null string via Objects.requireNonNull because Appendable.append would otherwise render null as "null", which is undesired here; both append overrides forward and return this. flush forwards only when the appendable is Flushable, close only when it is Closeable; neither is an error otherwise. IOExceptions from the appendable propagate to the caller.

**Uncertainties.**

- Correctness of the shared CurrentWrite assumes the Appendable consumes the sequence before write returns; the code relies on that but cannot prove it here.

<a id="u-9b752c36b8ee"></a>
### `CurrentWrite`

`class CurrentWrite implements CharSequence` · [gson/src/main/java/com/google/gson/internal/Streams.java:L135-L139][f1]

Mutable CharSequence pointing at a caller-supplied char[] so array writes avoid copying.

setChars stores the array and invalidates the cached string. length returns the array's full length and charAt indexes it; the Appendable's offset/length arguments supply the actual window. subSequence and toString materialize Strings, with toString caching its result until the next setChars. Reading past the installed array would throw ArrayIndexOutOfBounds; nothing bounds-checks internally.

<a id="u-41ace061025e"></a>
### `LazilyParsedNumber`

`class LazilyParsedNumber extends Number implements Comparable<LazilyParsedNumber>` · [gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java:L28-L35][f2]

A Number holding an unparsed numeric string, deferring conversion to a concrete numeric type until a primitive accessor is called.

intValue tries Integer.parseInt, then Long.parseLong cast to int, then BigDecimal.intValue via asBigDecimal (which delegates to NumberLimits.parseBigDecimal); longValue tries Long.parseLong then BigDecimal.longValue; floatValue and doubleValue parse directly and propagate NumberFormatException on malformed input. Serialization replaces the instance with a BigDecimal via writeReplace, and readObject throws InvalidObjectException to block direct deserialization. equals and hashCode compare the string representation, and compareTo is lexicographic on the strings, so "10" sorts before "9"; numeric comparison requires comparing BigDecimals. The constructor's value parameter must not be null, but null is not checked in the constructor itself. toString returns the original string unchanged.

**Notes.**

- failure: floatValue, doubleValue, and the final BigDecimal fallback of intValue/longValue throw NumberFormatException if the string is not a valid number.
- contract: Equality and ordering are string-based, not numeric, per the class's own compareTo documentation.

calls: [NumberLimits.parseBigDecimal](r1-internal-support.md#u-5f49b1496f23)

<a id="u-c939eb041613"></a>
### `JavaVersion`

`class JavaVersion` · [gson/src/main/java/com/google/gson/internal/JavaVersion.java:L20-L28][f3]

Determines and caches the major Java version of the current JVM, handling nonstandard version strings.

On class load it reads the "java.version" system property and parses it. Parsing first tries dotted/underscore form via parseDotted, splitting on . or _ into at most 3 parts; a first part of 1 with more parts yields the second part (legacy 1.8 style), otherwise the first part. Any NumberFormatException there returns -1 and falls back to extractBeginningInt, which concatenates leading digit characters and parses them (also returning -1 on failure). If both strategies fail (e.g. Debian's nonnumeric formats produce empty strings), parseMajorJavaVersion defaults to 6, the minimum supported JDK. getMajorJavaVersion returns the cached value; isJava9OrLater compares it against 9. Parsing helpers are package-visible/static; determineMajorJavaVersion and the constructor are private, so the class cannot be instantiated.

**Notes.**

- side_effect: Class initialization reads the "java.version" system property once and caches the result in a static final field.
- failure: NumberFormatException is caught inside both parse helpers and converted to -1, never propagated.

**Uncertainties.**

- Behavior when "java.version" is null is not provable from this source: String.split on null would throw NPE, but the property's presence is assumed.

<a id="u-9bcd073a2728"></a>
### `TroubleshootingGuide`

`class TroubleshootingGuide` · [gson/src/main/java/com/google/gson/internal/TroubleshootingGuide.java:L3-L4][f4]

Utility producing links into Gson's troubleshooting documentation: createUrl(id) returns the fixed GitHub Troubleshooting.md URL with '#'+id appended; the private constructor blocks instantiation.

Members folded: createUrl implements the string concatenation only; no network access or validation occurs.

<a id="u-a3774963f70f"></a>
### `JsonReaderInternalAccess`

`class JsonReaderInternalAccess` · [gson/src/main/java/com/google/gson/internal/JsonReaderInternalAccess.java:L23-L30][f5]

Internal-only extension point of JsonReader for other Gson classes, exposed as an abstract class with a static volatile INSTANCE.

INSTANCE is not initialized here; it is assigned by the JsonReader class during its class loading, which the comments rely on for thread safety and safe publication. Its single abstract operation, promoteNameToValue(JsonReader), changes the current property-name token into a string value token; the implementation lives in JsonReader, and MapTypeAdapterFactory calls it through INSTANCE. Any use before JsonReader is loaded would see a null INSTANCE, but the class-loading ordering makes this unreachable in practice.

**Uncertainties.**

- The actual promoteNameToValue implementation and INSTANCE assignment are in JsonReader, outside this batch.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/Streams.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/JavaVersion.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/TroubleshootingGuide.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/JsonReaderInternalAccess.java