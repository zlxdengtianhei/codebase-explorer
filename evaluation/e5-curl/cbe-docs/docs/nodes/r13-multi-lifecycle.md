# Multi Handle Lifecycle and Registry

**Capability.** Owns creation and destruction of multi handles, adding/removing easy handles, the easy-handle lookup registry, per-multi shared transfer buffers, xfer table registration, and connection-return decisions. Everything else in the engine resolves handles and registers state through this layer.

Use this to trace how a multi handle and its easy handles come into and leave existence, and where per-multi shared state (xfers, bufs) lives. Public wrappers here guard calls and delegate to these internals.

**Depends on.**

- [API Enter/Leave Guards](r13-api-guards.md) · graph-confirmed · 26 edge(s)
- [Integer-Keyed Containers](r3-int-containers.md) · graph-only · 34 edge(s)
- [Integer-keyed containers](r15-uint-containers.md) · graph-only · 24 edge(s)
- [Multi Interface Engine](r13-multi-engine.md) · within containment · 4 edge(s)

**Depended on by.**

- [Per-Transfer State Machine](r13-multi-statemachine.md) · graph-confirmed · 8 edge(s)
- [Multi Drive, Wait and Timers](r13-multi-timers-wait.md) · graph-confirmed · 14 edge(s)

Parent: [Multi Interface Engine](r13-multi-engine.md)

## Units (12)

<a id="u-09230e564764"></a>
### `multi-c-public-api-wrappers`

`CURLMcode curl_multi_add_handle(CURLM *m, CURL *curl)` · [lib/multi.c:L573-L588][f1]

Thin public API wrappers that serialize access through CURL_MAPI_ENTER/CURL_MAPI_LEAVE guards and delegate to the internal implementation.

Handle-taking wrappers first validate the easy handle with GOOD_EASY_HANDLE and reject internal handles with CURLM_BAD_EASY_HANDLE. curl_multi_wait and curl_multi_poll both call multi_wait, differing only in extrawait (FALSE vs TRUE), which controls whether the wait honors the timeout with no sockets and whether the wakeup socket is monitored. curl_multi_socket, curl_multi_socket_action, and curl_multi_socket_all call multi_socket with checkall FALSE/TRUE and the given socket/ev_bitmask (socket_all uses CURL_SOCKET_BAD and checkall TRUE). curl_multi_timeout calls the internal multi_timeout and widens the int to long. curl_multi_assign delegates to Curl_multi_ev_assign; curl_multi_notify_enable/disable delegate to Curl_mntfy_enable/disable; curl_multi_perform delegates to multi_perform.

**Uncertainties.**

- Semantics of CURL_MAPI_ENTER guard failure paths live in lib/api.c

<a id="u-ca4794ea3aa5"></a>
### `multi-c-easy-lookup`

`struct Curl_easy *Curl_multi_get_easy(struct Curl_multi *multi, uint32_t mid)` · [lib/multi.c:L4168-L4178][f1]

Easy-handle registry helpers.

Curl_multi_get_easy looks a mid up in the xfers table, validates the magic, and on a bad entry logs, removes the entry, and returns NULL. Curl_multi_knows_easy reports whether the table entry for a handle's mid is exactly that handle. multi_xfers_running returns xfers_alive (0 for a NULL multi, asserted). Curl_multi_xfers_attached returns the table count minus one to discount the admin handle. Curl_multi_mark_dirty/Curl_multi_clear_dirty set or clear a handle's dirty bit, ignored when the handle has no multi or an unset mid.

**Uncertainties.**

- Curl_multi_xfers_attached can underflow if only the admin is registered; no guard exists

<a id="u-7ec452e6150f"></a>
### `multi-c-xfer-bufs`

`static struct Curl_fixed_buf *fixed_buf_create(size_t len)` · [lib/multi.c:L3997-L4006][f1]

Per-multi shared transfer buffers with single-borrower semantics.

fixed_buf_create allocates a Curl_fixed_buf header plus payload in one block, rejecting sizes that would overflow SIZE_MAX. The buffer borrowers (xfer_buf using set.buffer_size, ulbuf using set.upload_buffer_size, sockbuf using an explicit length) all fail with CURLE_FAILED_INIT when the handle has no multi or (buf only) a zero buffer size, and with CURLE_AGAIN when that buffer is already borrowed; an existing buffer smaller than the requested size is freed and reallocated, allocation failure yielding CURLE_OUT_OF_MEMORY with a logged message. On success the borrower flag is set and the caller receives the data pointer and length (sockbuf: pointer only). Releases only clear the borrower flag after asserting the passed pointer matches (sockbuf frees the pointer instead when there is no multi, matching the share-admin fallback in its borrow). multi_xfer_bufs_free frees all three buffers and clears all flags; it is called when the process set empties and during multi cleanup.

**Uncertainties.**

- Whether buffers can outlive a borrow across multi cleanup safely relies on the free-when-idle call site

<a id="u-3360be030dd9"></a>
### `multi-c-aux-helpers`

`static void ph_freeentry(void *p)` · [lib/multi.c:L200-L207][f1]

Small bookkeeping helpers.

ph_freeentry is the proto_hash destructor that must never run: it only asserts its argument is NULL, since hash entries carry their own destructors. multi_addmsg marks a finished transfer's message as unread: when the msgsent bitset was empty it notifies the admin handle with CURLMNOTIFY_INFO_READ, then adds the transfer's mid to msgsent so curl_multi_info_read can later return it.

<a id="u-3dbcbea8f7db"></a>
### `Curl_multi_handle`

`struct Curl_multi *Curl_multi_handle(uint32_t xfer_table_size, size_t ev_hashsize, /*…` · [lib/multi.c:L223-L375][f1]

Allocates and initializes a multi handle with caller-supplied table and hash sizes, returning NULL on any failure.

It allocates the struct, creates the internal admin easy handle (whose lazy global-init check must run before curlx_pnow is safe), then initializes timeouts, DNS cache, notification list, event handling, the xfers table and process/dirty/pending/msgsent bitsets, proto_hash (with ph_freeentry as impossible destructor), and the shutdown queue; sets multiplexing on and max_concurrent_streams to 100. It then resizes the bitsets/table to xfer_table_size (jumping to the error path on failure), registers the admin handle in xfers and process, initializes the connection pool, and conditionally creates the TLS session cache, Winsock event, wakeup socketpairs, IPv6 probe, and threaded resolver (smaller thread counts for easy-size tables). Any of these may goto error, which tears down everything initialized so far in reverse and returns NULL. In debug builds, CURL_DEBUG enables admin verbosity and CURL_DBG_MAX_TOTAL_CONNECTIONS caps connections. curl_multi_init is the public wrapper passing the default sizes.

uses: [multi-c-aux-helpers](r13-multi-lifecycle.md#u-3360be030dd9)

**Uncertainties.**

- Whether Curl_probeipv6 or Curl_async_thrdd_multi_init can partially fail beyond the goto is not visible here

<a id="u-d7936e7e92c7"></a>
### `Curl_multi_add_handle`

`CURLMcode Curl_multi_add_handle(struct Curl_multi *multi, struct Curl_easy *data)` · [lib/multi.c:L470-L571][f1]

Adds an easy handle to a multi handle, rejecting re-adds with CURLM_ADDED_ALREADY when data->multi is already set.

If the multi is 'dead' (a prior callback error), the add aborts with CURLM_ABORTED_BY_CALLBACK unless only the admin handle remains, in which case deadness is cleared and the bookkeeping bitsets reset. A private multi handle left over from curl_easy_perform is destroyed. multi_xfers_add assigns the mid (failure returns CURLM_OUT_OF_MEMORY), then timeouts are initialized; from that point no failure is allowed. The handle is wired to the multi, set to MSTATE_INIT, PSL source selected (share or multi), added to the process set, alive counters incremented, connection-pool transfer init run, and it is marked dirty so it runs. If Curl_update_timer fails afterwards, the additions are rolled back (multi link cleared, table entry removed, mid reset to UINT32_MAX) and the error returned. Finally the admin handle's timeout, response timeout, and no_signal settings are cloned from the most recently added handle.

**Notes.**

- side_effect: Admin handle timeout settings are overwritten by each added transfer's values.

calls: [function::multi_xfers_add][f1], [function::Curl_update_timer][f1]

**Uncertainties.**

- Whether Curl_cpool_xfer_init can fail is not visible; its result is not checked

<a id="u-f59ff4660867"></a>
### `Curl_multi_remove_handle`

`CURLMcode Curl_multi_remove_handle(struct Curl_multi *multi, struct Curl_easy *data)` · [lib/multi.c:L758-L882][f1]

Removes an easy handle from its multi handle.

It is a no-op returning CURLM_OK if the handle has no multi, CURLM_BAD_EASY_HANDLE on a multi mismatch, and CURLM_INTERNAL_ERROR if the mid is invalid or the xfers table lookup disagrees. For a transfer not yet COMPLETED (premature) with a connection, the stream is closed if past DO, and multi_done runs (result ignored). All timers are cleared before data->multi is nulled so no splay node outlives the easy handle. Alive counters are decremented (MSGSENT already deducted xfers_alive; really_alive also assessed for wakeup when it hits zero), the wildcard destructor runs, state forced to COMPLETED, connection detached, and event handling told the transfer is gone. connect_only handles get their connection marked for closure: through the private multi_easy path only if bits.connect_only, otherwise closed outright via Curl_conn_close since the handle can no longer find it. PSL association is dropped, the mid removed from xfers and all four bitsets, mids reset to UINT32_MAX, pending transfers rescheduled, and the timer and wakeup reassessed; failures there propagate.

**Notes.**

- failure: Curl_update_timer or wakeup-assess failures abort removal after the handle is already detached, returning the error code.

**Uncertainties.**

- Interaction when Curl_getconnectinfo returns no connection for connect_only is unchecked in the code

<a id="u-dadbcdca0d4d"></a>
### `Curl_multi_add_perform`

`CURLMcode Curl_multi_add_perform(struct Curl_multi *multi, struct Curl_easy *data, st…` · [lib/multi.c:L1748-L1772][f1]

Adds an easy handle and immediately starts it on an existing connection.

After Curl_multi_add_handle succeeds it initializes the transfer with Curl_init_transfer passing NULL connection (so only the transfer, not the connection, is initialized); on failure it removes the handle again and returns CURLM_INTERNAL_ERROR. Otherwise the handle jumps straight to MSTATE_PERFORMING, is attached matched to the given connection, and the request is set to receive. The add result propagates.

**Uncertainties.**

- Which callers supply a pre-made connection is not visible here

<a id="u-999e0a652e37"></a>
### `curl_multi_cleanup`

`CURLMcode curl_multi_cleanup(CURLM *m)` · [lib/multi.c:L2986-L3087][f1]

Destroys a multi handle under the API guard.

It first removes every remaining easy handle from the xfers table (admin skipped for now): a bad handle aborts with CURLM_BAD_HANDLE before anything is destroyed; transfers never DONE with a connection get multi_done (premature), then the multi association, table entry, and mid are cleared, PSL association dropped, and internal handles closed. The connection pool and shutdown queue are destroyed, then the admin handle is closed. The magic number is zeroed, event handling, proto_hash, DNS cache, PSL, and (when built) TLS session cache, Winsock event, and wakeup pairs are destroyed, transfer buffers freed, notifications cleaned, and in debug builds any remaining xfers trigger a table dump and assert. The bitsets and table are destroyed and the struct is zeroed and freed. Returns CURLM_OK.

**Uncertainties.**

- Whether transfer callbacks may still fire during the teardown sequence is not determinable from this file

<a id="u-6fb676072691"></a>
### `multi_xfers_add`

`static CURLMcode multi_xfers_add(struct Curl_multi *multi, struct Curl_easy *data)` · [lib/multi.c:L416-L468][f1]

Inserts an easy handle into multi->xfers, assigning its mid, growing storage when needed.

If free rows fall below an eighth of capacity (minimum 4) it grows the table by 50% clamped to [128, 2048], capped at UINT_MAX-1 so mids never reach the 'invalid' UINT32_MAX. Growth resizes the four bitsets before the table, since sets tolerate being larger than the table but not smaller; any resize failure returns CURLM_OUT_OF_MEMORY. If the final table insert fails (asserted to mean full), it also returns CURLM_OUT_OF_MEMORY.

**Uncertainties.**

- Exact behavior of the uint-table resize on failure is in uint-table.c

<a id="u-62698a389f13"></a>
### `multi_conn_should_close`

`static bool multi_conn_should_close(struct connectdata *conn, struct Curl_easy *data,…` · [lib/multi.c:L594-L633][f1]

Decides whether a connection must be closed when a transfer finishes with it.

Returns TRUE if conn->bits.close is set; if the client forbade reuse (data->set.reuse_forbid), except during NTLM/NEGOTIATE handshakes at the TYPE2/AUTH_RECV stages where reuse must continue; if the scheme lacks PROTOPT_CONN_REUSE and the transfer is not connect_only; or if the transfer ended prematurely and the connection cannot multiplex. Otherwise FALSE, allowing the connection to be pooled.

**Uncertainties.**

- NTLM/SPNEGO state fields exist only under those build flags; behavior without them rests solely on the other conditions

<a id="u-7fefae2e20d9"></a>
### `multi_done_locked`

`static cpool_do_result multi_done_locked(struct Curl_easy *data, struct connectdata *…` · [lib/multi.c:L635-L671][f1]

cpool callback run when a finished transfer returns its connection.

If the connection is still used by other transfers it returns CPOOL_DO_KEEP so disposal is retried later. Otherwise multi_conn_should_close decides: on close it marks the connection closed via connclose and returns CPOOL_DO_TERMINATE for premature transfers else CPOOL_DO_CLOSE; if the server will not send more (no max concurrent) it likewise closes, logging the shutdown; only a reusable, healthy connection returns CPOOL_DO_IDLE for pooling.

calls: [function::multi_conn_should_close][f1]

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/multi.c
