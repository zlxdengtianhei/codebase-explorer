# Multi socket events

**Capability.** Tracks which transfers and connections are interested in which sockets for the multi handle: per-socket hash entries, pollset diffing against the previous state, and socket-callback notification of changes.

Read this to see how socket interest changes reach the application callback. mev_assess is the core: build the current pollset, diff it, update shared entries and fire the callback; assignment and dirty-marking hang off the same entries.

**Depends on.**

- [Generic hash and list containers](r4-generic-containers.md) · graph-confirmed · 5 edge(s)

Parent: [curl source tree](r4-curl.md)

## Units (23)

<a id="u-679f4a61d16b"></a>
### `multi-ev-pollset-meta-helpers`

`static void mev_pollset_dtor(const void *key, size_t klen, void *entry)` · [lib/multi_ev.c:L134-L143][f1]

Per-easy/per-connection pollset storage helpers.

Pollsets are heap-allocated easy_pollset structs attached under the meta key CURL_META_MEV_POLLSET with mev_pollset_dtor as destructor, which cleans up and frees the pollset. The two add-new helpers create a pollset and attach it to the connection or easy handle, returning NULL if creation or meta attachment fails. mev_get_last_pollset returns the connection's pollset when both data and conn are given, the easy handle's otherwise, and NULL when data is NULL.

**Notes.**

- failure: If Curl_conn_meta_set/Curl_meta_set fails after a successful pollset create, the created pollset is not visibly freed in this file.

uses: [Curl_hash_element](r8-container-types.md#u-270a73a3904a)

**Uncertainties.**

- Whether the meta layer takes ownership of the pollset on a failed set call is not visible here.

<a id="u-6f36ebdb623f"></a>
### `multi-ev-sh-entry-helpers`

`static void mev_sh_entry_dtor(void *freethis)` · [lib/multi_ev.c:L60-L68][f1]

Socket-entry primitives for the multi handle's socket hash.

They create, look up, mutate and destroy mev_sh_entry values: lookup skips CURL_SOCKET_BAD; add allocates an entry, initializes its spbset, inserts via Curl_hash_add and self-destructs on insertion failure; kill deletes by socket key; user_count is the transfer count plus one if a connection is attached; known/add/remove helpers register or unregister a connection pointer or transfer mid, returning whether the operation applied and asserting on inconsistent state (conn_add refuses a second connection; removes return FALSE when not registered).

**Notes.**

- failure: mev_sh_entry_add returns NULL on calloc failure or Curl_hash_add failure; in the latter it invokes mev_sh_entry_dtor on the fresh entry itself.
- side_effect: mev_sh_entry_dtor destroys the xfers spbset and, in DEBUGBUILD, zeroes the magic before freeing.

uses: [Curl_hash](r8-container-types.md#u-691a9d9c68ec), [uint32_spbset](r15-uint-containers.md#u-bb6a7acfa02e)

<a id="u-ee55dd891efa"></a>
### `Curl_multi_ev_assess_conn`

`CURLMcode Curl_multi_ev_assess_conn(struct Curl_multi *multi, struct Curl_easy *data,…` · [lib/multi_ev.c:L550-L555][f1]

Public wrapper assessing a connection by delegating to mev_assess with the given conn.

calls: [mev_assess](r4-multi-event.md#u-7e4cfdd040dc)

<a id="u-8a5c1710228d"></a>
### `Curl_multi_ev_assess_xfer`

`CURLMcode Curl_multi_ev_assess_xfer(struct Curl_multi *multi, struct Curl_easy *data)` · [lib/multi_ev.c:L544-L548][f1]

Public wrapper assessing a transfer (no connection) by delegating to mev_assess with conn NULL.

calls: [mev_assess](r4-multi-event.md#u-7e4cfdd040dc)

<a id="u-d10408e716af"></a>
### `Curl_multi_ev_assess_xfer_bset`

`CURLMcode Curl_multi_ev_assess_xfer_bset(struct Curl_multi *multi, struct uint32_bset…` · [lib/multi_ev.c:L557-L572][f1]

Assesses every easy handle whose mid is in the given uint32_bset, iterating the set in order via first/next.

Stops immediately when an assessment returns a non-OK CURLMcode; transfers no longer found by mid are skipped without error. Returns the first error or CURLM_OK.

calls: [Curl_multi_ev_assess_xfer](r4-multi-event.md#u-8a5c1710228d), [multi-c-easy-lookup](r13-multi-lifecycle.md#u-ca4794ea3aa5)

<a id="u-2538ecc63605"></a>
### `Curl_multi_ev_assign`

`CURLMcode Curl_multi_ev_assign(struct Curl_multi *multi, curl_socket_t s, void *user_…` · [lib/multi_ev.c:L574-L583][f1]

Stores application user_data on the socket's hash entry; returns CURLM_BAD_SOCKET if the socket has no entry, i.e. was never announced or is already forgotten, otherwise CURLM_OK after the assignment.

calls: [multi-ev-sh-entry-helpers](r4-multi-event.md#u-6f36ebdb623f)

<a id="u-c9d2529e2214"></a>
### `Curl_multi_ev_cleanup`

`void Curl_multi_ev_cleanup(struct Curl_multi *multi)` · [lib/multi_ev.c:L648-L651][f1]

Destroys the multi's socket hash, invoking the entry destructor (and thus spbset teardown and frees) for every remaining entry.

contract: [Curl_multi_ev_init](r4-multi-event.md#u-ebece1e6ab27)

<a id="u-1d7be4b2b61a"></a>
### `Curl_multi_ev_conn_done`

`void Curl_multi_ev_conn_done(struct Curl_multi *multi, struct Curl_easy *data, struct…` · [lib/multi_ev.c:L634-L640][f1]

Finalizes a destroyed connection: re-assesses the connection's pollset (dropping its sockets and firing REMOVE callbacks as needed), then removes the connection's stored pollset from connection meta.

The assessment result is discarded.

calls: [mev_assess](r4-multi-event.md#u-7e4cfdd040dc)

<a id="u-ba801b3576b5"></a>
### `Curl_multi_ev_dirty_xfers`

`void Curl_multi_ev_dirty_xfers(struct Curl_multi *multi, curl_socket_t s)` · [lib/multi_ev.c:L585-L618][f1]

Marks all transfers tied to socket s as dirty for immediate reprocessing.

A missing entry is silently ignored because stray socket actions (observed from libevent) can arrive after removal. For each mid in the entry's spbset, the matching easy handle is marked dirty; a mid without a handle is logged and removed from the set during iteration. If a connection is attached, the multi's admin easy handle is also marked dirty.

**Notes.**

- side_effect: Stale mids are pruned from the entry's spbset while iterating.

calls: [multi-c-easy-lookup](r13-multi-lifecycle.md#u-ca4794ea3aa5), [multi-ev-sh-entry-helpers](r4-multi-event.md#u-6f36ebdb623f)

<a id="u-ebece1e6ab27"></a>
### `Curl_multi_ev_init`

`void Curl_multi_ev_init(struct Curl_multi *multi, size_t hashsize)` · [lib/multi_ev.c:L642-L646][f1]

Initializes the multi's socket hash with the given slot count, keyed by socket values (CURL_HASH_TYPE_SOCKET) using mev_sh_entry_dtor as the element destructor.

contract: [multi-ev-sh-entry-helpers](r4-multi-event.md#u-6f36ebdb623f)

<a id="u-46586b0495e2"></a>
### `Curl_multi_ev_socket_done`

`void Curl_multi_ev_socket_done(struct Curl_multi *multi, struct Curl_easy *data, curl…` · [lib/multi_ev.c:L620-L624][f1]

Public hook when a socket will be closed: purges all knowledge of it via mev_forget_socket with cause 'socket done', including the REMOVE notification when announced.

calls: [mev_forget_socket](r4-multi-event.md#u-0b2bc626c370)

<a id="u-630e6b18b896"></a>
### `Curl_multi_ev_xfer_done`

`void Curl_multi_ev_xfer_done(struct Curl_multi *multi, struct Curl_easy *data)` · [lib/multi_ev.c:L626-L632][f1]

Finalizes a removed transfer: asserts the transfer has no connection left, re-assesses it as a transfer (which drops its interest from sockets and may fire REMOVE callbacks), then removes the transfer's stored pollset from its meta.

The assessment result is intentionally discarded.

calls: [mev_assess](r4-multi-event.md#u-7e4cfdd040dc); uses: [multi-ev-pollset-meta-helpers](r4-multi-event.md#u-679f4a61d16b)

<a id="u-7e4cfdd040dc"></a>
### `mev_assess`

`static CURLMcode mev_assess(struct Curl_multi *multi, struct Curl_easy *data, struct …` · [lib/multi_ev.c:L501-L542][f1]

Core assessment: builds the current pollset for a transfer or connection, diffs it against the last recorded pollset, and reports changes via the socket callback.

Returns CURLM_OK when multi or socket_cb is missing. For a connection it uses Curl_conn_adjust_pollset (mapping CURLE_OUT_OF_MEMORY to CURLM_OUT_OF_MEMORY, anything else to CURLM_INTERNAL_ERROR); otherwise it collects the transfer's pollset via Curl_multi_pollset. It fetches the last pollset from meta and, when absent but sockets exist, creates and attaches a new one; allocation failure yields CURLM_OUT_OF_MEMORY. With a last pollset present it runs mev_pollset_diff; otherwise it asserts the pollset is empty. The temporary pollset is always cleaned up on exit.

calls: [mev_pollset_diff](r4-multi-event.md#u-c87ecd5e78ca), [multi-ev-pollset-meta-helpers](r4-multi-event.md#u-679f4a61d16b)

<a id="u-0b2bc626c370"></a>
### `mev_forget_socket`

`static CURLMcode mev_forget_socket(struct Curl_multi *multi, struct Curl_easy *data, …` · [lib/multi_ev.c:L222-L273][f1]

Purges all multi-side knowledge of socket s and, if it was announced, tells the application's socket callback CURL_POLL_REMOVE.

Returns CURLM_OK immediately when no hash entry exists. It removes s from every still-registered transfer pollset (found via each mid in the entry's spbset) and from the connection's pollset, then invokes socket_cb under the multi API guard; a callback return of -1 sets multi->dead and yields CURLM_ABORTED_BY_CALLBACK. After the callback it re-fetches the entry (the callback may have mutated the hash) to clear announced before killing the entry.

**Notes.**

- side_effect: Removes the socket from cached pollsets so stale references disappear.

calls: [multi-ev-sh-entry-helpers](r4-multi-event.md#u-6f36ebdb623f), [multi-ev-pollset-meta-helpers](r4-multi-event.md#u-679f4a61d16b)

**Uncertainties.**

- If the re-fetched entry is gone after the callback, announced clearing is silently skipped; whether any other callback behavior can affect this path is not visible here.

<a id="u-c87ecd5e78ca"></a>
### `mev_pollset_diff`

`static CURLMcode mev_pollset_diff(struct Curl_multi *multi, struct Curl_easy *data, s…` · [lib/multi_ev.c:L354-L499][f1]

Reconciles the transfer's current pollset ps against the previously recorded prev_ps, updating the socket hash and firing the socket callback for changes.

First loop over ps: a socket without a hash entry is created (CURLM_OUT_OF_MEMORY on failure); first_time holds when the entry is new, or, for a connection, the conn is unregistered, or, for a transfer, the mid is unknown. For first_time the conn/mid is registered and prev_ps actions are deliberately ignored because the socket may have been destroyed and reopened; otherwise last_action is looked up in prev_ps. mev_sh_entry_update then reports changes. Second loop over prev_ps sockets no longer in ps: missing entries are normal (already cleaned up); if the conn or transfer was never registered, the mismatch is logged and skipped with a debug assertion; if other users remain, update is called with action 0, otherwise mev_forget_socket removes the socket entirely. Both loops propagate CURLM errors immediately. Finally prev_ps is overwritten with ps via Curl_pollset_move.

**Notes.**

- failure: Registration failures in the first loop and callback aborts in either loop return CURLM_OUT_OF_MEMORY or the propagated CURLMcode, stopping reconciliation.

calls: [mev_sh_entry_update](r4-multi-event.md#u-6c6bc5c5be97), [mev_forget_socket](r4-multi-event.md#u-0b2bc626c370), [multi-ev-sh-entry-helpers](r4-multi-event.md#u-6f36ebdb623f)

**Uncertainties.**

- DEBUGASSERT(NULL) suggests mismatch cases are treated as impossible; behavior in non-debug builds is to skip and continue.

<a id="u-6c6bc5c5be97"></a>
### `mev_sh_entry_update`

`static CURLMcode mev_sh_entry_update(struct Curl_multi *multi, struct Curl_easy *data…` · [lib/multi_ev.c:L275-L352][f1]

Applies one transfer's action change (last_action to cur_action) on socket s to the shared entry's reader/writer counters and notifies the socket callback only when the combined socket action changes.

Returns early if socket_cb is missing or actions are equal. Counters increment when cur_action newly has POLL_IN or POLL_OUT, decrement when last had it and cur no longer does. The combined action is POLL_OUT if any writer plus POLL_IN if any reader; unchanged from entry->action means no callback. A callback return of -1 sets multi->dead and returns CURLM_ABORTED_BY_CALLBACK. Because curl_easy_pause() may re-enter and free the entry, it is re-fetched from the hash before setting announced and action; a NULL re-fetch leaves state untouched.

**Notes.**

- side_effect: readers/writers are mutated even if the callback later aborts.

calls: [multi-ev-sh-entry-helpers](r4-multi-event.md#u-6f36ebdb623f); uses: [multi-ev-sh-entry-helpers](r4-multi-event.md#u-6f36ebdb623f)

<a id="u-9e9a74502c33"></a>
### `multi_ev.c module code (L1–L43)`

`module_region` · [lib/multi_ev.c:L1-L43][f1]

File header: license text plus include of curl_setup.h and the module's internal headers.

<a id="u-6aa160790024"></a>
### `multi_ev.c module code (L57–L59)`

`module_region` · [lib/multi_ev.c:L57-L59][f1]

Separator comment introducing the mev_sh_entry struct.

<a id="u-928b81b1db3e"></a>
### `multi_ev.c module code (L68–L70)`

`module_region` · [lib/multi_ev.c:L68-L70][f1]

Comment marking mev_sh_entry_dtor as the sockhash entry destructor callback.

<a id="u-e1e36e3b27d8"></a>
### `multi_ev.c module code (L79–L81)`

`module_region` · [lib/multi_ev.c:L79-L81][f1]

Comment for mev_sh_entry_get: look up a socket, skip invalid sockets.

<a id="u-873061ce39ba"></a>
### `multi_ev.c module code (L109–L111)`

`module_region` · [lib/multi_ev.c:L109-L111][f1]

Comment for mev_sh_entry_add: ensure the socket is present in the hash.

<a id="u-11cbd7980bc6"></a>
### `multi_ev.c module code (L218–L221)`

`module_region` · [lib/multi_ev.c:L218-L221][f1]

Comment introducing mev_forget_socket (purge socket info, notify callback when necessary).

<a id="u-fa0a432ac68f"></a>
### `mev_sh_entry`

`struct mev_sh_entry` · [lib/multi_ev.c:L44-L57][f1]

Per-socket bookkeeping entry for the multi handle's socket hash: a sparse bitset of transfer mids using the socket, an optional owning connection, application user_data from curl_multi_assign(), the last announced poll action, reader/writer counts, and an announced flag set once the socket callback has seen the socket.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/multi_ev.c
