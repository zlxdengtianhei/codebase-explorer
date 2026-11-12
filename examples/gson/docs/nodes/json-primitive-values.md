# JSON primitive values

**Capability.** Implements JsonPrimitive storage/conversion/equality and static primitive-wrapper identity utilities.

Use for JSON primitive value behavior and primitive class checks. Units show stored value accessors, numeric conversion, equality/hash, deep copy, and Primitives utilities.

**Depends on.**

- [Internal Java utilities](internal-java-utilities.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [JsonElement tree reader](jsonelement-tree-reader.md) · graph-only · 3 edge(s)
- [Map type adapter factory](map-type-adapter-factory.md) · graph-only · 3 edge(s)
- [JsonElement tree base](jsonelement-tree-base.md) · graph-only · 2 edge(s)
- [Gson serialization facade](gson-serialization-facade.md) · graph-only · 1 edge(s)

Parent: [Primitive values and utilities](primitive-values-and-utilities.md)

## Units (12)

<a id="u-c1bbab7ea01d"></a>
### `JsonPrimitive.java-construction-and-storage`

`class JsonPrimitive extends JsonElement` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L35-L37][f1]

JsonPrimitive stores exactly one non-null value and exposes it as a JSON primitive.

Boolean, Number, and String constructors reject null with NullPointerException; the Character constructor also rejects null and stores the character's one-character String form. The class is final and immutable.

<a id="u-8fe04b6bc915"></a>
### `JsonPrimitive.java-jsonprimitive`

`class JsonPrimitive extends JsonElement` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L105-L113][f1]

If the stored value is Boolean, returns it directly.

Otherwise converts the value to a string and parses it with Boolean.parseBoolean, so only a case-insensitive true yields true and every other string yields false.

<a id="u-d491ef72a38e"></a>
### `JsonPrimitive.java-jsonprimitive-2`

`class JsonPrimitive extends JsonElement` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L129-L138][f1]

If the stored value is a Number, returns it.

If it is a String, returns a LazilyParsedNumber that defers parsing and may throw NumberFormatException when its numeric methods are used. Any other stored type throws UnsupportedOperationException.

<a id="u-20983e92e5a7"></a>
### `JsonPrimitive.java-jsonprimitive-3`

`class JsonPrimitive extends JsonElement` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L155-L158][f1]

Returns the stored String directly; for a Number returns the number's toString; for a Boolean returns its toString.

Any other stored type throws AssertionError, which constructors normally prevent.

<a id="u-3d3a623c20f9"></a>
### `JsonPrimitive.java-jsonprimitive-4`

`class JsonPrimitive extends JsonElement` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L241-L248][f1]

Deprecated accessor that gets the string form and returns its first character.

If the string is empty, throws UnsupportedOperationException; otherwise returns charAt(0).

<a id="u-537e50ddfce2"></a>
### `JsonPrimitive.java-jsonprimitive-5`

`class JsonPrimitive extends JsonElement` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L257-L260][f1]

Returns 31 if the stored value is null, although constructors reject null.

For integral primitives and for other Number values, returns hashOfDoubleValue of the number's double value so equal numeric primitives across types share a hash. For non-number values, returns the stored value's hashCode.

<a id="u-f4b0c34b0cbe"></a>
### `JsonPrimitive.java-jsonprimitive-6`

`class JsonPrimitive extends JsonElement` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L284-L297][f1]

Casts the double to long and returns Long.hashCode of that long only when the double equals the cast long; otherwise returns Double.hashCode of the double.

Thus integral doubles outside long range use Double.hashCode, -0.0 hashes like 0.0, and NaN bit patterns collapse to the canonical Double.hashCode.

<a id="u-8de900421ffb"></a>
### `JsonPrimitive.java-jsonprimitive-7`

`class JsonPrimitive extends JsonElement` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L300-L306][f1]

Identity returns true; null or a different runtime class returns false.

Two integral primitives compare by BigInteger when either stores BigInteger, otherwise by long values. Two Number primitives compare by BigDecimal.compareTo when both store BigDecimal, otherwise by double equality with special handling so -0.0 equals +0.0 and all NaN values are equal. Mixed integral/non-integral Number pairs therefore compare by double equality, so Integer 42 equals Double 42.0. Non-number values use stored value equality.

<a id="u-1af374009fd6"></a>
### `JsonPrimitive.java-jsonprimitive-8`

`class JsonPrimitive extends JsonElement` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L336-L342][f1]

Returns true only when the stored value is a BigInteger, Long, Integer, Short, or Byte.

Other Number types, including BigDecimal, Double, and Float, return false.

<a id="u-14ef251dd4bc"></a>
### `JsonPrimitive.java-numeric-getters`

`class JsonPrimitive extends JsonElement` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L168-L173][f1]

These accessors convert the primitive to numeric types.

For getAsDouble, getAsFloat, getAsLong, getAsShort, getAsInt, and getAsByte, a stored Number is converted with the corresponding primitiveValue method; otherwise the string form is parsed with the corresponding parse method, and parse failures throw NumberFormatException. getAsBigDecimal returns a stored BigDecimal directly; any other value, including another Number type, is parsed from the string form via NumberLimits.parseBigDecimal. getAsBigInteger returns a stored BigInteger directly; an integral stored number is converted with BigInteger.valueOf(longValue); a non-integral value is parsed from the string form via NumberLimits.parseBigInteger. Parsing failures throw NumberFormatException.

**Uncertainties.**

- NumberLimits parsing rules and limits are not visible in this file.

<a id="u-0d824ffeec36"></a>
### `JsonPrimitive.java-type-checks-and-copy`

`class JsonPrimitive extends JsonElement` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L86-L93][f1]

deepCopy returns the same instance because primitives are immutable.

isBoolean, isNumber, and isString test the stored value's runtime type and perform no conversion. They return false for values of other types.

<a id="u-12ec5550eef8"></a>
### `Primitives.java-primitive-and-wrapper-utilities`

`class Primitives` · [gson/src/main/java/com/google/gson/internal/Primitives.java:L27-L28][f2]

Static utilities for primitive and wrapper class identity.

Primitive detection requires a Class that reports itself primitive. Wrapper detection matches the nine wrapper classes by identity. Wrap maps each primitive class to its wrapper and returns other classes unchanged; unwrap does the reverse. Both are idempotent.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonPrimitive.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/Primitives.java
