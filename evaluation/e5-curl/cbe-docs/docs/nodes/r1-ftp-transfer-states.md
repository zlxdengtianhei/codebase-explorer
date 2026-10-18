# FTP Transfer Command States

**Capability.** Owns the per-transfer command sequence: TYPE/SIZE/REST/MDTM negotiation, RETR/STOR/LIST replies, upload setup, and the entire data-connection establishment (EPSV/PASV and active-mode PORT/EPRT with socket bind/listen/resolve helpers), ending in ftp_initiate_transfer.

Use this to follow how a transfer is negotiated and how the data channel is opened. Each ftp_state_* function handles one server reply and advances via ftp_state_low; the ftp_port_* helpers implement active mode.

**Depends on.**

- [FTP Login and Response States](r1-ftp-login-states.md) · graph-confirmed · 36 edge(s) · Transfer state handlers advance protocol state through ftp_state_low in the login/response-states node.
- [FTP Path and Data-Channel Helpers](r1-ftp-path-data-helpers.md) · graph-confirmed · 3 edge(s)
- [Trace and Debug Logging](r1-trace-logging.md) · graph-confirmed · 53 edge(s)

**Depended on by.**

- [FTP Transfer Lifecycle](r1-ftp-lifecycle.md) · graph-confirmed · 7 edge(s)

Parent: [FTP Protocol Implementation](r1-ftp-protocol.md)

## Units (35)

<a id="u-7986bbe05a8e"></a>
### `client_write_header`

`static CURLcode client_write_header(struct Curl_easy *data, char *buf, size_t blen)` · [lib/ftp.c:L2474-L2497][f1]

Writes synthesized HTTP-style headers (Content-Length, Last-Modified, Accept-ranges) to the client.

It temporarily forces data->set.include_header so the header data always reaches the body callback — FTP historically expects this — then restores the previous flag; a CONNECT-proxy path must not keep it forced globally, hence the save/restore. Curl_client_write errors propagate.

<a id="u-caf4d73833ff"></a>
### `ftp_213_date`

`UNITTEST bool ftp_213_date(const char *p, int *year, int *month, int *day, int *hour,…` · [lib/ftp.c:L2457-L2472][f1]

Parses a 14+ digit MDTM timestamp YYMMDDHHMMSS (two-digit fields via twodigit, which returns TRUE on error and reads decimal digits) into year/month/day/hour/minute/second, adding century*100 to the year.

Returns FALSE on short input, non-digit fields, or out-of-range month (>12), day (>31), hour (>23), minute (>59) or second (>60, leap second allowed); exported for unit tests.

<a id="u-99cfd0fb5dd4"></a>
### `ftp_check_ctrl_on_data_wait`

`static CURLcode ftp_check_ctrl_on_data_wait(struct Curl_easy *data, struct ftp_conn *…` · [lib/ftp.c:L459-L533][f1]

While waiting for the server to connect back on the data socket, inspects the control connection for unexpected traffic.

A cached response whose first byte is not a digit or exceeds '3' is drained via getftpresponse and yields CURLE_FTP_ACCEPT_FAILED. Otherwise pp->overflow or a zero-timeout readability check decides whether control data is pending; a select error also gives CURLE_FTP_ACCEPT_FAILED. When control data is present: overflow above three lines is scanned for a final line with status 226, which is left cached as a trigger to proceed with CURLE_OK; otherwise the response is read, and a code above 3xx returns CURLE_FTP_ACCEPT_FAILED while anything else returns CURLE_WEIRD_SERVER_REPLY.

**Notes.**

- side_effect: A drained cached negative response is consumed from pp->recvbuf.

calls: [getftpresponse](r1-ftp-login-states.md#u-5a00bf964808)

<a id="u-582e45034fb1"></a>
### `ftp_control_addr_dup`

`static CURLcode ftp_control_addr_dup(struct Curl_easy *data, char **newhostp)` · [lib/ftp.c:L2001-L2026][f1]

Produces the host string for a passive data connection: through a proxy tunnel it is the original hostname (the effective address is the proxy's), otherwise the control connection's remote IP from Curl_conn_get_ip_info.

Failure to obtain the peer name fails out with CURLE_FTP_CANT_GET_HOST and *newhostp NULL; strdup failure gives CURLE_OUT_OF_MEMORY.

<a id="u-f00a9c7ecf0c"></a>
### `ftp_epsv_disable`

`static CURLcode ftp_epsv_disable(struct Curl_easy *data, struct ftp_conn *ftpc, struc…` · [lib/ftp.c:L1974-L1999][f1]

Falls back from EPSV to PASV.

On IPv6 without a proxy tunnel this cannot be done, so it fails with CURLE_WEIRD_SERVER_REPLY. Otherwise it disables ftp_use_epsv, closes the secondary socket, clears the error buffer so a later message can overwrite it, sends 'PASV', increments count1, and stays in FTP_PASV. Send errors propagate with the state unchanged.

<a id="u-81dbc64e99da"></a>
### `ftp_initiate_transfer`

`static CURLcode ftp_initiate_transfer(struct Curl_easy *data, struct ftp_conn *ftpc)` · [lib/ftp.c:L543-L574][f1]

After the server's data connection is established, finishes data-channel setup and starts the transfer.

A blocking Curl_conn_connect on SECONDARYSOCKET returns early if not fully connected. Uploads record infilesize via progress, set the xfer to send with shutdown requested and errors ignored (the server's control reply is authoritative); downloads set up receive with the known request size and strict shutdown. It then marks a pending server response and moves state to FTP_STOP.

calls: [Curl_conn_connect](r6-connection-management.md#u-6f9c8a958761)

<a id="u-2d462be7db75"></a>
### `ftp_nb_type`

`static CURLcode ftp_nb_type(struct Curl_easy *data, struct ftp_conn *ftpc, struct FTP…` · [lib/ftp.c:L3878-L3899][f1]

Sends 'TYPE A' or 'TYPE I' as needed.

When the connection already uses the wanted type, no command is sent: the state is set and the handler is invoked synchronously with a simulated 200 response. Otherwise the command is sent, transfertype is updated, and the response handler runs later via the state machine. Send errors propagate.

<a id="u-5e017a3f4a99"></a>
### `ftp_need_type`

`static int ftp_need_type(struct ftp_conn *ftpc, bool ascii_wanted)` · [lib/ftp.c:L345-L349][f1]

Returns nonzero when the connection's current transfer type ('A' or 'I') differs from the requested one, meaning a TYPE command must still be sent.

<a id="u-3f0b575ed0e5"></a>
### `ftp_port_bind_socket`

`static CURLcode ftp_port_bind_socket(struct Curl_easy *data, struct connectdata *conn…` · [lib/ftp.c:L1116-L1191][f1]

Binds the data socket to the resolved address, iterating ports from min to max.

A bind failing with EADDRNOTAVAIL while the address is non-local falls back to the control connection's local address (getsockname failure gives CURLE_FTP_PORT_FAILED) and restarts the port loop, disabling the fallback. Errors other than EADDRINUSE/EACCES fail with CURLE_FTP_PORT_FAILED; exhausting the range (guarding against 16-bit wrap at 0xffff) fails with 'ran out of ports'. After a successful bind it re-reads the bound name into *ss so the actual port can be reported; getsockname failure is CURLE_FTP_PORT_FAILED.

<a id="u-5a23b8001e38"></a>
### `ftp_port_default_host`

`static CURLcode ftp_port_default_host(struct Curl_easy *data, struct connectdata *con…` · [lib/ftp.c:L1011-L1049][f1]

Falls back to the control connection's local IP when the FTPPORT string names no host.

getsockname failure or inet_ntop failure yields CURLE_FTP_PORT_FAILED; success fills hbuf, sets *hostp, and clears *non_localp since the address is known local.

<a id="u-749a8107b661"></a>
### `ftp_port_listen`

`static CURLcode ftp_port_listen(struct Curl_easy *data, curl_socket_t portsock)` · [lib/ftp.c:L1196-L1207][f1]

Starts listening on the bound data socket with a backlog of 1; a listen failure is CURLE_FTP_PORT_FAILED with the errno text logged.

<a id="u-4d5e98dfb90a"></a>
### `ftp_port_open_socket`

`static CURLcode ftp_port_open_socket(struct Curl_easy *data, struct connectdata *conn…` · [lib/ftp.c:L1078-L1109][f1]

Opens a TCP socket for the data connection, trying each resolved address in turn.

CURLE_OUT_OF_MEMORY propagates unchanged; any other open error is coerced to CURLE_FTP_PORT_FAILED with the last errno remembered. If no address succeeded it fails out with the socket error text; otherwise *aip holds the winning address.

<a id="u-ed1676d2c2a4"></a>
### `ftp_port_parse_string`

`static CURLcode ftp_port_parse_string(struct Curl_easy *data, struct connectdata *con…` · [lib/ftp.c:L881-L1005][f1]

Parses the CURLOPT_FTPPORT string '(ipv4|ipv6|domain|interface)?(:port(-range)?)?'.

Empty or one-character input leaves host NULL and ports zero (the caller then derives a default host). Bracketed '[ipv6]:port' takes the bracketed address; a leading ':' means port-only; otherwise the text before a ':' is the address, unless the whole string parses as an IPv6 literal (then no port part). Port parsing reads a number up to 0xffff and an optional '-max'; a min above max zeroes both. For a given address it copies it to a bounded buffer, tries Curl_if2ip to resolve an interface name: IF2IP_NOT_FOUND treats the text as a hostname, IF2IP_AF_NOT_SUPPORTED fails with CURLE_FTP_PORT_FAILED, IF2IP_FOUND uses the resolved buffer. With no address, only the port range is returned and host stays NULL.

**Uncertainties.**

- On builds without USE_IPV6 the conn/ss parameters are unused and IPv6 forms are unhandled; behavior there depends on that compile flag.

<a id="u-e26c551bff40"></a>
### `ftp_port_resolve_host`

`static CURLcode ftp_port_resolve_host(struct Curl_easy *data, struct connectdata *con…` · [lib/ftp.c:L1054-L1073][f1]

Resolves the PORT host string with a blocking DNS lookup honoring conn->ip_version.

On failure it fails out with a message naming the host; on success it extracts the address list from the DNS entry into *resp.

<a id="u-633f82f9c34a"></a>
### `ftp_port_send_command`

`static CURLcode ftp_port_send_command(struct Curl_easy *data, struct ftp_conn *ftpc, …` · [lib/ftp.c:L1212-L1316][f1]

Sends EPRT or PORT for active mode, starting at the requested command.

EPRT is skipped when disabled — except it is force-enabled when connected over IPv6 — and PORT is IPv4-only. EPRT sends '|1|host|port|' or '|2|host|port|' using the printable address of the chosen ai (which may differ from the bound ss when a non-local fallback occurred); PORT rewrites dots to commas and appends the port as two bytes. Send failures are failed out with the command name. On success it records which command was sent in ftpc->count1 and moves to FTP_PORT.

**Notes.**

- side_effect: Under IPv6 with EPRT disabled, conn->bits.ftp_use_eprt is set back to TRUE.

<a id="u-ee3c3d82c7f6"></a>
### `ftp_state_cwd`

`static CURLcode ftp_state_cwd(struct Curl_easy *data, struct ftp_conn *ftpc, struct F…` · [lib/ftp.c:L823-L868][f1]

Sends the CWD command sequence after QUOTE.

If cwddone is already set it jumps straight to ftp_state_mdtm. Otherwise it asserts NOCWD does not reach here with directories pending, resets count2 (failed-CWD counter), and either: on a reused connection with an entrypath and a relative path, first CWDs back to entrypath (cwdcount 0, state FTP_CWD); or if components exist sends CWD for the first one (cwdcount 1); or with no directories skips directly to ftp_state_mdtm. Remaining CWDs are issued from the statemachine's FTP_CWD response handler.

calls: [ftp_state_mdtm](r1-ftp-transfer-states.md#u-8b31f04ee2bf)

<a id="u-4315c1ea0cb4"></a>
### `ftp_state_get_resp`

`static CURLcode ftp_state_get_resp(struct Curl_easy *data, struct ftp_conn *ftpc, str…` · [lib/ftp.c:L2778-L2889][f1]

Handles LIST and RETR replies.

On 150/125 the transfer starts: req.size defaults to unknown (-1); for binary non-list transfers without ignorecl and a missing/zero downloadsize, the reply text is scanned for '<num> bytes' to recover the size (listings and ASCII sizes are ignored as unreliable); otherwise a known downloadsize is used. A size above maxdownload is clamped, and ASCII mode resets the size to -1. With active mode the data connection is advanced like STOR: not immediately connected sets wait_data_conn, stops the machine and checks the control connection; connected proceeds. ftp_initiate_transfer then starts the transfer. Other codes: 450 on LIST means no matching files — transfer becomes NONE and the machine stops; otherwise the RETR response fails, with CURLE_REMOTE_FILE_NOT_FOUND specifically for RETR+550 and CURLE_FTP_COULDNT_RETR_FILE for the rest.

<a id="u-40bb64097b64"></a>
### `ftp_state_list`

`static CURLcode ftp_state_list(struct Curl_easy *data, struct ftp_conn *ftpc, struct …` · [lib/ftp.c:L1537-L1591][f1]

Sends the directory-listing command.

Under FTPFILE_NOCWD with a path, the URL-decoded raw path up to the last slash becomes the LIST/NLST argument (a leading slash keeps a one-character component); otherwise no argument is sent. The command name is the custom request if set, else 'NLST' when list_only is set, else 'LIST'. It is formatted with curl_maprintf (allocation failure gives CURLE_OUT_OF_MEMORY), sent via Curl_pp_sendf, freed, and on success the state moves to FTP_LIST.

<a id="u-8b31f04ee2bf"></a>
### `ftp_state_mdtm`

`static CURLcode ftp_state_mdtm(struct Curl_easy *data, struct ftp_conn *ftpc, struct …` · [lib/ftp.c:L1650-L1670][f1]

Requests the file modification time when get_filetime or a timecondition is set and a filename exists, by sending 'MDTM <file>' and entering FTP_MDTM; otherwise it continues with ftp_state_type.

<a id="u-f6d0d32a5c49"></a>
### `ftp_state_mdtm_resp`

`static CURLcode ftp_state_mdtm_resp(struct Curl_easy *data, struct ftp_conn *ftpc, st…` · [lib/ftp.c:L2499-L2611][f1]

Handles the MDTM reply.

A 213 is parsed with ftp_213_date and converted to a time via Curl_getdate_capped; for no-body info requests with get_filetime and a valid time, a 'Last-Modified:' header is formatted and written via client_write_header (gmtime failure propagates). Other codes log an unsupported format, and 550 logs that the file is missing or inaccessible and continues. Then a timecondition is applied when both filetime and timevalue are positive: IFMODSINCE with filetime <= timevalue, or IFUNMODSINCE with filetime > timevalue, cancels the transfer (PPTRANSFER_NONE), marks timecond met, and stops; missing times skip the comparison. Finally ftp_state_type continues the chain unless an error occurred.

calls: [ftp_state_type](r1-ftp-transfer-states.md#u-d900a03d293f)

<a id="u-33dd883877d6"></a>
### `ftp_state_pasv_resp`

`static CURLcode ftp_state_pasv_resp(struct Curl_easy *data, struct ftp_conn *ftpc, in…` · [lib/ftp.c:L2046-L2189][f1]

Handles the EPSV/PASV response.

EPSV (count1 0, code 229): parses '(|||port|)', rejecting malformed or illegal ports with CURLE_FTP_WEIRD_PASV_REPLY, and takes the host from the control connection via ftp_control_addr_dup. PASV (count1 1, code 227): scans the reply for six numbers; no match is CURLE_FTP_WEIRD_227_FORMAT; with ftp_skip_ip the control host is reused, otherwise the four IP numbers are formatted as the new host; the port is (n4<<8)+n5. EPSV failure delegates to ftp_epsv_disable; a bad PASV response code is CURLE_FTP_WEIRD_PASV_REPLY. The resulting host/port build conn->origin2 (and via_peer2 when a proxy peer is in use), then Curl_conn_setup attaches the SECONDARY connection with SSL enabled or disabled per ftp_use_data_ssl; setup failure (unless OOM) falls back to ftp_epsv_disable after EPSV. Finally do_more is set and the state stops, with newhost freed on every path.

**Uncertainties.**

- The behavior of Curl_conn_setup returning a non-blocking pending connect is commented but not provable here.

<a id="u-8e8ac311f149"></a>
### `ftp_state_port_resp`

`static CURLcode ftp_state_port_resp(struct Curl_easy *data, struct ftp_conn *ftpc, st…` · [lib/ftp.c:L2405-L2440][f1]

Handles the PORT/EPRT response.

Any non-2xx code disables EPRT when it was the failed command and advances to the next command; exhausting them (DONE) fails with CURLE_FTP_PORT_FAILED, otherwise ftp_state_use_port retries with the next command. A positive response stops the DO phase and calls ftp_dophase_done with connected=FALSE, so DO_MORE will await the server's inbound connection.

<a id="u-2fd5dbc875f9"></a>
### `ftp_state_prepare_transfer`

`static CURLcode ftp_state_prepare_transfer(struct Curl_easy *data, struct ftp_conn *f…` · [lib/ftp.c:L1455-L1494][f1]

Branches the DO phase toward the data connection.

Non-body transfers skip connection setup and go through ftp_state_quote with FTP_RETR_PREQUOTE (pre-quote commands only). With ftp_use_port set, active mode starts via ftp_state_use_port(EPRT). Otherwise PASV mode is used: if PRET is enabled it sends 'PRET NLST/LIST' (no file), 'PRET STOR <file>' (upload) or 'PRET RETR <file>' and enters FTP_PRET; otherwise ftp_state_use_pasv is invoked.

<a id="u-a863aaad6ffa"></a>
### `ftp_state_rest`

`static CURLcode ftp_state_rest(struct Curl_easy *data, struct ftp_conn *ftpc, struct …` · [lib/ftp.c:L1496-L1515][f1]

For head-like requests on a file, probes server range support by sending 'REST 0' and entering FTP_REST; all other cases continue with ftp_state_prepare_transfer.

<a id="u-9ab3e2b24cb5"></a>
### `ftp_state_rest_resp`

`static CURLcode ftp_state_rest_resp(struct Curl_easy *data, struct ftp_conn *ftpc, st…` · [lib/ftp.c:L2709-L2743][f1]

Handles REST replies.

The FTP_REST probe (default case): a 350 writes an 'Accept-ranges: bytes' header; either way the chain continues with ftp_state_prepare_transfer. In FTP_RETR_REST a non-350 fails with CURLE_FTP_COULDNT_USE_REST; a 350 sends 'RETR <file>' and enters FTP_RETR.

<a id="u-29b614deaee3"></a>
### `ftp_state_retr`

`static CURLcode ftp_state_retr(struct Curl_easy *data, struct ftp_conn *ftpc, struct …` · [lib/ftp.c:L1773-L1854][f1]

Starts a download given a file size (possibly -1 unknown).

A size above max_filesize fails with CURLE_FILESIZE_EXCEEDED; the size is stored in ftp->downloadsize. With a resume offset: unknown size just proceeds (server closes the data connection); a negative offset downloads the last abs(offset) bytes, converting resume_from to filesize - downloadsize, and an offset beyond the size is CURLE_BAD_DOWNLOAD_RESUME in both polarities. If nothing remains, the xfer is nop, transfer becomes NONE and the state stops. Otherwise 'REST <offset>' is sent with state FTP_RETR_REST; without resume, 'RETR <file>' is sent with state FTP_RETR.

**Notes.**

- side_effect: data->state.resume_from is rewritten for tail downloads.

<a id="u-b9beaad4eeea"></a>
### `ftp_state_size`

`static CURLcode ftp_state_size(struct Curl_easy *data, struct ftp_conn *ftpc, struct …` · [lib/ftp.c:L1517-L1535][f1]

For info-only requests on a file, sends 'SIZE <file>' and enters FTP_SIZE; otherwise continues with ftp_state_rest.

<a id="u-c2063727dc73"></a>
### `ftp_state_size_resp`

`static CURLcode ftp_state_size_resp(struct Curl_easy *data, struct ftp_conn *ftpc, st…` · [lib/ftp.c:L2646-L2707][f1]

Parses the SIZE reply.

On 213 it scans backwards from the line end for the trailing digit run and parses it; parse failure leaves size -1 (unknown). On 550 outside the STOR_SIZE probe (resumed-upload command probing), it fails with CURLE_REMOTE_FILE_NOT_FOUND. Dispatch: FTP_SIZE writes a synthesized 'Content-Length:' header when the size is known, records the download size, and continues with ftp_state_rest; FTP_RETR_SIZE records the size and continues with ftp_state_retr; FTP_STOR_SIZE stores the size as the new resume_from and calls ftp_state_ul_setup with sizechecked=TRUE.

**Notes.**

- failure: Only trailing digits of the reply line are parsed, tolerating server prepended text.

<a id="u-95815980dadc"></a>
### `ftp_state_stor_resp`

`static CURLcode ftp_state_stor_resp(struct Curl_easy *data, struct ftp_conn *ftpc, in…` · [lib/ftp.c:L2745-L2775][f1]

Handles the STOR reply.

Code >= 400 fails the upload with CURLE_UPLOAD_FAILED after stopping the state machine. With active mode (ftp_use_port) the state stops first, then the SECONDARY connection is advanced non-blockingly: if not immediately connected, wait_data_conn is set and the control connection is checked for early traffic; if connected, wait_data_conn clears. Passive mode falls through directly. Either way ftp_initiate_transfer starts the transfer.

<a id="u-d900a03d293f"></a>
### `ftp_state_type`

`static CURLcode ftp_state_type(struct Curl_easy *data, struct ftp_conn *ftpc, struct …` · [lib/ftp.c:L1617-L1646][f1]

Decides whether a TYPE command is needed.

For no-body requests on a file when the current transfer type differs from the wanted one, it marks the transfer as info-only and sends TYPE via ftp_nb_type (needed because sizes can differ per mode); any other case continues with ftp_state_size.

<a id="u-443be8d82e7c"></a>
### `ftp_state_type_resp`

`static CURLcode ftp_state_type_resp(struct Curl_easy *data, struct ftp_conn *ftpc, st…` · [lib/ftp.c:L2613-L2644][f1]

Validates the TYPE response: any non-2xx fails with CURLE_FTP_COULDNT_SET_TYPE; a non-200 positive code is tolerated with a log note (some servers answer 226).

Dispatch then continues by instate: FTP_TYPE to ftp_state_size, FTP_LIST_TYPE to ftp_state_list, FTP_RETR_TYPE/STOR_TYPE/LIST_TYPE to the matching prequote wrapper.

<a id="u-057e86c89c7b"></a>
### `ftp_state_ul_setup`

`static CURLcode ftp_state_ul_setup(struct Curl_easy *data, struct ftp_conn *ftpc, str…` · [lib/ftp.c:L1673-L1771][f1]

Prepares an upload.

With a resume offset (unknown size check pending, or a positive offset after SIZE), it first handles a negative resume: sends 'SIZE <file>' and enters FTP_STOR_SIZE. Otherwise it enables append, seeks the input stream to the resume offset via the user seek callback; a hard seek error is CURLE_FTP_COULDNT_USE_REST, and a CANTSEEK result is worked around by reading and discarding resume_from bytes from the input (a short or aborted read fails the same way). infilesize is then reduced by the offset; if nothing remains, the xfer is set to nop, ftp->transfer becomes PPTRANSFER_NONE, and the state stops with success. Finally it sends 'APPE <file>' or 'STOR <file>' and enters FTP_STOR.

**Notes.**

- side_effect: data->state.infilesize and the input stream position are consumed by the resume handling.

<a id="u-2afa55e00021"></a>
### `ftp_state_use_pasv`

`static CURLcode ftp_state_use_pasv(struct Curl_easy *data, struct ftp_conn *ftpc, str…` · [lib/ftp.c:L1410-L1446][f1]

Starts passive mode: EPSV is force-enabled when disabled on an IPv6 connection (under PF_INET6), then either 'EPSV' or 'PASV' is sent according to conn->bits.ftp_use_epsv.

On successful send, count1 records the mode, state moves to FTP_PASV, and passive connection is logged; send errors propagate.

<a id="u-a88b56c9cd72"></a>
### `ftp_state_use_port`

`static CURLcode ftp_state_use_port(struct Curl_easy *data, struct ftp_conn *ftpc, ftp…` · [lib/ftp.c:L1324-L1408][f1]

Sets up an active-mode data connection: parses the FTPPORT string, derives the default local host when none was given, resolves it, opens and binds the socket, listens, sends EPRT/PORT, and replaces the SECONDARY filter with a listening socket (after which portsock ownership moves to the filter; on failure the raw socket is closed).

The DNS entry is unlinked regardless. On failure state goes to FTP_STOP. On success, when data-connection SSL is requested for PORT mode and not yet in place, an SSL filter using the control connection's origin is added; do_more is cleared and an accept-timeout expiry is armed (user accepttimeout or DEFAULT_ACCEPT_TIMEOUT).

**Uncertainties.**

- Which failure inside the helper chain leaves which partial resources (socket, dns entry) is only partially visible; the cleanup path closes portsock but other intermediates rely on the helpers.

<a id="u-004cf8bdec2b"></a>
### `match_pasv_6nums`

`static bool match_pasv_6nums(const char *p, unsigned int *array) /* 6 numbers */` · [lib/ftp.c:L2028-L2044][f1]

Scans a 227 PASV reply for six comma-separated numbers, each at most 255, filling the caller's array.

Any missing comma or unparseable/oversized number returns FALSE; six successes return TRUE.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/ftp.c
