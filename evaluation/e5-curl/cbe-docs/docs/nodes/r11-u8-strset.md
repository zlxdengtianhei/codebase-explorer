# u8 string set

**Capability.** An owned id-to-string hash set (Robin Hood open addressing) with init/copy/set/unset/get lifecycle and backward-shift deletion.

Use it to associate small integer ids (e.g. RTSP channels) with heap strings. Consumers such as RTSP use setn/setx to bind strings and get to fetch them; unset0 additionally scrubs memory.

**Depended on by.**

- [DNS cache](r11-dnscache.md) · model-inferred · 0 edge(s)
- [RTSP protocol](r11-rtsp-protocol.md) · graph-confirmed · 10 edge(s)

Parent: [curlx shared utilities](r11-curlx-utilities.md)

## Units (14)

<a id="u-8d42139e9194"></a>
### `Curl_u8_strset_init`

`void Curl_u8_strset_init(struct u8_strset *set)` · [lib/u8_strset.c:L63-L82][f1]

Resets a set to its empty initial state using the embedded arrays.

It zeroes the whole struct (suppressing GCC 13 -Warray-bounds around the memset), points data/ids/psl at the inline sdata/sids/spsl, sets slotbits to CURL_U8_STRSET_START_BITS and slotmask to the matching low-bit mask, and resets count to 0. In DEBUGBUILD it stamps the init magic that other operations check with DEBUGASSERT.

uses: [u8_strset](r14-uint-set-containers.md#u-9cf5d076bbb7)

<a id="u-ee3e28f91bbd"></a>
### `Curl_u8_strset_clear`

`void Curl_u8_strset_clear(struct u8_strset *set)` · [lib/u8_strset.c:L84-L94][f1]

Frees all storage owned by a set and restores it to the freshly initialized state.

It asserts the init magic, frees every non-NULL string slot across the current slot count, frees the heap arrays only when data no longer points at the inline sdata, then reinitializes the set via Curl_u8_strset_init so it remains reusable.

calls: [Curl_u8_strset_init](r11-u8-strset.md#u-8d42139e9194)

<a id="u-50e3c4d4d5a6"></a>
### `Curl_u8_strset_copy`

`CURLcode Curl_u8_strset_copy(struct u8_strset *dest, struct u8_strset *src)` · [lib/u8_strset.c:L299-L311][f1]

Copies all string/id pairs from src into dest, replacing dest's prior contents.

It asserts src's init magic, clears dest (freeing its strings and resetting it), then iterates every occupied src slot in slot order, calling u8_strset_set for each so dest makes its own copy of the string. The loop stops at the first failing CURLcode, and that code is returned; CURLE_OUT_OF_MEMORY is the only failure a full copy can produce via u8_strset_set. src is left untouched.

calls: [function::Curl_u8_strset_set::7686][f1], [Curl_u8_strset_clear](r11-u8-strset.md#u-ee3e28f91bbd)

**Uncertainties.**

- Whether dest's init magic is asserted before clearing is not shown; only src->init is checked here, so copying into an uninitialized dest would leak undefined state

<a id="u-b813f0e5b66e"></a>
### `Curl_u8_strset_count`

`uint16_t Curl_u8_strset_count(struct u8_strset *set)` · [lib/u8_strset.c:L192-L195][f1]

Returns set->count; compiled only when UNITTESTS is defined.

<a id="u-48fba58a4b37"></a>
### `Curl_u8_strset_get`

`const char *Curl_u8_strset_get(struct u8_strset *set, uint8_t id)` · [lib/u8_strset.c:L198-L205][f1]

Returns the stored string for an id, or NULL when absent.

It asserts the init magic, resolves the slot with u8_strset_get_index, and returns that slot's data pointer on a hit; on a miss it returns NULL. The returned pointer aliases storage owned by the set and is valid only until the entry is replaced, unset, or the set is cleared or grown.

calls: [u8_strset_get_index](r11-u8-strset.md#u-1359ea97ed68)

<a id="u-8d6be39089c0"></a>
### `Curl_u8_strset_setn`

`CURLcode Curl_u8_strset_setn(struct u8_strset *set, uint8_t id, char *str)` · [lib/u8_strset.c:L207-L235][f1]

Binds str to id, taking ownership of str even on failure paths.

If str is NULL it unsets the id and returns CURLE_OK. If the id already exists, it frees the old slot string and stores str in place. Otherwise, when the set is full it attempts u8_strset_grow; if growth fails (allocation failure or the 256-slot ceiling) it frees str and returns CURLE_OUT_OF_MEMORY. On success it inserts via u8_strset_addn and returns CURLE_OK. Asserts the init magic at entry.

calls: [u8_strset_get_index](r11-u8-strset.md#u-1359ea97ed68), [u8_strset_grow](r11-u8-strset.md#u-c941de353471), [u8_strset_addn](r11-u8-strset.md#u-8fbbd2de7ede), [Curl_u8_strset_unset](r11-u8-strset.md#u-216a4460c8ee)

<a id="u-71cd8182b082"></a>
### `Curl_u8_strset_setx`

`CURLcode Curl_u8_strset_setx(struct u8_strset *set, uint8_t id, const char *str, size…` · [lib/u8_strset.c:L237-L252][f1]

Copying variant of setn for a buffer of slen bytes that need not be NUL-terminated.

A NULL str unsets the id and returns CURLE_OK. Otherwise it duplicates the bytes with a NUL terminator via curlx_memdup0, returning CURLE_OUT_OF_MEMORY if that allocation fails, and otherwise hands ownership of the duplicate to Curl_u8_strset_setn, propagating its result.

calls: [Curl_u8_strset_setn](r11-u8-strset.md#u-8d6be39089c0)

<a id="u-216a4460c8ee"></a>
### `Curl_u8_strset_unset`

`void Curl_u8_strset_unset(struct u8_strset *set, uint8_t id)` · [lib/u8_strset.c:L289-L292][f1]

Public unset wrapper: removes the id from the set and frees its string without zeroing memory, by calling u8_strset_unset with zero FALSE.

calls: [u8_strset_unset](r11-u8-strset.md#u-c5a29f521086)

<a id="u-909bfa680ded"></a>
### `Curl_u8_strset_unset0`

`void Curl_u8_strset_unset0(struct u8_strset *set, uint8_t id)` · [lib/u8_strset.c:L294-L297][f1]

Public unset wrapper that also scrubs memory: calls u8_strset_unset with zero TRUE so the removed string's bytes are zeroed before being freed, per the header note about removing and zeroing.

calls: [u8_strset_unset](r11-u8-strset.md#u-c5a29f521086)

<a id="u-8fbbd2de7ede"></a>
### `u8_strset_addn`

`static void u8_strset_addn(struct u8_strset *set, uint8_t id, char *val)` · [lib/u8_strset.c:L96-L116][f1]

Internal insertion taking ownership of val.

It starts at slot id & slotmask with probe-sequence length 0 and walks while the slot is occupied; when an occupied slot's stored psl is lower than the incoming psl, it swaps the two entries (data via temp pointer, psl and id via the XOR macro) and continues reinserting the displaced entry. On the first empty slot it stores id, val, and psl, then increments count. The caller must ensure spare capacity: this loop has no full-table guard and would not terminate on a fully occupied table.

uses: [u8_strset](r14-uint-set-containers.md#u-9cf5d076bbb7)

**Uncertainties.**

- Termination relies on callers growing before the table is full, as Curl_u8_strset_setn does; no guard exists here

<a id="u-1359ea97ed68"></a>
### `u8_strset_get_index`

`static bool u8_strset_get_index(struct u8_strset *set, uint8_t id, uint8_t *pindex)` · [lib/u8_strset.c:L167-L188][f1]

Locates the slot holding a given id, returning its index through pindex.

Starting at id & slotmask with walk length 0, it continues while the slot is occupied and the stored psl is at least the walk length; in Robin Hood ordering a slot with smaller psl proves the id is absent. On a matching id it stores the slot index and returns TRUE; on miss it writes 0 to pindex and returns FALSE. Under CURL_U8_STRSET_DEBUG it logs hits and misses to stderr.

uses: [u8_strset](r14-uint-set-containers.md#u-9cf5d076bbb7)

<a id="u-c941de353471"></a>
### `u8_strset_grow`

`static bool u8_strset_grow(struct u8_strset *set)` · [lib/u8_strset.c:L118-L165][f1]

Doubles the set's slot capacity and rehashes all entries.

It returns FALSE without changes when slotbits is already 8 (the 256-slot ceiling implied by 8-bit ids) or when the single calloc for the new combined block fails. On success it lays the new block out as nslots string pointers followed by nslots ids and nslots psl bytes, updates slotbits and slotmask, resets count to 0, re-adds every occupied old entry via u8_strset_addn, frees the old heap block when it was not the inline sdata, and returns TRUE.

**Notes.**

- failure: On allocation failure the set keeps its previous contents and capacity; the FALSE return is the only signal.

calls: [u8_strset_addn](r11-u8-strset.md#u-8fbbd2de7ede)

**Uncertainties.**

- prev_slots is assigned set->slotbits (a bit count) but consumed as a slot count in the re-add loop; the loop bound is therefore one eighth of the table, so correctness of the rehash depends on this being a real defect or on evidence not visible here

<a id="u-10c29b74d0ba"></a>
### `u8_strset_set`

`UNITTEST CURLcode u8_strset_set(struct u8_strset *set, uint8_t id, const char *str)` · [lib/u8_strset.c:L257-L261][f1]

Convenience wrapper for unit tests: forwards to Curl_u8_strset_setx with strlen(str) as the length when str is non-NULL, else 0, propagating its CURLcode.

The duplicate UNITTEST declaration precedes the definition.

calls: [Curl_u8_strset_setx](r11-u8-strset.md#u-71cd8182b082)

<a id="u-c5a29f521086"></a>
### `u8_strset_unset`

`static void u8_strset_unset(struct u8_strset *set, uint8_t id, bool zero)` · [lib/u8_strset.c:L263-L287][f1]

Internal removal of an id with backward-shift deletion to preserve Robin Hood invariants.

On a hit from u8_strset_get_index it zeroes the slot string when the zero flag is set (sensitive-data scrubbing), frees it, clears the slot's id and psl, and decrements count. It then walks forward while the next slot is occupied with a positive psl, moving each such entry down one slot with its psl decremented by one, clearing the vacated slot, until it reaches an entry with psl 0 or an empty slot. A miss leaves the set unchanged.

calls: [u8_strset_get_index](r11-u8-strset.md#u-1359ea97ed68)

**Uncertainties.**

- curlx_strzero is only linked as evidence; its exact semantics (setting bytes to zero) come from the call site and name, not this file

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/u8_strset.c
