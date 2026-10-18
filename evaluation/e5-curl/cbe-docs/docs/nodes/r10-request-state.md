# Request State and Predicates

**Capability.** Owns SingleRequest lifecycle and poll decisions: init/reset/free, start-of-request stamping, want_send/want_recv predicates gated by rate limits and buffer state, and halting both directions. Includes the token-bucket rate-limit state that gates these predicates.

Use this child to understand when a request is writable/readable and how state is reset between requests. The Curl_rlimit struct in ratelimit.h is the shared throttling state consulted by the predicates.

**Depends on.**

- [Transfer Direction API](r10-xfer-direction-api.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Transfer Loop and Lifecycle](r10-transfer-loop.md) · graph-confirmed · 4 edge(s) · The transfer loop consults request-state predicates (abort/stop send-recv) while driving each direction.

Parent: [Request and Transfer Engine](r10-transfer-engine.md)

## Units (13)

<a id="u-fd530a06dd0e"></a>
### `Curl_rlimit`

`struct Curl_rlimit` · [lib/ratelimit.h:L57-L67][f1]

Defines struct Curl_rlimit, a token-bucket rate limiter state: per-second and per-step rate and burst values, step_us spacing between token increases, the current token count, spare microseconds within a step, the last-update timestamp, and a blocked BIT flag.

The header comment documents semantics: burst caps token accumulation during idle, blocking forces zero availability until unblocked with no history, and rate 0 means effectively unlimited (INT64_MAX) unless blocked.

<a id="u-275aef1ce683"></a>
### `Curl_req_init`

`void Curl_req_init(struct SingleRequest *req)` · [lib/request.c:L37-L40][f2]

Zero-initializes a SingleRequest so it is safe for first use, via a full memset of the struct.

<a id="u-08c8fe509555"></a>
### `Curl_req_soft_reset`

`CURLcode Curl_req_soft_reset(struct SingleRequest *req, struct Curl_easy *data)` · [lib/request.c:L42-L91][f2]

Prepares a SingleRequest for a follow-up request while keeping the start time: clears per-request flags, counters, and version fields, frees the auth/proxy-auth header strings, and reinitializes the send buffer.

It first calls Curl_client_start; on error that result is returned immediately and nothing else is reset. The sendbuf is initialized once with upload_buffer_size and BUFQ_OPT_SOFT_LIMIT; on later calls it is only reset, unless the configured upload_buffer_size no longer matches the buffer's chunk_size, in which case the bufq is freed and reallocated with the new size. Proxy-auth freeing is compiled out when proxies are disabled.

calls: [Curl_client_start](r4-client-data-transfer.md#u-7a95ae4098b5), [bufq-c-init-free](r15-bufq-chunk-engine.md#u-1d395f59b0bc)

**Uncertainties.**

- Whether Curl_bufq_init2 can fail is not visible; its return value is ignored here.

<a id="u-9bceacfe3d05"></a>
### `Curl_req_hard_reset`

`void Curl_req_hard_reset(struct SingleRequest *req, struct Curl_easy *data)` · [lib/request.c:L112-L172][f2]

Resets a SingleRequest to a virgin state for reuse of the easy handle or a new connection, without memset since some state must survive.

It frees newurl, auth and proxy-auth headers, and the cookie host; resets the client state via Curl_client_reset; resets the sendbuf if initialized; destroys all cached resolve data; then clears counters, offsets, HTTP code/version, upgrade state, and all per-request flags (download_done, eos flags, chunked/trailer/auth flags, etc.), setting size and maxdownload to -1 and no_body from the transfer setting opt_no_body. Finally it unpauses both download and upload rate limiters via Curl_rlimit_block with a zero timestamp.

calls: [Curl_client_reset](r4-client-data-transfer.md#u-b5e0cc40324d), [bufq-c-init-free](r15-bufq-chunk-engine.md#u-1d395f59b0bc), [Curl_resolv_destroy_all](r5-dns-resolver.md#u-cffc06ce0248), [Curl_rlimit_block](r4-transfer-rate-limiting.md#u-a9fc3f1924c6)

**Uncertainties.**

- Fields not listed in this function (e.g. writer/reader stacks, sendbuf contents beyond reset) are intentionally preserved; the exact set of survivors is only what the code shows.

<a id="u-8b742283a321"></a>
### `Curl_req_start`

`CURLcode Curl_req_start(struct SingleRequest *req, struct Curl_easy *data)` · [lib/request.c:L93-L98][f2]

Marks the start of a request: stamps the current time into req->start via Curl_pgrs_now, then performs a soft reset and returns its result.

calls: [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77), [Curl_req_soft_reset](r10-request-state.md#u-08c8fe509555)

<a id="u-66821c2b10a9"></a>
### `Curl_req_done`

`CURLcode Curl_req_done(struct SingleRequest *req, struct Curl_easy *data, bool aborted)` · [lib/request.c:L102-L110][f2]

Finalizes a request: unless the request was aborted, it flushes buffered request data with req_flush (whose result is deliberately ignored); it always resets the client writer/reader state via Curl_client_reset and returns CURLE_OK.

The req parameter is unused.

calls: [req_flush](r10-request-send-path.md#u-aed65aeb48ff), [Curl_client_reset](r4-client-data-transfer.md#u-b5e0cc40324d)

**Uncertainties.**

- A flush error during non-aborted done is swallowed, so data loss at completion is not reported by this function.

<a id="u-88301b9ba7a8"></a>
### `Curl_req_free`

`void Curl_req_free(struct SingleRequest *req, struct Curl_easy *data)` · [lib/request.c:L174-L184][f2]

Releases all request-owned resources: frees newurl and the auth/proxy-auth header strings, frees the send buffer queue if it was initialized, and cleans up the client reader/writer stacks via Curl_client_cleanup.

calls: [bufq-c-init-free](r15-bufq-chunk-engine.md#u-1d395f59b0bc), [Curl_client_cleanup](r4-client-data-transfer.md#u-e08e0fd6aa55)

<a id="u-5174c23c5b32"></a>
### `Curl_req_want_send`

`bool Curl_req_want_send(struct Curl_easy *data)` · [lib/request.c:L432-L443][f2]

Poll-interest predicate: TRUE when the request is not done, the upload rate limiter is not blocking, and at least one of the SEND io flag is set, the send buffer is non-empty, or the transfer layer has pending flush bytes.

calls: [Curl_rlimit_is_blocked](r4-transfer-rate-limiting.md#u-b41b360b4e06), [Curl_xfer_needs_flush](r10-xfer-direction-api.md#u-8516d6ffa51d), [Curl_req_sendbuf_empty](r10-request-state.md#u-4eb7e350bb9f)

<a id="u-3d587494ebf9"></a>
### `Curl_req_want_recv`

`bool Curl_req_want_recv(struct Curl_easy *data)` · [lib/request.c:L445-L451][f2]

Poll-interest predicate for the download direction: TRUE when the request is not done, the download rate limiter is not blocking, and the RECV io flag is set.

calls: [Curl_rlimit_is_blocked](r4-transfer-rate-limiting.md#u-b41b360b4e06)

<a id="u-3383a1f6d70c"></a>
### `Curl_req_done_sending`

`bool Curl_req_done_sending(struct Curl_easy *data)` · [lib/request.c:L453-L456][f2]

TRUE when upload_done is set and the request no longer wants to send, i.e. all request data has been handed to the transfer layer and nothing more is pending or flagged.

calls: [Curl_req_want_send](r10-request-state.md#u-5174c23c5b32)

<a id="u-4eb7e350bb9f"></a>
### `Curl_req_sendbuf_empty`

`bool Curl_req_sendbuf_empty(struct Curl_easy *data)` · [lib/request.c:L427-L430][f2]

Reports whether nothing is buffered for sending: TRUE if the sendbuf was never initialized or the bufq is empty.

calls: [Curl_bufq_is_empty](r15-bufq-stream-api.md#u-972cf7343ce0)

<a id="u-29d60501598b"></a>
### `Curl_req_stop_send_recv`

`CURLcode Curl_req_stop_send_recv(struct Curl_easy *data)` · [lib/request.c:L492-L502][f2]

Halts both directions: aborts sending (which is a no-op if already done) when the SEND io flag is set, then clears all io flags.

Receive-pause bits on client writes are preserved since only io_flags are touched. Returns the abort result or CURLE_OK.

calls: [Curl_req_abort_sending](r10-request-state.md#u-6fb0cfe9b372)

<a id="u-6fb0cfe9b372"></a>
### `Curl_req_abort_sending`

`CURLcode Curl_req_abort_sending(struct Curl_easy *data)` · [lib/request.c:L481-L490][f2]

Stops sending request data: if the upload is not already done it discards the send buffer contents, sets upload_aborted, clears the SEND io flag, and finalizes the send phase via req_set_upload_done (which marks upload_done and closes the send direction).

Already-done uploads are a no-op returning CURLE_OK.

calls: [req_set_upload_done](r10-request-send-path.md#u-29ece764858f), [bufq-c-init-free](r15-bufq-chunk-engine.md#u-1d395f59b0bc)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/ratelimit.h
[f2]: ../../../../../../eval/curl-2c04412/lib/request.c
