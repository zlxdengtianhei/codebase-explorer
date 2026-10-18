# Asynchronous Connection Shutdown

**Capability.** Owns graceful, non-blocking teardown of connections outside the connection pool: a shutdown list with enqueue/prune-oldest lifecycle, per-socket shutdown deadlines, incremental shutdown steps driven through filter chains, wait/poll integration, and forced termination.

Use this subtree to understand how closed connections finish their protocol shutdown in the background and how the multi interface waits on them. It is the primary consumer of the filter framework's pollset, state queries, and chain discard functions.

**Depends on.**

- [Filter Chain Lifecycle](r8-cfilters-chain-mgmt.md) · graph-confirmed · 2 edge(s)
- [Filter Events, State and Queries](r8-cfilters-events-state.md) · graph-confirmed · 5 edge(s)

Parent: [curl Codebase](r8-curl-codebase.md)

## Units (12)

<a id="u-649ff17c65cb"></a>
### `cshutdn.c-add`

`static CURLMcode cshutdn_update_ev(struct Curl_multi *multi, struct connectdata *conn)` · [lib/cshutdn.c:L469-L477][f1]

Enqueue a connection for asynchronous shutdown.

cshutdn_update_ev briefly attaches the multi's admin handle, runs Curl_multi_ev_assess_conn to register shutdown socket events, detaches, and returns the CURLMcode. Curl_cshutdn_add first enforces the limit: when max_shutdowns is at or below the current list size it discards the oldest entry via cshutdn_destroy_oldest(NULL destination). If the multi has a socket_cb and cshutdn_update_ev returns failure, or Curl_ptrarray_add fails (allocation), the connection is immediately terminated instead of being listed; on success it is appended and the new count is traced.

calls: [cshutdn.c-add](r8-conn-shutdown.md#u-649ff17c65cb), [cshutdn.c-destroy-oldest](r8-conn-shutdown.md#u-448b6a0d1dd5), [Curl_cshutdn_terminate](r8-conn-shutdown.md#u-a031613cb853)

<a id="u-448b6a0d1dd5"></a>
### `cshutdn.c-destroy-oldest`

`static size_t cshutdn_destroy_oldest(struct cshutdn *cshutdn, struct Curl_easy *admin…` · [lib/cshutdn.c:L275-L298][f1]

Remove and terminate the oldest `count` connections from the shutdown list.

cshutdn_destroy_oldest walks the array with index i; on a destination match (NULL matches all) it removes the entry at i without advancing i because removal shifts later entries down, suppresses SIGPIPE around termination with sigpipe_apply, and destroys the connection with Curl_cshutdn_terminate(do_shutdown=FALSE); on mismatch it advances i. It restores the sigpipe state and returns how many were removed. Curl_cshutdn_close_oldest is the public wrapper returning 0 when cshutdn is NULL.

calls: [Curl_cshutdn_terminate](r8-conn-shutdown.md#u-a031613cb853)

<a id="u-f0d89924cc9b"></a>
### `cshutdn.c-lifecycle`

`void Curl_cshutdn_init(struct cshutdn *cshutdn)` · [lib/cshutdn.c:L416-L419][f1]

Lifecycle and counting for the shutdown list.

Curl_cshutdn_init just initializes the ptrarray. Curl_cshutdn_destroy, when given a non-NULL admin and a non-empty list, terminates all connections via cshutdn_terminate_all; under DEBUGBUILD the env var CURL_GRACEFUL_SHUTDOWN supplies a graceful timeout in ms (parsed with curlx_str_number, ignored on parse failure), otherwise timeout_ms is 0 (best-effort single pass). Curl_cshutdn_count returns the list size, 0 for NULL. Curl_cshutdn_dest_count counts entries whose conn->destination matches the given string via strcmp, returning 0 for NULL; unlike close_oldest it has no NULL-destination wildcard, so a NULL destination here would reach strcmp and is not a valid use.

calls: [cshutdn_terminate_all](r8-conn-shutdown.md#u-285aad4c9ae2)

<a id="u-c4e710b46514"></a>
### `cshutdn.c-shutdown-timers`

`void Curl_cshutdn_start_timer(struct Curl_easy *data, int8_t sockindex, int timeout_ms)` · [lib/cshutdn.c:L43-L61][f1]

Manage the per-socket shutdown deadline on a connection.

Curl_cshutdn_start_timer stamps conn->shutdown.start_ms[sockindex] as ms elapsed since conn->created and picks the timeout from the first positive of the timeout_ms argument, data->set.shutdowntimeout, then DEFAULT_SHUTDOWN_TIMEOUT_MS (2000ms); it arms Curl_expire_set(EXPIRE_SHUTDOWN) only when data->mid is set (admin handles get no timer). Curl_cshutdn_timeleft_ms returns 0 when start_ms is negative (not started/no limit), otherwise timeout minus elapsed since start, with an exact 0 converted to -1 so callers distinguish 'expired' from 'no limit'. cshutdn_conn_timeleft returns the smallest positive timeleft across both indices, looping only while timeout_ms is nonzero and skipping unstarted indices; it returns 0 when nothing is in shutdown. Curl_cshutdn_clear_timer resets one index's start_ms to -1, canceling that side's shutdown.

uses: [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3)

<a id="u-8750cbc0860e"></a>
### `cshutdn.c-wait-perform`

`static CURLcode cshutdn_wait(struct cshutdn *cshutdn, struct Curl_easy *admin, int ti…` · [lib/cshutdn.c:L313-L332][f1]

Maintenance loop machinery for connections being shut down.

cshutdn_wait builds a pollfd set from all shutdown connections via Curl_cshutdn_add_pollfds and polls once, capped at 1000ms by CURLMIN; a failure adding fds is returned, and cleanup always runs. cshutdn_perform returns immediately on an empty list; otherwise it applies SIGPIPE suppression, then iterates: each connection gets Curl_cshutdn_try_once; on done it is removed from the list and terminated, otherwise the smallest positive cshutdn_conn_timeleft is collected and, if any, armed as Curl_expire(EXPIRE_SHUTDOWN). Curl_cshutdn_perform is the trivial public wrapper around cshutdn_perform.

calls: [Curl_cshutdn_terminate](r8-conn-shutdown.md#u-a031613cb853), [cshutdn.c-fdsets](r8-conn-shutdown.md#u-6627908285f2)

<a id="u-6627908285f2"></a>
### `cshutdn.c-fdsets`

`void Curl_cshutdn_setfds(struct cshutdn *cshutdn, struct Curl_easy *admin, fd_set *re…` · [lib/cshutdn.c:L520-L558][f1]

Expose the sockets of connections being shut down to wait mechanisms; all three iterate the list, and per connection attach the admin handle, refresh a reused struct easy_pollset with Curl_conn_adjust_pollset, then detach.

Curl_cshutdn_setfds skips connections whose adjust fails and otherwise FD_SETs sockets per CURL_POLL_IN/CURL_POLL_OUT, skipping sockets failing FDSET_SOCK, and raises *maxfd; it cleans up the pollset afterwards. Curl_cshutdn_add_waitfds adds each successful pollset to a Curl_waitfds and returns the accumulated 'need'. Curl_cshutdn_add_pollfds adds each pollset to a curl_pollfds; on any error it cleans up both the pollset and the whole pollfds structure and returns the error, aborting the remaining connections.

calls: [lib-cfilters-c-pollset](r8-cfilters-events-state.md#u-025f1759dcd7)

<a id="u-a031613cb853"></a>
### `Curl_cshutdn_terminate`

`void Curl_cshutdn_terminate(struct Curl_easy *admin, struct connectdata *conn, bool d…` · [lib/cshutdn.c:L236-L273][f1]

Close and destroy a connection that must already be out of any pool (DEBUGASSERT cpid == UINT32_MAX) and detached from transfers.

It attaches the admin handle, runs the disconnect handler once, and if do_shutdown is set makes one last cshutdn_run_once attempt. Filters are then discarded with Curl_conn_cf_discard_all for SECONDARYSOCKET then FIRSTSOCKET; the trace distinguishes 'force' closing when shutdown_filters was not set. After detaching it frees the connection via Curl_conn_free, and when the admin has a multi handle fires Curl_multi_ev_conn_done and Curl_multi_connchanged.

calls: [cshutdn_run_conn_handler](r8-conn-shutdown.md#u-aec2cc5966ed), [cshutdn_run_once](r8-conn-shutdown.md#u-dc1506bb6f9b)

**Uncertainties.**

- Curl_conn_cf_discard_all and Curl_conn_free behavior is implemented outside this file.

<a id="u-b363435953a0"></a>
### `Curl_cshutdn_try_once`

`void Curl_cshutdn_try_once(struct Curl_easy *admin, struct connectdata *conn, bool *d…` · [lib/cshutdn.c:L224-L234][f1]

Attach the admin handle to the connection, run one shutdown step for both sockets via cshutdn_run_once, then detach; *done is TRUE on error or complete shutdown.

DEBUGASSERTs require the admin handle to hold no connection and no mid.

calls: [cshutdn_run_once](r8-conn-shutdown.md#u-dc1506bb6f9b)

<a id="u-0770abbbde79"></a>
### `Curl_cshutdn_try_once_idx`

`CURLcode Curl_cshutdn_try_once_idx(struct Curl_easy *data, int8_t sockindex, bool *done)` · [lib/cshutdn.c:L127-L181][f1]

Advance non-blocking shutdown of one socket index by driving do_shutdown through its filter chain.

Returns CURLE_BAD_FUNCTION_ARGUMENT for an invalid sockindex. It finds the first connected, not-yet-shutdown filter; if none, *done is TRUE and CURLE_OK returned. If this socket is not yet in shutdown it starts the timer via Curl_cshutdn_start_timer; otherwise it checks timeleft and returns CURLE_OPERATION_TIMEDOUT (logged only with infof, treated as potentially acceptable) when expired. Iterating filters: do_shutdown error is returned immediately with the filter unmarked; cfdone FALSE returns CURLE_OK with *done FALSE for later resumption; success marks cf->shutdown TRUE and continues. *done is TRUE only when the whole chain finished without error.

calls: [cshutdn.c-shutdown-timers](r8-conn-shutdown.md#u-c4e710b46514); group: [cshutdn_run_conn_handler](r8-conn-shutdown.md#u-aec2cc5966ed)

**Uncertainties.**

- Filter do_shutdown semantics are defined in filter implementations outside this source.

<a id="u-aec2cc5966ed"></a>
### `cshutdn_run_conn_handler`

`static void cshutdn_run_conn_handler(struct Curl_easy *data, struct connectdata *conn)` · [lib/cshutdn.c:L99-L125][f1]

Run the protocol disconnect handler at most once per connection.

Guarded by conn->bits.shutdown_handler: if already set, it is a no-op; the flag is set on exit even when conn->scheme is NULL or lacks a disconnect callback. When a disconnect exists and data->state.internal is set (internal handle), data->set.timeout is capped to DEFAULT_SHUTDOWN_TIMEOUT_MS and TIMER_STARTOP is stamped, so blocking handlers such as FTP/IMAP/SMTP/SFTP cannot hang for the default 120 seconds. The disconnect is invoked with (bool)conn->bits.aborted.

**Notes.**

- side_effect: data->set.timeout is overwritten persistently on internal handles; restoration is not visible in this file.

**Uncertainties.**

- Whether data->set.timeout is restored afterwards is decided outside this file.

<a id="u-dc1506bb6f9b"></a>
### `cshutdn_run_once`

`static void cshutdn_run_once(struct Curl_easy *data, struct connectdata *conn, bool *…` · [lib/cshutdn.c:L183-L222][f1]

Run one non-blocking shutdown step for both sockets of an attached connection.

Starts the FIRSTSOCKET timer if that side is not yet in shutdown, runs the protocol disconnect handler once, and returns early with *done TRUE if conn->bits.shutdown_filters was already set. Per socket: if not connect_only and connected, Curl_cshutdn_try_once_idx runs; otherwise that side is treated as done with result CURLE_OK. *done becomes TRUE when either side failed or both succeeded, and shutdown_filters is then set so later calls short-circuit. DEBUGASSERT requires data->conn == conn.

calls: [Curl_cshutdn_try_once_idx](r8-conn-shutdown.md#u-0770abbbde79), [cshutdn_run_conn_handler](r8-conn-shutdown.md#u-aec2cc5966ed)

<a id="u-285aad4c9ae2"></a>
### `cshutdn_terminate_all`

`static void cshutdn_terminate_all(struct cshutdn *cshutdn, struct Curl_easy *admin, i…` · [lib/cshutdn.c:L370-L414][f1]

Gracefully shut down every connection on the list within timeout_ms, then force-close any remainder.

Each round runs cshutdn_perform; it stops when the list empties ('finished cleanly'), when spent time reaches timeout_ms ('timeout' or, for timeout_ms <= 0, 'best effort done'), or when cshutdn_wait returns an error ('aborted'). Remaining connections are then popped from index 0 and terminated with do_shutdown FALSE, followed by a DEBUGASSERT that the list is empty. SIGPIPE suppression wraps the whole sequence.

calls: [cshutdn.c-wait-perform](r8-conn-shutdown.md#u-8750cbc0860e), [Curl_cshutdn_terminate](r8-conn-shutdown.md#u-a031613cb853)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cshutdn.c
