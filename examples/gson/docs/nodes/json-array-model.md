# JSON Array Model

**Capability.** Implements JsonArray, an ordered mutable list of JsonElements with typed adds, conversions, views, and deep copy.

The module is the in-memory representation of JSON arrays, delegating storage to an ArrayList. It offers single-element value conversions, a bidirectional List view, and order-preserving deep copies.

**Depends on.**

- [Tree Element Bridge](tree-element-bridge.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Element Tree Adapter](element-tree-adapter.md) · graph-confirmed · 1 edge(s)
- [Tree Element Bridge](tree-element-bridge.md) · graph-confirmed · 1 edge(s)

Parent: [Arrays and Stream Bridge](arrays-and-stream-bridge.md)

## Units (16)

<a id="u-0777bc5500a7"></a>
### `JsonArray.java-jsonarray-add-methods`

`public void add(Boolean bool)` · [gson/src/main/java/com/google/gson/JsonArray.java:L86-L88][f1]

Append a value to the array, wrapping non-null arguments in a JsonPrimitive and converting null to JsonNull.INSTANCE.

Overloads accept Boolean, Character, Number, String, and JsonElement; the JsonElement overload stores the element as-is (after null normalization) without copying. addAll appends all elements of another JsonArray in order, sharing (not copying) the element references; a null argument array would propagate a NullPointerException from ArrayList.addAll.

<a id="u-e69871ef26be"></a>
### `JsonArray.java-jsonarray-add-overloads`

`class JsonArray extends JsonElement implements Iterable<JsonElement>` · [gson/src/main/java/com/google/gson/JsonArray.java:L78-L86][f1]

These regions document JsonArray's typed add overloads, which append a JsonPrimitive wrapping the given Boolean, Character, Number, or String; a null argument of any of these types is stored as JsonNull.INSTANCE instead of failing.

<a id="u-88a3e0ccddb2"></a>
### `JsonArray.java-jsonarray-equality`

`@Override public boolean equals(Object o)` · [gson/src/main/java/com/google/gson/JsonArray.java:L423-L426][f1]

Equality is order-sensitive: true only for the same instance or another JsonArray whose backing element lists are equal.

hashCode delegates to the backing list's hashCode, keeping the equals/hashCode contract consistent.

<a id="u-46db61605e3d"></a>
### `JsonArray.java-jsonarray-mutation-and-membership`

`class JsonArray extends JsonElement implements Iterable<JsonElement>` · [gson/src/main/java/com/google/gson/JsonArray.java:L139-L149][f1]

These regions document set, both remove overloads, and contains.

set replaces the element at an index (null coerced to JsonNull) and returns the previous element, throwing IndexOutOfBoundsException on a bad index; remove(JsonElement) removes the first occurrence and returns whether it was present, remove(int) removes by index and returns the removed element; contains delegates to the backing list's contains.

<a id="u-73805428e7e3"></a>
### `JsonArray.java-jsonarray-set-remove-contains`

`@CanIgnoreReturnValue public JsonElement set(int index, JsonElement element)` · [gson/src/main/java/com/google/gson/JsonArray.java:L149-L152][f1]

Mutating and lookup operations delegated to the backing ArrayList.

set replaces the element at index (null normalized to JsonNull) and returns the previous element, throwing IndexOutOfBoundsException for an out-of-range index. remove(JsonElement) removes the first equal occurrence and reports whether one was removed; remove(int) removes by index, shifting subsequent elements left, and throws IndexOutOfBoundsException when out of range. contains reports whether an equal element is present, relying on JsonElement equality semantics.

<a id="u-14322e74683c"></a>
### `JsonArray.java-jsonarray-single-element-conversions`

`@Override public Number getAsNumber()` · [gson/src/main/java/com/google/gson/JsonArray.java:L251-L254][f1]

Each getAsX override delegates to the corresponding getAsX on the array's single element, obtained via the private helper.

Behavior: if the array is empty or has more than one element, IllegalStateException is thrown before any conversion; otherwise the result and any further exceptions (e.g. UnsupportedOperationException from a non-primitive element, NumberFormatException for invalid numeric text) come from the element's own method. getAsCharacter is deprecated and, per its doc, returns the string value's first character rather than a char-typed primitive.

<a id="u-2dcebe14e3ae"></a>
### `JsonArray.java-jsonarray-single-element-getas-conversions`

`class JsonArray extends JsonElement implements Iterable<JsonElement>` · [gson/src/main/java/com/google/gson/JsonArray.java:L254-L264][f1]

These regions document JsonArray's overrides of the numeric/string/boolean/character conversions.

Each delegates to getAsSingleElement() and then to the corresponding JsonElement getter, so a non-single-element array fails with IllegalStateException before any conversion is attempted, and any exception the element's getter declares (e.g. UnsupportedOperationException or NumberFormatException) propagates. getAsCharacter is deprecated because it returns the string's first character, not a char value.

<a id="u-63ebebcc5ab0"></a>
### `JsonArray.java-jsonarray-size-and-iteration`

`class JsonArray extends JsonElement implements Iterable<JsonElement>` · [gson/src/main/java/com/google/gson/JsonArray.java:L200-L208][f1]

These regions document size, isEmpty, and iterator, all thin delegations to the backing ArrayList; iteration preserves insertion order.

<a id="u-91e5208e69e2"></a>
### `JsonArray.java-jsonarray-size-isempty-iterator-get`

`public int size()` · [gson/src/main/java/com/google/gson/JsonArray.java:L198-L200][f1]

Read-only accessors delegated to the backing list: element count, emptiness test, an insertion-order iterator, and index-based access.

get(i) throws IndexOutOfBoundsException when i is negative or >= size(). The iterator is the ArrayList's own, so concurrent structural modification would produce its fail-fast behavior (not specified here).

<a id="u-4dd944345a63"></a>
### `JsonArray`

`class JsonArray extends JsonElement implements Iterable<JsonElement>` · [gson/src/main/java/com/google/gson/JsonArray.java:L42-L43][f1]

Ordered, mutable JSON array of JsonElement values backed by an ArrayList; null arguments are normalized to JsonNull.

It implements Iterable (insertion-order iteration) but not List; asList() provides a List view. Two constructors create an empty array, the second with a given initial capacity, which throws IllegalArgumentException if negative. The class does not support null elements directly: every add/set path converts null to JsonNull.INSTANCE. It is final and extends JsonElement, so it inherits the type checks and default getAs conversions from that base.

<a id="u-21b4b8fe342b"></a>
### `gson/src/main/java/com/google/gson/JsonArray.java:JsonArray (10)`

`class JsonArray extends JsonElement implements Iterable<JsonElement>` · [gson/src/main/java/com/google/gson/JsonArray.java:L241-L251][f1]

This region documents the private getAsSingleElement helper: it returns the sole element when the array has size 1, and otherwise throws IllegalStateException with a message reporting the actual size, so empty and multi-element arrays are both rejected.

<a id="u-835c76b43f1f"></a>
### `gson/src/main/java/com/google/gson/JsonArray.java:JsonArray (11)`

`class JsonArray extends JsonElement implements Iterable<JsonElement>` · [gson/src/main/java/com/google/gson/JsonArray.java:L49-L58][f1]

Constructs an empty JsonArray backed by an ArrayList with the caller-supplied initial capacity; a negative capacity propagates the ArrayList's IllegalArgumentException.

The underlying list is the single mutable element store shared by all add/set/remove operations.

<a id="u-ad638d9784b5"></a>
### `gson/src/main/java/com/google/gson/JsonArray.java:JsonArray (25)`

`class JsonArray extends JsonElement implements Iterable<JsonElement>` · [gson/src/main/java/com/google/gson/JsonArray.java:L417-L423][f1]

This region documents asList, which returns a mutable List view backed by the array's element list via NonNullElementWrapperList; mutations are bidirectionally visible, and unlike JsonArray's own null coercion, adding null through the view throws NullPointerException.

<a id="u-dad093fde0ab"></a>
### `JsonArray.asList`

`public List<JsonElement> asList()` · [gson/src/main/java/com/google/gson/JsonArray.java:L415-L417][f1]

Returns a mutable List view backed by this array's element list; changes through either are mutually visible.

Unlike JsonArray's null normalization, the wrapper rejects null elements with NullPointerException, so callers must use JsonNull explicitly.

<a id="u-93c989550c85"></a>
### `JsonArray.deepCopy`

`@Override public JsonArray deepCopy()` · [gson/src/main/java/com/google/gson/JsonArray.java:L68-L78][f1]

Returns a structurally independent copy: a new JsonArray whose elements are the deepCopy() of each contained element, preserving order.

An empty source yields a fresh empty array. Because immutable elements (primitives, nulls) may return themselves from deepCopy, the copy can share those references.

<a id="u-e04ba6879afe"></a>
### `JsonArray.getAsSingleElement`

`private JsonElement getAsSingleElement()` · [gson/src/main/java/com/google/gson/JsonArray.java:L235-L241][f1]

Private helper that returns the sole element of the array, enforcing the single-element precondition shared by all getAsX conversions.

If the size is not exactly 1 (including 0), it throws IllegalStateException with a message stating the actual size.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonArray.java
