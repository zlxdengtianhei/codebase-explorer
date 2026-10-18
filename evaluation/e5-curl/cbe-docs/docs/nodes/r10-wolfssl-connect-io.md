# wolfSSL Connect and Data I/O

**Capability.** Owns the per-connection data path: connect state machine, handshake result mapping, shutdown, encrypted send/recv, early data, and the custom BIO that bridges wolfSSL to curl connection filters.

Use this child for handshake flow, I/O over the filter chain, and BIO wiring. Handshake failures are mapped to curl results in the handshake units and their tail logic.

Parent: [wolfSSL TLS Backend](r10-tls-wolfssl.md)

## Units (16)

<a id="u-fb17bd332a54"></a>
### `wssl_connect_step1`

`static CURLcode wssl_connect_step1(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/wolfssl.c:L1466-L1531][f1]

First connect step: creates the SSL context and handle and attaches I/O.

Returns CURLE_OK immediately if the connection is already complete. Runs Curl_wssl_ctx_init with wssl_on_session_reuse as the session-reuse callback; failure propagates. With ALPN and non-deferred state it logs the offered protocols. When verifyhost is on and an SNI name exists, enables RFC 2818 domain checks via wolfSSL_check_domain_name (failure returns CURLE_SSL_CONNECT_ERROR); the comment notes this cannot check IP addresses, handled after the handshake. With the BIO chain, it requires the global BIO method, creates a BIO with the filter as data, and installs it for both read and write (method-missing returns CURLE_FAILED_INIT, BIO creation failure OUT_OF_MEMORY). Without the BIO chain it passes the raw socket to wolfSSL_set_fd, failing with CURLE_SSL_CONNECT_ERROR if the descriptor exceeds INT_MAX or the call fails.

calls: [Curl_wssl_ctx_init](r10-wolfssl-context-setup.md#u-87753aa47fb6); uses: [wssl_on_session_reuse](r10-wolfssl-session-cache.md#u-1982430f9387)

<a id="u-388bda9f47cd"></a>
### `wssl_connect`

`static CURLcode wssl_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bool *d…` · [lib/vtls/wolfssl.c:L2116-L2231][f1]

Connect state machine: runs step1, then the handshake, then post-handshake checks, across repeated non-blocking invocations.

A complete connection short-circuits with *done TRUE. In ssl_connect_1 with ECH needing HTTPS-RR, it delays (returning CURLE_OK with done FALSE) until DNS resolution of HTTPS records completes. After step1 succeeds, state moves to ssl_connect_2. In ssl_connect_2, deferred early-data connections skip the handshake until data arrives. wssl_handshake CURLE_AGAIN exits with done FALSE and CURLE_OK; any other result is stored in wssl->hs_result and state moves to ssl_connect_3. In ssl_connect_3 a stored hs_result errors again on every call (sticky failure); otherwise pinned-key verification runs, its failure also becoming the sticky hs_result. On success, ALPN is negotiated from wolfSSL_ALPN_GetProtocol (not-found sets no protocol; other errors set sticky CURLE_SSL_CONNECT_ERROR), the connection is marked complete, the handshake is reported, and with early data support the accepted/rejected status is recorded. done becomes TRUE when connecting reaches ssl_connect_done or the state is deferred. On any error done is forced FALSE, with CURLE_AGAIN converted to CURLE_OK.

**Uncertainties.**

- Exact interaction between connssl->earlydata_state 'await' and later resumption depends on external state changes not visible here.

<a id="u-687ab29a929d"></a>
### `wssl_handshake`

`static CURLcode wssl_handshake(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/wolfssl.c:L1654-L1785][f1]

Drives the TLS handshake, mapping wolfSSL results to curl results and I/O needs.

Sends pending early data first if in the sending state. Clears the error queue, calls wolfSSL_connect, then ensures the X509 store is set up after the ClientHello if not done (failure propagates from here). With key logging enabled, logs TLS<=1.2 secrets and frees retained arrays when the handshake succeeded or neither read nor write is pending. Then reads the error detail. On success with verifyhost and no SNI (IP-address origin) it fetches the peer certificate (missing: CURLE_PEER_FAILED_VERIFICATION) and checks the IP with wolfSSL_X509_check_ip_asc; a mismatch sets detail to DOMAIN_NAME_MISMATCH. Success returns CURLE_OK. Failure mapping: WANT_READ/WANT_WRITE set io_need to recv/send and return CURLE_AGAIN; DOMAIN_NAME_MISMATCH returns CURLE_PEER_FAILED_VERIFICATION; ASN_NO_SIGNER_E returns CURLE_SSL_CACERT_BADFILE when verifypeer is set, otherwise a warning and CURLE_OK; ASN_AFTER_DATE_E and ASN_BEFORE_DATE_E return CURLE_PEER_FAILED_VERIFICATION; an io_result of SEND/RECV_ERROR yields CURLE_SSL_CONNECT_ERROR while other io_results propagate; with ECH support, detail -1 triggers a best-effort base64 trace of retry configs (which the comment notes are currently not produced) and returns CURLE_SSL_CONNECT_ERROR; anything else formats the detail and returns CURLE_SSL_CONNECT_ERROR.

calls: [wssl_send_earlydata](r10-wolfssl-connect-io.md#u-7432b5855c54), [Curl_wssl_setup_x509_store](r10-wolfssl-context-setup.md#u-9c68b26fbb46), [wssl_log_tls12_secret](r10-wolfssl-support.md#u-292fb2c9c2ac)

<a id="u-97902e818739"></a>
### `lib/vtls/wolfssl.c:if (2)`

`else if(detail == -1)` · [lib/vtls/wolfssl.c:L1785-L1807][f1]

Tail of wssl_handshake: selects the failure return based on the wolfSSL detail code as described in the handshake unit's failure mapping (AGAIN, verification failures, CA-signer, expiry, io_result propagation, ECH retry trace, generic error).

<a id="u-a3ad715e4610"></a>
### `wssl_shutdown`

`static CURLcode wssl_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data, bool s…` · [lib/vtls/wolfssl.c:L1882-L1984][f1]

Performs TLS close-notify handling with wait, reporting progress via *done and cf->shutdown.

A missing SSL handle or already-shutdown filter completes immediately with *done TRUE. Marks the context shutting_down, resets io_need, and if we have not yet sent our close notify, reads: a wolfSSL_read returning 0 with WOLFSSL_ERROR_ZERO_RETURN means the server sent its notify first — if send_shutdown is false we are done; otherwise, when the next filter reports the peer has closed (is_alive false), we mark peer_closed and are done without sending ours. Then, if send_shutdown is requested, wolfSSL_shutdown is called: return 1 completes; WANT_WRITE sets io_need SEND and pauses. Afterward it reads up to 10 times to collect the server's notify and maps the final error: ZERO_RETURN completes; NONE/WANT_READ set io_need RECV; WANT_WRITE sets io_need SEND; anything else returns CURLE_RECV_ERROR. cf->shutdown is set when an error occurred or shutdown completed.

**Uncertainties.**

- The 'up to 10 reads' loop's rationale (draining app data vs notify frames) is not stated in the source; its sufficiency is unproven.

<a id="u-72817bfd75d4"></a>
### `wssl_send`

`static CURLcode wssl_send(struct Curl_cfilter *cf, struct Curl_easy *data, const void…` · [lib/vtls/wolfssl.c:L1819-L1880][f1]

Encrypts and sends at most INT_MAX bytes via wolfSSL_write.

Positive writes update *pnwritten. On failure, WANT_READ/WANT_WRITE mean data is pending: if some bytes were already written the result is success (partial write), otherwise CURLE_AGAIN. For other errors, an io_result of CURLE_AGAIN maps the same way (success on partial, else AGAIN); otherwise it logs the wolfSSL error plus errno and returns CURLE_SEND_ERROR. A zero-length write returns success with 0.

<a id="u-c8156ed0e1a5"></a>
### `wssl_recv`

`static CURLcode wssl_recv(struct Curl_cfilter *cf, struct Curl_easy *data, char *buf,…` · [lib/vtls/wolfssl.c:L2005-L2063][f1]

Decrypts and receives at most INT_MAX bytes via wolfSSL_read.

Positive reads set *pnread and return success. ZERO_RETURN (clean close) returns success with 0 bytes. NONE, WANT_READ, or WANT_WRITE mean data is pending and return CURLE_AGAIN only when io_result is clean and the peer has not closed; otherwise they fall through to the error path, where io_result CURLE_AGAIN again yields CURLE_AGAIN, a clean io_result with peer_closed logs 'Connection closed abruptly', and anything else logs the wolfSSL error and errno — all returning CURLE_RECV_ERROR.

<a id="u-7432b5855c54"></a>
### `wssl_send_earlydata`

`static CURLcode wssl_send_earlydata(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/wolfssl.c:L1611-L1651][f1]

Flushes queued TLS 1.3 early data through wolfSSL_write_early_data in a loop over the earlydata bufq.

A negative return is classified by wolfSSL_get_error: WOLFSSL_ERROR_NONE, WANT_READ, or WANT_WRITE return CURLE_AGAIN; any other error logs and returns CURLE_SEND_ERROR. On success the written bytes are skipped in the bufq; when everything is sent the state moves to ssl_earlydata_sent, early data bytes are reported via Curl_pgrsEarlyData for non-proxy connections, and CURLE_OK is returned. Compiled only with WOLFSSL_EARLY_DATA.

<a id="u-904727b72169"></a>
### `wssl_data_pending`

`static bool wssl_data_pending(struct Curl_cfilter *cf, const struct Curl_easy *data)` · [lib/vtls/wolfssl.c:L2092-L2106][f1]

Reports whether decrypted data is already buffered in wolfSSL.

Returns wolfSSL_pending when a handle exists, FALSE otherwise.

<a id="u-f1decde712f7"></a>
### `wssl_bio_cf_create`

`static int wssl_bio_cf_create(WOLFSSL_BIO *bio)` · [lib/vtls/wolfssl.c:L224-L231][f1]

create handler for the custom wolfSSL BIO.

In the USE_FULL_BIO build it sets the BIO shutdown flag to 1; it always sets the BIO data pointer to NULL and returns 1 for success.

<a id="u-32c6c11af444"></a>
### `wssl_bio_cf_ctrl`

`static long wssl_bio_cf_ctrl(WOLFSSL_BIO *bio, int cmd, long num, void *ptr)` · [lib/vtls/wolfssl.c:L233-L274][f1]

ctrl handler of the BIO that bridges wolfSSL to curl connection filters.

GET_CLOSE returns the shutdown flag in the full-BIO build, otherwise 0; SET_CLOSE sets the flag only in the full-BIO build; FLUSH and DUP return 1 with no real work (no delayed writes exist). When WOLFSSL_BIO_CTRL_EOF is defined, that command returns connssl->peer_closed, reading cf directly from the BIO data. Any other command returns 0.

uses: [wssl_bio_cf_init_methods](r10-wolfssl-connect-io.md#u-6843547b1651)

**Uncertainties.**

- The EOF case dereferences cf without a NULL check; the code relies on the BIO data being set before use.

<a id="u-2f08337ab480"></a>
### `wssl_bio_cf_in_read`

`static int wssl_bio_cf_in_read(WOLFSSL_BIO *bio, char *buf, int blen)` · [lib/vtls/wolfssl.c:L314-L355][f1]

read handler feeding decrypted input from the connection filter into wolfSSL.

Returns -1 with io_result CURLE_FAILED_INIT when data is NULL or blen is negative; returns 0 immediately for a NULL buffer or zero length. During connecting state ssl_connect_2 with x509_store_setup not yet set, it calls Curl_wssl_setup_x509_store first so ClientHello is not delayed; a setup failure is stored in io_result and returned as -1. It then receives via Curl_conn_cf_recv, records io_result, clears retry flags in the full-BIO build, sets retry-read on CURLE_AGAIN, and marks connssl->peer_closed when 0 bytes were read. Returns -1 on error, else the byte count.

calls: [Curl_wssl_setup_x509_store](r10-wolfssl-context-setup.md#u-9c68b26fbb46)

<a id="u-d378b8524bd5"></a>
### `wssl_bio_cf_out_write`

`static int wssl_bio_cf_out_write(WOLFSSL_BIO *bio, const char *buf, int blen)` · [lib/vtls/wolfssl.c:L276-L312][f1]

write handler forwarding encrypted wolfSSL output to the next connection filter.

Works around wolfSSL issue 7784: when shutting down and a previously blocked length is recorded smaller than the requested write, it trims the write to the blocked length and remembers the skipped tail (skiplen). Sends via Curl_conn_cf_send, stores the result in wssl->io_result, and clears retry flags in the full-BIO build. On CURLE_AGAIN it sets retry-write and, on the first shutdown block (io_send_blocked_len was 0), records io_send_blocked_len. On success with a skipped tail, the skip is added back into the returned count. Returns -1 on any error, otherwise the number of bytes written.

uses: [wssl_shutdown](r10-wolfssl-connect-io.md#u-a3ad715e4610)

<a id="u-6843547b1651"></a>
### `wssl_bio_cf_init_methods`

`static int wssl_bio_cf_init_methods(void)` · [lib/vtls/wolfssl.c:L359-L370][f1]

Creates the single global BIO method object (type WOLFSSL_BIO_MEMORY, name 'wolfSSL CF BIO') and installs the write, read, ctrl, and create handlers.

Returns FALSE on allocation failure, TRUE otherwise. Without USE_BIO_CHAIN this function is a macro evaluating to TRUE.

<a id="u-83ee6a999943"></a>
### `wssl_bio_cf_free_methods`

`static void wssl_bio_cf_free_methods(void)` · [lib/vtls/wolfssl.c:L372-L376][f1]

Frees the global BIO method object and sets the global pointer to NULL.

Without USE_BIO_CHAIN it is a no-op macro.

<a id="u-96c18277dd27"></a>
### `wssl_close`

`static void wssl_close(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/wolfssl.c:L1986-L2003][f1]

Releases the SSL handle and SSL context, NULLing both pointers.

No close-notify is sent here; shutdown is a separate step.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/wolfssl.c
