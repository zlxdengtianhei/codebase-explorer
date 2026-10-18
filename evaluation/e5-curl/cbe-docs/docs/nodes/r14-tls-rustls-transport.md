# rustls Connection Transport

**Capability.** Owns the runtime TLS data path: handshake driving, plaintext recv/send, graceful shutdown, ALPN reporting, and the I/O callbacks bridging rustls to the next connection filter.

Readers tracing encrypted bytes should follow read_cb/write_cb into tls_recv_more and cr_flush_out, then out through cr_recv/cr_send. cr_shutdown resumably closes the connection while cr_close merely frees state.

**Depends on.**

- [rustls Client Config Builder](r14-tls-rustls-config.md) · model-inferred · 0 edge(s)

Parent: [rustls TLS Backend](r14-tls-rustls.md)

## Units (17)

<a id="u-5034945dd123"></a>
### `cr_connect`

`static CURLcode cr_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bool *done)` · [lib/vtls/rustls.c:L1171-L1346][f1]

Performs the TLS handshake on an established connection, non-blocking, driven by repeated calls; *done is set only, never read.

With ECH, when HTTPS-RR data is required but not yet resolved it returns CURLE_OK with *done FALSE, deferring. If no connection exists it runs cr_init_backend and moves to ssl_connection_negotiating. The main loop resets io_need each pass. When rustls reports the handshake over, it flushes one final cr_send (CURLE_AGAIN schedules CURL_SSL_IO_NEED_SEND and returns CURLE_OK; other errors propagate), logs the negotiated TLS version, ciphersuite and kex group, then optionally collects peer certificates: counting stops above MAX_ALLOWED_CERT_AMOUNT with CURLE_SSL_CONNECT_ERROR, DER extraction or certinfo extraction failures abort with their error; otherwise state becomes ssl_connection_complete and *done TRUE. While still handshaking it flushes output when wanted (wants_write includes buffered plaintext; CURLE_AGAIN schedules a send wait) and reads TLS when wanted: a 0-byte read means abrupt peer close and fails with CURLE_SSL_CONNECT_ERROR; CURLE_AGAIN schedules a recv wait returning CURLE_OK; CURLE_RECV_ERROR maps to CURLE_SSL_CONNECT_ERROR; other errors propagate.

**Notes.**

- side_effect: Sets connssl->peer_closed when the peer closes during handshake read.

calls: [cr_init_backend](r14-tls-rustls-config.md#u-69fe9ed37f89), [cr_send](r14-tls-rustls-transport.md#u-ab962705525a), [tls_recv_more](r14-tls-rustls-transport.md#u-aacb7e60e5d9)

**Uncertainties.**

- Under CURLVERBOSE the version strings are computed but the infof always references them; without CURLVERBOSE ver stays 'TLS version unknown' while ciphersuite/kex names are still read from rustls.

<a id="u-7eac62854edd"></a>
### `cr_recv`

`static CURLcode cr_recv(struct Curl_cfilter *cf, struct Curl_easy *data, char *plainb…` · [lib/vtls/rustls.c:L197-L266][f1]

Filter receive method: fills plainbuf with decrypted TLS plaintext.

Loops while fewer than plainlen bytes were produced; when no data is pending it calls tls_recv_more, breaking with CURLE_OK on CURLE_AGAIN and propagating other errors. rustls_connection_read outcomes: PLAINTEXT_EMPTY clears data_in_pending and stops the loop so a server cannot pin the connection with empty TLS messages; UNEXPECTED_EOF fails with CURLE_RECV_ERROR after logging that the peer closed TCP without closing TLS; any other non-OK result fails with CURLE_RECV_ERROR via rustls_failf; n==0 marks a clean EOF (eof=TRUE) while keeping bytes already read; otherwise the count accumulates. If the loop ended without EOF and zero bytes were produced, CURLE_AGAIN is returned.

calls: [tls_recv_more](r14-tls-rustls-transport.md#u-aacb7e60e5d9)

<a id="u-ab962705525a"></a>
### `cr_send`

`static CURLcode cr_send(struct Curl_cfilter *cf, struct Curl_easy *data, const void *…` · [lib/vtls/rustls.c:L313-L388][f1]

Filter send method: copies plaintext into rustls and flushes its TLS output; callable with NULL/zero length purely to flush.

If a previous send blocked (plain_out_buffered nonzero) it flushes first; failure propagates, success credits the buffered count to *pnwritten and deducts it from the current buffer (or zeroes blen) before clearing it. New plaintext is added via rustls_connection_write: a rustls error or zero-written EOF fails with CURLE_WRITE_ERROR. Then cr_flush_out runs: on CURLE_AGAIN the amount rustls accepted (plainwritten) is stored in plain_out_buffered for the next call, and if bytes were already credited from the prior blocked send the result is downgraded to CURLE_OK; on a clean flush the accepted plaintext count is credited to *pnwritten.

calls: [cr_flush_out](r14-tls-rustls-transport.md#u-8ef00f989499)

<a id="u-42677430f580"></a>
### `cr_shutdown`

`static CURLcode cr_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data, const bo…` · [lib/vtls/rustls.c:L1357-L1418][f1]

Graceful TLS shutdown, resumable across calls.

If no connection exists or cf->shutdown is already set it marks *done TRUE and finishes. Otherwise, once only, it queues a close-notify when send_shutdown is requested (sent_shutdown flag prevents repeats), then flushes pending TLS output: CURLE_AGAIN schedules CURL_SSL_IO_NEED_SEND and reports success for later retry; other send errors abort with cf->shutdown set. It then reads up to 10 chunks of 1024 bytes via cr_recv to consume the peer's close notify; CURLE_AGAIN schedules CURL_SSL_IO_NEED_RECV with success, other errors propagate, and a final zero-byte read means the alert arrived and *done is TRUE. cf->shutdown is set whenever an error occurred or shutdown completed.

calls: [cr_send](r14-tls-rustls-transport.md#u-ab962705525a), [cr_recv](r14-tls-rustls-transport.md#u-7eac62854edd)

**Uncertainties.**

- The 10-iteration read loop may leave peer data unread if the close notify has not arrived within 10 chunks; behavior then depends on later calls.

<a id="u-8ef00f989499"></a>
### `cr_flush_out`

`static CURLcode cr_flush_out(struct Curl_cfilter *cf, struct Curl_easy *data, struct …` · [lib/vtls/rustls.c:L268-L301][f1]

Drains rustls' pending TLS output to the socket while rustls_connection_wants_write stays true.

Returns CURLE_AGAIN when a write reports EAGAIN (previously written bytes remain written), CURLE_SEND_ERROR after logging a socket write error, and CURLE_SEND_ERROR with an 'EOF in swrite' message when a write reports zero bytes; otherwise CURLE_OK once rustls has nothing more to send.

**Notes.**

- failure: A zero-length successful write is treated as EOF and fails with CURLE_SEND_ERROR.

<a id="u-8af65d34a138"></a>
### `cr_set_negotiated_alpn`

`static void cr_set_negotiated_alpn(struct Curl_cfilter *cf, struct Curl_easy *data, c…` · [lib/vtls/rustls.c:L1154-L1164][f1]

Reads the ALPN protocol rustls negotiated (if any) and reports it to curl via Curl_alpn_set_negotiated, updating the filter's ALPN state.

<a id="u-aacb7e60e5d9"></a>
### `tls_recv_more`

`static ssize_t tls_recv_more(struct Curl_cfilter *cf, struct Curl_easy *data, CURLcod…` · [lib/vtls/rustls.c:L154-L191][f1]

Reads one chunk of raw TLS bytes into rustls and processes newly received packets.

Returns the TLS byte count, or -1 with *err set: CURLE_AGAIN when the underlying read reports EAGAIN/EWOULDBLOCK (RAW_EAGAIN), CURLE_RECV_ERROR after logging any other socket read error, or map_error(rresult) when rustls_connection_process_new_packets fails (cert errors become CURLE_PEER_FAILED_VERIFICATION). On success it sets backend->data_in_pending so cr_recv knows plaintext may be available.

calls: [read_cb](r14-tls-rustls-transport.md#u-03db2fc2b875), [map_error](r14-tls-rustls-backend.md#u-721f2a4493c3)

<a id="u-03db2fc2b875"></a>
### `read_cb`

`static int read_cb(void *userdata, uint8_t *buf, uintptr_t len, uintptr_t *out_n)` · [lib/vtls/rustls.c:L104-L129][f1]

Rustls read callback pulling raw TLS bytes from the next connection filter via Curl_conn_cf_recv.

On success out_n carries the byte count; a zero read sets connssl->peer_closed to TRUE. CURLE_AGAIN maps to return value EAGAIN so rustls retries later; any other error returns EINVAL, with nread zeroed in both cases. Each call is trace-logged.

uses: [io_ctx](r14-tls-rustls-transport.md#u-df3b500d199a)

<a id="u-aef0584067f9"></a>
### `write_cb`

`static int write_cb(void *userdata, const uint8_t *buf, uintptr_t len, uintptr_t *out_n)` · [lib/vtls/rustls.c:L131-L152][f1]

Rustls write callback pushing raw TLS bytes to the next connection filter via Curl_conn_cf_send.

On success out_n carries the written count; CURLE_AGAIN maps to EAGAIN and any other error to EINVAL, both with out_n zeroed. Trace-logged per call.

**Uncertainties.**

- Meaning of the FALSE flag argument to Curl_conn_cf_send is not defined in this file.

<a id="u-df3b500d199a"></a>
### `io_ctx`

`struct io_ctx` · [lib/vtls/rustls.c:L99-L102][f1]

Context struct pairing a connection filter and a Curl_easy handle, passed as userdata to the rustls I/O callbacks so they know which filter's next layer and transfer to read from or write to.

<a id="u-07705f195781"></a>
### `rustls_ssl_backend_data`

`struct rustls_ssl_backend_data` · [lib/vtls/rustls.c:L54-L60][f1]

Per-connection rustls backend state stored in the SSL filter's backend slot: the built client config, the live rustls connection, a count of plaintext bytes rustls accepted but whose TLS output was not flushed after a blocked send, a flag that decrypted plaintext is buffered in rustls, and a flag that a close-notify was already queued during shutdown.

uses: [cr_send](r14-tls-rustls-transport.md#u-ab962705525a), [cr_recv](r14-tls-rustls-transport.md#u-7eac62854edd)

<a id="u-e32993e70d00"></a>
### `rustls.c module code (L388–L391)`

`module_region` · [lib/vtls/rustls.c:L388-L391][f1]

Short region between cr_send and cr_verify_none; non-behavioral.

<a id="u-723d62b4dd2d"></a>
### `rustls.c module code (L60–L62)`

`module_region` · [lib/vtls/rustls.c:L60-L62][f1]

Trivial separator region between the backend struct and the error-mapping helpers; no behavior.

<a id="u-5360d5a06e49"></a>
### `rustls.c module code (L102–L103)`

`module_region` · [lib/vtls/rustls.c:L102-L103][f1]

Trivial separator line after io_ctx; no behavior.

<a id="u-7ac28468c2e5"></a>
### `rustls.c module code (L191–L196)`

`module_region` · [lib/vtls/rustls.c:L191-L196][f1]

Small region between tls_recv_more and cr_recv, likely comments/whitespace; no behavior of its own.

<a id="u-250cd8095f7b"></a>
### `rustls.c module code (L301–L312)`

`module_region` · [lib/vtls/rustls.c:L301-L312][f1]

Region between cr_flush_out and cr_send containing the cr_send doc comment; non-behavioral.

<a id="u-6cce7ee8651b"></a>
### `rustls.c module code (L1164–L1170)`

`module_region` · [lib/vtls/rustls.c:L1164-L1170][f1]

Region between cr_set_negotiated_alpn and cr_connect containing the cr_connect doc comment; non-behavioral.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/rustls.c
