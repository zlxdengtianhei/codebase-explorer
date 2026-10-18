# QUIC Filter Lifecycle

**Capability.** Owns creation/insertion of QUIC and HTTP/3-proxy connection filters, HTTP/3 permission checks with build-gated fallbacks, library-wide QUIC init/teardown, version/error text, QLOG tracing, context setup/free, and ngtcp2/nghttp3 allocator shims.

Use this child to add or inspect QUIC filter wiring and context lifecycle. The memory shims route both QUIC stacks' allocations through curl's allocator.

Parent: [QUIC / HTTP-3 Transport](r10-quic-transport.md)

## Units (18)

<a id="u-f69cef14bfc8"></a>
### `cf-quiche-h`

`module_region` · [lib/vquic/cf-quiche.h:L1-L51][f1]

Declares the quiche QUIC connection-filter interface, compiled when HTTP is enabled and USE_QUICHE is defined.

Includes quiche.h and OpenSSL headers, forward-declares curl structures, and exposes `Curl_quiche_ver(p, len)` to write a version string into a caller buffer, plus `Curl_cf_quiche_create` and `Curl_cf_quiche_insert_after` factories with origin/peer/connection/sockaddr parameters returning CURLcode. Declarations only.

**Uncertainties.**

- Truncation or NUL-termination behavior of Curl_quiche_ver for small `len` is not specified in this header.

<a id="u-90e9d8f725c0"></a>
### `Curl_cf_h3_proxy_create`

`CURLcode Curl_cf_h3_proxy_create(struct Curl_cfilter **pcf, struct Curl_easy *data, s…` · [lib/vquic/vquic.c:L1175-L1201][f2]

Creates the HTTP/3 proxy connection filter.

With ngtcp2+nghttp3 it delegates to Curl_cf_ngtcp2_proxy_create, forwarding both the transport and tunnel parameters; otherwise *pcf is NULL and CURLE_NOT_BUILT_IN is returned. Debug-asserts transport_peer == TRNSPRT_QUIC.

<a id="u-f5ca3687b013"></a>
### `Curl_cf_h3_proxy_insert_after`

`CURLcode Curl_cf_h3_proxy_insert_after(struct Curl_cfilter *cf_at, struct Curl_easy *…` · [lib/vquic/vquic.c:L1154-L1173][f2]

Inserts the HTTP/3 proxy tunnel filter after a given filter.

Only compiled with proxy support and USE_PROXY_HTTP3; with ngtcp2+nghttp3 it delegates to Curl_cf_ngtcp2_proxy_insert_after, otherwise returns CURLE_NOT_BUILT_IN with all parameters discarded.

<a id="u-b99456d010cd"></a>
### `Curl_cf_quic_create`

`CURLcode Curl_cf_quic_create(struct Curl_cfilter **pcf, struct Curl_easy *data, struc…` · [lib/vquic/vquic.c:L1121-L1150][f2]

Creates the QUIC connection filter for a direct QUIC transport.

Delegates to the ngtcp2 or quiche backend's create function with origin, peer, connection, and socket address; without a backend it sets *pcf to NULL and returns CURLE_NOT_BUILT_IN. Asserts in debug builds that transport_peer is TRNSPRT_QUIC; the tunnel-related parameters are accepted but unused.

**Uncertainties.**

- Whether unused tunnel_peer/tunnel_transport are meaningful in other call paths is not visible here.

<a id="u-3a86bc03670c"></a>
### `Curl_cf_quic_insert_after`

`CURLcode Curl_cf_quic_insert_after(struct Curl_cfilter *cf_at, struct Curl_easy *data…` · [lib/vquic/vquic.c:L1089-L1119][f2]

Inserts the QUIC connection filter after a given filter, delegating to the compiled backend: ngtcp2+nghttp3 or quiche; without a backend it returns CURLE_NOT_BUILT_IN.

When built with HTTPS-RR and ECH, and the insert succeeded for an HTTP scheme whose TLS requires an HTTPS RR, it additionally schedules the HTTPS-RR DNS resolve on the connection and propagates its result.

contract: [Curl_cf_quic_create](r10-quic-filter-lifecycle.md#u-b99456d010cd)

**Uncertainties.**

- The source contains '(void)cf)' with an unbalanced parenthesis in the no-backend branch, which is a syntax error as written; the intended cast is inferred.
- Curl_ssl_need_httpsrr and Curl_conn_dns_add_https_resolve semantics are external.

<a id="u-be8c618bdb9f"></a>
### `Curl_conn_may_http3`

`CURLcode Curl_conn_may_http3(struct Curl_easy *data, struct connectdata *conn)` · [lib/vquic/vquic.c:L1205-L1226][f2]

Checks whether HTTP/3 is permissible for the connection, returning CURLE_OK or failing with a reason.

Rejects UNIX domain socket peers with CURLE_QUIC_CONNECT_ERROR, non-SSL origin schemes (missing PROTOPT_SSL) with CURLE_URL_MALFORMAT, and — unless proxy support is disabled — connections carrying a SOCKS proxy with CURLE_URL_MALFORMAT. Each rejection logs a descriptive message via failf.

**Uncertainties.**

- This is the full-HTTP3-build variant; a second same-named fallback exists for disabled HTTP/3.

<a id="u-088d30efca78"></a>
### `lib/vquic/vquic.c:Curl_conn_may_http3`

`CURLcode Curl_conn_may_http3(struct Curl_easy *data, struct connectdata *conn)` · [lib/vquic/vquic.c:L1336-L1343][f2]

Fallback definition for builds without HTTP/3 (HTTP disabled or no HTTP/3 support): ignores its arguments, logs a debug note that QUIC is not supported, and always returns CURLE_NOT_BUILT_IN so callers fail fast.

<a id="u-3e2855351808"></a>
### `Curl_vquic_h3_err_str`

`const char *Curl_vquic_h3_err_str(uint64_t error_code)` · [lib/vquic/vquic.c:L1229-L1275][f2]

Maps an HTTP/3 error code to a static name string, compiled only with CURLVERBOSE.

Codes fitting an unsigned int are matched against the CURL_H3_ERR_* enumeration; additionally, per RFC 9114, codes >= 0x21 where (code - 0x21) is a multiple of 0x1f are reserved and reported as "NO_ERROR". Everything else, including codes above UINT_MAX that match no pattern, returns "unknown".

**Uncertainties.**

- Whether codes above UINT_MAX can match the reserved pattern is moot since the pattern check applies to them too; only the switch is capped.

<a id="u-dc58cba5919f"></a>
### `Curl_qlogdir`

`CURLcode Curl_qlogdir(struct Curl_easy *data, unsigned char *scid, size_t scidlen, in…` · [lib/vquic/vquic.c:L1045-L1087][f2]

Opens a QLOG trace file when the QLOGDIR environment variable is set; otherwise sets *qlogfdp to -1 and returns OK.

Builds '<QLOGDIR>/<scid-as-hex>.sqlog' via dynbuf, hex-encoding each connection ID byte; any dynbuf addition failure aborts construction and is returned after freeing resources. On success it opens the file write-only/creat/binary with the connection's new_file_perms (masked to read/write on Windows); an open failure is not an error — *qlogfdp stays -1 and CURLE_OK is returned. Always frees the dynbuf and the getenv result. Per the comment, errors are returned only for failures other than failing to create the file.

**Uncertainties.**

- Behavior when QLOGDIR is set but scidlen is 0 is a file named with an empty ID; whether backends treat that fd is outside this file.

<a id="u-0d0796d52c65"></a>
### `Curl_quic_ver`

`void Curl_quic_ver(char *p, size_t len)` · [lib/vquic/vquic.c:L115-L122][f2]

Writes the active QUIC backend's version string into the caller's buffer.

Delegates to Curl_ngtcp2_ver when both ngtcp2 and nghttp3 are used, or Curl_quiche_ver when quiche is used; if neither backend is compiled in, the function body is empty and the buffer is left untouched.

uses: [Curl_vquic_ctx_init](r10-quic-filter-lifecycle.md#u-b0c0f802cf6b)

**Uncertainties.**

- Whether the buffer is NUL-terminated when no backend is selected is not shown here.

<a id="u-d6accf1616d2"></a>
### `Curl_vquic_init`

`int Curl_vquic_init(void)` · [lib/vquic/vquic.c:L97-L105][f2]

Performs library-wide QUIC initialization and reports success as a boolean-style int.

Only under ngtcp2 with OpenSSL QUIC API2 does it call ngtcp2_crypto_ossl_init(); a zero return from that call makes this function return 0 (treated as failure by callers), otherwise it returns 1. With other backends it returns 1 unconditionally.

uses: [vquic.c module code (L1–L74)][f2]

**Uncertainties.**

- Interpretation of the 0/1 return by callers is not visible in this file.

<a id="u-6a11d20e53bf"></a>
### `Curl_vquic_cleanup`

`void Curl_vquic_cleanup(void)` · [lib/vquic/vquic.c:L107-L113][f2]

Releases library-wide QUIC state at shutdown.

Under ngtcp2 with OpenSSL QUIC API2 and ngtcp2 >= 0x011800 it calls ngtcp2_crypto_ossl_free(); with any other configuration the body compiles to nothing.

<a id="u-b0c0f802cf6b"></a>
### `Curl_vquic_ctx_init`

`CURLcode Curl_vquic_ctx_init(struct Curl_easy *data, struct cf_quic_ctx *qctx)` · [lib/vquic/vquic.c:L124-L149][f2]

Initializes a QUIC connection filter's send context.

Sets up the send buffer queue with 64 KiB chunks, a single chunk, and SOFT_LIMIT. Chooses GSO support: no_gso is FALSE on Linux with UDP_SEGMENT and sendmsg, FALSE with Apple msg_x, TRUE otherwise. In DEBUGBUILD it reads CURL_DBG_QUIC_WBLOCK and, if it parses as a number <= 100 via curlx_str_number, stores it as wblock_percent for simulated blocking. Finally stamps last_op with the current progress time and returns CURLE_OK.

calls: [vquic.c-ctx-time](r10-quic-filter-lifecycle.md#u-9e410db5e19f); contract: [vquic_send_packets](r10-quic-packet-io.md#u-4e8ba842a00c)

**Uncertainties.**

- Failure of Curl_bufq_init2 is not checked here; its error behavior is outside this file.

<a id="u-5fc84986887e"></a>
### `Curl_vquic_ctx_free`

`void Curl_vquic_ctx_free(struct cf_quic_ctx *qctx)` · [lib/vquic/vquic.c:L151-L154][f2]

Releases the context's send buffer queue via Curl_bufq_free.

No other state is freed here.

<a id="u-9e410db5e19f"></a>
### `vquic.c-ctx-time`

`void Curl_vquic_ctx_set_time(struct cf_quic_ctx *qctx, const struct curltime *pnow)` · [lib/vquic/vquic.c:L156-L160][f2]

Updates the QUIC filter context's last-operation timestamp.

Both functions assign the pointed curltime value into qctx->last_op; Curl_vquic_ctx_update_time exists as a semantically identical call site name for recording when an I/O operation just happened. No return value, no failure paths.

<a id="u-4a92f093bf3b"></a>
### `vquic.c-ngtcp2-mem-allocators`

`static void *vquic_ngtcp2_malloc(size_t size, void *user_data)` · [lib/vquic/vquic.c:L1280-L1284][f2]

malloc/free/calloc/realloc shims adapting curl's memory functions to the ngtcp2/nghttp3 allocator interfaces.

Each ignores its user_data argument and forwards to Curl_cmalloc, Curl_cfree, Curl_ccalloc, or Curl_crealloc, so QUIC library allocations honor curl's memory tracking. They are wired into static ngtcp2_mem and nghttp3_mem structs (with NULL user_data) guarded by USE_NGTCP2 / USE_NGHTTP3 respectively.

<a id="u-fba8008b262e"></a>
### `Curl_ngtcp2_mem`

`struct ngtcp2_mem *Curl_ngtcp2_mem(void)` · [lib/vquic/vquic.c:L1312-L1315][f2]

Returns a pointer to the static ngtcp2_mem allocator struct that routes ngtcp2 allocations through curl's memory functions.

Compiled only with USE_NGTCP2.

uses: [vquic.c-ngtcp2-mem-allocators](r10-quic-filter-lifecycle.md#u-4a92f093bf3b)

<a id="u-fb8b1b0e26f3"></a>
### `Curl_nghttp3_mem`

`struct nghttp3_mem *Curl_nghttp3_mem(void)` · [lib/vquic/vquic.c:L1326-L1329][f2]

Returns a pointer to the static nghttp3_mem allocator struct using the same curl-backed allocation shims as the ngtcp2 variant.

Compiled only with USE_NGHTTP3.

uses: [vquic.c-ngtcp2-mem-allocators](r10-quic-filter-lifecycle.md#u-4a92f093bf3b)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-quiche.h
[f2]: ../../../../../../eval/curl-2c04412/lib/vquic/vquic.c
