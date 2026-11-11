# JSON Primitive Values

**Capability.** Implements JsonPrimitive, the immutable leaf node holding a Boolean, Number, or String with cross-type equality.

This module defines scalar JSON values: type predicates, numeric getters that parse string forms, and hashCode/equals rules that treat integral and double representations consistently. It also identifies integral-only numbers.

**Depends on.**

- [Lazy Number Handling](lazy-number-handling.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Map Serialization](map-serialization.md) · graph-confirmed · 3 edge(s)
- [In-memory tree reader](in-memory-tree-reader.md) · graph-only · 3 edge(s)
- [Tree Element Bridge](tree-element-bridge.md) · graph-only · 2 edge(s)

Parent: [Primitives and Map Adapters](primitives-and-map-adapters.md)

## Units (11)

<a id="u-4a066c73dcc4"></a>
### `JsonPrimitive.java-boolean-access`

`public boolean isBoolean()` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L103-L105][f1]

isBoolean reports whether the stored value is a Boolean.

getAsBoolean returns it directly when it is; otherwise it falls back to Boolean.parseBoolean on the string form, so any string other than case-insensitive "true" yields false.

<a id="u-49f59417c390"></a>
### `JsonPrimitive.java-hashcode-and-double-hashing`

`@Override public int hashCode()` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L260-L284][f1]

hashCode returns 31 for a null value; for integral primitives and for other Numbers it delegates to hashOfDoubleValue of the double value, so primitives that equals considers equal across branches (e.g. Integer 42 and Double 42.0) hash identically; otherwise it returns the stored value's hashCode.

hashOfDoubleValue uses Long.hashCode of the cast long when the double is mathematically integral (normalizing -0.0 to 0), otherwise Double.hashCode of the bits, collapsing NaN patterns to one value — both matching equals semantics.

<a id="u-734958abf7b5"></a>
### `JsonPrimitive.java-jsonprimitive-constructors`

`class JsonPrimitive extends JsonElement` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L37-L47][f1]

Each constructor stores the given Boolean, Number, or String after a null check that throws NullPointerException; the Character constructor converts the character to a one-character String because JSON has no character type.

The value is final, making the primitive immutable.

<a id="u-8b186d7c1053"></a>
### `JsonPrimitive.java-jsonprimitive-javadoc-wrapper-regions`

`class JsonPrimitive extends JsonElement` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L105-L113][f1]

These class regions contain only the Javadoc and annotations surrounding methods that already have their own units (getAsBoolean, getAsNumber, getAsDouble, getAsFloat, getAsCharacter, hashCode, hashOfDoubleValue); they add no separate behavior.

The Javadoc documents exception contracts: getAsNumber throws UnsupportedOperationException for non-number, non-string values; getAsCharacter throws UnsupportedOperationException on an empty string value and is deprecated because it returns the string's first character rather than a char value; hashCode's comment explains why every numeric branch must delegate to the double-based hash (consistency with equals across mixed numeric types, per gson issue 992).

<a id="u-744a3d314bc2"></a>
### `JsonPrimitive.java-number-access`

`public boolean isNumber()` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L127-L129][f1]

isNumber reports whether the stored value is a Number.

getAsNumber returns the stored Number, or, for a String value, wraps it in a LazilyParsedNumber that defers parsing until a method is called (potentially throwing NumberFormatException then); for any other value type it throws UnsupportedOperationException.

<a id="u-603d47f75143"></a>
### `JsonPrimitive.java-numeric-conversions`

`@Override public double getAsDouble()` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L173-L176][f1]

Each numeric getter returns the stored number's corresponding value when the primitive is a Number, otherwise parses the string form (Double.parseDouble, Float.parseFloat, Long.parseLong, Short.parseShort, Integer.parseInt, Byte.parseByte), propagating NumberFormatException on unparseable strings.

getAsBigDecimal returns a stored BigDecimal directly or parses the string via NumberLimits.parseBigDecimal. getAsBigInteger returns a stored BigInteger, converts an integral primitive via BigInteger.valueOf(longValue()), or parses the string via NumberLimits.parseBigInteger; note that a non-integral stored Number like Double 1.5 goes to the string-parsing path.

<a id="u-0f5cdbd2d1da"></a>
### `JsonPrimitive.java-string-access`

`public boolean isString()` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L153-L155][f1]

isString reports whether the stored value is a String.

getAsString returns the String directly; for a Number it returns its toString; for a Boolean its toString; the final branch throws AssertionError for an unexpected type, which is unreachable through the public constructors.

<a id="u-fc28200a3762"></a>
### `JsonPrimitive.deepCopy`

`@Override public JsonPrimitive deepCopy()` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L93-L96][f1]

Returns this instance itself because JsonPrimitive is immutable, so deep copies share identity.

<a id="u-fb80fb05ccaa"></a>
### `JsonPrimitive.equals`

`@Override public boolean equals(Object obj)` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L306-L336][f1]

Compares only JsonPrimitive instances of the same class: identical references are equal; null or other classes are not.

With a null value, equality requires the other's value also null. If both primitives are integral (Long/Integer/Short/Byte/BigInteger), they are compared by BigInteger when either side is a BigInteger, otherwise by longValue. If both are Numbers, two BigDecimals compare via compareTo (ignoring scale, so 0 equals 0.00); other numbers compare by double value using == plus a special case treating NaN on both sides as equal (deliberately not Double.compare, so -0.0 equals +0.0). All remaining cases fall back to value.equals.

<a id="u-0da3ed1dc54c"></a>
### `JsonPrimitive.getAsCharacter`

`@Deprecated @Override public char getAsCharacter()` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L248-L257][f1]

Deprecated method that returns the first character of the string form, not a char value; throws UnsupportedOperationException when the string is empty.

<a id="u-62fd262dc723"></a>
### `JsonPrimitive.isIntegral`

`private static boolean isIntegral(JsonPrimitive primitive)` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L342-L352][f1]

Returns true only when the stored value is a Number of type BigInteger, Long, Integer, Short, or Byte; false for any other value, including other Number types like Double.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonPrimitive.java
