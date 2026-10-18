# TFTP Protocol

**Capability.** UDP file transfer via an explicit per-connection state machine (START/RX/TX), packet encoding/decoding helpers, option negotiation (OACK), retry/timeout budgets, and curl callback plumbing.

Follow tftp_do/tftp_perform into tftp_multi_statemach and tftp_state_machine; tftp_rx/tftp_tx/tftp_send_first are the state handlers. Timeouts and the packet accessors are cross-cutting helpers used by every handler.

**Depends on.**

- [Polling and Pollsets](r5-poll-waiting.md) · graph-confirmed · 2 edge(s)
- [Trace and Debug Logging](r1-trace-logging.md) · graph-only · 38 edge(s)

Parent: [Protocol and Filter Implementations](r5-protocol-implementations.md)

## Units (22)

<a id="u-1f8e84abd5a0"></a>
### `tftp.c-packet-accessors`

`static void setpacketevent(struct tftp_packet *packet, unsigned short num)` · [lib/tftp.c:L209-L213][f1]

Tiny helpers encode and decode the four header bytes of a TFTP packet and parse option strings inside a received packet.

setpacketevent/setpacketblock write 16-bit big-endian values into bytes 0-1 (opcode) and 2-3 (block) of the send buffer; getrpacketevent/getrpacketblock read them back from the receive buffer. tftp_strnlen returns the length of a NUL-terminated string within maxlen, or maxlen if unterminated. tftp_option_get walks 'name\0value\0' pairs: it advances past the option name (returning NULL if the name reaches len, i.e. loc >= len), then past the value (NULL if loc exceeds len), returning a pointer past the value terminator and outputting option/value pointers.

uses: [tftp.c-packet-accessors](r5-tftp-protocol.md#u-1f8e84abd5a0)

**Uncertainties.**

- The byte layout assumes packet->data buffers are at least 4 bytes; callers own that guarantee.

<a id="u-de75028e485e"></a>
### `tftp_conn_dtor`

`static void tftp_conn_dtor(const void *key, size_t klen, void *entry)` · [lib/tftp.c:L893-L901][f1]

Connection-meta destructor for the tftp_conn entry: frees the receive and send packet buffers with curlx_safefree and then the state struct itself with curlx_free.

Key and key length arguments are ignored, matching the meta-store destructor signature.

**Uncertainties.**

- Whether the meta store invokes this under connection teardown locks is outside this file.

<a id="u-95cb452d7a8f"></a>
### `tftp_connect`

`static CURLcode tftp_connect(struct Curl_easy *data, bool *done)` · [lib/tftp.c:L910-L1001][f1]

Connect callback that allocates and initializes the per-connection TFTP state.

It callocs a tftp_conn and installs it in the connection meta under CURL_META_TFTP_CONN with tftp_conn_dtor as destructor; allocation or registration failure returns CURLE_OUT_OF_MEMORY. The block size comes from data->set.tftp_blksize (else 512); both packet buffers are allocated at max(blksize, 512)+4 bytes, each allocation failure returning CURLE_OUT_OF_MEMORY and leaking earlier buffers (no cleanup on that path). It marks the connection non-reusable (connclose), records data, socket, START state, TFTP_ERR_NONE, blksize 512 pending OACK, and the requested blksize. Missing remote address returns CURLE_FAILED_INIT (DEBUGASSERT); local_addr's family is copied from the remote. tftp_set_timeouts failure propagates. If the socket is not yet bound, bind() uses the remote address's length; failure logs and returns CURLE_COULDNT_CONNECT, success sets conn->bits.bound. On success *done is TRUE.

calls: [tftp_conn_dtor](r5-tftp-protocol.md#u-de75028e485e), [tftp_set_timeouts](r5-tftp-protocol.md#u-2b84095af0b1)

**Uncertainties.**

- Bind-by-any-address: local_addr is only family-initialized, so the actual local address chosen by bind() is OS-dependent.
- Packet buffer leak on second allocation failure is a real code path: no rollback is visible.

<a id="u-cead1e5175bf"></a>
### `tftp_connect_for_rx`

`static CURLcode tftp_connect_for_rx(struct tftp_conn *state, tftp_event_t event)` · [lib/tftp.c:L640-L652][f1]

Transitions into the RX state on connection confirmation: logs, sets state to TFTP_STATE_RX, recomputes timeouts via tftp_set_timeouts (propagating its timeout failure), then dispatches the event to tftp_rx and returns its result.

calls: [tftp_set_timeouts](r5-tftp-protocol.md#u-2b84095af0b1), [tftp_rx](r5-tftp-protocol.md#u-ae9046a01476)

<a id="u-605678ac0084"></a>
### `tftp_connect_for_tx`

`static CURLcode tftp_connect_for_tx(struct tftp_conn *state, tftp_event_t event)` · [lib/tftp.c:L504-L516][f1]

Transitions into the TX state on connection confirmation: logs, sets state to TFTP_STATE_TX, recomputes timeouts via tftp_set_timeouts (propagating its CURLE_OPERATION_TIMEDOUT failure), then dispatches the event to tftp_tx and returns its result.

calls: [tftp_set_timeouts](r5-tftp-protocol.md#u-2b84095af0b1), [tftp_tx](r5-tftp-protocol.md#u-3c5cc99cb06d)

<a id="u-7f78f8422061"></a>
### `tftp_do`

`static CURLcode tftp_do(struct Curl_easy *data, bool *done)` · [lib/tftp.c:L1294-L1321][f1]

DO callback that initiates the TFTP transfer.

If no TFTP state exists yet it runs tftp_connect (propagating failure) and re-fetches the state; still missing state returns CURLE_TFTP_ILLEGAL. It then runs tftp_perform; when perform succeeded, the stored internal error is translated via tftp_translate_code and may replace the OK result. The perform error itself takes precedence over the translated error.

calls: [tftp_connect](r5-tftp-protocol.md#u-95cb452d7a8f), [tftp_perform](r5-tftp-protocol.md#u-ee4e5fbec179), [tftp_translate_code](r5-tftp-protocol.md#u-ac91d452f52a)

<a id="u-0cf7053e9335"></a>
### `tftp_doing`

`static CURLcode tftp_doing(struct Curl_easy *data, bool *dophase_done)` · [lib/tftp.c:L1237-L1252][f1]

DOing-phase callback that advances the state machine via tftp_multi_statemach.

Completion is logged; while incomplete and no error, it refreshes progress with Curl_pgrsCheck because the multi machinery lacks DOING progress handling and TFTP may transfer entirely within this phase.

calls: [tftp_multi_statemach](r5-tftp-protocol.md#u-536b3f2f4c6c)

<a id="u-f6dadc046fb0"></a>
### `tftp_done`

`static CURLcode tftp_done(struct Curl_easy *data, CURLcode status, bool premature)` · [lib/tftp.c:L1010-L1028][f1]

Done callback that finalizes the transfer.

It ignores status and premature, calls Curl_pgrsDone; a truthy return (abort) yields CURLE_ABORTED_BY_CALLBACK immediately. If TFTP state exists in connection meta, the stored internal error is translated via tftp_translate_code and returned; with no state the result stays CURLE_OK.

calls: [tftp_translate_code](r5-tftp-protocol.md#u-ac91d452f52a); uses: [tftp_connect](r5-tftp-protocol.md#u-95cb452d7a8f)

<a id="u-536b3f2f4c6c"></a>
### `tftp_multi_statemach`

`static CURLcode tftp_multi_statemach(struct Curl_easy *data, bool *done)` · [lib/tftp.c:L1175-L1228][f1]

Drives one iteration of the TFTP state machine.

Missing meta state returns CURLE_FAILED_INIT. tftp_state_timeout supplies a possible TIMEOUT event and the remaining budget: a negative budget fails with CURLE_OPERATION_TIMEDOUT after failf. If a timeout event fired, the state machine handles it; completion (FIN) sets *done and switches the transfer to a no-op via Curl_xfer_setup_nop. Otherwise SOCKET_READABLE decides: -1 logs the socket error and records TFTP_EVENT_ERROR in state->event (returned result stays OK); nonzero readiness receives and processes a packet, propagating receive or state-machine errors, again setting *done and nop transfer on FIN; zero means the poll timed out and nothing happens.

calls: [tftp_state_timeout](r5-tftp-protocol.md#u-54c5bb814398), [tftp_state_machine](r5-tftp-protocol.md#u-5a85928a44e9), [tftp_receive_packet](r5-tftp-protocol.md#u-dfda784b6f9e)

**Uncertainties.**

- After SOCKET_READABLE fails, state->event is set to ERROR but tftp_state_machine is not called in that branch, so the recorded event is consumed only on a later iteration; that asymmetry is as coded.

<a id="u-f2791732168f"></a>
### `tftp_option_add`

`static CURLcode tftp_option_add(struct tftp_conn *state, size_t *csize, size_t index,…` · [lib/tftp.c:L332-L345][f1]

Appends one NUL-terminated option token to the send packet at byte offset index, bounded by the current blksize.

If index is at or beyond blksize, or the token plus its NUL would not fit in blksize - index, it returns CURLE_TFTP_ILLEGAL without writing. Otherwise it copies the token with curlx_strcopy into the remaining space and advances *csize by token length plus one.

**Uncertainties.**

- Whether curlx_strcopy's blen bound is respected byte-exactly for truncation is outside this file.

<a id="u-eae73e4ff847"></a>
### `tftp_parse_option_ack`

`static CURLcode tftp_parse_option_ack(struct tftp_conn *state, const char *ptr, int len)` · [lib/tftp.c:L259-L330][f1]

Parses a server OACK packet's option list and updates the connection state.

It first resets blksize to the 512-byte default, so an OACK without blksize leaves the default in force. The loop repeatedly extracts name/value pairs via tftp_option_get; a malformed pair fails with CURLE_TFTP_ILLEGAL. For a 'blksize' option, the value is parsed with curlx_str_number bounded by TFTP_BLKSIZE_MAX; any of zero, below TFTP_BLKSIZE_MIN, or above the client-requested blksize fails with CURLE_TFTP_ILLEGAL; a valid value is stored in state->blksize. For 'tsize' on downloads, a successfully parsed size is reported via Curl_pgrsSetDownloadSize; a parse failure or a zero tsize (only when not uploading) fails with CURLE_TFTP_ILLEGAL; tsize is ignored on upload.

calls: [tftp.c-packet-accessors](r5-tftp-protocol.md#u-1f8e84abd5a0); uses: [tftp_set_timeouts](r5-tftp-protocol.md#u-2b84095af0b1)

**Uncertainties.**

- curlx_str_number's failure semantics (nonzero return on invalid input) are inferred from usage, not this file.

<a id="u-ee4e5fbec179"></a>
### `tftp_perform`

`static CURLcode tftp_perform(struct Curl_easy *data, bool *dophase_done)` · [lib/tftp.c:L1261-L1282][f1]

Entry point that starts the transfer.

Missing meta state returns CURLE_FAILED_INIT with *dophase_done FALSE. It injects TFTP_EVENT_INIT into the state machine; if the state already reached FIN or an error occurred, it returns immediately. Otherwise it runs one statemach iteration, whose result and dophase_done are propagated.

calls: [tftp_state_machine](r5-tftp-protocol.md#u-5a85928a44e9), [tftp_multi_statemach](r5-tftp-protocol.md#u-536b3f2f4c6c)

<a id="u-4f212a5ac983"></a>
### `tftp_pollset`

`static CURLcode tftp_pollset(struct Curl_easy *data, struct easy_pollset *ps)` · [lib/tftp.c:L1030-L1034][f1]

Adds the TFTP socket (conn->sock[FIRSTSOCKET]) to the pollset for reading via Curl_pollset_add_in, used for both the connecting and doing phases as registered in the protocol handler.

uses: [tftp_multi_statemach](r5-tftp-protocol.md#u-536b3f2f4c6c)

<a id="u-dfda784b6f9e"></a>
### `tftp_receive_packet`

`static CURLcode tftp_receive_packet(struct Curl_easy *data, struct tftp_conn *state)` · [lib/tftp.c:L1043-L1134][f1]

Reads one datagram and classifies it.

recvfrom fills rbytes with at most blksize+4 bytes. If bytes arrived, a pinned remote must match the source exactly (length and memcmp), otherwise CURLE_RECV_ERROR; the first datagram pins the source address and sets remote_pinned. Fewer than 4 bytes is treated as a TIMEOUT event (not an error return). Otherwise the opcode becomes state->event: DATA on a download delivers payload to the client via Curl_client_write only when rbytes > 4 and the block is the expected next one; a write failure triggers tftp_state_machine with TFTP_EVENT_ERROR and returns the error. ERROR stores the server error code in state->error and logs the message if it is NUL-terminated. OACK is parsed by tftp_parse_option_ack, propagating its failure. RRQ/WRQ or unknown opcodes only log an internal-error failf. Finally Curl_pgrsUpdate runs; its failure likewise injects TFTP_EVENT_ERROR and returns.

calls: [tftp_parse_option_ack](r5-tftp-protocol.md#u-eae73e4ff847), [tftp_state_machine](r5-tftp-protocol.md#u-5a85928a44e9), [tftp.c-packet-accessors](r5-tftp-protocol.md#u-1f8e84abd5a0)

**Uncertainties.**

- A non-upload DATA packet returns CURLE_TFTP_ILLEGAL before address pinning is rechecked for that datagram only when bytes arrived; ordering with the short-packet branch matters and is as coded.
- state->event being a raw opcode cast means out-of-range opcodes flow through the switch's default.

<a id="u-ae9046a01476"></a>
### `tftp_rx`

`static CURLcode tftp_rx(struct tftp_conn *state, tftp_event_t event)` · [lib/tftp.c:L525-L638][f1]

Receive-state event handler.

On DATA: the received block number determines the path — the expected next block resets retries; a repeat of the current block is re-ACKed; any other block is logged and ignored (breaks without sending). For accepted blocks it ACKs via a 4-byte sendto (failure returns CURLE_SEND_ERROR), then enters FIN if the datagram was shorter than blksize+4, else stays in RX, refreshing rx_time. On OACK it ACKs block 0, resets retries, and moves to RX; send failure returns CURLE_SEND_ERROR. On TIMEOUT retries increment; past retry_max the error becomes TFTP_ERR_TIMEOUT with state FIN, otherwise the previous ACK is resent (socket failure CURLE_SEND_ERROR). On ERROR it best-effort sends a 4-byte error packet and enters FIN. Unknown events fail with failf and return CURLE_TFTP_ILLEGAL.

calls: [tftp.c-packet-accessors](r5-tftp-protocol.md#u-1f8e84abd5a0); uses: [tftp_parse_option_ack](r5-tftp-protocol.md#u-eae73e4ff847)

<a id="u-c9e50efadb69"></a>
### `tftp_send_first`

`static CURLcode tftp_send_first(struct tftp_conn *state, tftp_event_t event)` · [lib/tftp.c:L654-L800][f1]

START-state handler that sends the initial RRQ/WRQ.

On INIT or TIMEOUT it increments retries and, past retry_max, sets TFTP_ERR_NORESPONSE and enters FIN without error. It selects mode 'netascii' when ASCII was requested, builds the request with the opcode, the URL-decoded path (skipping the leading slash; an empty path fails with CURLE_TFTP_ILLEGAL), and mode, failing on decode errors or names that would exceed blksize (memory freed, CURLE_TFTP_ILLEGAL). Unless tftp_no_options is set it appends tsize, blksize, and timeout options via tftp_option_add; any failure there fails with CURLE_TFTP_ILLEGAL. The request is sent to the connection's remote address via sendto; a missing remote address returns CURLE_FAILED_INIT and a short/failed send returns CURLE_SEND_ERROR. On OACK it delegates to tftp_connect_for_tx (upload) or tftp_connect_for_rx (download); on ACK it requires an upload (else CURLE_TFTP_ILLEGAL) then delegates to tx; on DATA it requires a download (else CURLE_TFTP_ILLEGAL) then delegates to rx. ERROR sets FIN; unknown events fail with CURLE_TFTP_ILLEGAL.

calls: [tftp_option_add](r5-tftp-protocol.md#u-f2791732168f), [tftp_connect_for_tx](r5-tftp-protocol.md#u-605678ac0084), [tftp_connect_for_rx](r5-tftp-protocol.md#u-cead1e5175bf), [tftp.c-packet-accessors](r5-tftp-protocol.md#u-1f8e84abd5a0)

**Uncertainties.**

- Curl_urldecode's REJECT_ZERO behavior is defined in lib/escape.c, not visible here.
- Whether sbytes from curl_msnprintf counts exactly the formatted bytes including NULs is inferred from the format.

<a id="u-2b84095af0b1"></a>
### `tftp_set_timeouts`

`static CURLcode tftp_set_timeouts(struct tftp_conn *state)` · [lib/tftp.c:L155-L199][f1]

Computes the retry budget for a TFTP state from the connection time budget.

Curl_timeleft_ms provides the remaining time; a negative value means the deadline already passed, so it fails with CURLE_OPERATION_TIMEDOUT. For a remaining time between 1ms and one hour, the per-block timeout in seconds is (timeout_ms+500)/1000; otherwise (unlimited or >=1h) it defaults to 15s. retry_max (re-ACK attempts) is timeout/5 clamped to [3,50], and retry_time is timeout/retry_max floored at 1 second. It stamps state->rx_time with the current time and returns CURLE_OK.

**Uncertainties.**

- Whether Curl_timeleft_ms reflects connect-only or total transfer timeouts is not visible in this file despite the header comment.

<a id="u-a3ae69190a6e"></a>
### `tftp_setup_connection`

`static CURLcode tftp_setup_connection(struct Curl_easy *data, struct connectdata *conn)` · [lib/tftp.c:L1323-L1342][f1]

Prepares the connection for TFTP: requests UDP transport and strips a trailing ';mode=netascii' or ';mode=octet' suffix from the URL path, setting (or clearing) prefer_ascii accordingly.

A path shorter than the suffix is left untouched. Always returns CURLE_OK.

**Notes.**

- side_effect: Mutates data->state.up.path in place by truncating the mode suffix.

<a id="u-5a85928a44e9"></a>
### `tftp_state_machine`

`static CURLcode tftp_state_machine(struct tftp_conn *state, tftp_event_t event)` · [lib/tftp.c:L861-L891][f1]

Dispatches an event to the handler for the current state.

START delegates to tftp_send_first, RX to tftp_rx, TX to tftp_tx; FIN logs 'TFTP finished' and returns OK. Any unrecognized state fails with CURLE_TFTP_ILLEGAL. The handler's result is propagated unchanged.

calls: [tftp_send_first](r5-tftp-protocol.md#u-c9e50efadb69), [tftp_rx](r5-tftp-protocol.md#u-ae9046a01476), [tftp_tx](r5-tftp-protocol.md#u-3c5cc99cb06d)

<a id="u-54c5bb814398"></a>
### `tftp_state_timeout`

`static timediff_t tftp_state_timeout(struct tftp_conn *state, tftp_event_t *event)` · [lib/tftp.c:L1143-L1166][f1]

Checks both deadline and per-block inactivity.

It clears *event to TFTP_EVENT_NONE when an output pointer is given. Curl_timeleft_ms below zero marks the error as TFTP_ERR_TIMEOUT, enters FIN, and returns the negative value. Otherwise, if more than retry_time seconds passed since rx_time, *event becomes TFTP_EVENT_TIMEOUT and rx_time is refreshed even with no traffic. The remaining time budget is always returned.

uses: [tftp_set_timeouts](r5-tftp-protocol.md#u-2b84095af0b1)

<a id="u-ac91d452f52a"></a>
### `tftp_translate_code`

`static CURLcode tftp_translate_code(tftp_error_t error)` · [lib/tftp.c:L809-L852][f1]

Maps an internal tftp_error_t to a CURLcode.

TFTP_ERR_NONE yields CURLE_OK. NOTFOUND, PERM, UNKNOWNID, NOSUCHUSER map to their CURLE_TFTP_* equivalents; DISKFULL to CURLE_REMOTE_DISK_FULL; EXISTS to CURLE_REMOTE_FILE_EXISTS; UNDEF and ILLEGAL to CURLE_TFTP_ILLEGAL; TIMEOUT to CURLE_OPERATION_TIMEDOUT; NORESPONSE to CURLE_COULDNT_CONNECT; any other value to CURLE_ABORTED_BY_CALLBACK.

**Uncertainties.**

- Whether any server error value outside the enumerated internal codes can reach the default branch is not shown here.

<a id="u-3c5cc99cb06d"></a>
### `tftp_tx`

`static CURLcode tftp_tx(struct tftp_conn *state, tftp_event_t event)` · [lib/tftp.c:L358-L502][f1]

Transmit-state event handler that sends the next DATA block.

It rejects non-upload transfers with CURLE_TFTP_ILLEGAL. On ACK: a mismatched block number (except the tftpd-hpa 65535-ACK-when-expecting-0 wraparound bug) increments retries; exceeding retry_max fails with CURLE_SEND_ERROR, otherwise the previous packet is re-sent via sendto (socket failure also CURLE_SEND_ERROR) and the handler returns early. A matching ACK resets rx_time, increments the block, and clears retries; OACK starts at block 1. After setting the DATA header, if block > 1 and the previous payload was short, the transfer is complete and state moves to TFTP_STATE_FIN. Otherwise it loops Curl_client_read until a full blksize payload accumulates or a short read ends input, then sends; sendto failure is CURLE_SEND_ERROR, success updates writebytecount and upload progress. On TIMEOUT: retries increment; past retry_max the error becomes TFTP_ERR_TIMEOUT and state FIN, else the packet is resent and the upload counter is reset to the same byte position. On ERROR it sends a 4-byte error packet (return ignored) and enters FIN. Any other event fails via failf but returns CURLE_OK unless set earlier.

calls: [tftp.c-packet-accessors](r5-tftp-protocol.md#u-1f8e84abd5a0); uses: [tftp_set_timeouts](r5-tftp-protocol.md#u-2b84095af0b1), [tftp.c-packet-accessors](r5-tftp-protocol.md#u-1f8e84abd5a0)

**Uncertainties.**

- Curl_client_read's eos semantics (whether a zero cb always ends the loop) come from lib/sendf.c, not visible here.
- The state assignment to TFTP_STATE_FIN twice in the ERROR case is harmless but unexplained.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/tftp.c
