# TLS session reuse

**Capability.** Storing, retrieving and applying cached TLS sessions keyed by peer and ALPN, including early-data capacity negotiation on reuse.

ossl_new_session_cb and Curl_ossl_add_session capture new sessions; ossl_apply_session and ossl_on_session_reuse handle reuse, and ossl_init_session_and_alpns prepares a fresh SSL for both reuse and ALPN. Read this subtree for session-cache behavior and the FTP session-override case.

**Depended on by.**

- [OpenSSL connection lifecycle](r11-ossl-conn-lifecycle.md) · model-inferred · 0 edge(s)

Parent: [TLS backends \(OpenSSL-based\)](r11-tls-security.md)

## Units (5)

<a id="u-b745131ae858"></a>
### `Curl_ossl_add_session`

`CURLcode Curl_ossl_add_session(struct Curl_cfilter *cf, struct Curl_easy *data, struc…` · [lib/vtls/openssl.c:L2623-L2709][f1]

Serializes an accepted SSL_SESSION and stores it in curl's session cache.

With no filter/data it returns OK after nulling *psession. When the shared cache is in use it DER-encodes the session (either i2d sizing failure yields CURLE_OUT_OF_MEMORY, with allocation failures the same), reads the max early data when supported, clones QUIC transport parameters when given, and builds a Curl_ssl_session via Curl_ssl_session_create2 carrying the ALPN and an expiry of now plus the session timeout; allocation of the DER buffer or QUIC clone clone failures return CURLE_OUT_OF_MEMORY. Under Apple SecTrust the sectrust verdict is copied. For FTP control connections the session is additionally duplicated for the caller. The session is put into the shared cache, transferring ownership; on success a requested duplicate is returned via *psession, and all temporaries are freed on every exit path.

uses: [ossl_new_session_cb](r11-ossl-session-cache.md#u-edf17fe9bdb6)

<a id="u-edf17fe9bdb6"></a>
### `ossl_new_session_cb`

`static int ossl_new_session_cb(SSL *ssl, SSL_SESSION *ssl_sessionid)` · [lib/vtls/openssl.c:L2714-L2731][f1]

OpenSSL new-session callback: retrieves the connection filter from the SSL app data and, when present, stores the new session via Curl_ossl_add_session under the peer's scache key with the negotiated ALPN; if a session object comes back (FTP case) it replaces connssl->session.

Always returns 0, telling OpenSSL the session need not be retained internally.

<a id="u-75c38628d8ae"></a>
### `ossl_apply_session`

`static bool ossl_apply_session( struct ossl_ctx *octx, struct Curl_cfilter *cf, struc…` · [lib/vtls/openssl.c:L3357-L3430][f1]

Attempts to reuse a cached TLS session on the SSL handle, never failing: a DER session that OpenSSL cannot parse is logged and skipped.

A parsed session is applied with SSL_set_session; if OpenSSL rejects it, that is logged and ignored. When accepted, reuse is withheld if the session was never peer-verified (verify result not OK and peer verification is enabled, with a SecTrust exception for a natively verified prior session) by clearing the session again; otherwise reuse is confirmed: octx->reused_session is set, the SecTrust verdict recorded where applicable, and, with early-data support, if the config allows early data, the session has some, the connection is not connect-only and TLS 1.3 is in use, the sess_reuse_cb decides whether to restrict ALPN to the session's protocol so early data is not sent for the wrong protocol. Returns whether a session is being reused.

**Uncertainties.**

- SSL_set_session returning 0 means OpenSSL kept its own state; the code assumes the session is not partially applied

<a id="u-88c56534a3d4"></a>
### `ossl_on_session_reuse`

`static CURLcode ossl_on_session_reuse(struct Curl_cfilter *cf, struct Curl_easy *data…` · [lib/vtls/openssl.c:L3992-L4004][f1]

Session-reuse callback plumbing: copies the cached session's early-data capacity into connssl->earlydata_max, then delegates to Curl_on_session_reuse to decide reuse and early data.

<a id="u-b131146b307c"></a>
### `ossl_init_session_and_alpns`

`static CURLcode ossl_init_session_and_alpns( struct ossl_ctx *octx, struct Curl_cfilt…` · [lib/vtls/openssl.c:L3432-L3486][f1]

Prepares session reuse and ALPN on a fresh SSL handle.

It copies the requested ALPN list. For a TLS-secured FTP data connection on the secondary socket (non-proxy filter) it tries to reuse the control connection's session (issue #22225). Otherwise, when the shared cache is in use and OCSP status verification is not requested, it takes a cached session by the peer key and applies it (always returning it to the cache afterwards). Both paths run through ossl_apply_session. Finally, if any ALPN protocols remain, it serializes them and sets them on the SSL; a serialization or SSL_set_alpn_protos failure fails with CURLE_SSL_CONNECT_ERROR after a failf. Returns OK otherwise.

calls: [ossl_apply_session](r11-ossl-session-cache.md#u-75c38628d8ae)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/openssl.c
