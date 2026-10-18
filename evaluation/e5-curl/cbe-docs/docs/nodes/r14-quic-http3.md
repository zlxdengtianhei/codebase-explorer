# QUIC / HTTP/3 Filter (ngtcp2)

**Capability.** Owns the ngtcp2/nghttp3 connection filter: HTTP/3 stream lifecycle, request/response data transfer via h3 callbacks, QUIC flow-control window management, and the filter's send/recv/control/query methods, plus the proxy-tunnel filter declaration header.

Use this subtree to trace how request bytes are buffered onto H3 streams and how response headers/bodies flow from nghttp3 callbacks into the transfer. The static ngh3_callbacks table and factory functions tie the callbacks into the filter chain.

**Depends on.**

- [rustls Backend Registration & Misc](r14-tls-rustls-backend.md) · model-inferred · 0 edge(s)

Parent: [curl Codebase](r14-curl-codebase.md)

## Units (27)

<a id="u-d45e1c5e45d2"></a>
### `cf-ngtcp2-proxy-h`

`module_region` · [lib/vquic/cf-ngtcp2-proxy.h:L1-L52][f1]

Declares factories for the ngtcp2-based HTTP/3-proxy (tunnel) connection filter, compiled only when HTTP, proxy, HTTP3 proxy, nghttp3, ngtcp2, and OpenSSL are all enabled.

`Curl_cf_ngtcp2_proxy_insert_after` inserts the filter after `cf_at`, taking the origin peer, the peer, a tunnel peer, and a `tunnel_transport` byte. `Curl_cf_ngtcp2_proxy_create` instead creates the filter directly into `*pcf`, additionally taking the connection, an extended sockaddr, and a `transport_peer` byte. Both return CURLcode. No definitions here.

**Uncertainties.**

- Meaning of the `tunnel_transport`/`transport_peer` byte parameters and how the tunnel peer is used is not established from this header.

<a id="u-60c3c722a5d5"></a>
### `Curl_cf_ngtcp2_create`

`CURLcode Curl_cf_ngtcp2_create(struct Curl_cfilter **pcf, struct Curl_easy *data, str…` · [lib/vquic/cf-ngtcp2.c:L1070-L1112][f2]

Public factory creating an HTTP/3 filter on top of a UDP transport.

Allocates the ctx (CURLE_OUT_OF_MEMORY on failure), initializes it with the connection ssl_config and init_ngh3_conn, wraps it via Curl_cf_create in Curl_cft_http3, then chains a UDP filter created with TRNSPRT_QUIC, linking conn and sockindex. On any failure the created filter chain is discarded, or the bare ctx cleaned up; *pcf is NULL on failure.

<a id="u-ee49c11cc03e"></a>
### `Curl_cf_ngtcp2_insert_after`

`CURLcode Curl_cf_ngtcp2_insert_after(struct Curl_cfilter *cf_at, struct Curl_peer *or…` · [lib/vquic/cf-ngtcp2.c:L1114-L1145][f2]

Public factory inserting an HTTP/3 filter after an existing filter: allocates the ctx (CURLE_OUT_OF_MEMORY on failure), initializes it with the target filter's connection ssl_config and init_ngh3_conn, wraps it in Curl_cft_http3, and inserts it after cf_at via Curl_conn_cf_insert_after.

On failure the filter and ctx are freed and *pcf is NULL.

<a id="u-b5c2e078ca7c"></a>
### `cb_h3_acked_req_body`

`static int cb_h3_acked_req_body(nghttp3_conn *conn, int64_t stream_id, uint64_t datal…` · [lib/vquic/cf-ngtcp2.c:L568-L597][f2]

nghttp3 callback when the server ACKs datalen request-body bytes: frees that data from stream->sendbuf (skiplen clamped to tx_in_flight_size) and decrements tx_in_flight_size.

When buffered bytes now exceed in-flight size, resumes the H3 stream via nghttp3_conn_resume_stream, tolerating NGHTTP3_ERR_STREAM_NOT_FOUND; other failures return NGHTTP3_ERR_CALLBACK_FAILURE. Missing stream returns 0.

<a id="u-fd56253bd98b"></a>
### `cb_h3_deferred_consume`

`static int cb_h3_deferred_consume(nghttp3_conn *conn, int64_t stream3_id, size_t cons…` · [lib/vquic/cf-ngtcp2.c:L238-L257][f2]

nghttp3 callback for deferred consumption: extends both the stream-specific and connection-wide QUIC flow-control windows by the consumed byte count.

When a stream context is present it also advances rx_offset and rx_offset_max by the same amount. Always returns 0.

<a id="u-43eff203c9d3"></a>
### `cb_h3_end_headers`

`static int cb_h3_end_headers(nghttp3_conn *conn, int64_t stream_id, int fin, void *us…` · [lib/vquic/cf-ngtcp2.c:L259-L284][f2]

nghttp3 callback at the end of a header block.

Missing stream or transfer returns 0 quietly. Writes a CRLF via h3_xfer_write_resp_hd, with eos set from stream->closed. If the status code is not 1xx (stream->status_code/100 != 1), marks stream->resp_hds_complete; 1xx responses leave it incomplete so more header blocks are expected. Marks the transfer dirty.

calls: [h3_xfer_write_resp_hd](r14-quic-http3.md#u-901fa22f7297)

<a id="u-812fc78e2ec8"></a>
### `cb_h3_read_req_body`

`static nghttp3_ssize cb_h3_read_req_body(nghttp3_conn *conn, int64_t stream_id, nghtt…` · [lib/vquic/cf-ngtcp2.c:L599-L661][f2]

nghttp3 data reader supplying request-body vectors from stream->sendbuf.

Missing stream or transfer is a callback failure. Only bytes beyond tx_in_flight_size (already handed to nghttp3, not yet ACKed) are offered: it peeks sendbuf segments into vec, advancing tx_in_flight_size and nwritten, up to veccnt. nwritten decrements upload_left unless it is -1 (unknown size). If upload_left reaches 0 it sets NGHTTP3_DATA_FLAG_EOF and stream->send_closed. If no data could be offered and there is no EOF, returns NGHTTP3_ERR_WOULDBLOCK. Returns the vector count.

contract: [cb_h3_acked_req_body](r14-quic-http3.md#u-b5c2e078ca7c)

<a id="u-238843f24264"></a>
### `cb_h3_recv_data`

`static int cb_h3_recv_data(nghttp3_conn *conn, int64_t stream3_id, const uint8_t *buf…` · [lib/vquic/cf-ngtcp2.c:L209-L236][f2]

nghttp3 callback delivering received DATA bytes.

If the transfer or stream context is missing it returns NGHTTP3_ERR_CALLBACK_FAILURE, aborting the H3 processing. Otherwise it forwards the bytes via h3_xfer_write_resp (which swallows transfer-write errors), extends the connection max offset by buflen, advances stream->rx_offset (raising rx_offset_max to match if it lagged), and finally calls cf_ngtcp2_upd_rx_win to return flow-control credit.

calls: [h3_xfer_write_resp](r14-quic-http3.md#u-26acb2b79377), [cf_ngtcp2_upd_rx_win](r14-quic-http3.md#u-052da52c7e45)

<a id="u-859e7602be73"></a>
### `cb_h3_recv_header`

`static int cb_h3_recv_header(nghttp3_conn *conn, int64_t stream_id, int32_t token, ng…` · [lib/vquic/cf-ngtcp2.c:L286-L351][f2]

nghttp3 callback for each header.

Cleaned-up transfers return 0. For the QPACK :status token it decodes the status into stream->status_code (decode failure returns NGHTTP3_ERR_CALLBACK_FAILURE), builds an 'HTTP/3 <code> \r\n' line in ctx->scratch and forwards it as header bytes; any dynbuf allocation failure also yields NGHTTP3_ERR_CALLBACK_FAILURE. All other headers are reformatted as 'name: value\r\n' in the same scratch buffer and forwarded. Both branches route through h3_xfer_write_resp_hd, so a known transfer error suppresses the write.

calls: [h3_xfer_write_resp_hd](r14-quic-http3.md#u-901fa22f7297)

**Uncertainties.**

- Whether trailers reuse this callback with different token values is not visible; the code treats it the same as regular headers.

<a id="u-c589d854f558"></a>
### `cb_h3_reset_stream`

`static int cb_h3_reset_stream(nghttp3_conn *conn, int64_t stream_id, uint64_t app_err…` · [lib/vquic/cf-ngtcp2.c:L372-L391][f2]

nghttp3 callback to reset the send side of a QUIC stream: calls ngtcp2_conn_shutdown_stream_write with the app error code, logs when a transfer context exists, tolerates NGTCP2_ERR_STREAM_NOT_FOUND, and otherwise returns NGHTTP3_ERR_CALLBACK_FAILURE.

<a id="u-f1baca19f85d"></a>
### `cb_h3_stop_sending`

`static int cb_h3_stop_sending(nghttp3_conn *conn, int64_t stream_id, uint64_t app_err…` · [lib/vquic/cf-ngtcp2.c:L353-L370][f2]

nghttp3 callback when the peer sends STOP_SENDING: shuts down the read side of the QUIC stream with the given app error via ngtcp2_conn_shutdown_stream_read.

NGTCP2_ERR_STREAM_NOT_FOUND is tolerated (returns 0); any other ngtcp2 error maps to NGHTTP3_ERR_CALLBACK_FAILURE.

<a id="u-3e770a088fd6"></a>
### `cb_h3_stream_close`

`static int cb_h3_stream_close(nghttp3_conn *conn, int64_t stream_id, uint64_t app_err…` · [lib/vquic/cf-ngtcp2.c:L93-L121][f2]

nghttp3 callback marking a stream closed by the peer.

Resolves the transfer via Curl_cf_ngtcp2_get_xfer; if data or stream is already gone it returns 0 silently, since nghttp3 may invoke this after local cleanup. Sets stream->closed and error3; when the app error is not NGHTTP3_H3_NO_ERROR it also sets reset and send_closed (treated as a stream reset), otherwise only logs CLOSED. Always marks the transfer dirty so the multi loop revisits it.

uses: [recv_closed_stream](r14-quic-http3.md#u-b5f87b2083f7)

<a id="u-552dc0f3c163"></a>
### `cf_ngtcp2_adjust_pollset`

`static CURLcode cf_ngtcp2_adjust_pollset(struct Curl_cfilter *cf, struct Curl_easy *d…` · [lib/vquic/cf-ngtcp2.c:L55-L91][f2]

Updates the pollset for the QUIC socket to reflect HTTP/3 send/recv interest.

It resolves the socket from the QUIC context or the underlying filter chain and returns immediately (CURLE_OK) when there is no H3 connection or no socket. It reads current want_recv/want_send via Curl_pollset_check, forces want_send when the connection send buffer is non-empty, then under saved filter data computes: connection-level exhaustion (no ngtcp2 cwnd or max-data left) and stream-level exhaustion (quic flow blocked or in-flight tx at ideal). Either exhaustion or original want_recv turns on want_recv; want_send is cleared only by stream exhaustion. Final interest is applied with Curl_pollset_set.

**Notes.**

- side_effect: CF_DATA_SAVE/CF_DATA_RESTORE around ngtcp2 calls reroute Curl_easy-relative context during the check.

uses: [cf_ngtcp2_upd_rx_win](r14-quic-http3.md#u-052da52c7e45), [cf_ngtcp2_query](r14-quic-http3.md#u-845d8b713f22)

**Uncertainties.**

- Exact semantics of Curl_pollset_check/set are external to this file.

<a id="u-8d98e5079f4b"></a>
### `cf_ngtcp2_cntrl`

`static CURLcode cf_ngtcp2_cntrl(struct Curl_cfilter *cf, struct Curl_easy *data, int …` · [lib/vquic/cf-ngtcp2.c:L927-L967][f2]

Control-event dispatcher for the HTTP/3 filter, under saved filter data.

CF_CTRL_DATA_SETUP does nothing; CF_CTRL_DATA_PAUSE delegates to h3_data_pause; CF_CTRL_DATA_DONE runs Curl_cf_ngtcp2_h3_stream_done; CF_CTRL_DATA_DONE_SEND closes the send side when not already closed, recomputing upload_left as buffered minus in-flight bytes and resuming the H3 stream; CF_CTRL_CONN_INFO_UPDATE marks httpversion_seen=30 and enables multiplexing on a connected primary socket; all other events fall through to Curl_cf_ngtcp2_cmn_cntrl, whose result is propagated.

<a id="u-4bf3cf1cff52"></a>
### `cf_ngtcp2_connect`

`static CURLcode cf_ngtcp2_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bo…` · [lib/vquic/cf-ngtcp2.c:L987-L992][f2]

Connect callback; a pure pass-through to Curl_cf_ngtcp2_cmn_connect, returning its result and done flag.

<a id="u-d450ea94d396"></a>
### `cf_ngtcp2_destroy`

`static void cf_ngtcp2_destroy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vquic/cf-ngtcp2.c:L969-L985][f2]

Destroys the filter: when a QUIC connection still exists it closes it under saved filter data (Curl_cf_ngtcp2_cmn_conn_close), then cleans up the ctx and frees it, nulling cf->ctx.

Safe when ctx is already NULL.

<a id="u-845d8b713f22"></a>
### `cf_ngtcp2_query`

`static CURLcode cf_ngtcp2_query(struct Curl_cfilter *cf, struct Curl_easy *data, int …` · [lib/vquic/cf-ngtcp2.c:L994-L1051][f2]

Query handler for the HTTP/3 filter.

CF_QUERY_MAX_CONCURRENT: 0 when no QUIC connection or shutdown started; otherwise attached transfers plus the remaining budget of transport-negotiated bidi streams (clamped to INT_MAX); if transport params have not arrived, falls back to the multi's configured max concurrent streams. CF_QUERY_HTTP_VERSION reports 30. CF_QUERY_SSL_INFO/SSL_CTX_INFO fill a curl_tlssessioninfo via Curl_vquic_tls_get_ssl_info and return OK on success, otherwise falling through. CF_QUERY_ALPN_NEGOTIATED yields "h3" when connected, NULL otherwise. Unhandled queries delegate to Curl_cf_ngtcp2_cmn_query, whose result is returned.

**Uncertainties.**

- Whether CF_QUERY_SSL_INFO fall-through to cmn_query can succeed is decided by that helper.

<a id="u-88160ba67193"></a>
### `cf_ngtcp2_recv`

`static CURLcode cf_ngtcp2_recv(struct Curl_cfilter *cf, struct Curl_easy *data, char …` · [lib/vquic/cf-ngtcp2.c:L493-L566][f2]

Recv callback of the HTTP/3 filter: produces response bytes by driving nghttp3/QUIC.

Saves filter data, asserts connected state, zeroes *pnread. A stored ctx->tls_vrfy_result short-circuits to 'denied' with that code. No stream or a started shutdown returns CURLE_RECV_ERROR. Otherwise it updates the rx window, then loops twice: on each pass a known stream->xfer_result closes the H3 stream and returns that error; stream->closed delegates to recv_closed_stream. On the first iteration only, Curl_cf_ngtcp2_progress_ingress pumps incoming packets; processing may resolve or close the stream, hence the second check. If the stream survives both passes, the result is CURLE_AGAIN. At the shared exit, egress progress and expiry setting run via Curl_1st_fatal (first fatal error wins); a stored tls_vrfy_result overrides the final result. Filter data is always restored.

calls: [recv_closed_stream](r14-quic-http3.md#u-b5f87b2083f7), [cf_ngtcp2_upd_rx_win](r14-quic-http3.md#u-052da52c7e45)

**Uncertainties.**

- pnread is never assigned a nonzero value in this function; whether progress_ingress delivers data via the h3_xfer_write_* callbacks rather than through buf is implied but not directly visible here.

<a id="u-4339f19ec0de"></a>
### `cf_ngtcp2_send`

`static CURLcode cf_ngtcp2_send(struct Curl_cfilter *cf, struct Curl_easy *data, const…` · [lib/vquic/cf-ngtcp2.c:L791-L913][f2]

Send callback of the HTTP/3 filter: buffers outgoing request data on the H3 stream.

Saves filter data, zeroes *pnwritten; a stored ctx->tls_vrfy_result short-circuits to 'denied'. Runs ingress progress first; failure aborts. Branches: no stream or negative id means open a new one via h3_stream_open (CURLE_SEND_ERROR if the connection is shutting down; open failure propagates); a known stream->xfer_result closes the stream and returns that error; a closed stream with complete response headers silently discards the data, reporting all len written (valid for 30x/40x where the server ignores the body); a closed stream otherwise is CURLE_HTTP3; shutdown_started is CURLE_SEND_ERROR; in-flight bytes at tx_in_flight_ideal returns CURLE_AGAIN; otherwise data is appended to stream->sendbuf and nghttp3_conn_resume_stream is invoked. Early data written before the TLS handshake completes increments ctx->earlydata_skip. Egress progress then flushes packets. With bytes written, tx_in_flight_ideal adapts by 2 KiB: grown when ngtcp2 keeps more than ideal+delta in flight, shrunk when it keeps less than ideal-delta. The shared exit applies expiry via Curl_1st_fatal and lets tls_vrfy_result override; filter data is restored.

calls: [h3_stream_open](r14-quic-http3.md#u-6cb840a8600d)

**Uncertainties.**

- eos is explicitly unused in this version (comment 'use for stream EOF and block handling').

<a id="u-052da52c7e45"></a>
### `cf_ngtcp2_upd_rx_win`

`static void cf_ngtcp2_upd_rx_win(struct Curl_cfilter *cf, struct Curl_easy *data, str…` · [lib/vquic/cf-ngtcp2.c:L164-L207][f2]

Extends the QUIC flow-control window for a stream toward H3_STREAM_WINDOW_SIZE_MAX.

When a download rate limit is active: it returns without update if no bytes have arrived yet (rx_offset zero), and returns if the limiter has no tokens available; otherwise the wanted window is clamped to the available tokens. If rx_offset_max ever appears below rx_offset it asserts and bails. When wanted exceeds the current window, the delta is clamped to avoid uint64 overflow, then rx_offset_max is grown and ngtcp2_conn_extend_max_stream_offset tells ngtcp2 about the credit.

**Notes.**

- condition: Rate limit and underflow checks make this a no-op in those cases; only a positive delta triggers ngtcp2 flow-control extension.

<a id="u-110f788fdc95"></a>
### `h3_data_pause`

`static CURLcode h3_data_pause(struct Curl_cfilter *cf, struct Curl_easy *data, bool p…` · [lib/vquic/cf-ngtcp2.c:L915-L925][f2]

Handles transfer pause for H3 streams: ngtcp2 offers no per-stream window resize, so nothing is done when pausing; unpausing only marks the transfer dirty so the multi loop retries.

Always returns CURLE_OK.

<a id="u-6cb840a8600d"></a>
### `h3_stream_open`

`static CURLcode h3_stream_open(struct Curl_cfilter *cf, struct Curl_easy *data, const…` · [lib/vquic/cf-ngtcp2.c:L663-L789][f2]

Opens a new HTTP/3 request stream for outgoing data.

Sets up the stream context, parses the buffered request as HTTP/1 (respecting a custom request method unless http_ignorecustom); if parsing is incomplete it returns with *pnwritten=0 to wait for more data. Converts the request to h2 headers, allocates an nghttp3_nv array (allocation failure is CURLE_OUT_OF_MEMORY), then opens a QUIC bidi stream: failure is CURLE_SEND_ERROR. Assigns stream->id and counts used bidi streams. upload_left is set from infilesize for POST/PUT variants, -1 when unknown, 0 for bodiless requests; send_closed follows, and a data reader is attached when a body remains. nghttp3_conn_submit_request failure closes the stream and returns CURLE_SEND_ERROR (logged distinctly when the connection is closing). Finally updates the rx window and logs the opened stream and headers in verbose mode. The nva array and dynhds are always freed on the out path.

**Notes.**

- failure: After successful parse, *pnwritten reflects bytes consumed by Curl_h1_req_parse_read; incomplete requests leave *pnwritten set but no stream opened.

**Uncertainties.**

- Whether the *pnwritten value on the incomplete-parse path lets the caller retain unconsumed bytes depends on the caller's handling, not visible here.

<a id="u-26acb2b79377"></a>
### `h3_xfer_write_resp`

`static void h3_xfer_write_resp(struct Curl_cfilter *cf, struct Curl_easy *data, struc…` · [lib/vquic/cf-ngtcp2.c:L143-L162][f2]

Writes response body bytes to the transfer, recording the outcome in stream->xfer_result and skipping all later writes once an error is stored.

Errors are logged; the stream is cancelled in the filter's send/recv paths rather than here, per the source comment.

<a id="u-901fa22f7297"></a>
### `h3_xfer_write_resp_hd`

`static void h3_xfer_write_resp_hd(struct Curl_cfilter *cf, struct Curl_easy *data, st…` · [lib/vquic/cf-ngtcp2.c:L123-L141][f2]

Writes response header bytes to the transfer, returning no error by design: the CURLcode is recorded in stream->xfer_result, and once that is set no further writes are attempted.

The accompanying comment explains that the stream is cancelled higher up in send/recv callbacks; closing here would overwrite the transfer result with SEND/RECV errors.

<a id="u-9f4098e27c1f"></a>
### `init_ngh3_conn`

`static CURLcode init_ngh3_conn(struct Curl_cfilter *cf, struct Curl_easy *data, struc…` · [lib/vquic/cf-ngtcp2.c:L429-L453][f2]

Initializes the HTTP/3 layer on a QUIC connection.

Fails with CURLE_QUIC_CONNECT_ERROR when fewer than 3 unidirectional streams remain. Loads default nghttp3 settings and creates the client connection with the static callbacks and nghttp3 memory; creation failure is reported as CURLE_OUT_OF_MEMORY. Delegates ctrl/stream setup to Curl_cf_ngtcp2_h3_init_ctrls and returns its result.

<a id="u-b5f87b2083f7"></a>
### `recv_closed_stream`

`static CURLcode recv_closed_stream(struct Curl_cfilter *cf, struct Curl_easy *data, s…` · [lib/vquic/cf-ngtcp2.c:L455-L490][f2]

Classifies an already-closed stream during recv, always setting *pnread=0.

If the stream was reset: error CURL_H3_ERR_REQUEST_REJECTED logs a retry hint, marks the connection for close, sets data->state.refused_stream, and returns CURLE_RECV_ERROR to trigger a later retry; otherwise, if response headers completed and the request wants no body, the error is ignored (CURLE_OK); any other reset fails with CURLE_PARTIAL_FILE when some body bytes were received, else CURLE_HTTP3. A clean close before complete response headers is CURLE_HTTP3; a clean close after headers is CURLE_OK.

**Notes.**

- side_effect: connclose(cf->conn) and data->state.refused_stream are set only in the rejected-stream branch.

<a id="u-7f505efd951b"></a>
### `cf-ngtcp2.c module code (L391–L428)`

`module_region` · [lib/vquic/cf-ngtcp2.c:L391-L428][f2]

Static ngh3_callbacks table wiring the cb_h3_* functions into nghttp3, with NULLs for begin_headers, trailer callbacks, end_stream, shutdown and recv_settings, plus version-conditional NULL slots for NGHTTP3_CALLBACKS_V2/V3/V4.

Non-behavioral initializer.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-ngtcp2-proxy.h
[f2]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-ngtcp2.c
