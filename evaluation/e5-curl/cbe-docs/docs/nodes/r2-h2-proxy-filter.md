# H2-PROXY Filter & Session Plumbing

**Capability.** The H2-PROXY connection filter: context lifecycle, vtable entries, and the nghttp2 session drivers and network buffers that move frames to and from the lower filter.

Use to see how the filter is built, initialized and destroyed, how its vtable callbacks behave, and how nghttp2 output is flushed through bufqs to the next filter. Liveness and pending-input processing live here too.

**Depends on.**

- [Buffer Queue Model](r2-bufq-buffer-queues.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [CONNECT Tunnel State Machine](r2-h2-proxy-tunnel.md) · model-inferred · 0 edge(s)

Parent: [HTTP/2 Proxy CONNECT Tunnel](r2-h2-proxy-connect.md)

## Units (29)

<a id="u-bff8fa227557"></a>
### `cf-h2-proxy.c module code (L1–L58)`

`module_region` · [lib/cf-h2-proxy.c:L1-L58][f1]

Preprocessor-gated compilation unit for the HTTP/2 proxy CONNECT filter, active only when HTTP, proxy support, and nghttp2 are enabled.

Includes headers, defines buffer/window sizing constants, and declares the tunnel state enum and tunnel_stream struct.

group: [lib/cf-h2-proxy.c:<enum>](r2-h2-proxy-tunnel.md#u-7c9acefeaf6b)

<a id="u-409f5f241107"></a>
### `cf-h2-proxy.c module code (L1469–L1487)`

`CURLcode Curl_cf_h2_proxy_insert_after(struct Curl_cfilter *cf, struct Curl_easy *dat…` · [lib/cf-h2-proxy.c:L1488-L1515][f1]

Defines the Curl_cftype instance 'H2-PROXY' (IP_CONNECT and PROXY flags) binding all the cf_h2_proxy_* callbacks, using the default keep-alive implementation.

<a id="u-16455d257878"></a>
### `cf-h2-proxy.c module code (L1515–L1517)`

`module_region` · [lib/cf-h2-proxy.c:L1515-L1517][f1]

Closing preprocessor conditional matching the opening feature guards at the top of the file.

<a id="u-548c9d5914cd"></a>
### `cf_h2_proxy_ctx`

`struct cf_h2_proxy_ctx` · [lib/cf-h2-proxy.c:L179-L197][f1]

Filter context: the nghttp2 session, per-call easy-handle save area, network in/out bufqs, linked peer (proxy) and dest (target) peers, the single tunnel CONNECT stream, GOAWAY error and remote max stream id, and flags for conn closed, GOAWAY sent/received, output blocked, and UDP tunneling.

<a id="u-22e950e11ac8"></a>
### `Curl_cf_h2_proxy_insert_after`

`CURLcode Curl_cf_h2_proxy_insert_after(struct Curl_cfilter *cf, struct Curl_easy *dat…` · [lib/cf-h2-proxy.c:L1488-L1515][f1]

Public constructor: allocates a zeroed context, links the proxy peer and destination peer (incrementing their references), records whether this is a UDP tunnel, creates a filter from Curl_cft_h2_proxy, and inserts it after the given filter.

On any failure after allocation the context (including linked peers) is freed and the error — defaulting to CURLE_OUT_OF_MEMORY — is returned.

<a id="u-a0b7d11d5e2e"></a>
### `cf_h2_proxy_connect`

`static CURLcode cf_h2_proxy_connect(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/cf-h2-proxy.c:L987-L1039][f1]

Filter connect: if already connected reports done; otherwise connects the lower filters first, returning until they complete.

Then, with call data saved, lazily initializes the context, checks the time left (timeout yields CURLE_OPERATION_TIMEDOUT), and runs H2_CONNECT. Done is set only when the result is OK and the tunnel is ESTABLISHED, in which case the filter is marked connected and the request/client state is soft-reset so the real request follows the CONNECT.

calls: [cf_h2_proxy_ctx_init](r2-h2-proxy-filter.md#u-36837a5f7e71), [H2_CONNECT](r2-h2-proxy-tunnel.md#u-252187fef862)

<a id="u-36837a5f7e71"></a>
### `cf_h2_proxy_ctx_init`

`static CURLcode cf_h2_proxy_ctx_init(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-h2-proxy.c:L906-L985][f1]

Initializes the filter context: zeroes the tunnel, creates in/out bufqs, sets remote_max_sid to INT32_MAX, initializes the tunnel stream, and builds an nghttp2 client session with the send, frame-recv, (verbose) frame-send, data-chunk, stream-close, and header callbacks.

Submits settings for max concurrent streams (from the multi handle), a 10MB initial window, and push disabled; then sets a huge (100MB) connection-level local window. Allocation, callback, session, or settings failures return CURLE_OUT_OF_MEMORY, CURLE_HTTP2, or the nghttp2-derived error, always deleting the callbacks object.

<a id="u-f48b4529e121"></a>
### `cf_h2_proxy_ctx_clear`

`static void cf_h2_proxy_ctx_clear(struct cf_h2_proxy_ctx *ctx)` · [lib/cf-h2-proxy.c:L203-L217][f1]

Releases all context resources: deletes the nghttp2 session, frees both bufqs, unlinks peer and dest, clears the tunnel stream, then zeroes the context while preserving the saved call_data.

calls: [tunnel_stream_clear](r2-h2-proxy-tunnel.md#u-268b622e2869)

<a id="u-d39397e85e65"></a>
### `cf_h2_proxy_ctx_free`

`static void cf_h2_proxy_ctx_free(struct cf_h2_proxy_ctx *ctx)` · [lib/cf-h2-proxy.c:L219-L225][f1]

Frees the context if non-NULL by clearing its resources then releasing the allocation.

calls: [cf_h2_proxy_ctx_clear](r2-h2-proxy-filter.md#u-f48b4529e121)

<a id="u-96d52283f4ec"></a>
### `cf_h2_proxy_destroy`

`static void cf_h2_proxy_destroy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-h2-proxy.c:L1041-L1051][f1]

Filter destructor: frees the context and NULLs cf->ctx.

<a id="u-621100a3e906"></a>
### `cf_h2_proxy_shutdown`

`static CURLcode cf_h2_proxy_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data,…` · [lib/cf-h2-proxy.c:L1053-L1095][f1]

Graceful shutdown: no-op (done) if never connected, no session, already shutting down, or connection closed.

Otherwise submits a GOAWAY with reason "shutdown" once (submission failure is CURLE_SEND_ERROR), then runs egress and ingress progress until nghttp2 no longer wants I/O or the connection closes. cf->shutdown is set on completion or error; *done reflects completion.

**Notes.**

- side_effect: records ctx->sent_goaway so GOAWAY is submitted only once

<a id="u-b097f23f7fd4"></a>
### `cf_h2_proxy_flush`

`static CURLcode cf_h2_proxy_flush(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-h2-proxy.c:L1329-L1359][f1]

Flushes buffered tunnel data: resumes the suspended stream if sendbuf is non-empty (fatal resume error is CURLE_SEND_ERROR), then runs egress progress to push frames out, logging window and buffer state.

<a id="u-537c4f21455f"></a>
### `cf_h2_proxy_cntrl`

`static CURLcode cf_h2_proxy_cntrl(struct Curl_cfilter *cf, struct Curl_easy *data, in…` · [lib/cf-h2-proxy.c:L1449-L1469][f1]

Filter control: CF_CTRL_FLUSH performs cf_h2_proxy_flush with call-data save/restore; other events are ignored with CURLE_OK.

<a id="u-74a12356601e"></a>
### `cf_h2_proxy_query`

`static CURLcode cf_h2_proxy_query(struct Curl_cfilter *cf, struct Curl_easy *data, in…` · [lib/cf-h2-proxy.c:L1415-L1447][f1]

Filter query dispatch: CF_QUERY_HOST_PORT returns the destination host/port; CF_QUERY_NEED_FLUSH reports TRUE when either output buffer is non-empty (otherwise falls through); CF_QUERY_ALPN_NEGOTIATED returns NULL (no ALPN at this layer).

Unknown queries defer to the next filter or return CURLE_UNKNOWN_OPTION.

<a id="u-d883732e3c66"></a>
### `cf_h2_proxy_adjust_pollset`

`static CURLcode cf_h2_proxy_adjust_pollset(struct Curl_cfilter *cf, struct Curl_easy …` · [lib/cf-h2-proxy.c:L1108-L1159][f1]

Tunes socket poll interest.

Before connection with a live session, want-send covers nghttp2 write appetite plus non-empty out/tunnel send buffers, want-recv follows nghttp2 read appetite; after connection the current pollset interests are read. When a session exists, remote connection/stream window exhaustion forces want-recv (to process WINDOW_UPDATEs), and want-send is suppressed when the stream window is exhausted unless other output is pending. Separately, during shutdown (GOAWAY sent, not finished) it requests the I/O nghttp2 still needs. Pollset updates are wrapped in call-data save/restore.

**Uncertainties.**

- the want_recv assignment adds window exhaustion to want_recv even if it was previously false; the resulting poll semantics depend on Curl_pollset_set

<a id="u-5e4f9e882221"></a>
### `cf_h2_proxy_data_pending`

`static bool cf_h2_proxy_data_pending(struct Curl_cfilter *cf, const struct Curl_easy …` · [lib/cf-h2-proxy.c:L1097-L1106][f1]

Reports pending data when the input bufq is non-empty, or when the tunnel is established and its recvbuf holds data; otherwise defers to the next filter's has_data_pending, or FALSE if none.

<a id="u-b070a18b2702"></a>
### `cf_h2_proxy_is_alive`

`static bool cf_h2_proxy_is_alive(struct Curl_cfilter *cf, struct Curl_easy *data, boo…` · [lib/cf-h2-proxy.c:L1398-L1413][f1]

Filter is_alive wrapper: reports alive only when a context and session exist and the underlying check passes, with call-data save/restore and a trace log.

<a id="u-769a8dd5eab7"></a>
### `cf_h2_proxy_recv`

`static CURLcode cf_h2_proxy_recv(struct Curl_cfilter *cf, struct Curl_easy *data, cha…` · [lib/cf-h2-proxy.c:L1208-L1253][f1]

Filter read path; errors if the tunnel is not established.

When the recvbuf is empty it first progresses ingress to pull frames, then reads via tunnel_recv. Successful reads are reported to nghttp2 via nghttp2_session_consume to open the flow-control window. The first fatal result among the read and a following egress progress wins. If data remains queued with no fatal error, drain_tunnel re-marks the transfer dirty to prevent stalls.

calls: [tunnel_recv](r2-h2-proxy-tunnel.md#u-536db7feaaee), [proxy_h2_progress_ingress](r2-h2-proxy-filter.md#u-7c453beaefb8), [proxy_h2_progress_egress](r2-h2-proxy-filter.md#u-44dfb49417c4), [drain_tunnel](r2-h2-proxy-tunnel.md#u-55347d4e251a)

<a id="u-78edce6d9460"></a>
### `cf_h2_proxy_send`

`static CURLcode cf_h2_proxy_send(struct Curl_cfilter *cf, struct Curl_easy *data, con…` · [lib/cf-h2-proxy.c:L1255-L1327][f1]

Filter write path; errors if the tunnel is not established or already closed.

Appends bytes into tunnel.sendbuf (CURLE_AGAIN tolerated), resumes the suspended nghttp2 stream when data is buffered (fatal resume errors are CURLE_SEND_ERROR), then progresses ingress and egress, keeping the first fatal result. If afterwards nghttp2 considers the session done, an unclosed stream is CURLE_HTTP2 while a closed one is CURLE_SEND_ERROR. Pending data without fatal error triggers drain_tunnel; a trace line logs window and buffer state.

calls: [proxy_h2_progress_ingress](r2-h2-proxy-filter.md#u-7c453beaefb8), [proxy_h2_progress_egress](r2-h2-proxy-filter.md#u-44dfb49417c4), [drain_tunnel](r2-h2-proxy-tunnel.md#u-55347d4e251a)

<a id="u-f4b36d44df06"></a>
### `proxy_h2_client_new`

`static int proxy_h2_client_new(struct Curl_cfilter *cf, nghttp2_session_callbacks *cbs)` · [lib/cf-h2-proxy.c:L256-L277][f1]

Creates the nghttp2 client session with curl's memory functions.

Disables automatic window updates so curl enforces buffer limits itself; on nghttp2 >= 1.50.0 also disables RFC 9113 whitespace validation. Returns nonzero nghttp2 error code on failure, storing the session in ctx->h2 on success.

**Uncertainties.**

- exact nghttp2 version threshold behavior is compile-time dependent

<a id="u-6d1f8a876e3c"></a>
### `proxy_h2_process_pending_input`

`static CURLcode proxy_h2_process_pending_input(struct Curl_cfilter *cf, struct Curl_e…` · [lib/cf-h2-proxy.c:L314-L348][f1]

Feeds buffered network input to nghttp2 in a loop.

On an nghttp2 error (negative return) it fails with CURLE_RECV_ERROR and a message; a zero-byte return (deemed improbable) breaks the loop; otherwise consumed bytes are skipped and the loop ends when the input bufq is empty. Returns CURLE_OK otherwise.

<a id="u-7c453beaefb8"></a>
### `proxy_h2_progress_ingress`

`static CURLcode proxy_h2_progress_ingress(struct Curl_cfilter *cf, struct Curl_easy *…` · [lib/cf-h2-proxy.c:L350-L395][f1]

Drives inbound processing: first consumes any already-buffered input, then loops reading from the lower filter into inbufq and feeding nghttp2.

Loop stops when the connection or tunnel is closed, input is pending, or the tunnel recvbuf is full. A read error other than CURLE_AGAIN fails with CURLE_RECV_ERROR after logging; zero bytes read marks the connection closed; CURLE_AGAIN just breaks. Processing errors propagate immediately.

<a id="u-44dfb49417c4"></a>
### `proxy_h2_progress_egress`

`static CURLcode proxy_h2_progress_egress(struct Curl_cfilter *cf, struct Curl_easy *d…` · [lib/cf-h2-proxy.c:L397-L413][f1]

Drives outbound nghttp2 traffic: clears nw_out_blocked, then repeatedly calls nghttp2_session_send while it wants to write and output is not blocked, which queues frames into outbufq via the send callback.

A fatal nghttp2 error yields CURLE_SEND_ERROR; otherwise the outbufq is flushed (which may set nw_out_blocked again or return CURLE_AGAIN).

calls: [proxy_h2_nw_out_flush](r2-h2-proxy-filter.md#u-8341cad28c85)

<a id="u-8a8c5c2d176b"></a>
### `proxy_h2_should_close_session`

`static int proxy_h2_should_close_session(struct cf_h2_proxy_ctx *ctx)` · [lib/cf-h2-proxy.c:L279-L283][f1]

Returns true when nghttp2 neither wants to read nor write, i.e. the session considers itself finished.

<a id="u-72b60cf67138"></a>
### `proxy_h2_connisalive`

`static bool proxy_h2_connisalive(struct Curl_cfilter *cf, struct Curl_easy *data, boo…` · [lib/cf-h2-proxy.c:L1361-L1396][f1]

Liveness check delegating to the next filter; if the lower layer reports pending input it drains that data into inbufq, processes it as HTTP/2 frames, and considers the connection dead on processing error or when nghttp2 says the session is finished.

A failed read (other than CURLE_AGAIN) also means dead. Otherwise the connection is alive.

calls: [proxy_h2_process_pending_input](r2-h2-proxy-filter.md#u-6d1f8a876e3c), [proxy_h2_should_close_session](r2-h2-proxy-filter.md#u-8a8c5c2d176b)

<a id="u-203561a110c7"></a>
### `proxy_h2_nw_out_writer`

`static CURLcode proxy_h2_nw_out_writer(void *writer_ctx, const uint8_t *buf, size_t b…` · [lib/cf-h2-proxy.c:L239-L254][f1]

Bufq writer callback that sends buffered bytes through the next (lower) filter using Curl_conn_cf_send.

Sets *pnwritten to 0 first; if the writer context is NULL returns CURLE_FAILED_INIT, otherwise returns the send result and count.

<a id="u-8341cad28c85"></a>
### `proxy_h2_nw_out_flush`

`static CURLcode proxy_h2_nw_out_flush(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-h2-proxy.c:L285-L307][f1]

Flushes the network output bufq to the lower filter.

Returns OK immediately if empty. On CURLE_AGAIN from the writer it sets ctx->nw_out_blocked and returns the error; other errors propagate. On success returns OK if fully drained, else CURLE_AGAIN with data still queued.

**Notes.**

- side_effect: sets ctx->nw_out_blocked when the socket would block

<a id="u-d8b712e5ccaf"></a>
### `on_session_send`

`static ssize_t on_session_send(nghttp2_session *h2, const uint8_t *buf, size_t blen, …` · [lib/cf-h2-proxy.c:L415-L445][f1]

nghttp2 send callback that writes session output into outbufq, which passes bytes to the lower filter.

On CURLE_AGAIN it sets nw_out_blocked and returns NGHTTP2_ERR_WOULDBLOCK; other write errors return NGHTTP2_ERR_CALLBACK_FAILURE. Zero bytes written also yields WOULDBLOCK; counts above SSIZE_MAX are a callback failure, otherwise the byte count is returned.

<a id="u-857d631b4657"></a>
### `proxy_h2_on_frame_send`

`static int proxy_h2_on_frame_send(nghttp2_session *session, const nghttp2_frame *fram…` · [lib/cf-h2-proxy.c:L448-L465][f1]

Verbose-only nghttp2 callback that formats and logs each sent frame when cf tracing is enabled; always returns 0.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cf-h2-proxy.c
