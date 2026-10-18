# Primitive and Utility Type Adapters

**Capability.** TypeAdapters' static adapters and factory helpers for numbers (integer-like, float/double, big numbers), strings/characters, boolean/BitSet/Class, network/identity types (URL, URI, InetAddress, UUID, Currency), Calendar/Locale/enum/JsonElement aliases, plus the reusable factory-construction helpers.

Look here for the default mappings of JDK scalar and utility types and for the newFactory helpers every other factory uses. IntegerFieldsTypeAdapter's family and the optional java.time factory are wired from here into the builder's pipeline.

**Depends on.**

- [Runtime Generic Type Model](r1-type-model.md) · graph-only · 5 edge(s)
- [TypeAdapter Framework](r1-adapter-framework.md) · graph-only · 2 edge(s)
- [Internal Support Utilities](r1-internal-support.md) · graph-only · 2 edge(s)
- [Internal Utilities and Data Structures](r2-infrastructure.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Builder and Naming Configuration](r2-configuration.md) · graph-only · 9 edge(s)

Parent: [Built-in Type Adapter Factories](r2-default-adapters.md)

## Units (8)

<a id="u-5bbd44975629"></a>
### `typeadapters-big-numbers`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L585-L590][f1]

Groups the arbitrary-precision and deferred number adapters.

BIG_DECIMAL reads null to null, takes nextString, and parses via NumberLimits.parseBigDecimal; NumberFormatException is rethrown as JsonSyntaxException quoting the input and path. It writes the BigDecimal directly. BIG_INTEGER mirrors this with NumberLimits.parseBigInteger and writes the BigInteger. LAZILY_PARSED_NUMBER reads null to null else wraps nextString in a LazilyParsedNumber and writes the value directly; it exists for corner cases where this internal type is deserialized.

calls: [NumberLimits.parseBigDecimal](r1-internal-support.md#u-5f49b1496f23), [NumberLimits.parseBigInteger](r1-internal-support.md#u-513e7aece357)

**Uncertainties.**

- The additional limits NumberLimits enforces (e.g. magnitude restrictions) are defined outside this file.

<a id="u-09f7deced4ac"></a>
### `typeadapters-calendar-locale`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L897-L903][f1]

Groups the CALENDAR and LOCALE adapters plus the JsonElement/enum factory aliases.

CALENDAR extends IntegerFieldsTypeAdapter with fields year, month, dayOfMonth, hourOfDay, minute, second; create builds a GregorianCalendar using toIntExact on each value, so out-of-int-range components throw ArithmeticException, and integerValues extracts the matching Calendar fields. It is registered via newFactoryForMultipleTypes for Calendar and GregorianCalendar. LOCALE reads null to null, then splits the string on '_' into up to language, country, and variant, constructing a one-, two-, or three-argument Locale depending on which tokens are absent; a null language token (empty string) passes through to the Locale constructor. It writes toString or null. JSON_ELEMENT and ENUM_FACTORY simply alias JsonElementTypeAdapter.ADAPTER and EnumTypeAdapter.FACTORY.

**Uncertainties.**

- LOCALE read can pass null language to Locale when the string has no tokens; the resulting Locale is defined by the JDK, not this code.

<a id="u-c63756106113"></a>
### `typeadapters-char-string`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L527-L537][f1]

Groups the CHARACTER, STRING, StringBuilder, and StringBuffer adapters.

CHARACTER reads null to null and otherwise requires nextString to have length exactly 1, throwing JsonSyntaxException with the string, its length, and the path otherwise; it writes the character as a one-character string. STRING reads null to null, coerces JSON booleans to "true"/"false" for backward compatibility, else nextString, and writes the string as-is. STRING_BUILDER and STRING_BUFFER read null to null else wrap nextString in the respective type, and write toString or null.

<a id="u-f7009b97fbde"></a>
### `typeadapters-class-bitset-boolean`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L66-L71][f1]

Groups the Class, BitSet, Boolean, and boolean-as-string adapters of TypeAdapters.

CLASS never transfers data: write and read both throw UnsupportedOperationException naming the type and a TroubleshootingGuide URL, wrapped nullSafe so null still passes as null. BIT_SET reads a JSON array of numbers, booleans, or strings where each element must be 0/1 (number or string via nextInt) or a boolean; other values or token types throw JsonSyntaxException with the path, and set bits mark their index. It writes only up to src.length() as 1/0 values, nullSafe. BOOLEAN reads null, parses strings via Boolean.parseBoolean for GSON 1.7 compatibility, else nextBoolean, and writes the boolean directly. BOOLEAN_AS_STRING reads null or Boolean.valueOf(nextString) and writes "null" or the boolean's toString, supporting map keys.

calls: [TroubleshootingGuide](r2-infrastructure.md#u-9bcd073a2728)

<a id="u-434284f4fe08"></a>
### `typeadapters-factory-helpers`

`interface FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L976-L977][f1]

Groups the TypeAdapterFactory construction helpers.

The two single-type newFactory overloads return factories whose create returns the adapter only when the requested TypeToken equals the exact token or its raw type equals the exact class (with an unchecked cast), and null otherwise; the class variant also overrides toString as Factory[type=...,adapter=...]. The (unboxed, boxed) overload matches either primitive or wrapper raw type. newFactoryForMultipleTypes matches a base class or one specific subclass raw type. newTypeHierarchyFactory matches any raw type assignable from clazz and returns an adapter delegating write directly; its read delegates, then rejects non-null results that are not instances of the originally requested type with JsonSyntaxException, preventing a broader type from leaking. FactorySupplier is the single-method interface (get) the reflective java.time loader implements.

calls: [type-token-class](r1-type-model.md#u-55a9c25d6eea)

**Uncertainties.**

- The unchecked casts in create rely on the comment's stated runtime checks; whether a mismatched registration can still slip through depends on callers outside this file.

<a id="u-5b8e9989a17b"></a>
### `typeadapters-float-double`

`class FloatAdapter extends TypeAdapter<Number>` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L457-L460][f1]

Groups FloatAdapter, DoubleAdapter, and their strict/non-strict instances.

Both adapters read null to null, otherwise parse as double (FloatAdapter casts to float) with no validation on read. On write, null yields a JSON null; if the strict flag is set, checkValidFloatingPoint rejects NaN or infinite values with IllegalArgumentException pointing to GsonBuilder.serializeSpecialFloatingPointValues. Non-strict FLOAT and DOUBLE skip that check. FloatAdapter deliberately avoids JsonWriter.value(float), writing the original Float instance (or the float widened to Number) for backward compatibility with custom JsonWriter implementations.

<a id="u-3e7ac8874b8d"></a>
### `typeadapters-integer-like`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L186-L194][f1]

Groups adapters whose values are 32-bit or 64-bit integers and their atomic wrappers.

BYTE and SHORT read via nextInt (wrapping NumberFormatException into JsonSyntaxException), accept unsigned ranges up to 255/65535 plus the signed minimum, and throw JsonSyntaxException on lossy values; they write null or the narrowed value. INTEGER reads nextInt with the same NumberFormatException wrapping; ATOMIC_INTEGER is nullSafe and wraps the int. atomicLongAdapter(longAdapter) requires a non-null Number adapter (Objects.requireNonNull) and returns a nullSafe adapter delegating reads/writes to it, converting via longValue. ATOMIC_BOOLEAN is nullSafe and reads nextBoolean. ATOMIC_INTEGER_ARRAY reads a JSON array of ints into an AtomicIntegerArray (NumberFormatException becomes JsonSyntaxException) and writes each element. atomicLongArrayAdapter similarly delegates each element to the supplied long adapter but rejects null elements with JsonSyntaxException. LONG reads nextLong with NumberFormatException wrapping and writes longValue; LONG_AS_STRING writes value.toString() as a JSON string while still reading via nextLong, for map-key use.

uses: [TypeAdapter.nullSafe](r1-adapter-framework.md#u-c7dd40fc556f)

**Uncertainties.**

- BYTE/SHORT accept out-of-signed-range values (e.g. 200) that undergo silent narrowing on write; the exact returned byte/short for those is implied by Java casts.

<a id="u-9ff899f358da"></a>
### `typeadapters-net-id`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L699-L707][f1]

Groups URL, URI, InetAddress, UUID, and Currency adapters.

URL and URI read null to null and also map the literal string "null" to a null object; malformed input throws JsonSyntaxException quoting the string and path (MalformedURLException / URISyntaxException as cause); they write toExternalForm/toString or null. INET_ADDRESS reads null to null, then matches the string against a permissive pattern accepting dotted-quad IPv4 or anything containing a colon (IPv6); a non-match fails with JsonSyntaxException unless system property gson.allowDnsInetAddress is "true", after which InetAddress.getByName resolves the string — meaning DNS lookups can occur for allowed inputs. It writes getHostAddress or null. UUID parses via UUID.fromString, converting IllegalArgumentException to JsonSyntaxException, and writes toString or null. CURRENCY is nullSafe, parses via Currency.getInstance (IllegalArgumentException becomes JsonSyntaxException) and writes the currency code.

**Notes.**

- side_effect: INET_ADDRESS read may perform a DNS lookup via InetAddress.getByName when the string passes the pattern check or the gson.allowDnsInetAddress property is true.

**Uncertainties.**

- The ipAddressPattern intentionally accepts strings that are neither valid IPv4 nor IPv6; whether those resolve is decided by InetAddress.getByName, outside this source.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java