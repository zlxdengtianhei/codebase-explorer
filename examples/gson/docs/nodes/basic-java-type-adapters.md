# Basic Java type adapters

**Capability.** Defines TypeAdapter factories and adapters for common Java scalar, string, URL, UUID, and calendar types.

Use for built-in adapters of basic JDK value types. Units list scalar adapters, calendar/inet/locale/URI/URL/UUID/Currency, and optional JavaTime factory loading.

**Depends on.**

- [Internal Java utilities](internal-java-utilities.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Core Gson default adapters](core-gson-default-adapters.md) · graph-only · 1 edge(s)

Parent: [Built-in Java type adapters](built-in-java-type-adapters.md)

## Units (25)

<a id="u-84c1bccd30cb"></a>
### `TypeAdapters.java-base-subclass-factory`

`@SuppressWarnings("TypeParameterNaming") public static <TT> TypeAdapterFactory newFac…` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L1044-L1048][f1]

Creates a factory matching a base class or one specified subclass.

Its create returns the supplied adapter when the requested raw type equals either class, otherwise null; toString reports both classes and adapter.

<a id="u-22bd2bd8c6a5"></a>
### `TypeAdapters.java-bigdecimal-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L585-L590][f1]

BigDecimal adapter.

Reading null returns null; otherwise nextString is parsed with NumberLimits.parseBigDecimal, and NumberFormatException becomes JsonSyntaxException with the input and path. Writing delegates to the writer.

<a id="u-14f4ee7e3c76"></a>
### `TypeAdapters.java-biginteger-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L612-L616][f1]

BigInteger adapter.

Reading null returns null; otherwise nextString is parsed with NumberLimits.parseBigInteger, and NumberFormatException becomes JsonSyntaxException with the input and path. Writing delegates to the writer.

<a id="u-47b14cfef503"></a>
### `TypeAdapters.java-boolean-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L146-L150][f1]

Boolean adapter.

Reading null returns null; a STRING token is parsed with Boolean.parseBoolean for backward compatibility; otherwise nextBoolean is used. Writing delegates to the writer's value method.

<a id="u-f5de9e08bdf2"></a>
### `TypeAdapters.java-boolean-as-string-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L166-L174][f1]

Boolean-as-string adapter for map keys.

Reading null returns null; otherwise Boolean.valueOf(nextString). Writing emits "null" for null and the boolean's string form otherwise.

<a id="u-4d48e6fffe9d"></a>
### `TypeAdapters.java-byte-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L190-L194][f1]

Byte adapter.

Reading null returns null; nextInt failures are wrapped in JsonSyntaxException; values above 255 or below Byte.MIN_VALUE throw JsonSyntaxException for lossy conversion. Writing null emits null, otherwise byteValue.

<a id="u-fdd4f7065e50"></a>
### `TypeAdapters.java-calendar-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L897-L903][f1]

Calendar adapter built on the integer-fields adapter with year, month, dayOfMonth, hourOfDay, minute, and second.

create builds a GregorianCalendar using toIntExact on each value; integerValues reads those Calendar fields.

<a id="u-d4a247df6b60"></a>
### `TypeAdapters.java-character-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L533-L537][f1]

Character adapter.

Reading null returns null; otherwise nextString must have length exactly one or JsonSyntaxException is thrown with the string, length, and path. Writing null emits null, otherwise the character as a string.

<a id="u-a25f362cb166"></a>
### `TypeAdapters.java-factorysupplier`

`interface FactorySupplier` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L976-L977][f1]

Functional interface supplying a TypeAdapterFactory through get; it has no implementation in this file.

<a id="u-f015cb610fc8"></a>
### `TypeAdapters.java-inetaddress-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L759-L768][f1]

InetAddress adapter.

Reading null returns null; otherwise nextString is accepted only if the whole string matches the IPv6-like colon pattern or the entire IPv4-like dotted-number pattern, unless system property gson.allowDnsInetAddress is true; rejection throws JsonSyntaxException. Accepted strings go to InetAddress.getByName. Writing null emits null, otherwise getHostAddress.

<a id="u-5768a0c33705"></a>
### `TypeAdapters.java-integer-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L261-L265][f1]

Integer adapter.

Reading null returns null; nextInt failures are wrapped in JsonSyntaxException. Writing null emits null, otherwise intValue.

<a id="u-c05cd843e775"></a>
### `TypeAdapters.java-integerfieldstypeadapter`

`class IntegerFieldsTypeAdapter<T> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L851-L852][f1]

Abstract adapter for objects serialized as a fixed set of integer fields.

The constructor stores field names; subclasses implement create and integerValues. Reading null returns null; otherwise it reads an object, fills known fields with nextLong, skips unknown fields, and calls create. Writing null emits null; otherwise it writes each field name and its long value.

<a id="u-6339fb03b1b0"></a>
### `TypeAdapters.java-lazilyparsednumber-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L638-L645][f1]

LazilyParsedNumber adapter.

Reading null returns null; otherwise wraps nextString in a new LazilyParsedNumber. Writing delegates to the writer.

<a id="u-d92d81020862"></a>
### `TypeAdapters.java-locale-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L928-L932][f1]

Locale adapter.

Reading null returns null; otherwise nextString is split on underscores into up to language, country, and variant, then constructs Locale with one, two, or three parts. Writing null emits null, otherwise toString.

<a id="u-242103392268"></a>
### `TypeAdapters.java-long-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L409-L413][f1]

Long adapter.

Reading null returns null; nextLong failures are wrapped in JsonSyntaxException. Writing null emits null, otherwise longValue.

<a id="u-ce9d9e704f21"></a>
### `TypeAdapters.java-long-as-string-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L433-L438][f1]

Long-as-string adapter.

Reading null returns null; otherwise it returns nextLong without catching NumberFormatException, so parse failures propagate unwrapped. Writing null emits null, otherwise the value's string form.

<a id="u-61d8ee062ab6"></a>
### `TypeAdapters.java-short-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L225-L229][f1]

Short adapter.

Reading null returns null; nextInt failures are wrapped in JsonSyntaxException; values above 65535 or below Short.MIN_VALUE throw JsonSyntaxException for lossy conversion. Writing null emits null, otherwise shortValue.

<a id="u-1af03dfecaeb"></a>
### `TypeAdapters.java-string-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L564-L568][f1]

String adapter.

Reading null returns null; a BOOLEAN token is converted with Boolean.toString for backward compatibility; otherwise nextString. Writing delegates to the writer.

<a id="u-f364d959b612"></a>
### `TypeAdapters.java-stringbuffer-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L683-L687][f1]

StringBuffer adapter.

Reading null returns null; otherwise wraps nextString in a new StringBuffer. Writing null emits null, otherwise the buffer's string form.

<a id="u-3d6891a0b6d1"></a>
### `TypeAdapters.java-stringbuilder-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L663-L667][f1]

StringBuilder adapter.

Reading null returns null; otherwise wraps nextString in a new StringBuilder. Writing null emits null, otherwise the builder's string form.

<a id="u-a7f7d5f399ec"></a>
### `TypeAdapters.java-uri-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L731-L735][f1]

URI adapter.

Reading null returns null; the literal string "null" also returns null; otherwise new URI is attempted and URISyntaxException becomes JsonSyntaxException with input and path. Writing null emits null, otherwise toString.

<a id="u-036887cbf8ae"></a>
### `TypeAdapters.java-url-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L703-L707][f1]

URL adapter.

Reading null returns null; the literal string "null" also returns null; otherwise new URL is attempted and MalformedURLException becomes JsonSyntaxException with input and path. Writing null emits null, otherwise toExternalForm.

<a id="u-fe0375b5fa0b"></a>
### `TypeAdapters.java-uuid-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L799-L803][f1]

UUID adapter.

Reading null returns null; otherwise UUID.fromString is attempted and IllegalArgumentException becomes JsonSyntaxException with input and path. Writing null emits null, otherwise toString.

<a id="u-b8580df1c766"></a>
### `gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:TypeAdapters (45)`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L844-L851][f1]

Adapts Currency values to and from ISO 4217 currency-code strings, wrapping invalid codes as JsonSyntaxException.

Reading consumes the next string and calls Currency.getInstance; an IllegalArgumentException is caught and rethrown as JsonSyntaxException with the offending text and reader path. Writing emits the currency code. The enclosing constant applies nullSafe, so null JSON and null values are handled by that wrapper rather than by this class body.

<a id="u-f9f1ea7218e2"></a>
### `TypeAdapters.javaTimeTypeAdapterFactory`

`public static TypeAdapterFactory javaTimeTypeAdapterFactory()` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L980-L990][f1]

Attempts to load and instantiate the optional JavaTimeTypeAdapters class, cast it to FactorySupplier, and return its factory.

ReflectiveOperationException and LinkageError return null; ClassCastException from the cast and exceptions from supplier.get() propagate.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java
