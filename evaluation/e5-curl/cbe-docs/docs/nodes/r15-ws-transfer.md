# WS transfer API and filters

**Capability.** Public curl_ws_* API including disabled-build stubs, upgrade request and 101 handling, the ws-decode client writer and ws-encode client reader, raw send helpers, flushing, frame metadata exposure, and connection setup.

Consumers of the frame codec: recv drives ws_dec_pass over bufq input; send/start_frame drive ws_enc_send and ws_enc_write_head. Flush paths choose blocking versus transfer-aware send modes.

**Depends on.**

- [Bufq public API](r15-bufq-stream-api.md) · graph-confirmed · 17 edge(s)
- [Trace and Debug Logging](r1-trace-logging.md) · graph-only · 41 edge(s)

Parent: [WebSocket support](r15-ws-protocol.md)

## Units (22)

<a id="u-e4a7dd95f716"></a>
### `ws_cntrl_frame`

`struct ws_cntrl_frame` · [lib/ws.c:L109-L113][f1]

Stores one pending outgoing control frame: its CURLWS type and up to 125 payload bytes.

**Notes.**

- field: WS_MAX_CNTRL_LEN (125) bounds control payloads per RFC 6455 5.5; only one pending control frame is kept at a time.

<a id="u-84d93de90d9b"></a>
### `websocket`

`struct websocket` · [lib/ws.c:L117-L127][f1]

Per-connection WebSocket state combining encoder, decoder, raw network buffers, received-frame metadata and one pending control frame.

**Notes.**

- field: recvbuf buffers raw server bytes, sendbuf raw encoded bytes; sendbuf_payload counts unflushed payload bytes; using_reader selects the client-reader send path instead of ws_enc_send; recvframe mirrors curl_ws_frame metadata for callers.

<a id="u-be7bb0143d4d"></a>
### `Curl_ws_request`

`CURLcode Curl_ws_request(struct Curl_easy *data, struct dynbuf *req)` · [lib/ws.c:L1309-L1364][f1]

Builds the WebSocket upgrade request headers: Upgrade: websocket, Sec-WebSocket-Version: 13, and a Sec-WebSocket-Key from 16 random bytes base64-encoded.

**Notes.**

- failure: Random generation or base64 encoding failures propagate; an oversized encoded key frees the string and returns CURLE_FAILED_INIT. Each header is added only when the user has not set it (Curl_checkheaders).
- side_effect: Sets http_hd_upgrade, k->upgr101 to UPGR101_WS and the connection upgrade_in_progress bit.

<a id="u-3c95253f4ef3"></a>
### `Curl_ws_accept`

`CURLcode Curl_ws_accept(struct Curl_easy *data, const char *mem, size_t nread)` · [lib/ws.c:L1380-L1517][f1]

Handles the 101 Switching: creates or resets the per-connection websocket state and installs the ws-decode writer (and, for PUT uploads in non-raw mode, the ws-encode reader).

**Notes.**

- side_effect: On first use it allocates the websocket, sizes recvbuf/sendbuf (chunk size overridable via CURL_WS_CHUNK_SIZE in debug builds), initializes decoder/encoder and registers connection metadata with ws_conn_dtor as destructor (which frees both bufqs and the struct); on reuse it resets recvbuf, decoder and encoder. k->header is cleared and upgr101 set to UPGR101_RECEIVED.
- condition: In connect-only mode, already-received bytes are pushed to the connection-level recvbuf and content reading is stopped. For PUT uploads it switches to the fread reader, adds the ws-encode reader unless raw mode, resets eos_read/upload_done and re-enables sending. Otherwise any payload bytes in mem are passed to the client writers.
- failure: Allocation, metadata set, writer/reader creation or data processing failures jump to cleanup, freeing not-yet-owned writers/readers and returning the error.

**Uncertainties.**

- The Sec-WebSocket-Accept verification and extension/subprotocol checks exist only as comments; no such validation is implemented in this function.

<a id="u-3ea16a32855c"></a>
### `cr_ws_read`

`static CURLcode cr_ws_read(struct Curl_easy *data, struct Curl_creader *reader, char …` · [lib/ws.c:L1196-L1279][f1]

ws-encode client reader: pulls data from the next reader and converts it into masked WS BINARY frames buffered in the websocket sendbuf; cr_ws_ctx tracks EOS propagation, cr_ws_init and cr_ws_close are no-ops, and cr_ws_total_length always returns -1 because output length varies with input.

**Notes.**

- condition: After its own EOS was returned, subsequent reads return eos immediately. When the sendbuf is empty, it reads from the next reader (clamping blen to the current frame's payload_remain); if client_read started a new frame, a reported EOS is discarded and cleared on the next reader. Data is encoded as a new BINARY frame when no frame is ongoing, otherwise appended to the current frame.
- failure: Missing websocket metadata returns CURLE_FAILED_INIT; encode errors propagate; if the next reader gives no data, that result and EOS state are returned directly.
- condition: With buffered encoded data it copies out of the sendbuf and reports EOS once the sendbuf drains and the next reader signaled EOS.

calls: [ws_enc_write_head](r15-ws-frame-codec.md#u-be00a9a6c533), [ws_enc_write_payload](r15-ws-frame-codec.md#u-2e3a35ddda4c)

<a id="u-7fa2b9b27988"></a>
### `curl_ws_meta`

`const struct curl_ws_frame *curl_ws_meta(CURL *curl)` · [lib/ws.c:L1948-L1961][f1]

Returns the current received-frame metadata, but only for a valid easy handle inside a callback, with a connection and non-raw mode; otherwise NULL.

<a id="u-856ff6027e22"></a>
### `lib/ws.c:curl_ws_meta`

`const struct curl_ws_frame *curl_ws_meta(CURL *data)` · [lib/ws.c:L2060-L2064][f1]

Disabled-build stub that always returns NULL.

<a id="u-3ee296e6f5b1"></a>
### `curl_ws_recv`

`CURLcode curl_ws_recv(CURL *curl, void *buffer, size_t buflen, size_t *recv, const st…` · [lib/ws.c:L1596-L1704][f1]

Public receive API for WebSocket transfers: decodes frames from the connection into the caller's buffer, returning frame metadata and a byte count; nw_in_recv feeds it by wrapping Curl_easy_recv.

**Notes.**

- failure: NULL recv/metap or non-NULL buflen with NULL buffer fails with CURLE_BAD_FUNCTION_ARGUMENT. Without a connection, non-connect-only transfers fail with CURLE_UNSUPPORTED_PROTOCOL; connect-only resolves the connection via Curl_getconnectinfo or fails. Missing websocket metadata fails with CURLE_BAD_FUNCTION_ARGUMENT.
- condition: When recvbuf is empty it slurps more network data; a 0-byte read reports the connection as closed (CURLE_GOT_NOTHING). The decode loop retries while nothing was written and input is needed, breaks once bytes were delivered or a frame was auto-answered, and propagates other errors. Afterwards metadata is published, and in non-raw, non-reader mode any pending control frame is encoded and flushed opportunistically.

calls: [ws_dec_pass](r15-ws-frame-codec.md#u-980f6d341c15), [ws_enc_add_pending](r15-ws-frame-codec.md#u-d813613d24c0), [ws_flush](r15-ws-transfer.md#u-f737bbffdfa5)

<a id="u-9622fea2190f"></a>
### `lib/ws.c:curl_ws_recv`

`CURLcode curl_ws_recv(CURL *curl, void *buffer, size_t buflen, size_t *recv, const st…` · [lib/ws.c:L2034-L2044][f1]

Disabled-build stub that returns CURLE_NOT_BUILT_IN without touching its arguments.

<a id="u-342c291f6843"></a>
### `curl_ws_send`

`CURLcode curl_ws_send(CURL *curl, const void *buffer_arg, size_t buflen, size_t *sent…` · [lib/ws.c:L1855-L1935][f1]

Public WebSocket send API that validates arguments, attaches connect-only connections, and dispatches to raw sending or frame encoding via ws_enc_send.

**Notes.**

- failure: NULL buffer with non-zero buflen, or missing raw-mode buffer/sent pointers, or non-zero fragsize/flags in raw mode, each fails with CURLE_BAD_FUNCTION_ARGUMENT. No connection yields CURLE_SEND_ERROR (after a connect-only attach attempt); a non-websocket transfer yields CURLE_SEND_ERROR.
- condition: In raw mode pending data is flushed non-blocking first and the buffer is sent raw; otherwise ws_enc_send performs frame encoding with the caller's fragsize/flags.

calls: [ws_enc_send](r15-ws-frame-codec.md#u-ae44569caff2), [ws_send_raw](r15-ws-transfer.md#u-166d89d092fa)

<a id="u-d46670a3f0e9"></a>
### `lib/ws.c:curl_ws_send`

`CURLcode curl_ws_send(CURL *curl, const void *buffer, size_t buflen, size_t *sent, cu…` · [lib/ws.c:L2046-L2058][f1]

Disabled-build stub that returns CURLE_NOT_BUILT_IN without touching its arguments.

<a id="u-45132ef219cb"></a>
### `curl_ws_start_frame`

`CURL_EXTERN CURLcode curl_ws_start_frame(CURL *curl, unsigned int flags, curl_off_t f…` · [lib/ws.c:L1963-L2010][f1]

Starts a new outgoing frame of the given length and flags without yet supplying payload, rejecting raw mode and unfinished previous frames.

**Notes.**

- failure: Raw mode fails with CURLE_FAILED_INIT; no connection or non-websocket transfer, or a previous frame still with payload_remain, each fail with CURLE_SEND_ERROR. Head-encoding errors from ws_enc_write_head propagate.

calls: [ws_enc_write_head](r15-ws-frame-codec.md#u-be00a9a6c533)

<a id="u-c9967900e1d7"></a>
### `lib/ws.c:curl_ws_start_frame`

`CURL_EXTERN CURLcode curl_ws_start_frame(CURL *curl, unsigned int flags, curl_off_t f…` · [lib/ws.c:L2066-L2074][f1]

Disabled-build stub that returns CURLE_NOT_BUILT_IN without touching its arguments.

<a id="u-73e9a61d09fe"></a>
### `update_meta`

`static void update_meta(struct websocket *ws, int frame_age, int frame_flags, curl_of…` · [lib/ws.c:L575-L588][f1]

Writes frame age, flags, offset, delivered length and computed bytesleft into ws->recvframe for caller-visible metadata.

<a id="u-97f11a88f242"></a>
### `ws_client_collect`

`static CURLcode ws_client_collect(const uint8_t *buf, size_t buflen, int frame_age, i…` · [lib/ws.c:L1532-L1586][f1]

Decoder payload callback for curl_ws_recv: copies decoded bytes into the caller's buffer, records frame metadata on first write, and auto-answers completed PINGs with PONGs instead of returning them; the ws_collect struct is its context.

**Notes.**

- condition: remain < 0 (parameter mismatch) returns CURLE_BAD_FUNCTION_ARGUMENT. For a complete PING with auto-pong enabled, the payload is staged as a PONG and marked consumed without copying. Otherwise bytes are copied up to the remaining caller buffer space: a 0-length write is accepted, and no space returns CURLE_AGAIN so curl_ws_recv can return what it has.

calls: [ws_enc_add_cntrl](r15-ws-frame-codec.md#u-feef7167209b)

<a id="u-e7f4484f0c8e"></a>
### `ws_cw_dec_next`

`static CURLcode ws_cw_dec_next(const uint8_t *buf, size_t buflen, int frame_age, int …` · [lib/ws.c:L656-L701][f1]

Decoder payload callback for the client-writer path: auto-answers completed PING frames with an echoing PONG, otherwise forwards decoded bytes to the next client writer with updated frame metadata.

**Notes.**

- condition: Auto-pong applies only when not raw mode and auto-pong is enabled, for a fully received single-frame PING; otherwise non-empty data or a complete zero-length frame is forwarded via Curl_cwriter_write with CLIENTWRITE_0LEN so 0-length frames reach the client. Partial payloads write nothing yet.
- failure: ws_payload_remain < 0 (parameter mismatch) returns CURLE_BAD_FUNCTION_ARGUMENT; pong staging or writer errors propagate.

calls: [ws_enc_add_cntrl](r15-ws-frame-codec.md#u-feef7167209b)

<a id="u-97f3339bd110"></a>
### `ws_cw_flush`

`static CURLcode ws_cw_flush(struct Curl_easy *data, struct Curl_cwriter *writer)` · [lib/ws.c:L771-L820][f1]

Flush-time decoding for the ws-decode writer; in non-raw mode it flushes the next writer first, drains its bufq through the decoder with CLIENTWRITE_BODY, then flushes the next writer again.

**Notes.**

- condition: In raw mode it only flushes the next writer. AGAIN from decoding keeps data buffered and is reported as success; other decode errors reset the buffer and propagate; missing websocket metadata yields CURLE_FAILED_INIT.

<a id="u-550ce50e837b"></a>
### `ws_cw_write`

`static CURLcode ws_cw_write(struct Curl_easy *data, struct Curl_cwriter *writer, int …` · [lib/ws.c:L703-L769][f1]

ws-decode client writer: buffers body bytes, drives the frame decoder toward the next writer, and flushes encoded sends afterward; ws_cw_init sizes its internal bufq (WS_CHUNK_SIZE, soft limit), ws_cw_close frees it, and ws_cw_dec_ctx carries data/ws/next-writer/type to the payload callback.

**Notes.**

- condition: Non-body data or raw-mode input bypasses decoding and goes straight to the next writer. Body bytes are appended to ctx->buf; after flushing the next writer, ws_dec_pass with ws_cw_dec_next runs while data remains and the writer is not paused. CURLE_AGAIN from decoding is reported as success because a copy is retained; other errors reset the buffer and are returned.
- side_effect: After decoding, when the transfer does not use the reader path, ws_flush is invoked (blocking when inside a callback) with AGAIN treated as success.
- failure: EOS with data still buffered or a frame mid-decode fails with CURLE_RECV_ERROR.
- failure: Missing connection websocket metadata fails with CURLE_FAILED_INIT; a bufq write error is logged and returned.

calls: [ws_dec_pass](r15-ws-frame-codec.md#u-980f6d341c15), [ws_flush](r15-ws-transfer.md#u-f737bbffdfa5)

**Uncertainties.**

- ws_cw_dec_next is invoked via a function pointer by ws_dec_pass, not directly.

<a id="u-f737bbffdfa5"></a>
### `ws_flush`

`static CURLcode ws_flush(struct Curl_easy *data, struct websocket *ws, bool blocking)` · [lib/ws.c:L1706-L1770][f1]

Sends buffered encoded frames, first staging any pending control frame when there is room, and choosing a blocking, senddata or xfer send path per call context.

**Notes.**

- condition: When sendbuf is below one chunk, ws_enc_add_pending runs (AGAIN tolerated). For each buffered segment: blocking mode uses ws_send_raw_blocking; connect-only or in-callback sends use Curl_senddata; otherwise Curl_xfer_send with a 0-byte result on non-empty data treated as CURLE_AGAIN. AGAIN and errors return immediately, leaving the rest buffered; success skips the flushed bytes and continues. Debug builds can simulate EAGAIN after CURL_WS_CHUNK_EAGAIN bytes.

<a id="u-166d89d092fa"></a>
### `ws_send_raw`

`static CURLcode ws_send_raw(struct Curl_easy *data, const void *buffer, size_t buflen…` · [lib/ws.c:L1816-L1853][f1]

Raw-mode send helper that first flushes pending encoded data, then sends the buffer blocking inside callbacks or via Curl_senddata otherwise.

**Notes.**

- condition: Inside a callback it flushes blocking and then sends blocking, reporting full length on success, because callbacks may not handle partial writes; otherwise it flushes non-blocking and uses Curl_senddata for possibly partial writes. A zero length returns OK without sending; missing websocket metadata fails with CURLE_SEND_ERROR.

<a id="u-693da6cd8ac1"></a>
### `ws_send_raw_blocking`

`static CURLcode ws_send_raw_blocking(struct Curl_easy *data, struct websocket *ws, co…` · [lib/ws.c:L1772-L1814][f1]

Sends a raw buffer fully, retrying partial sends while polling the socket for writability within the remaining time limit.

**Notes.**

- failure: No data returns OK immediately. Send errors propagate. On partial sends, an expired time limit or a bad socket returns CURLE_SEND_ERROR; a SOCKET_WRITABLE error also returns CURLE_SEND_ERROR.

**Uncertainties.**

- The timeout when left_ms is 0 falls back to 500 ms; the rationale for that constant is not evident from source.

<a id="u-603736510cdf"></a>
### `ws_setup_conn`

`static CURLcode ws_setup_conn(struct Curl_easy *data, struct connectdata *conn)` · [lib/ws.c:L1937-L1946][f1]

Restricts the connection to HTTP/1.x (disabling 0.9 and 1.0-only negotiation) and delegates to Curl_http_setup_conn.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/ws.c
