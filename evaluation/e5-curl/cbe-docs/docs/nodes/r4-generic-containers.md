# Generic hash and list containers

**Capability.** The reusable in-memory container implementations used across the library: a seeded generic hash table with typed key hashing/comparison, element lifecycle and iterators, plus the intrusive doubly linked list header.

Treat these as infrastructure consumed by feature modules (e.g. the multi socket hash). The hash supports BYTE and SOCKET key types with per-element destructors and lazy table allocation; llist.h declares the linked-list API.

**Depended on by.**

- [Multi socket events](r4-multi-event.md) · graph-confirmed · 5 edge(s)

Parent: [curl source tree](r4-curl.md)

## Units (29)

<a id="u-8441449b9d19"></a>
### `Curl_hash_add2`

`void *Curl_hash_add2(struct Curl_hash *h, const void *key, size_t key_len, void *p, C…` · [lib/hash.c:L291-L327][f1]

Inserts or replaces a value for a key with an optional per-element destructor.

Invalid key lengths return NULL. The bucket table is lazily calloc'ed on first insert; allocation failure returns NULL. The bucket is hashed, then scanned: on an existing equal key the old pointer is cleared through hash_elem_clear_ptr (running the old dtor), the stored pointer and dtor are overwritten with the new values, and p is returned. Otherwise hash_elem_create allocates a new element; NULL on OOM; the element is linked at the chain head and p is returned. DEBUGBUILD asserts initialization and nonzero slots.

**Notes.**

- failure: Both invalid key length and allocation failure are reported only by a NULL return; callers cannot distinguish them.

calls: [hash_key_is_valid](r4-generic-containers.md#u-92847f233a34), [hash_get_functions](r4-generic-containers.md#u-6737990b315d), [hash_elem_clear_ptr](r4-generic-containers.md#u-74957ab94165), [hash_elem_create](r4-generic-containers.md#u-9b481ae1d198), [hash_elem_link](r4-generic-containers.md#u-6d4eb7867563); contract: [Curl_hash_add](r4-generic-containers.md#u-2b0745caec1d)

<a id="u-2b0745caec1d"></a>
### `Curl_hash_add`

`void *Curl_hash_add(struct Curl_hash *h, const void *key, size_t key_len, void *p)` · [lib/hash.c:L337-L341][f1]

Convenience wrapper inserting a value with the hash-level destructor only, by calling Curl_hash_add2 with a NULL per-element dtor; its return value semantics are identical.

calls: [Curl_hash_add2](r4-generic-containers.md#u-8441449b9d19)

<a id="u-96a1e754ffac"></a>
### `Curl_hash_clean`

`void Curl_hash_clean(struct Curl_hash *h)` · [lib/hash.c:L424-L439][f1]

Removes every entry: a NULL hash or NULL table is a no-op.

Otherwise each slot's chain is drained from the head via an anchor pointer, unlinking (decrementing size) and destroying each element so its destructor runs. DEBUGBUILD asserts initialization.

calls: [hash_elem_unlink](r4-generic-containers.md#u-26a8d4de1c26), [hash_elem_destroy](r4-generic-containers.md#u-24466a09e09c)

<a id="u-a39cbcc6ceda"></a>
### `Curl_hash_clean_with_criterium`

`void Curl_hash_clean_with_criterium(struct Curl_hash *h, void *user, int (*comp)(void…` · [lib/hash.c:L448-L470][f1]

Selectively removes entries: a NULL hash or NULL table returns immediately.

Each chain is walked with an anchor; an entry is unlinked and destroyed when comp is NULL (behaving like a full clean) or comp(user, ptr) returns nonzero; otherwise the anchor advances past it, so surviving entries keep their order. DEBUGBUILD asserts initialization.

calls: [hash_elem_unlink](r4-generic-containers.md#u-26a8d4de1c26), [hash_elem_destroy](r4-generic-containers.md#u-24466a09e09c)

<a id="u-de5497d63974"></a>
### `Curl_hash_count`

`size_t Curl_hash_count(struct Curl_hash *h)` · [lib/hash.c:L441-L445][f1]

Returns the maintained h->size counter; DEBUGBUILD asserts initialization.

The table pointer is not consulted, so the count reflects inserts/deletes, not the table allocation state.

<a id="u-b8312f0e5e92"></a>
### `Curl_hash_delete`

`int Curl_hash_delete(struct Curl_hash *h, const void *key, size_t key_len)` · [lib/hash.c:L348-L373][f1]

Removes the entry matching a key and returns 0 on success, 1 on failure.

Invalid key length returns 1 immediately. If the table was never allocated it returns 1. Otherwise the bucket is hashed and the chain walked via an anchor pointer: on the first equal key the element is unlinked (size decremented), destroyed (running its dtor), and 0 returned; exhausting the chain returns 1. DEBUGBUILD asserts initialization and nonzero slots.

calls: [hash_key_is_valid](r4-generic-containers.md#u-92847f233a34), [hash_get_functions](r4-generic-containers.md#u-6737990b315d), [hash_elem_unlink](r4-generic-containers.md#u-26a8d4de1c26), [hash_elem_destroy](r4-generic-containers.md#u-24466a09e09c)

<a id="u-5e8ba01b3862"></a>
### `Curl_hash_destroy`

`void Curl_hash_destroy(struct Curl_hash *h)` · [lib/hash.c:L409-L418][f1]

Tears a hash down for reuse or deallocation: if a table exists, all entries are cleaned via Curl_hash_clean and the table freed with curlx_safefree; then slots is zeroed.

DEBUGBUILD asserts initialization and, after cleaning, that size reached 0. The struct itself is not freed and other fields are not reset.

calls: [Curl_hash_clean](r4-generic-containers.md#u-96a1e754ffac); uses: [Curl_hash_count](r4-generic-containers.md#u-de5497d63974)

<a id="u-36ff0a136417"></a>
### `Curl_hash_global_init`

`CURLcode Curl_hash_global_init(void)` · [lib/hash.c:L59-L84][f1]

Initializes the process-wide hash seed exactly once.

A static 'seeded' flag short-circuits repeat calls with CURLE_OK. It obtains sizeof(size_t) random bytes from Curl_rand_bytes, propagating any CURLcode failure, assembles them big-endian into a seed, and stores a nonzero seed (substituting 1 if randomness yielded zero) into the static hash_seed, read-only afterwards. Passing NULL to Curl_rand_bytes indicates no easy handle context; the DEBUGBUILD FALSE argument presumably disables a deterministic/test mode.

**Notes.**

- side_effect: Sets the file-static hash_seed once; subsequent calls are no-ops returning CURLE_OK.

calls: [Curl_rand_bytes](r10-misc-utilities.md#u-c3e86a9c4806)

**Uncertainties.**

- Behavior of Curl_rand_bytes with a NULL handle is defined in lib/rand.c, not visible here.

<a id="u-90f5f7290602"></a>
### `Curl_hash_init`

`void Curl_hash_init(struct Curl_hash *h, size_t slots, Curl_hash_type type, Curl_hash…` · [lib/hash.c:L213-L231][f1]

Initializes a hash in place: clears the table pointer (lazy allocation happens on first add), stores the destructor, slot count, and type, and zeroes size.

DEBUGBUILD stamps h->init with HASHINIT so later API calls can DEBUGASSERT correct initialization. No allocation occurs and no return value is produced.

contract: [Curl_hash_add2](r4-generic-containers.md#u-8441449b9d19)

<a id="u-a96afb4c17d8"></a>
### `Curl_hash_next_element`

`struct Curl_hash_element *Curl_hash_next_element( struct Curl_hash_iterator *iter)` · [lib/hash.c:L484-L510][f1]

Advances an iterator and returns the next element, or NULL when exhausted or the table is unallocated.

It first steps to current->next within the current chain; if that ends the chain, it scans slots from slot_index forward for the first nonempty bucket, setting current to its head and slot_index to the bucket after it. DEBUGBUILD asserts the iterator's ITERINIT stamp, so iteration without a prior start call fails an assert in debug builds.

**Uncertainties.**

- Whether an iterator can be safely reused after the hash is modified during iteration is not established by this code.

<a id="u-b27c1a441dda"></a>
### `Curl_hash_pick`

`void *Curl_hash_pick(struct Curl_hash *h, const void *key, size_t key_len)` · [lib/hash.c:L379-L400][f1]

Looks up a value by key and returns its stored pointer, or NULL when the key length is invalid, the table is unallocated, or no element compares equal.

The bucket is hashed and the chain scanned with the type's comparator; the first match's ptr is returned. DEBUGBUILD asserts initialization (and slots only when the table exists).

calls: [hash_key_is_valid](r4-generic-containers.md#u-92847f233a34), [hash_get_functions](r4-generic-containers.md#u-6737990b315d)

<a id="u-8ffb0a3f3bcf"></a>
### `Curl_hash_print`

`void Curl_hash_print(struct Curl_hash *h, void (*func)(void *))` · [lib/hash.c:L172-L205][f1]

Debug dump function compiled out by '#if 0': when enabled it would print each bucket and element key/pointer (or apply a caller callback) to stderr via a hash iterator.

**Uncertainties.**

- As written it is not compiled and has no runtime effect.

<a id="u-c0cf53da9f6a"></a>
### `Curl_hash_start_iterate`

`void Curl_hash_start_iterate(struct Curl_hash *hash, struct Curl_hash_iterator *iter)` · [lib/hash.c:L472-L482][f1]

Positions an iterator at the start of a hash: stores the hash pointer, resets slot_index to 0 and current to NULL, and stamps ITERINIT in DEBUGBUILD for later assertion.

<a id="u-6ced9ea38f4b"></a>
### `compare_bytes`

`static size_t compare_bytes(const void *key1, size_t key1_len, const void *key2, size…` · [lib/hash.c:L145-L149][f1]

Byte-wise key comparison: returns 1 only when both lengths are equal and memcmp over key1_len bytes reports no difference.

<a id="u-7ca519d3a328"></a>
### `compare_socket`

`static size_t compare_socket(const void *key1, size_t key1_len, const void *key2, siz…` · [lib/hash.c:L132-L143][f1]

Compares two socket keys: returns 0 (no match) if either length differs from sizeof(curl_socket_t), otherwise 1 iff the copied descriptors are equal.

<a id="u-74957ab94165"></a>
### `hash_elem_clear_ptr`

`static void hash_elem_clear_ptr(struct Curl_hash *h, struct Curl_hash_element *he)` · [lib/hash.c:L253-L265][f1]

Releases the entry's stored pointer.

If ptr is set, the per-element dtor is called with (key bytes, key_len, ptr) when present; otherwise the hash-level dtor receives only ptr. Then ptr is NULLed. Elements with a NULL ptr and NULL per-element dtor fall back to the hash dtor only when ptr is non-NULL.

<a id="u-9b481ae1d198"></a>
### `hash_elem_create`

`static struct Curl_hash_element *hash_elem_create(const void *key, size_t key_len, vo…` · [lib/hash.c:L233-L251][f1]

Allocates a hash element with key_len extra bytes appended and copies the key after the header, initializing next to NULL and storing ptr and the per-element destructor dtor.

Returns NULL on allocation failure.

calls: [hash_elem_key](r4-generic-containers.md#u-7e0248a10bdb)

<a id="u-24466a09e09c"></a>
### `hash_elem_destroy`

`static void hash_elem_destroy(struct Curl_hash *h, struct Curl_hash_element *he)` · [lib/hash.c:L267-L272][f1]

Frees an element: invokes hash_elem_clear_ptr to run the applicable destructor, then curlx_free on the element itself.

calls: [hash_elem_clear_ptr](r4-generic-containers.md#u-74957ab94165)

<a id="u-7e0248a10bdb"></a>
### `hash_elem_key`

`static char *hash_elem_key(struct Curl_hash_element *he)` · [lib/hash.c:L115-L118][f1]

Returns a pointer to the key bytes stored immediately after the Curl_hash_element header, computed via offsetof so the flexible trailing key[1] member is not treated as a one-byte object.

<a id="u-6d4eb7867563"></a>
### `hash_elem_link`

`static void hash_elem_link(struct Curl_hash *h, struct Curl_hash_element **he_anchor,…` · [lib/hash.c:L282-L289][f1]

Inserts an element at the front of a chain via the anchor pointer and increments the hash size.

<a id="u-26a8d4de1c26"></a>
### `hash_elem_unlink`

`static void hash_elem_unlink(struct Curl_hash *h, struct Curl_hash_element **he_ancho…` · [lib/hash.c:L274-L280][f1]

Removes an element from its chain by rewiring the caller-provided anchor pointer to he->next and decrements the hash size; no destructor is run here.

<a id="u-6737990b315d"></a>
### `hash_get_functions`

`static const struct hash_functions *hash_get_functions(uint8_t type)` · [lib/hash.c:L156-L162][f1]

Maps a hash type to its function pair from the static hash_functions table.

DEBUGBUILD asserts the table covers all types; a type value at or beyond CURL_HASH_TYPE_LAST falls back to the BYTES pair, so an invalid type silently behaves as a byte-keyed hash.

uses: [hash_functions](r4-generic-containers.md#u-f44d5e86aff7)

<a id="u-92847f233a34"></a>
### `hash_key_is_valid`

`static bool hash_key_is_valid(uint8_t type, size_t key_len)` · [lib/hash.c:L164-L169][f1]

Validates a key length for a hash type: BYTES accepts any length; SOCKET accepts only exactly sizeof(curl_socket_t); other types are never valid.

<a id="u-b78260497367"></a>
### `hash_socket`

`static size_t hash_socket(const void *key, size_t key_length, size_t slots_num)` · [lib/hash.c:L120-L130][f1]

Hashes a socket descriptor key.

DEBUGASSERT requires key_length == sizeof(curl_socket_t); in release builds a mismatched length returns 0 instead. Otherwise the descriptor bytes are copied in and reduced modulo slots_num via signed curl_socket_t arithmetic.

**Uncertainties.**

- Negative curl_socket_t values would yield negative modulo results cast to size_t; behavior depends on the platform socket type.

<a id="u-806746f50889"></a>
### `hash_str`

`UNITTEST size_t hash_str(const void *key, size_t key_length, size_t slots_num)` · [lib/hash.c:L109-L112][f1]

Seeds hash_str_seeded with the global hash_seed, so results are nondeterministic across runs unless seeded (deterministic before global init would use seed 0).

calls: [hash_str_seeded](r4-generic-containers.md#u-4ca9a6a98056)

<a id="u-4ca9a6a98056"></a>
### `hash_str_seeded`

`UNITTEST size_t hash_str_seeded(const void *key, size_t key_length, size_t slots_num,…` · [lib/hash.c:L90-L104][f1]

DJBX33X-style string hash over key_length bytes starting from 5381 XORed with the seed, returning the value modulo slots_num.

Marks an entry at the slot equal to the hash; a zero-length key hashes to the seeded constant.

<a id="u-a10c8d057bdd"></a>
### `hash.c module code (L1–L50)`

`module_region` · [lib/hash.c:L1-L50][f1]

License header and includes for the generic hash table implementation, plus debug-only magic constants HASHINIT and ITERINIT used to detect uninitialized hash or iterator use.

<a id="u-f44d5e86aff7"></a>
### `hash_functions`

`struct hash_functions` · [lib/hash.c:L51-L54][f1]

Type definitions: hash_function and comp_function callbacks, a compile-time array assertion that hash type values fit in uint8_t, and the struct hash_functions pair binding a hash function to a comparator per hash type.

uses: [hash_get_functions](r4-generic-containers.md#u-6737990b315d), [Curl_hash_init](r4-generic-containers.md#u-90f5f7290602)

<a id="u-e947a3c088b0"></a>
### `Curl_llist`

`struct Curl_llist` · [lib/llist.h:L33-L41][f2]

Header declaring the intrusive doubly linked list and its node types plus accessor API.

**Notes.**

- contract: Both structs carry a DEBUGBUILD-only _init marker intended to detect API misuse; members are documented as private to the dedicated llist functions.
- field: Curl_llist holds head/tail pointers, a Curl_llist_dtor callback, and a size counter; Curl_llist_node links back to its owning list and stores prev/next plus a void payload pointer.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/hash.c
[f2]: ../../../../../../eval/curl-2c04412/lib/llist.h
