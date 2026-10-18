# POP3 state machine and transfer

**Capability.** Drives the POP3 connection through greeting, CAPA, STLS upgrade, URL/command parsing, DO phase, body streaming (dot-unstuffing, CRLF.CRLF detection), and blocking disconnect, using pop3_state as the sole state mutator.

Read here for connect/doing/done/disconnect entry points and per-state response handlers. URL path and custom-request parsing feed the DO phase and belong here.

**Depends on.**

- [MD5 digest service](r12-md5-digest.md) · model-inferred · 0 edge(s)

Parent: [POP3 client](r12-pop3-client.md)

## Units (31)

<a id="u-c47efccf635b"></a>
### `pop3.c-lifecycle`

`static void pop3_easy_dtor(const void *key, size_t klen, void *entry)` · [lib/pop3.c:L1653-L1663][f1]

Allocation and destruction of POP3 handle state.

pop3_easy_dtor and pop3_conn_dtor are meta-registered destructors: the easy one frees the message id and custom request then the struct POP3; the connection one disconnects the pingpong layer, frees the APOP timestamp, then the struct pop3_conn. pop3_setup_connection allocates both structs and registers them under the meta keys with those destructors; any allocation or registration failure returns CURLE_OUT_OF_MEMORY, and failure at the second step still leaves the first struct to be cleaned by its registered destructor. These destructors are what makes missing-meta checks elsewhere the only cleanup guard needed.

<a id="u-dc37f9cebb7e"></a>
### `pop3.c-protocol`

`group` · [lib/pop3.c:L1399-L1424][f1]

Static protocol configuration tables.

saslpop3 wires the SASL layer to POP3: service name 'pop', callbacks pop3_perform_auth/pop3_continue_auth/pop3_cancel_auth/pop3_get_message, continuation code '*', success code '+', default mechanism set, base64 flag, and max line length 255-8. Curl_protocol_pop3 is the handler table for the pop3 scheme, binding setup_connection, do, done, connect_it, connecting, doing, proto/doing pollsets (both pop3_pollset), disconnect, and write_resp (pop3_write) to this file's functions; do_more and several optional hooks are ZERO_NULL.

<a id="u-9f6ca90b1b25"></a>
### `pop3.c-types`

`struct POP3` · [lib/pop3.c:L96-L100][f1]

Defines the POP3 protocol's data structures and command table.

struct POP3 holds per-easy state: the pingpong transfer mode, target message id, and custom request string. The pop3state enum lists machine states from POP3_STOP through POP3_QUIT (POP3_LAST unused). struct pop3_conn carries per-connection state: the pingpong layer, current state (changed only via pop3_state), the partial end-of-body match counter eob, body-strip counter strip, SASL storage, the server's APOP timestamp, accepted authentication type flags, preferred type, and BIT flags ssldone/tls_supported. struct pop3_cmd describes each command name and whether its response is multi-line unconditionally or only when arguments are present; pop3cmds enumerates the known commands so pop3_is_multiline can look them up. The module-level type flags POP3_TYPE_CLEARTEXT/APOP/SASL and their NONE/ANY combinations parameterize the preference matching used by the parsers and the authentication decision.

<a id="u-e76a8490b528"></a>
### `pop3_statemachine`

`static CURLcode pop3_statemachine(struct Curl_easy *data, struct connectdata *conn)` · [lib/pop3.c:L1272-L1359][f1]

Runs one pass of the POP3 response state machine.

While in POP3_UPGRADETLS it delegates to pop3_perform_upgrade_tls and returns unless the state moved on. Pending send data is flushed first. It then loops: Curl_pp_readresp classifies each complete line via pop3_endofresp into pop3code, dispatching to the handler for the current state (SERVERGREET, CAPA, STARTTLS, AUTH, APOP, USER, PASS, COMMAND, QUIT->STOP); POP3_STARTTLS success jumps back to the upgrade path before further I/O; unknown states are treated as internal errors and stop the machine. The loop continues while no error, the state is not POP3_STOP, and more buffered data remains. Missing meta returns CURLE_FAILED_INIT.

calls: [pop3_perform_upgrade_tls](r12-pop3-state-machine.md#u-db9548f2bfb1), [function::Curl_pp_readresp::2068][f2]

<a id="u-59bad43f9c4f"></a>
### `pop3_state`

`static void pop3_state(struct Curl_easy *data, pop3state newstate)` · [lib/pop3.c:L385-L414][f1]

Sole mutator of the connection's pop3state, storing newstate into pop3c->state.

In verbose debug builds it logs old-to-new state names from a static table when the state actually changes. If connection meta is missing it silently does nothing, so the transition is lost without an error to callers.

<a id="u-978a7ccd0f21"></a>
### `pop3_endofresp`

`static bool pop3_endofresp(struct Curl_easy *data, struct connectdata *conn, const ch…` · [lib/pop3.c:L292-L338][f1]

Classifies one received server line as a completed POP3 response, storing a code via *resp and returning TRUE when the line ends a response.

Test order: a line starting with '-ERR' (len>=4) yields '-'; while in POP3_CAPA state every line is final, the lone-dot terminator yielding '+' and all other CAPA lines '*' (untagged continuation); otherwise '+OK' (len>=3) yields '+'; a line whose first byte is '+' yields '*'; anything else returns FALSE so the caller keeps waiting for more data. Missing connection meta returns TRUE immediately, reporting every line as final.

**Notes.**

- condition: The '-ERR' test runs before the CAPA branch, so an '-ERR' line during CAPA yields '-' rather than '*'

<a id="u-15107b2d9e9b"></a>
### `pop3_get_message`

`static CURLcode pop3_get_message(struct Curl_easy *data, struct bufref *out)` · [lib/pop3.c:L346-L377][f1]

Extracts the SASL challenge/message from the pingpong receive buffer into a bufref.

When nfinal>2 it skips the two leading status bytes, trims leading blanks then trailing blanks/newlines, NUL-terminates, and sets the bufref to point into the receive buffer with a NULL releaser; otherwise it sets a zero-length static empty string. Missing connection meta returns CURLE_FAILED_INIT.

**Uncertainties.**

- The bufref has no destructor, so the message's validity window depends on recvbuf reuse outside this file

<a id="u-55dda340f569"></a>
### `pop3_is_multiline`

`static bool pop3_is_multiline(const char *cmdline)` · [lib/pop3.c:L267-L281][f1]

Decides whether a command's response is a multi-line body terminated by a lone dot.

Scans pop3cmds for the first entry whose name matches the start of cmdline (case-insensitive, nlen bytes): if the byte after the name is NUL it returns that entry's multiline flag; if it is a space it returns multiline_with_args. Any unknown command returns TRUE for backward compatibility with older curl that only handled multi-line responses.

**Uncertainties.**

- Matching stops at the first name-prefix hit, so a command name that is a prefix of another could shadow it; table order decides

<a id="u-9c1cf19c1bac"></a>
### `pop3_write`

`static CURLcode pop3_write(struct Curl_easy *data, const char *str, size_t nread, boo…` · [lib/pop3.c:L1075-L1205][f1]

Streams body data, detecting the 5-byte end-of-body marker CRLF.CRLF possibly split across chunks, and un-stuffs server dot-stuffing.

The persistent pop3c->eob counter tracks partial marker matches byte by byte: 0x0d advances at 0 or restarts at 1 (advances at 3), 0x0a advances at 1 or 4 else resets, 0x2e advances at 2 or, at 3, flags strip_dot and resets (an escaped dot). When a partial match fails, the previously matched bytes are flushed: the CRLF prefix minus the inserted dot when strip_dot, otherwise the full matched prefix; matching bytes are consumed so the tail is written from the new last offset. A full match writes the leading CRLF (part of the message per RFC-1939), clears the receive request and eob, and ends the transfer. While a partial match is pending nothing is output; otherwise the remaining tail is written. Missing meta returns CURLE_FAILED_INIT.

**Notes.**

- side_effect: pop3c->eob persists across calls, allowing the marker to span multiple data chunks
- side_effect: On a full match the function clears the receiver via CURL_REQ_CLEAR_RECV and resets pop3c->eob

**Uncertainties.**

- is_eos is accepted but ignored, so end-of-stream handling is delegated to the caller

<a id="u-b1240c8cf6f6"></a>
### `pop3_multi_statemach`

`static CURLcode pop3_multi_statemach(struct Curl_easy *data, bool *done)` · [lib/pop3.c:L1362-L1374][f1]

Non-blocking entry point for the multi interface: runs the pingpong state machine once in non-blocking mode and reports done when the POP3 state has reached POP3_STOP.

Missing meta returns CURLE_FAILED_INIT with done left at the caller's value.

calls: [Curl_pp_statemach](r12-pingpong-transport.md#u-673b0f00a073)

<a id="u-480c8f07c6db"></a>
### `pop3_block_statemach`

`static CURLcode pop3_block_statemach(struct Curl_easy *data, struct connectdata *conn…` · [lib/pop3.c:L1376-L1390][f1]

Blocking state-machine loop used during disconnect: repeatedly runs the pingpong state machine in blocking mode, passing the disconnecting flag through, until the state reaches POP3_STOP or an error occurs.

Missing meta returns CURLE_FAILED_INIT.

calls: [Curl_pp_statemach](r12-pingpong-transport.md#u-673b0f00a073)

<a id="u-5c5a29b04ec7"></a>
### `pop3_connect`

`static CURLcode pop3_connect(struct Curl_easy *data, bool *done)` · [lib/pop3.c:L1425-L1456][f1]

Protocol connect phase.

Registers pop3_statemachine and pop3_endofresp into the pingpong layer, sets the initial preftype to POP3_TYPE_ANY, initializes SASL from saslpop3, initializes the pingpong layer with a progress timestamp, parses URL login options (failing fast on error), then moves to POP3_SERVERGREET and runs one non-blocking statemachine pass; done reports whether the greeting already completed. Missing meta returns CURLE_FAILED_INIT with done FALSE.

calls: [Curl_sasl_init](r15-sasl-auth.md#u-8325e3b05815), [pop3_multi_statemach](r12-pop3-state-machine.md#u-b1240c8cf6f6)

<a id="u-c96d588222a1"></a>
### `pop3_doing`

`static CURLcode pop3_doing(struct Curl_easy *data, bool *dophase_done)` · [lib/pop3.c:L1638-L1651][f1]

Called from the multi interface during DOing: runs one non-blocking statemachine pass; on failure logs it, and when the DO phase completes invokes the no-op pop3_dophase_done.

calls: [pop3_multi_statemach](r12-pop3-state-machine.md#u-b1240c8cf6f6)

<a id="u-c8e83f55c416"></a>
### `pop3_done`

`static CURLcode pop3_done(struct Curl_easy *data, CURLcode status, bool premature)` · [lib/pop3.c:L1467-L1492][f1]

Per-request cleanup after the DO phase.

A non-OK status marks the connection for close and propagates that status as the result. It frees the message id and custom request and resets the transfer mode to PPTRANSFER_BODY for the next request. Missing easy meta is tolerated, returning OK.

<a id="u-dd8e879ae27c"></a>
### `pop3_disconnect`

`static CURLcode pop3_disconnect(struct Curl_easy *data, struct connectdata *conn, boo…` · [lib/pop3.c:L1610-L1635][f1]

Blocking disconnect with cleanup.

QUIT is sent only when the connection is not flagged dead, the protocol connect started, no pingpong data awaits flush, and the quit send succeeds; the subsequent blocking state machine run ignores errors since QUIT replies are best-effort. It then always disconnects the pingpong layer and frees the APOP timestamp, returning CURLE_OK. Missing meta returns CURLE_FAILED_INIT.

calls: [pop3_perform_quit](r12-pop3-state-machine.md#u-25d9eb1beb80)

<a id="u-b00fb4965108"></a>
### `pop3_do`

`static CURLcode pop3_do(struct Curl_easy *data, bool *done)` · [lib/pop3.c:L1583-L1601][f1]

Registered do_it function: parses the URL path into the message id, then the custom request (each failure aborts), then runs the regular transfer.

done defaults to FALSE and only becomes true via the transfer path.

calls: [pop3_parse_url_path](r12-pop3-state-machine.md#u-815981d68afd), [pop3_parse_custom_request](r12-pop3-state-machine.md#u-f82cc36fe4e6), [pop3_regular_transfer](r12-pop3-state-machine.md#u-a931f64ae745)

<a id="u-d1bd940673b1"></a>
### `pop3_perform`

`static CURLcode pop3_perform(struct Curl_easy *data, bool *connected, bool *dophase_d…` · [lib/pop3.c:L1501-L1532][f1]

DO-phase driver: sends the transfer command (which may set req.no_body), then converts a no-body request into PPTRANSFER_INFO so no transfer occurs, and starts the non-blocking state machine, reporting connection state from Curl_conn_is_connected.

Missing easy meta returns CURLE_FAILED_INIT; command-send failure aborts before the state machine runs.

calls: [pop3_perform_command](r12-pop3-state-machine.md#u-d135131030fa), [lib-cfilters-c-chain-state-queries](r8-cfilters-events-state.md#u-b752791790cf)

<a id="u-a931f64ae745"></a>
### `pop3_regular_transfer`

`static CURLcode pop3_regular_transfer(struct Curl_easy *data, bool *dophase_done)` · [lib/pop3.c:L1552-L1572][f1]

Prepares and runs a regular transfer: unknown size (-1), progress reset, then pop3_perform; on success with the DO phase complete it calls pop3_dophase_done, which is a no-op returning OK.

<a id="u-2523beefa7c4"></a>
### `pop3_setup_connection`

`static CURLcode pop3_setup_connection(struct Curl_easy *data, struct connectdata *conn)` · [lib/pop3.c:L1676-L1691][f1]

Allocates and registers the per-easy and per-connection POP3 state structs with their destructors; any allocation or registration failure returns CURLE_OUT_OF_MEMORY.

uses: [pop3.c-lifecycle](r12-pop3-state-machine.md#u-c47efccf635b)

<a id="u-6947810d0be7"></a>
### `pop3_pollset`

`static CURLcode pop3_pollset(struct Curl_easy *data, struct easy_pollset *ps)` · [lib/pop3.c:L1393-L1399][f1]

Adds the POP3 connection's poll descriptors (protocol-connect and doing phases) via Curl_pp_pollset.

With no connection meta it is a no-op returning CURLE_OK.

<a id="u-d135131030fa"></a>
### `pop3_perform_command`

`static CURLcode pop3_perform_command(struct Curl_easy *data)` · [lib/pop3.c:L727-L764][f1]

Sends the transfer command for the DO phase.

With no message id or list_only set it uses LIST (marking the transfer PPTRANSFER_INFO when a specific message id accompanies LIST); otherwise RETR. A non-empty custom request overrides both. It sends the command with or without the message id argument, and on success moves to POP3_COMMAND and sets data->req.no_body from pop3_is_multiline(command). Missing easy or connection meta returns CURLE_FAILED_INIT.

calls: [pop3_is_multiline](r12-pop3-state-machine.md#u-55dda340f569)

<a id="u-375bcce4a4e0"></a>
### `pop3_perform_capa`

`static CURLcode pop3_perform_capa(struct Curl_easy *data, struct connectdata *conn)` · [lib/pop3.c:L423-L443][f1]

Sends the CAPA command to discover server capabilities.

Clears sasl.authmechs and sasl.authused to SASL_AUTH_NONE and tls_supported to FALSE so stale capability data is never reused, sends 'CAPA', and on send success transitions to POP3_CAPA. Missing meta returns CURLE_FAILED_INIT; a failed send propagates with the state unchanged.

calls: [Curl_pp_vsendf](r12-pingpong-transport.md#u-38c5e1d73b67)

<a id="u-25d9eb1beb80"></a>
### `pop3_perform_quit`

`static CURLcode pop3_perform_quit(struct Curl_easy *data, struct connectdata *conn)` · [lib/pop3.c:L772-L787][f1]

Sends QUIT prior to socket close and, on send success, transitions to POP3_QUIT.

Missing meta returns CURLE_FAILED_INIT.

<a id="u-ff82d7899212"></a>
### `pop3_perform_starttls`

`static CURLcode pop3_perform_starttls(struct Curl_easy *data, struct connectdata *conn)` · [lib/pop3.c:L451-L466][f1]

Sends the STLS command to begin a plaintext-to-TLS upgrade and, on send success, transitions to POP3_STARTTLS.

Missing meta returns CURLE_FAILED_INIT; send failure propagates with the state unchanged.

<a id="u-db9548f2bfb1"></a>
### `pop3_perform_upgrade_tls`

`static CURLcode pop3_perform_upgrade_tls(struct Curl_easy *data, struct connectdata *…` · [lib/pop3.c:L474-L511][f1]

Drives the TLS upgrade of an established POP3 connection; without SSL in the build it returns CURLE_NOT_BUILT_IN.

If the first socket is not yet SSL it adds an SSL connection filter and switches conn->scheme to Curl_scheme_pop3s; filter-add failure exits immediately. It then runs Curl_conn_connect non-blocking; when the handshake completes (ssldone true) it records ssldone and immediately calls pop3_perform_capa, which moves the state out of POP3_UPGRADETLS. Missing meta returns CURLE_FAILED_INIT.

calls: [pop3_perform_capa](r12-pop3-state-machine.md#u-375bcce4a4e0)

**Uncertainties.**

- DEBUGASSERT(!pop3c->ssldone) implies one-shot use, but behavior on a second entry with ssldone already set is not pinned

<a id="u-96d73f7bf9d6"></a>
### `pop3_state_servergreet_resp`

`static CURLcode pop3_state_servergreet_resp(struct Curl_easy *data, int pop3code, pop…` · [lib/pop3.c:L790-L843][f1]

Handles the initial server greeting.

A non-'+' code fails with CURLE_WEIRD_SERVER_REPLY. On success with a line longer than the status word it scans for an APOP timestamp: the span from '<' to the next '>', accepted only when it contains '@' (RFC-822 id syntax); a conformant timestamp is duplicated into pop3c->apoptimestamp and POP3_TYPE_APOP is added to authtypes, with allocation failure returning CURLE_OUT_OF_MEMORY. When no APOP capability is found the code still proceeds. It then always sends CAPA to continue the connect phase.

calls: [pop3_perform_capa](r12-pop3-state-machine.md#u-375bcce4a4e0)

**Uncertainties.**

- When len <= 3 on a '+' greeting neither the timestamp scan nor CAPA runs and the state stays in POP3_SERVERGREET; recovery from that stall is outside this file

<a id="u-40d785e4ecbd"></a>
### `pop3_state_capa_resp`

`static CURLcode pop3_state_capa_resp(struct Curl_easy *data, int pop3code, pop3state …` · [lib/pop3.c:L846-L929][f1]

Handles each CAPA response line and the capability summary.

Untagged '*' lines set tls_supported on STLS, add POP3_TYPE_CLEARTEXT on USER, and on 'SASL ' tokenize the remainder, OR-ing each recognized mechanism (exact word match via Curl_sasl_decode_mech) into sasl.authmechs. On the final line: a non-'+' code (CAPA rejected) implies clear-text support; then if TLS is not requested or already active it starts authentication, else on '+' with tls_supported it sends STLS, else if use_ssl is at most CURLUSESSL_TRY it still falls back to authentication, and otherwise fails with CURLE_USE_SSL_FAILED after 'STLS not supported.'

calls: [pop3_perform_authentication](r12-pop3-authentication.md#u-ea6cae735793), [pop3_perform_starttls](r12-pop3-state-machine.md#u-ff82d7899212), [Curl_sasl_decode_mech](r15-sasl-auth.md#u-dcd56164044a)

<a id="u-6c0911d856fc"></a>
### `pop3_state_starttls_resp`

> **ID corrected by CBE.** CBE changed the unit ID from ` lib/pop3.c::function::pop3_state_starttls_resp::960 ` to the inventory ID ` lib/pop3.c::function::pop3_state_starttls_resp::26244 `. The model wrote this body under the wrong ID; it may be inaccurate.

`static CURLcode pop3_state_starttls_resp(struct Curl_easy *data, struct connectdata *…` · [lib/pop3.c:L932-L960][f1]

Handles the STLS response.

Any pipelined data after the response is rejected outright with CURLE_WEIRD_SERVER_REPLY. A denied STLS ('-' code) fails with CURLE_USE_SSL_FAILED unless use_ssl is CURLUSESSL_TRY, in which case it falls back to pop3_perform_authentication; a '+' code moves to POP3_UPGRADETLS for the handshake. Missing meta returns CURLE_FAILED_INIT.

calls: [pop3_perform_authentication](r12-pop3-authentication.md#u-ea6cae735793)

<a id="u-14617b97249d"></a>
### `pop3_state_command_resp`

`static CURLcode pop3_state_command_resp(struct Curl_easy *data, int pop3code, pop3sta…` · [lib/pop3.c:L1208-L1270][f1]

Handles the reply to the transfer command and hands the connection over to body reception.

A non-'+' code stops the machine and returns CURLE_WEIRD_SERVER_REPLY. On success it seeds eob=2 and strip=2 so the OK line's CRLF counts toward the end-of-body marker but is not delivered. When a body is expected it sets up socket reception and, if the pingpong buffer holds overflow data (actual body content, possibly with trailing junk), trims the buffer to the overflow, writes it via pop3_write unless no_body was requested, then resets the buffer and overflow counter; without a body it just clears overflow. Finally it moves to POP3_STOP, ending the DO phase.

calls: [pop3_write](r12-pop3-state-machine.md#u-9c1cf19c1bac)

**Uncertainties.**

- The comment notes there may be additional 'headers' after the body, but no code here separates them

<a id="u-815981d68afd"></a>
### `pop3_parse_url_path`

`static CURLcode pop3_parse_url_path(struct Curl_easy *data)` · [lib/pop3.c:L231-L241][f1]

URL-decodes the request path (skipping its first character) into the per-easy message id pop3->id via Curl_urldecode with control-character rejection.

Missing easy-handle meta returns CURLE_FAILED_INIT; otherwise the decode result propagates.

calls: [Curl_urldecode](r7-string-escape-utils.md#u-0db7582a0fb5)

<a id="u-f82cc36fe4e6"></a>
### `pop3_parse_custom_request`

`static CURLcode pop3_parse_custom_request(struct Curl_easy *data)` · [lib/pop3.c:L249-L262][f1]

URL-decodes the user's custom request string into pop3->custom with control-character rejection.

Missing meta returns CURLE_FAILED_INIT; if no custom request is set it returns CURLE_OK without allocating.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/pop3.c
[f2]: ../../../../../../eval/curl-2c04412/lib/pingpong.c
