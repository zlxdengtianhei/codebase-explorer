# Multi Drive, Wait and Timers

**Capability.** Owns the outer driving entry points (multi_perform, multi_socket), platform wait implementations, the multi splay of per-handle timers, timer set/clear/expiry processing, and dirty-transfer rerun. It decides when transfers are executed and when the application should be woken or polled again.

Use this to understand event-driven vs socket-callback-driven operation and how per-handle timeouts feed the multi-level timer splay. Expiry marks handles dirty and re-arms remaining timers.

**Depends on.**

- [API Enter/Leave Guards](r13-api-guards.md) · graph-confirmed · 14 edge(s)
- [Multi Handle Lifecycle and Registry](r13-multi-lifecycle.md) · graph-confirmed · 14 edge(s)
- [Per-Transfer State Machine](r13-multi-statemachine.md) · graph-confirmed · 10 edge(s)
- [Integer-Keyed Containers](r3-int-containers.md) · graph-only · 32 edge(s)
- [Multi Interface Engine](r13-multi-engine.md) · within containment · 3 edge(s)

Parent: [Multi Interface Engine](r13-multi-engine.md)

## Units (19)

<a id="u-c7db6e5b4783"></a>
### `multi-c-per-handle-timeouts`

`static void multi_timeouts_init(struct Curl_easy *data)` · [lib/multi.c:L3131-L3135][f1]

Per-handle timeout list management.

multi_timeouts_init resets a handle's expire list to empty (head EXPIRE_LAST, node unregistered). multi_set_timeout removes any prior entry for the id (via multi_clear_timeout), stores the absolute microsecond offset, and inserts the id into the singly linked list sorted by offset so the head is always the nearest deadline. multi_clear_timeout validates the id, unlinks it, and — when the handle is registered in the multi's splay and the head changed or the list became empty — removes the handle from the splay, re-adding it if deadlines remain. Curl_expire_set computes an absolute stamp from pnow plus ms (capped at INT_MAX ms), replaces that id's entry, and only touches the multi splay when the newly set timer becomes or changes the head; if a previously-registered head still comes first nothing changes. Curl_expire is a convenience wrapper using the current time; Curl_expire_clear removes one id; Curl_expire_clear_all removes the handle's splay node and reinitializes the list, doing nothing without a multi. multi_timeouts_check (debug only) validates the list terminates, has no self-loops, and stays sorted, reporting violations via failf.

calls: [function::Curl_timeouts_add][f2], [function::Curl_timeouts_remove][f2], [function::Curl_trc_timer][f3]

**Uncertainties.**

- The duplicated assignment 'timeouts->next[eid] = *anchor;' in multi_set_timeout is redundant but harmless; no behavioral difference is derivable

<a id="u-ebd32a3c7e31"></a>
### `multi_perform`

`static CURLMcode multi_perform(struct Curl_multi *multi, int *running_handles)` · [lib/multi.c:L2898-L2972][f1]

Drives all transfers in the process set once per curl_multi_perform call.

Timestamped at entry (the entry time, not current time, must be used for expiry removal to avoid dropping unhandled timers), with sigpipe context initialized and restored around the run. Each process-set transfer runs through multi_runsingle, collecting the first error; missing table entries are asserted and pruned. Afterwards: pending rescheduling on state change, notification dispatch when queued, and removal of all timers expired at the entry timestamp — each removed timer's transfer re-arms via add_next_timeout, and PENDING transfers whose timeout fired get multi_handle_timeout applied and are moved back to CONNECT. *running_handles receives the alive-transfer count clamped to INT_MAX. If the result is CURLM_OK or better, Curl_update_timer refreshes the application timer.

**Notes.**

- side_effect: Expired timers are pruned with the function-entry timestamp so timers expiring during processing are not lost.

<a id="u-b183b831daed"></a>
### `multi_socket`

`static CURLMcode multi_socket(struct Curl_multi *multi, bool checkall, curl_socket_t …` · [lib/multi.c:L3249-L3329][f1]

Socket-based entry point.

With checkall it simply runs multi_perform and then reassesses event registration for the whole process set (except a CURLM_BAD_HANDLE result). Otherwise: a real socket marks all transfers of that socket dirty; CURL_SOCKET_TIMEOUT resets last_expire_offset_us to force a timer callback even for an unchanged deadline and, for apps that register socket_cb after adding transfers, assesses the admin wakeup first. It then marks timers expired now as dirty and runs dirty transfers; if any ran, a fresh timestamp catches newly expired timers and runs them once more (exactly once, to stay fair to other sockets). The sigpipe context wraps the run. Finally, connection-state changes reschedule pending transfers, queued notifications dispatch, *running_handles gets the clamped alive count, and on success Curl_update_timer refreshes the app timer.

**Uncertainties.**

- ev_bitmask is accepted but unused in this implementation

<a id="u-d4e125ebbd6d"></a>
### `multi_wait`

`static CURLMcode multi_wait(struct Curl_multi *multi, struct curl_waitfd extra_fds[],…` · [lib/multi.c:L1522-L1642][f1]

Core wait for curl_multi_wait/poll.

Rejects negative timeouts with CURLM_BAD_FUNCTION_ARGUMENT. It collects pollfds: each process-set transfer's pollset (missing entries asserted and pruned from process/dirty; allocation failure -> CURLM_OUT_OF_MEMORY), the shutdown queue's fds, then — when extrawait, existing fds, or extra user fds exist (ENABLE_WAKEUP) — the wakeup socket read end is appended so curl_multi_wakeup interrupts the wait. User extra_fds follow with translated event bits. The internal timeout is queried only after collection, since collecting sockets can install new timers, and the shorter of internal and requested timeout is used; with !extrawait and no internal timers, multi_timeout yields no wait. The platform backend (multi_winsock_select or multi_posix_poll) performs the wait. Finally, if the wakeup socket fired, its signal is consumed and excluded from the returned event count. Scratch structures are always cleaned up and *ret (if non-NULL) gets the event count.

**Uncertainties.**

- Exact timeout semantics when multi_timeout reports no timers and extrawait is FALSE rest on multi_timeout's 0/negative convention

<a id="u-d9647d01e346"></a>
### `multi_posix_poll`

`static CURLMcode multi_posix_poll(struct Curl_multi *multi, struct curl_pollfds *cpfd…` · [lib/multi.c:L1469-L1516][f1]

POSIX implementation of the multi wait.

With collected fds it runs Curl_poll for timeout_ms, mapping a negative result to CURLM_UNRECOVERABLE_POLL, and translates each extra fd's trailing poll revents into CURL_WAIT_POLLIN/POLLOUT/POLLPRI bits. With no fds but extrawait, it sleeps via curlx_wait_ms(timeout_ms), since Curl_poll may return immediately on some platforms when the fd list is empty. Without fds and without extrawait it returns immediately with zero events. *pnevents receives the count.

<a id="u-92c68624a250"></a>
### `multi_winsock_select`

`static CURLMcode multi_winsock_select(struct Curl_multi *multi, struct curl_pollfds *…` · [lib/multi.c:L1361-L1465][f1]

Winsock implementation of the multi wait.

For each collected pollfd it builds a WSA event mask (POLLIN -> FD_READ|FD_ACCEPT|FD_CLOSE, POLLPRI -> FD_OOB, POLLOUT -> FD_WRITE|FD_CONNECT|FD_CLOSE plus a reset_socket_fdwrite call that nudges TCP FD_WRITE state with a zero-length send), attaches it to the multi's WSA event, and maps WSAEventSelect failure to CURLM_OUT_OF_MEMORY. If there are curl fds or extrawait: a zero-timeout Curl_poll pre-check counts immediately ready fds (negative result -> CURLM_UNRECOVERABLE_POLL); if none, it blocks in WSAWaitForMultipleEvents for timeout_ms. Then, unconditionally so WSAEventSelect(fd, event, 0) detaches every socket, it enumerates network events for extra fds and curl fds, translating them to CURL_WAIT_* revent bits; when the pre-poll found nothing, any reported network events increment nevents. For extra fds with a positive pre-poll, revents come from the poll results instead. The event is reset before returning; *pnevents always receives the count. reset_socket_fdwrite only issues the empty send for SOCK_STREAM sockets, since an empty UDP datagram would actually go out.

**Uncertainties.**

- Whether WSAEnumNetworkEvents failures other than returning 0 should count as errors is not handled explicitly

<a id="u-e8eb67091b9f"></a>
### `multi_timeout`

`static void multi_timeout(struct Curl_multi *multi, timediff_t *pexire_offset_us, int…` · [lib/multi.c:L3524-L3562][f1]

Computes the multi's next timer value in ms.

A dead multi reports 0 immediately so the app re-enters promptly. If any dirty transfer is currently processed (multi_has_dirties, which also prunes stale dirty entries), the timeout is 0 and the offset reflects now, since work is outstanding. Otherwise Curl_timeouts_next_ms reports the nearest splay deadline and the owning mid, with verbose tracing of the winning timer. pexire_offset_us (optional) receives the absolute offset for timer-change detection; *timeout_ms is always written.

<a id="u-d5e1509288a4"></a>
### `Curl_update_timer`

`CURLMcode Curl_update_timer(struct Curl_multi *multi)` · [lib/multi.c:L3585-L3637][f1]

Notifies the application's timer callback only when needed.

With no timer callback or a dead multi it does nothing. It queries multi_timeout, then decides: no timeout now and none set before — nothing; timeout cleared though one existed — callback with -1; first timeout — callback with the value; new timeout whose absolute offset differs from the last — callback even if the ms value is identical, because the deadline moved; identical offset — no callback since the app timer still runs. On callback (inside multi-callback guards) the recorded offset and set-flag update first; a callback return of -1 marks the multi dead and returns CURLM_ABORTED_BY_CALLBACK.

<a id="u-8d88bc1ba951"></a>
### `Curl_expire_set`

`void Curl_expire_set(struct Curl_easy *data, expire_id eid, timediff_t ms, const stru…` · [lib/multi.c:L3750-L3797][f1]

Sets or replaces one of a handle's named timers relative to pnow.

Without a multi it is a no-op. Milliseconds above INT_MAX are capped. The absolute stamp is computed with usec normalization, stored via multi_set_timeout (which sorts the per-handle list), and the multi splay is updated only when the new timer is or becomes the earliest: if a previously-earlier timer id still heads the list, nothing changes; otherwise the handle is removed from and re-added to the splay at the new head offset.

calls: [function::Curl_timeouts_add][f2], [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77)

<a id="u-c0224d30f7cf"></a>
### `Curl_expire_clear_all`

`void Curl_expire_clear_all(struct Curl_easy *data)` · [lib/multi.c:L3818-L3835][f1]

Removes the handle's node from the multi timeout splay entirely and reinitializes its per-handle timer list, only when a multi is attached.

Returns silently when nothing was registered.

<a id="u-27b8c1680859"></a>
### `add_next_timeout`

`static CURLMcode add_next_timeout(const struct curltime *pnow, struct Curl_multi *mul…` · [lib/multi.c:L3147-L3168][f1]

After a handle's splay node was removed because its earliest timer expired, advances past all per-handle timers already expired at the given now (comparing stored offsets to the multi timeout clock's offset for pnow) and, if a future timer remains, re-adds the handle to the multi's splay at that offset.

Always returns CURLM_OK.

<a id="u-5ab4dbdc15f9"></a>
### `multi_mark_expired_as_dirty`

`static void multi_mark_expired_as_dirty(struct Curl_multi *multi, const struct curlti…` · [lib/multi.c:L3170-L3199][f1]

Removes every splay timer expiring at or before the given timestamp: for each removed mid it looks up the transfer (missing entries assert and are skipped), re-arms remaining timers via add_next_timeout, and marks the transfer dirty so multi_run_dirty processes it.

Missing transfers simply continue the loop.

<a id="u-4208601191c1"></a>
### `multi_run_dirty`

`static CURLMcode multi_run_dirty(struct Curl_multi *multi, struct Curl_sigpipe_ctx *s…` · [lib/multi.c:L3201-L3247][f1]

Runs all dirty transfers, counting processed ones into *pnum.

For each dirty mid: an unknown transfer is dropped from dirty. A dirty transfer not in the process set is either pending — moved to CONNECT via move_pending_to_connect to act on the event — or no longer processed and dropped. Qualifying transfers run through multi_runsingle (which clears their dirty bit); afterwards, on CURLM_OK-or-better, the transfer's event registration is reassessed via Curl_multi_ev_assess_xfer, with failure aborting the loop. The first error code propagates.

<a id="u-9d0c03752ab2"></a>
### `curl_multi_fdset`

`CURLMcode curl_multi_fdset(CURLM *m, fd_set *read_fd_set, fd_set *write_fd_set, fd_se…` · [lib/multi.c:L1240-L1293][f1]

Public fd_set collector under the API guard.

Iterates the process bitset, builds each transfer's pollset with Curl_multi_pollset, and FD_SETs sockets into read/write sets per their actions, skipping sockets that do not fit an fd_set and tracking the maximum fd; missing table entries assert and are skipped. Also folds in the shutdown queue's fds via Curl_cshutdn_setfds, stores the max (or -1 when empty) into *max_fd, and cleans up the scratch pollset. exc_fd_set is intentionally unused.

**Uncertainties.**

- Curl_multi_pollset errors are ignored here; a failed pollset contributes no fds

<a id="u-8e9b3a1ee3c8"></a>
### `curl_multi_waitfds`

`CURLMcode curl_multi_waitfds(CURLM *m, struct curl_waitfd *ufds, unsigned int size, u…` · [lib/multi.c:L1295-L1344][f1]

Public wait-fd collector under the API guard.

Validates arguments: a NULL ufds is only acceptable with size 0 and a non-NULL fd_count, else CURLM_BAD_FUNCTION_ARGUMENT. It builds each process-set transfer's pollset, adds it to a Curl_waitfds via Curl_waitfds_add_ps, then adds shutdown-queue fds, counting total need. Missing table entries are asserted and pruned from process and dirty. If more fds were needed than fit and ufds was given, it returns CURLM_OUT_OF_MEMORY; *fd_count always receives the needed count when non-NULL.

<a id="u-cab73b5fcac9"></a>
### `curl_multi_setopt`

`CURLMcode curl_multi_setopt(CURLM *m, CURLMoption option, ...)` · [lib/multi.c:L3332-L3461][f1]

Public option setter under the API guard, parsing varargs per option.

Direct field stores: socket/push/timer callbacks and their user data, notify callback/data, quick_exit flag, and PIPELINING (multiplexing on only when CURLPIPE_MULTIPLEX bit set). MAXCONNECTS stores only values <= UINT32_MAX (silently ignoring larger). MAX_HOST_CONNECTIONS and MAX_TOTAL_CONNECTIONS convert long via curlx_sltouz, returning CURLM_BAD_FUNCTION_ARGUMENT on conversion failure and clamping to UINT32_MAX. MAX_CONCURRENT_STREAMS resets to 100 when conversion fails, the value is 0, or above INT_MAX; otherwise stores clamped to UINT32_MAX. NETWORK_CHANGED maps the legacy all-bits value to DNS|CONNS, then clears the DNS cache and/or signals the connection pool per bits. RESOLV_THREADS_MAX (threaded resolver builds) validates a positive <= UINT32_MAX long and maps Curl_async_thrdd_multi_set_props results to CURLM codes, defaulting unknown errors to CURLM_INTERNAL_ERROR. Five legacy pipelining options are accepted and ignored. Unknown options yield CURLM_UNKNOWN_OPTION. va_end runs before the guard leaves.

**Uncertainties.**

- Whether a bad long conversion for HOST/TOTAL connections should leave the old value untouched is implied but not stated

<a id="u-b90e537bfb63"></a>
### `curl_multi_info_read`

`CURLMsg *curl_multi_info_read(CURLM *m, int *msgs_in_queue)` · [lib/multi.c:L3096-L3118][f1]

Pops one completed-transfer message.

It zeroes *msgs_in_queue first, then under the API guard takes the first mid from the msgsent bitset, removes it, reports the remaining count (converted to int), and returns a pointer to that transfer's embedded CURLMsg — or NULL when the table entry is already gone (asserted). Subsequent calls retrieve further messages until the set is empty.

**Uncertainties.**

- The returned msg pointer into the easy handle is invalidated if the handle is removed/cleaned; the code itself offers no protection

<a id="u-8b1f2d0726bd"></a>
### `curl_multi_get_handles`

`CURL **curl_multi_get_handles(CURLM *m)` · [lib/multi.c:L3918-L3946][f1]

Returns a malloc'd NULL-terminated array of the non-internal easy handles currently in the multi, under the API guard.

The array is sized from the xfers table count plus one for the terminator; internal handles (like the admin) are skipped, leaving the array possibly shorter than allocated. Returns NULL on allocation failure or guard failure; the caller owns the array.

**Uncertainties.**

- Whether the caller must free the array with curl_free is not stated in this file

<a id="u-7c3330d062a1"></a>
### `curl_multi_get_offt`

`CURLMcode curl_multi_get_offt(CURLM *m, CURLMinfo_offt info, curl_off_t *pvalue)` · [lib/multi.c:L3948-L3995][f1]

Public integer statistics getter under the API guard.

Rejects a NULL pvalue with CURLM_BAD_FUNCTION_ARGUMENT. XFERS_CURRENT counts the xfers table minus the admin handle; XFERS_RUNNING counts the process set minus the admin when present; XFERS_PENDING counts the pending set; XFERS_DONE counts the msgsent set; XFERS_ADDED returns the lifetime added counter. Unknown info sets *pvalue to -1 and returns CURLM_UNKNOWN_OPTION.

**Uncertainties.**

- Whether the admin subtraction for RUNNING uses a mid that is guaranteed in the set is only guarded by the contains check

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/multi.c
[f2]: ../../../../../../eval/curl-2c04412/lib/splay.c
[f3]: ../../../../../../eval/curl-2c04412/lib/curl_trc.c
