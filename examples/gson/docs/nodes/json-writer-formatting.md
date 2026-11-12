# JSON writer formatting

**Capability.** Implements streaming JSON writing, tree writing, formatting styles, escaping, and writer state handling.

Use for JSON output formatting and writer behavior. Units show FormattingStyle, JsonTreeWriter, JsonWriter token emission, escaping, and separators.

**Depends on.**

- [Gson serialization facade](gson-serialization-facade.md) · graph-confirmed · 4 edge(s)
- [JsonElement tree base](jsonelement-tree-base.md) · graph-only · 1 edge(s)
- [Ordered JSON array](ordered-json-array.md) · graph-only · 1 edge(s)
- [Ordered JSON object map](ordered-json-object-map.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Gson serialization facade](gson-serialization-facade.md) · graph-confirmed · 2 edge(s) · The Gson serialization facade uses JSON writer formatting to emit serialized output.

Parent: [Serialization facade and writing](serialization-facade-and-writing.md)

## Units (28)

<a id="u-98eaf74e288f"></a>
### `FormattingStyle.java-formattingstyle`

`class FormattingStyle` · [gson/src/main/java/com/google/gson/FormattingStyle.java:L39-L40][f1]

Immutable value object describing JSON output formatting: newline string, indent string, and whether a space follows ',' and ':'.

Predefined instances: COMPACT ("", "", false) and PRETTY ("\n", two spaces, true). The private constructor rejects null newline/indent and throws IllegalArgumentException unless newline matches only [\r\n]* and indent only [ \t]*. The withNewline/withIndent/withSpaceAfterSeparators methods return new instances copying the other two settings; the three getters return the stored values. JsonWriter consumes these getters when producing output.

<a id="u-bffdb6a59604"></a>
### `FormattingStyle.java-formattingstyle-immutable-withers`

`class FormattingStyle` · [gson/src/main/java/com/google/gson/FormattingStyle.java:L80-L95][f1]

These class regions of FormattingStyle each hold a wither that returns a new FormattingStyle copying the other two settings and replacing one: withNewline replaces the newline string, withIndent the indent string, and withSpaceAfterSeparators the boolean separator-space flag.

Because the private constructor validates inputs, every wither re-validates: a null newline or indent throws NullPointerException, a newline containing characters other than '\r'/'\n' throws IllegalArgumentException, and an indent containing characters other than spaces/tabs throws IllegalArgumentException. The original instance is never mutated.

<a id="u-a8d385011f00"></a>
### `JsonTreeWriter.java-container-begin-end`

`@CanIgnoreReturnValue @Override public JsonWriter beginArray() throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L99-L106][f2]

beginArray/beginObject create the container, put it into the current position, push it, and return this.

endArray/endObject throw IllegalStateException if stack empty or a name is pending; they remove the top only if it is the matching container type, otherwise throw.

<a id="u-0a23b4f06886"></a>
### `JsonTreeWriter.java-jsontreewriter-class`

`class JsonTreeWriter extends JsonWriter` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L33-L36][f2]

JsonWriter that builds a JsonElement tree.

Holds a stack of open elements, a pending object name, and a product root initialized to JsonNull. Constructor uses an unwritable writer. get returns product only when stack empty; close rejects incomplete documents.

<a id="u-782a08d0128a"></a>
### `JsonTreeWriter.java-put-and-peek`

`private JsonElement peek()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L76-L78][f2]

peek returns the top open element.

put with pendingName adds the value to the current JsonObject only if value is non-null or serializeNulls is true, then clears pendingName; with empty stack sets product; otherwise requires top to be JsonArray and appends, else throws IllegalStateException.

<a id="u-75b28b587985"></a>
### `JsonTreeWriter.java-terminal-operations`

`@Override public JsonWriter jsonValue(String value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L239-L242][f2]

jsonValue always throws UnsupportedOperationException.

flush is a no-op. close throws IOException if the stack is non-empty; otherwise adds the closed sentinel to the stack.

<a id="u-c5b8eed43e42"></a>
### `JsonTreeWriter.java-unwritable-writer`

`@Override public void write(char[] buffer, int offset, int counter)` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L36-L39][f2]

Anonymous Writer backing the superclass; write, flush, and close all throw AssertionError because tree writing never uses character output.

<a id="u-da4fe72bfabc"></a>
### `JsonTreeWriter.java-value-methods`

`@CanIgnoreReturnValue @Override public JsonWriter value(String value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L160-L168][f2]

String/Boolean/Number nulls route to nullValue; boolean/long write primitives.

Float/double and Number reject NaN/Infinity with IllegalArgumentException when not lenient. nullValue puts JsonNull. All successful values go through put.

<a id="u-16fa1c5bd4af"></a>
### `JsonWriter.java-array-and-object-scopes`

`@CanIgnoreReturnValue public JsonWriter beginArray() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L406-L410][f3]

Opens and closes array/object scopes, writing separators and brackets.

Beginning an array or object first flushes any deferred name, then runs value preparation, pushes the empty scope, and writes '[' or '{'. Closing checks that the top scope is the matching empty or nonempty kind and that no deferred name remains; it then pops the scope, writes a newline only for a nonempty scope, and writes ']' or '}'. A mismatched scope or dangling name throws IllegalStateException.

<a id="u-9f7e2ebca9ea"></a>
### `JsonWriter.java-configuration-documentation-and-defaults`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L224-L231][f3]

Documents the writer's configuration surface and defaults: compact formatting, LEGACY_STRICT strictness, HTML-unsafe output, and null serialization enabled.

setIndent maps an empty string to COMPACT and a non-empty string to PRETTY with that indent; setFormattingStyle requires non-null and caches separator/newline behavior. setLenient is deprecated and maps true to LENIENT, false to LEGACY_STRICT; isLenient is true only for LENIENT. setStrictness requires non-null; LENIENT permits NaN/Infinity and multiple top-level values, while STRICT and LEGACY_STRICT are identical for this writer. setHtmlSafe toggles escaping of <, >, &, =, and '; setSerializeNulls controls whether null object members are written and has no effect on array elements.

<a id="u-796c9dfcdbae"></a>
### `JsonWriter.java-flush-and-close`

`@Override public void flush() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L705-L711][f3]

Flushes or closes the underlying Writer while enforcing writer state.

Flush throws IllegalStateException if the writer is already closed, otherwise flushes the destination. Close first closes the destination, then throws IOException if the stack is deeper than one or the sole remaining scope is not a completed document; on success it clears the stack. Because the destination is closed before the completeness check, an incomplete document still closes the underlying Writer.

<a id="u-bdb45dbae5a7"></a>
### `JsonWriter.java-formatting-configuration`

`public final void setIndent(String indent)` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L248-L254][f3]

Controls the writer's formatting style and caches separator/newline decisions.

Setting an empty indent selects COMPACT; a nonempty indent selects PRETTY with that indent. Setting a style null-checks it, then sets colon to ': ' whenever space-after-separators is enabled, sets comma to ', ' only when that flag is enabled and the newline is empty, otherwise comma is ','; colon is ':' when the flag is off. The empty-newline-and-indent flag is true only when both newline and indent are empty. The getter returns the current style.

<a id="u-4644d7d61361"></a>
### `JsonWriter.java-jsonwriter-class-and-construction`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L162-L165][f3]

Streaming JSON writer that emits tokens to a supplied Writer while tracking nesting and deferred names.

The constructor rejects a null destination and installs COMPACT formatting; the instance starts with an empty-document scope, default LEGACY_STRICT strictness, HTML escaping off, and null serialization on. It is single-stream and not thread-safe; malformed call sequences are rejected with IllegalStateException.

<a id="u-e3b6d7ec88b5"></a>
### `JsonWriter.java-numeric-values`

`@CanIgnoreReturnValue public JsonWriter value(float value) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L577-L586][f3]

Writes numeric values with finite/format validation and deferred-name handling.

Float and double first flush a pending name, then reject NaN or infinity with IllegalArgumentException unless strictness is LENIENT, prepare the value position, and append the Java string form. Long flushes the name, prepares, and writes the decimal string. Number handles null as null, flushes a pending name before validation, then: for classes known to produce valid JSON numbers it skips validation; otherwise it rejects -Infinity/Infinity/NaN unless LENIENT, and for classes other than Float/Double it rejects strings not matching the JSON number pattern. Because the pending name is flushed first, a rejected Number can leave the property name already written. The known-valid classes are Integer, Long, Byte, Short, BigDecimal, BigInteger, AtomicInteger, and AtomicLong.

<a id="u-c6ade21c6d08"></a>
### `JsonWriter.java-property-names`

`@CanIgnoreReturnValue public JsonWriter name(String name) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L498-L510][f3]

Queues an object property name until its value is written.

The name setter rejects null, rejects a second pending name, and requires the current scope to be an empty or nonempty object; it stores the name without writing. The deferred writer, when a name is pending, writes the separator/newline, writes the quoted name, and clears the pending name.

<a id="u-bce0fd3e01a0"></a>
### `JsonWriter.java-scope-stack-helpers`

`private void push(int newTop)` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L472-L477][f3]

Maintains the nesting stack.

Push doubles the backing array when full and appends the new scope; peek throws IllegalStateException when the stack is empty, which represents a closed writer; replaceTop overwrites the current top.

<a id="u-07ee7883d862"></a>
### `JsonWriter.java-string-and-boolean-values`

`@CanIgnoreReturnValue public JsonWriter value(String value) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L526-L535][f3]

Writes string and boolean values, routing null strings and null boxed booleans to null handling.

Non-null values first flush any deferred name, prepare the value position, then write the quoted string or the literal true/false. The primitive boolean overload never treats a value as null.

<a id="u-b639ac6f0eeb"></a>
### `JsonWriter.java-structural-writing-documentation`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L398-L406][f3]

Documents the structural writing contract: beginArray and beginObject start a new array or object and must be paired with the corresponding end call; name records a non-null property name that is written only when the next value is emitted, and a second name before a value is an error.

<a id="u-5d7338d80cf5"></a>
### `JsonWriter.java-value-emission-documentation`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L518-L526][f3]

Documents value emission and separator handling.

String values treat null as nullValue; otherwise they write any deferred name, run beforeValue, then write an escaped string. Float and double values write the deferred name, reject NaN/Infinity unless strictness is LENIENT, then run beforeValue and append the numeric text. Long values write the deferred name, run beforeValue, and append. jsonValue treats null as nullValue; otherwise it writes the deferred name, runs beforeValue, and appends raw text. beforeValue inserts the required comma/colon/newline/indent and updates the scope stack; it throws on nesting problems and, for a non-empty document, throws unless strictness is LENIENT.

<a id="u-58a4de8f7ae3"></a>
### `JsonTreeWriter.get`

`public JsonElement get()` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L69-L74][f2]

get returns the produced root element; if any element remains open on the stack, throws IllegalStateException listing the stack.

<a id="u-d25e72cadb38"></a>
### `JsonTreeWriter.name`

`@CanIgnoreReturnValue @Override public JsonWriter name(String name) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java:L145-L158][f2]

name requires non-null, rejects empty stack or pending name with IllegalStateException, and sets pendingName only when top is JsonObject; otherwise throws IllegalStateException.

<a id="u-fcbf13c19cb0"></a>
### `gson/src/main/java/com/google/gson/stream/JsonWriter.java:JsonWriter`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L179-L202][f3]

Static initialization builds the two 128-entry replacement tables used for string escaping: control characters U+0000–U+001F become \uXXXX, and quote, backslash, tab, backspace, newline, carriage return, and form feed get short escapes; the HTML-safe clone additionally escapes <, >, &, =, and '.

The final writer field stores the non-null output destination.

<a id="u-d0ef08a1ce43"></a>
### `JsonWriter.beforeName`

`private void beforeName() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L790-L799][f3]

Prepares the writer for an object property name.

In a nonempty object it writes the cached comma; in an empty object it writes no comma; any other scope throws IllegalStateException. It then writes newline/indent and changes the top scope to dangling-name.

<a id="u-ad1b67731900"></a>
### `JsonWriter.beforeValue`

`@SuppressWarnings("fallthrough") private void beforeValue() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L805-L835][f3]

Prepares the writer for a value or opening bracket based on the current scope.

In a nonempty document it throws IllegalStateException unless strictness is LENIENT, then falls through to mark the document nonempty. In an empty document it marks it nonempty. In an empty array it marks it nonempty and writes newline/indent. In a nonempty array it writes the cached comma and newline/indent. In a dangling-name scope it writes the cached colon and marks the object nonempty. Any other scope throws IllegalStateException.

<a id="u-9480bc3f4b32"></a>
### `JsonWriter.jsonValue`

`@CanIgnoreReturnValue public JsonWriter jsonValue(String value) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L691-L700][f3]

Writes a raw JSON fragment without quoting or escaping.

A null argument delegates to null handling; otherwise it flushes any deferred name, prepares the value position, and appends the string verbatim. This base writer does not validate the fragment.

<a id="u-b48d57328999"></a>
### `JsonWriter.newline`

`private void newline() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L775-L784][f3]

Writes a newline and indentation before a nested element.

It does nothing when both the configured newline and indent are empty; otherwise it writes the configured newline and then repeats the configured indent once per enclosing scope above the document level.

<a id="u-09865727958f"></a>
### `JsonWriter.nullValue`

`@CanIgnoreReturnValue public JsonWriter nullValue() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L666-L679][f3]

Writes a JSON null, honoring deferred object names.

If a name is pending and null serialization is enabled, the name is written first; if disabled, the pending name is discarded and nothing is written. Otherwise it prepares the value position and writes null.

<a id="u-7ae7c2f67a79"></a>
### `JsonWriter.string`

`private void string(String value) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L743-L773][f3]

Writes a quoted JSON string with escaping.

It chooses the HTML-safe replacement table when enabled; that table additionally escapes <, >, &, =, and ' as Unicode escapes. The base table escapes control characters U+0000 through U+001F, quote, backslash, tab, backspace, newline, carriage return, and form feed; U+2028 and U+2029 are always escaped. Characters below 128 use the selected table, other characters pass through except those two line separators. It writes opening quote, unchanged chunks, replacements, and closing quote.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/FormattingStyle.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JsonTreeWriter.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonWriter.java
