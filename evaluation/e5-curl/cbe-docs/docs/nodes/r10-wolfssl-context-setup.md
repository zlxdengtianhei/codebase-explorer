# wolfSSL Context Setup

**Capability.** Owns constructing the wolfSSL client context and per-connection handle: TLS versions, cipher and curve lists, client certificates, ECH, and the cached multi-level X509 trust store.

Use this child when changing how wolfSSL contexts are configured or how CA material is loaded and cached. Curl_wssl_ctx_init orchestrates the smaller config helpers; the X509 cache enables store reuse across connections.

Parent: [wolfSSL TLS Backend](r10-tls-wolfssl.md)

## Units (19)

<a id="u-87753aa47fb6"></a>
### `Curl_wssl_ctx_init`

`CURLcode Curl_wssl_ctx_init(struct wssl_ctx *wctx, struct Curl_cfilter *cf, struct Cu…` · [lib/vtls/wolfssl.c:L1314-L1425][f1]

Builds the wolfSSL client context: method, CTX, TLS versions, ciphers, curves, client certificate, verification mode, SNI, session callback, and ECH, then creates the SSL handle.

Fails with CURLE_FAILED_INIT when the filter config is missing. Creates wolfTLS_client_method (failure: OUT_OF_MEMORY); frees any pre-existing ssl_ctx and creates a new one (failure: OUT_OF_MEMORY). Then in order: ssl_version, wssl_init_ciphers, wssl_init_curves, wssl_client_cert — any failure aborts. Sets verify mode to WOLFSSL_VERIFY_PEER or VERIFY_NONE based on verifypeer. With SNI support and peer->sni shorter than USHRT_MAX, wolfSSL_CTX_UseSNI failure returns CURLE_SSL_CONNECT_ERROR. With HAVE_EX_DATA and cache usable on non-QUIC transport, registers wssl_vtls_new_session_cb. Runs cb_setup if provided. If an application ssl_fsslctx callback is set, ensures the X509 store is set up first and then invokes it, treating its failure as 'error signaled by SSL ctx callback'; on NO_FILESYSTEM builds without the callback, verifypeer fails because certificates cannot be loaded. Then creates the SSL handle and, when ECH is enabled, configures it.

calls: [ssl_version](r10-wolfssl-context-setup.md#u-d1a3054e7147), [wssl_init_ciphers](r10-wolfssl-context-setup.md#u-626a96665211), [wssl_init_curves](r10-wolfssl-context-setup.md#u-79adfea7045f), [wssl_client_cert](r10-wolfssl-context-setup.md#u-2737801e77a5), [Curl_wssl_setup_x509_store](r10-wolfssl-context-setup.md#u-9c68b26fbb46), [wssl_init_ssl_handle](r10-wolfssl-context-setup.md#u-ce8985e628c4), [wssl_init_ech](r10-wolfssl-context-setup.md#u-ac78404b25e4); uses: [wssl_vtls_new_session_cb](r10-wolfssl-session-cache.md#u-b0b33e18616e)

<a id="u-5013a7d95390"></a>
### `lib/vtls/wolfssl.c:if`

`else if(conn_config->verifypeer)` · [lib/vtls/wolfssl.c:L1425-L1432][f1]

Tail cleanup of Curl_wssl_ctx_init: on any error result it frees and NULLs wctx->ssl and wctx->ssl_ctx, so a failed init leaves the wssl_ctx with no live wolfSSL objects.

Success leaves both intact.

<a id="u-d1a3054e7147"></a>
### `ssl_version`

`static CURLcode ssl_version(struct Curl_easy *data, struct ssl_filter_config *conn_co…` · [lib/vtls/wolfssl.c:L996-L1063][f1]

Translates the configured min/max TLS versions into OpenSSL-style version constants and applies them to the SSL context.

Resets both outputs to 0. Min version mapping supports TLSv1 generic, TLSv1_0..TLSv1_3 (the last only with WOLFSSL_TLS13); any other value fails with CURLE_SSL_CONNECT_ERROR. Max version mapping supports MAX_TLSv1_0..MAX_TLSv1_3 (1.3 only with WOLFSSL_TLS13); MAX_DEFAULT and MAX_NONE leave max at 0 (unset); other values fail. Sets the minimum via wolfSSL_CTX_set_min_proto_version (failure: CURLE_SSL_CONNECT_ERROR) and, only when a max was resolved, the maximum (failure: same code).

<a id="u-a890b8473813"></a>
### `wssl_legacy_CTX_set_min_proto_version`

`static int wssl_legacy_CTX_set_min_proto_version(WOLFSSL_CTX *ctx, int version)` · [lib/vtls/wolfssl.c:L864-L890][f1]

Fallback for wolfSSL builds lacking wolfSSL_CTX_set_min_proto_version (no OPENSSL_EXTRA).

Emulates the OpenSSL semantics by trying successively newer minimum versions with wolfSSL_CTX_SetMinVersion: starting at the requested version (default TLS1), each attempt falls through to the next higher version on failure until TLS1_2, and additionally TLS1_3 when WOLFSSL_TLS13 is available. Returns the last result if all attempts fail. Compiled only without OPENSSL_EXTRA and installed via macro over wolfSSL_CTX_set_min_proto_version.

<a id="u-cf00df3430f2"></a>
### `wssl_legacy_CTX_set_max_proto_version`

`static int wssl_legacy_CTX_set_max_proto_version(WOLFSSL_CTX *ctx, int version)` · [lib/vtls/wolfssl.c:L892-L896][f1]

Fallback max-version setter that ignores its arguments and always returns WOLFSSL_NOT_IMPLEMENTED.

Without OPENSSL_EXTRA it is macro-installed as wolfSSL_CTX_set_max_proto_version, so max-version restriction is unsupported on legacy builds.

<a id="u-626a96665211"></a>
### `wssl_init_ciphers`

`static CURLcode wssl_init_ciphers(struct Curl_easy *data, struct wssl_ctx *wctx, stru…` · [lib/vtls/wolfssl.c:L1069-L1123][f1]

Applies the configured cipher list to the SSL context.

Without WOLFSSL_TLS13 it simply sets conn_config->cipher_list if present, failing with CURLE_SSL_CIPHER when SSL_CTX_set_cipher_list rejects it. With TLS 1.3 support and any cipher list configured, it builds a combined list in a dynbuf capped at 4096 chars: the TLS 1.3 part is the configured cipher_list13 or the built-in TLS13 ciphers (via wssl_add_default_ciphers) but only when tls_max is 0 or >= TLS1_3_VERSION; the TLS<=1.2 part is the configured cipher_list or the built-in non-TLS13 ciphers, but only when tls_min < TLS1_3_VERSION. Setting the combined list failure returns CURLE_SSL_CIPHER. The dynbuf is always freed.

calls: [wssl_add_default_ciphers](r10-wolfssl-context-setup.md#u-b3b14b99944c)

<a id="u-b3b14b99944c"></a>
### `wssl_add_default_ciphers`

`static CURLcode wssl_add_default_ciphers(bool tls13, struct dynbuf *buf)` · [lib/vtls/wolfssl.c:L837-L860][f1]

Appends wolfSSL's built-in cipher names, filtered by TLS version family, to a dynbuf as a colon-separated list.

Iterates wolfSSL_get_cipher_list(i); a name starting with 'TLS13' is included when tls13 is true, others when tls13 is false. Adds a colon separator when the buffer is non-empty, then the name. Separator addition failure propagates its CURLcode; name addition failure returns CURLE_OUT_OF_MEMORY. Compiled only with WOLFSSL_TLS13.

<a id="u-79adfea7045f"></a>
### `wssl_init_curves`

`static CURLcode wssl_init_curves(struct Curl_easy *data, struct wssl_ctx *wctx, struc…` · [lib/vtls/wolfssl.c:L1135-L1147][f1]

Applies the configured EC curves/groups list to the SSL context.

With no explicit list it leaves wolfSSL's default key-share group selection untouched. Setting failure via wssl_CTX_set1_groups_list (set1_groups_list with OPENSSL_EXTRA, else set1_curves_list, per the comment about PQC/hybrid group acceptance) fails with CURLE_SSL_CIPHER.

<a id="u-ac78404b25e4"></a>
### `wssl_init_ech`

`static CURLcode wssl_init_ech(struct wssl_ctx *wctx, struct Curl_cfilter *cf, struct …` · [lib/vtls/wolfssl.c:L1245-L1311][f1]

Configures ECH for the SSL handle when enabled.

An ech_public (outer name) setting is unsupported and returns CURLE_SSL_CONNECT_ERROR. GREASE mode is accepted as wolfSSL default behavior with no action. An explicit ech_config string is set via wolfSSL_SetEchConfigsBase64; a non-empty config that fails to set only aborts when ech is CURLECH_HARD. Otherwise ECH configs are taken from the HTTPS RR for the origin when available; SetEchConfigs failure or absence of a config aborts only under CURLECH_HARD, otherwise continues with info messages. Successful setup sets trying_ech_now, after which forcing TLS 1.3 minimum on the handle via wolfSSL_set_min_proto_version failure returns CURLE_SSL_CONNECT_ERROR. Compiled only with HAVE_WOLFSSL_CTX_GENERATEECHCONFIG.

**Uncertainties.**

- SetEchConfigsBase64 success with an empty (zero-length) config string takes the else branch and claims setup; boundary of that path is untested here.

<a id="u-2737801e77a5"></a>
### `wssl_client_cert`

`static CURLcode wssl_client_cert(struct Curl_easy *data, struct ssl_filter_config *co…` · [lib/vtls/wolfssl.c:L901-L994][f1]

Loads the client certificate and private key into the SSL context.

With filesystem support it acts when cert_blob or clientcert is set; without, only when cert_blob is set. The certificate type string is mapped via wssl_do_file_type: an unknown type (-1) fails with CURLE_BAD_FUNCTION_ARGUMENT ('unknown cert type'). PEM uses the certificate-chain loader, ASN1 the plain certificate loader, each taking the blob when present, else the file. A loader return other than 1 fails with CURLE_SSL_CONNECT_ERROR. When no separate key blob/file is configured the certificate source is reused as the key; otherwise the key type string is re-mapped. Private key loading failure (return != 1) yields CURLE_SSL_CONNECT_ERROR. Success returns CURLE_OK.

calls: [wssl_do_file_type](r10-wolfssl-context-setup.md#u-f116c68a0044)

<a id="u-f116c68a0044"></a>
### `wssl_do_file_type`

`static int wssl_do_file_type(const char *type)` · [lib/vtls/wolfssl.c:L211-L220][f1]

Maps a certificate-type string to a wolfSSL file-type constant.

NULL or empty string defaults to WOLFSSL_FILETYPE_PEM; case-insensitive 'PEM' yields PEM, 'DER' yields WOLFSSL_FILETYPE_ASN1, any other value returns -1 which callers treat as an unknown type.

<a id="u-9c68b26fbb46"></a>
### `Curl_wssl_setup_x509_store`

`CURLcode Curl_wssl_setup_x509_store(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/vtls/wolfssl.c:L781-L834][f1]

Prepares the CA verification store for the SSL context, using the multi-level X509 store cache when eligible.

Marks x509_store_setup done unconditionally first, so this runs at most once per context regardless of outcome. The store is cacheable only when ssl_ca_cache_timeout is nonzero, verifypeer is on, and no CApath, CA blob, CRL file, or native CA store is configured. Four cases: if a cached store is already installed in the context nothing happens; if a cached store exists and up_ref succeeds it is installed via wolfSSL_CTX_set_cert_store; if cacheable but no usable cache, a fresh WOLFSSL_X509_STORE is created (failure returns CURLE_OUT_OF_MEMORY), installed, populated via wssl_populate_x509_store, and cached on success; otherwise the context's own store is populated without caching.

calls: [wssl_populate_x509_store](r10-wolfssl-context-setup.md#u-402f3929ed14), [wssl_set_cached_x509_store](r10-wolfssl-context-setup.md#u-fe9f10e82932)

<a id="u-402f3929ed14"></a>
### `wssl_populate_x509_store`

`static CURLcode wssl_populate_x509_store(struct Curl_cfilter *cf, struct Curl_easy *d…` · [lib/vtls/wolfssl.c:L576-L664][f1]

Fills the SSL context's CA verification sources from the filter config.

CURLOPT_CAINFO_BLOB overrides CURLOPT_CAINFO. Under a filesystem build: if a native CA store is configured, wolfSSL_CTX_load_system_CA_Certs failure is only a warning; success marks native CA imported. A CA blob is loaded with wolfSSL_CTX_load_verify_buffer as PEM; failure returns CURLE_SSL_CACERT_BADFILE. Then, when CAfile or CApath is set, wolfSSL_CTX_load_verify_locations_ex with IGNORE_ERR is used; on failure it fails with CURLE_SSL_CACERT_BADFILE only if verifypeer is set AND neither native CA nor blob was imported, otherwise it continues with an info warning. A NULL store returns CURLE_OUT_OF_MEMORY (only reached in the filesystem branch). Without filesystem support only the blob path exists. The store parameter itself is unused.

**Uncertainties.**

- wolfSSL_CTX_load_system_CA_certs is called on wssl->ssl_ctx while the parameter named store is unused; whether that mismatch matters is not determinable from this source.

<a id="u-23d639ba79dc"></a>
### `wssl_cached_x509_store_different`

`static bool wssl_cached_x509_store_different(struct Curl_cfilter *cf, const struct ws…` · [lib/vtls/wolfssl.c:L701-L709][f1]

Returns whether the cached store was built for a different CAfile than the current config.

If either the stored or configured CAfile is NULL, difference is defined by pointer inequality (so NULL vs set counts as different); otherwise a strcmp of the two paths decides.

<a id="u-ea02a4f7427d"></a>
### `wssl_cached_x509_store_expired`

`static bool wssl_cached_x509_store_expired(struct Curl_easy *data, const struct wssl_…` · [lib/vtls/wolfssl.c:L689-L699][f1]

Returns whether the cached X509 store has exceeded its configured age.

A negative ssl_ca_cache_timeout means never expire (returns FALSE); otherwise TRUE when elapsed time since the share's creation reaches timeout in milliseconds.

<a id="u-5365baf5812f"></a>
### `wssl_get_cached_x509_store`

`static WOLFSSL_X509_STORE *wssl_get_cached_x509_store(struct Curl_cfilter *cf, struct…` · [lib/vtls/wolfssl.c:L711-L729][f1]

Looks up the shared X509 store in the multi's proto_hash under MPROTO_WSSL_X509_KEY.

Returns the store only when a share entry exists with a store, it is not expired, and it matches the current CAfile; otherwise NULL. Returns NULL when data->multi is absent despite the debug assertion.

<a id="u-fe9f10e82932"></a>
### `wssl_set_cached_x509_store`

`static void wssl_set_cached_x509_store(struct Curl_cfilter *cf, struct Curl_easy *dat…` · [lib/vtls/wolfssl.c:L731-L779][f1]

Stores an X509 store in the multi-level cache for reuse across connections.

Does nothing if data->multi is missing. Creates and registers a new wssl_x509_share entry if none exists, freeing the allocation or bailing out silently if hash insertion fails. Only when wolfSSL_X509_STORE_up_ref succeeds does it clone the current CAfile (clone failure frees the store ref and returns); it then replaces any previously cached store and CAfile and stamps the current time. All failure paths are silent (no error reporting).

<a id="u-71d9b8153635"></a>
### `wssl_x509_share_free`

`static void wssl_x509_share_free(const void *key, size_t key_len, void *p)` · [lib/vtls/wolfssl.c:L675-L687][f1]

Hash destructor for the per-multi X509 store share.

Debug-asserts the key matches MPROTO_WSSL_X509_KEY, frees the cached WOLFSSL_X509_STORE if present, then frees the CAfile string and the share struct itself.

<a id="u-ce8985e628c4"></a>
### `wssl_init_ssl_handle`

`static CURLcode wssl_init_ssl_handle( struct wssl_ctx *wctx, struct Curl_cfilter *cf,…` · [lib/vtls/wolfssl.c:L1149-L1242][f1]

Creates the per-connection SSL handle and configures session reuse, ALPN, key logging, and secure renegotiation.

wolfSSL_new failure returns CURLE_OUT_OF_MEMORY. With HAVE_EX_DATA the user data pointer is stored as app data; with WOLFSSL_QUIC and QUIC transport the legacy codepoint usage is disabled. Special FTP case: on the secondary socket of a non-proxy filter it fetches the control connection's session and applies it, so servers requiring the same TLS session on data connections succeed. Otherwise, if the session cache is usable, it takes the cached session for the peer key; successful application returns the session to the cache, failure destroys it. With ALPN support and a non-empty spec, wolfSSL_UseALPN with CONTINUE_ON_MISMATCH failure returns CURLE_SSL_CONNECT_ERROR. With OPENSSL_EXTRA and key logging enabled it calls wolfSSL_KeepArrays and, when available, installs the TLS 1.3 secret callback. With secure renegotiation support, wolfSSL_UseSecureRenegotiation failure returns CURLE_SSL_CONNECT_ERROR.

calls: [wssl_apply_session](r10-wolfssl-session-cache.md#u-aac78449d9ba); uses: [wssl_tls13_secret_callback](r10-wolfssl-support.md#u-4141cd7e6ca8)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/wolfssl.c
