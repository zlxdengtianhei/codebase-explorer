# Integer-keyed containers

**Capability.** A uint32-keyed dynamic table (init/resize/add/remove/clear/destroy with iteration and lookup helpers) and a sparse uint32 bitset optimized for few clustered values, with documented iteration contracts.

Infrastructure used for tracking integer-indexed state. The table stores entries in growable rows; the spbset answers membership/next queries without dense allocation.

**Depended on by.**

- [Multi Handle Lifecycle and Registry](r13-multi-lifecycle.md) · graph-only · 24 edge(s)

Parent: [curl codebase](r15-curl-codebase.md)

## Units (14)

<a id="u-23d737ab764a"></a>
### `uint-table-c-trivial-accessors-and-lookup`

`uint32_t Curl_uint32_tbl_capacity(struct uint32_tbl *tbl)` · [lib/uint-table.c:L99-L102][f1]

This group covers the table's stateless accessors: capacity and count report nrows and nentries; get returns the entry at key or NULL when key exceeds nrows; contains returns TRUE only when a row at key is non-NULL.

All are read-only, allocate nothing, and dereference tbl without NULL checks.

group: [uint-table-c-trivial-accessors-and-lookup](r15-uint-containers.md#u-23d737ab764a)

<a id="u-fab3d590b0e3"></a>
### `uint-table-c-iteration-helpers`

`static bool uint32_tbl_next_at(struct uint32_tbl *tbl, uint32_t key, uint32_t *pkey, …` · [lib/uint-table.c:L161-L174][f1]

Iteration helpers: static uint32_tbl_next_at scans from key upward for the first non-NULL row, writing its index and entry into pkey/pentry and returning TRUE, or setting *pkey to UINT32_MAX, *pentry to NULL and returning FALSE when none exists.

Curl_uint32_tbl_first rejects NULL out-parameters and, when nentries is nonzero, returns the first occupied row; otherwise it asserts and returns FALSE with the invalid sentinel. Curl_uint32_tbl_next likewise rejects NULL out-parameters and scans from last_key + 1 (wrapping naturally via the upward scan; no wrap to 0), returning FALSE with sentinels at the end.

**Notes.**

- contract: Iteration ends when pkey is UINT32_MAX; last_key + 1 wraps to 0 when last_key is UINT32_MAX, restarting the scan.

group: [uint-table-c-iteration-helpers](r15-uint-containers.md#u-fab3d590b0e3)

**Uncertainties.**

- first()'s DEBUGASSERT(!tbl->nentries) fires only when nentries is inconsistent with row contents; release builds just return FALSE.

<a id="u-296f319a953c"></a>
### `Curl_uint32_tbl_init`

`void Curl_uint32_tbl_init(struct uint32_tbl *tbl)` · [lib/uint-table.c:L32-L39][f1]

Initializes a caller-provided table to empty.

It zeroes the whole struct, sets last_key_added to UINT32_MAX, and in DEBUGBUILD stamps tbl->init with the magic value checked by later DEBUGASSERTs.

<a id="u-3543eb5e579d"></a>
### `Curl_uint32_tbl_resize`

`CURLcode Curl_uint32_tbl_resize(struct uint32_tbl *tbl, uint32_t nrows)` · [lib/uint-table.c:L56-L76][f1]

Grows or shrinks the table's row capacity.

Returns CURLE_BAD_FUNCTION_ARGUMENT when nrows is 0. When the requested size differs from the current nrows, it allocates a new zeroed array (CURLE_OUT_OF_MEMORY on failure), copies min(nrows, old nrows) rows, and on shrink calls uint32_tbl_clear_rows over the dropped tail so nentries drops accordingly before freeing the old array. A no-op when nrows equals current nrows. DEBUGASSERT validates the magic stamp. The comment explains nrows+1 must stay valid during iteration.

calls: [uint32_tbl_clear_rows](r15-uint-containers.md#u-9071f6a8e83c)

<a id="u-aa04762f59cf"></a>
### `Curl_uint32_tbl_add`

`bool Curl_uint32_tbl_add(struct uint32_tbl *tbl, void *entry, uint32_t *pkey)` · [lib/uint-table.c:L114-L148][f1]

Stores entry in the first free row and returns its index through *pkey.

Returns FALSE immediately when entry or pkey is NULL, or when the table is full (nentries == nrows); it sets *pkey to UINT32_MAX on entry. Search starts just after min(last_key_added, nrows) and wraps to scan [0, start_pos) if nothing is free above, giving a reuse-ascending key policy. On success it fills the row, increments nentries, updates last_key_added, and returns TRUE. The final DEBUGASSERT(0) marks the wrap scan failing as an internal inconsistency; release builds return FALSE.

**Notes.**

- failure: On any failure *pkey is set to UINT32_MAX, an always-invalid key.

**Uncertainties.**

- The wrap scan makes the full-check at the top redundant; a FALSE from the end should be unreachable except via inconsistency.

<a id="u-fdb7f80367e5"></a>
### `Curl_uint32_tbl_remove`

`void Curl_uint32_tbl_remove(struct uint32_tbl *tbl, uint32_t key)` · [lib/uint-table.c:L150-L154][f1]

Removes the entry at key by delegating to uint32_tbl_clear_rows over the single-slot range [key, key+1); out-of-range keys are silently ignored.

calls: [uint32_tbl_clear_rows](r15-uint-containers.md#u-9071f6a8e83c)

<a id="u-9071f6a8e83c"></a>
### `uint32_tbl_clear_rows`

`static void uint32_tbl_clear_rows(struct uint32_tbl *tbl, uint32_t from, uint32_t upt…` · [lib/uint-table.c:L41-L54][f1]

Static helper that nulls table rows in [from, min(upto_excluding, nrows)) and decrements nentries for each non-NULL row cleared.

End is clamped to nrows, so an over-large range is truncated rather than overrunning the array; from is not clamped, so a from above nrows yields no iterations.

**Uncertainties.**

- No check that from <= nrows; relies on callers passing valid starts.

<a id="u-f152697bb7f0"></a>
### `uint32_tbl_clear`

`UNITTEST void uint32_tbl_clear(struct uint32_tbl *tbl)` · [lib/uint-table.c:L83-L89][f1]

Empties the table without freeing storage: clears all rows via uint32_tbl_clear_rows(0, nrows), asserts nentries became 0, and resets last_key_added to UINT32_MAX.

DEBUGASSERT checks the magic stamp first; in release builds an unstamped table is cleared unchecked.

calls: [uint32_tbl_clear_rows](r15-uint-containers.md#u-9071f6a8e83c)

<a id="u-744118d7b812"></a>
### `Curl_uint32_tbl_destroy`

`void Curl_uint32_tbl_destroy(struct uint32_tbl *tbl)` · [lib/uint-table.c:L91-L97][f1]

Tears down the table: clears all entries, frees the rows array, and zeroes the struct so the table cannot be reused safely.

DEBUGASSERT validates the magic stamp.

calls: [uint32_tbl_clear](r15-uint-containers.md#u-f152697bb7f0)

<a id="u-f37077ad1717"></a>
### `uint-spbset.h module code (L1–L41)`

`module_region` · [lib/uint-spbset.h:L1-L41][f2]

Guard, license, curl_setup.h include and the sparse-bitset design comment (efficient for few, close-together values).

<a id="u-7ffa391fd098"></a>
### `uint-spbset.h module code (L46–L47)`

`module_region` · [lib/uint-spbset.h:L46-L47][f2]

Chunk slot-count macros: 4 slots = 256 bits, kept a power of two, with the corresponding range mask.

<a id="u-ba0401eb296c"></a>
### `uint32_spbset_chunk`

`struct uint32_spbset_chunk` · [lib/uint-spbset.h:L42-L46][f2]

One chunk of the sparse bitset: a next link for chaining, 4 uint64_t slots (256 bits, per CURL_UINT32_SPBSET_CH_SLOTS) and the base offset of the covered value range.

<a id="u-bb6a7acfa02e"></a>
### `uint32_spbset`

`struct uint32_spbset` · [lib/uint-spbset.h:L48-L53][f2]

Sparse uint32_t bitset optimized for few, clustered values: an inline head chunk followed by chained chunks; DEBUGBUILD adds an init guard.

Values map to a bit in the chunk whose 256-value window covers them.

uses: [uint32_spbset_chunk](r15-uint-containers.md#u-ba0401eb296c)

<a id="u-62ea0b5da83c"></a>
### `uint-spbset.h module code (L53–L91)`

`module_region` · [lib/uint-spbset.h:L53-L91][f2]

Sparse bitset API prototypes with contracts: init, destroy, count, add (idempotent, FALSE on allocation failure), remove, contains, first (FALSE when empty), and next (smallest value greater than last; documents safe iteration while the set is modified: added values above last appear, others do not; removed values above last are not visited).

uses: [uint32_spbset](r15-uint-containers.md#u-bb6a7acfa02e)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/uint-table.c
[f2]: ../../../../../../eval/curl-2c04412/lib/uint-spbset.h
