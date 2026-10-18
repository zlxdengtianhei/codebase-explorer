# QUIC/HTTP3 proxy filter stack

**Capability.** ngtcp2/HTTP3-based connection filters, including the shared ngtcp2 filter context and stream state types and the capsule filter factory declaration.

This node holds the shared state definitions and factory declarations used by the QUIC filters; the H3 proxy implementation is split into its connection-filter surface and the tunnel protocol below.

**Children.**

- [H3 proxy connection filter](r4-quic-connection-filter.md) `r4-quic-connection-filter` · 13 unit(s)
- [HTTP/3 CONNECT tunnel](r4-h3-proxy-tunnel.md) `r4-h3-proxy-tunnel` · 21 unit(s)

**Depends on.**

- [H3 proxy connection filter](r4-quic-connection-filter.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r4-quic-proxy-stack ` → ` r4-quic-connection-filter `)

Parent: [TLS and QUIC connections](r4-tls-quic.md)

## Units (4)

<a id="u-bfb4dcf0ac9b"></a>
### `cf-capsule-h`

`module_region` · [lib/vquic/cf-capsule.h:L1-L40][f1]

Declares the capsule connection-filter factory.

`Curl_cf_capsule_insert_after` inserts a filter after `cf_at` in the filter chain that encapsulates and decapsulates UDP datagrams using the RFC 9297 HTTP Datagram capsule format; it returns a CURLcode. Also exposes `extern struct Curl_cftype Curl_cft_capsule`, the filter type descriptor defined elsewhere. Guarded by `!CURL_DISABLE_PROXY && !CURL_DISABLE_HTTP`. Only declarations appear here.

uses: [capsule-h](r12-quic-capsule-filter.md#u-f4c17f4eea52)

**Uncertainties.**

- Insertion failure modes and filter lifecycle are defined in the corresponding .c file, not visible here.

<a id="u-c9ac809564f4"></a>
### `cf_ngtcp2_ctx`

`struct cf_ngtcp2_ctx` · [lib/vquic/cf-ngtcp2-cmn.h:L107-L148][f2]

Shared state for ngtcp2-based QUIC connect filters: QUIC transport objects (path, connection, CIDs, version, settings, transport params, last error, crypto conn ref), TLS state (ssl_peer, curl_tls_ctx, optional OpenSSL QUIC-API2 ctx), nghttp3 connection and settings, timing fields, a stream buffer pool, scratch dynbuf, the set of active h3 streams keyed by transfer mid, stream-count limits, early-data bookkeeping, the TLS verification result, a qlog fd, a tunnel ingress buffer, and status bitflags (initialized, TLS handshake complete, early data use/acceptance, shutdown started, stats reported).

Also declares the cf_ngtcp2_init_h3_conn callback type and the CF_CTX_CALL_DATA access macro for per-call call_data, plus prototypes for context init/cleanup and error setting.

**Uncertainties.**

- Member behavior depends on definitions outside this header; only the declared layout and names are observed

<a id="u-2736a4721dc4"></a>
### `cf_ngtcp2_io_ctx`

`struct cf_ngtcp2_io_ctx` · [lib/vquic/cf-ngtcp2-cmn.h:L204-L210][f2]

Small context bundling a filter, transfer, and time for ngtcp2 I/O progress: cf, data, a curltime now, an ngtcp2 timestamp, and a ngtcp2_path_storage.

Init and time-update helpers are declared here but defined elsewhere.

<a id="u-b8873e95b62e"></a>
### `h3_stream_ctx`

`struct h3_stream_ctx` · [lib/vquic/cf-ngtcp2-cmn.h:L166-L186][f2]

HTTP/3 per-stream state: the H3 stream id and owning transfer's xfer_id/mid, a bufq for the request body with an h1 request parser, an HTTP/3 error code, upload and receive accounting (upload_left, rx_total, rx_offset, rx_offset_max), send accounting (tx_in_flight_size/ideal), the response status code and response-write result, and bitflags for complete response, closed, reset, locally send-closed, and QUIC-flow-blocked.

Frees and error reporting are via the declared helper prototypes (e.g. Curl_cf_ngtcp2_h3_stream_ctx_free).

**Uncertainties.**

- Only the field layout is defined here; the free/error helpers are declared, not defined, in this file

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-capsule.h
[f2]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-ngtcp2-cmn.h
