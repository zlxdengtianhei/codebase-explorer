# Built-in JDK Type Adapters

**Capability.** Provides Gson's stock TypeAdapters and factory helpers for basic JDK types like numbers, strings, atomics, Locale, UUID and InetAddress.

Come here for the default serialization behavior of primitive wrappers, atomic types, and common JDK value classes. The module also contains factory combinators for exact-type, boxed-type, and subtype matching, plus troubleshooting-guide URL construction for unsupported types like Class.

**Depends on.**

- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-only · 3 edge(s)

**Depended on by.**

- [Exclusion Strategies and Builder](exclusion-strategies-and-builder.md) · graph-only · 2 edge(s)
- [Generic Type Reflection](generic-type-reflection.md) · graph-only · 2 edge(s)
- [Token consumption and value decoding](token-consumption-and-value-decoding.md) · graph-only · 2 edge(s)

Parent: [Built-in Adapter Implementations](built-in-adapter-implementations.md)

## Units (30)

<a id="u-013a59f1aa5f"></a>
### `TypeAdapters.java-atomic-boolean-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L323-L327][f1]

Reads a boolean into AtomicBoolean and writes value.get(); nullSafe wrapper handles nulls, and no parse-error wrapping is done.

<a id="u-232be009c8a2"></a>
### `TypeAdapters.java-atomic-integer-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L288-L292][f1]

Reads an int and wraps it in AtomicInteger, wrapping NumberFormatException as JsonSyntaxException; write emits value.get().

nullSafe, so null reads/writes are handled by the wrapper.

<a id="u-ebb5bc85c5f4"></a>
### `TypeAdapters.java-atomic-integer-array-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L335-L337][f1]

Reads a JSON array of ints into an AtomicIntegerArray, wrapping per-element NumberFormatException as JsonSyntaxException; write emits each element as a JSON array.

nullSafe.

<a id="u-154865415faa"></a>
### `TypeAdapters.java-bitset-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L90-L94][f1]

Serializes a BitSet as a JSON array of 0/1 integers.

read accepts NUMBER, STRING (coerced via nextInt) and BOOLEAN elements; values other than 0 or 1 throw JsonSyntaxException with the previous path, and any other token type throws with the current path. nullSafe wrapper handles nulls.

<a id="u-47b14cfef503"></a>
### `TypeAdapters.java-boolean-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L146-L150][f1]

Reads booleans: null token returns null, STRING tokens are parsed with Boolean.parseBoolean for GSON 1.7 compatibility, otherwise nextBoolean.

Writes the boolean value directly; not nullSafe, so a null value reaches JsonWriter.

<a id="u-f5de9e08bdf2"></a>
### `TypeAdapters.java-boolean-as-string-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L166-L174][f1]

Boolean adapter for map keys: read parses a string via Boolean.valueOf (null token returns null); write emits the string "null" for null and toString otherwise, since JSON object names must be strings.

<a id="u-4d48e6fffe9d"></a>
### `TypeAdapters.java-byte-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L190-L194][f1]

Reads an int, returning null for a null token; NumberFormatException from nextInt becomes JsonSyntaxException.

Accepts values from Byte.MIN_VALUE up to 255 (unsigned support); anything outside throws a lossy-conversion JsonSyntaxException. Returns a Byte; write emits byteValue() or null.

<a id="u-fdd4f7065e50"></a>
### `TypeAdapters.java-calendar-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L897-L903][f1]

IntegerFieldsTypeAdapter for Calendar over fields year, month, dayOfMonth, hourOfDay, minute, second.

create builds a GregorianCalendar from the values using toIntExact (an out-of-int-range value throws ArithmeticException); integerValues extracts the same six Calendar getters.

<a id="u-d4a247df6b60"></a>
### `TypeAdapters.java-character-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L533-L537][f1]

Reads a string and requires length exactly 1, otherwise throws JsonSyntaxException with the string and previous path; null token returns null.

write emits the single-character string, or null for null.

<a id="u-21a172d880ed"></a>
### `TypeAdapters.java-class-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L66-L71][f1]

TypeAdapter for java.lang.Class whose read and write both throw UnsupportedOperationException with a troubleshooting-guide URL, reminding users to register a custom adapter; wrapped nullSafe so nulls are handled before the exception.

<a id="u-cec7e942cbae"></a>
### `TypeAdapters.java-currency-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L824-L828][f1]

Reads a currency code string and resolves it with Currency.getInstance, wrapping IllegalArgumentException in a JsonSyntaxException; write emits getCurrencyCode.

nullSafe wrapper handles nulls, so read assumes a non-null token.

<a id="u-a25f362cb166"></a>
### `TypeAdapters.java-factorysupplier`

`interface FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L976-L977][f1]

Internal interface providing a TypeAdapterFactory via get(); used to load the optional java.time adapter factory reflectively.

<a id="u-ea1cf3373559"></a>
### `TypeAdapters.java-inet-address-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L759-L768][f1]

Reads a string and, unless it matches the permissive IP-address pattern (contains a colon, or four dot-separated numeric groups) or the system property gson.allowDnsInetAddress is true, throws JsonSyntaxException explaining how to allow DNS names.

It then resolves via InetAddress.getByName. write emits getHostAddress() or null.

<a id="u-5768a0c33705"></a>
### `TypeAdapters.java-integer-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L261-L265][f1]

Reads an Integer via nextInt (null token returns null; NumberFormatException wrapped in JsonSyntaxException) and writes intValue() or null.

<a id="u-c05cd843e775"></a>
### `TypeAdapters.java-integerfieldstypeadapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L844-L851][f1]

Abstract adapter for types serialized as a fixed set of integer fields (used by Calendar and legacy java.time).

The constructor takes the field names. read: null token returns null; otherwise reads an object, filling values by field-name index and skipping unknown names, then calls the abstract create(long[]). write: null writes null; otherwise calls abstract integerValues(T) and writes each field name with its long value. Subclasses supply create and integerValues.

<a id="u-d92d81020862"></a>
### `TypeAdapters.java-locale-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L928-L932][f1]

Reads an underscore-separated string and splits it into language, country and variant tokens, constructing a Locale with as many parts as present (null token returns null).

write emits toString() or null.

<a id="u-242103392268"></a>
### `TypeAdapters.java-long-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L409-L413][f1]

Reads a Long via nextLong (null token returns null; NumberFormatException wrapped as JsonSyntaxException) and writes longValue() or null.

<a id="u-ce9d9e704f21"></a>
### `TypeAdapters.java-long-as-string-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L433-L438][f1]

Like LONG for reading, but write emits value.toString() instead of a numeric literal, preserving the original textual form; null writes null.

<a id="u-c3e151ccfcd0"></a>
### `TypeAdapters.java-newfactory-typetoken`

`@SuppressWarnings("TypeParameterNaming") public static <TT> TypeAdapterFactory newFac…` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L992-L996][f1]

Returns a factory whose create yields the given adapter only when the requested TypeToken equals the captured token, else null.

<a id="u-31921b0a8a02"></a>
### `TypeAdapters.java-newfactoryformultipletypes`

`@SuppressWarnings("TypeParameterNaming") public static <TT> TypeAdapterFactory newFac…` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L1044-L1048][f1]

Returns a factory matching either the base or the subtype raw type exactly and returning the shared adapter, else null; toString lists both class names.

<a id="u-15558103439d"></a>
### `TypeAdapters.java-newtypehierarchyfactory`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L1066-L1072][f1]

Returns a factory for all subtypes of the given class: create returns null unless the requested raw type is assignable to the class, otherwise it wraps the adapter in a delegating TypeAdapter.

The wrapper's read applies a runtime check — a non-null result that is not an instance of the requested type throws JsonSyntaxException naming both classes and the previous path; write simply delegates. toString identifies the hierarchy and adapter.

<a id="u-61d8ee062ab6"></a>
### `TypeAdapters.java-short-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L225-L229][f1]

Same pattern as the byte adapter but with the range Short.MIN_VALUE..65535; out-of-range values throw a lossy-conversion JsonSyntaxException, parse failures wrap as JsonSyntaxException, and write emits shortValue() or null.

<a id="u-1af03dfecaeb"></a>
### `TypeAdapters.java-string-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L564-L568][f1]

Reads strings: null token returns null, BOOLEAN tokens are coerced to "true"/"false" for backward compatibility, otherwise nextString.

write passes the value straight to JsonWriter.

<a id="u-06f9e728d4c8"></a>
### `TypeAdapters.java-string-buffer-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L683-L687][f1]

Reads a string into a new StringBuffer (null token returns null); write emits toString() or null.

<a id="u-fc45edaee468"></a>
### `TypeAdapters.java-string-builder-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L663-L667][f1]

Reads a string into a new StringBuilder (null token returns null); write emits toString() or null.

<a id="u-a7f7d5f399ec"></a>
### `TypeAdapters.java-uri-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L731-L735][f1]

Reads a string; the literal "null" maps to null, URISyntaxException becomes a JsonSyntaxException with input and previous path, and a null token returns null.

write emits toString() or null.

<a id="u-036887cbf8ae"></a>
### `TypeAdapters.java-url-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L703-L707][f1]

Reads a string; the literal "null" maps to null, MalformedURLException becomes a JsonSyntaxException with input and previous path, and a null token returns null.

write emits toExternalForm() or null.

<a id="u-fe0375b5fa0b"></a>
### `TypeAdapters.java-uuid-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L799-L803][f1]

Reads a string and parses it with UUID.fromString, wrapping IllegalArgumentException in a JsonSyntaxException with input and previous path; null token returns null.

write emits toString() or null.

<a id="u-aa0852b1012e"></a>
### `TroubleshootingGuide.createUrl`

`public static String createUrl(String id)` · [gson/src/main/java/com/google/gson/internal/TroubleshootingGuide.java:L7-L9][f2]

Builds a URL pointing at the given anchor in Gson's Troubleshooting.md on GitHub by simple string concatenation.

<a id="u-d8f65492684f"></a>
### `TypeAdapters`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L63-L64][f1]

Utility class of built-in TypeAdapters and factory helpers for basic JDK types; its constructor throws UnsupportedOperationException to prevent instantiation.

Complex adapters live in separate classes in the same package.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/TroubleshootingGuide.java
