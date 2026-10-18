# Transfer Direction API

**Capability.** Owns the connection-facing transfer API: direction setup (send/recv/nop/bidi), raw send/recv with EOS, flush and shutdown of each side, pause/blocked/secure queries, and delivery of response body/header bytes to the client writer.

Use this child as the reference for how request.c and the transfer loop talk to a connection's send/receive sides, and how received data reaches the client.

**Depended on by.**

- [Request Send Path](r10-request-send-path.md) · graph-confirmed · 6 edge(s)
- [Request State and Predicates](r10-request-state.md) · graph-confirmed · 1 edge(s)
- [Transfer Loop and Lifecycle](r10-transfer-loop.md) · graph-confirmed · 3 edge(s) · The per-socket-event transfer loop sends and receives bytes through the connection-facing xfer direction API.

Parent: [Request and Transfer Engine](r10-transfer-engine.md)

## Units (22)

<a id="u-ac233bfb6863"></a>
### `xfer_setup`

`static void xfer_setup( struct Curl_easy *data, /* transfer */ int8_t send_idx, /* so…` · [lib/transfer.c:L664-L707][f1]

Configures the transfer's send/receive directions before data flows.

It stores send_idx and recv_idx (both in [-1,1], asserted) on the connection, sets the request's expected body size (recv_size; -1 unknown), records whether the scheme's run callback writes response headers separately, and clears shutdown flags since shutdown is opt-in later. When headers are not separately written and a positive size is known, it reports the download size to the progress layer. If either headers or body is wanted (i.e. not no_body), it arms receive and/or send on the request for the non-negative indexes; a negative send index additionally asserts that the request does not want to send. Logs the chosen indexes via multi trace.

calls: [progress-c-state-reset-and-counters](r9-progress-timing-and-policy.md#u-f8d97fbe4396), [Curl_trc_multi](r1-trace-logging.md#u-385de27aa970)

**Uncertainties.**

- Scheme-provided run callbacks (write_resp_hd) are populated by protocol implementations elsewhere.

<a id="u-18a177e8d14f"></a>
### `Curl_xfer_setup_nop`

`void Curl_xfer_setup_nop(struct Curl_easy *data)` · [lib/transfer.c:L709-L712][f1]

Configures the transfer with neither send nor receive direction and unknown size, i.e. no data transfer is set up.

calls: [xfer_setup](r10-xfer-direction-api.md#u-ac233bfb6863)

<a id="u-13855c9f3fa4"></a>
### `Curl_xfer_setup_recv`

`void Curl_xfer_setup_recv(struct Curl_easy *data, int8_t sockindex, curl_off_t recv_s…` · [lib/transfer.c:L727-L732][f1]

Sets up a receive-only transfer on the given socket index with the given expected size (or -1 unknown).

calls: [xfer_setup](r10-xfer-direction-api.md#u-ac233bfb6863)

<a id="u-886095062fc5"></a>
### `Curl_xfer_setup_send`

`void Curl_xfer_setup_send(struct Curl_easy *data, int8_t sockindex)` · [lib/transfer.c:L721-L725][f1]

Sets up a send-only transfer on the given socket index, with no receive direction and unknown size.

calls: [xfer_setup](r10-xfer-direction-api.md#u-ac233bfb6863)

<a id="u-c56645f36b43"></a>
### `Curl_xfer_setup_sendrecv`

`void Curl_xfer_setup_sendrecv(struct Curl_easy *data, int8_t sockindex, curl_off_t re…` · [lib/transfer.c:L714-L719][f1]

Sets up bidirectional transfer on the given socket index with the given receive size (or -1 when unknown).

calls: [xfer_setup](r10-xfer-direction-api.md#u-ac233bfb6863)

<a id="u-859255dc1b0d"></a>
### `Curl_xfer_send`

`CURLcode Curl_xfer_send(struct Curl_easy *data, const void *buf, size_t blen, bool eo…` · [lib/transfer.c:L811-L832][f1]

Sends up to blen bytes from buf on the connection's send side, with an EOS flag marking end of stream.

CURLE_AGAIN is converted into success with *pnwritten set to 0, so callers treat it as would-block rather than error. On successful nonzero writes the byte count is added to data->info.request_size. The write is traced in debug builds and the result code propagates.

calls: [lib-cfilters-c-conn-io-entry](r8-cfilters-io.md#u-688833f4c38c), [lib/curl_trc.c:Curl_infof](r1-trace-logging.md#u-b6145e5eb5c9)

<a id="u-18b96fe52910"></a>
### `Curl_xfer_send_close`

`CURLcode Curl_xfer_send_close(struct Curl_easy *data)` · [lib/transfer.c:L847-L851][f1]

Signals the connection that the sending direction of the transfer is complete, then returns CURLE_OK unconditionally.

calls: [lib-cfilters-c-cntrl-events](r8-cfilters-events-state.md#u-cfc5bee94659)

<a id="u-493d54edc07a"></a>
### `Curl_xfer_send_is_paused`

`bool Curl_xfer_send_is_paused(struct Curl_easy *data)` · [lib/transfer.c:L865-L868][f1]

Reports whether the upload direction is paused by the upload rate limiter.

calls: [Curl_rlimit_is_blocked](r4-transfer-rate-limiting.md#u-b41b360b4e06)

<a id="u-3de3370b40ff"></a>
### `Curl_xfer_send_shutdown`

`CURLcode Curl_xfer_send_shutdown(struct Curl_easy *data, bool *done)` · [lib/transfer.c:L160-L165][f1]

Runs one shutdown attempt on the connection's send side, mirroring the recv variant.

Returns CURLE_FAILED_INIT when data or conn is missing, otherwise delegates to shutdown for send_idx with *done reporting completion.

calls: [Curl_cshutdn_try_once_idx](r8-conn-shutdown.md#u-0770abbbde79)

<a id="u-2fc91278fee5"></a>
### `Curl_xfer_recv`

`CURLcode Curl_xfer_recv(struct Curl_easy *data, char *buf, size_t blen, size_t *pnrcvd)` · [lib/transfer.c:L834-L845][f1]

Receives from the connection's receive side into buf.

The requested length is clamped down to the configured set.buffer_size when smaller, then delegated to the connection receive, which may return CURLE_AGAIN or a count via *pnrcvd. Asserts buffer_size is positive.

calls: [lib-cfilters-c-conn-io-entry](r8-cfilters-io.md#u-688833f4c38c), [warnless.c-narrowing-conversions](r12-socket-and-buffer-utils.md#u-97fe403e2706)

<a id="u-5121a827239b"></a>
### `Curl_xfer_recv_is_paused`

`bool Curl_xfer_recv_is_paused(struct Curl_easy *data)` · [lib/transfer.c:L870-L873][f1]

Reports whether the download direction is paused by the download rate limiter.

calls: [Curl_rlimit_is_blocked](r4-transfer-rate-limiting.md#u-b41b360b4e06)

<a id="u-93869fc8f58e"></a>
### `Curl_xfer_flush`

`CURLcode Curl_xfer_flush(struct Curl_easy *data)` · [lib/transfer.c:L806-L809][f1]

Flushes buffered data on the connection's send side, returning the flush result.

calls: [lib-cfilters-c-cntrl-events](r8-cfilters-events-state.md#u-cfc5bee94659)

<a id="u-8516d6ffa51d"></a>
### `Curl_xfer_needs_flush`

`bool Curl_xfer_needs_flush(struct Curl_easy *data)` · [lib/transfer.c:L801-L804][f1]

Reports whether the connection's send side has buffered data still needing a flush.

calls: [lib-cfilters-c-pending-flush](r8-cfilters-io.md#u-0cbca31d987f)

<a id="u-1daf7f07ba51"></a>
### `Curl_xfer_is_blocked`

`bool Curl_xfer_is_blocked(struct Curl_easy *data)` · [lib/transfer.c:L853-L863][f1]

Determines whether the transfer can make no progress because both wanted directions are paused.

When only receive is wanted, blocked means the download rate limit holds; when only send is wanted, the upload rate limit; when both are wanted, the transfer is blocked only if both limits hold simultaneously; when neither is wanted it is not blocked.

calls: [Curl_xfer_recv_is_paused](r10-xfer-direction-api.md#u-5121a827239b), [Curl_xfer_send_is_paused](r10-xfer-direction-api.md#u-493d54edc07a)

<a id="u-3e3676e58d1b"></a>
### `Curl_xfer_is_secure`

`bool Curl_xfer_is_secure(struct Curl_easy *data)` · [lib/transfer.c:L896-L908][f1]

Reports whether the transfer's origin connection is SSL/TLS secured.

When proxy support is enabled and the connection talks to a forward proxy it returns FALSE, since a forward proxy is never used for secured URLs here, asserting the origin scheme is not SSL. Otherwise it returns whether the origin scheme carries the PROTOPT_SSL flag. Assumes data->state.origin is set.

**Uncertainties.**

- The DEBUGASSERT on non-SSL proxy origins is only active in debug builds; the release-path contract for proxy connections relies on that invariant.

<a id="u-5e0ac2ef4a8e"></a>
### `Curl_xfer_set_shutdown`

`void Curl_xfer_set_shutdown(struct Curl_easy *data, bool shutdown, bool ignore_errors)` · [lib/transfer.c:L734-L743][f1]

Records whether the connection should be shut down at transfer end and whether shutdown errors should be ignored.

Asserts shutdown is only requested when at most one direction is active. Sets the request's shutdown and shutdown_err_ignore flags.

<a id="u-267fe6c826d7"></a>
### `Curl_xfer_pause_recv`

`CURLcode Curl_xfer_pause_recv(struct Curl_easy *data, bool enable)` · [lib/transfer.c:L885-L894][f1]

Pauses or unpauses the download direction.

It toggles the download rate limiter with the current timestamp; when unpausing, a paused client writer chain is unpainted (result propagated); it signals the connection's data-pause event so the socket stops being read; and updates progress recv-pause state. Returns the writer-unpause result or CURLE_OK.

calls: [Curl_rlimit_block](r4-transfer-rate-limiting.md#u-a9fc3f1924c6), [Curl_cwriter_unpause](r4-client-writer-stack.md#u-68de7683c9b6), [lib-cfilters-c-cntrl-events](r8-cfilters-events-state.md#u-cfc5bee94659), [progress-c-state-reset-and-counters](r9-progress-timing-and-policy.md#u-f8d97fbe4396), [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77)

<a id="u-c086905230ef"></a>
### `Curl_xfer_pause_send`

`CURLcode Curl_xfer_pause_send(struct Curl_easy *data, bool enable)` · [lib/transfer.c:L875-L883][f1]

Pauses (enable=TRUE) or unpauses (enable=FALSE) the upload direction.

It blocks/unblocks the upload rate limiter stamped with the current time; when unpausing, if the client reader chain is itself paused it is unpainted via Curl_creader_unpause and its result propagates; finally progress is told the send pause state changed. Returns the reader-unpause result or CURLE_OK.

calls: [Curl_rlimit_block](r4-transfer-rate-limiting.md#u-a9fc3f1924c6), [sendf.c-creader-pause](r4-client-reader-stack.md#u-f4d59b982184), [progress-c-state-reset-and-counters](r9-progress-timing-and-policy.md#u-f8d97fbe4396), [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77)

<a id="u-71b758b2bb91"></a>
### `Curl_xfer_write_resp`

`CURLcode Curl_xfer_write_resp(struct Curl_easy *data, const char *buf, size_t blen, b…` · [lib/transfer.c:L745-L775][f1]

Delivers received response body (and optionally EOS) to the client.

When the connection's scheme provides a run-level write_resp callback, that callback takes full responsibility for writing all download data. Otherwise, if there are bytes or this is the EOS, the data is written as CLIENTWRITE_BODY (with CLIENTWRITE_EOS added for EOS) via the client-write chain. On success with EOS, the request is marked eos_written and download_done. The write result is traced and propagated to the caller.

calls: [Curl_client_write](r4-client-writer-stack.md#u-5e34efff1274), [curl-trc-c-simple-tracers](r1-trace-logging.md#u-added0315fa4)

<a id="u-9d503a001568"></a>
### `Curl_xfer_write_resp_hd`

`CURLcode Curl_xfer_write_resp_hd(struct Curl_easy *data, const char *hd0, size_t hdle…` · [lib/transfer.c:L782-L793][f1]

Delivers received response header bytes to the client.

If the scheme provides a run-level write_resp_hd callback, the buffer (asserted NUL-terminated at hdlen) is handed to it, taking full responsibility for header writing; otherwise the data falls through to Curl_xfer_write_resp and is treated like response body bytes with the given EOS flag. The resulting code is returned.

calls: [Curl_xfer_write_resp](r10-xfer-direction-api.md#u-71b758b2bb91)

<a id="u-69638806569b"></a>
### `Curl_xfer_write_done`

`CURLcode Curl_xfer_write_done(struct Curl_easy *data, bool premature)` · [lib/transfer.c:L795-L799][f1]

Finalizes client writing for the transfer, delegating to the output writer's done step; the premature flag is accepted but unused here.

calls: [Curl_cw_out_done](r2-cw-out-writer.md#u-9070681942cc)

<a id="u-900cb16d9cb6"></a>
### `Curl_xfer_write_is_paused`

`bool Curl_xfer_write_is_paused(struct Curl_easy *data)` · [lib/transfer.c:L777-L780][f1]

Reports whether the client writer chain is currently paused, so response writing must wait.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/transfer.c
