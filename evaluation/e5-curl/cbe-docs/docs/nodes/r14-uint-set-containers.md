# Integer/String Set Containers

**Capability.** Owns the header-declared set containers (u32-keyed pointer set, u8-keyed string hash set, dense uint32 bitset) and the sparse-paged bitset implementation with chunked storage, iteration and membership operations.

Use these subtrees as generic data-structure building blocks; they expose init/add/remove/contains/iterate APIs independent of any protocol. The sparse bitset implementation organizes storage in offset-ordered chunks with reuse of empty chunks.

Parent: [curl Codebase](r14-curl-codebase.md)

## Units (20)

<a id="u-006d00705cf7"></a>
### `u32_ptrset.h module code (L1–L34)`

`module_region` · [lib/u32_ptrset.h:L1-L34][f1]

Header declaring the u32_ptrset API: a destructor type taking (id, ptr) and prototypes for init, clear, count, get, set, unset, and visit, plus the visit callback typedef.

Included by the implementation.

<a id="u-d8b9eb95c40c"></a>
### `u32_ptrset.h module code (L46–L70)`

`module_region` · [lib/u32_ptrset.h:L46-L70][f1]

Remainder of the header: function prototypes, destructor and visit-callback typedefs, and include guard.

Non-behavioral declarations only.

<a id="u-5b6acd93d8a1"></a>
### `u32_ptrset`

`struct u32_ptrset` · [lib/u32_ptrset.h:L35-L46][f1]

Struct u32_ptrset holds parallel arrays for pointers, ids, and probe sequence lengths, a slotmask for index computation, the entry count, an optional per-entry destructor, and slotbits controlling capacity.

In debug builds an int32_t init field stores a magic value so public entry points can assert proper initialization. Documented contract: setting a pointer for an existing id replaces it, get of an absent id returns NULL, and setting NULL unsets the id.

**Uncertainties.**

- Header claims capacity up to INT32_MAX+1 pointers; the implementation's grow limit at slotbits 31 caps differently, per the .c uncertainty.

<a id="u-9cf5d076bbb7"></a>
### `u8_strset`

`struct u8_strset` · [lib/u8_strset.h:L47-L60][f2]

Defines a Robin Hood hash set holding up to 256 strings keyed by 8-bit ids, with inline initial storage of 8 slots.

Fields data/ids/psl point at either the embedded sdata/sids/spsl arrays or a heap block laid out as slots string pointers followed by slots ids and slots psl bytes (the layout u8_strset_grow allocates). psl stores each entry's probe-sequence length for Robin Hood balancing; count tracks live entries; slotbits/slotmask give current capacity 1<<slotbits and its index mask. Under DEBUGBUILD, init holds a magic stamp checked by DEBUGASSERT. The header documents the contract: setting an existing id replaces its value, setting NULL unsets, and getting a missing id returns NULL.

contract: [Curl_u8_strset_init](r11-u8-strset.md#u-8d42139e9194); group: [u8_strset](r14-uint-set-containers.md#u-9cf5d076bbb7)

<a id="u-a2ea9410f68f"></a>
### `uint32_bset`

`struct uint32_bset` · [lib/uint-bset.h:L40-L47][f3]

Data layout of the 64-bit-word bitset: a malloc'd slots array of uint64_t, the slot count nslots (capacity is nslots*64 values), first_slot_used as a scan-start hint maintained by add/first/clear, and in debug builds an init magic for use-after-free detection.

<a id="u-a1249ff289c7"></a>
### `Curl_uint32_spbset_add`

`bool Curl_uint32_spbset_add(struct uint32_spbset *bset, uint32_t i)` · [lib/uint-spbset.c:L181-L192][f4]

Sets the bit for value i, returning TRUE on success.

It obtains the chunk with grow=TRUE, so a missing chunk is created or reused; NULL (allocation failure) returns FALSE without setting the bit. The index is rebased by the chunk offset (debug-asserted non-negative and in range) and the corresponding 64-bit slot word is OR-ed with the bit.

calls: [uint32_spbset_get_chunk](r14-uint-set-containers.md#u-29a56371cdd9)

<a id="u-5f5ec85bc21a"></a>
### `Curl_uint32_spbset_contains`

`bool Curl_uint32_spbset_contains(struct uint32_spbset *bset, uint32_t i)` · [lib/uint-spbset.c:L205-L215][f4]

Tests membership of i: returns FALSE when the covering chunk does not exist, otherwise TRUE exactly when the rebased slot bit is set.

calls: [uint32_spbset_get_chunk](r14-uint-set-containers.md#u-29a56371cdd9)

<a id="u-aefe6f3b48a0"></a>
### `Curl_uint32_spbset_count`

`uint32_t Curl_uint32_spbset_count(struct uint32_spbset *bset)` · [lib/uint-spbset.c:L63-L75][f4]

Returns the number of set bits by walking every chunk and every slot word, adding CURL_POPCOUNT64 of each nonzero slot.

Chunks whose offset makes them unreachable are still counted, since the walk follows the linked list only.

uses: [Curl_popcount64](r3-int-containers.md#u-0d9de696010b)

<a id="u-526a03e42b0e"></a>
### `Curl_uint32_spbset_destroy`

`void Curl_uint32_spbset_destroy(struct uint32_spbset *bset)` · [lib/uint-spbset.c:L57-L61][f4]

Releases all storage owned by the sparse bitset by asserting the debug magic, when enabled, and delegating to uint32_spbset_clear to free all chunks and reset the head.

calls: [uint32_spbset_clear](r14-uint-set-containers.md#u-4611b5892389)

<a id="u-43a75438b739"></a>
### `Curl_uint32_spbset_first`

`bool Curl_uint32_spbset_first(struct uint32_spbset *bset, uint32_t *pfirst)` · [lib/uint-spbset.c:L217-L232][f4]

Stores the smallest member in *pfirst by scanning chunks in offset order and each chunk's slots from index 0, using CURL_CTZ64 on the first nonzero word.

Returns TRUE when found; on an empty set it writes 0 to *pfirst for a defined value and returns FALSE.

uses: [Curl_ctz64](r3-int-containers.md#u-deab07778b06)

<a id="u-d4d0e039c852"></a>
### `Curl_uint32_spbset_init`

`void Curl_uint32_spbset_init(struct uint32_spbset *bset)` · [lib/uint-spbset.c:L33-L39][f4]

Initializes a sparse bitset by zeroing the whole struct; in debug builds it stamps a magic value used later to detect misuse.

contract: [Curl_uint32_spbset_destroy](r14-uint-set-containers.md#u-526a03e42b0e)

**Uncertainties.**

- The magic constant CURL_UINT32_SPBSET_MAGIC and the init field exist only under DEBUGBUILD, so non-debug behavior of destroy's assert path is unproven here.

<a id="u-363273dd75e8"></a>
### `Curl_uint32_spbset_next`

`bool Curl_uint32_spbset_next(struct uint32_spbset *bset, uint32_t last, uint32_t *pnext)` · [lib/uint-spbset.c:L275-L305][f4]

Iterator step: stores the smallest member strictly greater than last in *pnext.

It increments last, computes its aligned offset, and advances the chunk walk to the first chunk at or beyond that offset. If that chunk exactly matches the offset, uint32_spbset_chunk_next is tried; failure moves to the following chunk. Remaining higher chunks are searched with uint32_spbset_chunk_first until one succeeds. On no member it writes UINT32_MAX and returns FALSE, so iteration can be driven by first/next returning FALSE as the terminator.

**Notes.**

- contract: *pnext is set to UINT32_MAX on FALSE; UINT32_MAX is described elsewhere as a value the set cannot store, so it is a safe sentinel.

calls: [uint32_spbset_chunk_next](r14-uint-set-containers.md#u-cc41dd3fcfe7), [uint32_spbset_chunk_first](r14-uint-set-containers.md#u-28f2ace34e34); contract: [Curl_uint32_spbset_first](r14-uint-set-containers.md#u-43a75438b739)

<a id="u-8c68a0d78702"></a>
### `Curl_uint32_spbset_remove`

`void Curl_uint32_spbset_remove(struct uint32_spbset *bset, uint32_t i)` · [lib/uint-spbset.c:L194-L203][f4]

Clears the bit for value i if its chunk exists (lookup with grow=FALSE); otherwise it does nothing.

The bit is cleared by AND-ing the complement of the mask in the rebased slot word.

calls: [uint32_spbset_get_chunk](r14-uint-set-containers.md#u-29a56371cdd9)

<a id="u-28f2ace34e34"></a>
### `uint32_spbset_chunk_first`

`static bool uint32_spbset_chunk_first(struct uint32_spbset_chunk *chunk, uint32_t *pf…` · [lib/uint-spbset.c:L234-L246][f4]

Smallest member of a single chunk: scans slots in order and returns chunk->offset plus bit position of the lowest set bit via CURL_CTZ64; on an all-empty chunk writes UINT32_MAX (a value outside the representable set) and returns FALSE.

uses: [Curl_ctz64](r3-int-containers.md#u-deab07778b06); calls: [Curl_uint32_spbset_next](r14-uint-set-containers.md#u-363273dd75e8)

<a id="u-cc41dd3fcfe7"></a>
### `uint32_spbset_chunk_next`

`static bool uint32_spbset_chunk_next(struct uint32_spbset_chunk *chunk, uint32_t last…` · [lib/uint-spbset.c:L248-L273][f4]

Smallest member of a chunk strictly greater than last.

Only applies when last is at or after the chunk offset. It indexes the slot containing last; within bounds, it shifts that slot right by (last mod 64) and returns last plus the trailing-zero count if any higher bit is set; otherwise it scans forward through remaining slots for the next nonzero word and returns that bit. If last is beyond this chunk's slots or no higher bit exists, writes UINT32_MAX and returns FALSE.

uses: [Curl_ctz64](r3-int-containers.md#u-deab07778b06); calls: [Curl_uint32_spbset_next](r14-uint-set-containers.md#u-363273dd75e8)

<a id="u-4611b5892389"></a>
### `uint32_spbset_clear`

`UNITTEST void uint32_spbset_clear(struct uint32_spbset *bset)` · [lib/uint-spbset.c:L46-L55][f4]

Empties the sparse bitset, freeing every chunk after the embedded head chunk in a forward walk, then zeroing the head chunk so the set is empty and reusable.

Does not free the head chunk itself since it is part of the struct.

calls: [Curl_uint32_spbset_destroy](r14-uint-set-containers.md#u-526a03e42b0e); contract: [Curl_uint32_spbset_init](r14-uint-set-containers.md#u-d4d0e039c852)

**Uncertainties.**

- Graph evidence maps the free call to fwrite_xattr, which is inconsistent with the visible curlx_free call; the release mechanism is therefore recorded as curlx_free per source.

<a id="u-760d00124658"></a>
### `uint32_spbset_empty_chunk`

`static bool uint32_spbset_empty_chunk(struct uint32_spbset_chunk *chunk)` · [lib/uint-spbset.c:L77-L85][f4]

Reports whether all slot words of a chunk are zero, scanning slots in order and returning FALSE on the first nonzero word, TRUE otherwise.

<a id="u-29a56371cdd9"></a>
### `uint32_spbset_get_chunk`

`static struct uint32_spbset_chunk *uint32_spbset_get_chunk( struct uint32_spbset *bse…` · [lib/uint-spbset.c:L144-L179][f4]

Locates or creates the chunk covering index i's aligned offset.

Returns NULL immediately if bset is NULL. The walk stops at a chunk with a matching offset (found) or a larger offset (position for a new chunk). With grow=false it only reports existence. With grow=true it first tries uint32_spbset_unlink_empty to reuse an empty chunk's memory; a reused head chunk is returned directly, a truly unlinked one is inserted; if none is reusable, a zeroed chunk is allocated and NULL is returned on allocation failure. The chunk is then spliced into order by uint32_spbset_insert_chunk, whose return value is the result.

**Notes.**

- failure: Allocation failure during grow yields FALSE from add, while remove and contains silently report absence.

calls: [uint32_spbset_unlink_empty](r14-uint-set-containers.md#u-f85939f22e86), [uint32_spbset_insert_chunk](r14-uint-set-containers.md#u-7f1427a4aac7); contract: [Curl_uint32_spbset_add](r14-uint-set-containers.md#u-a1249ff289c7), [Curl_uint32_spbset_remove](r14-uint-set-containers.md#u-8c68a0d78702)

<a id="u-7f1427a4aac7"></a>
### `uint32_spbset_insert_chunk`

`static struct uint32_spbset_chunk *uint32_spbset_insert_chunk( struct uint32_spbset *…` · [lib/uint-spbset.c:L114-L142][f4]

Splices a prepared chunk into the offset-ordered chunk list.

If the new chunk's offset is below the head's, head contents are copied into the new chunk and the head takes the new offset, linking to it. Otherwise a panchor scan finds the first chunk with a larger offset and inserts before it, or appends at the tail. In debug builds a non-swap insert asserts the offset exceeds the head's.

calls: [uint32_spbset_get_chunk](r14-uint-set-containers.md#u-29a56371cdd9)

**Uncertainties.**

- When swapping with the head, the new chunk inherits the old head's next pointer and then head.next is set to it; whether the old-head node should also keep a next link is not re-verified in this code.

<a id="u-f85939f22e86"></a>
### `uint32_spbset_unlink_empty`

`static struct uint32_spbset_chunk *uint32_spbset_unlink_empty( struct uint32_spbset *…` · [lib/uint-spbset.c:L87-L112][f4]

Finds the first empty chunk in the ordered list for reuse by a new offset, returning it linked or unlinked depending on position.

It walks from the head with a panchor; when it finds an empty chunk: if it is the head and there is no next chunk or the requested offset sorts before the next chunk's offset, the head is returned still linked; otherwise the head is swapped with its next (head copies the next chunk's contents, the old-next node is zeroed and becomes free for insertion). Non-head empty chunks are unlinked via the panchor and zeroed. Returns NULL when no empty chunk exists.

calls: [uint32_spbset_empty_chunk](r14-uint-set-containers.md#u-760d00124658), [uint32_spbset_get_chunk](r14-uint-set-containers.md#u-29a56371cdd9)

**Uncertainties.**

- The head-swap path assumes an empty head chunk's next chain is copied intact by the single memcpy including its own next pointer; the resulting head.next then points at the zeroed former head node only if the copied next field equals it, which the code relies on without further fixing.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/u32_ptrset.h
[f2]: ../../../../../../eval/curl-2c04412/lib/u8_strset.h
[f3]: ../../../../../../eval/curl-2c04412/lib/uint-bset.h
[f4]: ../../../../../../eval/curl-2c04412/lib/uint-spbset.c
