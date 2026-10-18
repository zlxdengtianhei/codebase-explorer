# H3 proxy connection filter

**Capability.** The Curl_cftype surface of the H3-PROXY filter: filter context allocation, creation/insertion into the filter chain, pollset adjustment, data-pending reporting and the send/recv paths over QUIC flow control.

Use this node for the filter's lifecycle and I/O interface: how the filter is created and inserted above the UDP sub-chain, how send buffers egress and recv consumes response data with receive-window updates.

**Depends on.**

- [HTTP/3 CONNECT tunnel](r4-h3-proxy-tunnel.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [HTTP/3 CONNECT tunnel](r4-h3-proxy-tunnel.md) · model-inferred · 0 edge(s)
- [QUIC/HTTP3 proxy filter stack](r4-quic-proxy-stack.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r4-quic-proxy-stack ` → ` r4-quic-connection-filter `)

Parent: [QUIC/HTTP3 proxy filter stack](r4-quic-proxy-stack.md)

## Units (13)

<a id="u-235a696250d8"></a>
### `cf-ngtcp2-proxy-cft-vtable`

`group` · [lib/vquic/cf-ngtcp2-proxy.c:L1204-L1222][f1]

The Curl_cftype instance 'H3-PROXY' for this filter, typed IP_CONNECT|PROXY|SSL at log level NONE.

It binds destroy, connect, shutdown, adjust_pollset, data_pending, send, and recv to the local cf_h3_proxy_* functions; control and keep-alive use the generic defaults, while is-alive and query delegate to the shared ngtcp2 implementations. This table is what makes the preceding functions reachable as a connection filter.

uses: [cf_h3_proxy_connect](r4-h3-proxy-tunnel.md#u-32c83cbf45de)

<a id="u-ce5466565bfe"></a>
### `cf-ngtcp2-proxy-ctx`

`struct cf_h3_proxy_ctx` · [lib/vquic/cf-ngtcp2-proxy.c:L167-L171][f1]

The proxy filter context wraps a generic ngtcp2 context, one h3_tunnel_stream, and a connected flag; instances are zero-allocated by creators.

cf_h3_proxy_ctx_init initializes the ngtcp2 context with cf_ngtcp2_proxy_h3_init as its H3 setup hook, then initializes the tunnel stream for the tunnel peer, treating the transport as UDP when TRNSPRT_IS_DGRAM holds; the first failing step's error is returned. cf_h3_proxy_ctx_free is NULL-safe: it cleans the ngtcp2 context, cleans the tunnel stream, and frees the context.

calls: [h3_tunnel_stream_init](r4-h3-proxy-tunnel.md#u-494fe532bc7f), [h3_tunnel_stream_cleanup](r4-h3-proxy-tunnel.md#u-2ce926c6dd95)

**Uncertainties.**

- Curl_cf_ngtcp2_ctx_init and TRNSPRT_IS_DGRAM semantics come from headers not shown.

<a id="u-b0d9dd77ca82"></a>
### `Curl_cf_ngtcp2_proxy_create`

`CURLcode Curl_cf_ngtcp2_proxy_create(struct Curl_cfilter **pcf, struct Curl_easy *dat…` · [lib/vquic/cf-ngtcp2-proxy.c:L1223-L1275][f1]

Creates a standalone H3-PROXY filter chain.

Validates preconditions: a tunnel peer must exist, the peer transport must be QUIC, and the connection must have an HTTP proxy peer; otherwise CURLE_FAILED_INIT. It allocates a zeroed context, initializes it with the connection's proxy SSL config, creates the filter, chains a UDP filter as cf->next via Curl_cf_udp_create for QUIC, and links connections. On any failure the created chain or context is discarded and *pcf is NULL; on success it logs the udp_tunnel flag.

calls: [cf-ngtcp2-proxy-ctx](r4-quic-connection-filter.md#u-ce5466565bfe); uses: [cf-ngtcp2-proxy-cft-vtable](r4-quic-connection-filter.md#u-235a696250d8)

<a id="u-1cb87420ff23"></a>
### `Curl_cf_ngtcp2_proxy_insert_after`

`CURLcode Curl_cf_ngtcp2_proxy_insert_after(struct Curl_cfilter *cf_at, struct Curl_ea…` · [lib/vquic/cf-ngtcp2-proxy.c:L1277-L1315][f1]

Alternative creation path: allocates and initializes a proxy context using the filter-chain connection's proxy SSL config, creates the H3-PROXY filter, and inserts it after cf_at so it sits above the existing HAPPY-EYEBALLS -> UDP sub-chain, reusing the UDP socket created below.

On failure any created chain or context is discarded; unlike the create path, no UDP filter is added here.

calls: [cf-ngtcp2-proxy-ctx](r4-quic-connection-filter.md#u-ce5466565bfe)

**Uncertainties.**

- Whether the existing chain below cf_at always provides a UDP filter is assumed from the comment, not verifiable in this file.

<a id="u-b04a803de5c2"></a>
### `cf_h3_proxy_adjust_pollset`

`static CURLcode cf_h3_proxy_adjust_pollset(struct Curl_cfilter *cf, struct Curl_easy …` · [lib/vquic/cf-ngtcp2-proxy.c:L981-L1013][f1]

Adjusts poll interest on the QUIC socket (the UDP socket if bound, else the filter-chain socket); returns OK untouched if no connection, stream, or socket.

If anything wants recv, wants send, or the QUIC sendbuf is non-empty, it recomputes: congestion or connection-flow exhaustion, or a flow-blocked stream, forces recv interest; send interest is dropped while the stream is flow-blocked but kept while the sendbuf holds data, then applied via Curl_pollset_set.

<a id="u-36ef18159882"></a>
### `cf_h3_proxy_data_pending`

`static bool cf_h3_proxy_data_pending(struct Curl_cfilter *cf, const struct Curl_easy …` · [lib/vquic/cf-ngtcp2-proxy.c:L1015-L1023][f1]

Reports pending readable data: TRUE when the tunnel recvbuf is non-empty, otherwise delegates to the next filter's has_data_pending, or FALSE if there is none.

<a id="u-2e8b8056527f"></a>
### `cf_h3_proxy_destroy`

`static void cf_h3_proxy_destroy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vquic/cf-ngtcp2-proxy.c:L1181-L1198][f1]

Filter destructor.

If the QUIC connection still exists it closes it within a save/restore of the call data, then frees the proxy context and NULLs cf->ctx.

calls: [cf-ngtcp2-proxy-ctx](r4-quic-connection-filter.md#u-ce5466565bfe)

<a id="u-3aaf604bff6f"></a>
### `cf_h3_proxy_recv`

`static CURLcode cf_h3_proxy_recv(struct Curl_cfilter *cf, struct Curl_easy *data, cha…` · [lib/vquic/cf-ngtcp2-proxy.c:L799-L882][f1]

Filter recv path for tunnel response data.

TLS verification failure returns that result and blocks reads. With no stream or a started shutdown it returns CURLE_RECV_ERROR. It drains the tunnel recvbuf, progresses ingress, and drains again if ingress produced data, extending the rx window after each drain. If nothing was read: a stored stream xfer_result closes the h3 stream and is returned; a closed stream is resolved by cf_h3_proxy_recv_closed_stream; otherwise CURLE_AGAIN. Egress and expiry handling apply on the way out with the first fatal error winning; call data is always restored.

calls: [cf_h3_proxy_recv_closed_stream](r4-quic-connection-filter.md#u-5fa103c8747e), [cf_h3_proxy_upd_rx_win](r4-quic-connection-filter.md#u-cd0b3e805a9e)

<a id="u-5fa103c8747e"></a>
### `cf_h3_proxy_recv_closed_stream`

`static ssize_t cf_h3_proxy_recv_closed_stream(struct Curl_cfilter *cf, struct Curl_ea…` · [lib/vquic/cf-ngtcp2-proxy.c:L655-L698][f1]

Produces a read result for a tunnel stream that was closed.

If the stream was reset: error CURL_H3_ERR_REQUEST_REJECTED logs a refusal, closes the connection, sets data->state.refused_stream, and returns CURLE_RECV_ERROR; otherwise, if response headers were complete and the request wants no body, the error is ignored with nread 0; any other reset fails with CURLE_PARTIAL_FILE (if bytes were received) or CURLE_HTTP3. A clean close before complete response headers fails with CURLE_HTTP3; a clean close after headers yields nread 0.

<a id="u-2d173eeffdd4"></a>
### `cf_h3_proxy_send`

`static CURLcode cf_h3_proxy_send(struct Curl_cfilter *cf, struct Curl_easy *data, con…` · [lib/vquic/cf-ngtcp2-proxy.c:L713-L796][f1]

Filter send path buffering CONNECT request body and driving QUIC egress.

Saves call data and refuses everything if TLS verification failed (returning that result) or if the tunnel or its stream is gone (CURLE_SEND_ERROR). If the stream is closed: with complete response headers (e.g. 30x/40x) the data is silently discarded as success with full length reported; without a response it fails with CURLE_HTTP3. Otherwise bytes go to the sendbuf via cf_h3_proxy_sendbuf_add and nghttp3_conn_resume_stream is invoked (result ignored). Bytes sent while early data is enabled but the TLS handshake is incomplete count toward earlydata_skip. Egress progresses, then the first fatal error among egress and expiry-setting wins; data context is always restored.

calls: [cf_h3_proxy_sendbuf_add](r4-quic-connection-filter.md#u-3193c81af05d)

**Uncertainties.**

- Curl_1st_fatal's definition of 'fatal' is external; only its ordering effect is visible.
- eos is explicitly unused here.

<a id="u-3193c81af05d"></a>
### `cf_h3_proxy_sendbuf_add`

`static CURLcode cf_h3_proxy_sendbuf_add(struct Curl_easy *data, struct h3_stream_ctx …` · [lib/vquic/cf-ngtcp2-proxy.c:L700-L711][f1]

Appends outgoing bytes to the stream's sendbuf via Curl_bufq_write, reporting bytes written; the easy handle parameter is unused.

<a id="u-e988e1fcdbb8"></a>
### `cf_h3_proxy_shutdown`

`static CURLcode cf_h3_proxy_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data,…` · [lib/vquic/cf-ngtcp2-proxy.c:L1200-L1204][f1]

Delegates shutdown entirely to the shared Curl_cf_ngtcp2_cmn_shutdown, returning its result and done flag.

<a id="u-cd0b3e805a9e"></a>
### `cf_h3_proxy_upd_rx_win`

`static void cf_h3_proxy_upd_rx_win(struct Curl_cfilter *cf, struct Curl_easy *data, s…` · [lib/vquic/cf-ngtcp2-proxy.c:L270-L304][f1]

Extends HTTP/3/QUIC flow-control credit based on locally buffered response data.

Returns early if the stream is gone; if rx_offset_max is below rx_offset it DEBUGASSERTs and returns. The wanted window is 512 KiB minus buffered recvbuf bytes; if that exceeds the current window (rx_offset_max - rx_offset), the delta — clamped so rx_offset_max cannot overflow UINT64_MAX — is added and announced to ngtcp2 via both stream and connection offset extension.

contract: [cb_h3_proxy_recv_data](r4-h3-proxy-tunnel.md#u-2efb4eba3a54)

**Uncertainties.**

- DEBUGASSERT's release-build behavior comes from outside this file; the code path plainly returns.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-ngtcp2-proxy.c
