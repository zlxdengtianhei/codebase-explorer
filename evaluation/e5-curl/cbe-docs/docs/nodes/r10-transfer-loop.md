# Transfer Loop and Lifecycle

**Capability.** Owns per-transfer preparation (pretransfer, CONNECT reinit, header checks, time conditions, retry) and the low-level per-socket-event step that drives download then upload work with timeouts and completeness checks.

Use this child to follow a transfer's outer loop: how a handle is prepared before each perform pass, how download/upload halves iterate, and how retries and shutdown-start detection work.

**Depends on.**

- [HSTS Cache](r10-hsts-cache.md) · graph-confirmed · 2 edge(s)
- [Request Send Path](r10-request-send-path.md) · graph-confirmed · 1 edge(s)
- [Request State and Predicates](r10-request-state.md) · graph-confirmed · 4 edge(s) · The transfer loop consults request-state predicates (abort/stop send-recv) while driving each direction.
- [Transfer Direction API](r10-xfer-direction-api.md) · graph-confirmed · 3 edge(s) · The per-socket-event transfer loop sends and receives bytes through the connection-facing xfer direction API.

Parent: [Request and Transfer Engine](r10-transfer-engine.md)

## Units (12)

<a id="u-0a1763a1e3d6"></a>
### `Curl_pretransfer`

`CURLcode Curl_pretransfer(struct Curl_easy *data)` · [lib/transfer.c:L440-L595][f1]

Prepares a handle once per perform(), before any transfer including redirects and authentication passes.

It resets the retry count, then resolves the URL: with neither a URL string nor a CURLU handle it fails with CURLE_URL_MALFORMAT; with a CURLU handle its URL part overrides CURLOPT_URL, failing with the same code (after clearing the stale url bufref) when extraction fails. It validates that POSTFIELDS is not combined with RESUME_FROM (CURLE_BAD_FUNCTION_ARGUMENT). It then copies set-state into transfer state (ascii preference, list_only under the list-only protocol, http method), clears previous origin peers and follow/auth/error flags, reinitializes HTTP negotiation, and resets info strings and priority state; referer handling honors http_auto_referer by freeing the old value and re-seeding from the configured referer when present. infilesize follows the method: PUT uses filesize, other non-GET/HEAD methods use postfieldsize (deriving the length from a NUL-terminated postfields when set to -1), GET/HEAD get zero. It loads cookie files (with the session flag honored) and runs the cookie engine, loads resolve host pairs, loads HSTS files, enables port overriding, and — unless signals are suppressed on platforms without MSG_NOSIGNAL — installs SIGPIPE ignore while saving the previous handler. It resets session info, restarts progress accounting, narrows picked auth methods to the wanted sets, and under FTP-enabled builds initializes wildcard matching when enabled (DEBUGBUILD may force it via CURL_DBG_FTP_WILDCARD), returning CURLE_OUT_OF_MEMORY if wildcard allocation fails. It then loads HSTS via callback. Regardless of earlier results it clears headerbytecount and cleans stored headers before returning the accumulated result.

**Notes.**

- failure: Any failing load step (cookies, resolve, HSTS files, wildcard allocation) short-circuits the remaining setup steps but headers cleanup still runs.

calls: [Curl_cookie_loadfiles](r12-cookie-jar-core.md#u-1e8d227a05b1), [Curl_cookie_run](r12-cookie-jar-core.md#u-b6b48f4206b9), [Curl_loadhostpairs](r11-dnscache.md#u-34dd448da4b1), [Curl_hsts_loadfiles](r10-hsts-cache.md#u-f807f9357170), [Curl_hsts_loadcb](r10-hsts-cache.md#u-d415407fc208), [Curl_initinfo](r5-easy-handle-api.md#u-52b50ca2d001), [progress-c-state-reset-and-counters](r9-progress-timing-and-policy.md#u-f8d97fbe4396), [Curl_pgrsStart](r9-progress-timing-and-policy.md#u-3243c486ba28), [Curl_headers_cleanup](r8-http-headers-api.md#u-32b5758c22f9), [Curl_http_neg_init](r6-http-request-build.md#u-1369787fcf66), [Curl_bufref_set](r14-bufref-buffers.md#u-214d3ce6e368), [Curl_bufref_free](r14-bufref-buffers.md#u-2c7e087ba1d6), [Curl_peer_unlink](r3-peer-identity.md#u-63430ed0e6c2), [ftplistparser-lifecycle](r6-ftp-list-parsing.md#u-2008b8f1a40a), [curl_url_get](r6-url-encoding-and-getters.md#u-770bb73cd6cf), [Curl_failf](r1-trace-logging.md#u-c8338023c157), [Curl_u8_strset_get](r11-u8-strset.md#u-48fba58a4b37), [Curl_u8_strset_setn](r11-u8-strset.md#u-8d6be39089c0)

**Uncertainties.**

- Behavior of Curl_data_priority_clear_state and CURL_EASY_STR accessors is defined elsewhere.

<a id="u-5c4dad1d7b43"></a>
### `Curl_init_CONNECT`

`void Curl_init_CONNECT(struct Curl_easy *data)` · [lib/transfer.c:L428-L433][f1]

Reinitializes per-connection I/O state each time the handle enters the CONNECT phase, i.e. also on each redirect.

It restores the read callback and its userdata from the user settings and sets the upload flag true only when the current HTTP method is PUT.

<a id="u-75bb75f01340"></a>
### `Curl_checkheaders`

`char *Curl_checkheaders(const struct Curl_easy *data, const char *thisheader, const s…` · [lib/transfer.c:L84-L99][f1]

Scans the transfer's custom header list for a header starting with the given prefix (prefix given without colon) and returns the first matching header's data, or NULL if none match.

Asserts the length is nonzero and the prefix does not end with a colon. A list entry matches when its first thislen bytes compare case-insensitively and the following character is a header separator, preventing prefix-only matches like 'Accept' matching 'Accept-Encoding'. Compiled only when HTTP, SMTP, or IMAP is enabled.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

**Uncertainties.**

- Exact behavior of Curl_headersep for separators other than colon is defined in its own implementation.

<a id="u-11738a2110b5"></a>
### `Curl_meets_timecondition`

`bool Curl_meets_timecondition(struct Curl_easy *data, time_t timeofdoc)` · [lib/transfer.c:L120-L144][f1]

Evaluates the CURLOPT_TIMECONDITION against a document's modification time and signals whether the transfer should proceed.

Returns TRUE immediately when either the document time or the configured timevalue is zero. For IFMODSINCE (the default case), a document not newer than the threshold logs 'not new enough', sets data->info.timecond to TRUE, and returns FALSE so the body is skipped. For IFUNMODSINCE, a document not older than the threshold logs 'not old enough', sets timecond, and returns FALSE. Otherwise the condition is met and TRUE is returned; timecond stays FALSE.

calls: [lib/curl_trc.c:Curl_infof](r1-trace-logging.md#u-b6145e5eb5c9)

<a id="u-53ef6323f3d9"></a>
### `Curl_retry_request`

`CURLcode Curl_retry_request(struct Curl_easy *data, char **url)` · [lib/transfer.c:L600-L662][f1]

Decides whether a request should be retried on a fresh connection and, if so, prepares the retry.

For uploads over non-HTTP/RTSP protocols it never retries. Retry is signaled when a reused connection yielded zero received bytes while the body was still expected (for HTTP always, for other protocols only when a body was expected, and never for RTSPREQ_RECEIVE), or when a refused-stream error occurred with zero data received (cleared after logging). Each retry increments the retry counter; exceeding CONN_MAX_RETRIES (5) logs failure, resets the counter, and returns CURLE_SEND_ERROR. On retry it returns the request URL as a malloc'd copy (failure yields CURLE_OUT_OF_MEMORY), closes the current connection, marks it as a retry connection, and asks the client reader to rewind so the body can be resent. Returns CURLE_OK both when retrying and when no retry is needed; *url is NULL when no retry.

calls: [bufref-c-accessors](r14-bufref-buffers.md#u-ac8cad6d65f5), [Curl_conncontrol](r6-connection-management.md#u-c9e8d244e35b), [lib/curl_trc.c:Curl_infof](r1-trace-logging.md#u-b6145e5eb5c9), [Curl_failf](r1-trace-logging.md#u-c8338023c157), [sendf.c-rewind-flag](r4-client-reader-stack.md#u-49ea9d6c696c)

**Uncertainties.**

- Exact effect of conn->bits.retry on other protocol paths is determined by consumers elsewhere.

<a id="u-0dbb8ff46874"></a>
### `Curl_sendrecv`

`CURLcode Curl_sendrecv(struct Curl_easy *data)` · [lib/transfer.c:L354-L424][f1]

Low-level per-socket-event transfer step: performs available download work, then upload work, then enforces timeouts and completeness checks.

If the transfer is paused in both directions it returns OK immediately. Download runs only while the request wants receive; upload only while it wants send; either error or request completion aborts. It then reads the progress clock: if I/O is still wanted and the time budget is exhausted, it fails with CURLE_OPERATION_TIMEDOUT, with a message including the expected size when known. If no I/O is wanted, it validates the transfer: unless the response has no body, the size is unknown, or a redirect target exists, a byte count below the expected size fails with CURLE_PARTIAL_FILE. When nothing more is wanted, the request is marked done. Finally runs the progress check and returns its result; errors are traced in debug builds.

calls: [sendrecv_dl](r10-transfer-loop.md#u-41c42021e748), [sendrecv_ul](r10-transfer-loop.md#u-d1c009a48dd7), [Curl_xfer_is_blocked](r10-xfer-direction-api.md#u-1daf7f07ba51), [Curl_timeleft_now_ms](r6-connection-management.md#u-5ce65257b36d), [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77), [Curl_pgrsCheckX](r9-progress-timing-and-policy.md#u-187f13cf6312), [Curl_req_want_send](r10-request-state.md#u-5174c23c5b32), [lib/curl_trc.c:Curl_infof](r1-trace-logging.md#u-b6145e5eb5c9)

**Uncertainties.**

- Interplay of CURL_REQ_WANT_IO with the req state machine is defined in request code.

<a id="u-41c42021e748"></a>
### `sendrecv_dl`

`static CURLcode sendrecv_dl(struct Curl_easy *data, struct SingleRequest *k)` · [lib/transfer.c:L220-L335][f1]

Drives the download half of a transfer: repeatedly receives response data and writes it to the client until EOS, EAGAIN, or the loop budget (10 iterations) is spent.

It borrows a transfer buffer from the multi handle and releases it on exit. Per iteration: it re-checks whether the connection is multiplexed (which relaxes EOF/size restrictions, multiplex state changes only toward true); applies the download rate limit by breaking out with rate_limited when no budget remains or shrinking the read when less than requested; calls xfer_recv_resp, converting CURLE_AGAIN into rcvd_eagain, and — only when the download is done with no body and no trailer announced — continues as if EOS arrived instead of leaving the loop; a non-AGAIN error aborts. A zero-length read is EOS: it stops send/receive on the request, and breaks early if EOS was already written to the client. Received bytes go through Curl_xfer_write_resp, aborting on error or when the request completes. Unless multiplexed, receiving stops when download_done or EOS, and the loop exits when receiving is no longer wanted. After the loop: if data may still arrive (no EOS, not rate limited, receive wanted, and either no EAGAIN or data_pending says buffers hold data), it marks the handle dirty for another read round; if reading is complete but sending continues on a close-or-multiplex connection, it aborts sending so the server can close. Returns the first error encountered, CURLE_OK otherwise.

calls: [xfer_recv_resp](r10-transfer-loop.md#u-a8bcc4938578), [Curl_xfer_write_resp](r10-xfer-direction-api.md#u-71b758b2bb91), [data_pending](r10-transfer-loop.md#u-f3c34a6bd051), [multi-c-easy-lookup](r13-multi-lifecycle.md#u-ca4794ea3aa5), [multi-c-xfer-bufs](r13-multi-lifecycle.md#u-7ec452e6150f), [Curl_rlimit_active](r4-transfer-rate-limiting.md#u-2b75c0e6d389), [Curl_rlimit_avail](r4-transfer-rate-limiting.md#u-c1d44aedac60), [Curl_req_abort_sending](r10-request-state.md#u-6fb0cfe9b372), [Curl_req_stop_send_recv](r10-request-state.md#u-29d60501598b), [lib-cfilters-c-chain-state-queries](r8-cfilters-events-state.md#u-b752791790cf), [lib/curl_trc.c:Curl_infof](r1-trace-logging.md#u-b6145e5eb5c9), [Curl_trc_multi](r1-trace-logging.md#u-385de27aa970)

**Uncertainties.**

- The exact semantics of CURL_REQ_* request-state macros and k->eos_written transitions are defined elsewhere.
- Behavior of the disabled DEBUGF rate-limit trace (#if 0) is not active code.

<a id="u-d1c009a48dd7"></a>
### `sendrecv_ul`

`static CURLcode sendrecv_ul(struct Curl_easy *data)` · [lib/transfer.c:L340-L348][f1]

Upload half of the socket loop.

Asserts sending is not already finished; when it is not done, it asks the request layer to send more data, whose result propagates; when already done sending, it returns CURLE_OK without action.

calls: [Curl_req_done_sending](r10-request-state.md#u-3383a1f6d70c), [Curl_req_send_more](r10-request-send-path.md#u-2d5cffaa5623)

<a id="u-f3c34a6bd051"></a>
### `data_pending`

`static int data_pending(struct Curl_easy *data, bool rcvd_eagain)` · [lib/transfer.c:L102-L114][f1]

Reports whether unread data may still be pending so the download loop should retry instead of treating EAGAIN as final.

For FTP-family connections it checks the secondary (data) socket. Otherwise, for SCP/SFTP it returns true whenever the last receive did not end in EAGAIN, because libssh2 may hold buffered data, or falls back to checking the primary socket's pending state.

calls: [lib-cfilters-c-pending-flush](r8-cfilters-io.md#u-0cbca31d987f)

<a id="u-a8bcc4938578"></a>
### `xfer_recv_resp`

`static CURLcode xfer_recv_resp(struct Curl_easy *data, char *buf, size_t blen, bool e…` · [lib/transfer.c:L175-L213][f1]

Receives one chunk of raw response body into buf for the download path.

It first clamps the read size: without reliable EOS and for a body-sized (non-header) transfer with known req.size, it limits the read to the remaining size; if receive-side shutdown has already started it reads nothing. It then receives via Curl_xfer_recv when space remains. When zero bytes were read and the request asked for shutdown, it performs one recv-side shutdown attempt; if shutdown is not finished it returns CURLE_AGAIN so the caller retries. On success with zero bytes it logs that the transfer is done. Errors from receive and shutdown propagate to the caller; *pnread is zeroed on entry.

calls: [Curl_xfer_recv](r10-xfer-direction-api.md#u-2fc91278fee5), [xfer_recv_shutdown](r10-transfer-loop.md#u-5a88d52af949), [warnless.c-narrowing-conversions](r12-socket-and-buffer-utils.md#u-97fe403e2706)

<a id="u-5a88d52af949"></a>
### `xfer_recv_shutdown`

`static CURLcode xfer_recv_shutdown(struct Curl_easy *data, bool *done)` · [lib/transfer.c:L146-L151][f1]

Runs one shutdown attempt on the connection's receive side.

Returns CURLE_FAILED_INIT when data or its connection is missing; otherwise delegates to the connection shutdown machinery for recv_idx, reporting progress via *done.

calls: [Curl_cshutdn_try_once_idx](r8-conn-shutdown.md#u-0770abbbde79)

<a id="u-39031ba3894f"></a>
### `xfer_recv_shutdown_started`

`static bool xfer_recv_shutdown_started(struct Curl_easy *data)` · [lib/transfer.c:L153-L158][f1]

Returns whether shutdown has already started on the receive side.

Yields FALSE when data or conn is absent; otherwise tests the connection's in-shutdown state for recv_idx.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/transfer.c
