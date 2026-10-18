# Quiche H3 Connection Lifecycle

**Capability.** Owning the quiche connection-filter context, filter construction, control/pollset handling, QUIC handshake, shutdown, queries and liveness for HTTP/3 over quiche.

Use to understand how the quiche H3 filter is created, how the QUIC connection and configuration are opened once the socket exists, and how control, pollset, query and liveness are answered. Data-plane stream handling lives in the sibling transfer I/O node.

**Depends on.**

- [Quiche H3 Transfer I/O](r2-quiche-transfer-io.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Quiche H3 Transfer I/O](r2-quiche-transfer-io.md) · model-inferred · 0 edge(s)

Parent: [Connection Filter Protocol Stacks](r2-protocol-filters.md)

## Units (10)

<a id="u-5d1b8ed9a8f6"></a>
### `cf-quiche.c-ctx-lifecycle`

`void Curl_quiche_ver(char *p, size_t len)` · [lib/vquic/cf-quiche.c:L73-L76][f1]

Manages the lifetime of the quiche connection-filter context and its per-stream records.

Init initializes the header dynbuf, the stream pointer set (with h3_stream_set_free as element destructor), the write bufq, and the TLS peer data; under DEBUG_QUICHE it installs the one-shot stderr debug-log callback. Free cleans TLS, SSL peer, vquic, stream set, dynbuf and bufq only when initialized, then frees the context itself, nulling tls.ossl.ssl because quiche owns that object. Close frees the H3 connection/config, QUIC connection and config (each guarded by a null check and nulled after free) and cleans the SSL peer; it is the destructor path used by cf_quiche_destroy. Curl_quiche_ver merely formats 'quiche/<version>' into a caller buffer. h3_stream_ctx_free releases the h1 parser state and the stream record; h3_stream_set_free adapts it to the pointer-set visitor signature.

uses: [cf_quiche_ctx](r2-quiche-connection.md#u-3128c35b540c)

<a id="u-bb1e0b6ddd57"></a>
### `cf-quiche.c-factory`

`CURLcode Curl_cf_quiche_create(struct Curl_cfilter **pcf, struct Curl_easy *data, str…` · [lib/vquic/cf-quiche.c:L1641-L1681][f1]

Constructs HTTP/3 connection filters.

Both Curl_cf_quiche_create and Curl_cf_quiche_insert_after allocate a cf_quiche_ctx, initialize it from the origin/peer and the connection's SSL config, and wrap it in a filter using Curl_cft_http3. Create additionally sets cf->conn, chains a new UDP filter for TRNSPRT_QUIC as cf->next (sharing conn and sockindex), and on failure discards the whole filter chain or frees the bare context, returning NULL via *pcf on error. Insert_after inserts the new filter after cf_at and, on failure, frees the filter and context; *pcf receives the filter (NULL on failure).

calls: [cf-quiche.c-ctx-lifecycle](r2-quiche-connection.md#u-5d1b8ed9a8f6)

<a id="u-a2abd77c5164"></a>
### `cf-quiche.c-control`

`static CURLcode h3_data_pause(struct Curl_cfilter *cf, struct Curl_easy *data, bool p…` · [lib/vquic/cf-quiche.c:L1207-L1218][f1]

Control-plane handling for the filter.

h3_data_pause cannot resize quiche flow windows (no API, noted in a comment) so on unpause it only marks the transfer dirty. cf_quiche_cntrl dispatches events: DATA_SETUP does nothing; DATA_PAUSE delegates to h3_data_pause with arg1; DATA_DONE runs h3_data_done to close and unregister the stream; DONE_SEND sends a zero-length eos marker through cf_quiche_send if the stream has not yet closed its send side (marking send_closed first); CONN_INFO_UPDATE, on sockindex 0 of a connected filter, records HTTP version 30 and enables multiplexing on the connection; REPORT_STATS reports TIMER_CONNECT from first-byte time and TIMER_APPCONNECT from handshake time once, guarded by stats_reported and a set handshake_at. Unknown events are ignored.

calls: [cf_quiche_send](r2-quiche-transfer-io.md#u-5c47d03a2325), [cf-quiche.c-stream-teardown](r2-quiche-transfer-io.md#u-004a71731234)

<a id="u-e02b6d621609"></a>
### `cf-quiche.c-pollset`

`static bool stream_is_writable(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vquic/cf-quiche.c:L1168-L1176][f1]

Adjusts socket poll interest for the transfer.

stream_is_writable reports whether the transfer has a stream that quiche reports writable for at least 1 byte. cf_quiche_adjust_pollset returns OK when no QUIC connection exists; when the socket is already in the pollset with recv or send interest it computes: connection exhaustion is always FALSE (no quiche API found for it), send exhaustion is true when the transfer wants to send and its stream is flow-blocked or not writable; recv interest is requested whenever wanted or sending is exhausted, send interest is kept only when not exhausted or when the QUIC sendbuf still holds data; the result is applied with Curl_pollset_set.

<a id="u-3128c35b540c"></a>
### `cf_quiche_ctx`

`struct cf_quiche_ctx` · [lib/vquic/cf-quiche.c:L78-L98][f1]

Per-filter state for the quiche HTTP/3 connection filter.

It embeds the generic QUIC filter context, TLS peer/session data, the quiche connection, config, and H3 connection/config handles, the locally generated connection ID, handshake timestamps, the set of transfer-id-to-stream-ctx mappings, a temp buffer for HTTP/1-style header assembly, a write bufq, and counters/flags: data_recvd byte total, initialized, goaway received, x509 store setup, shutdown packets queued, and stats reported.

<a id="u-4c93ed726581"></a>
### `cf_quiche_connect`

`static CURLcode cf_quiche_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bo…` · [lib/vquic/cf-quiche.c:L1382-L1476][f1]

Drives the QUIC/H3 handshake.

Already-connected returns done immediately. It first connects the underlying UDP filter and returns until that is done, then delays when HTTPS-RR is required but DNS records are not resolved yet. With no QUIC connection it opens one (cf_quiche_ctx_open), records started_at, flushes egress, and returns — nothing can be received yet. Otherwise it processes ingress and flushes egress; when quiche reports the connection established it records handshake_at, verifies the peer, creates the H3 config (max field section size raised to MAX_HTTP_RESP_HEADER_SIZE because quiche 0.29.3+ defaults to 32 KiB) and H3 connection, then marks the filter connected and done. A draining connection (server sent CONNECTION_CLOSE, e.g. during server shutdown) yields CURLE_WEIRD_SERVER_REPLY so a retry can succeed later. Under CURLVERBOSE failures other than AGAIN are logged with the remote address.

calls: [cf_quiche_ctx_open](r2-quiche-connection.md#u-aba636a3a263), [function::cf_quiche_verify_peer::39751][f1], [cf-quiche.c-ingress](r2-quiche-transfer-io.md#u-11d7bd52116d), [cf-quiche.c-egress](r2-quiche-transfer-io.md#u-1efcb1d816f1)

<a id="u-aba636a3a263"></a>
### `cf_quiche_ctx_open`

`static CURLcode cf_quiche_ctx_open(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vquic/cf-quiche.c:L1272-L1373][f1]

Creates the QUIC connection and its configuration when the socket is available.

It initializes the vquic context, builds a quiche config for the QUIC v1 protocol with pacing disabled, 1 MiB initial data, QUIC_MAX_STREAMS bidi/uni streams, H3_STREAM_WINDOW_SIZE per-stream windows, a 10x connection/stream window cap, active migration disabled, and the H3 application protocols. It initializes TLS with an 'h3' ALPN spec, generates a random source connection ID, peeks the socket, reads the local address via getsockname (failure is CURLE_QUIC_CONNECT_ERROR), and creates the QUIC connection with TLS (failure is CURLE_OUT_OF_MEMORY). On non-Windows with qlog support it attaches a qlog file when a qlog dir is available. It then flushes egress to send the client Initial, and finally traces the ALPN list by rewriting each length prefix to a comma. Several early failures after config creation leak ctx->cfg in this code path.

**Uncertainties.**

- quiche_config is not freed on the error returns after its creation; whether callers destroy the whole context (calling cf_quiche_ctx_close) on this error is not visible here.
- qlog availability depends on build macros outside this file.

<a id="u-96aa4e3c45a4"></a>
### `cf_quiche_shutdown`

`static CURLcode cf_quiche_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data, b…` · [lib/vquic/cf-quiche.c:L1478-L1523][f1]

Gracefully closes the QUIC connection.

Already shut down, missing context or connection reports done. On first call it marks shutdown_started, closes the connection via quiche_conn_close (application-side, error 0); a nonzero quiche error aborts with CURLE_SEND_ERROR. While the sendbuf holds data it flushes egress; when the sendbuf is empty it declares shutdown done, otherwise it reports still blocked, relying on repeated calls. A comment notes quiche cannot wait for a peer shutdown reply.

<a id="u-3bb3c8eab65e"></a>
### `cf_quiche_query`

`static CURLcode cf_quiche_query(struct Curl_cfilter *cf, struct Curl_easy *data, int …` · [lib/vquic/cf-quiche.c:L1535-L1585][f1]

Answers connection queries.

MAX_CONCURRENT reports attached transfers plus the peer's remaining bidirectional streams unless goaway was received or no QUIC connection exists, clamped to INT_MAX. CONNECT_REPLY_MS gives milliseconds from start to first byte, or -1 without data. HTTP_VERSION reports 30. SSL_INFO/SSL_CTX_INFO fill a tlssessioninfo via Curl_vquic_tls_get_ssl_info, falling through when it fails. ALPN_NEGOTIATED returns "h3" once connected, else NULL. Unknown queries pass to the next filter or return CURLE_UNKNOWN_OPTION.

<a id="u-b32fac7df54e"></a>
### `cf_quiche_conn_is_alive`

`static bool cf_quiche_conn_is_alive(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/vquic/cf-quiche.c:L1587-L1622][f1]

Liveness probe for the connection.

No QUIC connection means not alive. A quiche-closed connection (idle timeout or otherwise, logged) is not alive. It then asks the next filter; a dead next filter or pending input flagged by it triggers a re-check: input_pending is cleared and ingress is processed — failure means not alive, success keeps alive. Otherwise alive stays TRUE. Protocol-only frames are the expected 'pending' data before a request is sent.

calls: [cf-quiche.c-ingress](r2-quiche-transfer-io.md#u-11d7bd52116d)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-quiche.c
