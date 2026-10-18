# OpenSSL connection lifecycle

**Capability.** SSL_CTX/SSL construction, the filter-tunneling custom BIO, version/ALPN/ECH/session setup, the handshake state machine, send/recv/shutdown/close, and verbose TLS traffic tracing.

Follow ossl_connect through its step functions to see context creation (BIO, method, session/ALPN, ECH) and error classification; ossl_send/ossl_recv/ossl_shutdown handle data-plane I/O. Trace helpers and the BIO glue belong here because they exist only to serve this lifecycle.

**Depends on.**

- [peer certificate verification](r11-ossl-cert-verify.md) · model-inferred · 0 edge(s)
- [TLS session reuse](r11-ossl-session-cache.md) · model-inferred · 0 edge(s)
- [TLS key logging](r11-tls-keylog.md) · model-inferred · 0 edge(s)

Parent: [TLS backends \(OpenSSL-based\)](r11-tls-security.md)

## Units (23)

<a id="u-28521ed418ed"></a>
### `openssl.c-bio-cf`

`static int ossl_bio_cf_create(BIO *bio)` · [lib/vtls/openssl.c:L528-L534][f1]

Custom BIO method that tunnels OpenSSL's I/O through curl's connection filter chain.

create marks the BIO initialized with shutdown=1 and NULL data; destroy only rejects NULL. ctrl handles GET/SET_CLOSE, FLUSH and DUP (always successful), and BIO_CTRL_EOF reads connssl->peer_closed from the filter stored in the BIO data; unknown commands return 0. out_write refuses negative lengths with 0, sends via Curl_conn_cf_send, stores the result in octx->io_result, and on CURLE_AGAIN sets the BIO retry-write flag and returns -1, else the byte count. in_read rejects NULL buffers or negative lengths with 0, receives via Curl_conn_cf_recv, records io_result, sets BIO retry-read on CURLE_AGAIN, and on success marks connssl->input_pending and peer_closed when nothing was read. Crucially, before any data is handed to OpenSSL it lazily completes the x509 store setup (Curl_ssl_setup_x509_store); a setup failure clears retry flags, stores the error and returns -1. method_create builds a BIO_TYPE_MEM method wiring these five callbacks and returns NULL on allocation failure; method_free releases it when non-NULL.

**Uncertainties.**

- BIO_CTRL_EOF dereferences cf without a NULL check; it assumes the BIO data is always a valid connection filter

<a id="u-87528f44a0b4"></a>
### `ossl_init`

`static int ossl_init(void)` · [lib/vtls/openssl.c:L1621-L1641][f1]

Global OpenSSL initialization; always returns 1.

It calls OPENSSL_init_ssl with OPENSSL_INIT_ENGINE_ALL_BUILTIN when available and either OPENSSL_INIT_NO_LOAD_CONFIG (when auto config loading is disabled) or OPENSSL_INIT_LOAD_CONFIG, then opens the TLS keylog unless key logging is handled upstream.

**Notes.**

- side_effect: initializes the global OpenSSL library state and opens the keylog file

<a id="u-7a55de84eaac"></a>
### `ossl_cleanup`

`static void ossl_cleanup(void)` · [lib/vtls/openssl.c:L1644-L1649][f1]

Global cleanup counterpart to ossl_init; it closes the TLS keylog unless key logging is handled upstream and performs no OpenSSL library deinitialization.

<a id="u-07f012f2a7b0"></a>
### `ossl_connect`

`static CURLcode ossl_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bool *d…` · [lib/vtls/openssl.c:L4993-L5074][f1]

Drives the TLS handshake state machine to completion, reporting *done.

A completed connection short-circuits to done. It resets io_need, then runs the stages in order guarded by connecting_state: step1 (delayed without a needed HTTPS-RR answer, returning OK not-done); step2, where early data is sent first (waiting state returns early, sending state runs ossl_send_earlydata) before ossl_connect_step2; step3 certificate checks, then early-data acceptance is read via SSL_get_early_data_status into accepted/rejected; done marks state complete. CURLE_AGAIN from any stage is converted to OK with *done FALSE, letting the caller retry on socket readiness; otherwise *done reflects connection completion (complete or deferred).

<a id="u-3e6c77364bd9"></a>
### `ossl_connect_step1`

`static CURLcode ossl_connect_step1(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/openssl.c:L4036-L4085][f1]

First connect stage: builds the SSL context and attaches curl's filter-based BIO.

It initializes the ossl_ctx via Curl_ossl_ctx_init (propagating errors), creates the custom BIO method and a BIO from it (either failure is CURLE_OUT_OF_MEMORY), stores the filter in the BIO, and attaches it as read and write BIO (SSL_set0_rbio/wbio with an up-ref on OpenSSL 1.1.1+, SSL_set_bio otherwise). When an ALPN list is offered and the connection is not deferred it logs the offer. Moves connecting_state to ssl_connect_2.

uses: [openssl.c-bio-cf](r11-ossl-conn-lifecycle.md#u-28521ed418ed), [ossl_new_session_cb](r11-ossl-session-cache.md#u-edf17fe9bdb6)

<a id="u-4d0d6c5b6469"></a>
### `lib/vtls/openssl.c:if`

`else if((lib == ERR_LIB_SSL) && (reason == SSL_R_TLSV13_ALERT_CERTIFICATE_REQUIRED))` · [lib/vtls/openssl.c:L4257-L4264][f1]

Fragment of ossl_connect_step2's error handling isolated by the parser; it corresponds to a conditional block around the certificate-verification-failed error classification, where the SSL verify result is read, stored in ssl_config->certverifyresult, and the concrete X509 verify error string is failed with CURLE_PEER_FAILED_VERIFICATION (or a generic message when OpenSSL reports X509_V_OK despite the verify-failed reason).

**Uncertainties.**

- The inventory's line ranges split ossl_connect_step2 into these 'if' fragments plus a module residual; the full function behavior is described across these fragments and the residual region

<a id="u-976488dd8f11"></a>
### `lib/vtls/openssl.c:if (2)`

`else if((lib == ERR_LIB_SSL) && #ifndef HAVE_BORINGSSL_LIKE (reason == SSL_R_ECH_REQU…` · [lib/vtls/openssl.c:L4267-L4306][f1]

Continuation fragment of ossl_connect_step2's untreated-error classification: after the certificate-verify and client-cert-required cases, it distinguishes ECH-required (tracing retry configs and returning CURLE_ECH_REQUIRED) from the generic case returning CURLE_SSL_CONNECT_ERROR, with a supplementary message built from the socket errno when OpenSSL produced no error detail and the failure is SSL_ERROR_SYSCALL.

<a id="u-aebc7e117922"></a>
### `ossl_init_method`

`static CURLcode ossl_init_method(struct Curl_cfilter *cf, struct Curl_easy *data, str…` · [lib/vtls/openssl.c:L3656-L3707][f1]

Chooses the SSL_METHOD and minimum version from transport and configured version.

TCP: explicit TLSv1.0-1.3 or generic TLSv1 selects TLS_client_method with the version applied later; SSLv2 and SSLv3 are rejected as CURLE_NOT_BUILT_IN; unrecognized values are CURLE_SSL_CONNECT_ERROR. QUIC forces TLS 1.3 minimum and rejects any max below TLS 1.3, selecting TLS_method. Other transports are CURLE_SSL_CONNECT_ERROR. A NULL method also yields CURLE_SSL_CONNECT_ERROR.

<a id="u-b6e8bbbf347e"></a>
### `ossl_init_ssl`

`static CURLcode ossl_init_ssl(struct ossl_ctx *octx, struct Curl_cfilter *cf, struct …` · [lib/vtls/openssl.c:L3611-L3654][f1]

Creates and configures the per-connection SSL structure.

It frees any prior SSL, creates a new one from the context (failure is CURLE_OUT_OF_MEMORY), installs the caller's user data, requests OCSP stapling when verifystatus is set, enters connect state, sets the SNI name (failure is CURLE_SSL_CONNECT_ERROR), initializes ECH when supported, and finishes with session/ALPN setup via ossl_init_session_and_alpns.

calls: [ossl_init_ech](r11-ossl-conn-lifecycle.md#u-b9d0ae27e0de), [ossl_init_session_and_alpns](r11-ossl-session-cache.md#u-b131146b307c)

<a id="u-b9d0ae27e0de"></a>
### `ossl_init_ech`

`static CURLcode ossl_init_ech(struct ossl_ctx *octx, struct Curl_cfilter *cf, struct …` · [lib/vtls/openssl.c:L3489-L3608][f1]

Configures Encrypted Client Hello on the SSL handle when ECH is enabled; otherwise returns OK immediately.

GREASE mode just enables ECH grease. With an explicit ech_config (base64-decoded on BoringSSL-like builds, raw otherwise): an empty config is CURLE_SSL_CONNECT_ERROR; a decode failure or SSL_set1_ech_config_list failure is fatal only in CURLECH_HARD mode, otherwise ECH is attempted anyway. Without a config it consults the HTTPS RR ECHConfigList, applying the same hard-fail semantics; no available config fails only in hard mode. When ECH is being attempted and a public name is configured, it sets inner/outer server names via SSL_ech_set1_server_names (BoringSSL-like builds cannot do this and fail); failure is CURLE_SSL_CONNECT_ERROR. Attempting ECH forces TLS 1.3 as the minimum version, failing if that cannot be set.

**Uncertainties.**

- BoringSSL-like and OpenSSL branches differ in decode and naming APIs; behavior was read per-branch from the respective conditional code

<a id="u-615c420a47d9"></a>
### `ossl_set_ssl_version_min_max`

`static CURLcode ossl_set_ssl_version_min_max(struct Curl_cfilter *cf, SSL_CTX *ctx, u…` · [lib/vtls/openssl.c:L2554-L2621][f1]

Translates curl's TLS min/max version options to OpenSSL bounds on the SSL_CTX.

The minimum maps TLSv1/TLSv1_0..TLSv1_3 to the corresponding TLS1_x_VERSION constants (no default case; other values leave the constant 0). The maximum maps the MAX_TLSv1_x constants likewise, while MAX_NONE, MAX_DEFAULT or anything unknown maps to 0, which OpenSSL treats as 'highest supported'. It applies both with SSL_CTX_set_min/max_proto_version; either failure returns CURLE_SSL_CONNECT_ERROR.

<a id="u-30ae1f5c9e0f"></a>
### `ossl_send`

`static CURLcode ossl_send(struct Curl_cfilter *cf, struct Curl_easy *data, const void…` · [lib/vtls/openssl.c:L5084-L5183][f1]

Encrypts and sends application data via SSL_write.

Length is capped at INT_MAX; if a previous write was blocked at a different length, the blocked length must be reused exactly — a shorter new length is an assertion failure returning CURLE_BAD_FUNCTION_ARGUMENT, otherwise the blocked length is used, because OpenSSL requires the same buffer/length on retry. Successful writes report the count (a count beyond the requested length is CURLE_SEND_ERROR). On failure: WANT_READ/WANT_WRITE remember the blocked length, set io_need, and return CURLE_AGAIN; SYSCALL is CURLE_AGAIN when the underlying filter reported again, else a described CURLE_SEND_ERROR; SSL_ERROR_SSL and all other errors are CURLE_SEND_ERROR with the best available error description. ERR queue is cleared on entry.

<a id="u-ad78a245e4d4"></a>
### `ossl_recv`

`static CURLcode ossl_recv(struct Curl_cfilter *cf, struct Curl_easy *data, /* transfe…` · [lib/vtls/openssl.c:L5185-L5298][f1]

Reads decrypted data via SSL_read, buffering size capped at INT_MAX.

Positive reads report the count. Zero/negative results are classified: SSL_ERROR_NONE is not an error (falls through with 0 bytes); ZERO_RETURN is a close_notify (logged for the first socket, returning OK with 0); WANT_READ/WANT_WRITE set io_need and return CURLE_AGAIN. In the default branch, an underlying CURLE_AGAIN propagates as CURLE_AGAIN; a negative return or queued OpenSSL error produces CURLE_RECV_ERROR with the error described from the OpenSSL queue, errno (SYSCALL only), or the SSL error name. A SYSCALL without queued error reports either the filter's io_result, 'Connection closed abruptly' when peer_closed was seen, or a generic failure, all as CURLE_RECV_ERROR except the propagated io_result. On exit, an EOF or AGAIN result clears input_pending so the socket is not polled needlessly.

<a id="u-32df96ffb82c"></a>
### `ossl_send_earlydata`

`static CURLcode ossl_send_earlydata(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/openssl.c:L4915-L4990][f1]

Drains the buffered TLS 1.3 early data through SSL_write_early_data (HAVE_OPENSSL_EARLYDATA builds).

It loops over the earlydata bufq; on each failed write it classifies: WANT_READ/WANT_WRITE set the matching io_need and return CURLE_AGAIN; SYSCALL is CURLE_AGAIN when the underlying filter itself reported again, otherwise fails as CURLE_SEND_ERROR with the OpenSSL error, socket error or SSL error name; SSL_ERROR_SSL fails as CURLE_SEND_ERROR with the queued error; anything else is a generic CURLE_SEND_ERROR. Each successful partial write skips that many buffered bytes. When the buffer is exhausted it logs the early-data send and returns OK.

<a id="u-710b32a2366c"></a>
### `ossl_data_pending`

`static bool ossl_data_pending(struct Curl_cfilter *cf, const struct Curl_easy *data)` · [lib/vtls/openssl.c:L5076-L5082][f1]

Reports whether decrypted data may be pending: returns connssl->input_pending unchanged.

<a id="u-b8e53902e7a1"></a>
### `ossl_shutdown`

`static CURLcode ossl_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data, bool s…` · [lib/vtls/openssl.c:L1835-L1954][f1]

Performs or advances a TLS close for the filter, reporting via *done whether shutdown is complete.

If there is no SSL or shutdown already happened it marks done and returns. When we have not yet sent our close notify, it reads up to 10 times to see if the server already sent one: on SSL_ERROR_ZERO_RETURN with no data, it finishes without sending ours if send_shutdown is false, or marks peer_closed and finishes when the underlying filter reports the connection dead. If send_shutdown is requested and we still have not sent, it calls SSL_shutdown: rc==1 finishes immediately, SSL_ERROR_WANT_WRITE sets io_need to SEND for retry. It then reads up to 10 times for the server's close notify: ZERO_RETURN triggers a final SSL_shutdown and marks done; NONE or WANT_READ sets io_need NEED_RECV to await the notify later; WANT_WRITE sets NEED_SEND; any other error is treated as the server dropping the connection and completes the shutdown with OK. On exit cf->shutdown is set when done or errored, and input_pending is cleared whenever shutdown happened or I/O is still needed.

**Uncertainties.**

- The default error case swallows the underlying error deliberately (result forced to CURLE_OK), relying on the connection-close path elsewhere

<a id="u-fe91fca361d5"></a>
### `ossl_close`

`static void ossl_close(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/openssl.c:L1956-L1978][f1]

Releases one connection's TLS resources: clears input_pending, frees and nulls the SSL, frees the SSL_CTX (resetting x509_store_setup so a reconnect re-populates the store), and frees the custom BIO method.

<a id="u-8b1698542c2b"></a>
### `ossl_close_all`

`static void ossl_close_all(struct Curl_easy *data)` · [lib/vtls/openssl.c:L1984-L1998][f1]

Easy-handle teardown: finishes and frees the selected crypto engine when engine support is built, and cleans up provider state via ossl_provider_cleanup when providers are built.

calls: [ossl_provider_cleanup](r11-ossl-cert-key-config.md#u-4b7c8ec2ac0c)

<a id="u-78338196a3d3"></a>
### `ossl_trace`

`static void ossl_trace(int direction, int ssl_ver, int content_type, const void *buf,…` · [lib/vtls/openssl.c:L2449-L2552][f1]

SSL_CTX message callback emitting verbose TLS traffic diagnostics.

It returns immediately without a filter, current data, debug callback, or a direction other than 0/1. It resolves the protocol version to a name (hex fallback). For interesting records only (nonzero ssl_ver, not raw header, not TLS 1.3 inner content type) it decodes: change-cipher-spec takes buf[0]; alerts combine two bytes into SSL_alert_desc_string_long; anything else treats buf[0] as a handshake message named via ssl_msg_type. It logs the composed summary via Curl_debug as CURLINFO_TEXT and always dumps the raw payload as SSL_DATA_OUT (direction 1) or SSL_DATA_IN.

calls: [tls_rt_type](r11-ossl-conn-lifecycle.md#u-82a529856b9c), [ssl_msg_type](r11-ossl-conn-lifecycle.md#u-76847ff8a823)

<a id="u-d84e4993b34d"></a>
### `ossl_trace_ech_retry_configs`

`static int ossl_trace_ech_retry_configs(struct Curl_cfilter *cf, struct Curl_easy *da…` · [lib/vtls/openssl.c:L4089-L4149][f1]

Traces ECH retry configurations received from a server when ECH is enabled (ECH support builds only).

It fetches retry configs (SSL_ech_get1_retry_config or SSL_get0_ech_retry_configs); when present it base64-encodes and logs them, then logs the ECH status including inner and outer names (per-backend API). Without retry configs it logs that none were received. Returns the backend's status value, and its return is the ECH status consumed by callers.

**Uncertainties.**

- The exact semantics of the returned rv for BoringSSL-like builds (a length rather than a status) differ; callers only use it under !HAVE_BORINGSSL_LIKE

<a id="u-76847ff8a823"></a>
### `ssl_msg_type`

`static const char *ssl_msg_type(int ssl_ver, int msg)` · [lib/vtls/openssl.c:L2365-L2424][f1]

Maps an SSLv3/TLS handshake message type to its name for trace output; for SSL3_VERSION_MAJOR messages it returns the known names (conditionally compiled variants included), otherwise "Unknown".

<a id="u-82a529856b9c"></a>
### `tls_rt_type`

`static const char *tls_rt_type(int type)` · [lib/vtls/openssl.c:L2426-L2444][f1]

Maps a TLS record content type (header, change cipher spec, alert, handshake, app data) to its name for trace output; unknown values return "TLS Unknown".

<a id="u-22c0a4200aa2"></a>
### `Curl_ossl_report_handshake`

`void Curl_ossl_report_handshake(struct Curl_easy *data, struct ossl_ctx *octx)` · [lib/vtls/openssl.c:L4006-L4034][f1]

Logs the negotiated TLS version, cipher, group and peer signature algorithm in one informational line; only compiled work under CURLVERBOSE and only when verbose tracing is enabled, otherwise a no-op.

Group name retrieval differs across OpenSSL versions (SSL_get0_group_name vs OBJ_nid2sn of the negotiated group).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/openssl.c
