# Schannel record I/O

**Capability.** Encrypts and decrypts TLS records and manages the associated buffers: send, recv with plaintext-first delivery, renegotiation detection and completion, shutdown, and buffer sizing guarantees.

Read this for data-path behavior after the handshake. schannel_recv may detect SEC_I_RENEGOTIATE and hand off to schannel_recv_renegotiate, which blocks up to MAX_RENEG_BLOCK_TIME; shutdown is idempotent.

**Depends on.**

- [Schannel handshake and credentials](r4-schannel-handshake.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Schannel handshake and credentials](r4-schannel-handshake.md) · model-inferred · 0 edge(s)

Parent: [Schannel TLS backend](r4-schannel-tls.md)

## Units (8)

<a id="u-f1fc6266a96a"></a>
### `schannel.c-renegotiation-decls`

`enum schannel_renegotiate_caller_t` · [lib/vtls/schannel.c:L1766-L1769][f1]

The schannel_renegotiate_caller_t enum distinguishing recv-initiated from send-initiated renegotiation, the MAX_RENEG_BLOCK_TIME constant (60 seconds in milliseconds), and its explanatory comment about DecryptMessage returning SEC_I_RENEGOTIATE.

Declarations only.

uses: [schannel_recv_renegotiate](r4-schannel-record-io.md#u-c67f8ebd596f)

<a id="u-423227f031f6"></a>
### `ensure_decoding_size`

`static CURLcode ensure_decoding_size(struct Curl_easy *data, struct sbuffer *decdata,…` · [lib/vtls/schannel.c:L1200-L1228][f1]

Guarantees the decrypted-data buffer can hold at least nowsize (or the minimum free size, whichever is larger) bytes after the current offset and can hold len bytes total.

Offset exceeding length returns CURLE_FAILED_INIT. When capacity is insufficient the buffer is realloc'd to offset plus the required size, raised to len when needed; allocation failure returns CURLE_OUT_OF_MEMORY. Otherwise decdata->buffer and decdata->length are updated in place.

uses: [schannel_recv](r4-schannel-record-io.md#u-57aff20ea872)

<a id="u-498290b40ed5"></a>
### `ensure_encoding_size`

`static CURLcode ensure_encoding_size(struct Curl_easy *data, struct sbuffer *encdata,…` · [lib/vtls/schannel.c:L1172-L1198][f1]

Guarantees the encrypted-data buffer has at least CURL_SCHANNEL_BUFFER_FREE_SIZE free bytes and can hold min_length bytes total.

An offset larger than length is an internal inconsistency returning CURLE_FAILED_INIT. When the free space or total size is insufficient, the buffer is realloc'd to offset plus free-size, raised to min_length when needed; allocation failure logs and returns CURLE_OUT_OF_MEMORY. On success encdata->buffer and encdata->length reflect the new capacity.

uses: [schannel_recv](r4-schannel-record-io.md#u-57aff20ea872)

<a id="u-21e1c6aaa8a0"></a>
### `schannel_data_pending`

`static bool schannel_data_pending(struct Curl_cfilter *cf, const struct Curl_easy *data)` · [lib/vtls/schannel.c:L2380-L2398][f1]

Reports whether the connection still holds undelivered TLS state.

Without an SSPI context it returns FALSE. Otherwise it is TRUE when decrypted data is buffered, when unprocessed encrypted data exists that is not flagged incomplete, or when the connection was closed, a close_notify was seen, or an unrecoverable error is latched.

<a id="u-57aff20ea872"></a>
### `schannel_recv`

`static CURLcode schannel_recv(struct Curl_cfilter *cf, struct Curl_easy *data, char *…` · [lib/vtls/schannel.c:L2102-L2378][f1]

Returns decrypted application data, prioritizing delivery of whatever plaintext is available even across errors.

Early exits: if the decrypted buffer already satisfies a nonzero request, on a stored unrecoverable error, or after a close_notify, only cached data is returned. Otherwise it sizes the encrypted buffer for the request plus overhead, reads from the next filter (CURLE_AGAIN is tolerated; other read errors or EOF are recorded in recv_unrecoverable_err / recv_connection_closed), and loops DecryptMessage while encrypted data remains. On success, renegotiate, or context-expired statuses it appends decrypted data (growing the buffer as needed), shifts any SECBUFFER_EXTRA remainder to the buffer start, and resets the offset when nothing remains. SEC_I_RENEGOTIATE delegates to schannel_recv_renegotiate and, on success, retries decryption; SEC_I_CONTEXT_EXPIRED records close_notify, treats a trailing CURLE_RECV_ERROR as success, and exits; SEC_E_INCOMPLETE_MESSAGE flags incomplete data and yields CURLE_AGAIN; any other status is CURLE_RECV_ERROR. Cleanup delivers up to len bytes from the decrypted buffer (always CURLE_OK when data is returned), flags a missing close_notify at connection close as CURLE_RECV_ERROR to prevent truncation, stores any non-AGAIN error as unrecoverable, and returns CURLE_AGAIN when no data and the connection is open; a zero-length request returns CURLE_OK regardless.

**Notes.**

- side_effect: recv_unrecoverable_err latches the first fatal error so subsequent calls fail fast until close.

calls: [schannel_recv_renegotiate](r4-schannel-record-io.md#u-c67f8ebd596f), [ensure_decoding_size](r4-schannel-record-io.md#u-423227f031f6), [ensure_encoding_size](r4-schannel-record-io.md#u-498290b40ed5)

**Uncertainties.**

- Whether decrypted data left over a context expiry is delivered on the next call depends on the latched close_notify early exit, which returns cached data first — the source supports this but no test evidence exists here.

<a id="u-c67f8ebd596f"></a>
### `schannel_recv_renegotiate`

`static CURLcode schannel_recv_renegotiate( struct Curl_cfilter *cf, struct Curl_easy …` · [lib/vtls/schannel.c:L1784-L1965][f1]

Completes a server-requested renegotiation detected by schannel_recv, blocking up to 60 seconds (MAX_RENEG_BLOCK_TIME) so that callers waiting in only one direction are not stalled.

A call when no renegotiation is pending is CURLE_SSL_CONNECT_ERROR, as is a missing socket. On a fresh renegotiation it logs, moves state to ssl_connection_negotiating / ssl_connect_2, resets the state, stamps the start time, and records the needed io direction. The main loop repeatedly restores the saved io_need, advances the handshake via schannel_connect, and converts an incomplete result to CURLE_AGAIN; exceeding the 60-second budget fails with CURLE_SSL_CONNECT_ERROR. Between attempts it polls the socket with Curl_socket_check: the caller's own direction is blocked (up to 1-second intervals so progress callbacks run and the operation timeout is honored, returning CURLE_OPERATION_TIMEDOUT on expiry) while the other direction uses a zero timeout; socket readiness resumes the handshake, a timeout without blocking returns CURLE_AGAIN, and a poll error is CURLE_SSL_CONNECT_ERROR. On any exit the started flag, recv_renegotiating flag, and io_need are cleared; a failed result adds a 'renegotiation failed' message.

calls: [schannel_connect](r4-schannel-handshake.md#u-5f8743053a3d); uses: [schannel_recv](r4-schannel-record-io.md#u-57aff20ea872)

**Uncertainties.**

- Whether schannel_connect can fully re-establish the context during renegotiation depends on step2 behavior with buffered app data, which is only commented on, not proven here.

<a id="u-d0071ea7442e"></a>
### `schannel_send`

`static CURLcode schannel_send(struct Curl_cfilter *cf, struct Curl_easy *data, const …` · [lib/vtls/schannel.c:L1967-L2100][f1]

Encrypts and sends one TLS record.

A pending renegotiation is completed first; failure aborts. Input longer than cbMaximumMessage is truncated to one record's worth. A send buffer of header plus payload plus trailer is (re)allocated only when the needed size grows, the data is copied into the SECBUFFER_DATA slot, and EncryptMessage is called. On SEC_E_OK the entire record is sent in a loop honoring the operation timeout and socket writability: timeout (including a preexisting timeout) yields CURLE_OPERATION_TIMEDOUT, a poll failure CURLE_SEND_ERROR, and a partial write continues until the whole record is out. SEC_E_INSUFFICIENT_MEMORY maps to CURLE_OUT_OF_MEMORY and any other EncryptMessage error to CURLE_SEND_ERROR. Only when the full record was written is *pnwritten set to the unencrypted payload size; otherwise it stays 0 even if part of the ciphertext reached the wire.

**Notes.**

- failure: A partial ciphertext write reports zero bytes written with CURLE_OK deferred to the loop, so the caller cannot assume resumability of half-sent records.

calls: [schannel_recv_renegotiate](r4-schannel-record-io.md#u-c67f8ebd596f)

**Uncertainties.**

- When the loop exits due to an error after partial writes, ciphertext already sent is not tracked; resending behavior is decided by callers outside this file.

<a id="u-ef1ea1ae5cde"></a>
### `schannel_shutdown`

`static CURLcode schannel_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data, bo…` · [lib/vtls/schannel.c:L2403-L2562][f1]

Sends the TLS close_notify and drains the peer's response; idempotent and safe on failed handshakes.

A prior shutdown marks done immediately. Without a context it only sets done. When credentials and context exist and no shutdown was generated, it applies the SCHANNEL_SHUTDOWN control token (failure is CURLE_SEND_ERROR) and calls InitializeSecurityContext to produce the close token; SEC_E_OK or SEC_I_CONTEXT_EXPIRED saves the token, otherwise the buffer is freed and CURLE_SEND_ERROR returned. The token is then sent with resume support: CURLE_AGAIN or a partial write records io_need need-send and returns CURLE_OK with done unset; a send error is downgraded to success when the server already closed the connection, otherwise CURLE_SEND_ERROR. After the token is fully sent it is freed and sent_shutdown is set with done TRUE. Finally, when the peer's close_notify has not been seen, schannel_recv drains incoming data: CURLE_AGAIN sets need-recv, other errors become CURLE_RECV_ERROR, and a zero read marks the connection closed and done. cf->shutdown ends up TRUE on error or completion.

calls: [schannel_recv](r4-schannel-record-io.md#u-57aff20ea872)

**Uncertainties.**

- The (void)send_shutdown parameter means a caller-requested unidirectional close is silently treated as a full close_notify exchange; how callers choose the flag is outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/schannel.c
