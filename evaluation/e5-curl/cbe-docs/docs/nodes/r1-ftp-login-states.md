# FTP Login and Response States

**Capability.** Owns the pingpong response dispatch (ftp_pp_statemachine), the initial 220/USER/PASS/ACCT/PWD handshake states, and the core reply-reading primitives (ftp_readresp, getftpresponse, ftp_endofresp), with ftp_state_low as the sole authorized state transition point.

Read this for connection-level FTP dialogues. ftp_pp_statemachine routes each server reply to a handler; quote/prequote handling and the blocking quote sender also live here since they gate the login sequence.

**Depends on.**

- [Trace and Debug Logging](r1-trace-logging.md) · graph-confirmed · 24 edge(s)
- [Pingpong command/response transport](r12-pingpong-transport.md) · graph-only · 25 edge(s)

**Depended on by.**

- [FTP Transfer Lifecycle](r1-ftp-lifecycle.md) · graph-confirmed · 6 edge(s)
- [FTP Transfer Command States](r1-ftp-transfer-states.md) · graph-confirmed · 36 edge(s) · Transfer state handlers advance protocol state through ftp_state_low in the login/response-states node.

Parent: [FTP Protocol Implementation](r1-ftp-protocol.md)

## Units (17)

<a id="u-9735c61b73c7"></a>
### `lib/ftp.c-prequote-states`

`static CURLcode ftp_state_list_prequote(struct Curl_easy *data, struct ftp_conn *ftpc…` · [lib/ftp.c:L1593-L1599][f1]

Three thin wrappers that forward to ftp_state_quote with init=TRUE and the corresponding instate: FTP_LIST_PREQUOTE, FTP_RETR_PREQUOTE and FTP_STOR_PREQUOTE.

They are invoked after TYPE handling to start sending the pre-quote command list.

<a id="u-9899c0a51458"></a>
### `ftp_endofresp`

`static bool ftp_endofresp(struct Curl_easy *data, struct connectdata *conn, const cha…` · [lib/ftp.c:L576-L589][f1]

Pingpong response terminator: a line ends an FTP response when it exceeds 3 characters, starts with three digits followed by a space (LASTLINE), and those digits parse as a number up to 999, which is stored in *code.

Any other line keeps the response accumulating.

<a id="u-94352f2724e9"></a>
### `ftp_has_ctrl`

`static bool ftp_has_ctrl(const char *string)` · [lib/ftp.c:L2925-L2934][f1]

Returns TRUE when any byte of the NUL-terminated string is below 0x20.

Used to reject CR/LF (or any control byte) inside values that become part of an FTP command line, preventing command smuggling.

<a id="u-fc5cbe118df0"></a>
### `ftp_pp_statemachine`

`static CURLcode ftp_pp_statemachine(struct Curl_easy *data, struct connectdata *conn)` · [lib/ftp.c:L3180-L3500][f1]

Pingpong callback dispatching one FTP server response to the current state's handler.

Missing metadata is CURLE_FAILED_INIT; pending sends are flushed first, then a response is read; no complete response yet returns quietly. State dispatch: WAIT220 -> ftp_wait_resp. AUTH rejects pipelined responses, accepts 234/334 by adding the SSL filter (failure CURLE_USE_SSL_FAILED) and doing a blocking TLS connect before USER; otherwise tries the next AUTH mechanism up to two attempts (count3), and after exhaustion fails with CURLE_USE_SSL_FAILED when SSL is required or continues in clear text. USER/PASS, ACCT, PWD, SYST (records server OS, special-casing OS/400 with SITE NAMEFMT 1 then FTP_NAMEFMT), NAMEFMT (250 reloads the path via PWD), quote states (>=400 without the '*'-tolerance flag is CURLE_QUOTE_ERROR), CWD (failure triggers MKD when create-missing-dirs is enabled, with count3 allowing one MKD failure then a second CWD try; otherwise cwdfail is set and access denied; success walks the component list), MKD (one tolerated failure via count3, then CWD into it), MDTM/TYPE/SIZE/REST/STOR/LIST/RETR/PASV/PORT/PRET (non-200 fails CURLE_FTP_PRET_FAILED) and CCC (code < 500 removes the SSL filter, active mode per setting, then PWD) all delegate to their handler functions. FTP_PROT sets ftp_use_data_ssl on success and fails with CURLE_USE_SSL_FAILED when 'P' was required and rejected; FTP_QUIT or an unknown state simply stops.

calls: [ftp_state_user_resp](r1-ftp-login-states.md#u-fefae17bfb11), [ftp_state_pasv_resp](r1-ftp-transfer-states.md#u-33dd883877d6)

**Uncertainties.**

- The PROT/PBSZ handling assumes Curl_conn_is_ssl on the control socket reflects the TLS filter added in AUTH; the filter's timing is external to this file.

<a id="u-399e3d4ac932"></a>
### `ftp_pwd_resp`

`static CURLcode ftp_pwd_resp(struct Curl_easy *data, struct ftp_conn *ftpc, int ftpcode)` · [lib/ftp.c:L3018-L3120][f1]

Parses the PWD reply to learn the login directory.

On 257 it scans from offset 4 for the first quote, then accumulates the quoted path, honoring RFC 959 quote-doubling ("" -> literal "); a control character inside the path aborts with CURLE_WEIRD_SERVER_REPLY. An extracted path that does not start with '/' and an unknown server OS triggers a 'SYST' query before storing the path. The path is stored as ftpc->entrypath (freeing the old one) and duplicated into data->state.most_recent_ftp_entrypath (OOM propagates). With a pending SYST the state enters FTP_SYST; otherwise, and also for unparseable or non-257 replies, the machine stops, ending the CONNECT phase.

**Notes.**

- side_effect: ftpc->server_os is left unset when SYST is queued, so the SYST handler later fills it.

<a id="u-5a80fd0a11a3"></a>
### `ftp_readresp`

`static CURLcode ftp_readresp(struct Curl_easy *data, struct ftp_conn *ftpc, int8_t so…` · [lib/ftp.c:L591-L622][f1]

Reads one server response through Curl_pp_readresp.

The code is stored in data->info.httpcode unless the connection is shutting down, and is always copied to *ftpcodep. A code of 421 (service not available, control connection closing — typically idle timeout) is treated generically at this layer: state moves to FTP_STOP and CURLE_OPERATION_TIMEDOUT is returned regardless of the underlying read result.

calls: [ftp_state_low](r1-ftp-login-states.md#u-f9bf7fcbe802)

<a id="u-1ad9ab7d531b"></a>
### `ftp_sendquote`

`static CURLcode ftp_sendquote(struct Curl_easy *data, struct ftp_conn *ftpc, struct c…` · [lib/ftp.c:L3576-L3620][f1]

Blocking sender of a quote command list: each item is sent with Curl_pp_sendf, the response timeout is re-anchored to now, and getftpresponse blocks for the reply.

Transport errors propagate immediately. A reply code >= 400 is CURLE_QUOTE_ERROR unless the command began with '*', which suppresses the failure regardless of the reply.

<a id="u-5fb46f344516"></a>
### `ftp_state_acct_resp`

`static CURLcode ftp_state_acct_resp(struct Curl_easy *data, struct ftp_conn *ftpc, in…` · [lib/ftp.c:L3003-L3016][f1]

Handles the ACCT reply: any code other than 230 fails with CURLE_FTP_WEIRD_PASS_REPLY; 230 continues with ftp_state_loggedin.

<a id="u-9f04eb1fc19e"></a>
### `ftp_state_loggedin`

`static CURLcode ftp_state_loggedin(struct Curl_easy *data, struct ftp_conn *ftpc)` · [lib/ftp.c:L2892-L2920][f1]

Runs after successful USER/PASS/ACCT.

Over an SSL control connection it sends 'PBSZ 0' first (PROT requires it per the FTPS draft) entering FTP_PBSZ; otherwise it continues with ftp_state_pwd.

<a id="u-f9bf7fcbe802"></a>
### `ftp_state_low`

`static void ftp_state_low(struct Curl_easy *data, struct ftp_conn *ftpc, ftpstate new…` · [lib/ftp.c:L134-L153][f1]

Sole authorized way to change the FTP connection's protocol state.

When the state actually differs from the new one it emits a trace naming old and new state (with the calling line under DEBUGBUILD, via the ftp_state macro); otherwise it only overwrites ftpc->state with no other side effects.

**Uncertainties.**

- State-name tracing is compiled only under CURLVERBOSE; FTP_CSTATE is undefined otherwise, so the trace path's availability depends on those macros.

<a id="u-a5fee87d0a38"></a>
### `ftp_state_pwd`

`static CURLcode ftp_state_pwd(struct Curl_easy *data, struct ftp_conn *ftpc)` · [lib/ftp.c:L753-L766][f1]

Sends the PWD command and on success moves to FTP_PWD.

Under DEBUGBUILD only, the environment variable CURL_FTP_PWD_STOP combined with data->id == 0 suppresses the command and returns CURLE_OK without changing state.

<a id="u-8a0a27d691ee"></a>
### `ftp_state_quote`

`static CURLcode ftp_state_quote(struct Curl_easy *data, struct ftp_conn *ftpc, struct…` · [lib/ftp.c:L1856-L1970][f1]

Sends the quote/pre-quote/post-quote command lists one item per state entry, driven by ftpc->count1 as the list index.

The list is chosen by instate: quote, prequote (three states) or postquote. A leading '*' marks the command as allowed to fail (count2=1); otherwise a failure code aborts later. Each present item is sent and the state re-enters instate. When the list is exhausted, the continuation depends on instate: QUOTE goes to ftp_state_cwd; RETR_PREQUOTE either stops for non-body transfers, or reuses a known file size via ftp_state_retr, or sends RETR directly when ignorecl or ASCII is set (skipping SIZE), else sends SIZE entering FTP_RETR_SIZE; STOR_PREQUOTE calls ftp_state_ul_setup; LIST_PREQUOTE enters FTP_LIST_TYPE and calls ftp_state_list; POSTQUOTE ends. Send errors propagate.

calls: [ftp_state_cwd](r1-ftp-transfer-states.md#u-ee3c3d82c7f6)

<a id="u-990b4f5cd56c"></a>
### `ftp_state_user`

`static CURLcode ftp_state_user(struct Curl_easy *data, struct ftp_conn *ftpc, struct …` · [lib/ftp.c:L740-L751][f1]

Sends 'USER <user>' from the connection credentials; on success clears ftp_trying_alternative and moves to FTP_USER.

Send failure is propagated and the state is unchanged.

<a id="u-fefae17bfb11"></a>
### `ftp_state_user_resp`

`static CURLcode ftp_state_user_resp(struct Curl_easy *data, struct ftp_conn *ftpc, in…` · [lib/ftp.c:L2937-L3000][f1]

Handles USER/PASS replies.

331 while in FTP_USER sends 'PASS <password>' entering FTP_PASS. Any 2xx proceeds to ftp_state_loggedin. 332 requests an account: a missing FTP_ACCOUNT fails with CURLE_LOGIN_DENIED; an account containing a control byte fails with CURLE_BAD_FUNCTION_ARGUMENT; otherwise 'ACCT <account>' is sent entering FTP_ACCT. All other codes (e.g. 530) try the alternative-to-user command once when configured — again rejecting control bytes — setting ftp_trying_alternative and re-entering FTP_USER; otherwise login fails with CURLE_LOGIN_DENIED.

**Notes.**

- failure: ftp_trying_alternative prevents an infinite USER/alternative retry loop.

<a id="u-5f28e297c466"></a>
### `ftp_use_ssl`

`static unsigned char ftp_use_ssl(struct connectdata *conn, struct ftp_conn *ftpc)` · [lib/ftp.c:L3172-L3178][f1]

Resolves the effective SSL usage: an implicit-TLS scheme (PROTOPT_SSL) with no explicit setting forces CURLUSESSL_ALL; otherwise ftpc->use_ssl is returned unchanged.

<a id="u-93da0e1c6bf3"></a>
### `ftp_wait_resp`

`static CURLcode ftp_wait_resp(struct Curl_easy *data, struct connectdata *conn, struc…` · [lib/ftp.c:L3124-L3169][f1]

Handles the initial 220 (or an already-logged-in 230).

A non-220/230 reply fails with CURLE_WEIRD_SERVER_REPLY. A 230 is treated as USER response when SSL use is at most TRY or TLS is already active. When FTPS is requested and the control channel is still clear text, the AUTH state is prepared per CURLFTPAUTH: default/SSL selects 'AUTH SSL' (count2=1, count1=0), TLS selects 'AUTH TLS' (count2=-1, count1=1); an unsupported auth value is CURLE_UNKNOWN_OPTION. Otherwise, or after the AUTH setup, the USER command is sent via ftp_state_user.

<a id="u-5a00bf964808"></a>
### `getftpresponse`

`static CURLcode getftpresponse(struct Curl_easy *data, size_t *nreadp, /* return numb…` · [lib/ftp.c:L631-L738][f1]

Blocking reader of a complete FTP response after a command.

It loops until a final code arrives or an error occurs, recomputing the pingpong timeout each iteration; timeout already expired gives CURLE_OPERATION_TIMEDOUT. It skips waiting when cached recvbuf data exists, but after two consecutive cache-only rounds with no new bytes it waits anyway (cache_skip counter) to avoid busy-looping. Otherwise it selects on the control socket (plus the flush socket when a send is pending) in intervals of at most one second, running a progress update on each select timeout; select failure gives CURLE_RECV_ERROR. Pending sends are flushed before reading. On exit it clears pp->pending_resp; *ftpcodep stays 0 on errors.

**Uncertainties.**

- Whether Curl_pgrsUpdate can itself set result and stop the loop is not visible here; the code assigns but does not check it before continuing.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/ftp.c
