# Ordered JSON array

**Capability.** Implements ordered JsonArray storage, access, mutation, equality, copying, and single-element conversions.

Use when working with JSON array tree nodes. Units show list-backed storage, read-only queries, mutation, deep copy, and order-sensitive equality.

**Depends on.**

- [JsonElement tree base](jsonelement-tree-base.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [JsonElement tree adapter](jsonelement-tree-adapter.md) · graph-confirmed · 1 edge(s)
- [JsonElement tree base](jsonelement-tree-base.md) · graph-confirmed · 1 edge(s)
- [JSON writer formatting](json-writer-formatting.md) · graph-only · 1 edge(s)

Parent: [JSON element tree components](json-element-tree-components.md)

## Units (12)

<a id="u-e69871ef26be"></a>
### `JsonArray.java-jsonarray-add-overloads`

`public void add(Boolean bool)` · [gson/src/main/java/com/google/gson/JsonArray.java:L86-L88][f1]

Appends one element to the internal list.

A null Boolean, Character, Number, String, or JsonElement argument is stored as JsonNull.INSTANCE; non-null primitive wrappers are wrapped in a new JsonPrimitive, while a non-null JsonElement is added directly. The array is mutated and insertion order is preserved.

<a id="u-edca307ff3b7"></a>
### `JsonArray.java-jsonarray-class`

`class JsonArray extends JsonElement implements Iterable<JsonElement>` · [gson/src/main/java/com/google/gson/JsonArray.java:L42-L43][f1]

Final ordered JSON array backed by an ArrayList of JsonElement; it implements Iterable but not List.

Constructors create an empty array, optionally with an initial capacity; a negative capacity is documented to throw IllegalArgumentException. Null elements supplied through array methods are stored as JsonNull.INSTANCE, and insertion order is preserved. A mutable List view is available via asList.

<a id="u-d83ab01e2e69"></a>
### `JsonArray.java-jsonarray-collection-access`

`public boolean contains(JsonElement element)` · [gson/src/main/java/com/google/gson/JsonArray.java:L189-L191][f1]

Read-only queries over the internal list: contains tests presence, size and isEmpty report counts, iterator walks elements in insertion order, and get returns the element at an index.

get propagates IndexOutOfBoundsException for a negative index or an index at least the current size. These methods do not convert nulls.

<a id="u-c0eaeeac11f9"></a>
### `JsonArray.java-jsonarray-remove-overloads`

`@CanIgnoreReturnValue public boolean remove(JsonElement element)` · [gson/src/main/java/com/google/gson/JsonArray.java:L162-L165][f1]

The element overload removes the first occurrence of the given element and returns true if it was present, false otherwise.

The index overload removes the element at that index, shifts later elements left, and returns the removed element; an invalid index propagates IndexOutOfBoundsException. Both mutate the array.

<a id="u-14322e74683c"></a>
### `JsonArray.java-jsonarray-single-element-conversions`

`@Override public Number getAsNumber()` · [gson/src/main/java/com/google/gson/JsonArray.java:L251-L254][f1]

Each conversion first requires exactly one element via the private helper, then delegates to the corresponding getAs method on that element.

If the array size is not one, IllegalStateException is thrown before any element conversion. If size is one, any exception from the element's conversion propagates. The character conversion is deprecated and returns the first character of the element's string value.

<a id="u-8bd70c4927cd"></a>
### `JsonArray.addAll`

`public void addAll(JsonArray array)` · [gson/src/main/java/com/google/gson/JsonArray.java:L137-L139][f1]

Appends every element from another JsonArray's internal list to this array.

A null argument causes a NullPointerException when its elements field is dereferenced, before the list addAll call. The source array is not modified; this array is mutated.

<a id="u-dad093fde0ab"></a>
### `JsonArray.asList`

`public List<JsonElement> asList()` · [gson/src/main/java/com/google/gson/JsonArray.java:L415-L417][f1]

Returns a new mutable List view backed by the array's internal list.

Changes through the list are visible in the JsonArray and vice versa. The view rejects null elements with NullPointerException; use JsonNull for JSON null values.

<a id="u-93c989550c85"></a>
### `JsonArray.deepCopy`

`@Override public JsonArray deepCopy()` · [gson/src/main/java/com/google/gson/JsonArray.java:L68-L78][f1]

Returns a new JsonArray containing a deep copy of each element when the array is non-empty; an empty array yields a new empty JsonArray.

The original array and its elements are not modified.

<a id="u-23d2bf4f21cf"></a>
### `JsonArray.equals`

`@Override public boolean equals(Object o)` · [gson/src/main/java/com/google/gson/JsonArray.java:L423-L426][f1]

Returns true when the other object is the same instance or is a JsonArray whose underlying element list is equal in the same order; otherwise returns false.

Equality is based on the internal list.

<a id="u-e04ba6879afe"></a>
### `JsonArray.getAsSingleElement`

`private JsonElement getAsSingleElement()` · [gson/src/main/java/com/google/gson/JsonArray.java:L235-L241][f1]

Private helper that returns the sole element when the array size is exactly one.

For any other size it throws IllegalStateException with a message stating the required size and the actual size.

<a id="u-9978bed02c19"></a>
### `JsonArray.hashCode`

`@Override public int hashCode()` · [gson/src/main/java/com/google/gson/JsonArray.java:L432-L435][f1]

Returns the hash code of the internal element list, so it is consistent with the order-sensitive equality.

<a id="u-bf823185955c"></a>
### `JsonArray.set`

`@CanIgnoreReturnValue public JsonElement set(int index, JsonElement element)` · [gson/src/main/java/com/google/gson/JsonArray.java:L149-L152][f1]

Replaces the element at the given index, converting a null replacement to JsonNull.INSTANCE, and returns the element previously at that position.

An invalid index propagates IndexOutOfBoundsException from the underlying list.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonArray.java
