# Lazy Number Handling

**Capability.** Implements LazilyParsedNumber, its serialization and identity semantics, and bounded BigDecimal/BigInteger parsing adapters.

The module covers numbers kept in textual form until a concrete numeric type is requested, plus the NumberLimits guard against extreme values. It also supplies the adapters that parse JSON strings into BigDecimal and BigInteger with syntax-error wrapping.

**Depended on by.**

- [JSON Primitive Values](json-primitive-values.md) · graph-only · 2 edge(s)

Parent: [Built-in Adapter Implementations](built-in-adapter-implementations.md)

## Units (7)

<a id="u-1d68d513bc88"></a>
### `LazilyParsedNumber.java-lazilyparsednumber-numeric-conversions`

`class LazilyParsedNumber extends Number implements Comparable<LazilyParsedNumber>` · [gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java:L28-L30][f1]

A Number implementation that stores a numeric value as its original string and converts to a requested numeric type only on demand.

intValue first tries Integer.parseInt; on NumberFormatException it retries with Long.parseLong and casts to int; if that also fails it falls back to BigDecimal (via NumberLimits.parseBigDecimal) and takes intValue, which truncates rather than throws for out-of-range values. longValue similarly tries Long.parseLong and falls back to BigDecimal.longValue. floatValue and doubleValue delegate directly to Float/Double.parseDouble with no fallback, so a malformed string propagates NumberFormatException from those two methods. The constructor accepts any string; null is documented as forbidden but not checked.

<a id="u-36e2f7fd9637"></a>
### `LazilyParsedNumber.java-lazilyparsednumber-serialization-guards`

`class LazilyParsedNumber extends Number implements Comparable<LazilyParsedNumber>` · [gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java:L78-L84][f1]

These class regions hold Java-serialization behavior for the lazily parsed number: on serialization a replacement BigDecimal is written (parsed via the length- and scale-limited parser) so the receiver needs no Gson; direct deserialization of the class is blocked by throwing InvalidObjectException from readObject, since writeReplace should have produced a BigDecimal instead.

<a id="u-470858675925"></a>
### `LazilyParsedNumber.java-lazilyparsednumber-value-semantics-and-serialization`

`@Override public String toString()` · [gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java:L75-L78][f1]

Defines string-based identity, ordering, and Java serialization behavior for the lazily parsed number.

toString returns the original string; equals is true only for the same instance or another LazilyParsedNumber with an equal string; hashCode is the string's hash; compareTo compares the strings lexicographically, which the docstring explicitly notes does not correspond to numeric ordering. For serialization, writeReplace substitutes a BigDecimal so receivers need no Gson; direct deserialization is blocked by readObject throwing InvalidObjectException.

<a id="u-c546b13cd45a"></a>
### `NumberLimits.java-numberlimits`

`class NumberLimits` · [gson/src/main/java/com/google/gson/internal/NumberLimits.java:L10-L11][f2]

Static guard that bounds numbers parsed from JSON to avoid performance problems with extreme values.

Both parseBigDecimal and parseBigInteger first call checkNumberStringLength, which throws NumberFormatException (message includes the first 30 characters) when the input exceeds 10,000 characters. parseBigDecimal additionally constructs a BigDecimal and rejects it with NumberFormatException when the absolute scale (cast to long to avoid Integer.MIN_VALUE abs issues) is >= 10,000; parseBigInteger has no extra check beyond length. Both propagate any NumberFormatException raised by the underlying constructors.

<a id="u-213d2eb1519c"></a>
### `TypeAdapters.java-big-decimal-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L585-L590][f3]

Reads a string and parses it with NumberLimits.parseBigDecimal, wrapping NumberFormatException in a JsonSyntaxException that includes the input and previous path; null token returns null.

write emits the BigDecimal directly.

<a id="u-1c502ccb2e42"></a>
### `TypeAdapters.java-big-integer-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L612-L616][f3]

Reads a string parsed with NumberLimits.parseBigInteger, wrapping NumberFormatException in a JsonSyntaxException with input and path; null token returns null.

write emits the BigInteger directly.

<a id="u-51fb16ce263f"></a>
### `TypeAdapters.java-lazily-parsed-number-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L638-L645][f3]

Reads a string into a LazilyParsedNumber (null token returns null) and writes the value directly; exists mainly for corner cases since the type is internal.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/NumberLimits.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java
