# Per-Transfer State Machine

**Capability.** Owns the sanctioned state transition primitive (mstate) and all per-state handlers from INIT through CONNECT, DO/DOING, PERFORMING, RATELIMITING to DONE/COMPLETED, plus the pollset builders and protocol-phase drivers they invoke. This is the only place a transfer's progress through connection setup, request execution and completion is decided.

Use this to follow one easy handle through its states. State entry hooks, pollset adjustment and rate limiting are layered here; failure paths converge on multi_done and finalize via is_finished/handle_completed.

**Depends on.**

- [API Enter/Leave Guards](r13-api-guards.md) · graph-confirmed · 2 edge(s) · State-machine dispatch enters and leaves the callback-API guards when invoking internals.
- [Multi Handle Lifecycle and Registry](r13-multi-lifecycle.md) · graph-confirmed · 8 edge(s)
- [Multi Interface Engine](r13-multi-engine.md) · within containment · 10 edge(s)

**Depended on by.**

- [Multi Drive, Wait and Timers](r13-multi-timers-wait.md) · graph-confirmed · 10 edge(s)

Parent: [Multi Interface Engine](r13-multi-engine.md)

## Units (29)

<a id="u-06bd7bc014c8"></a>
### `multi-c-do-delegators`

`static CURLcode multi_do(struct Curl_easy *data, bool *done)` · [lib/multi.c:L1774-L1786][f1]

Thin dispatch to scheme callbacks.

multi_do calls the scheme's do_it when present, returning its result and leaving *done untouched otherwise (done is only meaningful when do_it exists). multi_do_more initializes *complete to DOMORE_INCOMPLETE, then calls the scheme's do_more when present, letting it set DOMORE_DONE or DOMORE_GOBACK; it exists to support protocols with a second connection such as FTP.

**Uncertainties.**

- If a scheme lacks do_it, *done is never assigned by multi_do

<a id="u-fa248c3516ad"></a>
### `multi-c-protocol-phase`

`static CURLcode protocol_connecting(struct Curl_easy *data, bool *done)` · [lib/multi.c:L1869-L1882][f1]

Protocol-phase drivers called repeatedly by the state machine.

protocol_connecting runs the scheme's connecting callback until it reports done; with no connection or callback it reports done immediately with CURLE_OK. protocol_doing is analogous for the scheme's doing callback. protocol_connect asserts the first socket is connected; if the protocol connect has not started it runs connect_it (propagating failure without setting protoconnstart) and marks protoconnstart; it reports protocol_done TRUE immediately when the scheme has no connecting callback, FALSE otherwise.

<a id="u-2a6067f4eb0d"></a>
### `multi-c-state-entry-hooks`

`static void mstate_enter_connect(struct Curl_easy *data, CURLMstate from_state)` · [lib/multi.c:L94-L99][f1]

Per-state entry hooks run once when the state machine transitions into a new state.

mstate_enter_connect initializes the connect phase. mstate_enter_did resets chunk state, records the pretransfer timer, and records posttransfer time when the request does not want to send. mstate_enter_done emits CURLMNOTIFY_EASY_DONE. mstate_enter_completed repairs state for direct jumps to COMPLETED: when entering from a state before DID it back-fills pretransfer, posttransfer, and starttransfer timers; it asserts no connection is attached, marks progress completed, emits the DONE notification if coming from before DONE, removes the mid from the process and pending bitsets, frees the multi's transfer buffers when the process set becomes empty, detaches the connection, and clears all timers via Curl_expire_clear_all. All hooks ignore from_state except the COMPLETED hook.

uses: [function::multi_xfer_bufs_free][f1]; calls: [function::Curl_expire_clear_all][f1]

**Uncertainties.**

- Behavior of Curl_pgrsCompleted and CURLM_NTFY depends on code outside this file

<a id="u-21e144c4f9e1"></a>
### `multi-c-state-pollset`

`static CURLcode mstate_connecting_pollset(struct Curl_easy *data, struct easy_pollset…` · [lib/multi.c:L1004-L1025][f1]

Per-state pollset builders, each layering: scheme-specific hook (if any), a default when absent, rate-limit/pause adjustment via multi_adjust_pollset, then connection-filter adjustment via Curl_conn_adjust_pollset; the first error short-circuits the chain.

mstate_connecting_pollset: skipped entirely when receive is paused; requests POLL_IN on the first socket when known (always consulting filters during eyeballing), then filters. mstate_protocol_pollset: uses the scheme's proto_pollset, defaulting to POLL_IN on the first socket. mstate_do_pollset and mstate_domore_pollset: use the scheme's doing/domore pollset, defaulting to add-out on the connection's send socket when its index is valid. mstate_perform_pollset: uses the scheme's perform_pollset, defaulting to add-in on recv_idx when the request wants receive and add-out on send_idx when it wants send.

calls: [function::multi_adjust_pollset][f1]

**Uncertainties.**

- Behavior of scheme-provided pollset callbacks is external

<a id="u-ffcc6fbf943e"></a>
### `mstate`

`static void mstate(struct Curl_easy *data, CURLMstate state #ifdef DEBUGBUILD , int l…` · [lib/multi.c:L149-L190][f1]

Changes an easy handle's multi state, the only sanctioned way to do so.

If the new state equals the current one it returns without side effects. Otherwise it stores the state, traces the transition (with line number in debug builds), and invokes the per-state entry hook from a static table; states INIT, PENDING, SETUP, CONNECTING, PROTOCONNECT, PROTOCONNECTING, DO, DOING, DOING_MORE, PERFORMING, RATELIMITING, and MSGSENT have NULL hooks and only change the stored state. The multistate() macro passes __LINE__ in debug builds.

<a id="u-38ff00be4559"></a>
### `multi_runsingle`

`static CURLMcode multi_runsingle(struct Curl_multi *multi, struct Curl_easy *data, st…` · [lib/multi.c:L2719-L2896][f1]

Runs one easy handle through its state machine, possibly looping.

A dead multi fails the transfer immediately with CURLE_ABORTED_BY_CALLBACK through posttransfer/multi_done to COMPLETED. The dirty bit is cleared up front (it may be set again during processing). The admin handle is special: it consumes internal wakeup signals, processes the threaded resolver, and runs connection shutdown chores, then exits. Otherwise sigpipe state is applied and a do/while loop runs: connection-state changes reschedule pending transfers; states between CONNECT and COMPLETED must have a connection (else CURLM_INTERNAL_ERROR); live transfers get a timeout check via multi_handle_timeout whose TRUE skips straight to finalization. A switch dispatches per state to the multistate_* helpers; unknown states return CURLM_INTERNAL_ERROR. Stream timeouts are checked only on the loop's final iteration (when no CURLM_CALL_MULTI_PERFORM is pending) so imminent work is not cut short. statemachine_end applies is_finished to the result, transitioning errors to COMPLETED; a completed transfer is finalized by handle_completed and returns CURLM_OK. The loop continues while a state demands re-entry or connection state changed. The final result is stored on data->result.

**Uncertainties.**

- Exact interplay between sigpipe handling and scheme callbacks is external

<a id="u-f5e978336a24"></a>
### `multistate_init`

`static CURLMcode multistate_init(struct Curl_easy *data, CURLcode *result)` · [lib/multi.c:L2469-L2491][f1]

Initial state handler, run once per added handle.

On first run it marks the transfer really_alive, and when it is the first really-alive transfer it enables wakeup listening via multi_assess_wakeup, failing the state with a logged error if that fails. Then Curl_pretransfer runs; on error the result is stored and CURLM_OK returned (the error surfaces via is_finished). Success moves to MSTATE_SETUP, records TIMER_STARTOP, and returns CURLM_CALL_MULTI_PERFORM.

<a id="u-c730887697b7"></a>
### `multistate_setup`

`static CURLMcode multistate_setup(struct Curl_easy *data)` · [lib/multi.c:L2493-L2508][f1]

Prepares a (possibly repeated, e.g. after redirect) transfer attempt: records TIMER_STARTSINGLE, installs the EXPIRE_TIMEOUT timer when a total timeout is set, and installs EXPIRE_CONNECTTIMEOUT once here — before CONNECT — because a handle may bounce to PENDING and back several times.

Moves to MSTATE_CONNECT and returns CURLM_CALL_MULTI_PERFORM.

<a id="u-cbb71e6d28b6"></a>
### `multistate_connect`

`static CURLMcode multistate_connect(struct Curl_multi *multi, struct Curl_easy *data,…` · [lib/multi.c:L2316-L2359][f1]

Runs the CONNECT state, entering from SETUP or PENDING.

Curl_connect either fails with CURLE_NO_CONNECTION_AVAILABLE — in which case the handle moves to MSTATE_PENDING and migrates from process/dirty to the pending bitset, reporting OK — or succeeds/fails otherwise, in which case pending transfers are rescheduled (a slot likely freed). On success with an already-established connection: a brand-new multiplexable connection wakes pending handles, and the state becomes PROTOCONNECT; if the connection is not yet established it becomes CONNECTING. Success sets CURLM_CALL_MULTI_PERFORM; failures propagate through *resultp.

<a id="u-97135e8877df"></a>
### `multistate_connecting`

`static CURLMcode multistate_connecting(struct Curl_easy *data, bool *stream_error, CU…` · [lib/multi.c:L2510-L2542][f1]

Drives TCP connect completion.

A missing connection is an asserted internal failure reported as CURLE_FAILED_INIT. Unless receive is paused, Curl_conn_connect runs on the first socket: on completion with success a new multiplexable connection wakes pending transfers and the state becomes PROTOCONNECT with CURLM_CALL_MULTI_PERFORM; on failure posttransfer and multi_done run (premature) and the stream error flag is set. Paused or not-yet-connected transfers simply keep waiting.

<a id="u-99f8a8518b1b"></a>
### `multistate_protoconnecting`

`static CURLMcode multistate_protoconnecting(struct Curl_easy *data, bool *stream_erro…` · [lib/multi.c:L2578-L2598][f1]

Waits for the protocol-specific connect phase via protocol_connecting.

When done without error the state becomes DO with CURLM_CALL_MULTI_PERFORM; on error posttransfer and multi_done (premature) run and the stream error flag is set; otherwise it keeps waiting.

<a id="u-678be26e716c"></a>
### `multistate_protoconnect`

`static CURLMcode multistate_protoconnect(struct Curl_easy *data, bool *stream_error, …` · [lib/multi.c:L2544-L2576][f1]

Runs protocol connect setup.

A reused connection skips straight to MSTATE_DO because re-running protoconnect on reused connections (e.g. FTP) hangs. Otherwise protocol_connect runs; if it succeeded but the protocol layer is still connecting, the state becomes PROTOCONNECTING with CURLM_CALL_MULTI_PERFORM; if fully connected, DO. Any failure runs posttransfer and multi_done (premature) and sets the stream error flag.

<a id="u-e80b4b1ed176"></a>
### `multistate_do`

`static CURLMcode multistate_do(struct Curl_easy *data, bool *stream_errorp, CURLcode …` · [lib/multi.c:L2155-L2289][f1]

Executes the DO phase.

If a pre-request callback is configured, it is invoked with local/remote ip/port inside callback guards; any return other than CURL_PREREQFUNC_OK aborts with CURLE_ABORTED_BY_CALLBACK, runs posttransfer and multi_done (not premature), sets the stream error flag, and ends. Plain connect_only transfers (non-websocket) jump to DONE. Otherwise multi_do runs the scheme DO. On success: if DO did not complete in one call the state becomes DOING — except for wildcard FTP matching, where a wildcard in DONE/SKIP state runs multi_done and jumps to DONE or straight to COMPLETED when no connection remains; if DO finished and conn->bits.do_more is set the state becomes DOING_MORE; otherwise DID. On CURLE_SEND_ERROR over a reused connection, the likely-dead connection is retried: Curl_retry_request produces a retry URL, posttransfer and multi_done run, and with a URL and multi_done returning OK or SEND_ERROR a FOLLOW_RETRY follow moves the handle back to SETUP (result reset to OK); follow failure or an unexpected multi_done result propagates as the error; with no retry URL the stream error flag is set. Any other failure runs posttransfer and multi_done (not premature) and sets the stream error flag.

**Notes.**

- failure: A pre-request callback abort skips all DO processing and reports the failure to the app via the message queue.

**Uncertainties.**

- Wildcard matching states (CURLWC_DONE/SKIP) semantics are in FTP code

<a id="u-67d5504c495a"></a>
### `multistate_doing`

`static CURLMcode multistate_doing(struct Curl_easy *data, bool *stream_error, CURLcod…` · [lib/multi.c:L2600-L2624][f1]

Continues the DO phase via protocol_doing until complete.

Completion advances to DOING_MORE when conn->bits.do_more is set, else to DID, returning CURLM_CALL_MULTI_PERFORM. Failure runs posttransfer and multi_done (not premature) and sets the stream error flag.

<a id="u-6ec08b844516"></a>
### `multistate_doing_more`

`static CURLMcode multistate_doing_more(struct Curl_easy *data, bool *stream_error, CU…` · [lib/multi.c:L2626-L2655][f1]

Continues the second-stage DO via multi_do_more.

A DOMORE_DONE result advances to DID; DOMORE_GOBACK returns to DOING (e.g. FTP second connection work); DOMORE_INCOMPLETE stays in DOING_MORE. Failure runs posttransfer and multi_done (not premature) and sets the stream error flag.

<a id="u-0c5dd25a7173"></a>
### `multistate_did`

`static CURLMcode multistate_did(struct Curl_multi *multi, struct Curl_easy *data)` · [lib/multi.c:L2657-L2688][f1]

Bridges from request-sent to transfer.

On a multiplexed connection, pending transfers are scheduled. When a valid receive or send socket exists, the state becomes PERFORMING; the return is CURLM_OK instead of CURLM_CALL_MULTI_PERFORM only when more than one transfer is alive and the scheme is HTTP family, deliberately yielding to other transfers (with a noted caveat that some SFTP handlers dislike this). With no usable socket, wildcard FTP transfers on non-wildcard schemes are marked CURLWC_DONE, and the state becomes DONE with CURLM_CALL_MULTI_PERFORM.

**Uncertainties.**

- The SFTP-side impact of the yield is stated in a comment, not verifiable here

<a id="u-9a3ea4843452"></a>
### `multistate_performing`

`static CURLMcode multistate_performing(struct Curl_easy *data, bool *stream_errorp, C…` · [lib/multi.c:L2016-L2051][f1]

Drives the PERFORMING state: after a rate-limit check that may return CURLM_OK to wait (mspeed_check returning CURLE_AGAIN), it runs the transfer I/O via Curl_sendrecv and interprets the outcome.

This covers the function's full body including the sections split off as separate regions. Branches: when the request is done or a CURLE_RECV_ERROR occurred, Curl_retry_request decides on a retry (a race-lost reused connection); a retry resets the result to OK and marks the request done. Independently, a CURLE_HTTP2_STREAM that is an HTTP/1.1-required error downgrades the negotiation to HTTP/1.1, closes the stream, and sets up a retry URL (duplicating the current URL when none was produced; failure to allocate becomes CURLE_OUT_OF_MEMORY). On any remaining error: connections of non-dual-channel schemes are closed (except CURLE_HTTP2_STREAM), posttransfer runs, and multi_done executes with premature TRUE. When the request finished and writes are not paused: posttransfer runs; with a redirect URL or retry pending, multi_done runs (CURLE_OK, not premature) and multi_follow sets up the next request — success moves to MSTATE_SETUP with CURLM_CALL_MULTI_PERFORM. Otherwise any Location header is consumed as FOLLOW_FAKE; failure there sets the stream error flag and runs multi_done prematurely, while success — or the plain completion path — moves to MSTATE_DONE with CURLM_CALL_MULTI_PERFORM. When neither error nor done, mspeed_check runs again. The scratch URL is freed and the result and mresult are reported through the out-params.

**Uncertainties.**

- Curl_retry_request's decision logic is in transfer/retry code

<a id="u-9409b6895d35"></a>
### `multistate_ratelimiting`

`static CURLMcode multistate_ratelimiting(struct Curl_easy *data, CURLcode *resultp)` · [lib/multi.c:L2291-L2314][f1]

Handles the RATELIMITING state: rechecks progress via Curl_pgrsCheck.

On error, non-dual-channel connections are closed (except CURLE_HTTP2_STREAM), posttransfer runs, and multi_done executes with premature TRUE. On success, mspeed_check decides: when limits still bind it keeps waiting (CURLM_OK), otherwise CURLM_CALL_MULTI_PERFORM resumes transfer. The result propagates through *resultp.

<a id="u-66d57c2eed59"></a>
### `multistate_done`

`static CURLMcode multistate_done(struct Curl_easy *data, CURLcode *presult)` · [lib/multi.c:L2690-L2717][f1]

Handles the DONE state.

With a connection still attached, multi_done runs (not premature) and its result becomes the reported result only if no earlier error exists. Wildcard FTP transfers not yet in CURLWC_DONE restart at MSTATE_INIT with CURLM_CALL_MULTI_PERFORM. Otherwise the state becomes COMPLETED regardless of multi_done's outcome, returning CURLM_CALL_MULTI_PERFORM.

<a id="u-030e62c58d11"></a>
### `is_finished`

`static CURLcode is_finished(struct Curl_multi *multi, struct Curl_easy *data, const s…` · [lib/multi.c:L2362-L2419][f1]

Post-state-machine error and progress finalizer; returns the possibly updated result.

While the transfer is not yet COMPLETED: with an error it reschedules pending transfers, and when a connection exists with a stream error it detaches and closes the connection (dead_connection true for timeouts); without a connection but in MSTATE_CONNECT (Curl_connect failure) it runs posttransfer and a no-meter progress update; then the state becomes COMPLETED and the error returns. Without error, a connected first socket gets a Curl_pgrsUpdateX progress callback; if that aborts, the stream is closed and the state moves to DONE (if not already past it) with the abort result returned.

<a id="u-c920ed420ea0"></a>
### `handle_completed`

`static void handle_completed(struct Curl_multi *multi, struct Curl_easy *data, CURLco…` · [lib/multi.c:L2421-L2467][f1]

Finalizes a transfer that reached COMPLETED.

Sub-transfers (master_mid != UINT32_MAX) are not reported to the application; instead their sub_xfer_done callback runs with the master handle if it still exists, otherwise only a trace is logged. Regular transfers get their CURLMsg filled: CURLMSG_DONE, the easy handle, and the result code. The state becomes MSGSENT, the mid is removed from process, dirty, and pending, and msg_to_app transfers are queued for curl_multi_info_read via multi_addmsg. really_alive and alive counters are decremented, with wakeup reassessment when either count reaches zero.

**Uncertainties.**

- Whether sub_xfer_done can be NULL when master_mid is set is not guarded here

<a id="u-700c750b6c73"></a>
### `mspeed_check`

`static CURLcode mspeed_check(struct Curl_easy *data)` · [lib/multi.c:L1972-L2014][f1]

Applies send/receive rate limits and drives the RATELIMITING state.

When either rlimit is active: it computes required wait times; if either is positive it moves the handle to MSTATE_RATELIMITING (unless already there), sets an EXPIRE_TOOFAST timer for the longer wait, clears the dirty bit, and returns CURLE_AGAIN. When no wait is needed it still sets EXPIRE_TOOFAST at the sooner next token-refill time (or the later one when that computes to 0) so a limited transfer cannot stall. On entry with limits inactive, or once waits expire, it moves the handle back to MSTATE_PERFORMING and returns CURLE_OK.

**Uncertainties.**

- Semantics of the rlimit wait/next-step helpers live in progress code

<a id="u-6469f79b2a8a"></a>
### `multi_follow`

`static CURLcode multi_follow(struct Curl_easy *data, const struct Curl_scheme *handle…` · [lib/multi.c:L1956-L1970][f1]

Handles redirect/retry follow-ups.

When the scheme provides a follow callback it delegates the new URL and follow type there. Without a scheme callback, FOLLOW_RETRY succeeds generically (retries need no protocol-specific handling); any other type without a callback fails with CURLE_TOO_MANY_REDIRECTS. The given newurl string is never freed here.

<a id="u-d7529c2385d2"></a>
### `multi_posttransfer`

`static void multi_posttransfer(struct Curl_easy *data)` · [lib/multi.c:L1939-L1948][f1]

Runs immediately after a transfer ends.

Only on platforms with signals, SIGPIPE, and no MSG_NOSIGNAL does it restore the previously saved SIGPIPE handler unless data->set.no_signal is set; on other platforms it does nothing.

<a id="u-51dc424ec91d"></a>
### `multi_done`

`static CURLcode multi_done(struct Curl_easy *data, CURLcode status, /* an error if th…` · [lib/multi.c:L673-L756][f1]

Finalizes a finished or aborted transfer; idempotent via data->state.done, returning CURLE_OK on the second call.

It shuts down async resolution, frees redirect strings, and forces premature=TRUE for CURLE_ABORTED_BY_CALLBACK, CURLE_READ_ERROR, and CURLE_WRITE_ERROR. The protocol's done callback runs only when a connection exists, its scheme defines done, and the state reached PROTOCONNECT; otherwise result stays the incoming status. Curl_pgrsDone runs when the transfer got past CONNECTING and the result is not an abort-by-callback, with its failure reported as CURLE_ABORTED_BY_CALLBACK. Transfer writes are finished via Curl_xfer_write_done (fatal errors take precedence), then Curl_req_done. With a connection, connection filters are told the transfer is done, the connection detached, DNS pruned, and the connection returned to the pool through multi_done_locked; afterwards pending transfers on that multi are scheduled. Netrc cache is flushed and the first error propagates.

calls: [function::multi_done_locked][f1], [function::multi_schedule_pending][f1]

**Uncertainties.**

- Behavior of Curl_req_done and Curl_conn_ev_data_done is external

<a id="u-de5d5c4b283d"></a>
### `multi_handle_timeout`

`static bool multi_handle_timeout(struct Curl_easy *data, const struct curltime *pnow,…` · [lib/multi.c:L1813-L1861][f1]

Checks and handles a per-transfer timeout.

With remaining time below zero: the base timer for the message is TIMER_STARTSINGLE while still connecting, else TIMER_STARTOP. In MSTATE_CONNECTING it reports whether resolving or connecting timed out with elapsed ms and calls Curl_conn_report_failed to keep partial connect knowledge; otherwise it reports elapsed time with bytes received (and total when known). It sets *result to CURLE_OPERATION_TIMEDOUT; when a connection exists and the state is past DO, the stream is closed and *stream_error set, and multi_done runs with premature TRUE. Returns TRUE only when a timeout fired, letting callers skip the state machine.

<a id="u-e7a4f1331000"></a>
### `multi_schedule_pending`

`static void multi_schedule_pending(struct Curl_multi *multi)` · [lib/multi.c:L3876-L3910][f1]

Moves one pending transfer back to CONNECT, resuming it round-robin: it starts after last_pending_mid and promotes the first pending transfer found, remembering that mid so repeated calls advance through the queue; when the scan passes the end it wraps to the beginning.

This deliberately promotes one transfer per call since limits like max host connections may only allow one, while pipewait changes could allow many. Unknown pending transfers (not in the xfers table) are asserted and removed.

<a id="u-2fa5203d4230"></a>
### `multi_adjust_pollset`

`static CURLcode multi_adjust_pollset(struct Curl_easy *data, struct easy_pollset *ps)` · [lib/multi.c:L960-L1002][f1]

Adjusts a prepared pollset for rate limits and pauses.

When either download or upload rlimit has no budget, it walks both primary and secondary sockets removing POLLIN entries on recv-block and POLLOUT entries on send-block, stopping on error. Independently, when receive is not blocked but the pollset wants receive and the connection filters still hold buffered data on either socket, the transfer is marked dirty so it re-runs instead of waiting for socket activity. Returns the first pollset error or CURLE_OK.

**Uncertainties.**

- Assumes data->conn is valid whenever ps->n is nonzero; a NULL conn here would crash

<a id="u-acef74bb393a"></a>
### `Curl_multi_pollset`

`CURLMcode Curl_multi_pollset(struct Curl_easy *data, struct easy_pollset *ps)` · [lib/multi.c:L1125-L1238][f1]

Builds the socket poll actions for one transfer based on its multi state.

Resets the pollset; under ENABLE_INTERNAL_WAKEUP the admin handle listens on the internal wakeup socket while any transfers are really alive. Without a connection it returns an empty set (legal during removal-driven assessment). State dispatch: INIT/PENDING/SETUP/CONNECT poll nothing; CONNECTING, PROTOCONNECT(ING), DO/DOING, DOING_MORE, and DID/PERFORMING delegate to the matching per-state builder; RATELIMITING lets time pass; DONE/COMPLETED/MSGSENT poll nothing; an unknown state fails and asserts. Any CURLE_OUT_OF_MEMORY maps to CURLM_OUT_OF_MEMORY; other errors are logged and mapped to CURLM_INTERNAL_ERROR. In verbose builds it traces the resulting pollset and timer count.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/multi.c
