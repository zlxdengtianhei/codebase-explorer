# wolfSSL Session Reuse

**Capability.** Owns TLS session caching: the new-session callback stores each negotiated session via the serializer, and the apply path decodes a cached session onto a new SSL handle.

Use this child to trace session-reuse behavior for wolfSSL. Serialization is delegated to the shared TLS session packer.

**Depends on.**

- [TLS Session Serializer](r10-tls-session-packer.md) · model-inferred · 0 edge(s)

Parent: [wolfSSL TLS Backend](r10-tls-wolfssl.md)

## Units (4)

<a id="u-9213b8833ca8"></a>
### `Curl_wssl_cache_session`

`CURLcode Curl_wssl_cache_session(struct Curl_cfilter *cf, struct Curl_easy *data, con…` · [lib/vtls/wolfssl.c:L386-L463][f1]

Serializes a wolfSSL session and stores it in the TLS session cache.

Clears *pscs and exits with success if session is NULL. Measures the DER length with wolfSSL_i2d_SSL_SESSION(session, NULL); a non-positive length yields CURLE_FAILED_INIT. Allocation failure of the serialization buffer yields CURLE_OUT_OF_MEMORY. Serialization into the buffer failing also yields CURLE_FAILED_INIT. Non-empty QUIC transport parameters are cloned; clone failure frees the buffer and returns CURLE_OUT_OF_MEMORY. With WOLFSSL_EARLY_DATA the session's max early-data is recorded. The cache entry is created with expiry = now + session timeout; for FTP connections a duplicate session is produced for *pscs. On success the entry is handed to Curl_ssl_scache_put, transferring ownership; out frees leftovers and any unowned session objects.

uses: [wssl_vtls_new_session_cb](r10-wolfssl-session-cache.md#u-b0b33e18616e)

**Uncertainties.**

- The comment warns wolfSSL might one day advance the i2d pointer argument; current code assumes it does not.

<a id="u-aac78449d9ba"></a>
### `wssl_apply_session`

`static bool wssl_apply_session( struct Curl_cfilter *cf, struct Curl_easy *data, stru…` · [lib/vtls/wolfssl.c:L512-L574][f1]

Decodes a cached session and applies it to the SSL handle, returning whether reuse succeeded.

It attempts application only when session data exists and the session's ALPN is absent or contained in the offered ALPN list. Decoding via wolfSSL_d2i_SSL_SESSION failure logs 'could not decode previous session' and returns FALSE. If wolfSSL_set_session rejects the session, an info message says it is removed from cache and FALSE is returned; on acceptance the session is reused and TRUE is set. When early data is configured, the connection is not connect_only, and the negotiated version is exactly 'TLSv1.3', it optionally calls sess_reuse_cb; a callback error aborts with FALSE. With WOLFSSL_EARLY_DATA and do_early_data, the ALPN list is restricted to the session's protocol and the SSL handle's max early data is set (clamping to UINT_MAX); without support it only asserts do_early_data is false. The decoded session is always freed; success is the return value.

**Uncertainties.**

- Session-cache removal on set_session rejection is stated in the log message but the actual removal is done elsewhere; not visible here.

<a id="u-1982430f9387"></a>
### `wssl_on_session_reuse`

`static CURLcode wssl_on_session_reuse(struct Curl_cfilter *cf, struct Curl_easy *data…` · [lib/vtls/wolfssl.c:L491-L510][f1]

Session-reuse callback adapter that records the maximum early-data size before delegating.

With WOLFSSL_EARLY_DATA it reads earlydata_max from the current session on the SSL handle; otherwise sets 0 (the comment notes there is no wolfSSL way to signal 'no EarlyData' in a stored session). It then forwards to Curl_on_session_reuse, which decides do_early_data.

<a id="u-b0b33e18616e"></a>
### `wssl_vtls_new_session_cb`

`static int wssl_vtls_new_session_cb(WOLFSSL *ssl, WOLFSSL_SESSION *session)` · [lib/vtls/wolfssl.c:L465-L488][f1]

wolfSSL new-session callback that caches each negotiated session.

Reads the connection filter from the SSL app data and, when the filter, connection, session, and current data are all present, calls Curl_wssl_cache_session with the peer's scache key, negotiated ALPN, and TLS version. If a session object comes back it replaces connssl->session, destroying the previous one. Always returns 0. Compiled only with HAVE_EX_DATA.

calls: [Curl_wssl_cache_session](r10-wolfssl-session-cache.md#u-9213b8833ca8)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/wolfssl.c
