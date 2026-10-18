# H2 Frame Event Handling

**Capability.** nghttp2 callbacks that translate received frames, headers, stream closes and errors into per-stream actions and transfer results, plus session ingress/egress progress drivers.

Use to trace how nghttp2 events reach a transfer: frame dispatch to per-stream handling, header and data chunk delivery, stream-close handling, and the progress functions that push or pull session bytes. Verbose frame/error formatting is included.

Parent: [HTTP/2 Connection Filter \(nghttp2\)](r2-h2-connection-filter.md)

## Units (17)

<a id="u-f61b4f47df6c"></a>
### `on_frame_recv`

`static int on_frame_recv(nghttp2_session *session, const nghttp2_frame *frame, void *…` · [lib/http2.c:L1195-L1270][f1]

nghttp2 frame-received callback.

Stream id 0 handles connection-level frames: a non-ack SETTINGS refreshes ctx->max_concurrent_streams and ctx->enable_push from remote settings, marks the multi connection changed when the concurrency value actually changed, and un-holds a transfer that wants to send so an enlarged server window cannot stall it; a GOAWAY records the received flag, error code, and last stream id, logs it, and marks the connection changed. For stream frames it resolves the owning easy handle via cf_h2_get_stream_xfer and returns 0 when none exists; otherwise it dispatches to on_stream_frame, translating any error into NGHTTP2_ERR_CALLBACK_FAILURE.

calls: [on_stream_frame](r2-h2-frame-processing.md#u-4b3263804f42)

<a id="u-4b3263804f42"></a>
### `on_stream_frame`

`static CURLcode on_stream_frame(struct Curl_cfilter *cf, struct Curl_easy *data, stru…` · [lib/http2.c:L983-L1094][f1]

Applies a received frame to one stream.

Without a stream context it returns CURLE_FAILED_INIT. DATA before body start is a protocol error: RST_STREAM is submitted and a fatal result returns CURLE_RECV_ERROR. HEADERS after body start are trailers and ignored; otherwise a missing status code (fuzz-found case) returns CURLE_RECV_ERROR, a non-1xx status marks the header block complete and body started while a 1xx resets the status code; then the terminating CRLF header chunk is written and the transfer marked dirty. PUSH_PROMISE delegates to push_promise and on denial submits RST_STREAM with NGHTTP2_CANCEL — fatal submit yields CURLE_SEND_ERROR and CURL_PUSH_ERROROUT yields CURLE_RECV_ERROR. RST_STREAM with a nonzero error marks reset_by_server; WINDOW_UPDATE forces reprocessing when the request wants to send with an empty sendbuf, otherwise resumes suspended data when the sendbuf is non-empty. Finally, on END_STREAM with an unfinished upload and a status outside 2xx-3xx, the upload is aborted via RST_STREAM and the stream marked closed; the transfer is marked dirty.

<a id="u-4e2f2305c81c"></a>
### `on_header`

`static int on_header(nghttp2_session *session, const nghttp2_frame *frame, const uint…` · [lib/http2.c:L1421-L1596][f1]

nghttp2 header callback for HEADERS and PUSH_PROMISE frames.

It resolves the transfer first, returning NGHTTP2_ERR_CALLBACK_FAILURE for unknown transfers or missing stream context. For PUSH_PROMISE headers it validates :authority against the parent's origin (hostname:port, allowing the default-port or bare-hostname match), RST-ing with PROTOCOL_ERROR and failing otherwise per RFC 7540; it then accumulates 'name:value' strings into stream->push_headers, growing the array by doubling from 10 entries, failing with NGHTTP2_ERR_CALLBACK_FAILURE past 1000 entries ('too many headers') or on any allocation failure, freeing previously collected headers in that case. For normal frames: headers after body start are buffered as response trailers (failure routes through cf_h2_header_error); the :status pseudo header is decoded into status_code, pushed as a pseudo header, and converted to an 'HTTP/2 <code>' status line written via h2_xfer_write_resp_hd; any other header is converted to HTTP/1 style 'name: value' in ctx->scratch and written the same way. Any dynbuf/decode/push failure triggers cf_h2_header_error and returns NGHTTP2_ERR_CALLBACK_FAILURE; when the header arrived for a transfer other than the current filter call data, that transfer is marked dirty.

<a id="u-93bc389103b1"></a>
### `on_stream_close`

`static int on_stream_close(nghttp2_session *session, int32_t stream_id, uint32_t erro…` · [lib/http2.c:L1340-L1401][f1]

Handles nghttp2 closing a stream.

Stream id 0 is ignored; an unresolvable transfer or an invalid/no-longer-good easy handle (indicating libcurl freed it without DONE/DETACH) clears user_data and returns NGHTTP2_ERR_CALLBACK_FAILURE, as does a good easy handle with no stream context. Otherwise the stream is marked closed with the error code: a nonzero error marks it reset, and REFUSED_STREAM occurring after a GOAWAY carrying an error adopts the GOAWAY error as the stream error. The transfer is marked dirty and the stream's user_data is cleared, logging (with a debug assert) on failure but still returning 0.

<a id="u-775b66e1151b"></a>
### `on_data_chunk_recv`

`static int on_data_chunk_recv(nghttp2_session *session, uint8_t flags, int32_t stream…` · [lib/http2.c:L1305-L1338][f1]

Delivers a DATA chunk for a stream.

Unknown transfers (e.g. after an aborted transfer) are silently ignored and their bytes explicitly consumed with nghttp2_session_consume; a missing stream context returns NGHTTP2_ERR_CALLBACK_FAILURE. Known streams get the chunk written via h2_xfer_write_resp (which may RST the stream on transfer error), the bytes are consumed for flow control, and stream->nrcvd_data accumulates the length.

<a id="u-9e58de2e5e21"></a>
### `cf_h2_on_invalid_frame_recv`

`static int cf_h2_on_invalid_frame_recv(nghttp2_session *session, const nghttp2_frame …` · [lib/http2.c:L1272-L1303][f1]

Callback for frames nghttp2 rejects.

When the stream has an owning transfer it logs the invalid frame (verbose builds); if a stream context exists it submits RST_STREAM (NGHTTP2_STREAM_CLOSED), records the nghttp2 error in stream->error, and marks the stream closed and reset. Always returns 0, deliberately letting nghttp2 perform any further RST/GOAWAY itself.

<a id="u-c2bfb4c768a7"></a>
### `on_frame_send`

`static int on_frame_send(nghttp2_session *session, const nghttp2_frame *frame, void *…` · [lib/http2.c:L1168-L1192][f1]

Verbose-only send callback: logs the sent frame when trace is enabled, and when the sent frame is a GOAWAY the library itself did not initiate, logs a failure message with the nghttp2 shutdown error code.

Always returns 0.

<a id="u-864baa2aac58"></a>
### `error_callback`

`static int error_callback(nghttp2_session *session, const char *msg, size_t len, void…` · [lib/http2.c:L1645-L1655][f1]

Verbose-only nghttp2 error callback that forwards the session's error message to failf and always returns 0.

<a id="u-16cc48e88b98"></a>
### `h2_process_pending_input`

`static CURLcode h2_process_pending_input(struct Curl_cfilter *cf, struct Curl_easy *d…` · [lib/http2.c:L514-L548][f1]

Feeds all buffered network input to nghttp2.

It repeatedly peeks the input bufq and calls nghttp2_session_mem_recv; a conversion failure of the returned byte count logs the nghttp2 error and returns CURLE_RECV_ERROR, otherwise the consumed bytes are skipped. The loop breaks when the buffer is empty. After processing, if nghttp2_session_check_request_allowed returns 0 (GOAWAY received or stream id space exhausted) the connection is marked for closure so it will not be reused.

<a id="u-b2315c0f2fa5"></a>
### `h2_progress_ingress`

`static CURLcode h2_progress_ingress(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/http2.c:L1886-L1959][f1]

Pulls network data into the nghttp2 session.

A session nghttp2 considers done returns CURLE_HTTP2 immediately. Buffered input is processed first; failure propagates. Then it repeatedly receives from the next filter into the input bufq until the connection is closed or buffered input remains: a stream that is closed or a zero byte budget stops the loop, marking the transfer dirty only if the next filter has no pending data; a recv error other than CURLE_AGAIN fails with its code; a zero-byte read sets ctx->conn_closed; otherwise the byte budget is decremented and the input is processed. If the connection is closed with an empty buffer, the connection is marked closed (connclose) with GOAWAY noted if present.

<a id="u-f1055458aefb"></a>
### `h2_progress_egress`

`static CURLcode h2_progress_egress(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/http2.c:L1810-L1849][f1]

Drives nghttp2 sending.

When the user-set weight differs from the weight in effect and a live stream exists, it submits a PRIORITY frame via h2_pri_spec, aborting to the exit path on submit failure. Then it clears nw_out_blocked and loops nghttp2_session_send while nghttp2 wants to write and output is not blocked; a fatal error becomes CURLE_SEND_ERROR. Before the filter is connected (and unless connect_only) it defers flushing so SETTINGS and the first request go out together, returning CURLE_OK; otherwise it flushes the output bufq via nw_out_flush.

calls: [sweight_wanted](r2-h2-session-lifecycle.md#u-f30167bb62c2), [nw_out_flush](r2-h2-frame-processing.md#u-fd7962779ee2)

<a id="u-d05ba0675d06"></a>
### `send_callback`

`static ssize_t send_callback(nghttp2_session *h2, const uint8_t *buf, size_t blen, in…` · [lib/http2.c:L632-L667][f1]

nghttp2's send callback: routes frame bytes either into the output bufq while the filter is not yet connected, or directly through the next filter appended to the output bufq when connected.

CURLE_AGAIN or a zero-byte write sets ctx->nw_out_blocked and returns NGHTTP2_ERR_WOULDBLOCK; other errors log and return NGHTTP2_ERR_CALLBACK_FAILURE. On success returns the written count, capping failure if it exceeds SSIZE_MAX.

<a id="u-fd7962779ee2"></a>
### `nw_out_flush`

`static CURLcode nw_out_flush(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/http2.c:L420-L441][f1]

Drains the filter's network output bufq through the next filter.

Returns CURLE_OK immediately when the buffer is empty. On send failure it propagates the error; CURLE_AGAIN additionally sets ctx->nw_out_blocked so egress loops stop writing until unblocked. If some but not all bytes were written it returns CURLE_AGAIN.

<a id="u-246a29d9782d"></a>
### `Curl_nghttp2_fr_print`

`int Curl_nghttp2_fr_print(const nghttp2_frame *frame, char *buffer, size_t blen)` · [lib/http2.c:L1097-L1166][f1]

Verbose-only frame-to-text formatter.

Produces per-type descriptions of length and flags for DATA, HEADERS, PRIORITY, RST_STREAM, SETTINGS (with ack), PUSH_PROMISE, PING, GOAWAY (including a truncated copy of the opaque debug data), and WINDOW_UPDATE, and a generic numeric form for other types; returns the curl_msnprintf character count.

<a id="u-d556f148562f"></a>
### `http2_handle_stream_close`

`static CURLcode http2_handle_stream_close(struct Curl_cfilter *cf, struct Curl_easy *…` · [lib/http2.c:L1699-L1774][f1]

Turns a closed stream into a transfer result.

On reset: REFUSED_STREAM closes the connection, sets state.refused_stream, and returns CURLE_RECV_ERROR so a retry can be scheduled; a reset after complete headers on a no-body request is tolerated as CURLE_OK with close_handled set; otherwise failf reports who reset the stream and it returns CURLE_HTTP2_STREAM for a nonzero error, CURLE_PARTIAL_FILE if bytes were received, or CURLE_HTTP2. A clean close before any body/header start is CURLE_HTTP2_STREAM. For a normal close with trailers, each trailer is formatted, debug-logged, written as a header/trailer to the client, and its size bumped; any write or size failure aborts and propagates. On success sets close_handled and returns CURLE_OK.

<a id="u-a24c92b4639d"></a>
### `cf_h2_header_error`

`static void cf_h2_header_error(struct Curl_cfilter *cf, struct Curl_easy *data, struc…` · [lib/http2.c:L1403-L1418][f1]

Reports a header reception failure via failf and, when a stream context exists, submits RST_STREAM (NGHTTP2_STREAM_CLOSED) and marks the stream closed and reset.

<a id="u-87b8d7ec4155"></a>
### `Curl_h2_http_1_1_error`

`bool Curl_h2_http_1_1_error(struct Curl_easy *data)` · [lib/http2.c:L2965-L2972][f1]

For a transfer that already got a CURLE_HTTP2_STREAM error on an HTTP/2 connection, returns TRUE only when the connection's stream error equals NGHTTP2_HTTP_1_1_REQUIRED; FALSE otherwise, including on non-h2 connections.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http2.c
