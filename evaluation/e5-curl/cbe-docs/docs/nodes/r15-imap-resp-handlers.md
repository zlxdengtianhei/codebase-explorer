# IMAP response handlers

**Capability.** The pingpong state machine (imap_pp_statemachine) dispatching tagged and untagged replies to per-state handlers: greeting, capability, login, select, fetch, append, list/search; plus the statemachine wrapper group used by phase callbacks.

Handlers parse untagged lines, capture state such as UIDVALIDITY or message size, and chain the next DO command. Start at the statemachine to see the dispatch table over all imap_state_*_resp functions.

**Depends on.**

- [IMAP authentication and TLS upgrade](r15-imap-auth.md) · graph-confirmed · 6 edge(s)
- [IMAP commands and URL parsing](r15-imap-commands.md) · graph-confirmed · 5 edge(s)
- [IMAP core, types and framing](r15-imap-core.md) · graph-confirmed · 12 edge(s)
- [Generic SASL authentication](r15-sasl-auth.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [IMAP transfer driver](r15-imap-transfer-driver.md) · graph-confirmed · 4 edge(s)

Parent: [IMAP protocol implementation](r15-imap-protocol.md)

## Units (11)

<a id="u-5ec99d75dbd1"></a>
### `imap_pp_statemachine`

`static CURLcode imap_pp_statemachine(struct Curl_easy *data, struct connectdata *conn)` · [lib/imap.c:L1542-L1644][f1]

Drives the IMAP pingpong state machine: it reads server responses and dispatches them to the per-state handlers.

Missing per-connection or per-easy meta data returns CURLE_FAILED_INIT. While in IMAP_UPGRADETLS it performs the TLS handshake and returns immediately until the upgrade completes (re-entered via goto after STARTTLS). Pending send data is flushed first via Curl_pp_flushsend. It then loops: Curl_pp_readresp parses one response; a parse error code of -1 fails with CURLE_WEIRD_SERVER_REPLY, an empty code (0) breaks the loop awaiting more data, and otherwise the current state selects the handler - SERVERGREET, CAPABILITY, STARTTLS (which jumps back to the TLS upgrade path on success), AUTHENTICATE, LOGIN, LIST/SEARCH (shared handler), SELECT, FETCH, FETCH_FINAL, APPEND, APPEND_FINAL - while LOGOUT and any unhandled state is treated as an internal error that forces IMAP_STOP. The loop continues while no error occurred, the state is not IMAP_STOP, and Curl_pp_moredata indicates another buffered response.

**Notes.**

- failure: A continuation seen outside AUTHENTICATE/APPEND surfaces as imapcode -1 here and becomes CURLE_WEIRD_SERVER_REPLY.

calls: [Curl_pp_readresp](r12-pingpong-transport.md#u-f696034e55f0), [imap_state_fetch_resp](r15-imap-resp-handlers.md#u-d6bb4332a952), [imap_perform_upgrade_tls](r15-imap-auth.md#u-238bba4bb07d)

<a id="u-80274aece5b5"></a>
### `imap.c-statemach-drivers`

`static CURLcode imap_multi_statemach(struct Curl_easy *data, bool *done)` · [lib/imap.c:L1647-L1660][f1]

Wrappers that run the IMAP state machine and expose its sockets for polling.

imap_multi_statemach is the non-blocking driver used by the multi interface: it returns CURLE_FAILED_INIT without per-connection data, otherwise runs Curl_pp_statemach non-blocking and reports done only when the state has reached IMAP_STOP, always setting *done first. imap_block_statemach loops Curl_pp_statemach in blocking mode until IMAP_STOP or the first error, with a disconnecting flag forwarded so shutdown behavior can differ. imap_pollset adds the pingpong sockets to the pollset during connect and DO phases and returns CURLE_OK (no sockets) when the connection has no IMAP data.

calls: [Curl_pp_statemach](r12-pingpong-transport.md#u-673b0f00a073), [Curl_pp_pollset](r12-pingpong-transport.md#u-61def25ad0af)

<a id="u-cff7930d5b5d"></a>
### `imap_state_servergreet_resp`

`static CURLcode imap_state_servergreet_resp(struct Curl_easy *data, struct imap_conn …` · [lib/imap.c:L988-L1006][f1]

Handles the initial server greeting.

A PREAUTH greeting marks imapc->preauth and proceeds as authenticated; any code other than PREAUTH or OK fails with CURLE_WEIRD_SERVER_REPLY after logging; an OK greeting falls through normally. In all non-failing cases the next step is imap_perform_capability, whose result is returned.

calls: [imap_perform_capability](r15-imap-commands.md#u-7f3fe5078b59)

<a id="u-299c57fda937"></a>
### `imap_state_capability_resp`

`static CURLcode imap_state_capability_resp(struct Curl_easy *data, struct imap_conn *…` · [lib/imap.c:L1009-L1083][f1]

Parses CAPABILITY untagged lines and decides the next connection step.

For '*' responses it walks the line word by word, skipping blanks and newlines: a STARTTLS word sets tls_supported, LOGINDISABLED sets login_disabled, SASL-IR sets ir_supported, and any AUTH=<mech> word whose mechanism decodes via Curl_sasl_decode_mech (with full-length match) is OR-ed into sasl.authmechs; unknown words are skipped. For the tagged completion it branches on TLS policy: if use_ssl is set and the socket is not yet SSL, an OK response with STARTTLS support and no PREAUTH triggers imap_perform_starttls; if STARTTLS is not available and use_ssl is at most CURLUSESSL_TRY, it proceeds to imap_perform_authentication; otherwise it fails with CURLE_USE_SSL_FAILED after logging 'STARTTLS not available.'. Without a pending SSL requirement the tagged completion always proceeds to authentication.

**Notes.**

- condition: PREAUTH connections never take the STARTTLS branch even when the capability is advertised.

calls: [imap_perform_starttls](r15-imap-auth.md#u-2dc16fc7c7b1), [imap_perform_authentication](r15-imap-auth.md#u-efaa09f5691c)

**Uncertainties.**

- Curl_sasl_decode_mech's matching rules are external to this file.

<a id="u-b3a1bc756a4c"></a>
### `imap_state_login_resp`

`static CURLcode imap_state_login_resp(struct Curl_easy *data, struct imap_conn *imapc…` · [lib/imap.c:L1147-L1164][f1]

Handles the tagged LOGIN reply.

A non-OK reply logs 'Access denied.' with the response code and returns CURLE_LOGIN_DENIED; an OK reply ends the connect phase by moving to IMAP_STOP.

calls: [imap_state](r15-imap-core.md#u-648840e562ec)

<a id="u-fc92dc5b4934"></a>
### `imap_state_select_resp`

`static CURLcode imap_state_select_resp(struct Curl_easy *data, struct imap_conn *imap…` · [lib/imap.c:L1330-L1380][f1]

Processes SELECT responses: captures UIDVALIDITY from untagged lines, validates it on the tagged OK, and chains the follow-up DO command.

Untagged lines matching 'OK [UIDVALIDITY <n>' (checked at offset 2, minimum 18 bytes) store the value in mb_uidvalidity and set mb_uidvalidity_set; parse failures leave the flag unset. The tagged OK verifies the requested UIDVALIDITY when both sides have one: a mismatch fails with CURLE_REMOTE_FILE_NOT_FOUND after logging. Otherwise the mailbox is recorded on the connection (asserted not to already be set; allocation failure returns CURLE_OUT_OF_MEMORY) and the next command is dispatched: imap_perform_list for custom requests, imap_perform_search for queries, otherwise imap_perform_fetch. A tagged failure logs 'Select failed' and returns CURLE_LOGIN_DENIED.

calls: [imap_perform_list](r15-imap-commands.md#u-bf5fff79adc6), [imap_perform_search](r15-imap-commands.md#u-6aba4a290da5), [imap_perform_fetch](r15-imap-commands.md#u-304b1158baf6)

<a id="u-d6bb4332a952"></a>
### `imap_state_fetch_resp`

`static CURLcode imap_state_fetch_resp(struct Curl_easy *data, struct imap_conn *imapc…` · [lib/imap.c:L1383-L1476][f1]

Parses the first FETCH response line to learn the message size and starts the body transfer.

A non-untagged reply sets download size -1, moves to IMAP_STOP, and returns CURLE_REMOTE_FILE_NOT_FOUND. For untagged lines it locates a '{size}' literal via imap_find_literal and parses it; failure to parse fails with CURLE_WEIRD_SERVER_REPLY after logging 'Failed to parse FETCH response.'. On success the download size is set to the literal size, and any buffered overflow data is flushed to the client first: the overflow is trimmed from the receive buffer (nfinal cleared), capped at the literal size (a zero cap ends the transfer immediately at IMAP_STOP), written as body, and any remaining overflow is retained in the buffer or reset. If bytecount already equals the size the transfer is a no-op; otherwise maxdownload is set and the socket receiver is armed for the remaining literal bytes. The state moves to IMAP_STOP at the end of the DO phase in all successful paths.

calls: [imap_find_literal](r15-imap-core.md#u-81549113d8d4), [Curl_xfer_setup_nop](r10-xfer-direction-api.md#u-18a177e8d14f)

**Uncertainties.**

- Whether client write callbacks can partially consume the overflow chunk and how errors interact with the retained buffer is external.

<a id="u-7c4487c6d593"></a>
### `imap_state_fetch_final_resp`

`static CURLcode imap_state_fetch_final_resp(struct Curl_easy *data, struct imap_conn …` · [lib/imap.c:L1479-L1495][f1]

Consumes the final tagged reply after a FETCH download.

A non-OK reply yields CURLE_WEIRD_SERVER_REPLY; an OK reply ends the DONE phase by moving to IMAP_STOP.

calls: [imap_state](r15-imap-core.md#u-648840e562ec)

<a id="u-78892ad64a5a"></a>
### `imap_state_append_resp`

`static CURLcode imap_state_append_resp(struct Curl_easy *data, struct imap_conn *imap…` · [lib/imap.c:L1498-L1521][f1]

Handles the server's reply to the APPEND command.

Any reply other than the '+' continuation fails with CURLE_UPLOAD_FAILED and leaves the state unchanged. On '+' it records the upload size for progress, switches the transfer to send mode on the first socket, and ends the DO phase by moving to IMAP_STOP so the body upload can proceed.

calls: [Curl_xfer_setup_send](r10-xfer-direction-api.md#u-886095062fc5)

<a id="u-7e0d778819c5"></a>
### `imap_state_append_final_resp`

`static CURLcode imap_state_append_final_resp(struct Curl_easy *data, struct imap_conn…` · [lib/imap.c:L1524-L1540][f1]

Consumes the final tagged reply after an APPEND upload.

A non-OK reply returns CURLE_UPLOAD_FAILED; an OK reply moves the state to IMAP_STOP, ending the DONE phase.

calls: [imap_state](r15-imap-core.md#u-648840e562ec)

<a id="u-02788f28d805"></a>
### `imap_state_listsearch_resp`

`static CURLcode imap_state_listsearch_resp(struct Curl_easy *data, struct imap_conn *…` · [lib/imap.c:L1203-L1327][f1]

Delivers LIST and SEARCH results to the client, with special handling for FETCH-style responses carrying an IMAP literal.

Missing per-easy IMAP data returns CURLE_FAILED_INIT. When the response is untagged ('*') and is a custom FETCH listing (per is_custom_fetch_listing) nothing is written here. Other untagged responses: if a literal '{size}' exists on the first line, and the size parses up to the closing brace, the header line is written as body, then any bytes already buffered after the header are written (truncated to the literal size), with leftovers kept in the receive buffer and tracked in pp->overflow; the download size is set to header length plus literal size (saturating at CURL_OFF_T_MAX to avoid overflow); if all bytes are already delivered the transfer is set up as a no-op, otherwise maxdownload is set and the receiver is pointed at the socket; the state moves to IMAP_STOP ending the DO phase. A malformed literal or a line with no literal is written as-is as body data. A tagged non-OK reply fails with CURLE_QUOTE_ERROR; a tagged OK ends the DO phase.

calls: [imap.c-custom-fetch-listing](r15-imap-commands.md#u-0a582d6feb17), [imap_find_literal](r15-imap-core.md#u-81549113d8d4), [Curl_xfer_setup_nop](r10-xfer-direction-api.md#u-18a177e8d14f)

**Uncertainties.**

- Exact behavior of curlx_str_number/curlx_str_single on overflow or trailing characters is external; only the parsed/not-parsed split is evidenced here.
- The chunk arithmetic assumes after_header bytes in the recvbuf are contiguous literal body.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/imap.c
