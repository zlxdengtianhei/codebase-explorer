# Public API utility classes

**Capability.** Provides public API helpers and types for fields, naming, parsing, contexts, exceptions, strictness, and factories.

Use for public utility and API surface behavior. Units show FieldAttributes, naming policies, JsonParser, stream parser, exceptions, strictness, and module exports.

**Depends on.**

- [Gson serialization facade](gson-serialization-facade.md) · graph-only · 3 edge(s)
- [Stream serialization helpers](stream-serialization-helpers.md) · graph-only · 2 edge(s)

Parent: [Public utilities and dates](public-utilities-and-dates.md)

## Units (21)

<a id="u-749a76fde0e8"></a>
### `FieldAttributes.java-fieldattributes`

`class FieldAttributes` · [gson/src/main/java/com/google/gson/FieldAttributes.java:L35-L36][f1]

Immutable, thread-safe wrapper exposing reflective attributes of a single java.lang.reflect.Field.

The constructor rejects a null field via Objects.requireNonNull. Accessors delegate directly to the wrapped Field: getDeclaringClass/getName return identity metadata, getDeclaredType returns the generic type (parameterized types preserved), getDeclaredClass returns the raw Class, getAnnotation returns the annotation of the given type or null, getAnnotations returns a fixed-size list wrapper over the field's annotations, hasModifier tests a bitmask against the field's modifiers, and toString returns the field's own string.

<a id="u-0f6f712f347f"></a>
### `FieldAttributes.java-fieldattributes-reflective-accessors`

`class FieldAttributes` · [gson/src/main/java/com/google/gson/FieldAttributes.java:L63-L84][f1]

These class regions of FieldAttributes each wrap one reflective accessor that delegates to the stored java.lang.reflect.Field: getDeclaredType returns the field's generic type (preserving parameterization, e.g. List<String>), getDeclaredClass returns the raw Class, getAnnotation returns the field's annotation of the requested type or null, getAnnotations returns a fixed-size list view of all field annotations, and hasModifier tests the field's modifier bits against the given mask with a non-zero bitwise AND.

All are pure queries over the immutable field reference; none validate or transform beyond the underlying reflection call.

<a id="u-9f9b24b07602"></a>
### `FieldNamingPolicy.java-field-naming-policies`

`@Override public String translateName(Field f)` · [gson/src/main/java/com/google/gson/FieldNamingPolicy.java:L35-L38][f2]

These enum policies translate a Java field name to a JSON field name.

Identity returns the name unchanged; upper camel case uppercases the first letter; upper camel case with spaces separates camel-case words with spaces then uppercases the first letter; upper case with underscores separates with '_' then uppercases all letters; lower case with underscores separates with '_' then lowercases; lower case with dashes separates with '-' then lowercases; lower case with dots separates with '.' then lowercases. Case conversion uses Locale.ENGLISH. For a name like aURL, lower underscore gives a_u_r_l, upper underscore gives A_U_R_L, dash gives a-u-r-l, and dot gives a.u.r.l.

<a id="u-243769b227ba"></a>
### `JsonDeserializationContext.java-deserialization-context`

`public interface JsonDeserializationContext` · [gson/src/main/java/com/google/gson/JsonDeserializationContext.java:L28-L42][f3]

Deserialization context interface passed to a custom deserializer; its single method invokes default deserialization for a parse tree and target type, returning an object of that type.

It declares a parse exception when the tree lacks expected data. The documentation warns not to call it on the element received by the custom deserializer because that would re-enter the custom deserializer and loop. No implementation is present here.

<a id="u-063847ba8112"></a>
### `JsonIOException.java-json-i-o-exception`

`class name is part of the public API public final class JsonIOException extends JsonP…` · [gson/src/main/java/com/google/gson/JsonIOException.java:L24-L26][f4]

Final exception class extending its superclass.

Three constructors pass a message, a message plus cause, or a cause to the superclass; no additional state is introduced in these symbols.

<a id="u-66f61d122b74"></a>
### `JsonNull.java-null-value-singleton`

`class JsonNull extends JsonElement` · [gson/src/main/java/com/google/gson/JsonNull.java:L26-L32][f5]

Final value class extending JsonElement.

The deprecated public constructor does nothing; deepCopy returns the shared instance; hashCode returns the class hash; equals returns true for any instance of this class. Thus all instances compare equal and share one hash code, while deepCopy may return a different instance than the receiver.

<a id="u-bb8aa7e508d6"></a>
### `JsonParseException.java-base-parse-exception`

`class JsonParseException extends RuntimeException` · [gson/src/main/java/com/google/gson/JsonParseException.java:L32-L33][f6]

Unchecked exception class extending RuntimeException.

Three constructors pass a message, a message plus cause, or a cause to the superclass; no other behavior or state is defined in these symbols.

<a id="u-7c09129e5edc"></a>
### `JsonParser.java-jsonparser-entry-points-and-deprecated-methods`

`class JsonParser` · [gson/src/main/java/com/google/gson/JsonParser.java:L73-L77][f7]

Static facade for parsing JSON into JsonElement trees.

parseString wraps the string in a StringReader and delegates to parseReader(Reader). The class's public constructor and the three instance parse methods are deprecated; each parse overload simply forwards to its static counterpart (parseString, parseReader(Reader), parseReader(JsonReader)).

<a id="u-331ccd417571"></a>
### `JsonParser.java-jsonparser-parsereader-variants`

`class JsonParser` · [gson/src/main/java/com/google/gson/JsonParser.java:L78-L91][f7]

These class regions of JsonParser contain the two parseReader implementations plus the deprecated parse(Reader) bridge.

parseReader(Reader) wraps the reader in a JsonReader, delegates to parseReader(JsonReader), and then enforces single-document input: if the parsed element is not JSON null and the reader's next token is not END_DOCUMENT it throws JsonSyntaxException for trailing data; MalformedJsonException and NumberFormatException are converted to JsonSyntaxException and IOException to JsonIOException. parseReader(JsonReader) reads one value from an existing reader via Streams.parse: if the reader's strictness is LEGACY_STRICT it temporarily switches to LENIENT, catches StackOverflowError/OutOfMemoryError as JsonParseException, and restores the original strictness in finally. The deprecated parse(Reader) simply forwards to parseReader(Reader).

<a id="u-893f451167b0"></a>
### `JsonSerializationContext.java-serialization-context`

`public interface JsonSerializationContext` · [gson/src/main/java/com/google/gson/JsonSerializationContext.java:L28-L36][f8]

Serialization context interface with two overloads that invoke default serialization and return a tree of elements.

The no-type overload serializes the object directly; the typed overload accepts generic type information. The typed overload's documentation warns not to call it on the element received by a custom serializer because that would re-enter the custom serializer and loop. No implementation is present here.

<a id="u-5cdbb7a14ba5"></a>
### `JsonStreamParser.java-jsonstreamparser`

`class JsonStreamParser implements Iterator<JsonElement>` · [gson/src/main/java/com/google/gson/JsonStreamParser.java:L51-L52][f9]

Iterator<JsonElement> that reads multiple concatenated JSON values from a Reader or String in lenient mode; conditionally thread-safe, requiring external synchronization across threads.

hasNext() synchronizes on an internal lock, peeks the reader, and returns true unless the token is END_DOCUMENT; MalformedJsonException becomes JsonSyntaxException and IOException becomes JsonIOException. next() first checks hasNext() and throws NoSuchElementException when exhausted, then parses one element via Streams.parse, converting StackOverflowError/OutOfMemoryError to JsonParseException. remove() always throws UnsupportedOperationException.

<a id="u-b6102efda8ea"></a>
### `JsonStreamParser.java-jsonstreamparser-iterator-core`

`class JsonStreamParser implements Iterator<JsonElement>` · [gson/src/main/java/com/google/gson/JsonStreamParser.java:L71-L82][f9]

These class regions of JsonStreamParser contain the iterator core.

next() first checks hasNext(); if no element remains it throws NoSuchElementException, otherwise it parses one value via Streams.parse, converting StackOverflowError/OutOfMemoryError to JsonParseException. hasNext() synchronizes on an internal lock and returns whether the reader's peek is not END_DOCUMENT, converting MalformedJsonException to JsonSyntaxException and IOException to JsonIOException. remove() is unconditionally unsupported and throws UnsupportedOperationException. Note next() calls hasNext() (which locks) but its own parse is not synchronized, so cross-thread use still requires external synchronization as documented.

<a id="u-3fc443006932"></a>
### `JsonSyntaxException.java-syntax-exception`

`class JsonSyntaxException extends JsonParseException` · [gson/src/main/java/com/google/gson/JsonSyntaxException.java:L24-L26][f10]

Final exception class extending its superclass.

Three constructors pass a message, a message plus cause, or a cause to the superclass; no other behavior or state is defined in these symbols.

<a id="u-a19533384685"></a>
### `MalformedJsonException.java-malformedjsonexception`

`class MalformedJsonException extends IOException` · [gson/src/main/java/com/google/gson/stream/MalformedJsonException.java:L26-L27][f11]

Final IOException subtype used to report malformed JSON.

Its three constructors forward a message, a message plus cause, or a cause to the corresponding IOException constructor; it adds no other state beyond a fixed serial version.

<a id="u-f62cb9a19af0"></a>
### `FieldNamingPolicy.separateCamelCase`

`static String separateCamelCase(String name, char separator)` · [gson/src/main/java/com/google/gson/FieldNamingPolicy.java:L179-L189][f2]

Builds a new string by inserting the separator before each uppercase character except when it would be the first output character, then appending the character.

It preserves original character case and does not split on digits or lowercase transitions. Returns the transformed string.

<a id="u-e1b81b3e2980"></a>
### `FieldNamingPolicy.upperCaseFirstLetter`

`static String upperCaseFirstLetter(String s)` · [gson/src/main/java/com/google/gson/FieldNamingPolicy.java:L192-L212][f2]

Scans for the first letter in the string.

If that letter is already uppercase, returns the original string unchanged; if lowercase, replaces only that character with its uppercase form and returns the result. If no letter is found, returns the original string. The rest of the string is not altered.

<a id="u-ec3cb47a826f"></a>
### `JsonParser.parseReader`

`public static JsonElement parseReader(Reader reader) throws JsonIOException, JsonSynt…` · [gson/src/main/java/com/google/gson/JsonParser.java:L107-L120][f7]

Parses an entire Reader into a JsonElement, rejecting trailing or multiple top-level elements.

It wraps the reader in a JsonReader, delegates to parseReader(JsonReader), and if the result is not JSON null and the reader's next token is not END_DOCUMENT, throws JsonSyntaxException("Did not consume the entire document."). MalformedJsonException and NumberFormatException are converted to JsonSyntaxException; IOException is converted to JsonIOException.

<a id="u-a100555ee735"></a>
### `gson/src/main/java/com/google/gson/JsonParser.java:JsonParser.parseReader`

`public static JsonElement parseReader(JsonReader reader) throws JsonIOException, Json…` · [gson/src/main/java/com/google/gson/JsonParser.java:L136-L150][f7]

Parses the next value from a JsonReader as a tree, allowing multiple top-level elements and trailing data.

If the reader's strictness is LEGACY_STRICT it temporarily switches to LENIENT for backward compatibility; other strictness values (including STRICT) are used as-is. It delegates to Streams.parse, converts StackOverflowError/OutOfMemoryError to JsonParseException, and in a finally block restores the reader's original strictness.

<a id="u-bfab23ee9e5a"></a>
### `Strictness`

`public enum Strictness` · [gson/src/main/java/com/google/gson/Strictness.java:L20-L29][f12]

Enum of three strictness modes: LENIENT allows large deviations from the JSON specification, LEGACY_STRICT allows certain small deviations for legacy reasons, and STRICT requires strict compliance.

No methods or state are defined.

<a id="u-c58ad34373b0"></a>
### `TypeAdapterFactory.create`

`<T> TypeAdapter<T> create(Gson gson, TypeToken<T> type);` · [gson/src/main/java/com/google/gson/TypeAdapterFactory.java:L170-L170][f13]

Factory interface producing TypeAdapter instances for related types; create(Gson, TypeToken<T>) returns an adapter for the requested type or null when the factory does not support it.

Factories are called for many types and must return null for unsupported ones; they are registered with GsonBuilder, where earlier registrations take precedence, and should perform expensive reflection eagerly in create so the returned adapter's read/write stay fast.

<a id="u-a76a3a49ccfe"></a>
### `module-info.java module code (L1–L36)`

`module_region` · [gson/src/main/java/module-info.java:L1-L36][f14]

Declares the com.google.gson module, exporting four public API packages and marking three dependencies as static.

It exports com.google.gson, com.google.gson.annotations, com.google.gson.reflect, and com.google.gson.stream. It declares static requirements on com.google.errorprone.annotations, java.sql, and jdk.unsupported; these are compile-time module dependencies declared optional at runtime, but the descriptor alone does not establish that runtime code paths avoid or tolerate their absence.

**Notes.**

- contract: The module exports exactly the four listed packages and declares no opens, uses, provides, or transitive requirements.

**Uncertainties.**

- Whether runtime code actually uses or safely handles absence of the three static dependencies is not shown by this descriptor.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/FieldAttributes.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/FieldNamingPolicy.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonDeserializationContext.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonIOException.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonNull.java
[f6]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonParseException.java
[f7]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonParser.java
[f8]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonSerializationContext.java
[f9]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonStreamParser.java
[f10]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonSyntaxException.java
[f11]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/stream/MalformedJsonException.java
[f12]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/Strictness.java
[f13]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/TypeAdapterFactory.java
[f14]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/module-info.java
