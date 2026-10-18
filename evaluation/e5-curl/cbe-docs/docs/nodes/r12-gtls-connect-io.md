# GnuTLS connect and record IO

**Capability.** Sets up client sessions (priority/version translation, transport push/pull callbacks), drives the non-blocking handshake including 0-RTT early data, and performs record send/receive/shutdown plus backend init, cleanup, and introspection.

Start at gtls_connect/gtls_connect_common for the connection flow and gtls_send/gtls_recv for data transfer. Logging/keylog helpers round out runtime behavior.

**Depends on.**

- [GnuTLS session reuse](r12-gtls-session-cache.md) · model-inferred · 0 edge(s)
- [GnuTLS trust store and shared credentials](r12-gtls-trust-creds.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [GnuTLS server verification](r12-gtls-verification.md) · model-inferred · 0 edge(s)

Parent: [GnuTLS backend](r12-gtls-backend.md)

## Units (25)

<a id="u-6466d2546a1f"></a>
### `Curl_gtls_ctx_init`

`CURLcode Curl_gtls_ctx_init(struct gtls_ctx *gctx, struct Curl_cfilter *cf, struct Cu…` · [lib/vtls/gtls.c:L1125-L1218][f1]

Builds the GnuTLS context for a connection filter, preferring a cached session.

On the secondary socket of a non-proxy filter it first tries the control connection's session (FTP requires the same TLS session). Otherwise, when session caching is on and verifystatus is off, it takes a cached session by scache key and tries to apply it. If neither applied, it runs gtls_client_init with no early data. It stores the ssl user data pointer, runs cb_setup when given, enables the keylog callback when keylog is enabled (under CURL_GNUTLS_EARLY_DATA), converts the ALPN spec to GnuTLS format and sets it as mandatory protocols, failing with CURLE_SSL_CONNECT_ERROR if that call fails. The scache take reference is always returned on exit.

calls: [gtls_apply_session](r12-gtls-session-cache.md#u-870a210fad7b), [gtls_client_init](r12-gtls-connect-io.md#u-7daf82409575)

<a id="u-21d52fd5f8b9"></a>
### `Curl_gtls_version`

`size_t Curl_gtls_version(char *buffer, size_t size)` · [lib/vtls/gtls.c:L2165-L2168][f1]

Writes the 'GnuTLS/<version>' string into the caller buffer via curl_msnprintf and returns the written length.

<a id="u-bc44d49dd2b8"></a>
### `cf_gtls_handshake`

`static CURLcode cf_gtls_handshake(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/gtls.c:L236-L301][f1]

Drives one non-blocking round of the GnuTLS handshake.

It resets io_need and io_result, calls gnutls_handshake, and after the ClientHello prepares the trust store once via Curl_gtls_client_trust_setup, propagating its error. Return handling in order: GNUTLS_E_AGAIN/INTERRUPTED sets io_need to SEND or RECV per gnutls_record_get_direction and returns CURLE_AGAIN; a non-fatal negative rc logs a warning (alert name for GNUTLS_E_WARNING_ALERT_RECEIVED under CURLVERBOSE) and returns CURLE_AGAIN; a fatal rc while io_result is set returns that io_result; any other fatal rc fails with the alert name (GNUTLS_E_FATAL_ALERT_RECEIVED) or GnuTLS error string and returns CURLE_SSL_CONNECT_ERROR; otherwise CURLE_OK.

calls: [Curl_gtls_client_trust_setup](r12-gtls-trust-creds.md#u-f2861cb7fcb3), [gtls_connect_common](r12-gtls-connect-io.md#u-942fed2dddb8); uses: [gtls_recv](r12-gtls-connect-io.md#u-db344e9eab09)

**Uncertainties.**

- Resuming a non-fatal handshake error on a later call relies on GnuTLS keeping the session resumable; that is library behavior not shown here.

<a id="u-8b12b2dd1f30"></a>
### `gnutls_set_ssl_version_min_max`

`static CURLcode gnutls_set_ssl_version_min_max( struct Curl_easy *data, struct ssl_pe…` · [lib/vtls/gtls.c:L323-L394][f1]

Translates requested min/max TLS versions into a GnuTLS priority list string.

Versions at or below CURL_SSLVERSION_TLSv1 are raised to TLS1.0; a NONE/DEFAULT max becomes TLS1.3 when the library supports it, else TLS1.2. For QUIC transport the max must be at least TLS1.3 (else failf and CURLE_SSL_CONNECT_ERROR) and QUIC_PRIORITY is selected. Otherwise a switch over the combined min|max value picks the exact +VERS list for each supported combination; any unmatched combination fails with 'cannot set TLS protocol' and CURLE_SSL_CONNECT_ERROR.

uses: [gtls_client_init](r12-gtls-connect-io.md#u-7daf82409575)

<a id="u-c28dfea2c25c"></a>
### `gtls_cert_status_request`

`static bool gtls_cert_status_request(void)` · [lib/vtls/gtls.c:L2202-L2205][f1]

Backend capability probe that always reports TRUE for certificate status (OCSP) support.

<a id="u-e7d8910f5215"></a>
### `gtls_cleanup`

`static void gtls_cleanup(void)` · [lib/vtls/gtls.c:L167-L171][f1]

Global teardown: deinitializes GnuTLS and closes the TLS keylog file.

<a id="u-7daf82409575"></a>
### `gtls_client_init`

`static CURLcode gtls_client_init(struct Curl_cfilter *cf, struct Curl_easy *data, str…` · [lib/vtls/gtls.c:L882-L1037][f1]

Initializes a client-side GnuTLS session and its credential store.

SSLv2/v3 requests fail immediately. It creates shared creds, computes init flags (client role; early-data and no-end-of-early-data for QUIC with earlydata_max, early-data for TCP sessions announcing a value other than 0xFFFFFFFF, plus optional no-tickets/no-status-request flags) and calls gnutls_init. It sets SNI when a peer name exists, applies the default priority, detects TLS 1.3 support (>= 3.6.5) and rejects a TLSv1_3 request without it, then derives the priority list via gnutls_set_ssl_version_min_max and applies it with gtls_set_priority. With a client cert configured, it first ensures the trust setup, then loads a P12 file via gnutls_certificate_set_x509_simple_pkcs12_file (empty password when none given) or a PEM/DER cert+key pair via gnutls_certificate_set_x509_key_file2 with a fixed set of PKCS encryption algorithms; load failures return CURLE_SSL_CONNECT_ERROR. Finally it sets the credentials on the session and, when verifystatus is on, enables the OCSP status-request extension.

calls: [Curl_gtls_shared_creds_create](r12-gtls-trust-creds.md#u-0ae8a78bdbd1), [gnutls_set_ssl_version_min_max](r12-gtls-connect-io.md#u-8b12b2dd1f30), [gtls_set_priority](r12-gtls-connect-io.md#u-78033c8a869a), [Curl_gtls_client_trust_setup](r12-gtls-trust-creds.md#u-f2861cb7fcb3)

<a id="u-fcaa9fe11bd3"></a>
### `gtls_close`

`static void gtls_close(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/gtls.c:L2103-L2119][f1]

Releases the backend: deinits the GnuTLS session (nulling the pointer) and drops the shared-creds reference via Curl_gtls_shared_creds_free.

calls: [Curl_gtls_shared_creds_free](r12-gtls-trust-creds.md#u-f01b938c2f77)

<a id="u-05f32bc6f0d2"></a>
### `gtls_connect`

`static CURLcode gtls_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bool *d…` · [lib/vtls/gtls.c:L1945-L1959][f1]

Connect entry point that, under CURL_GNUTLS_EARLY_DATA, refuses to make progress when deferred and waiting for early data (reporting done with CURLE_OK); otherwise delegates to gtls_connect_common.

<a id="u-942fed2dddb8"></a>
### `gtls_connect_common`

`static CURLcode gtls_connect_common(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/vtls/gtls.c:L1847-L1943][f1]

State machine completing the TLS connection.

An already-complete connection reports done immediately. State ssl_connect_1 runs gtls_connect_step1 and advances to 2; state 2 (under CURL_GNUTLS_EARLY_DATA) waits in ssl_earlydata_await, flushes early data from ssl_earlydata_sending, then runs cf_gtls_handshake and advances to 3; state 3 reports the handshake, runs gtls_verifyserver, marks the connection complete, reads the negotiated ALPN (absent ALPN treated as empty) and applies it via Curl_alpn_set_negotiated, resolves the early-data accepted/rejected state from GNUTLS_SFLAGS_EARLY_DATA, and advances to done. On CURLE_AGAIN it returns OK with done FALSE; otherwise done reflects the complete/deferred connection state.

calls: [gtls_connect_step1](r12-gtls-connect-io.md#u-996317d03084), [cf_gtls_handshake](r12-gtls-connect-io.md#u-bc44d49dd2b8), [gtls_verifyserver](r12-gtls-verification.md#u-566bc29e3dc3), [gtls_send_earlydata](r12-gtls-connect-io.md#u-d5f3326926cf)

<a id="u-996317d03084"></a>
### `gtls_connect_step1`

`static CURLcode gtls_connect_step1(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/gtls.c:L1220-L1266][f1]

Prepares the GnuTLS layer before handshaking.

It is idempotent for an already-complete connection. It runs Curl_gtls_ctx_init (with gtls_on_session_reuse under CURL_GNUTLS_EARLY_DATA), logs the offered ALPN set unless the connection is deferred, installs gtls_handshake_cb as a post hook for any handshake message, and registers cf as the transport pointer with gtls_push/gtls_pull as push/pull callbacks.

calls: [Curl_gtls_ctx_init](r12-gtls-connect-io.md#u-6466d2546a1f); uses: [gtls_push](r12-gtls-connect-io.md#u-bfd833bf8398), [gtls_pull](r12-gtls-connect-io.md#u-d55858204d44), [gtls_handshake_cb](r12-gtls-session-cache.md#u-b5699d8ef0dc)

<a id="u-2bef3d2cbc80"></a>
### `gtls_data_pending`

`static bool gtls_data_pending(struct Curl_cfilter *cf, const struct Curl_easy *data)` · [lib/vtls/gtls.c:L1961-L1974][f1]

Reports whether GnuTLS holds undelivered decrypted record data, TRUE only when a session exists and gnutls_record_check_pending is nonzero.

<a id="u-2573527f8e68"></a>
### `gtls_get_internals`

`static void *gtls_get_internals(struct ssl_connect_data *connssl, CURLINFO info)` · [lib/vtls/gtls.c:L2207-L2215][f1]

Returns the backend's raw GnuTLS session pointer for CURLINFO introspection; the info argument is ignored.

<a id="u-5c91c6f2bc90"></a>
### `gtls_init`

`static int gtls_init(void)` · [lib/vtls/gtls.c:L156-L165][f1]

Global GnuTLS initialization: returns 1 on success and 0 if gnutls_global_init fails; under GTLSDEBUG it also installs the stderr log callback at level 2.

Per its docstring it is not thread-safe and must run only from curl_global_init.

<a id="u-d55858204d44"></a>
### `gtls_pull`

`static ssize_t gtls_pull(void *s, void *buf, size_t blen)` · [lib/vtls/gtls.c:L109-L143][f1]

GnuTLS transport pull callback reading encrypted data via the next filter.

If the shared creds have no trust store yet, it first builds one with Curl_gtls_client_trust_setup, returning -1 with EINVAL on failure. It stores io_result, maps CURLE_AGAIN to EAGAIN and other errors to EINVAL (returning -1), and on a zero-byte read sets connssl->peer_closed to TRUE before returning the byte count.

calls: [Curl_gtls_client_trust_setup](r12-gtls-trust-creds.md#u-f2861cb7fcb3)

<a id="u-bfd833bf8398"></a>
### `gtls_push`

`static ssize_t gtls_push(void *s, const void *buf, size_t blen)` · [lib/vtls/gtls.c:L85-L107][f1]

GnuTLS transport push callback that sends record output through the next connection filter.

It sends via Curl_conn_cf_send using the current easy handle, stores the CURLcode in backend->gtls.io_result, and on failure maps CURLE_AGAIN to EAGAIN and any other code to EINVAL via gnutls_transport_set_errno, returning -1; success returns the byte count.

uses: [gtls_connect_step1](r12-gtls-connect-io.md#u-996317d03084)

<a id="u-2bf72cabceee"></a>
### `gtls_random`

`static CURLcode gtls_random(struct Curl_easy *data, unsigned char *entropy, size_t le…` · [lib/vtls/gtls.c:L2171-L2178][f1]

Fills a buffer with random bytes via gnutls_rnd; data may be NULL.

Returns CURLE_FAILED_INIT on a nonzero GnuTLS result, else CURLE_OK.

<a id="u-db344e9eab09"></a>
### `gtls_recv`

`static CURLcode gtls_recv(struct Curl_cfilter *cf, struct Curl_easy *data, char *buf,…` · [lib/vtls/gtls.c:L2121-L2163][f1]

Receives decrypted data via gnutls_record_recv.

Nonnegative results set the byte count. GNUTLS_E_AGAIN/INTERRUPTED return CURLE_AGAIN. GNUTLS_E_REHANDSHAKE (TLS 1.2 renegotiation or a TLS 1.3 key update) runs cf_gtls_handshake and, on success, returns CURLE_AGAIN so the caller retries. Any other negative result fails with the GnuTLS error and returns io_result if set, else CURLE_RECV_ERROR.

calls: [cf_gtls_handshake](r12-gtls-connect-io.md#u-bc44d49dd2b8)

<a id="u-5cfa847eec86"></a>
### `gtls_send`

`static CURLcode gtls_send(struct Curl_cfilter *cf, struct Curl_easy *data, const void…` · [lib/vtls/gtls.c:L1976-L2023][f1]

Encrypts and sends a buffer, looping until all bytes are consumed.

Each iteration clears io_result and calls gnutls_record_send. A nonnegative result advances the buffer and total; a result larger than the remainder is treated as a GnuTLS violation, fails, and returns CURLE_SEND_ERROR immediately. A negative result when some bytes were already sent and the error is GNUTLS_E_AGAIN returns success with the partial count; otherwise GNUTLS_E_AGAIN maps to CURLE_AGAIN and other errors to io_result if set, else CURLE_SEND_ERROR.

<a id="u-d5f3326926cf"></a>
### `gtls_send_earlydata`

`static CURLcode gtls_send_earlydata(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/gtls.c:L1799-L1835][f1]

Flushes buffered 0-RTT early data through gnutls_record_send_early_data in a loop.

GNUTLS_E_AGAIN maps to CURLE_AGAIN; other negative results map to io_result if set, else CURLE_SEND_ERROR. GnuTLS returns 0 on success (not a byte count), so a zero return is treated as consuming the whole peeked buffer; anything else skips the returned amount. On full drain it infos the early-data byte count.

<a id="u-78033c8a869a"></a>
### `gtls_set_priority`

`static CURLcode gtls_set_priority(struct Curl_cfilter *cf, struct Curl_easy *data, st…` · [lib/vtls/gtls.c:L838-L880][f1]

Applies the GnuTLS priority string to the session, honoring a user cipher list.

If the cipher list starts with '+', '-' or '!', it is appended after the base priority in a dynamic buffer (which then becomes the effective priority); any other cipher list replaces the base entirely. It logs the effective priority, then calls gnutls_priority_set_direct; failure logs the GnuTLS error and position and returns CURLE_SSL_CONNECT_ERROR. The buffer is always freed.

<a id="u-f38a58d61684"></a>
### `gtls_sha256sum`

`static CURLcode gtls_sha256sum(const unsigned char *input, size_t len, unsigned char …` · [lib/vtls/gtls.c:L2180-L2200][f1]

Computes a SHA-256 digest with nettle, chunking the input into at-most-UINT_MAX updates until consumed.

On nettle >= 4 sha256_digest omits the length argument; older nettle passes sha256len as the digest size. Always returns CURLE_OK.

<a id="u-80f6e8fb1acf"></a>
### `gtls_shutdown`

`static CURLcode gtls_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data, bool s…` · [lib/vtls/gtls.c:L2029-L2101][f1]

Performs TLS shutdown while keeping the socket usable (CCC).

With no session, an already-shutdown filter, or a connection not fully established it reports done immediately. Otherwise it clears io_need; the first call with send_shutdown sends gnutls_bye(GNUTLS_SHUT_RDWR): EAGAIN/INTERRUPTED sets io_need from the record direction, re-arms sent_shutdown for a retry, and returns OK; any other non-success returns CURLE_RECV_ERROR. After our side started shutdown it reads up to ten records waiting for the peer's close_notify: a positive read means data is still arriving (not done), zero means done, EAGAIN/INTERRUPTED sets io_need for a later retry, and other errors give CURLE_RECV_ERROR. On exit cf->shutdown becomes TRUE whenever an error occurred or shutdown completed.

**Uncertainties.**

- The ten-read drain loop's effect on buffered application data (discarding records) is not analyzed further here; source only counts records.

<a id="u-04fc8c0edfdc"></a>
### `keylog_callback`

`static int keylog_callback(gnutls_session_t session, const char *label, const gnutls_…` · [lib/vtls/gtls.c:L1040-L1054][f1]

GnuTLS keylog callback that writes TLS secrets to the keylog file after fetching client/server randoms; it returns -1 when the client random is not 32 bytes, else 0 after Curl_tls_keylog_write.

<a id="u-8502f73e9be1"></a>
### `tls_log_func`

`static void tls_log_func(int level, const char *str)` · [lib/vtls/gtls.c:L64-L67][f1]

Debug-only GnuTLS log callback that prints the log level and message to stderr; compiled only when GTLSDEBUG is defined.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/gtls.c
