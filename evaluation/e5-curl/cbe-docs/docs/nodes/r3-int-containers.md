# Integer-Keyed Containers

**Capability.** Provides a Robin Hood hash set mapping uint32_t ids to pointers with destructor and visit support, a fixed-capacity uint32 bitset with SWAR popcount/ctz iteration primitives, and a key-to-pointer table header defining its data layout and round-robin key assignment.

Use this subtree when code must associate data with numeric ids or iterate compact sets of integers. ptrset owns heap slots with growth; bset is capacity-bounded with first/next iteration; uint-table.h is layout only.

**Depended on by.**

- [Multi Handle Lifecycle and Registry](r13-multi-lifecycle.md) · graph-only · 34 edge(s)
- [Multi Drive, Wait and Timers](r13-multi-timers-wait.md) · graph-only · 32 edge(s)

Parent: [Shared Core Utilities](r3-core-utilities.md)

## Units (27)

<a id="u-a4aad014b36b"></a>
### `u32_ptrset.c module code (L1–L62)`

`module_region` · [lib/u32_ptrset.c:L1-L62][f1]

Implements a Robin Hood hash set mapping uint32_t ids to pointers.

Local macros derive slot count as 2^slotbits and the slot index as id masked by slotmask; a XOR macro swaps two values; DEBUGBUILD defines a magic pattern used to verify initialization.

**Notes.**

- field: CURL_U32_SLOT_CNT(bits) evaluates to 0 when bits is 0, so an uninitialized set with slotbits==0 has zero slots.

imports: [u32_ptrset.h module code (L46–L70)](r14-uint-set-containers.md#u-d8b9eb95c40c); uses: [u32_ptrset](r14-uint-set-containers.md#u-5b6acd93d8a1)

<a id="u-99dc02c3798c"></a>
### `Curl_u32_ptrset_init`

`void Curl_u32_ptrset_init(struct u32_ptrset *set, Curl_u32_ptrset_dtor *dtor)` · [lib/u32_ptrset.c:L63-L71][f1]

Initializes a u32_ptrset by zeroing the whole struct, then storing the caller-supplied destructor and, in debug builds, stamping the magic init value.

An existing allocation is not freed by init itself; callers wanting release use clear.

<a id="u-3080bb8ea0ed"></a>
### `Curl_u32_ptrset_clear`

`void Curl_u32_ptrset_clear(struct u32_ptrset *set)` · [lib/u32_ptrset.c:L73-L84][f1]

Frees all entries and resets the set for reuse.

If a dtor was configured, it iterates every slot and invokes dtor(id, ptr) for each non-NULL pointer; slots with NULL data are skipped. It then frees the backing arrays with curlx_safefree and re-initializes the set in place with the same dtor, restoring zeroed state including slotbits. In debug builds it first asserts the set was initialized with the magic value.

calls: [Curl_u32_ptrset_init](r3-int-containers.md#u-99dc02c3798c)

<a id="u-5d2cc0f03652"></a>
### `u32_ptrset_add`

`static void u32_ptrset_add(struct u32_ptrset *set, uint32_t id, void *ptr)` · [lib/u32_ptrset.c:L86-L112][f1]

Internal insert implementing Robin Hood placement: starting at the id-masked slot, it walks occupied slots, incrementing the new entry's probe sequence length (psl); whenever the existing entry's psl is lower, it swaps the new entry with that entry and continues placing the displaced one.

The walk stops at the first empty slot, where the current (possibly displaced) entry is stored with its psl and count is incremented. Assumes the set has a free slot and a non-NULL data array; it never grows or checks capacity. Compile-time CURL_U32_PTRSET_DEBUG logging to stderr is dead in normal builds.

uses: [u32_ptrset_grow](r3-int-containers.md#u-415d157563f9)

**Uncertainties.**

- No full-table detection inside add; a caller must ensure a slot exists, as Curl_u32_ptrset_set does via grow.

<a id="u-415d157563f9"></a>
### `u32_ptrset_grow`

`static bool u32_ptrset_grow(struct u32_ptrset *set)` · [lib/u32_ptrset.c:L114-L162][f1]

Doubles the slot array to accommodate more entries, returning FALSE on failure without modifying the set.

Fails when slotbits is already 31, when the new slot count times the per-slot byte size (pointer plus two uint32_t) would overflow SIZE_MAX (possible on 32-bit archs), or when the calloc for the combined arrays fails. On success it allocates one block, points ids and psl into it after the pointer array, doubles slotbits and recomputes slotmask, zeroes count, re-inserts every non-NULL entry from the old arrays via u32_ptrset_add, and frees the old block. First growth goes from 0 bits to 5 (32 slots).

calls: [u32_ptrset_add](r3-int-containers.md#u-5d2cc0f03652)

**Uncertainties.**

- Earlier-version limit: header comment claims capacity up to INT32_MAX+1 pointers, but grow refuses slotbits >= 31 which corresponds to 2^31 slots; the boundary at exactly 2^31 entries is not exercised in this source.

<a id="u-e6b7b0dde40f"></a>
### `u32_ptrset_get_index`

`static bool u32_ptrset_get_index(struct u32_ptrset *set, uint32_t id, uint32_t *pindex)` · [lib/u32_ptrset.c:L164-L188][f1]

Locates the slot holding a given id.

Returns FALSE immediately with *pindex untouched meaningfully if the data array is NULL. It probes while slots are occupied and the stored psl is at least the current probe count (Robin Hood invariant means the id cannot lie further once a slot's psl is lower); it returns TRUE setting *pindex on id match, or FALSE setting *pindex to 0 when the probe stops (empty slot or lower psl).

**Uncertainties.**

- On the not-found path *pindex is set to 0, so callers cannot distinguish 'absent at index 0' from absence; they must check the return value.

<a id="u-300fffc42295"></a>
### `u32_ptrset_unset`

`static void u32_ptrset_unset(struct u32_ptrset *set, uint32_t id)` · [lib/u32_ptrset.c:L236-L263][f1]

Removes an id if present; otherwise does nothing.

On a hit it invokes the dtor if one is configured, clears the slot (data NULL, id and psl 0), decrements count, then backfills: while the next slot is occupied with psl > 0, it shifts that entry one position up with psl decremented and clears its old slot, preserving the Robin Hood invariant. Debug init assert applies.

calls: [u32_ptrset_get_index](r3-int-containers.md#u-e6b7b0dde40f)

<a id="u-3439641bc3ca"></a>
### `Curl_u32_ptrset_count`

`uint32_t Curl_u32_ptrset_count(struct u32_ptrset *set)` · [lib/u32_ptrset.c:L190-L193][f1]

Returns the stored entry count without touching slot arrays.

<a id="u-581c7c553f33"></a>
### `Curl_u32_ptrset_get`

`void *Curl_u32_ptrset_get(struct u32_ptrset *set, uint32_t id)` · [lib/u32_ptrset.c:L195-L202][f1]

Returns the pointer registered for an id, or NULL if the id is absent.

Delegates lookup to u32_ptrset_get_index and reads data at the found slot. Asserts debug-build initialization.

calls: [u32_ptrset_get_index](r3-int-containers.md#u-e6b7b0dde40f)

**Uncertainties.**

- A stored NULL pointer is indistinguishable from absence; callers should never store NULL via set (set with NULL means unset).

<a id="u-5c54e3c19be1"></a>
### `Curl_u32_ptrset_set`

`CURLcode Curl_u32_ptrset_set(struct u32_ptrset *set, uint32_t id, void *ptr)` · [lib/u32_ptrset.c:L204-L234][f1]

Inserts or replaces the pointer for an id, returning CURLE_OK or CURLE_OUT_OF_MEMORY.

If ptr is NULL it unsets the id and returns OK instead of storing a NULL. If the id exists, it invokes dtor on the old pointer only when a dtor exists and the old pointer differs from the new one, then overwrites the slot. If the id is new and the table is full (count >= slot count), grow is attempted; its failure yields CURLE_OUT_OF_MEMORY and the entry is not added. Otherwise the entry is inserted via u32_ptrset_add. Debug init assert applies.

calls: [u32_ptrset_unset](r3-int-containers.md#u-300fffc42295), [u32_ptrset_get_index](r3-int-containers.md#u-e6b7b0dde40f), [u32_ptrset_grow](r3-int-containers.md#u-415d157563f9), [u32_ptrset_add](r3-int-containers.md#u-5d2cc0f03652)

<a id="u-d358fa33e352"></a>
### `Curl_u32_ptrset_unset`

`void Curl_u32_ptrset_unset(struct u32_ptrset *set, uint32_t id)` · [lib/u32_ptrset.c:L265-L268][f1]

Public wrapper that forwards to the static unset helper.

calls: [u32_ptrset_unset](r3-int-containers.md#u-300fffc42295)

<a id="u-ae0f73076d2a"></a>
### `Curl_u32_ptrset_visit`

`void Curl_u32_ptrset_visit(struct u32_ptrset *set, Curl_u32_ptrset_visit_cb *cb, void…` · [lib/u32_ptrset.c:L270-L279][f1]

Iterates every slot in array order, invoking cb(id, ptr, user_data) for each occupied slot; iteration stops early as soon as the callback returns FALSE.

Does not assert debug init and ignores the set's dtor.

**Uncertainties.**

- Visit order is slot-array order, not insertion or id order.

<a id="u-e598630ca79a"></a>
### `Curl_uint32_bset_init`

`void Curl_uint32_bset_init(struct uint32_bset *bset)` · [lib/uint-bset.c:L32-L38][f2]

Zeroes the bitset, giving it zero capacity; in debug builds also stamps a magic value used by later DEBUGASSERT checks.

<a id="u-50a20a3b07bb"></a>
### `Curl_uint32_bset_resize`

`CURLcode Curl_uint32_bset_resize(struct uint32_bset *bset, uint32_t nmax)` · [lib/uint-bset.c:L40-L61][f2]

Grows or shrinks capacity to hold values 0..nmax, rounding nmax up to a multiple of 64 slots-bits (capped near UINT32_MAX/64).

If the slot count changes, it allocates a new zeroed slot array; on allocation failure returns CURLE_OUT_OF_MEMORY leaving the set untouched. When shrinking or growing it copies min(new,old) slots, frees the old array, and resets first_slot_used. A resize to the current size is a no-op returning CURLE_OK.

<a id="u-5ee2cb64d833"></a>
### `Curl_uint32_bset_destroy`

`void Curl_uint32_bset_destroy(struct uint32_bset *bset)` · [lib/uint-bset.c:L63-L68][f2]

Frees the slot array and zeroes the whole struct, including the debug magic stamp, so a later use fails debug assertions.

<a id="u-7dd3fbb002fa"></a>
### `Curl_uint32_bset_count`

`uint32_t Curl_uint32_bset_count(struct uint32_bset *bset)` · [lib/uint-bset.c:L79-L88][f2]

Returns the number of set bits by popcounting each nonzero slot, starting the scan at first_slot_used so leading known-empty slots are skipped.

<a id="u-0797671d053d"></a>
### `uint32_bset_capacity`

`UNITTEST uint32_t uint32_bset_capacity(struct uint32_bset *bset)` · [lib/uint-bset.c:L73-L76][f2]

UNITTEST-only accessor returning nslots * 64, the number of representable values.

<a id="u-607d6b2a6129"></a>
### `Curl_uint32_bset_empty`

`bool Curl_uint32_bset_empty(struct uint32_bset *bset)` · [lib/uint-bset.c:L90-L98][f2]

Returns TRUE when no slot from first_slot_used onward is nonzero; FALSE at the first populated slot.

<a id="u-0f3c0d732432"></a>
### `Curl_uint32_bset_clear`

`void Curl_uint32_bset_clear(struct uint32_bset *bset)` · [lib/uint-bset.c:L100-L106][f2]

If capacity is nonzero, memsets all slots and sets first_slot_used to UINT32_MAX, marking the whole set as scanned-empty.

With zero capacity it does nothing.

<a id="u-8a82c69e76db"></a>
### `Curl_uint32_bset_add`

`bool Curl_uint32_bset_add(struct uint32_bset *bset, uint32_t i)` · [lib/uint-bset.c:L108-L117][f2]

Sets bit i and returns TRUE, or returns FALSE without effect if i/64 is beyond capacity.

Adding also lowers first_slot_used when i lands before it, keeping the scan optimization correct.

<a id="u-ce6aec0bf288"></a>
### `Curl_uint32_bset_remove`

`void Curl_uint32_bset_remove(struct uint32_bset *bset, uint32_t i)` · [lib/uint-bset.c:L119-L124][f2]

Clears bit i when its slot exists; out-of-capacity values are silently ignored.

first_slot_used is not raised, so later scans may skip past empty leading slots only at the cost of scanning.

<a id="u-2707f58fd689"></a>
### `Curl_uint32_bset_contains`

`bool Curl_uint32_bset_contains(struct uint32_bset *bset, uint32_t i)` · [lib/uint-bset.c:L126-L132][f2]

Returns TRUE iff bit i is set; values beyond capacity report FALSE.

<a id="u-0342ae52ab92"></a>
### `Curl_uint32_bset_first`

`bool Curl_uint32_bset_first(struct uint32_bset *bset, uint32_t *pfirst)` · [lib/uint-bset.c:L134-L146][f2]

Finds the smallest set value by scanning from first_slot_used for a nonzero slot and taking its lowest set bit via CTZ64; it caches the slot index in first_slot_used.

When the set is empty it sets both first_slot_used and *pfirst to UINT32_MAX and returns FALSE.

<a id="u-0193d548776e"></a>
### `Curl_uint32_bset_next`

`bool Curl_uint32_bset_next(struct uint32_bset *bset, uint32_t last, uint32_t *pnext)` · [lib/uint-bset.c:L148-L174][f2]

Returns the smallest set value strictly greater than last; last need not be present.

It checks the slot containing last+1 after shifting away already-visited bits, then scans forward for the first nonzero slot, returning its lowest set bit. When no such value exists it sets *pnext to UINT32_MAX (a value the set cannot store) and returns FALSE. The documented iteration contract follows from this: additions above last are seen, additions below are not, and removals above last are simply never visited.

<a id="u-0d9de696010b"></a>
### `Curl_popcount64`

`uint32_t Curl_popcount64(uint64_t x)` · [lib/uint-bset.c:L177-L193][f2]

Portable Hamming-weight of a uint64_t using the SWAR popcount trick: pairwise bit counts, nibble counts, byte counts, then a multiply-and-shift to sum all bytes.

Compiled only when CURL_POPCOUNT64_IMPLEMENT is defined, i.e. when no intrinsic backs the CURL_POPCOUNT64 macro.

<a id="u-deab07778b06"></a>
### `Curl_ctz64`

`uint32_t Curl_ctz64(uint64_t x)` · [lib/uint-bset.c:L197-L232][f2]

Counts trailing zeros of a uint64_t by divide-and-conquer: zero input returns 64; otherwise it adds 32/16/8/4/2 as wider lower halves are zero and shifts down, finishing with n minus the lowest bit.

Compiled only when CURL_CTZ64_IMPLEMENT is defined.

<a id="u-09f6519df381"></a>
### `uint32_tbl`

`struct uint32_tbl` · [lib/uint-table.h:L28-L36][f3]

Data layout of the key-to-pointer table: a rows array of void*, its length nrows, the number of live entries, last_key_added (UINT_MAX or the last assigned key, driving round-robin key assignment), and a debug init stamp.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/u32_ptrset.c
[f2]: ../../../../../../eval/curl-2c04412/lib/uint-bset.c
[f3]: ../../../../../../eval/curl-2c04412/lib/uint-table.h
