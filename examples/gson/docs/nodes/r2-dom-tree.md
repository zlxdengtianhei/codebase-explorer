# JSON DOM Tree

**Capability.** Models JSON data as an immutable in-memory tree: JsonElement is the abstract base, with JsonObject (insertion-ordered via LinkedTreeMap), JsonArray, and JsonPrimitive (with numerically normalized equals/hashCode) as concrete node types.

Use these classes to build, inspect, and transform JSON values programmatically. Adapters and the streaming layer convert between this tree and JSON text; JsonPrimitive's cross-type numeric equality and LazilyParsedNumber-backed number semantics matter when comparing or hashing trees.

**Children.**

- [Tree-Bound Writer](r2-tree-writer.md) `r2-tree-writer` · 22 unit(s)

**Depends on.**

- [Built-in Type Adapter Factories](r2-default-adapters.md) · model-inferred · 0 edge(s)
- [Internal Utilities and Data Structures](r2-infrastructure.md) · graph-confirmed · 13 edge(s) · JsonObject stores its members insertion-ordered in LinkedTreeMap and elements use Streams for bridging.
- [Streaming JSON Writer and Lexical Model](r2-streaming.md) · graph-confirmed · 6 edge(s)
- [Insertion-Ordered AVL Map](r2-linkedtreemap.md) · graph-only · 11 edge(s)
- [Internal Support Utilities](r1-internal-support.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Built-in Type Adapter Factories](r2-default-adapters.md) · graph-confirmed · 21 edge(s)
- [Tree-Bound Writer](r2-tree-writer.md) · containment · → 3 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r2-tree-writer ` → ` r2-dom-tree `) · JsonTreeWriter assembles JsonElement, JsonArray, and JsonObject nodes instead of emitting characters.
- [Collection, Map, and Tree Adapters](r2-collection-map-adapters.md) · graph-only · 21 edge(s)
- [Streaming JSON Reading](r1-streaming-json.md) · graph-only · 6 edge(s)

Parent: [Gson JSON Library](r2-gson.md)

## Units (8)

<a id="u-103ba2beeebe"></a>
### `jsonelement-class`

`class JsonElement` · [gson/src/main/java/com/google/gson/JsonElement.java:L96-L102][f1]

Abstract base of all JSON tree nodes (JsonObject, JsonArray, JsonPrimitive, JsonNull).

Type checks isJsonArray/isJsonObject/isJsonPrimitive/isJsonNull are instanceof tests and always return a definite boolean. The four getAsJson* cast helpers return this cast to the requested subclass when the matching check passes and otherwise throw IllegalStateException with a 'Not a JSON <Type>: ' + this message, so the exception text embeds toString output. All primitive-conversion getAs* methods (getAsBoolean, getAsNumber, getAsString, getAsDouble, getAsFloat, getAsLong, getAsInt, getAsByte, getAsCharacter, getAsBigDecimal, getAsBigInteger, getAsShort) are base-class stubs that unconditionally throw UnsupportedOperationException with the concrete class's simple name; each subclass is expected to override them, which is why JsonArray's overrides delegate to its single element. deepCopy is abstract, forcing subclasses to implement copying. The deprecated public constructor exists only for backward compatibility; subclassing is discouraged as undefined behavior. toString serializes the tree by wrapping a StringBuilder in a JsonWriter via Streams.writerForAppendable, setting strictness to LENIENT so NaN/Infinity primitives still serialize, then Streams.write emits the element; an IOException (theoretically impossible for StringBuilder) is rethrown as AssertionError, so toString never propagates IOException.

**Notes.**

- failure: AsX methods throw IllegalStateException whose message concatenates this element's toString, so a malformed message element indirectly triggers full serialization.
- condition: The getAs* primitive stubs throwing UnsupportedOperationException(getClass().getSimpleName()) mean calling them on a subclass that fails to override them fails at runtime, not compile time.

calls: [Streams](r2-infrastructure.md#u-931987e48ef4), [jsonwriter-config-accessors](r2-streaming.md#u-cccb91734698)

**Uncertainties.**

- Whether uncaught Error paths or non-IOException failures in Streams.write behave differently than the AssertionError path is not established here.
- The concrete serialization output format is determined by JsonWriter/Streams, which are outside this source.

<a id="u-d79acd357359"></a>
### `jsonarray-class`

`class JsonArray extends JsonElement implements Iterable<JsonElement>` · [gson/src/main/java/com/google/gson/JsonArray.java:L42-L46][f2]

Represents a JSON array as an ordered, final wrapper over a private ArrayList<JsonElement>, extending JsonElement and implementing Iterable.

Null-receiving mutators (all add overloads, set) substitute JsonNull.INSTANCE for null so no true null is ever stored. deepCopy builds a new JsonArray with deep copies of each child when non-empty, otherwise returns a plain empty array. The getAs* overrides all delegate through the private getAsSingleElement: with exactly one element they forward to that element's conversion (surfacing its NumberFormatException/UnsupportedOperationException behavior), and with size 0 or >1 they throw IllegalStateException naming the actual size. addAll appends another array's internal list contents; remove(JsonElement) removes the first equal occurrence and returns whether anything was removed, while remove(int) removes by position returning the prior element and throwing IndexOutOfBoundsException for invalid indices. contains, size, isEmpty, iterator, and get forward directly to the backing list; get throws IndexOutOfBoundsException for out-of-range indices. asList exposes a mutable NonNullElementWrapperList view that mirrors changes bidirectionally but rejects null with NullPointerException, unlike the JsonNull-substituting mutators. equals requires the argument to be a JsonArray with element-wise equal contents in the same order (reference-equal short-circuits); hashCode is the backing list's hash code, so equal arrays hash equally.

**Notes.**

- failure: Every getAs* override on JsonArray throws IllegalStateException with the message 'Array must have size 1, but has size N' when the array does not hold exactly one element.
- condition: The capacity constructor forwards to ArrayList, so a negative capacity throws IllegalArgumentException; the no-arg constructor always allocates empty.
- side_effect: asList returns a live view backed by the same ArrayList; structural or value changes through either handle are visible to the other, but the view rejects null elements.

**Uncertainties.**

- addAll takes array.elements directly; behavior if array is this same instance is not established by the source.

<a id="u-5c0ff73487b7"></a>
### `jsonobject-class`

`class JsonObject extends JsonElement` · [gson/src/main/java/com/google/gson/JsonObject.java:L40-L44][f3]

Represents a JSON object as a final JsonElement subclass backed by a private LinkedTreeMap<String, JsonElement> created with ordering-preserving, non-sorted behavior, so members keep insertion order.

add stores the key and substitutes JsonNull.INSTANCE for a null value; addProperty overloads (String, Number, Boolean, Character) wrap the value in a JsonPrimitive first, or store JsonNull.INSTANCE when the value is null, then delegate to add. remove deletes by key and returns the prior element or null when absent. Accessors entrySet, keySet, size, isEmpty, has, and get forward to the map, with get returning null for missing names. The typed getters getAsJsonPrimitive/getAsJsonArray/getAsJsonObject(String) fetch via map.get and cast; a missing name yields null (a null cast is legal), while a present member of the wrong type throws ClassCastException. deepCopy constructs a new JsonObject and re-adds each value's deepCopy under the same key. asMap returns the internal LinkedTreeMap directly as a live mutable Map view; the code comments this is safe because that map itself disallows null keys and values, and writes through it affect this object. equals considers only JsonObject instances with equal members, order-independent per the underlying map's equals (reference-equal short-circuits); hashCode is the map's hash code.

**Notes.**

- failure: The String-based getAsJsonPrimitive/getAsJsonArray/getAsJsonObject return null for absent keys and throw ClassCastException only when an existing member has the wrong type.
- side_effect: asMap hands out the internal LinkedTreeMap itself, so mutations through the returned Map directly modify this JsonObject.

calls: [LinkedTreeMap](r2-linkedtreemap.md#u-603f4565d5fe)

**Uncertainties.**

- Whether LinkedTreeMap.equals is truly order-independent is asserted by the class Javadoc and map choice but not proven from LinkedTreeMap source in this batch.

<a id="u-1c779c98f5ee"></a>
### `JsonPrimitive`

`class JsonPrimitive extends JsonElement` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L35-L47][f4]

Represents a JSON primitive value holding exactly one of Boolean, Number, String, or a character converted to a one-character String; it is a final JsonElement subclass that is immutable.

The four constructors reject null arguments via Objects.requireNonNull (NullPointerException); the Character constructor stores the character as a String since JSON has no char type. deepCopy returns this because instances are immutable. isBoolean/isNumber/isString are instanceof checks on the stored value. Conversion methods define distinct fallbacks: getAsBoolean parses the string value with Boolean.parseBoolean (case-insensitive "true", everything else false); getAsNumber returns the stored Number, wraps a String in a LazilyParsedNumber (which can throw NumberFormatException only later when parsed), and throws UnsupportedOperationException otherwise; getAsString returns the String, the Number's string form, the Boolean's string form, and throws AssertionError for any other value type. Numeric accessors (getAsDouble/Float/Long/Short/Int/Byte) convert directly when the value is a Number and otherwise parse getAsString() with the corresponding parse method, propagating NumberFormatException. getAsBigDecimal returns a stored BigDecimal or delegates to NumberLimits.parseBigDecimal; getAsBigInteger returns a stored BigInteger, uses BigInteger.valueOf(getAsNumber().longValue()) for integral types, otherwise NumberLimits.parseBigInteger. getAsCharacter (deprecated) returns the first character of getAsString() and throws UnsupportedOperationException when that string is empty.

**Notes.**

- failure: Null constructor arguments fail fast with NullPointerException from Objects.requireNonNull, not with a lazy error.
- failure: String-backed numeric conversions defer parse errors: getAsNumber wraps the string, so NumberFormatException surfaces when the LazilyParsedNumber is read, while the typed getX accessors parse eagerly.
- field: Characters are normalized to Strings at construction, so isString() is true for a primitive built from a char.

calls: [JsonPrimitive.isIntegral](r2-dom-tree.md#u-62fd262dc723), [NumberLimits.parseBigDecimal](r1-internal-support.md#u-5f49b1496f23), [NumberLimits.parseBigInteger](r1-internal-support.md#u-513e7aece357)

**Uncertainties.**

- The full behavior of LazilyParsedNumber and NumberLimits.parseBigDecimal/parseBigInteger (e.g. their exact validation limits) lives outside this file.

<a id="u-fb80fb05ccaa"></a>
### `JsonPrimitive.equals`

`@Override public boolean equals(Object obj)` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L306-L336][f4]

Implements value equality with numeric cross-type normalization.

Reference-equal objects are equal; null or a different class is not. If either value is null, equality means both are null. If both values are integral (isIntegral true for both), comparison is via BigInteger values when either side is a BigInteger, otherwise via longValue equality. If both are Numbers but not both integral: two BigDecimals are compared with compareTo (so 0 and 0.00 are equal regardless of scale); all other number pairs are compared as doubles, treating -0.0 and +0.0 as equal (deliberately not Double.compare) and treating any two NaN values as equal. Anything else (involving strings or booleans) falls back to value.equals(other.value).

calls: [JsonPrimitive.isIntegral](r2-dom-tree.md#u-62fd262dc723); uses: [JsonPrimitive](r2-dom-tree.md#u-1c779c98f5ee)

<a id="u-7032cf116ee8"></a>
### `JsonPrimitive.hashCode`

`@Override public int hashCode()` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L260-L284][f4]

Computes a hash code consistent with equals across mixed numeric types.

For a null value it returns 31. If the value is integral (per isIntegral) or any other Number, it hashes the double value via hashOfDoubleValue so that, e.g., Integer 42 and Double 42.0 hash identically, matching equals' double-based numeric comparison; all non-numeric values hash the stored value's own hashCode. The comment records that any other scheme would break the equals/hashCode contract for cross-type equal primitives.

calls: [JsonPrimitive.hashOfDoubleValue](r2-dom-tree.md#u-04051759d706), [JsonPrimitive.isIntegral](r2-dom-tree.md#u-62fd262dc723)

<a id="u-04051759d706"></a>
### `JsonPrimitive.hashOfDoubleValue`

`private static int hashOfDoubleValue(double doubleValue)` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L297-L300][f4]

Derives a hash from the double value that equals ultimately compares numbers by.

If the double equals its long cast (mathematically integral within long range) it returns Long.hashCode of that long, which also normalizes -0.0 to 0.0; otherwise it returns Double.hashCode, collapsing all NaN bit patterns to one value, matching equals which treats all NaNs as equal.

<a id="u-62fd262dc723"></a>
### `JsonPrimitive.isIntegral`

`private static boolean isIntegral(JsonPrimitive primitive)` · [gson/src/main/java/com/google/gson/JsonPrimitive.java:L342-L352][f4]

Reports whether a primitive's stored value is an integral number: true only when the value is a BigInteger, Long, Integer, Short, or Byte; any other Number (for example Double, Float, BigDecimal, or LazilyParsedNumber) or a non-number value yields false.

Used by equals and hashCode to pick integral versus double-based comparison.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonElement.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonArray.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonObject.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonPrimitive.java