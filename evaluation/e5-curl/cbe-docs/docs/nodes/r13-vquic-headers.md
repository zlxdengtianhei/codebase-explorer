# QUIC Shared Header Contracts

**Capability.** Owns the compile-time contracts shared by all HTTP/3 backends: the vquic-tls.h QUIC TLS layer with its backend-selected curl_tls_ctx union, and vquic_int.h with the cf_quic_ctx transport state and the RFC 9114 HTTP/3 error-code enumeration. These headers exist so backend implementations agree on state layout and error codes without runtime code here.

Use these units when reading or writing an HTTP/3 backend: the context structs define what per-connection state a backend must maintain, and vquic_h3_error standardizes error reporting.

**Depends on.**

- [Socket Connect Filters](r13-socket-filters.md) · model-inferred · 0 edge(s)

Parent: [curl Library Responsibilities](r13-curl-library-core.md)

## Units (5)

<a id="u-763b731d8fcd"></a>
### `vquic-tls-h`

`module_region` · [lib/vquic/vquic-tls.h:L50-L125][f1]

Declares the shared QUIC TLS layer used by all HTTP/3 backends under USE_HTTP3 with OpenSSL, GnuTLS, or wolfSSL.

`Curl_vquic_tls_init` initializes a `curl_tls_ctx` from the filter, transfer, and ssl_peer, negotiating the given ALPN spec (may be NULL); it accepts an optional early-setup callback (documented as running after SSL_CTX creation on openssl/wolfSSL and after gtls_client_init on GnuTLS), an ssl_user_data pointer, and a session-reuse callback that receives the negotiated ALPNs and sets `do_early_data`. Supporting typedefs `Curl_vquic_tls_ctx_setup` and `Curl_vquic_session_reuse_cb` define those callback signatures. Companion declarations cover the rest of the TLS lifecycle: peer init (`Curl_vquic_tls_peer_init`), pre-receive processing (`Curl_vquic_tls_before_recv`), post-handshake certificate/peer verification (`Curl_vquic_tls_verify_peer`), SSL info retrieval with a `give_ssl_ctx` flag (`Curl_vquic_tls_get_ssl_info`, returns bool), handshake reporting, and `Curl_vquic_tls_cleanup` to release initialized data. All factory-style functions return CURLcode; no bodies here.

uses: [vquic-tls-h-curl_tls_ctx](r13-vquic-headers.md#u-e4f532ce0c90)

**Uncertainties.**

- Error codes returned on handshake or verification failure are not specified in this header.
- Exact semantics of `give_ssl_ctx` and of `do_early_data` reporting are documented only by parameter names.

<a id="u-e4f532ce0c90"></a>
### `vquic-tls-h-curl_tls_ctx`

`struct curl_tls_ctx` · [lib/vquic/vquic-tls.h:L42-L50][f1]

Defines the QUIC TLS context as a single-member compile-time-selected struct: `ossl` for OpenSSL, `gtls` for GnuTLS, or `wssl` for wolfSSL, under the USE_HTTP3 plus backend guard.

Exactly one member exists per build, so backend code accesses its native context through this common type.

group: [vquic-tls-h](r13-vquic-headers.md#u-763b731d8fcd)

**Uncertainties.**

- Struct layouts of ossl_ctx/gtls_ctx/wssl_ctx are defined in vtls headers not supplied here.

<a id="u-e3e658eb32f6"></a>
### `vquic_int-h`

`module_region` · [lib/vquic/vquic_int.h:L79-L130][f2]

Declares the shared QUIC transport helpers used by all HTTP/3 backends under USE_HTTP3.

`MAX_UDP_PAYLOAD_SIZE` is fixed at 1452 bytes. `Curl_vquic_h3_err_str` returns a string for an H3 error code when CURLVERBOSE is defined; otherwise the macro expands it to an empty string, costing nothing in non-verbose builds. Context lifecycle helpers init and free `cf_quic_ctx`, and set/update its timestamps. Sending is split into `Curl_vquic_send` (flush the sendbuf with the given GSO length), `Curl_vquic_send_tail_split` (send with a differing GSO length for the tail bytes), and `Curl_vquic_flush`; all return CURLcode. `Curl_vquic_recv_packets` reads up to `max_pkts` datagrams and invokes the caller-supplied `Curl_vquic_recv_pkts_cb` per packet with payload, gso_size, remote address, and ECN. Under USE_NGTCP2/USE_NGHTTP3 it also exposes custom allocator getters `Curl_ngtcp2_mem`/`Curl_nghttp3_mem`. All declarations, no bodies.

uses: [vquic_int-h-cf_quic_ctx](r13-vquic-headers.md#u-9c8bfd20bea0), [vquic_int-h-enum](r13-vquic-headers.md#u-49678e79b7e3)

**Uncertainties.**

- Behavior on short writes, EAGAIN, or per-packet callback errors is defined in the .c file and cannot be determined from these declarations.

<a id="u-9c8bfd20bea0"></a>
### `vquic_int-h-cf_quic_ctx`

`struct cf_quic_ctx` · [lib/vquic/vquic_int.h:L62-L79][f2]

Defines `cf_quic_ctx`, the per-filter QUIC transport state shared by HTTP/3 backends: the connected UDP socket with its bound local address, a send bufq for one or more packets, timing fields (first received byte, last attempted and last successful socket IO), GSO parameters (packet length `gsolen`, and `split_len`/`split_gsolen` describing the alternate GSO length beyond the split point), debug-only `wblock_percent` for simulated EAGAIN on writes, and flags `got_first_byte` and `no_gso` to disable GSO.

The header also defines the `H3_STREAM_CTX(ctx, data)` macro, which looks up the transfer's stream context by `(data)->mid` in `ctx->streams` via `Curl_u32_ptrset_get`, yielding NULL when `data` is NULL or no stream exists.

group: [vquic_int-h](r13-vquic-headers.md#u-e3e658eb32f6)

**Uncertainties.**

- The `streams` member is referenced by H3_STREAM_CTX but is not visible in the shown struct fields, suggesting the listing omits it; how streams is initialized cannot be confirmed here.

<a id="u-49678e79b7e3"></a>
### `vquic_int-h-enum`

`enum` · [lib/vquic/vquic_int.h:L36-L54][f2]

Defines `vquic_h3_error`, the HTTP/3 error-code enumeration from RFC 9114 section 8.1, with values 0x0100-0x0110 covering NO_ERROR through VERSION_FALLBACK.

Pure constant table used as H3-level error codes alongside QUIC error codes.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/vquic-tls.h
[f2]: ../../../../../../eval/curl-2c04412/lib/vquic/vquic_int.h
