# HTTP/3 CONNECT tunnel

**Capability.** Implements the CONNECT tunnel over HTTP/3: per-tunnel stream state and its state machine, request composition and submission, response inspection, and the nghttp3 callback table driving the tunnel stream.

Read this to follow a proxy CONNECT from cf_h3_proxy_connect through the tunnel state machine to the response; the h3 callbacks table wires all nghttp3 events, with NULLs for events this tunnel ignores.

**Depends on.**

- [H3 proxy connection filter](r4-quic-connection-filter.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [H3 proxy connection filter](r4-quic-connection-filter.md) · model-inferred · 0 edge(s)

Parent: [QUIC/HTTP3 proxy filter stack](r4-quic-proxy-stack.md)

## Units (21)

<a id="u-c82dfb0ca0cb"></a>
### `cf-ngtcp2-proxy-h3-callbacks-table`

`group` · [lib/vquic/cf-ngtcp2-proxy.c:L591-L628][f1]

Static nghttp3_callbacks instance wiring the tunnel callbacks: acked data, stream close, recv data, deferred consume, recv header, end headers (also as trailer end), stop sending, and reset stream; begin_headers, begin/end_trailers, end_stream, shutdown, and settings callbacks are NULL, so those nghttp3 events carry no action here.

Optional v2–v4 entries are NULL behind version macros, and missing-field-initializer warnings are suppressed around the initializer.

uses: [cb_h3_proxy_recv_header](r4-h3-proxy-tunnel.md#u-847522b867e0)

**Uncertainties.**

- Version-gated macro availability (NGHTTP3_CALLBACKS_V2/V3/V4) depends on the nghttp3 build, not this file.

<a id="u-0fbb90842b32"></a>
### `cb_h3_proxy_acked_req_body`

`static int cb_h3_proxy_acked_req_body(nghttp3_conn *conn, int64_t stream_id, uint64_t…` · [lib/vquic/cf-ngtcp2-proxy.c:L202-L234][f1]

nghttp3 callback for acknowledged request-body bytes on the tunnel stream; events for other streams are ignored (return 0).

It skips the ACKed delta (clamped to tx_in_flight_size) from the stream sendbuf and decreases tx_in_flight_size. When un-ACKed buffered data exceeds the in-flight amount, it resumes the stream; any nghttp3_conn_resume_stream error other than NGHTTP3_ERR_STREAM_NOT_FOUND returns NGHTTP3_ERR_CALLBACK_FAILURE.

contract: [cb_h3_tunnel_read_data](r4-h3-proxy-tunnel.md#u-ae132d09768b)

<a id="u-8ba148cbb9df"></a>
### `cb_h3_proxy_deferred_consume`

`static int cb_h3_proxy_deferred_consume(nghttp3_conn *conn, int64_t stream_id, size_t…` · [lib/vquic/cf-ngtcp2-proxy.c:L348-L367][f1]

nghttp3 callback reporting bytes nghttp3 consumed on a QUIC stream; extends both the stream and connection ngtcp2 flow-control offsets by that amount.

Returns 0 when the ngtcp2 context is absent.

<a id="u-ecb0aeb0b1d9"></a>
### `cb_h3_proxy_end_headers`

`static int cb_h3_proxy_end_headers(nghttp3_conn *conn, int64_t stream_id, int fin, vo…` · [lib/vquic/cf-ngtcp2-proxy.c:L436-L475][f1]

nghttp3 end-of-headers callback.

Missing easy handle fails the callback; unknown streams log and return 0. When the status class is not 1xx it sets pctx->tunnel.has_final_response and marks stream->resp_hds_complete, so 1xx informational responses leave the tunnel waiting for the final one. Marks the transfer dirty before returning.

<a id="u-2efb4eba3a54"></a>
### `cb_h3_proxy_recv_data`

`static int cb_h3_proxy_recv_data(nghttp3_conn *conn, int64_t stream3_id, const uint8_…` · [lib/vquic/cf-ngtcp2-proxy.c:L306-L346][f1]

nghttp3 callback delivering tunnel response DATA.

Missing easy handle, missing stream, or stream-id mismatch returns NGHTTP3_ERR_CALLBACK_FAILURE. It accumulates rx_total, writes all bytes into the tunnel recvbuf — an error or short write returns NGHTTP3_ERR_CALLBACK_FAILURE so nghttp3 redelivers — advances rx_offset (raising rx_offset_max as needed), then extends the rx window via cf_h3_proxy_upd_rx_win and marks the transfer dirty.

calls: [cf_h3_proxy_upd_rx_win](r4-quic-connection-filter.md#u-cd0b3e805a9e)

<a id="u-847522b867e0"></a>
### `cb_h3_proxy_recv_header`

`static int cb_h3_proxy_recv_header(nghttp3_conn *conn, int64_t stream_id, int32_t tok…` · [lib/vquic/cf-ngtcp2-proxy.c:L369-L434][f1]

nghttp3 header callback for the tunnel response, also registered for trailers.

No easy handle fails the callback; an unknown stream logs and returns 0; once has_final_response is set, everything is ignored as trailers. For the :status pseudo-header it decodes the status into the stream and builds an http_resp replacing any previous tunnel response. Any other header requires an existing tunnel response (otherwise callback failure) and is appended to its headers; decode/add errors fail the callback.

contract: [cb_h3_proxy_end_headers](r4-h3-proxy-tunnel.md#u-ecb0aeb0b1d9)

<a id="u-fb14bd1e91e8"></a>
### `cb_h3_proxy_reset_stream`

`static int cb_h3_proxy_reset_stream(nghttp3_conn *conn, int64_t stream_id, uint64_t a…` · [lib/vquic/cf-ngtcp2-proxy.c:L499-L527][f1]

nghttp3 callback for a stream reset.

Missing easy handle fails the callback; non-tunnel streams are ignored. It shuts down the write side of the QUIC stream with the app error code, detaches pctx->tunnel.stream, marks the tunnel closed, and treats errors other than NGTCP2_ERR_STREAM_NOT_FOUND as callback failure.

<a id="u-157126f2c7f6"></a>
### `cb_h3_proxy_stop_sending`

`static int cb_h3_proxy_stop_sending(nghttp3_conn *conn, int64_t stream_id, uint64_t a…` · [lib/vquic/cf-ngtcp2-proxy.c:L477-L497][f1]

nghttp3 callback for STOP_SENDING on a stream; asks ngtcp2 to shut down reading of that stream with the app error code.

Errors other than NGTCP2_ERR_STREAM_NOT_FOUND return NGHTTP3_ERR_CALLBACK_FAILURE; a missing ngtcp2 context is silently tolerated.

<a id="u-8f5f6c78728a"></a>
### `cb_h3_proxy_stream_close`

`static int cb_h3_proxy_stream_close(nghttp3_conn *conn, int64_t stream_id, uint64_t a…` · [lib/vquic/cf-ngtcp2-proxy.c:L236-L268][f1]

nghttp3 callback when the peer closes the tunnel stream.

Without a current easy handle it returns NGHTTP3_ERR_CALLBACK_FAILURE; other streams are ignored. Sets stream closed with error3 from the app error code; a code other than NGHTTP3_H3_NO_ERROR additionally marks reset and send_closed and logs RESET, otherwise logs CLOSED. It detaches pctx->tunnel.stream, sets pctx->tunnel.closed, and marks the transfer dirty so the multi loop revisits it.

<a id="u-ae132d09768b"></a>
### `cb_h3_tunnel_read_data`

`static nghttp3_ssize cb_h3_tunnel_read_data(nghttp3_conn *conn, int64_t stream_id, ng…` · [lib/vquic/cf-ngtcp2-proxy.c:L529-L591][f1]

nghttp3 data reader supplying the CONNECT request body from the stream sendbuf.

Missing easy handle or stream mismatch returns NGHTTP3_ERR_CALLBACK_FAILURE. Bytes already handed to nghttp3 but unACKed are tracked in tx_in_flight_size; the reader peeks sendbuf chunks beyond that offset into output vectors, advancing tx_in_flight_size per chunk. If nothing can be given it returns NGHTTP3_ERR_WOULDBLOCK (not EOF), so upload pauses until ACKs free more credit.

contract: [cb_h3_proxy_acked_req_body](r4-h3-proxy-tunnel.md#u-0fbb90842b32)

**Uncertainties.**

- EOF signaling relies on *pflags, which this function never sets; it only logs whether EOF is already flagged, so who sets EOF is not visible here.

<a id="u-32c83cbf45de"></a>
### `cf_h3_proxy_connect`

`static CURLcode cf_h3_proxy_connect(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/vquic/cf-ngtcp2-proxy.c:L1149-L1179][f1]

Filter connect: first runs the common ngtcp2 connect; its error or an incomplete connect exits early.

Once QUIC is up, saves call data and drives cf_h3_proxy_tunnel for the proxy CONNECT. When done, marks the filter connected, soft-resets the request state (the real request follows the CONNECT), and resets the client; call data is restored when it was saved.

calls: [cf_h3_proxy_tunnel](r4-h3-proxy-tunnel.md#u-7e01402249ef)

**Uncertainties.**

- Curl_cf_ngtcp2_cmn_connect's *done semantics come from the shared module, not this file.

<a id="u-ef3149511ed3"></a>
### `cf_h3_proxy_inspect_response`

`static CURLcode cf_h3_proxy_inspect_response(struct Curl_cfilter *cf, struct Curl_eas…` · [lib/vquic/cf-ngtcp2-proxy.c:L1048-L1073][f1]

Interprets the received CONNECT response through Curl_http_proxy_inspect_tunnel_response (its error propagates directly).

PROXY_INSPECT_OK advances the tunnel to ESTABLISHED; PROXY_INSPECT_FAILED moves it to FAILED and returns CURLE_COULDNT_CONNECT; PROXY_INSPECT_AUTH_RETRY returns the tunnel to INIT for a fresh attempt.

calls: [h3_tunnel_go_state](r4-h3-proxy-tunnel.md#u-378ea191ea29)

**Uncertainties.**

- Behavior for any proxy_inspect_result value outside the three handled cases is not coded here; the switch has no default.

<a id="u-04a7ba395a32"></a>
### `cf_h3_proxy_submit`

`static CURLcode cf_h3_proxy_submit(struct Curl_cfilter *cf, struct Curl_easy *data, s…` · [lib/vquic/cf-ngtcp2-proxy.c:L884-L979][f1]

Builds and submits the CONNECT request on a new bidirectional QUIC stream.

Converts the HTTP request to h2 headers (errors propagate), sets up an h3 stream context, and packs headers into nghttp3_nv entries (allocation failure is CURLE_OUT_OF_MEMORY). Opens a bidi stream — failure is CURLE_SEND_ERROR after failf — assigns the id, attaches it to the tunnel stream, and counts it in used_bidi_streams. For CONNECT-UDP the request stream stays open (send_closed 0) with the read-data callback as reader. Request submission failure is CURLE_SEND_ERROR with distinct logging for a closing connection. Headers and the nv array are always freed.

uses: [cb_h3_tunnel_read_data](r4-h3-proxy-tunnel.md#u-ae132d09768b)

<a id="u-5b1362c2faac"></a>
### `cf_h3_proxy_submit_CONNECT`

`static CURLcode cf_h3_proxy_submit_CONNECT(struct Curl_cfilter *cf, struct Curl_easy …` · [lib/vquic/cf-ngtcp2-proxy.c:L1025-L1046][f1]

Composes the CONNECT request for the tunnel via Curl_http_proxy_create_tunnel_request (with the proxy TLS peer, tunnel destination, H3 proxy version, and UDP flag), replaces the request reader with a null reader, then submits it with cf_h3_proxy_submit.

The request is always freed; any failure additionally failfs 'Failed sending CONNECT to proxy'.

calls: [cf_h3_proxy_submit](r4-h3-proxy-tunnel.md#u-04a7ba395a32)

<a id="u-7e01402249ef"></a>
### `cf_h3_proxy_tunnel`

`static CURLcode cf_h3_proxy_tunnel(struct Curl_cfilter *cf, struct Curl_easy *data, s…` · [lib/vquic/cf-ngtcp2-proxy.c:L1075-L1147][f1]

Non-blocking state machine driving the CONNECT tunnel, looping while state is INIT.

From INIT it submits CONNECT, moves to CONNECT, and progresses egress. In CONNECT it progresses ingress then egress: a non-AGAIN egress error moves the tunnel to FAILED; once a final response is seen it advances to RESPONSE, otherwise it returns OK to wait for the multi interface. In RESPONSE it inspects the response and marks the context connected. ESTABLISHED sets *pdone TRUE and returns OK; FAILED returns CURLE_RECV_ERROR. At the common exit, any error other than CURLE_AGAIN or a closed tunnel forces state FAILED.

calls: [cf_h3_proxy_submit_CONNECT](r4-h3-proxy-tunnel.md#u-5b1362c2faac), [cf_h3_proxy_inspect_response](r4-h3-proxy-tunnel.md#u-ef3149511ed3)

**Uncertainties.**

- The final FALLTHROUGH from CONNECT's out-path and the do/while re-loop condition (state == H3_TUNNEL_INIT) interact with inspect's AUTH_RETRY transition; whether a retry re-runs in the same call depends on that transition landing back in INIT, which the loop then re-enters.

<a id="u-51721e165bd7"></a>
### `cf_ngtcp2_proxy_h3_init`

`static CURLcode cf_ngtcp2_proxy_h3_init(struct Curl_cfilter *cf, struct Curl_easy *da…` · [lib/vquic/cf-ngtcp2-proxy.c:L629-L653][f1]

Sets up HTTP/3 on an established QUIC connection for the proxy.

If fewer than 3 unidirectional streams remain it fails with CURLE_QUIC_CONNECT_ERROR. It initializes default nghttp3 settings, creates an nghttp3 client connection with the proxy callbacks (failure maps to CURLE_OUT_OF_MEMORY after a failf), and finishes with Curl_cf_ngtcp2_h3_init_ctrls whose result is propagated.

uses: [cf-ngtcp2-proxy-h3-callbacks-table](r4-h3-proxy-tunnel.md#u-c82dfb0ca0cb)

<a id="u-378ea191ea29"></a>
### `h3_tunnel_go_state`

`static void h3_tunnel_go_state(struct Curl_cfilter *cf, struct h3_tunnel_stream *ts, …` · [lib/vquic/cf-ngtcp2-proxy.c:L113-L165][f1]

Moves a tunnel stream between state-machine states with per-state side effects; a no-op if already in the target state.

Leaving H3_TUNNEL_CONNECT clears data->req.ignorebody. Entering H3_TUNNEL_INIT logs and resets the stream. CONNECT and RESPONSE only set the state. Entering H3_TUNNEL_ESTABLISHED logs 'CONNECT[-UDP] phase completed', marks data->state.authproxy done with multipass FALSE, and frees data->req.hd_proxy_auth. Entering H3_TUNNEL_FAILED likewise frees hd_proxy_auth so proxy credentials cannot leak into the document request.

calls: [h3_tunnel_stream_reset](r4-h3-proxy-tunnel.md#u-76103487cbb7)

**Uncertainties.**

- Semantics of data->req and data->state.authproxy fields are assumed from usage; their definitions are outside this file.

<a id="u-2ce926c6dd95"></a>
### `h3_tunnel_stream_cleanup`

`static void h3_tunnel_stream_cleanup(struct h3_tunnel_stream *ts)` · [lib/vquic/cf-ngtcp2-proxy.c:L104-L111][f1]

Tears down a tunnel stream: unlinks the dest peer, frees the recvbuf and response, frees the authority string, and leaves the state at H3_TUNNEL_INIT.

<a id="u-494fe532bc7f"></a>
### `h3_tunnel_stream_init`

`static CURLcode h3_tunnel_stream_init(struct h3_tunnel_stream *ts, struct Curl_peer *…` · [lib/vquic/cf-ngtcp2-proxy.c:L73-L91][f1]

Initializes a tunnel stream: state H3_TUNNEL_INIT, links the dest peer, creates recvbuf with soft-limit chunks, stores the udp flag, and formats authority as host:port with IPv6 brackets.

Returns CURLE_OUT_OF_MEMORY if authority formatting fails, else CURLE_OK.

uses: [h3_tunnel_stream](r4-h3-proxy-tunnel.md#u-ec21459470be)

<a id="u-76103487cbb7"></a>
### `h3_tunnel_stream_reset`

`static void h3_tunnel_stream_reset(struct h3_tunnel_stream *ts)` · [lib/vquic/cf-ngtcp2-proxy.c:L93-L102][f1]

Resets a tunnel stream for reuse: clears recvbuf, frees and NULLs the response, detaches the stream context, clears has_final_response and closed, and returns state to H3_TUNNEL_INIT.

<a id="u-ec21459470be"></a>
### `h3_tunnel_stream`

`struct h3_tunnel_stream` · [lib/vquic/cf-ngtcp2-proxy.c:L61-L71][f1]

Holds per-tunnel state for one HTTP/3 proxy CONNECT: the tunnel destination peer, parsed response, a recvbuf for proxy response DATA, an authority host:port string, the active h3 stream context, the state-machine state, and udp/has_final_response/closed flags.

**Notes.**

- field: recvbuf is sized from PROXY_H3_TUNNEL_RX_WIN (512 KiB) with soft limit; the udp flag selects CONNECT-UDP semantics.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-ngtcp2-proxy.c
