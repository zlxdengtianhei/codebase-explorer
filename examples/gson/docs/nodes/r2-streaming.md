# Streaming JSON Writer and Lexical Model

**Capability.** Emits RFC 8259 JSON token by token through a scope-stack state machine (JsonScope), with a Strictness policy, the JsonToken vocabulary, and MalformedJsonException defining the lexical contract shared with reading.

Use JsonWriter for direct character output: structural methods (name, begin/end array/object) and value overloads all funnel through writeDeferredName/beforeValue/newline and the formatting style configured by setFormattingStyle/setIndent. JsonScope and Strictness explain the state and validation rules; JsonToken names the stream's token types.

**Depends on.**

- [Gson Facade and Conversion API](r1-facade-api.md) · graph-only · 7 edge(s)

**Depended on by.**

- [Built-in Type Adapter Factories](r2-default-adapters.md) · model-inferred · 0 edge(s)
- [JSON DOM Tree](r2-dom-tree.md) · graph-confirmed · 6 edge(s)
- [Tree-Bound Writer](r2-tree-writer.md) · graph-confirmed · 5 edge(s) · JsonTreeWriter mirrors the streaming JsonWriter structural contract while building a tree.
- [Gson Facade and Conversion API](r1-facade-api.md) · graph-only · 26 edge(s)

Parent: [Gson JSON Library](r2-gson.md)

## Units (22)

<a id="u-d122b2c80531"></a>
### `JsonWriter`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L162-L231][f1]

Streaming writer that emits RFC 8259 JSON to a Writer token by token, tracking nesting with an int scope stack seeded to EMPTY_DOCUMENT by an instance initializer.

Static initialization builds REPLACEMENT_CHARS (control chars as \u00xx plus quote, backslash, tab, backspace, newline, carriage return, form feed) and an HTML-safe clone also escaping <, >, &, =, and '; VALID_JSON_NUMBER_PATTERN validates Number.toString output. Instances are single-use per stream and not thread safe; malformed call sequences throw IllegalStateException, invalid numbers IllegalArgumentException.

**Notes.**

- field: Cached state derived from the formatting style (formattedColon, formattedComma, usesEmptyNewlineAndIndent) is recomputed on each style change to avoid per-write evaluation.

calls: [JsonWriter.setFormattingStyle](r2-streaming.md#u-0b57837cd8a1)

<a id="u-2378d32a3e3a"></a>
### `jsonwriter-array-object-scopes`

`@CanIgnoreReturnValue public JsonWriter beginArray() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L406-L410][f1]

Bracket handling for arrays and objects.

beginArray/beginObject flush any deferred name, then openScope runs beforeValue (emitting separators), pushes EMPTY_ARRAY or EMPTY_OBJECT, and writes '[' or '{'. endArray/endObject call closeScope, which peeks the top scope and throws IllegalStateException('Nesting problem.') when it is neither the expected empty nor nonempty variant, and IllegalStateException('Dangling name: ...') when a name lacks a value; otherwise it pops the scope, writes a newline first if the scope was nonempty, and writes ']' or '}'. All return this writer; IOException propagates from the underlying Writer.

calls: [JsonWriter.writeDeferredName](r2-streaming.md#u-6a980e648500), [jsonwriter-array-object-scopes](r2-streaming.md#u-2378d32a3e3a)

<a id="u-cccb91734698"></a>
### `jsonwriter-config-accessors`

`@Deprecated // Don't specify @InlineMe, so caller with setLenient(false) becomes aw…` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L309-L315][f1]

Configuration accessors for strictness, HTML safety, and null serialization.

setLenient(boolean) maps true to Strictness.LENIENT and false to LEGACY_STRICT by delegating to setStrictness, which stores a non-null strictness (null throws NullPointerException). isLenient() is true only when strictness equals LENIENT; getStrictness returns it. setHtmlSafe and setSerializeNulls store their flags and the getters return them. Strictness governs value validation elsewhere (NaN/infinity, multiple top-level values); serializeNulls controls whether nullValue() writes a value for a deferred name.

calls: [jsonwriter-config-accessors](r2-streaming.md#u-cccb91734698)

<a id="u-6c7c3ae29103"></a>
### `jsonwriter-stack-helpers`

`private void push(int newTop)` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L472-L477][f1]

Scope-stack primitives underlying every structural decision.

push appends a scope, doubling the 32-slot int array with Arrays.copyOf when full. peek throws IllegalStateException('JsonWriter is closed.') when stackSize is 0, otherwise returns the top scope. replaceTop overwrites the top slot with no emptiness check, so callers must guarantee a live scope.

<a id="u-776591f6d945"></a>
### `jsonwriter-value-overloads`

`@CanIgnoreReturnValue public JsonWriter value(String value) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L526-L535][f1]

Scalar value writers sharing a common sequence: flush any deferred name, then beforeValue, then the literal.

String, Boolean-boxed, and Number overloads treat null as nullValue(). value(boolean) and value(long) write 'true'/'false' and Long.toString directly. value(float) and value(double) throw IllegalArgumentException('Numeric values must be finite, but was ...') for NaN/infinity unless strictness is LENIENT, then append their toString. value(Number) writes Number.toString() directly; for classes not in alwaysCreatesValidJsonNumber it validates first: exact strings 'Infinity', '-Infinity', 'NaN' are allowed only when LENIENT, and other non-Float/Double classes must match VALID_JSON_NUMBER_PATTERN or throw IllegalArgumentException('String created by ... is not a valid JSON number').

calls: [JsonWriter.nullValue](r2-streaming.md#u-09865727958f), [JsonWriter.alwaysCreatesValidJsonNumber](r2-streaming.md#u-72f261060659)

**Uncertainties.**

- The graph leaves nullValue() call targets in the value overloads ambiguous between JsonWriter.nullValue and JsonTreeWriter.nullValue; within this class the receiver is JsonWriter so JsonWriter.nullValue is used here.

<a id="u-72f261060659"></a>
### `JsonWriter.alwaysCreatesValidJsonNumber`

`private static boolean alwaysCreatesValidJsonNumber(Class<? extends Number> c)` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L730-L741][f1]

Static predicate reporting whether a Number subclass's toString is guaranteed to be a valid JSON number: Integer, Long, Byte, Short, BigDecimal, BigInteger, AtomicInteger, and AtomicLong qualify.

Float and Double are excluded because they can be NaN or infinite, and lazily parsed numbers are excluded because their string could be malformed; such classes force validation in value(Number).

<a id="u-d0ef08a1ce43"></a>
### `JsonWriter.beforeName`

`private void beforeName() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L790-L799][f1]

Prepares output for a property name and updates the scope stack.

If the top scope is NONEMPTY_OBJECT it writes the cached formattedComma; if it is not EMPTY_OBJECT either, it throws IllegalStateException('Nesting problem.'); EMPTY_OBJECT writes nothing. Then it emits a newline when formatting requires one and replaces the top scope with DANGLING_NAME, so the next write must be this name's value.

<a id="u-ad1b67731900"></a>
### `JsonWriter.beforeValue`

`@SuppressWarnings("fallthrough") private void beforeValue() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L805-L835][f1]

Inserts separators before any literal value, array, or object and adjusts the scope, dispatching on the peeked scope: NONEMPTY_DOCUMENT throws IllegalStateException('JSON must have only one top-level value.') unless strictness is LENIENT, in which case it falls through; EMPTY_DOCUMENT and the fallen-through NONEMPTY_DOCUMENT replace the top with NONEMPTY_DOCUMENT; EMPTY_ARRAY becomes NONEMPTY_ARRAY and writes a newline; NONEMPTY_ARRAY writes formattedComma then a newline; DANGLING_NAME writes formattedColon and becomes NONEMPTY_OBJECT.

Any other scope (including CLOSED) throws IllegalStateException('Nesting problem.').

<a id="u-f4c5ccc43d0e"></a>
### `JsonWriter.close`

`@Override public void close() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L718-L727][f1]

Flushes and closes the underlying Writer, then verifies the document is complete: it throws IOException('Incomplete document') when more than one scope remains on the stack, or when the single remaining scope is not NONEMPTY_DOCUMENT (for example after closeScope popped the top-level value but lenient multiple values left a fresh EMPTY_DOCUMENT).

On success it sets stackSize to 0, which makes subsequent peek, flush, and any structural call fail with 'JsonWriter is closed'.

<a id="u-6d507e7579af"></a>
### `JsonWriter.flush`

`@Override public void flush() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L705-L711][f1]

Flushes buffered output to the underlying Writer.

Throws IllegalStateException('JsonWriter is closed.') when stackSize is 0, i.e. after close() has reset the stack; otherwise delegates to out.flush().

<a id="u-9480bc3f4b32"></a>
### `JsonWriter.jsonValue`

`@CanIgnoreReturnValue public JsonWriter jsonValue(String value) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L691-L700][f1]

Writes the given string to the stream verbatim, without quoting or escaping, after flushing any deferred name and running beforeValue.

A null argument is encoded as nullValue(). Subclasses that cannot support raw output may reject this with UnsupportedOperationException; this base implementation has no such check, so callers are responsible for the content being valid JSON.

**Uncertainties.**

- Which subclass throws UnsupportedOperationException is not visible in this file; only the Javadoc asserts it.

<a id="u-c396f32bf192"></a>
### `JsonWriter.name`

`@CanIgnoreReturnValue public JsonWriter name(String name) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L498-L510][f1]

Defers writing an object property name until the next value call.

It rejects a null name with NullPointerException, throws IllegalStateException('Already wrote a name, expecting a value.') if another deferred name is pending, and throws IllegalStateException('Please begin an object before writing a name.') unless the current scope is EMPTY_OBJECT or NONEMPTY_OBJECT. On success it stores the name and returns this writer; the name is actually encoded later by writeDeferredName via beforeName and string.

uses: [JsonWriter.writeDeferredName](r2-streaming.md#u-6a980e648500)

<a id="u-b48d57328999"></a>
### `JsonWriter.newline`

`private void newline() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L775-L784][f1]

Writes pretty-printing whitespace before separators and brackets.

Returns immediately without output when usesEmptyNewlineAndIndent is set (compact style); otherwise writes the style's newline string followed by the indent string repeated stackSize-1 times, so the top-level document scope gets no indentation.

uses: [formattingstyle-java](r1-facade-api.md#u-674df3655ab3)

<a id="u-09865727958f"></a>
### `JsonWriter.nullValue`

`@CanIgnoreReturnValue public JsonWriter nullValue() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L666-L679][f1]

Writes the literal 'null' with beforeValue separators.

When a name is deferred, serializeNulls decides the outcome: if true the name is flushed and 'null' written as its value; if false the deferred name is discarded and the method returns without writing anything, skipping both the name and the value. This skipping affects object members only, not array elements.

**Notes.**

- condition: If serializeNulls is false and a name is pending, no output is produced at all for that member.

<a id="u-0b57837cd8a1"></a>
### `JsonWriter.setFormattingStyle`

`public final void setFormattingStyle(FormattingStyle formattingStyle)` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L266-L283][f1]

Stores the formatting style and precomputes the separator strings used by all later writes.

formattedColon defaults to ':' and formattedComma to ','; when the style usesSpaceAfterSeparators, formattedColon becomes ': ' and formattedComma becomes ', ' only if the style's newline is empty, otherwise it stays ','. usesEmptyNewlineAndIndent is true when both newline and indent are empty, which makes newline() emit nothing. Null style throws NullPointerException.

uses: [formattingstyle-java](r1-facade-api.md#u-674df3655ab3)

<a id="u-a9b5222e3bd5"></a>
### `JsonWriter.setIndent`

`public final void setIndent(String indent)` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L248-L254][f1]

Convenience setter that overwrites any previously set formatting style from an indent string: an empty indent selects FormattingStyle.COMPACT, a non-empty indent selects PRETTY with that indent via withIndent.

A null indent fails with NullPointerException from indent.isEmpty().

calls: [JsonWriter.setFormattingStyle](r2-streaming.md#u-0b57837cd8a1), [formattingstyle-java](r1-facade-api.md#u-674df3655ab3)

<a id="u-7ae7c2f67a79"></a>
### `JsonWriter.string`

`private void string(String value) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L743-L773][f1]

Writes a quoted, escaped JSON string.

It picks HTML_SAFE_REPLACEMENT_CHARS when htmlSafe is set, otherwise REPLACEMENT_CHARS, opens a quote, then scans chars: ASCII chars with a replacement table entry are substituted (control chars as \u00xx, quote, backslash, tab, backspace, newline, carriage return, form feed; plus <, >, &, =, ' in HTML-safe mode), U+2028 and U+2029 always become \u2028/\u2029, and all other chars pass through. Runs of unescaped text are written in bulk between substitutions, and the closing quote is appended.

<a id="u-6a980e648500"></a>
### `JsonWriter.writeDeferredName`

`private void writeDeferredName() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L512-L518][f1]

Flushes any name stored by name(): if a deferred name exists it runs beforeName (emitting separators and switching the scope to DANGLING_NAME), writes the name through string (quoting/escaping), and clears the pending name.

Does nothing when no name is deferred.

calls: [JsonWriter.string](r2-streaming.md#u-7ae7c2f67a79), [JsonWriter.beforeName](r2-streaming.md#u-d0ef08a1ce43)

<a id="u-bd71fedaafc9"></a>
### `gson/src/main/java/com/google/gson/stream/JsonScope.java:JsonScope`

`class JsonScope` · [gson/src/main/java/com/google/gson/stream/JsonScope.java:L26-L51][f2]

Defines package-private int constants for the lexical states of a JSON reader or writer: EMPTY_ARRAY, NONEMPTY_ARRAY, EMPTY_OBJECT, DANGLING_NAME, NONEMPTY_OBJECT, EMPTY_DOCUMENT, NONEMPTY_DOCUMENT, and CLOSED.

Consumers such as JsonWriter keep these on an int stack to decide when separators, newlines, or errors apply. The private constructor prevents instantiation.

<a id="u-80701413ca25"></a>
### `JsonToken`

`public enum JsonToken` · [gson/src/main/java/com/google/gson/stream/JsonToken.java:L25-L76][f3]

Public enum naming each token type of a JSON stream: BEGIN_ARRAY, END_ARRAY, BEGIN_OBJECT, END_OBJECT, NAME, STRING, NUMBER, BOOLEAN, NULL, and the END_DOCUMENT sentinel signaled by JsonReader.peek() at stream end.

It carries no behavior; the Javadoc ties constants to the JsonWriter/JsonReader methods that produce or consume them.

<a id="u-3e0f7abd667b"></a>
### `gson/src/main/java/com/google/gson/stream/MalformedJsonException.java:MalformedJsonException`

`class MalformedJsonException extends IOException` · [gson/src/main/java/com/google/gson/stream/MalformedJsonException.java:L39-L40][f4]

Final IOException subclass thrown when a reader encounters malformed JSON; the Javadoc notes some syntax errors can be tolerated by setting Strictness.LENIENT on JsonReader.

It adds no state beyond serialVersionUID and offers three constructors: message only, message plus cause, and cause only, all delegating to IOException.

<a id="u-bfab23ee9e5a"></a>
### `Strictness`

`public enum Strictness` · [gson/src/main/java/com/google/gson/Strictness.java:L20-L29][f5]

Enumerates how strictly a JsonReader or JsonWriter follows RFC 8259 syntax.

Three levels ordered by permissiveness: LENIENT allows large deviations, LEGACY_STRICT permits certain small legacy deviations, and STRICT requires full specification compliance. The enum carries no methods; its effect is applied through JsonReader.setStrictness/JsonWriter.setStrictness and GsonBuilder.setStrictness, whose implementations determine concrete acceptance behavior.

uses: [Strictness.java module code (L1–L19)][f5]

**Uncertainties.**

- Concrete syntax deviations allowed per level are implemented in JsonReader/JsonWriter, not here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonWriter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonScope.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonToken.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/MalformedJsonException.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/Strictness.java