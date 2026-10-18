# QUIC TLS Bridge

**Capability.** Owns the backend-independent TLS interface for QUIC filters: context init/cleanup per compiled backend, trust setup before receive, peer verification, handshake reporting, and TLS info for CURLINFO queries.

Use this child to see how QUIC delegates TLS to OpenSSL, GnuTLS or wolfSSL without depending on one backend. Each function dispatches on the compiled backend and keeps QUIC state in the vquic TLS peer struct.

**Depends on.**

- [wolfSSL TLS Backend](r10-tls-wolfssl.md) · model-inferred · 0 edge(s)

Parent: [QUIC / HTTP-3 Transport](r10-quic-transport.md)

## Units (7)

<a id="u-1ed61522bb04"></a>
### `Curl_vquic_report_handshake`

`void Curl_vquic_report_handshake(struct curl_tls_ctx *ctx, struct Curl_cfilter *cf, s…` · [lib/vquic/vquic-tls.c:L221-L237][f1]

Reports a completed handshake to transfer statistics via the backend-specific helper: Curl_ossl_report_handshake, Curl_gtls_report_handshake, or Curl_wssl_report_handshake; a no-op with unused-parameter casts when no supported backend is compiled.

<a id="u-0957930f5b8e"></a>
### `Curl_vquic_tls_before_recv`

`CURLcode Curl_vquic_tls_before_recv(struct curl_tls_ctx *ctx, struct Curl_cfilter *cf…` · [lib/vquic/vquic-tls.c:L122-L151][f1]

Ensures trust/CA material is set up before receiving on the QUIC TLS connection, once per context: OpenSSL sets up the X509 store (flagged by x509_store_setup), wolfSSL its X509 store, and GnuTLS its client trust (flagged by trust_setup).

Setup failures propagate and are retried on the next call since the flag is only set on success (OpenSSL path explicitly; the wolfSSL/GnuTLS paths rely on the flag inside their state). Returns CURLE_OK when already set up or on unknown backends.

**Uncertainties.**

- Whether wolfSSL/GnuTLS flags are set only on success depends on the called setup functions, not shown

<a id="u-cb80bd111a6b"></a>
### `Curl_vquic_tls_cleanup`

`void Curl_vquic_tls_cleanup(struct curl_tls_ctx *ctx)` · [lib/vquic/vquic-tls.c:L102-L120][f1]

Releases backend TLS resources: OpenSSL frees the SSL and SSL_CTX when set; GnuTLS deinits the session and frees shared creds; wolfSSL frees the SSL and SSL_CTX.

Always zeroes the whole ctx afterwards, so reuse after cleanup is safe from stale pointers.

<a id="u-a376c7b53d58"></a>
### `Curl_vquic_tls_get_ssl_info`

`bool Curl_vquic_tls_get_ssl_info(struct curl_tls_ctx *ctx, bool give_ssl_ctx, struct …` · [lib/vquic/vquic-tls.c:L197-L219][f1]

Fills a curl_tlssessioninfo for CURLINFO_TLS_SSL_PTR style queries.

Sets the backend constant for the compiled TLS library; internals is the SSL_CTX when give_ssl_ctx is true, otherwise the SSL session (OpenSSL/wolfSSL); GnuTLS always returns its session and ignores the flag. Returns TRUE, or FALSE when no supported backend is compiled in.

<a id="u-a21f0a2e1634"></a>
### `Curl_vquic_tls_init`

`CURLcode Curl_vquic_tls_init(struct curl_tls_ctx *ctx, struct Curl_cfilter *cf, struc…` · [lib/vquic/vquic-tls.c:L75-L100][f1]

Initializes the backend-specific TLS context for a QUIC filter, dispatching on the compiled TLS backend: Curl_ossl_ctx_init, Curl_gtls_ctx_init, or Curl_wssl_ctx_init, all receiving the peer, ALPN spec, setup callback, user data, and session-reuse callback.

The #else branch is a compile-time error.

**Uncertainties.**

- Backend init behavior is defined in vtls files not supplied

<a id="u-3799a8f25b69"></a>
### `Curl_vquic_tls_peer_init`

`CURLcode Curl_vquic_tls_peer_init(struct Curl_peer *origin, struct Curl_peer *peer, s…` · [lib/vquic/vquic-tls.c:L52-L73][f1]

Initializes a QUIC TLS peer description.

Builds a tls_id string naming the active TLS backend (OpenSSL/GnuTLS/wolfSSL; the #else branch is a compile-time error). If the ssl_peer already holds origin or peer data it is cleaned first, then Curl_ssl_peer_init sets it up from origin/peer/filter config with transport QUIC.

**Uncertainties.**

- Curl_ssl_peer_init/cleanup semantics live in vtls and are not visible here

<a id="u-41168dc69474"></a>
### `Curl_vquic_tls_verify_peer`

`CURLcode Curl_vquic_tls_verify_peer(struct curl_tls_ctx *ctx, struct Curl_cfilter *cf…` · [lib/vquic/vquic-tls.c:L153-L195][f1]

Verifies the QUIC server peer against the active TLS backend.

Fetches the filter's ssl_filter_config, returning CURLE_FAILED_INIT if absent. OpenSSL delegates to Curl_ossl_check_peer_cert; GnuTLS to Curl_gtls_verifyserver with the pinned-publickey string; wolfSSL checks the host only when verifyhost is set: no peer certificate -> CURLE_OUT_OF_MEMORY, SNI mismatch -> or absent SNI with hostname (IP) mismatch -> CURLE_PEER_FAILED_VERIFICATION, then runs pinned-key verification. On any failure it removes all cached TLS sessions for the peer's scache_key before returning the error.

**Uncertainties.**

- Backend verification functions are defined in vtls and not visible here

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/vquic-tls.c
