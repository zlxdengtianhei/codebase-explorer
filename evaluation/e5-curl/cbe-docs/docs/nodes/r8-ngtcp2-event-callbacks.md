# ngtcp2 Event Callbacks

**Capability.** Implements the ngtcp2 callback table: stream data delivered to nghttp3, acknowledgements, flow-control and stream-limit updates, stream reset/stop/close (with v1.25+ dual error codes), connection-ID generation, handshake completion, receive-key availability and randomness.

Use this subtree when a QUIC protocol event must trigger library behavior; these callbacks are the bridge from ngtcp2 internals into curl transfer and HTTP/3 state.

Parent: [QUIC via ngtcp2](r8-quic-ngtcp2.md)

## Units (13)

<a id="u-8c3bc4406a79"></a>
### `cb_acked_stream_data_offset`

`static int cb_acked_stream_data_offset(ngtcp2_conn *tconn, int64_t stream_id, uint64_…` · [lib/vquic/cf-ngtcp2-cmn.c:L393-L412][f1]

ngtcp2 callback notifying nghttp3 that stream data was acknowledged.

Calls nghttp3_conn_add_ack_offset; STREAM_NOT_FOUND is tolerated, any other error returns NGTCP2_ERR_CALLBACK_FAILURE, else 0.

<a id="u-22bc09578f2d"></a>
### `cb_extend_max_local_streams_bidi`

`static int cb_extend_max_local_streams_bidi(ngtcp2_conn *tconn, uint64_t max_streams,…` · [lib/vquic/cf-ngtcp2-cmn.c:L522-L536][f1]

ngtcp2 callback reporting a raised bidirectional stream limit.

Stores max_streams into ctx->max_bidi_streams and, when current data is available, traces the new limit against ctx->used_bidi_streams. Always returns 0.

<a id="u-e5a0007fe360"></a>
### `cb_extend_max_stream_data`

`static int cb_extend_max_stream_data(ngtcp2_conn *tconn, int64_t stream_id, uint64_t …` · [lib/vquic/cf-ngtcp2-cmn.c:L538-L562][f1]

ngtcp2 callback on a MAX_STREAM_DATA grant.

Unblocks the stream in nghttp3 (STREAM_NOT_FOUND tolerated, other errors NGTCP2_ERR_CALLBACK_FAILURE). When the resolved stream had quic_flow_blocked set, clears the flag and marks the transfer dirty via Curl_multi_mark_dirty so paused sending resumes.

calls: [Curl_cf_ngtcp2_get_xfer](r8-ngtcp2-h3-streams.md#u-2144d129125f)

<a id="u-6329368dad96"></a>
### `cb_get_new_connection_id2`

`static int cb_get_new_connection_id2( ngtcp2_conn *tconn, ngtcp2_cid *cid, struct ngt…` · [lib/vquic/cf-ngtcp2-cmn.c:L600-L618][f1]

Connection-ID generator for ngtcp2 v1.22+ (NGTCP2_CALLBACKS_V3).

Same behavior as the older variant but writes the reset token into a struct ngtcp2_stateless_reset_token.

<a id="u-4e435fdaa64f"></a>
### `cb_get_new_connection_id`

`static int cb_get_new_connection_id(ngtcp2_conn *tconn, ngtcp2_cid *cid, uint8_t *tok…` · [lib/vquic/cf-ngtcp2-cmn.c:L579-L597][f1]

Connection-ID generator for ngtcp2 < v1.22.

Fills the CID with Curl_rand (failure: NGTCP2_ERR_CALLBACK_FAILURE), sets its length, then fills the stateless reset token; token generation failure also fails the callback.

<a id="u-bb67be94f88a"></a>
### `cb_ngtcp2_handshake_completed`

`static int cb_ngtcp2_handshake_completed(ngtcp2_conn *tconn, void *user_data)` · [lib/vquic/cf-ngtcp2-cmn.c:L272-L352][f1]

ngtcp2 callback run when the TLS handshake completes.

Returns NGTCP2_ERR_CALLBACK_FAILURE if cf->ctx or current data is missing. Records the handshake time, marks TLS complete, reports the handshake, and verifies the peer: a non-zero verify result aborts with NGTCP2_ERR_CALLBACK_FAILURE. Under CURLVERBOSE it logs remote transport params. For early-data connections it reports the APPCONNECT timer once (unless the filter is a proxy), determines earlydata_accepted — via ngtcp2_conn_get_tls_early_data_rejected2 on ngtcp2 >= 0x011700, otherwise per-backend via OpenSSL/GnuTLS/wolfSSL session flags, with wolfSSL without WOLFSSL_EARLY_DATA asserting and treating it as rejected — and reports the sent-or-not early data amount to progress stats. Returns 0 on success.

uses: [Curl_cf_ngtcp2_get_xfer](r8-ngtcp2-h3-streams.md#u-2144d129125f), [get_conn](r8-ngtcp2-errors-tls.md#u-ecc550fdfd50)

**Uncertainties.**

- Whether Curl_pgrsEarlyData's negative amount has further semantics is outside this file.

<a id="u-01a830143438"></a>
### `cb_rand`

`static void cb_rand(uint8_t *dest, size_t destlen, const ngtcp2_rand_ctx *rand_ctx)` · [lib/vquic/cf-ngtcp2-cmn.c:L564-L576][f1]

ngtcp2 randomness callback for non-cryptographic use.

Fills dest via Curl_rand; on failure it logs nothing and memsets dest to zeros, treating that as random by documented design.

<a id="u-8de6137bfe28"></a>
### `cb_recv_rx_key`

`static int cb_recv_rx_key(ngtcp2_conn *tconn, ngtcp2_encryption_level level, void *us…` · [lib/vquic/cf-ngtcp2-cmn.c:L621-L639][f1]

ngtcp2 callback invoked when a receive key becomes available.

Returns 0 immediately unless the level is 1-RTT. On 1-RTT, if there is no h3conn yet and an init_h3_conn_cb is configured, it invokes that callback to create the HTTP/3 connection; a failure returns NGTCP2_ERR_CALLBACK_FAILURE. This defers nghttp3 setup until application traffic can flow.

uses: [Curl_cf_ngtcp2_h3_init_ctrls](r8-ngtcp2-h3-streams.md#u-0f5296e113b1)

**Uncertainties.**

- The concrete init_h3_conn_cb implementation lives outside this file; only the contract is visible here.

<a id="u-0b55e8d26da4"></a>
### `cb_recv_stream_data`

`static int cb_recv_stream_data(ngtcp2_conn *tconn, uint32_t flags, int64_t stream_id,…` · [lib/vquic/cf-ngtcp2-cmn.c:L354-L391][f1]

ngtcp2 callback delivering received stream data to nghttp3.

Derives fin from the STREAM_DATA_FLAG_FIN bit and the owning transfer via Curl_cf_ngtcp2_get_xfer. Feeds the buffer into nghttp3_conn_read_stream; a negative result is logged if the stream is known and returns NGTCP2_ERR_CALLBACK_FAILURE. On success the consumed byte count (framing and QPACK overhead, not DATA payload) extends both stream and connection flow-control windows via ngtcp2_conn_extend_max_stream_offset/extend_max_offset and advances the stream's rx_offset and rx_offset_max when a stream context exists. Returns 0.

calls: [Curl_cf_ngtcp2_get_xfer](r8-ngtcp2-h3-streams.md#u-2144d129125f)

<a id="u-5bf0ec2138cd"></a>
### `cb_stream_close2`

`static int cb_stream_close2(ngtcp2_conn *tconn, uint32_t flags, int64_t stream_id, ui…` · [lib/vquic/cf-ngtcp2-cmn.c:L446-L478][f1]

Replacement for cb_stream_close on ngtcp2 v1.25+ (NGTCP2_CALLBACKS_V5), differing in receiving separate rx/tx app error codes.

Uses the rx error code only when the RX_APP_ERROR_CODE_SET flag is set, else H3_NO_ERROR; ignores tx code. Otherwise identical: resolve transfer (fallback CF_DATA_CURRENT, fail without one), nghttp3_conn_close_stream, tolerate STREAM_NOT_FOUND, otherwise Curl_cf_ngtcp2_h3_err_set plus NGTCP2_ERR_CALLBACK_FAILURE.

calls: [Curl_cf_ngtcp2_h3_err_set](r8-ngtcp2-errors-tls.md#u-4424220abf66)

<a id="u-04fd0d106252"></a>
### `cb_stream_close`

`static int cb_stream_close(ngtcp2_conn *tconn, uint32_t flags, int64_t stream_id, uin…` · [lib/vquic/cf-ngtcp2-cmn.c:L414-L443][f1]

ngtcp2 callback for a closed stream (pre v1.25 variant).

Resolves the transfer, falling back to CF_DATA_CURRENT, and fails with NGTCP2_ERR_CALLBACK_FAILURE if no data is available. If the APP_ERROR_CODE_SET flag is absent the error code becomes NGHTTP3_H3_NO_ERROR. Closes the stream in nghttp3 via nghttp3_conn_close_stream; STREAM_NOT_FOUND is tolerated, any other error is recorded with Curl_cf_ngtcp2_h3_err_set and reported as NGTCP2_ERR_CALLBACK_FAILURE.

calls: [Curl_cf_ngtcp2_h3_err_set](r8-ngtcp2-errors-tls.md#u-4424220abf66)

<a id="u-15674f433ed9"></a>
### `cb_stream_reset`

`static int cb_stream_reset(ngtcp2_conn *tconn, int64_t stream_id, uint64_t final_size…` · [lib/vquic/cf-ngtcp2-cmn.c:L481-L501][f1]

ngtcp2 callback on stream reset.

Shuts down the stream's read side in nghttp3 via nghttp3_conn_shutdown_stream_read, logging the result if a transfer was resolved. STREAM_NOT_FOUND tolerated; other errors return NGTCP2_ERR_CALLBACK_FAILURE. final_size and app_error_code ignored.

<a id="u-29f76824a6f2"></a>
### `cb_stream_stop_sending`

`static int cb_stream_stop_sending(ngtcp2_conn *tconn, int64_t stream_id, uint64_t app…` · [lib/vquic/cf-ngtcp2-cmn.c:L503-L520][f1]

ngtcp2 callback when the peer sends STOP_SENDING.

Shuts down the stream's read side in nghttp3; STREAM_NOT_FOUND tolerated, other errors return NGTCP2_ERR_CALLBACK_FAILURE. No transfer lookup or logging.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-ngtcp2-cmn.c
