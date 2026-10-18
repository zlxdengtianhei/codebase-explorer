# FTP Transfer Lifecycle

**Capability.** Owns the phase entry points the multi interface calls (connect, do, doing, do_more, done, disconnect, quit) and the composition of DONE-phase sub-steps, plus the blocking/non-blocking statemach drivers and connection setup/reuse.

Use this to trace a transfer's phases. ftp_connect/ftp_do/ftp_done delegate into the state machines and helpers; ftp_setup_connection and Curl_ftp_conns_match handle per-connection state and reuse.

**Depends on.**

- [FTP Login and Response States](r1-ftp-login-states.md) · graph-confirmed · 6 edge(s)
- [FTP Path and Data-Channel Helpers](r1-ftp-path-data-helpers.md) · graph-confirmed · 5 edge(s)
- [FTP Transfer Command States](r1-ftp-transfer-states.md) · graph-confirmed · 7 edge(s)

**Depended on by.**

- [FTP Wildcard Transfer](r1-ftp-wildcard-transfer.md) · model-inferred · 0 edge(s)

Parent: [FTP Protocol Implementation](r1-ftp-protocol.md)

## Units (24)

<a id="u-de1465f07e9f"></a>
### `Curl_ftp_conns_match`

`bool Curl_ftp_conns_match(struct connectdata *needle, struct connectdata *conn)` · [lib/ftp.c:L4473-L4493][f1]

Connection-reuse compatibility check for FTP.

Either side lacking ftp_conn, differing account or alternative-to-user strings (compared time-safely via Curl_timestrcmp), or a differing ccc value is incompatible. SSL use: a needle of CURLUSESSL_TRY matches any connection whose SSL use is not NONE; all other needle values require exact equality.

<a id="u-6675804c17f0"></a>
### `ftp_block_statemach`

`static CURLcode ftp_block_statemach(struct Curl_easy *data, struct ftp_conn *ftpc)` · [lib/ftp.c:L3510-L3525][f1]

Runs Curl_pp_statemach in blocking mode repeatedly until the state reaches FTP_STOP or an error occurs, logging a note while shutting down and waiting for the server's final response.

Used for QUIT handling.

<a id="u-1487ea085c74"></a>
### `ftp_connect`

`static CURLcode ftp_connect(struct Curl_easy *data, bool *done) /* see description ab…` · [lib/ftp.c:L3535-L3565][f1]

Performs the FTP connection phase.

Missing ftp_conn metadata is CURLE_FAILED_INIT. The pingpong machinery is wired to ftp_pp_statemach and ftp_endofresp via PINGPONG_SETUP. An already-TLS control connection is connected blocking first (failure propagates). Pingpong state is initialized with the current progress timestamp, the state enters FTP_WAIT220, and the non-blocking state machine runs to determine *done.

calls: [ftp_statemach](r1-ftp-lifecycle.md#u-1d69fff49155)

<a id="u-2d90a165f9f0"></a>
### `ftp_disconnect`

`static CURLcode ftp_disconnect(struct Curl_easy *data, struct connectdata *conn, bool…` · [lib/ftp.c:L4324-L4345][f1]

Protocol disconnect (blocking).

Missing metadata is CURLE_FAILED_INIT. It marks the session as shutting down and invalidates ctl_valid when the connection was declared dead or has unsent data, so the quit inside ftp_quit (whose errors are deliberately ignored) will be skipped in those cases.

<a id="u-655b1f3f65dc"></a>
### `ftp_do`

`static CURLcode ftp_do(struct Curl_easy *data, bool *done)` · [lib/ftp.c:L4232-L4280][f1]

Registered do_it entry.

Missing metadata is CURLE_FAILED_INIT; wait_data_conn resets to FALSE. Under CURL_PREFER_LF_LINEENDS a line-conversion content writer (ftp_cw_lc) is created and inserted into the write chain, freed and failed out on insertion error. With wildcard matching enabled the wildcard state machine advances; SKIP/DONE states skip the transfer (returning OK) and errors propagate. Otherwise the URL path is parsed. Either way ftp_regular_transfer runs and its result with *done is returned.

calls: [ftp_regular_transfer](r1-ftp-lifecycle.md#u-3751fd573f72)

<a id="u-7e9b1544c8ef"></a>
### `ftp_do_more`

`static CURLcode ftp_do_more(struct Curl_easy *data, domore *more)` · [lib/ftp.c:L2215-L2375][f1]

DO_MORE driver, called when the data connection progresses.

Missing ftp_conn or FTP metadata is CURLE_FAILED_INIT; *more defaults to DOMORE_INCOMPLETE. If a SECONDARY filter exists it advances the data connection non-blockingly: OOM returns immediately; a failed/unconnected attempt that is not a passive listen and not IP-connected is treated as a failed EPSV (count1 0) and falls back via ftp_epsv_disable with DOMORE_GOBACK. If the FTP state is running, the state machine steps; completion sets DOMORE_DONE, but while wait_data_conn holds, more stays INCOMPLETE. For transfers at or below INFO: with wait_data_conn it tries to accept the server's data connection — on success wait_data_conn clears, ftp_initiate_transfer runs and more is DONE; otherwise the control connection is sanity-checked for early traffic. Uploads send TYPE (which may skip straight to STOR) then step the machine, DONE only when complete and no data wait remains. Downloads initialize downloadsize to -1, apply the range, mark dont_check when maxdownload >= 0, choose LIST mode (ASCII TYPE) for directory-ish paths without prequote, RETR_LIST_TYPE when prequote exists without a file, else RETR_TYPE with the preferred mode, then step the machine. With nothing to transfer the xfer becomes nop and more is DONE unless still waiting on the data connection.

**Uncertainties.**

- Exact interplay between Curl_range result and maxdownload for dont_check (assignment happens when result is OK and maxdownload >= 0) is stated from code but its downstream meaning lives elsewhere.

<a id="u-8a0aab8eaef3"></a>
### `ftp_doing`

`static CURLcode ftp_doing(struct Curl_easy *data, bool *dophase_done)` · [lib/ftp.c:L4348-L4367][f1]

Called by the multi loop while the DO phase runs asynchronously.

Missing metadata is CURLE_FAILED_INIT. It steps ftp_statemach; on error the phase failure is traced, and on completion ftp_dophase_done runs with connected=FALSE so DO_MORE remains in charge of the data connection.

<a id="u-02d201c342b7"></a>
### `ftp_domore_pollset`

`static CURLcode ftp_domore_pollset(struct Curl_easy *data, struct easy_pollset *ps)` · [lib/ftp.c:L777-L802][f1]

Pollset for the DO_MORE phase.

Missing ftp_conn metadata is a silent no-op. If the state machine is stopped (FTP_STOP), the code is waiting for a server-side connect, so the control socket is added for input; an unconnected SECONDARY socket is expected to add itself via its own filter's adjust_pollset (asserted). Otherwise sockets come from the pingpong machinery.

calls: [Curl_pp_pollset](r12-pingpong-transport.md#u-61def25ad0af)

<a id="u-821b9565fd7a"></a>
### `ftp_done`

`static CURLcode ftp_done(struct Curl_easy *data, CURLcode status, bool premature)` · [lib/ftp.c:L3841-L3868][f1]

DONE-phase entry point composing the finish sequence.

Missing metadata returns OK immediately. It classifies the status (ftp_done_status), handles wildcard end state, resolves the remembered path, closes the secondary socket (possibly sending ABOR), reads the final control reply, and verifies transfer completeness — each step feeding its result into the next. transfer is reset to PPTRANSFER_BODY and dont_check cleared for the next use. When neither the incoming status nor the computed result failed and the transfer was not premature, post-quote commands are sent blocking via ftp_sendquote; that result is returned.

calls: [ftp_sendquote](r1-ftp-login-states.md#u-1ad9ab7d531b)

<a id="u-efe6eac75c04"></a>
### `ftp_done_check_partial`

`static CURLcode ftp_done_check_partial(struct Curl_easy *data, struct ftp_conn *ftpc,…` · [lib/ftp.c:L3791-L3830][f1]

Detects short or empty transfers when no earlier error or premature end occurred.

Uploads with a known infilesize fail with CURLE_PARTIAL_FILE when the written byte count is short (in plain mode any mismatch counts; with CRLF/ASCII conversion only a shortfall counts). Downloads fail with CURLE_PARTIAL_FILE when a known size was neither fully received nor capped by maxdownload, or with CURLE_FTP_COULDNT_RETR_FILE when checking is on, nothing was received, and a size was expected.

<a id="u-730b352ffde3"></a>
### `ftp_done_control_reply`

`static CURLcode ftp_done_control_reply(struct Curl_easy *data, struct ftp_conn *ftpc,…` · [lib/ftp.c:L3734-L3789][f1]

Reads the server's final transfer status when a body transfer completed normally over a valid control connection with a pending reply.

The pingpong response timeout is re-anchored and getftpresponse blocks for the code. A timeout with zero bytes read declares the control connection dead (ctl_valid invalid, connection close). For partial downloads (dont_check with data received) the connection is closed since ABOR's effect is unknowable. Otherwise, when checking is enabled, 226/250 are accepted, 552 maps to CURLE_REMOTE_DISK_FULL, and any other code maps to CURLE_PARTIAL_FILE with a message.

<a id="u-76f4f34d020b"></a>
### `ftp_done_path`

`static void ftp_done_path(struct Curl_easy *data, struct ftp_conn *ftpc, CURLcode res…` · [lib/ftp.c:L3674-L3710][f1]

Decides which working directory to remember for connection reuse.

On error, ctl_valid is cleared, the connection is marked for closure and prevpath is dropped. On success with a raw path: NOCWD with an absolute path keeps the existing prevpath untouched (no CWDs happened); otherwise prevpath becomes the raw path truncated before the filename (multi-CWD methods) or to length 0 (NOCWD relative, meaning FTP home), or NULL when cwdfail is set. The remembered directory is logged.

<a id="u-0e418979ac46"></a>
### `ftp_done_secondary_socket`

`static CURLcode ftp_done_secondary_socket(struct Curl_easy *data, struct ftp_conn *ft…` · [lib/ftp.c:L3712-L3732][f1]

Cleanup of the data connection at DONE.

If a SECONDARY filter is set up and the transfer was a partial download with dont_check, 'ABOR' is sent; a failed ABOR marks ctl_valid invalid and closes the connection. The secondary socket is then closed unconditionally in that case, and the incoming result is propagated or replaced.

<a id="u-ead50c8274c2"></a>
### `ftp_done_status`

`static CURLcode ftp_done_status(struct Curl_easy *data, struct ftp_conn *ftpc, CURLco…` · [lib/ftp.c:L3622-L3658][f1]

Classifies the transfer's final status for control-connection reuse.

A list of recoverable codes (bad resume, weird PASV, PORT failure, accept failure/timeout, TYPE failure, retrieval failure, partial file, upload failure, access denied, size exceeded, file not found, write error) plus CURLE_OK keep the connection alive when the transfer was not premature; premature transfers fall through to the failure path. Any other status — and any premature one — marks ctl_valid FALSE, sets cwdfail so the path is not remembered, closes the connection, and returns the status unchanged.

<a id="u-56739bf97409"></a>
### `ftp_done_wildcard`

`static void ftp_done_wildcard(struct Curl_easy *data, struct ftp_conn *ftpc)` · [lib/ftp.c:L3660-L3672][f1]

Wildcard-transfer end handling: when wildcard matching was active and a chunk_end callback with a current file exists, it invokes the callback (under the API guard), frees the directory state, and in all wildcard cases resets known_filesize to -1.

<a id="u-e077a8fa2246"></a>
### `ftp_dophase_done`

`static CURLcode ftp_dophase_done(struct Curl_easy *data, struct ftp_conn *ftpc, struc…` · [lib/ftp.c:L2378-L2403][f1]

Finalizes the DO phase.

If the data connection was established in this phase, ftp_do_more runs; any error closes the secondary socket and propagates. Non-body transfers get a nop xfer; a body transfer without an established connection sets do_more so DO_MORE runs later. ctl_valid is set TRUE as the connection is presumed usable.

<a id="u-4a032625953c"></a>
### `ftp_multi_statemach`

`static CURLcode ftp_multi_statemach(struct Curl_easy *data, bool *done)` · [lib/ftp.c:L3503-L3508][f1]

Public connecting hook: resolves ftp_conn from metadata and runs ftp_statemach; missing metadata yields CURLE_FAILED_INIT.

<a id="u-7604e1d1a4a9"></a>
### `ftp_perform`

`static CURLcode ftp_perform( struct Curl_easy *data, struct ftp_conn *ftpc, struct FT…` · [lib/ftp.c:L3908-L3948][f1]

Core DO phase.

no-body requests mark the transfer info-only. It starts the machine at the QUOTE state via ftp_state_quote, then steps ftp_statemach to set *dophase_done. *connected reports whether the SECONDARY socket is already established, logged accordingly; DO-phase completion is traced. Errors from the initial quote command propagate.

<a id="u-d4d9565a4251"></a>
### `ftp_pollset`

`static CURLcode ftp_pollset(struct Curl_easy *data, struct easy_pollset *ps)` · [lib/ftp.c:L769-L774][f1]

Protocol/doing pollset for the FTP phases: adds sockets via Curl_pp_pollset when the ftp_conn metadata exists, otherwise no-op with CURLE_OK.

<a id="u-01d5dcc7c90b"></a>
### `ftp_quit`

`static CURLcode ftp_quit(struct Curl_easy *data, struct ftp_conn *ftpc)` · [lib/ftp.c:L4292-L4315][f1]

Sends QUIT when the control connection is still valid, then blocks in ftp_block_statemach for the server's reply.

A send failure logs, invalidates ctl_valid, marks the connection for closure, stops the state machine and returns the error.

<a id="u-3751fd573f72"></a>
### `ftp_regular_transfer`

`static CURLcode ftp_regular_transfer(struct Curl_easy *data, struct ftp_conn *ftpc, s…` · [lib/ftp.c:L4189-L4221][f1]

Runs a standard (non-wildcard) transfer: resets req.size to unknown and progress counters, sets ctl_valid TRUE, and runs ftp_perform.

If the DO phase completed, ftp_dophase_done finalizes; while still in progress it returns OK to let the multi loop drive ftp_doing. A perform error frees the parsed directory state before propagating.

<a id="u-fbf158e81de9"></a>
### `ftp_setup_connection`

`static CURLcode ftp_setup_connection(struct Curl_easy *data, struct connectdata *conn)` · [lib/ftp.c:L4422-L4471][f1]

Allocates and attaches the per-transfer FTP struct (with ftp_easy_dtor) and per-connection ftp_conn struct (with ftp_conn_dtor); allocation or metadata-registration failure returns CURLE_OUT_OF_MEMORY, with the connection metadata removed again when later duplication steps fail.

The FTP_ACCOUNT and FTP_ALTERNATIVE_TO_USER strings are cloned. The path is taken as the URL path minus the leading slash, then type_url_check strips any ';type=' suffix. Initial values: transfer BODY, downloadsize 0, known_filesize -1, use_ssl from settings, ccc from settings.

<a id="u-1d69fff49155"></a>
### `ftp_statemach`

`static CURLcode ftp_statemach(struct Curl_easy *data, struct ftp_conn *ftpc, bool *done)` · [lib/ftp.c:L2192-L2204][f1]

Non-blocking step of the FTP state machine: runs one Curl_pp_statemach pass with blocking disabled and reports done when the state has reached FTP_STOP, checked outside the socket-status logic so an already-stopped state is recognized.

<a id="u-62d8340d59b7"></a>
### `type_url_check`

`static void type_url_check(struct Curl_easy *data, struct FTP *ftp)` · [lib/ftp.c:L4393-L4420][f1]

Handles the FTP URL ';type=<code>' suffix: when present it is truncated from the path and the code selects behavior — 'A' sets prefer_ascii, 'D' sets list_only, and 'I' or any other value clears prefer_ascii (binary default).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/ftp.c
