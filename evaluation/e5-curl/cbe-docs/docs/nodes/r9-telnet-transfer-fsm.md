# Telnet transfer loop and data path

**Capability.** The transfer lifecycle: init_telnet allocation and easy-handle meta destructor, check_telnet_options application, telrcv byte FSM, suboption response, send_telnet_data IAC escaping, sendsuboption (NAWS), and the telnet_do pump plus telnet_done cleanup, wired into the Curl_protocol_telnet vtable.

Use this child to trace raw socket bytes to body output and back. Options validation rejects non-ASCII strings; only NAWS suboptions produce replies.

**Depends on.**

- [Case-insensitive strings](r9-caseless-strings.md) · graph-confirmed · 5 edge(s)
- [printf engine \(mprintf\)](r9-mprintf.md) · graph-confirmed · 7 edge(s)
- [Transfer progress](r9-progress.md) · graph-confirmed · 3 edge(s)
- [Telnet state, options and negotiation](r9-telnet-state-and-options.md) · graph-confirmed · 8 edge(s)
- [Telnet verbose logging](r9-telnet-verbose-logging.md) · graph-confirmed · 10 edge(s)

Parent: [Telnet protocol backend](r9-telnet.md)

## Units (12)

<a id="u-22b56216d671"></a>
### `telnet-c-protocol-table`

`group` · [lib/telnet.c:L1551-L1576][f1]

Module tail defining the Curl_protocol_telnet handler struct: only do_it (telnet_do) and done (telnet_done) are populated; every other callback including setup_connection, disconnect, and all pollset hooks is NULL, reflecting that telnet performs its whole exchange inside do.

<a id="u-6bccf2645cbd"></a>
### `telnet-c-residuals`

`group` · [lib/telnet.c:L167-L169][f1]

Small residual regions between symbols: guard closing/opening lines and the end-of-file #endif with the protocol-table comment; no behavior beyond the neighbors that own them.

<a id="u-8680c74c2bff"></a>
### `check_telnet_options`

`static CURLcode check_telnet_options(struct Curl_easy *data, struct TELNET *tn)` · [lib/telnet.c:L828-L955][f1]

Validates and applies CURLOPT_TELNETOPTIONS into the TELNET state.

If credentials exist, a non-ASCII username returns CURLE_BAD_FUNCTION_ARGUMENT; otherwise USER,<name> is prepended to telnet_vars (allocation failure frees the list, NULLs it, returns CURLE_OUT_OF_MEMORY) and NEW_ENVIRON is preferred. Each option string must contain '='; a missing separator fails with CURLE_SETOPT_OPTION_SYNTAX. Recognized names by length: TTYPE (5) sets subopt_ttype and prefers TTYPE; XDISPLOC (8) sets subopt_xdisploc; NEW_ENV (7) appends the value to telnet_vars; WS (2) parses '<num>x<num>' with both capped at 0xffff via curlx_str_number/curlx_str_single, else fails with syntax error and stores subopt_wsx/wsy; BINARY (6) disables BINARY preference in both directions when the value parses as a number not equal to 1. Non-ASCII argument values are silently skipped. Unknown names of any length fail with CURLE_UNKNOWN_OPTION (logged for the default case). On any accumulated error the whole telnet_vars list is freed and NULLed before returning the first error.

calls: [str_is_nonascii](r9-telnet-transfer-fsm.md#u-c3807a0964fd), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

**Uncertainties.**

- BINARY value parse failures are silently ignored (option treated as unset); whether that is intended is not stated in source.

<a id="u-2b0230d865b2"></a>
### `init_telnet`

`static CURLcode init_telnet(struct Curl_easy *data)` · [lib/telnet.c:L180-L223][f1]

Allocates and initializes the per-transfer TELNET state, or returns CURLE_OUT_OF_MEMORY on allocation failure.

Initializes the dynbuf (capacity 0xffff), sets the FSM to CURL_TS_DATA, clears the suboption pointer, prefers SGA and BINARY in both directions, prefers him-ECHO (without requesting it), and marks NAWS subnegotiation to send. Registers the struct in the easy-handle meta store with telnet_easy_dtor as destructor via Curl_meta_set, whose result is returned.

uses: [telnet_easy_dtor](r9-telnet-transfer-fsm.md#u-1605b760a7d4)

<a id="u-d88fdb892af2"></a>
### `send_telnet_data`

`static CURLcode send_telnet_data(struct Curl_easy *data, struct TELNET *tn, const cha…` · [lib/telnet.c:L604-L664][f1]

Escapes and writes a data block to the peer, handling the telnet 0xFF doubling.

Negative nread returns CURLE_TOO_LARGE. If the buffer contains IAC (0xFF), each byte is copied into tn->out with an extra 0xFF appended after each IAC; otherwise the input is sent directly, avoiding the copy. The write loop polls the first socket for writability using Curl_timeleft_ms: a negative timeout returns CURLE_OPERATION_TIMEDOUT; timeout_ms 0 becomes an infinite poll; poll failure yields CURLE_SEND_ERROR, timeout yields CURLE_OPERATION_TIMEDOUT, readiness triggers a partial-aware Curl_xfer_send that advances total_written. Loop ends when all bytes are written or an error occurs.

calls: [curlx_dyn_reset](r3-dynbuf.md#u-76d5fbff65c6)

<a id="u-c24eac885a4b"></a>
### `sendsuboption`

`static void sendsuboption(struct Curl_easy *data, struct TELNET *tn, int option)` · [lib/telnet.c:L671-L718][f1]

Sends suboption data after negotiation; only NAWS is implemented, other options produce no output.

For NAWS it builds the IAC SB NAWS width height IAC SE frame in the suboption buffer (sizes byte-swapped via htons for network order; CURL_SB_ACCUM silently truncates if the 512-byte buffer overflows), logs it via printsub, then sends in three parts: the 3-byte header and 2-byte footer with Curl_xfer_send, and the 4-byte window size through send_telnet_data so embedded 0xFF bytes are escaped. Header/footer send failures are logged but not propagated; send_telnet_data's failure code is discarded.

calls: [send_telnet_data](r9-telnet-transfer-fsm.md#u-d88fdb892af2)

**Uncertainties.**

- Whether partial sends of header/footer break the frame is unhandled in the visible code; only logging occurs.

<a id="u-c3807a0964fd"></a>
### `str_is_nonascii`

`static bool str_is_nonascii(const char *str)` · [lib/telnet.c:L818-L826][f1]

Returns TRUE if the NUL-terminated string contains any byte with the high bit set, FALSE otherwise.

<a id="u-d126e245a4fe"></a>
### `suboption`

`static CURLcode suboption(struct Curl_easy *data, struct TELNET *tn)` · [lib/telnet.c:L971-L1055][f1]

Responds to a completed received suboption held in the suboption buffer; empty payloads are ignored.

Reads the option byte and dispatches: TTYPE and XDISPLOC reject NULL or IAC-containing values with CURLE_BAD_FUNCTION_ARGUMENT and values longer than 1000 chars with CURLE_SEND_ERROR, then format 'IAC SB <opt> IS <value> IAC SE' into a 2048-byte stack buffer via curl_msnprintf and send it; send failure is logged and propagated. NEW_ENVIRON builds an IS reply listing every telnet_vars entry (entries with IAC abort with CURLE_BAD_FUNCTION_ARGUMENT; entries that fit are appended, splitting NAME,VALUE on the first comma; entries too large are silently skipped) and sends it. Unknown options produce no reply. Returns CURLE_OK otherwise.

**Uncertainties.**

- The 2048-byte temp truncation semantics rely on curl_msnprintf's return length, which is not verified against truncation here.

<a id="u-ee7aa2e45c82"></a>
### `telnet_do`

`static CURLcode telnet_do(struct Curl_easy *data, bool *done)` · [lib/telnet.c:L1220-L1551][f1]

Main telnet transfer loop: initializes TELNET state (propagating init/check failures including CURLE_FAILED_INIT when meta lookup misses), applies user options, then pumps bidirectional data until an error, EOF, close, or timeout.

*done is set TRUE unconditionally at entry. Two platform paths share behavior: poll the first socket for readability (and the input source unless a user read callback is set) and the input source for data to upload. Network reads via Curl_xfer_recv treat CURLE_AGAIN as retry, other errors or nread==0 stop the loop; received bytes increment download progress and feed telrcv. After telrcv succeeds and the peer initiated negotiation, telnet_negotiate runs exactly once (guarded by already_negotiate/please_negotiate) so non-telnet servers are not spoken to. Input side: with a user fread callback, CURL_READFUNC_ABORT ends with CURLE_READ_ERROR and PAUSE just re-loops; without one, stdin is polled (invalid fd fails with CURLE_RECV_ERROR before looping) and read(); snread<0 stops, snread>0 goes through send_telnet_data and increments upload progress. The Windows path mirrors this with WSA events and named-pipe/stdin reads; WSAEventSelect or ReadFile failures yield CURLE_RECV_ERROR/READ_ERROR. Each iteration enforces Curl_timeleft_ms (negative yields 'Time-out' and CURLE_OPERATION_TIMEDOUT); the non-Windows loop also runs Curl_pgrsUpdate. On any recv error carrying ECONNRESET the failure is only debug-logged. On exit, Curl_xfer_setup_nop marks the transfer as finished and the last result is returned.

calls: [init_telnet](r9-telnet-transfer-fsm.md#u-2b0230d865b2), [check_telnet_options](r9-telnet-transfer-fsm.md#u-8680c74c2bff), [telrcv](r9-telnet-transfer-fsm.md#u-4fad1ef8f717), [send_telnet_data](r9-telnet-transfer-fsm.md#u-d88fdb892af2), [telnet_negotiate](r9-telnet-state-and-options.md#u-1ed47d41b533)

**Uncertainties.**

- result may be returned stale from a previous loop iteration when the poll loop exits via keepon paths that never set result (e.g. poll -1 on non-Windows path without prior assignment is a 'continue', but Windows WAIT_TIMEOUT paths rely on send_telnet_data to set it); the exact stale-result exposure is not fully provable from source.

<a id="u-f02604d842b1"></a>
### `telnet_done`

`static CURLcode telnet_done(struct Curl_easy *data, CURLcode status, bool premature)` · [lib/telnet.c:L1211-L1218][f1]

Cleanup callback: removes the TELNET struct from the easy-handle meta store (triggering telnet_easy_dtor) and returns CURLE_OK regardless of status or premature flags.

uses: [telnet_easy_dtor](r9-telnet-transfer-fsm.md#u-1605b760a7d4)

<a id="u-1605b760a7d4"></a>
### `telnet_easy_dtor`

`static void telnet_easy_dtor(const void *key, size_t klen, void *entry)` · [lib/telnet.c:L170-L178][f1]

Meta destructor invoked when the TELNET struct is removed from the easy handle: frees the environment-variable slist, releases the output dynbuf, and frees the struct itself.

<a id="u-4fad1ef8f717"></a>
### `telrcv`

`static CURLcode telrcv(struct Curl_easy *data, struct TELNET *tn, const unsigned char…` · [lib/telnet.c:L1057-L1209][f1]

Byte-at-a-time telnet receive FSM converting raw socket data into body output and negotiation events.

Data bytes are accumulated between startwrite marks and flushed to the application with Curl_client_write (CLIENTWRITE_BODY); a macro-based startskipping/flush mechanism emits pending bytes whenever interpretation switches away from data. In CURL_TS_DATA an IAC switches to command mode (flushing pending data), CR defers one byte; CURL_TS_CR drops a NUL after CR, otherwise emits the byte. CURL_TS_IAC dispatches WILL/WONT/DO/DONT/SB/IAC (doubled IAC emits a literal 0xFF) and ignores DM/NOP/GA and unknown commands (logging them). WILL/WONT/DO/DONT set please_negotiate and delegate to rec_will/rec_wont/rec_do/rec_dont. Suboption bytes accumulate via CURL_SB_ACCUM until IAC SE terminates (error paths: a non-doubled non-SE byte after IAC logs 'suboption error' and returns CURLE_RECV_ERROR immediately, dropping buffered output); on proper termination suboption() handles the payload, with errors propagated. The final bufferflush at end of input emits any trailing data. Any Curl_client_write or suboption error returns early, discarding the rest of the input chunk.

calls: [rec_will](r9-telnet-state-and-options.md#u-d56441fa4bf4), [suboption](r9-telnet-transfer-fsm.md#u-d126e245a4fe)

**Uncertainties.**

- Partial negotiation commands split across recv chunks would lose state coherence only if the FSM were reset between calls; per-call entry always starts at tn->telrcv_state, which persists, but output flushing across chunk boundaries depends on startwrite reset per call.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/telnet.c
