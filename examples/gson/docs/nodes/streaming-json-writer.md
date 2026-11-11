# Streaming JSON writer

**Capability.** Emits RFC 8259 JSON token-by-token to a Writer, enforcing structural well-formedness, formatting, and value-encoding rules.

This module contains JsonWriter and FormattingStyle: scope-stack state machine, name/value emission, escaping (including HTML-safe mode), and indent/newline configuration. Readers implementing serialization output should start here.

Parent: [JSON Writing Infrastructure](json-writing-infrastructure.md)

## Units (30)

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

<a id="u-af2db411ac34"></a>
### `JsonWriter.java-array-and-object-delimiters-docs`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L388-L396][f2]

These regions document the structural delimiters: beginArray/beginObject each must be paired with a matching endArray/endObject; all four methods return the writer for chaining and may throw IOException.

<a id="u-c79bbeaf057e"></a>
### `JsonWriter.java-array-and-object-scope-operations`

`@CanIgnoreReturnValue public JsonWriter beginArray() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L406-L410][f2]

beginArray/beginObject flush any deferred name then open a scope: beforeValue writes separators, the scope is pushed, and '[' or '{' is written.

endArray/endObject delegate to closeScope, which throws IllegalStateException("Nesting problem.") if the top of stack is neither the matching empty nor nonempty scope, and IllegalStateException if a deferred name is still pending; it pops the scope, emits a newline before the closing bracket only when the scope was nonempty, then writes ']' or '}'. All return this and propagate IOException from the underlying writer.

<a id="u-a10b81ac3323"></a>
### `JsonWriter.java-float-and-double-value-docs`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L565-L577][f2]

These regions document the floating-point value methods: values must be finite unless strictness is LENIENT, which also permits NaN and infinities; otherwise an IllegalArgumentException is thrown.

The float overload exists since 2.9.1. Both return the writer.

<a id="u-bdb45dbae5a7"></a>
### `JsonWriter.java-formatting-configuration`

`public final void setIndent(String indent)` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L248-L254][f2]

setIndent is a convenience: an empty string selects FormattingStyle.COMPACT, otherwise PRETTY with the given indent, overwriting any prior style.

setFormattingStyle requires non-null (NPE otherwise) and caches derived data: formattedComma is "," plus a space only when the style uses space-after-separators and its newline is empty; formattedColon is ": " or ":" on the same condition; usesEmptyNewlineAndIndent is true only when both newline and indent are empty, letting newline() become a no-op. getFormattingStyle returns the current style.

<a id="u-8924031ef33e"></a>
### `JsonWriter.java-formatting-style-configuration-docs`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L224-L231][f2]

These documentation regions describe the formatting-style configuration of the writer: setting a non-null FormattingStyle controls indentation and newline style (cached internally for performance), and the getter returns the style currently in use.

The setter contract requires a non-null argument.

<a id="u-16584c181c13"></a>
### `JsonWriter.java-html-safety-docs`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L324-L345][f2]

These regions document HTML/XML safety: when enabled, the characters <, >, &, = and ' are escaped before being written so output can be embedded directly in HTML or XML; the getter reports whether this mode is active.

Default is off.

<a id="u-ba262b5360d9"></a>
### `JsonWriter.java-property-name-handling`

`@CanIgnoreReturnValue public JsonWriter name(String name) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L498-L510][f2]

name requires a non-null name (NPE otherwise), throws IllegalStateException if a name is already deferred ("Already wrote a name, expecting a value."), and IllegalStateException unless the current scope is EMPTY_OBJECT or NONEMPTY_OBJECT; it only stores the name, returning this.

writeDeferredName, called by value writers and scope openers, emits the separator via beforeName, writes the escaped name with string(), and clears the deferred field; it is a no-op when nothing is deferred.

<a id="u-bce0fd3e01a0"></a>
### `JsonWriter.java-scope-stack-helpers`

`private void push(int newTop)` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L472-L477][f2]

push doubles the int array (copyOf) when full before appending; peek throws IllegalStateException("JsonWriter is closed.") when the stack is empty; replaceTop overwrites the top entry without size change.

These maintain the JsonScope state machine that all structural validation reads.

<a id="u-21f89f7c62d0"></a>
### `JsonWriter.java-serialize-nulls-docs`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L357-L367][f2]

These regions document null serialization: the setter controls whether object members with null values are written (default true); it has no effect on array elements.

The getter returns the current setting.

<a id="u-ee90959a8a32"></a>
### `JsonWriter.java-simple-value-overloads`

`@CanIgnoreReturnValue public JsonWriter value(String value) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L526-L535][f2]

These overloads encode a value after flushing any deferred name and calling beforeValue.

value(String) and value(Boolean) map null to nullValue(). Booleans write "true"/"false". value(float) and value(double) throw IllegalArgumentException("Numeric values must be finite...") for NaN or infinity unless strictness is LENIENT, then append Float/Double.toString. value(long) writes Long.toString. All return this and propagate IOException.

<a id="u-20fca5de414c"></a>
### `JsonWriter.java-strictness-configuration-docs`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L254-L266][f2]

These regions document the strictness controls: the deprecated setLenient maps true to LENIENT and false to LEGACY_STRICT (callers of setLenient(false) are pointed to STRICT); isLenient reports whether strictness equals LENIENT.

setStrictness takes a non-null Strictness (default LEGACY_STRICT, where STRICT and LEGACY_STRICT behave identically and only RFC 8259 JSON is written); LENIENT additionally permits NaN, infinities, and multiple top-level values. getStrictness returns the current value.

<a id="u-d122b2c80531"></a>
### `JsonWriter`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L162-L165][f2]

Streaming writer that emits an RFC 8259 JSON value token-by-token to a java.io.Writer, tracking lexical scope on an int stack and enforcing structural well-formedness with IllegalStateException.

State includes the scope stack (initially containing EMPTY_DOCUMENT, grown by push), the current FormattingStyle with cached separator strings, a Strictness (default LEGACY_STRICT), htmlSafe and serializeNulls flags (defaults false and true), and a deferred property name. Instances are single-use per stream and not thread-safe; malformed sequences fail with IllegalStateException rather than producing invalid JSON.

<a id="u-fcbf13c19cb0"></a>
### `gson/src/main/java/com/google/gson/stream/JsonWriter.java:JsonWriter`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L179-L202][f2]

Constructor rejects a null Writer (NullPointerException from Objects.requireNonNull) and initializes formatting to FormattingStyle.COMPACT via setFormattingStyle.

The static initializer builds two escape tables: REPLACEMENT_CHARS escapes control characters U+0000–U+001F as \u00xx plus ", \, tab, backspace, newline, CR and form feed; HTML_SAFE_REPLACEMENT_CHARS clones it and additionally escapes <, >, &, = and ' for HTML/XML safety.

<a id="u-aa296878055a"></a>
### `gson/src/main/java/com/google/gson/stream/JsonWriter.java:JsonWriter (16)`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L490-L498][f2]

This region documents the property-name method: it encodes the name of the forthcoming value, requires a non-null argument, and returns the writer.

The name is deferred until the value is written.

<a id="u-0929c9fcb46e"></a>
### `gson/src/main/java/com/google/gson/stream/JsonWriter.java:JsonWriter (17)`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L518-L526][f2]

This region documents the string value method: a null argument encodes the JSON null literal; otherwise the literal string is encoded, quoted and escaped.

Returns the writer.

<a id="u-75c668b77db6"></a>
### `gson/src/main/java/com/google/gson/stream/JsonWriter.java:JsonWriter (24)`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L619-L632][f2]

This region documents the Number value method: the value's toString() is written directly, so implementations must produce a valid JSON number.

Null encodes the null literal. IllegalArgumentException is thrown for NaN/Infinity when not lenient, or when the toString() result is not a valid JSON number.

<a id="u-b742882bc5d1"></a>
### `gson/src/main/java/com/google/gson/stream/JsonWriter.java:JsonWriter (26)`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L679-L691][f2]

This region documents the null-literal method: it encodes JSON null and returns the writer.

<a id="u-42ec8c472062"></a>
### `gson/src/main/java/com/google/gson/stream/JsonWriter.java:JsonWriter (32)`

`class JsonWriter implements Closeable, Flushable` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L799-L805][f2]

This region documents the internal beforeValue helper: it inserts any necessary separators and whitespace before a literal value, inline array, or inline object, and adjusts the scope stack to expect either a closing bracket or another element.

<a id="u-72f261060659"></a>
### `JsonWriter.alwaysCreatesValidJsonNumber`

`private static boolean alwaysCreatesValidJsonNumber(Class<? extends Number> c)` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L730-L741][f2]

Static predicate listing Number classes whose toString() is guaranteed to be a valid JSON number: Integer, Long, Byte, Short, BigDecimal, BigInteger, AtomicInteger, AtomicLong.

Float and Double are excluded because they can produce NaN/Infinity, and LazilyParsedNumber because it may wrap a malformed string; value(Number) uses this to decide whether validation is needed.

<a id="u-d0ef08a1ce43"></a>
### `JsonWriter.beforeName`

`private void beforeName() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L790-L799][f2]

Inserts separators before a property name: if the scope is NONEMPTY_OBJECT it writes the cached comma, else if the scope is not EMPTY_OBJECT it throws IllegalStateException("Nesting problem.").

It then emits a newline and replaces the top scope with DANGLING_NAME so the next value is treated as the name's value.

<a id="u-ad1b67731900"></a>
### `JsonWriter.beforeValue`

`@SuppressWarnings("fallthrough") private void beforeValue() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L805-L835][f2]

Inserts separators before any value and advances the scope state machine via a switch on peek().

NONEMPTY_DOCUMENT throws IllegalStateException("JSON must have only one top-level value.") unless LENIENT, then falls through to EMPTY_DOCUMENT, which replaces the top with NONEMPTY_DOCUMENT. EMPTY_ARRAY becomes NONEMPTY_ARRAY with a newline; NONEMPTY_ARRAY writes the cached comma then a newline; DANGLING_NAME writes the cached colon and replaces the top with NONEMPTY_OBJECT. Any other scope (EMPTY_OBJECT, NONEMPTY_OBJECT, CLOSED) hits default and throws IllegalStateException("Nesting problem.").

<a id="u-f4c5ccc43d0e"></a>
### `JsonWriter.close`

`@Override public void close() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L718-L727][f2]

Closes the underlying Writer first, then validates completeness: it throws IOException("Incomplete document") if more than one scope remains on the stack, or if exactly one remains and it is not NONEMPTY_DOCUMENT (i.e., no top-level value was completed).

On success the stack is emptied, marking the writer closed; note the underlying writer is closed even when the document is incomplete.

<a id="u-6d507e7579af"></a>
### `JsonWriter.flush`

`@Override public void flush() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L705-L711][f2]

Flushes the underlying Writer, but only if the writer is not closed: it throws IllegalStateException("JsonWriter is closed.") when the scope stack is empty, then delegates to out.flush(), propagating IOException.

<a id="u-9480bc3f4b32"></a>
### `JsonWriter.jsonValue`

`@CanIgnoreReturnValue public JsonWriter jsonValue(String value) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L691-L700][f2]

Writes the given string verbatim without quoting or escaping after flushing a deferred name and calling beforeValue; null delegates to nullValue().

Because no validation is performed, the caller is responsible for producing valid JSON; subclasses may override to throw UnsupportedOperationException per the contract.

<a id="u-b48d57328999"></a>
### `JsonWriter.newline`

`private void newline() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L775-L784][f2]

Emits the formatting style's newline followed by one indent string per enclosing scope (loop from 1 to stackSize-1, so the current innermost level gets no indent).

It is a no-op when the cached usesEmptyNewlineAndIndent is true, i.e. the style has both empty newline and empty indent (compact output).

<a id="u-09865727958f"></a>
### `JsonWriter.nullValue`

`@CanIgnoreReturnValue public JsonWriter nullValue() throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L666-L679][f2]

Encodes a null literal, honoring the deferred-name and serializeNulls interaction: if a name is deferred and serializeNulls is true the name is written then "null"; if false, both the name and the value are silently skipped (the deferred name is cleared and this returned); with no deferred name it writes separators via beforeValue then "null".

<a id="u-7ae7c2f67a79"></a>
### `JsonWriter.string`

`private void string(String value) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L743-L773][f2]

Writes a JSON string literal with escaping: selects the HTML-safe or standard replacement table based on the htmlSafe flag, wraps the value in double quotes, and for each character either emits a replacement (control chars, quote, backslash, and the JavaScript line separators U+2028/U+2029) or passes it through.

Unescaped runs are written in bulk segments between replacements for efficiency; characters >= 128 other than U+2028/U+2029 are written unchanged.

<a id="u-cf4e50d729d7"></a>
### `gson/src/main/java/com/google/gson/stream/JsonWriter.java:JsonWriter.value (6)`

`@CanIgnoreReturnValue public JsonWriter value(Number value) throws IOException` · [gson/src/main/java/com/google/gson/stream/JsonWriter.java:L632-L659][f2]

Encodes a Number by writing its toString() directly, mapping null to nullValue().

For classes not in the trusted set (Integer, Long, Byte, Short, BigDecimal, BigInteger, AtomicInteger, AtomicLong), the string is validated: "-Infinity", "Infinity" or "NaN" throw IllegalArgumentException unless strictness is LENIENT; for any other non-Float/Double class a string not matching the RFC 8259 number pattern throws IllegalArgumentException naming the class. Trusted classes and Float/Double skip pattern validation, so a custom Number subclass with a well-formed toString is accepted while a malformed one is rejected before any output is written.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/FormattingStyle.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/JsonWriter.java
