# mbedTLS Handshake & Session

**Capability.** Driving and configuring the TLS handshake: version/cipher setup, SSL context assembly, BIO bridges to the filter chain, session reuse, send/recv, shutdown/close and process-global crypto services.

Read to understand how mbed_connect_step1/step2 assemble and run the handshake, how BIO callbacks route bytes through connection filters, and how sessions are cached or applied. Also covers backend init/cleanup, random, SHA-256, version, internals and data-pending queries.

**Depends on.**

- [mbedTLS Credentials & Verification](r2-mbedtls-certs.md) · model-inferred · 0 edge(s)

Parent: [mbedTLS vTLS Backend](r2-tls-mbedtls.md)

## Units (27)

<a id="u-45f3f1a98555"></a>
### `mbed_ssl_backend_data`

`struct mbed_ssl_backend_data` · [lib/vtls/mbedtls.c:L77-L94][f1]

Per-connection mbedTLS backend state, allocated by the backend factory size.

It owns the SSL context, CA and client certificates, optional CRL, private key, and SSL config; plus an ALPN protocol name array, a heap-allocated ciphersuite array that must outlive the config, and flags tracking context initialization, shutdown sent, and a blocked partial send whose exact length is remembered so mbed_send can retry with the same byte count.

uses: [mbedtls.c module code (L1678–L1723)][f1]

<a id="u-b8cfebd108c4"></a>
### `rng_context_t`

`struct rng_context_t` · [lib/vtls/mbedtls.c:L99-L102][f1]

Groups entropy and CTR-DRBG contexts into one static RNG holder used by mbedTLS < 4.0 for randomized operations (key parsing, SSL config RNG).

It is file-static, so all connections share one seeded DRBG initialized by mbedtls_init.

**Uncertainties.**

- Thread safety of the shared static rng instance is not established by this file.

<a id="u-40d85eabdf9b"></a>
### `mbedtls.c module code (L171–L253)`

`module_region` · [lib/vtls/mbedtls.c:L171-L253][f1]

Region containing mbed_set_ssl_version_min_max.

It translates curl's requested TLS version range into mbedTLS bounds. Defaults: minimum TLS 1.2 (TLS 1.3 if TLS 1.2 support is absent), maximum TLS 1.3 (TLS 1.2 if TLS 1.3 support is absent). Minimum: CURL_SSLVERSION_TLSv1/TLSv1_0/TLSv1_1/TLSv1_2 select TLS 1.2 when MBEDTLS_SSL_PROTO_TLS1_2 is built; TLSv1_3 selects TLS 1.3 when TLS 1.3 is built; any other value, or a case whose protocol macro is undefined (falling through to default), fails with 'unsupported minimum TLS version value' and CURLE_SSL_CONNECT_ERROR. Maximum: MAX_DEFAULT/MAX_NONE/MAX_TLSv1_3 select TLS 1.3 when built; MAX_TLSv1_2 selects TLS 1.2 when built; MAX_TLSv1_1, MAX_TLSv1_0, or a case disabled by build config fails with 'unsupported maximum TLS version value' and CURLE_SSL_CONNECT_ERROR. On success both bounds are applied to backend->config.

**Uncertainties.**

- Whether TLS 1.0/1.1 are ever accepted depends on compile macros not visible here; when MBEDTLS_SSL_PROTO_TLS1_2 is undefined those curl values fall through to the failure branch.

<a id="u-42b693029482"></a>
### `mbedtls.c module code (L276–L391)`

`module_region` · [lib/vtls/mbedtls.c:L276-L391][f1]

Region containing mbed_set_selected_ciphers, which builds a ciphersuite list from the user's TLS 1.2 and TLS 1.3 cipher strings.

It enumerates mbedtls_ssl_list_ciphersuites() and mallocs an int array of that capacity plus terminator (allocation failure: CURLE_OUT_OF_MEMORY). With TLS 1.3 support: no TLS 1.3 list means all supported suites whose name starts with 'TLS1-3' are preselected (default13_count marks that prefix); a TLS 1.3 list, when given, is parsed first and then the TLS 1.2 list. Each token is resolved via mbed_cipher_suite_walk_str, rejected with an infof message when unknown or unsupported, and skipped as a duplicate outside the default TLS 1.3 block (the duplicate scan also bounds the array). Without TLS 1.3 support only the TLS 1.2 list is parsed. If a TLS 1.3-only selection ends up with no non-TLS1-3 suites and ciphers12 is absent, all supported non-'TLS1-3' suites are appended. A zero-length final selection fails with 'no supported cipher in list' and CURLE_SSL_CIPHER; on success the array is stored in backend->ciphersuites (mbedTLS does not copy it, so it must outlive the config) and handed to mbedtls_ssl_conf_ciphersuites.

**Uncertainties.**

- Precise duplicate-message suppression for suites overlapping the default TLS 1.3 prefix (default13_count) assumes that field is 0 when a TLS 1.3 list was supplied.

<a id="u-598c1df7d954"></a>
### `mbedtls.c module code (L826–L1035)`

`module_region` · [lib/vtls/mbedtls.c:L826-L1035][f1]

Region containing mbed_configure_ssl, which assembles the client SSL configuration.

It initializes config defaults (client, stream, default preset; failure: CURLE_SSL_CONNECT_ERROR), installs the debug callback at threshold 4 when MBEDTLS_DEBUG is on, enables TLS 1.3 session-ticket signaling on mbedTLS 3.6.1–3.x, always registers mbed_verify_cb with VERIFY_REQUIRED authmode (flag clearing happens in the callback), initializes the SSL context (marked initialized), selects the 'next' cert profile, applies the version range via mbed_set_ssl_version_min_max, and on mbedTLS < 4 sets the shared DRBG as RNG. mbedtls_ssl_setup failure is CURLE_SSL_CONNECT_ERROR. The BIO callbacks are attached to the filter. Ciphers: user lists go through mbed_set_selected_ciphers (failure propagated after an extra failf); without user lists the library default list is used. Renegotiation is enabled when supported; session tickets are disabled. On a SECONDARYSOCKET non-proxy filter (FTP), the control connection's cached session is applied via mbed_apply_session; otherwise a session is taken from the shared cache, loaded and set (failures logged, non-fatal), then returned to the cache. The CA chain (with optional CRL) and own certificate (when a key is configured) are set. Hostname for SNI/CN checks prefers peer.sni over the origin host; failure is CURLE_SSL_CONNECT_ERROR. ALPN protocols are copied into backend->protocols (mbedTLS does not clone the array) and configured; failure is CURLE_SSL_CONNECT_ERROR. Finally the application ssl_fsslctx callback may modify the config; its failure is only logged, and its result is the function's return value.

calls: [mbed_apply_session](r2-mbedtls-handshake.md#u-8f3ea77ba12d), [mbed_verify_cb](r2-mbedtls-certs.md#u-d80facdd38ba)

**Uncertainties.**

- The final 'return result' after the ssl_fsslctx callback: if the callback was never invoked, result holds the value of the last assignment, which is CURLE_OK from the cipher-list else-branch only by control-flow accident; this ordering is fragile to refactor.

<a id="u-0cfb8beee6dd"></a>
### `mbedtls.c module code (L1063–L1068)`

`module_region` · [lib/vtls/mbedtls.c:L1063-L1068][f1]

Compile-time definition of HAVE_PINNED_PUBKEY when mbedTLS offers PK writing and keeps the peer certificate; gates pinned-public-key support in step 2 and the SSLSUPP_PINNEDPUBKEY support flag.

<a id="u-3f339025f12b"></a>
### `mbedtls_connect`

`static CURLcode mbedtls_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bool…` · [lib/vtls/mbedtls.c:L1540-L1589][f1]

Drives the TLS handshake state machine.

A completed connection reports done immediately. Otherwise it runs step1 when in state 1 and step2 when in state 2, returning on the first error (step2 may return success while needing I/O, leaving the state for a later call). In state 3, sessions are only captured for TLS 1.2 or below (mbed_new_session failure aborts); state then becomes ssl_connect_done, at which point connssl->state is set to ssl_connection_complete and done is reported true.

calls: [mbed_connect_step1](r2-mbedtls-handshake.md#u-77d9b133a618), [mbed_connect_step2](r2-mbedtls-handshake.md#u-223bcf26da77), [mbed_new_session](r2-mbedtls-handshake.md#u-b52dfbe27204)

<a id="u-77d9b133a618"></a>
### `mbed_connect_step1`

`static CURLcode mbed_connect_step1(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/mbedtls.c:L1036-L1063][f1]

First TLS connect phase: rejects SSLv2/SSLv3 requests with CURLE_NOT_BUILT_IN, then loads CA cert, client cert, private key, and CRL in sequence, each only attempted when all prior steps succeeded, and finally configures the SSL context.

Any failure short-circuits and is returned; on success the connecting state advances to ssl_connect_2.

calls: [mbedtls.c module code (L826–L1035)](r2-mbedtls-handshake.md#u-598c1df7d954), [mbed_load_cacert](r2-mbedtls-certs.md#u-d1c88e34358e), [mbed_load_clicert](r2-mbedtls-certs.md#u-cf8892bc230b), [mbed_load_privkey](r2-mbedtls-certs.md#u-89af3a14cdee), [mbed_load_crl](r2-mbedtls-certs.md#u-4f763aa27a66)

<a id="u-223bcf26da77"></a>
### `mbed_connect_step2`

`static CURLcode mbed_connect_step2(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/mbedtls.c:L1069-L1199][f1]

Second TLS connect phase: runs the handshake and handles its outcomes.

WANT_READ/WANT_WRITE record the needed I/O in connssl->io_need and return CURLE_OK so the transfer layer can wait; X509 verify failure is CURLE_PEER_FAILED_VERIFICATION; any other error is logged and CURLE_SSL_CONNECT_ERROR. On success the negotiated TLS version and cipher name are logged (via mbed_cipher_suite_get_str). With pinned-public-key support configured, the peer certificate must exist; it is copied (via a parsed DER copy because the DER writer needs a non-const key), its public key is DER-encoded into a PUB_DER_MAX_BYTES buffer written at the buffer end, and matched through Curl_pin_peer_pubkey; missing cert, copy failure, or key extraction failure yield CURLE_SSL_PINNEDPUBKEYNOTMATCH (allocation failures: CURLE_OUT_OF_MEMORY), and all temp resources are freed on every path. With ALPN the negotiated protocol is reported via Curl_alpn_set_negotiated (error propagated). Success advances to ssl_connect_3 and logs 'SSL connected'.

calls: [mbed_cipher_suite_get_str](r2-mbedtls-handshake.md#u-e47eb57717d5)

**Uncertainties.**

- When HAVE_PINNED_PUBKEY is defined, a Curl_pin_peer_pubkey mismatch returns its result; when it is undefined, pinning is silently unsupported, matching the SSLSUPP flags.

<a id="u-0356d479f30c"></a>
### `mbedtls_bio_cf_read`

`static int mbedtls_bio_cf_read(void *bio, unsigned char *buf, size_t blen)` · [lib/vtls/mbedtls.c:L150-L171][f1]

BIO read callback bridging mbedTLS to the connection filter chain.

Receives through cf->next into the caller buffer; CURLE_AGAIN maps to MBEDTLS_ERR_SSL_WANT_READ, other errors to -1, success to the byte count. Returns 0 when no current Curl_easy exists or the buffer is NULL, mirroring OpenSSL's tolerance of a NULL buffer.

uses: [mbedtls.c module code (L826–L1035)](r2-mbedtls-handshake.md#u-598c1df7d954)

<a id="u-47a1302a9712"></a>
### `mbedtls_bio_cf_write`

`static int mbedtls_bio_cf_write(void *bio, const unsigned char *buf, size_t blen)` · [lib/vtls/mbedtls.c:L130-L148][f1]

BIO write callback bridging mbedTLS to the connection filter chain.

Sends through cf->next; CURLE_AGAIN maps to MBEDTLS_ERR_SSL_WANT_WRITE so mbedTLS retries later, any other error maps to -1, success returns the written byte count. With no current Curl_easy (asserted in debug builds) it returns 0 without sending.

uses: [mbedtls.c module code (L826–L1035)](r2-mbedtls-handshake.md#u-598c1df7d954)

<a id="u-8f3ea77ba12d"></a>
### `mbed_apply_session`

`static bool mbed_apply_session(struct Curl_cfilter *cf, struct Curl_easy *data, struc…` · [lib/vtls/mbedtls.c:L796-L826][f1]

Applies a cached TLS session to the backend SSL context, used for FTP data connections reusing the control connection's session.

Only acts when the session holds non-empty serialized data; a load or set failure logs the negative mbedTLS code and returns FALSE, while success logs 'SSL reusing session ID' and returns TRUE. The loaded mbedtls_ssl_session is freed on every path.

calls: [mbedtls.c module code (L826–L1035)](r2-mbedtls-handshake.md#u-598c1df7d954)

<a id="u-b52dfbe27204"></a>
### `mbed_new_session`

`static CURLcode mbed_new_session(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/mbedtls.c:L1201-L1271][f1]

Captures the current TLS session and stores it in the shared session cache.

Skips entirely when the cache is not in use. Retrieves the session from the SSL context (ALLOC_FAILED still allows freeing; other failures are CURLE_SSL_CONNECT_ERROR), sizes it with a probe save call (zero length: non-CURLcode failure logged), serializes into a malloc buffer (allocation failure: CURLE_OUT_OF_MEMORY), and creates a cache session tagged with the negotiated TLS version and ALPN; the buffer's ownership passes to the created session. For FTP connections the session is also duplicated into connssl->session (destroying any prior one). Finally the session is put into the cache; on cache-put failure the session is destroyed in cleanup. All temporary resources are freed on every exit path.

**Uncertainties.**

- If Curl_ssl_session_create fails, the duplicate for FTP is skipped and the error propagates; the cache is not updated.

<a id="u-d79f7779e689"></a>
### `mbed_send`

`static CURLcode mbed_send(struct Curl_cfilter *cf, struct Curl_easy *data, const void…` · [lib/vtls/mbedtls.c:L1273-L1345][f1]

Encrypts and sends application data through the SSL context.

Resets io_need and the write count first. If a previous write blocked, the call must use the same byte count again; when the caller now offers fewer bytes the call fails with CURLE_BAD_FUNCTION_ARGUMENT, otherwise the remembered blocked length replaces len. A non-negative mbedtls_ssl_write result clears the blocked state and reports the count. Negative results: TLS 1.3 RECEIVED_NEW_SESSION_TICKET triggers mbed_new_session and, on success, retries the whole send; WANT_READ/WANT_WRITE set io_need and return CURLE_AGAIN, recording the blocked length when not already blocked so the retry resends exactly the same range; any other error is CURLE_SEND_ERROR.

calls: [mbed_new_session](r2-mbedtls-handshake.md#u-b52dfbe27204)

<a id="u-80e563bdfbaf"></a>
### `mbed_recv`

`static CURLcode mbed_recv(struct Curl_cfilter *cf, struct Curl_easy *data, char *buf,…` · [lib/vtls/mbedtls.c:L1461-L1514][f1]

Reads decrypted data from the SSL context.

Positive counts are reported. Negative results: TLS 1.3 RECEIVED_NEW_SESSION_TICKET stores the ticket via mbed_new_session and retries the read when that succeeded; WANT_READ/WANT_WRITE set io_need and return CURLE_AGAIN; PEER_CLOSE_NOTIFY maps to CURLE_OK with zero bytes read (clean EOF); any other error is logged with its mbedTLS message and returned as CURLE_RECV_ERROR.

calls: [mbed_new_session](r2-mbedtls-handshake.md#u-b52dfbe27204)

<a id="u-5e73f1015e09"></a>
### `mbedtls_init`

`static int mbedtls_init(void)` · [lib/vtls/mbedtls.c:L1595-L1626][f1]

Initializes the backend once per process: returns 0 if psa_crypto_init fails.

On mbedTLS < 4 it additionally seeds the shared static CTR-DRBG from entropy (seed failure: 0) and enables prediction resistance, re-gathering entropy before each random call. Returns 1 on success.

**Uncertainties.**

- Repeat invocation re-initializes the static DRBG without freeing prior state; behavior of double init is not defined here.

<a id="u-ad0e48f877a1"></a>
### `mbedtls_cleanup`

`static void mbedtls_cleanup(void)` · [lib/vtls/mbedtls.c:L1628-L1636][f1]

Tears down backend-global state: frees PSA crypto, and on mbedTLS < 4 also frees the shared DRBG and entropy contexts.

<a id="u-2019120cb323"></a>
### `mbedtls_random`

`static CURLcode mbedtls_random(struct Curl_easy *data, unsigned char *entropy, size_t…` · [lib/vtls/mbedtls.c:L1529-L1538][f1]

Fills the buffer with random bytes via psa_generate_random, ignoring the Curl_easy argument (which may be NULL).

PSA_SUCCESS returns CURLE_OK; any other status returns CURLE_FAILED_INIT.

<a id="u-84cb199dc474"></a>
### `mbedtls_sha256sum`

`static CURLcode mbedtls_sha256sum(const unsigned char *input, size_t inputlen, unsign…` · [lib/vtls/mbedtls.c:L1650-L1668][f1]

Computes a SHA-256 digest.

When PSA SHA-256 is compiled in, psa_hash_compute fills the output and any PSA failure returns CURLE_BAD_FUNCTION_ARGUMENT; otherwise it falls back to Curl_sha256it.

**Uncertainties.**

- Whether psa_hash_compute can fail for length reasons versus input problems is not distinguishable; all failures map to BAD_FUNCTION_ARGUMENT.

<a id="u-21f5431de757"></a>
### `mbedtls_version`

`static size_t mbedtls_version(char *buffer, size_t size)` · [lib/vtls/mbedtls.c:L1516-L1526][f1]

Renders the backend version string into the caller buffer.

With mbedTLS version support it formats 'mbedTLS/x.y.z' from the numeric version bytes; otherwise it falls back to the compile-time MBEDTLS_VERSION_STRING.

<a id="u-6e1460855a4e"></a>
### `mbedtls_shutdown`

`static CURLcode mbedtls_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data, boo…` · [lib/vtls/mbedtls.c:L1347-L1437][f1]

Performs or completes TLS shutdown.

A non-initialized backend or an already-shutdown filter is instantly done. Sends close_notify once (guarded by sent_shutdown) when requested: success falls through to reading the peer's response; PEER_CLOSE_NOTIFY means done; WANT_READ/WANT_WRITE set io_need and return (retry later); other errors are CURLE_RECV_ERROR. It then reads up to 10 times to drain for the peer's close notify, retrying once on a TLS 1.3 spurious WANT_READ and skipping TLS 1.3 new-session-ticket interrupts; positive data keeps looping. Outcome: ret 0 or PEER_CLOSE_NOTIFY marks done; WANT_READ/WANT_WRITE set io_need for resumption; any other negative result is CURLE_RECV_ERROR. cf->shutdown is set true on any error or completion.

**Uncertainties.**

- The comment flags a suspected mbedTLS TLS 1.3 bug behind the double-read on WANT_READ; exact server-side conditions are unverifiable here.

<a id="u-0215ce2666b7"></a>
### `mbedtls_close`

`static void mbedtls_close(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/mbedtls.c:L1439-L1459][f1]

Releases all backend TLS resources: private key, client and CA certs, optional CRL, the ciphersuite array, and the SSL config; the SSL context is freed only when it was initialized and the flag is then cleared, so a double close is safe.

<a id="u-30bd3dd814eb"></a>
### `mbedtls_data_pending`

`static bool mbedtls_data_pending(struct Curl_cfilter *cf, const struct Curl_easy *data)` · [lib/vtls/mbedtls.c:L1638-L1648][f1]

Reports whether decrypted bytes are already buffered inside the SSL context, via mbedtls_ssl_get_bytes_avail; true when nonzero.

Pure query with no state change.

<a id="u-91d08a5a3f44"></a>
### `mbedtls_get_internals`

`static void *mbedtls_get_internals(struct ssl_connect_data *connssl, CURLINFO info)` · [lib/vtls/mbedtls.c:L1670-L1678][f1]

Returns a pointer to the backend's mbedtls_ssl_context for CURLINFO introspection, ignoring which info was requested.

Asserts the backend exists in debug builds.

<a id="u-57a65e56a2a2"></a>
### `mbed_debug`

`static void mbed_debug(void *context, int level, const char *f_name, int line_nb, con…` · [lib/vtls/mbedtls.c:L112-L127][f1]

mbedTLS debug callback forwarding library debug lines to curl's info log (compiled only with MBEDTLS_DEBUG).

Ignores level, file name, and line number; with a non-NULL Curl_easy it trims one trailing newline and logs the line via infof; a NULL context silently drops the message.

<a id="u-e47eb57717d5"></a>
### `mbed_cipher_suite_get_str`

`static int mbed_cipher_suite_get_str(uint16_t id, char *buf, size_t buf_size, bool pr…` · [lib/vtls/mbedtls.c:L254-L262][f1]

Ciphersuite id-to-name lookup with provisional support for the non-IANA-reserved TLS_ECJPAKE_WITH_AES_128_CCM_8.

For that exact id it writes the literal name into the buffer and returns 0; every other id is delegated to Curl_cipher_suite_get_str. Compiled only when the ECJPAKE suite macro is defined; otherwise a macro alias for the generic function.

calls: [mbed_connect_step2](r2-mbedtls-handshake.md#u-223bcf26da77)

<a id="u-42f76704ae08"></a>
### `mbed_cipher_suite_walk_str`

`static uint16_t mbed_cipher_suite_walk_str(const char **str, const char **end)` · [lib/vtls/mbedtls.c:L264-L276][f1]

Parses the next cipher name from a user list, extending the generic walker with the ECJPAKE suite.

Calls Curl_cipher_suite_walk_str first; if that yields id 0 and the consumed token equals 'TLS_ECJPAKE_WITH_AES_128_CCM_8' case-insensitively at exactly that length, returns the ECJPAKE id. Otherwise returns the walker's result, possibly 0 for unknown names. Only compiled when the ECJPAKE macro is defined; otherwise a macro alias.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/mbedtls.c
