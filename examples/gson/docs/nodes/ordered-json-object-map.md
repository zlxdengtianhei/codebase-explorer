# Ordered JSON object map

**Capability.** Implements ordered JsonObject members and the insertion-ordered AVL-backed LinkedTreeMap used for storage.

Use for JSON object tree behavior and ordered map internals. Units show member access/mutation, deep copy/equality, AVL balancing, and insertion-order iteration.

**Depends on.**

- [JSON element tree components](json-element-tree-components.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [JSON element tree components](json-element-tree-components.md) · graph-confirmed · 2 edge(s)
- [JSON writer formatting](json-writer-formatting.md) · graph-only · 1 edge(s)
- [JsonElement tree adapter](jsonelement-tree-adapter.md) · graph-only · 1 edge(s)
- [JsonElement tree base](jsonelement-tree-base.md) · graph-only · 1 edge(s)

Parent: [JSON tree model](json-tree-model.md)

## Units (20)

<a id="u-cc9f6a9621b1"></a>
### `JsonObject.java-jsonobject-addproperty-overloads`

`public void addProperty(String property, String value)` · [gson/src/main/java/com/google/gson/JsonObject.java:L93-L95][f1]

Each overload wraps a non-null String, Number, Boolean, or Character in a new JsonPrimitive and delegates to add.

A null value becomes JsonNull.INSTANCE. The object is mutated and no value is returned.

<a id="u-164df50dc073"></a>
### `JsonObject.java-jsonobject-class`

`class JsonObject extends JsonElement` · [gson/src/main/java/com/google/gson/JsonObject.java:L40-L41][f1]

Final ordered JSON object backed by a LinkedTreeMap of String to JsonElement; it does not implement Map.

Constructors create an empty object. Member names must be non-null, and null values supplied through object methods are stored as JsonNull.INSTANCE. A mutable Map view is available via asMap.

<a id="u-b65db27d8d49"></a>
### `JsonObject.java-jsonobject-queries`

`public int size()` · [gson/src/main/java/com/google/gson/JsonObject.java:L156-L158][f1]

size returns the number of members; isEmpty returns true when there are zero members; has reports whether a member with the given name exists; get returns the member value or null when absent.

These methods do not mutate the object.

<a id="u-f2aaea0e55ed"></a>
### `JsonObject.java-jsonobject-typed-getters`

`public JsonPrimitive getAsJsonPrimitive(String memberName)` · [gson/src/main/java/com/google/gson/JsonObject.java:L198-L200][f1]

Each method fetches the member by name and casts it to JsonPrimitive, JsonArray, or JsonObject.

It returns null when no member exists and throws ClassCastException when the member exists but has a different type. No conversion is performed.

<a id="u-35bfc02929e2"></a>
### `JsonObject.java-jsonobject-view-methods`

`public Set<Map.Entry<String, JsonElement>> entrySet()` · [gson/src/main/java/com/google/gson/JsonObject.java:L136-L138][f1]

entrySet and keySet return the underlying map's entry set and key set.

asMap returns the underlying map itself and is documented as a mutable view whose changes are visible in both directions. The source does not establish whether mutations through entrySet or keySet affect the JsonObject.

<a id="u-2ecedb0017ac"></a>
### `LinkedTreeMap.java-avl-rebalancing-and-rotations`

`private void rebalance(Node<K, V> unbalanced, boolean insert)` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L328-L386][f2]

Restores AVL balance by walking from an unbalanced node toward the root and rotating as needed.

For a right-heavy node, a right child delta of -1, or 0 during removal, causes a single left rotation; otherwise it asserts the child delta is 1, then rotates the child right and the node left. For a left-heavy node, a left child delta of 1, or 0 during removal, causes a single right rotation; otherwise it asserts the child delta is -1, then rotates the child left and the node right. Insert-driven rotations stop the walk; a balanced node updates height and stops on insert; an already height-stable node stops on removal. Rotations rewire parent links through parent replacement and recompute affected heights.

<a id="u-570ba476a48a"></a>
### `LinkedTreeMap.java-entry-set-view`

`class EntrySet extends AbstractSet<Entry<K, V>>` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L590-L591][f2]

Entry-set view over the map.

Size reports map size. Iterator returns entries from the map iterator. Contains accepts only entries and uses entry lookup. Remove accepts only entries, returns false when lookup fails, otherwise removes the found node with unlinking and returns true. Clear delegates to the map.

<a id="u-f5f051239601"></a>
### `LinkedTreeMap.java-key-set-view`

`class KeySet extends AbstractSet<K>` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L631-L632][f2]

Key-set view over the map.

Size reports map size. Iterator returns keys from the map iterator. Contains delegates to key lookup. Remove deletes by key and reports whether a node was found. Clear delegates to the map.

<a id="u-ef8070cb168b"></a>
### `LinkedTreeMap.java-lookup-and-entry-matching`

`Node<K, V> find(K key, boolean create)` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L142-L201][f2]

Finds existing nodes and creates new ones in comparison order, with insertion-order linking.

Traversal uses the comparator or natural Comparable ordering; equality is comparison zero. If not creating, a missing key returns null. When creating, an empty tree with no comparator and a non-Comparable key throws ClassCastException; otherwise a new node is linked at the end of the iteration list (after the sentinel's previous node, before the sentinel), attached as root or child, rebalanced, and counted. With a non-empty tree and no comparator, the natural-order cast happens before the create check, so a non-Comparable key throws regardless of create. Object lookup returns null for null keys and catches ClassCastException as not found. Entry lookup requires both comparator-equal key and Objects.equals value.

<a id="u-e282791657f7"></a>
### `LinkedTreeMap.java-map-core-and-constructors`

`class LinkedTreeMap<K, V> extends AbstractMap<K, V> implements Serializable` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L43-L48][f2]

An insertion-ordered map backed by an AVL tree for key comparison and a sentinel linked list for iteration order.

Constructors choose natural or supplied comparator ordering and whether null values are allowed; the sentinel starts self-linked. Size returns the entry count. Get and containsKey use lookup, so null keys yield null/false and comparison ClassCastException is swallowed. Put rejects null keys, rejects null values when disallowed, finds or creates a node, returns the previous value, and stores the new value. Clear resets root and size, increments modification count, and relinks the sentinel to itself. Remove deletes by key and returns the removed value or null.

<a id="u-78a89b50c11c"></a>
### `LinkedTreeMap.java-map-iterator`

`class LinkedTreeMapIterator<T> implements Iterator<T>` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L552-L553][f2]

Iterator over the map's insertion-order linked list with fail-fast modification checks.

It starts at the sentinel's next node and records the current modification count. Has-next tests whether the next node is not the sentinel. Next-node throws NoSuchElementException at the sentinel and ConcurrentModificationException when the modification count changed, then advances and records the returned node. Remove throws IllegalStateException if nothing was returned, removes the last returned node with unlinking, clears that record, and resynchronizes the expected modification count.

<a id="u-b7c469272d8f"></a>
### `LinkedTreeMap.java-node-entries`

`class Node<K, V> implements Entry<K, V>` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L459-L460][f2]

Map entry node used both as the sentinel header and as tree/list elements.

The header constructor makes a self-linked null-key node. A regular constructor stores parent/key, starts height at one, and links itself before the supplied next node and after the supplied previous node; callers pass the sentinel as next and the sentinel's previous node as previous, so new entries land at the end of iteration order. Set-value rejects null when the node disallows null values and returns the old value. Equality compares key and value null-safely only against other entries; hash code XORs key and value hashes; string form is key=value. First and last walk left or right to the subtree extreme.

<a id="u-83b12b3e8273"></a>
### `LinkedTreeMap.java-removal-and-parent-replacement`

`void removeInternal(Node<K, V> node, boolean unlink)` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L235-L292][f2]

Removes a node from the tree and optionally from the iteration list, preserving AVL balance and size/modification state.

If unlinking, it splices the node out of the linked list first. With two children, it recursively removes the taller side's adjacent extreme with unlink false; that recursive call performs rebalance, size decrement, and modification increment. It then attaches the node's remaining children to the adjacent node, fixes that node's height, replaces the original node in its parent, and returns without further rebalance or count changes for the original node. With one or no child, it replaces the node by the child or null, rebalances from the original parent, then decrements size and increments modification count. Key removal returns the removed node or null. Parent replacement clears the old parent link, updates the replacement's parent, and rewires the parent's child pointer or root; it asserts the right-child case when the node is not the left child.

<a id="u-75a742c7d002"></a>
### `LinkedTreeMap.java-serialization-replacement`

`class LinkedTreeMap<K, V> extends AbstractMap<K, V> implements Serializable` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L661-L668][f2]

Serialization hooks for the map.

Serialization replaces the map with a standard linked hash map built from its entries, so the serialized form does not require this class. Direct deserialization is rejected with InvalidObjectException.

<a id="u-7d96c1e624b1"></a>
### `LinkedTreeMap.java-view-sets`

`@Override public Set<Entry<K, V>> entrySet()` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L441-L448][f2]

Returns cached entry-set and key-set views, creating each view lazily on first use.

<a id="u-09ee201cddaa"></a>
### `JsonObject.add`

`public void add(String property, JsonElement value)` · [gson/src/main/java/com/google/gson/JsonObject.java:L69-L71][f1]

Stores the given property and value in the underlying member map.

A null value is replaced with JsonNull.INSTANCE before insertion. The method mutates the object and returns void.

**Uncertainties.**

- The method does not check for a null property name; whether the underlying map rejects it is not shown in this unit.

<a id="u-3c7245fc1690"></a>
### `JsonObject.deepCopy`

`@Override public JsonObject deepCopy()` · [gson/src/main/java/com/google/gson/JsonObject.java:L52-L59][f1]

Creates a new JsonObject and copies every member by adding the same key with a deep copy of the value.

The original object is not modified; member order from the underlying map is preserved.

<a id="u-31bf469912f1"></a>
### `JsonObject.equals`

`@Override public boolean equals(Object o)` · [gson/src/main/java/com/google/gson/JsonObject.java:L246-L249][f1]

Returns true when the other object is the same instance or is a JsonObject whose underlying member map is equal, ignoring order; otherwise returns false.

<a id="u-ad6a2de0018b"></a>
### `JsonObject.hashCode`

`@Override public int hashCode()` · [gson/src/main/java/com/google/gson/JsonObject.java:L255-L258][f1]

Returns the hash code of the underlying member map, consistent with the order-insensitive equality.

<a id="u-7f5fc069485e"></a>
### `JsonObject.remove`

`@CanIgnoreReturnValue public JsonElement remove(String property)` · [gson/src/main/java/com/google/gson/JsonObject.java:L81-L84][f1]

Removes the member with the given name from the underlying map and returns the removed JsonElement, or null when no such member exists.

The object is mutated.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonObject.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java
