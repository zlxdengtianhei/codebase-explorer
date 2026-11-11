# JSON Object and Ordered Map

**Capability.** Implements JsonObject and the LinkedTreeMap that backs it, providing insertion-ordered member storage with AVL-tree lookups.

This module covers the JSON object model and its underlying comparable-key map derived from Android's TreeMap. Readers interested in member ordering, deep copies, mutable map views, or the tree's rebalancing internals should look here.

**Depends on.**

- [Element Types and Tree Adapters](element-types-and-tree-adapters.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Element Types and Tree Adapters](element-types-and-tree-adapters.md) · graph-confirmed · 2 edge(s)

Parent: [JSON Element Tree Model](json-element-tree-model.md)

## Units (30)

<a id="u-3d6ccb718dbc"></a>
### `JsonObject.java-jsonobject`

`class JsonObject extends JsonElement` · [gson/src/main/java/com/google/gson/JsonObject.java:L40-L41][f1]

Ordered, mutable JSON object mapping member names to JsonElement values, backed by a LinkedTreeMap constructed to reject null keys; null values passed to add/addProperty are normalized to JsonNull.

Member order is insertion order. deepCopy produces a new JsonObject whose entries are the deepCopy of each value under the same keys, so nested structures are independent while immutable leaves may be shared.

<a id="u-992ea537c94a"></a>
### `JsonObject.java-jsonobject-add-and-remove`

`class JsonObject extends JsonElement` · [gson/src/main/java/com/google/gson/JsonObject.java:L71-L81][f1]

These regions document add and remove.

add puts a name-value pair into the ordered member map, coercing a null value to JsonNull.INSTANCE; remove deletes the member and returns its previous value, or null when absent.

<a id="u-cc9f6a9621b1"></a>
### `JsonObject.java-jsonobject-addproperty-overloads`

`public void addProperty(String property, String value)` · [gson/src/main/java/com/google/gson/JsonObject.java:L93-L95][f1]

Convenience adders that wrap the value in a JsonPrimitive of the matching type (String, Number, Boolean, Character) and delegate to add.

A null value of any type becomes JsonNull.INSTANCE rather than a primitive, so addProperty("k", (String) null) stores JSON null.

<a id="u-d3726c0bbd60"></a>
### `JsonObject.java-jsonobject-addproperty-overloads-2`

`class JsonObject extends JsonElement` · [gson/src/main/java/com/google/gson/JsonObject.java:L95-L104][f1]

These regions document the four addProperty overloads for String, Number, Boolean, and Character values: each wraps a non-null value in a JsonPrimitive of the matching type and delegates to add, with null converted to JsonNull.INSTANCE.

<a id="u-a8ab9c509c71"></a>
### `JsonObject.java-jsonobject-collection-views-and-size`

`class JsonObject extends JsonElement` · [gson/src/main/java/com/google/gson/JsonObject.java:L138-L146][f1]

These regions document entrySet, keySet, size, and isEmpty, all delegating to the LinkedTreeMap of members; both views preserve insertion order.

<a id="u-cf0dfc62d65d"></a>
### `JsonObject.java-jsonobject-equality`

`@Override public boolean equals(Object o)` · [gson/src/main/java/com/google/gson/JsonObject.java:L246-L249][f1]

Equality holds only for the same instance or another JsonObject whose member maps are equal, which per the doc ignores member order; hashCode delegates to the map's hashCode consistently.

<a id="u-290fc7dcc401"></a>
### `JsonObject.java-jsonobject-has-and-get`

`class JsonObject extends JsonElement` · [gson/src/main/java/com/google/gson/JsonObject.java:L178-L186][f1]

These regions document has and get: has reports whether a member name exists, get returns the member's JsonElement or null when no such member exists.

<a id="u-f988e3baab53"></a>
### `JsonObject.java-jsonobject-read-accessors`

`public Set<Map.Entry<String, JsonElement>> entrySet()` · [gson/src/main/java/com/google/gson/JsonObject.java:L136-L138][f1]

Read-only views delegated to the backing LinkedTreeMap: an insertion-ordered entry set, an ordered key set, pair count, emptiness test, membership check, and value lookup by name.

get returns null when the name is absent; has distinguishes presence (a stored JsonNull still counts as present).

<a id="u-dbf7f70fa829"></a>
### `JsonObject.java-jsonobject-typed-member-access`

`class JsonObject extends JsonElement` · [gson/src/main/java/com/google/gson/JsonObject.java:L200-L210][f1]

These regions document getAsJsonPrimitive, getAsJsonArray, and getAsJsonObject, each a plain cast of the looked-up member: they return null when the name is absent and throw ClassCastException when the member exists but has a different type.

<a id="u-9ede018dca66"></a>
### `JsonObject.java-jsonobject-typed-member-getters`

`public JsonPrimitive getAsJsonPrimitive(String memberName)` · [gson/src/main/java/com/google/gson/JsonObject.java:L198-L200][f1]

Fetch the named member and cast it to JsonPrimitive, JsonArray, or JsonObject respectively.

A missing member yields null (the cast is skipped only because null casts succeed); a member of the wrong type throws ClassCastException. Unlike JsonElement's getAsJsonX, these do not validate with a friendly message.

<a id="u-62dbb5eade8e"></a>
### `LinkedTreeMap.java-basic-map-operations`

`@Override public int size()` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L89-L92][f2]

size() returns the count; get/containsKey delegate to findByObject, returning null/false for missing keys or non-comparable lookups.

put rejects a null key with NullPointerException and a null value when null values are disallowed, then find(key,true) creates or locates the node and swaps the value, returning the old one. clear() nulls the root, resets size, bumps modCount, and resets the header's links to itself. remove() removes by key and returns the old value or null.

<a id="u-f93675f4c02b"></a>
### `LinkedTreeMap.java-entryset`

`class EntrySet extends AbstractSet<Entry<K, V>>` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L590-L591][f2]

View of the map's entries: size delegates to the map; iterator yields nodes via nextNode; contains requires an Entry matching by findByEntry; remove returns false for non-Entry or absent entries, otherwise removes the matched node with unlinking and returns true; clear delegates to the map's clear.

<a id="u-a415b7b2872f"></a>
### `LinkedTreeMap.java-keyset`

`class KeySet extends AbstractSet<K>` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L631-L632][f2]

View of the map's keys: size delegates; iterator yields node keys via nextNode; contains delegates to containsKey; remove removes by key and reports whether anything was removed; clear delegates to the map.

<a id="u-b9c5328e4fd9"></a>
### `LinkedTreeMap.java-linkedtreemap-class-and-constructors`

`class LinkedTreeMap<K, V> extends AbstractMap<K, V> implements Serializable` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L43-L48][f2]

A serializable map of comparable keys that iterates in insertion order while using comparison order only as an AVL-tree optimization, derived from Android's TreeMap.

It holds a comparator (null means natural ordering via direct compareTo), an allowNullValues flag, tree root, size, modCount, and a sentinel header node preserving iteration order. Constructors: no-arg uses natural order and allows null values; single-boolean sets null-value policy; two-arg sets comparator and null-value policy, creating the header sentinel.

<a id="u-456f19a828b0"></a>
### `LinkedTreeMap.java-linkedtreemap-javadoc-regions`

`class LinkedTreeMap<K, V> extends AbstractMap<K, V> implements Serializable` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L135-L142][f2]

These symbols are source regions of LinkedTreeMap containing only javadoc comments that precede the tree-navigation, removal, and rebalancing methods; they hold no executable statements, fields, or types of their own.

Any behavior attributed to them belongs to the methods documented immediately after each region.

**Uncertainties.**

- The symbol list labels these as 'class LinkedTreeMap' regions, but the supplied source at the corresponding lines shows only comment text; if the extractor intended a different construct, that construct is not visible in the provided source.

<a id="u-9aa0153e872e"></a>
### `LinkedTreeMap.java-linkedtreemapiterator`

`class LinkedTreeMapIterator<T> implements Iterator<T>` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L552-L553][f2]

Base iterator over the linked list starting at header.next, snapshotting modCount.

hasNext checks next != header. nextNode throws NoSuchElementException at the end and ConcurrentModificationException on structural modification since creation, then advances and records lastReturned. remove() throws IllegalStateException if no element was returned, removes that node with unlinking, and re-syncs expectedModCount so removal during iteration is legal.

<a id="u-acb69d907264"></a>
### `LinkedTreeMap.java-lookup-helpers`

`@SuppressWarnings("unchecked") Node<K, V> findByObject(Object key)` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L203-L210][f2]

findByObject safely looks up any Object key: null returns null and ClassCastException is swallowed to null.

findByEntry matches an Entry by comparator-based key lookup plus Objects.equals on values, returning the map's node only if both match — so a comparator inconsistent with equals makes remove/contains violate the collections contract, as documented.

<a id="u-9528d4531bf8"></a>
### `LinkedTreeMap.java-node`

`class Node<K, V> implements Entry<K, V>` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L459-L460][f2]

Tree/entry node holding parent, left, right, height, key, value, and next/prev links for iteration order.

The header constructor makes a self-linked sentinel with null key; the regular constructor links itself between prev and next and sets height 1. getKey/getValue are trivial; setValue rejects null when allowNullValue is false (NullPointerException) and returns the old value. equals compares key and value with null-safe equals against another Entry; hashCode XORs null-safe key/value hashes; toString is key=value. first()/last() descend left/right to the subtree's extreme node.

<a id="u-c6ed22c3bfe1"></a>
### `LinkedTreeMap.java-removal-plumbing`

`Node<K, V> removeInternalByKey(Object key)` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L294-L300][f2]

removeInternalByKey finds the node by key and removes it with unlinking, returning it or null.

replaceInParent detaches the node's parent pointer and splices a replacement (possibly null) into the parent's left/right slot by reference equality, or makes it the root when the parent is null; an assertion checks the node was the parent's right child when not the left.

<a id="u-826588df6d62"></a>
### `LinkedTreeMap.java-rotations`

`private void rotateLeft(Node<K, V> root)` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L389-L411][f2]

rotateLeft makes the root's right child (pivot) the new subtree root: the pivot's left child moves to the root's right, the root becomes the pivot's left child, replaceInParent splices the pivot in, and both heights are recomputed bottom-up.

rotateRight is the mirror with the left child as pivot. Both assume the pivot exists (callers only invoke under imbalance).

<a id="u-fec7fbc0fd50"></a>
### `LinkedTreeMap.java-serialization`

`class LinkedTreeMap<K, V> extends AbstractMap<K, V> implements Serializable` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L661-L668][f2]

Java serialization is deliberately redirected: writeReplace() returns a LinkedHashMap copy so the peer needs no Gson, and readObject() always throws InvalidObjectException because direct deserialization of this class is unsupported.

The comment notes serialization defeats the class's DoS defense.

<a id="u-94f6c1e1ceb4"></a>
### `LinkedTreeMap.java-set-views`

`@Override public Set<Entry<K, V>> entrySet()` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L441-L448][f2]

entrySet() and keySet() lazily create and memoize their respective view objects, returning the same instance on repeated calls.

<a id="u-173faeb636e5"></a>
### `gson/src/main/java/com/google/gson/JsonObject.java:JsonObject (11)`

`class JsonObject extends JsonElement` · [gson/src/main/java/com/google/gson/JsonObject.java:L240-L246][f1]

This region documents asMap, which directly exposes the underlying LinkedTreeMap as a mutable Map view; changes are bidirectionally visible, and the map rejects null keys and values with NullPointerException rather than coercing them, so JsonNull must be used explicitly.

<a id="u-f4f476d95b1d"></a>
### `gson/src/main/java/com/google/gson/JsonObject.java:JsonObject (15)`

`class JsonObject extends JsonElement` · [gson/src/main/java/com/google/gson/JsonObject.java:L59-L69][f1]

This region documents JsonObject.deepCopy, which builds a new JsonObject and re-adds every entry with a recursively deep-copied value, preserving insertion order.

<a id="u-09ee201cddaa"></a>
### `JsonObject.add`

`public void add(String property, JsonElement value)` · [gson/src/main/java/com/google/gson/JsonObject.java:L69-L71][f1]

Adds or replaces a member: puts the value under the property name, converting a null value to JsonNull.INSTANCE.

Re-adding an existing name overwrites the previous value (the map's put semantics); a null property key is rejected by the underlying map.

<a id="u-efd687a1683b"></a>
### `JsonObject.asMap`

`public Map<String, JsonElement> asMap()` · [gson/src/main/java/com/google/gson/JsonObject.java:L237-L240][f1]

Returns the underlying LinkedTreeMap directly as a mutable Map view, so changes are immediately visible in the JsonObject and vice versa.

The map rejects null keys and values with NullPointerException, which the comment cites as the reason exposing it is safe; use JsonNull for JSON null.

<a id="u-7f5fc069485e"></a>
### `JsonObject.remove`

`@CanIgnoreReturnValue public JsonElement remove(String property)` · [gson/src/main/java/com/google/gson/JsonObject.java:L81-L84][f1]

Removes the member with the given name and returns its value, or null when no such member exists.

Delegates to the backing map's remove.

<a id="u-6410d671180a"></a>
### `LinkedTreeMap.find`

`Node<K, V> find(K key, boolean create)` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L142-L201][f2]

Returns the node at or adjacent to the given key, optionally creating it.

Walks from the root comparing via the key's compareTo (natural order) or the comparator; equal comparison returns the existing node. Without create, a miss returns null. With create, a new node is linked before the header's prev (end of iteration order); if the tree was empty and no comparator exists, the key must be Comparable or a ClassCastException is thrown; otherwise the node becomes the appropriate child of the nearest node and rebalance(nearest, true) runs. Insertion increments size and modCount. Non-comparable keys throw ClassCastException during comparison.

<a id="u-5ee8b6d95269"></a>
### `LinkedTreeMap.rebalance`

`private void rebalance(Node<K, V> unbalanced, boolean insert)` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L328-L386][f2]

Rebalances the AVL tree walking from the unbalanced node toward the root, fixing heights.

Delta -2 (right-heavy): single rotateLeft when the right child's own delta is -1, or 0 on removal; otherwise rotateRight(right) then rotateLeft(node). Delta +2 is the mirror image. Delta 0 sets height to leftHeight+1 and stops after an insert; delta ±1 sets height to max+1 and stops after a removal (height unchanged). After a rotation during insert, no further rotations are needed, so the loop breaks; removals continue up the path.

<a id="u-5e94275610c7"></a>
### `LinkedTreeMap.removeInternal`

`void removeInternal(Node<K, V> node, boolean unlink)` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L235-L292][f2]

Removes a node from the AVL tree and optionally unlinks it from the iteration list.

With both children, it recursively removes (without unlinking) the adjacent node from the taller subtree — left.last() or right.first() — then re-attaches the victim's possibly-changed subtrees to that adjacent node, recomputes its height, and replaces it in the parent, returning early (the recursive call already rebalanced and decremented size). With one child the child replaces the node; with none the parent link becomes null. The single-child/leaf path then rebalances from the original parent as a removal and decrements size and modCount.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonObject.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java
