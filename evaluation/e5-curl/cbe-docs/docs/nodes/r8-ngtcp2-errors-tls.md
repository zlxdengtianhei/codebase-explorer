# QUIC Errors, TLS Sessions and Diagnostics

**Capability.** Records ngtcp2 and HTTP/3 errors (first-writer wins, closing the connection on fatal codes), caches resumable QUIC TLS sessions across GnuTLS/OpenSSL/wolfSSL backends, resolves the crypto conn-ref, and provides verbose diagnostics (qlog, debug logging, handshake message names, version strings).

Use this subtree for error propagation rules and TLS session resumption for QUIC, and for the verbose/debug helpers used during QUIC troubleshooting.

Parent: [QUIC via ngtcp2](r8-quic-ngtcp2.md)

## Units (11)

<a id="u-5cbaff237170"></a>
### `Curl_cf_ngtcp2_cmn_err_set`

`void Curl_cf_ngtcp2_cmn_err_set(struct Curl_cfilter *cf, struct Curl_easy *data, int …` · [lib/vquic/cf-ngtcp2-cmn.c:L1362-L1378][f1]

Records an ngtcp2-level error in the connection's last_error, first-writer wins.

Only when error_code is still zero: for NGTCP2_ERR_CRYPTO it stores the TLS alert obtained from ngtcp2_conn_get_tls_alert, otherwise the library error via ngtcp2_ccerr_set_liberr. When cf_ngtcp2_err_is_fatal(code) holds, the connection is closed through Curl_cf_ngtcp2_cmn_conn_close.

calls: [cf_ngtcp2_err_is_fatal](r8-ngtcp2-errors-tls.md#u-c353c702db2c), [Curl_cf_ngtcp2_cmn_conn_close](r8-ngtcp2-conn-lifecycle.md#u-220f46099cea)

<a id="u-4424220abf66"></a>
### `Curl_cf_ngtcp2_h3_err_set`

`void Curl_cf_ngtcp2_h3_err_set(struct Curl_cfilter *cf, struct Curl_easy *data, int c…` · [lib/vquic/cf-ngtcp2-cmn.c:L106-L116][f1]

Records an HTTP/3-level error in the connection's last_error and closes the connection when fatal.

Only sets the error if last_error.error_code is still zero, translating the nghttp3 code to a QUIC application error via nghttp3_err_infer_quic_app_error_code. When cf_ngtcp2_h3_err_is_fatal(code) is true it calls Curl_cf_ngtcp2_cmn_conn_close; otherwise the connection stays up.

calls: [cf_ngtcp2_h3_err_is_fatal](r8-ngtcp2-errors-tls.md#u-ef48d233fdb1), [Curl_cf_ngtcp2_cmn_conn_close](r8-ngtcp2-conn-lifecycle.md#u-220f46099cea)

<a id="u-c353c702db2c"></a>
### `cf_ngtcp2_err_is_fatal`

`static bool cf_ngtcp2_err_is_fatal(int code)` · [lib/vquic/cf-ngtcp2-cmn.c:L1355-L1360][f1]

Classifies an ngtcp2 error code as fatal: codes at or below NGTCP2_ERR_FATAL, NGTCP2_ERR_DROP_CONN, or NGTCP2_ERR_IDLE_CLOSE.

<a id="u-ef48d233fdb1"></a>
### `cf_ngtcp2_h3_err_is_fatal`

`static bool cf_ngtcp2_h3_err_is_fatal(int code)` · [lib/vquic/cf-ngtcp2-cmn.c:L100-L104][f1]

Classifies an HTTP/3 error code as fatal.

Returns true when code is at or below NGHTTP3_ERR_FATAL, or when it equals NGHTTP3_ERR_H3_CLOSED_CRITICAL_STREAM; other codes are non-fatal.

calls: [Curl_cf_ngtcp2_h3_err_set](r8-ngtcp2-errors-tls.md#u-4424220abf66)

<a id="u-ecc550fdfd50"></a>
### `get_conn`

`static ngtcp2_conn *get_conn(ngtcp2_crypto_conn_ref *conn_ref)` · [lib/vquic/cf-ngtcp2-cmn.c:L194-L199][f1]

ngtcp2_crypto_conn_ref callback returning the filter's current ngtcp2 connection.

Reads cf from conn_ref->user_data and returns ctx->qconn, which may be NULL before the connection exists.

<a id="u-2d12c53a5aa5"></a>
### `quic_gtls_handshake_cb`

`static int quic_gtls_handshake_cb(gnutls_session_t session, unsigned int htype, unsig…` · [lib/vquic/cf-ngtcp2-cmn.c:L780-L823][f1]

GnuTLS post-handshake-message hook caching QUIC sessions.

Resolves cf/ctx from the session's user pointer; acts only after a message is processed (when non-zero) and with valid cf/ctx, returning 0 early if no current data. Logs the message direction and name. On GNUTLS_HANDSHAKE_NEW_SESSION_TICKET it encodes 0-RTT transport parameters (silently skipping on encode error) and caches the session via Curl_gtls_cache_session with ALPN 'h3'. All other message types are ignored; always returns 0.

calls: [gtls_hs_msg_name](r8-ngtcp2-errors-tls.md#u-e4118d3e4c1a)

<a id="u-2d40106e3183"></a>
### `quic_ossl_new_session_cb`

`static int quic_ossl_new_session_cb(SSL *ssl, SSL_SESSION *ssl_sessionid)` · [lib/vquic/cf-ngtcp2-cmn.c:L714-L746][f1]

OpenSSL new-session callback storing resumable QUIC sessions.

Retrieves the conn_ref from the SSL app data and resolves cf/ctx/data; does nothing (returns 0) if any is missing. Under HAVE_OPENSSL_EARLYDATA it encodes 0-RTT transport parameters into a 256-byte buffer, keeping them only if encoding succeeds, then hands the session to Curl_ossl_add_session with ALPN 'h3' and the peer's scache key. Always returns 0, meaning OpenSSL may remove the session from its own cache.

**Uncertainties.**

- Return value 0 always lets OpenSSL drop the session; caching happens only inside Curl_ossl_add_session, whose behavior is external.

<a id="u-e28b505b533f"></a>
### `wssl_quic_new_session_cb`

`static int wssl_quic_new_session_cb(WOLFSSL *ssl, WOLFSSL_SESSION *session)` · [lib/vquic/cf-ngtcp2-cmn.c:L827-L858][f1]

wolfSSL new-session callback caching QUIC sessions.

Resolves the conn_ref from SSL app data; with cf and session present it gathers ctx and current data, encodes 0-RTT transport parameters (skipping them on encode error), and calls Curl_wssl_cache_session with the wolfSSL version and ALPN 'h3'. Always returns 0.

<a id="u-e4118d3e4c1a"></a>
### `gtls_hs_msg_name`

`static const char *gtls_hs_msg_name(int mtype)` · [lib/vquic/cf-ngtcp2-cmn.c:L752-L777][f1]

CURLVERBOSE-only helper mapping GnuTLS handshake message type numbers to names (ClientHello, ServerHello, SessionTicket, EncryptedExtensions, Certificate, CertificateRequest, CertificateVerify, Finished, KeyUpdate, MessageHash); unknown values return "Unknown".

<a id="u-fb664a96c9e0"></a>
### `qlog_callback`

`static void qlog_callback(void *user_data, uint32_t flags, const void *data, size_t d…` · [lib/vquic/cf-ngtcp2-cmn.c:L213-L227][f1]

Writes ngtcp2 qlog traces to the filter's qlog file descriptor.

Does nothing if qlogfd is -1. On a write() returning -1 it closes the fd and sets qlogfd to -1 so no further attempts are made; partial writes are not handled.

**Notes.**

- failure: Partial qlog writes (0 <= rc < datalen) are silently accepted, only -1 disables logging.

<a id="u-9485c949d84e"></a>
### `quic_printf`

`static void quic_printf(void *user_data, const char *fmt, ...)` · [lib/vquic/cf-ngtcp2-cmn.c:L202-L210][f1]

DEBUG_NGTCP2-only log callback.

Formats a vararg message to stderr via curl_mvfprintf and appends a newline; user_data ignored.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-ngtcp2-cmn.c
