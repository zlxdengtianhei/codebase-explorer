# Insertion-Ordered AVL Map

**Capability.** A Map of comparable keys that keeps iteration in insertion order while using key comparison only to balance an AVL tree; nodes double as entries and link into an iteration list, with lookup, rebalancing, and view/iterator machinery.

Use this as the backing store where order preservation plus efficient keyed access are both required (JsonObject). Note writeReplace serializes it as a plain LinkedHashMap, which the source warns weakens its collision DoS defense.

**Depended on by.**

- [JSON DOM Tree](r2-dom-tree.md) · graph-only · 11 edge(s)

Parent: [Internal Utilities and Data Structures](r2-infrastructure.md)

## Units (10)

<a id="u-603f4565d5fe"></a>
### `LinkedTreeMap`

`class LinkedTreeMap<K, V> extends AbstractMap<K, V> implements Serializable` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L43-L62][f1]

Map of comparable keys to values that iterates in insertion order while using key comparison only to structure an AVL tree for efficient put/get/remove.

Three constructors share one: no-arg and (boolean allowNullValues) both use natural ordering (null comparator), with allowNullValues defaulting to true; the full constructor stores the comparator, the null-value policy, and a self-linked header Node that anchors iteration order. size/get/containsKey are thin counts and findByObject lookups (get returns the node's value or null). put throws NullPointerException for a null key and, unless allowNullValues, for a null value, then inserts or updates via find and returns the old value. clear resets root and size, bumps modCount, and re-links header to itself. remove delegates to removeInternalByKey and returns the removed value or null. entrySet and keySet lazily create and cache their view objects. Serialization is handled by writeReplace/readObject covered separately.

calls: [LinkedTreeMap.find](r2-linkedtreemap.md#u-6410d671180a), [LinkedTreeMap.removeInternal](r2-linkedtreemap.md#u-5e94275610c7)

<a id="u-6410d671180a"></a>
### `LinkedTreeMap.find`

`Node<K, V> find(K key, boolean create)` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L142-L201][f1]

Core tree descent: returns the node with the given key, or its would-be parent neighborhood, creating and inserting a node when create is true.

With a null comparator the key is cast to Comparable and compared directly; a bad cast surfaces as ClassCastException. The loop stops at an exact match (comparison 0, returned immediately) or at a missing child. If not creating, it returns null. When creating: if the tree was empty it checks that natural-order keys implement Comparable, throwing ClassCastException naming the key's class otherwise, then makes the new node the root; otherwise the new node becomes left or right child of the nearest node depending on the sign of the last comparison, and rebalance(nearest, true) runs. New nodes are spliced into the header's circular list just before the header (append at end), preserving insertion order; size and modCount increment on any creation.

calls: [linkedtreemap.java-avl-rebalance-rotations](r2-linkedtreemap.md#u-7ece693173be)

<a id="u-5e94275610c7"></a>
### `LinkedTreeMap.removeInternal`

`void removeInternal(Node<K, V> node, boolean unlink)` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L235-L292][f1]

Removes a node from the tree, optionally also from the iteration list.

When unlink is true the node's list neighbors are re-linked around it. If the node has two children, the adjacent in-order node from the taller subtree (left.last() or right.first()) is removed first via removeInternal(adjacent, false), which handles rebalancing, size--, and modCount; then the saved children are reattached under the adjacent node, its height is recomputed, and replaceInParent puts it in the removed node's place — the method returns here, skipping the common tail. For zero or one child it replaces the node with the surviving child or null via replaceInParent, then rebalances from the original parent, decrements size, and bumps modCount. removeInternalByKey finds the node with findByObject (swallowing incomparable keys as null), removes it with unlink=true, and returns the node or null.

<a id="u-487bcd60fa0c"></a>
### `Node`

`class Node<K, V> implements Entry<K, V>` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L459-L471][f1]

Tree node doubling as a Map.Entry, with AVL fields (parent/left/right/height) and iteration-list links (next/prev).

The one-argument constructor builds the header sentinel: null key, self-linked next/prev. The regular constructor sets height 1 and splices the node into the circular list by updating the given next/prev neighbors. setValue rejects null values with NullPointerException(

<a id="u-d4683593a3b0"></a>
### `EntrySet`

`class EntrySet extends AbstractSet<Entry<K, V>>` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L590-L591][f1]

Live entry-set view over the map.

size reports the map's size; iterator returns a LinkedTreeMapIterator whose next yields the node itself as an Entry. contains accepts only Entry instances and matches via findByEntry, i.e. comparator-based key identity plus value equality. remove likewise requires an Entry, finds the matching node, and removes it with unlink=true, returning false when no match exists. clear delegates to the outer map's clear. All mutations go through the map, keeping the view consistent with modCount-based fail-fast iteration.

<a id="u-ca11a80db8a7"></a>
### `KeySet`

`class KeySet extends AbstractSet<K>` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L631-L632][f1]

Live key-set view over the map.

size reports the map's size; the iterator's next returns nextNode().key. contains delegates to containsKey (comparator-based lookup, tolerant of incomparable or null keys via findByObject). remove delegates to removeInternalByKey and reports whether a node was found. clear delegates to the outer map's clear.

<a id="u-221658191923"></a>
### `LinkedTreeMapIterator`

`class LinkedTreeMapIterator<T> implements Iterator<T>` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L552-L557][f1]

Shared fail-fast iterator base for both views.

It starts at header.next, tracks the last returned node, and snapshots modCount. hasNext is simply next != header. nextNode throws NoSuchElementException when exhausted, then throws ConcurrentModificationException if modCount changed since the snapshot (the exhaustion check runs first, so an exhausted modified iterator reports NoSuchElementException); otherwise it advances next and records lastReturned. remove requires a prior next (IllegalStateException otherwise), removes the node via removeInternal with unlink=true, clears lastReturned, and resynchronizes expectedModCount so continued iteration is allowed.

<a id="u-7ece693173be"></a>
### `linkedtreemap.java-avl-rebalance-rotations`

`@SuppressWarnings("ReferenceEquality") private void replaceInParent(Node<K, V> node, …` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L302-L320][f1]

AVL maintenance.

rebalance walks from an unbalanced node toward the root recomputing heights and rotating where needed: a height delta of -2 rotates left when the right child leans right (rightDelta -1, or 0 after a removal), otherwise performs a right rotation on the right child followed by a left rotation; symmetrically for delta 2 on the left side; after an insert one fix suffices and the loop breaks, while after a removal it continues to the root. A delta of 0 just sets the height (insertion is then done); deltas ±1 set the taller height and, on removal, indicate no height change so the loop breaks. rotateLeft and rotateRight each promote the respective child to the subtree root via replaceInParent, move the old root beneath it, reattach the pivot's inner child to the old root, and recompute both heights; replaceInParent rewrites the parent's child pointer (or root), clearing the removed node's parent pointer.

<a id="u-f27a96de7fe4"></a>
### `linkedtreemap.java-lookup-helpers`

`@SuppressWarnings("unchecked") Node<K, V> findByObject(Object key)` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L203-L210][f1]

Lookup helpers with deliberately lenient failure semantics.

findByObject maps a null key to null and otherwise calls find(key, false); it catches ClassCastException from incomparable keys and returns null instead of propagating, so get/containsKey never throw for bad key types. findByEntry locates this map's node for the entry's key and requires Objects.equals on the values; note it uses the comparator (not key equals) for key identity, so for comparators inconsistent with equals, contains/remove on views can violate the collections API contract.

<a id="u-4e09cb30fe62"></a>
### `linkedtreemap.java-serialization-replacement`

`private Object writeReplace() throws ObjectStreamException` · [gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java:L668-L670][f1]

Serialization is redirected: writeReplace returns a plain LinkedHashMap copy of this map, so the serialized form is a standard map readable without Gson on the other side (and, as the comment warns, defeats the map's DoS defense if used).

readObject always throws InvalidObjectException, so direct deserialization of LinkedTreeMap is impossible; the replacement mechanism is the only supported path.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/LinkedTreeMap.java