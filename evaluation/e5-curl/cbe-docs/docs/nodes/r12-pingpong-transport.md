# Pingpong command/response transport

**Capability.** Generic line-oriented command send and response read machinery shared by POP3-like protocols: buffered send, incremental response scanning, timeouts, and pollset wiring.

Read this before touching any pingpong-based protocol engine. Engines drive it via Curl_pp_init/vsendf/readresp/statemach and never parse raw sockets themselves.

**Depended on by.**

- [POP3 client](r12-pop3-client.md) · graph-confirmed · 22 edge(s) · The POP3 engine drives its command/response dialog through the shared pingpong transport.
- [FTP Login and Response States](r1-ftp-login-states.md) · graph-only · 25 edge(s)
- [SMTP protocol engine](r7-smtp-protocol.md) · graph-only · 24 edge(s)

Parent: [Protocol engines](r12-protocol-engines.md)

## Units (9)

<a id="u-2bd21cb068dd"></a>
### `Curl_pp_init`

`void Curl_pp_init(struct pingpong *pp, const struct curltime *pnow)` · [lib/pingpong.c:L124-L133][f1]

Prepares a pingpong struct for a fresh response cycle: zeroes nread_resp, starts the response deadline from the caller-supplied timestamp, sets pending_resp, initializes sendbuf and recvbuf dynbufs with the DYN_PINGPPONG_CMD limit, and marks initialized.

DEBUGASSERT fires on double initialization.

calls: [curlx_dyn_init](r3-dynbuf.md#u-dba8ba103985)

<a id="u-38c5e1d73b67"></a>
### `Curl_pp_vsendf`

`CURLcode Curl_pp_vsendf(struct Curl_easy *data, struct pingpong *pp, const char *pref…` · [lib/pingpong.c:L135-L198][f1]

Formats and sends one command line to the server, never blocking.

It resets sendbuf, builds '[prefix ]<fmt>\r\n' via dynbuf adds (returning early on any allocation failure), sets pending_resp TRUE, and sends the whole buffer over FIRSTSOCKET with Curl_conn_send. CURLE_AGAIN is treated as zero bytes written; other errors propagate. The bytes actually written are logged via Curl_debug (CURLINFO_HEADER_OUT). Partial writes store the residual: sendthis points at the buffer, sendsize the full length, sendleft the remainder, and the response deadline is NOT restarted; a complete write clears those fields and restarts the response timer via Curl_pgrs_now. Without a connection it returns CURLE_SEND_ERROR. DEBUGASSERTs require no leftover send from a previous call.

calls: [lib-cfilters-c-conn-io-entry](r8-cfilters-io.md#u-688833f4c38c), [Curl_debug](r1-trace-logging.md#u-20b8ae9f02d8)

**Uncertainties.**

- sendbuf ownership of sendthis: the pointer stays valid only until the next sendbuf reset, which callers must respect.

<a id="u-f696034e55f0"></a>
### `Curl_pp_readresp`

`CURLcode Curl_pp_readresp(struct Curl_easy *data, int8_t sockindex, struct pingpong *…` · [lib/pingpong.c:L228-L341][f1]

Reads and scans server response bytes until a final response line is found or no more data is immediately available; on success *code holds the server code and *size the total response byte count, both zeroed at entry.

Loop structure: an outer do/while continues while the last recv filled the whole 900-byte buffer; each pass first drops any previously recognized final line (pp->nfinal bytes) from the head of recvbuf via curlx_dyn_tail and clears nfinal. Unless pp->overflow says the buffer already holds extra data, it reads from the socket via pingpong_read: CURLE_AGAIN returns CURLE_OK (still pending), other recv errors propagate, an empty read fails with 'response reading failed (errno)' and CURLE_RECV_ERROR, then bytes are appended to recvbuf and counted in nread_resp and req.headerbytecount. The inner scan finds the first '\n'; an embedded NUL within that line fails with CURLE_WEIRD_SERVER_REPLY; each complete line is debug-logged and delivered to the client as CLIENTWRITE_INFO headers, propagating any error. pp->endofresp decides if the line terminates the response: then nfinal records its length, overflow counts any surplus bytes kept in the buffer, *size is set, nread_resp resets, and the loops break. A non-final line is trimmed off the buffer. maxloops=10 bounds socket reads per call to avoid starvation. Only when a final line was processed does pending_resp drop to FALSE.

**Notes.**

- failure: A NUL byte inside a response line aborts with CURLE_WEIRD_SERVER_REPLY, mirroring HTTP header validation.
- condition: The maxloops counter limits reads to 10 socket fetches per call; hitting it returns CURLE_OK with the response still incomplete.

calls: [Curl_pp_readresp](r12-pingpong-transport.md#u-f696034e55f0), [Curl_debug](r1-trace-logging.md#u-20b8ae9f02d8), [Curl_client_write](r4-client-writer-stack.md#u-5e34efff1274), [curlx_dyn_tail](r3-dynbuf.md#u-3a3e5b30ff85)

**Uncertainties.**

- endofresp semantics (which lines count as final, and the *code value) are protocol-defined and not visible here.
- Whether returning CURLE_OK with pending_resp still TRUE after CURLE_AGAIN or maxloops is interpreted uniformly by all callers is decided outside this file.

<a id="u-673b0f00a073"></a>
### `Curl_pp_statemach`

`CURLcode Curl_pp_statemach(struct Curl_easy *data, struct pingpong *pp, bool block, b…` · [lib/pingpong.c:L62-L121][f1]

Drives one iteration of the protocol's pingpong state machine, optionally blocking for socket activity.

If Curl_pp_state_timeleft_ms reports no time left it fails with 'server response timeout' and returns CURLE_OPERATION_TIMEDOUT. When blocking, it waits in up to 1-second slices capped by the remaining timeout; when non-blocking it waits zero and schedules a Curl_expire(EXPIRE_SERVER_RESPONSE) so the multi API wakes even without traffic. If data is pending on the first socket or pp->overflow holds cached bytes, rc is treated as ready without polling; otherwise Curl_socket_check polls the socket for reading (or writing while pp->sendleft is set). After a blocking wait it runs Curl_pgrsCheck and returns any progress error. rc == -1 yields failf 'select/poll error' and CURLE_OUT_OF_MEMORY; a ready socket invokes pp->statemachine and returns its result; no activity with disconnecting true returns CURLE_OPERATION_TIMEDOUT; otherwise CURLE_OK.

calls: [Curl_pp_state_timeleft_ms](r12-pingpong-transport.md#u-f6e71e88371f), [lib-cfilters-c-pending-flush](r8-cfilters-io.md#u-0cbca31d987f), [Curl_socket_check](r5-poll-waiting.md#u-0a038eae5033), [Curl_expire_set](r13-multi-timers-wait.md#u-8d88bc1ba951), [Curl_pgrsCheck](r9-progress-timing-and-policy.md#u-bcd5c04b6516)

**Uncertainties.**

- The protocol-supplied pp->statemachine result codes for individual states are defined outside this file.
- Duplicate readiness checks (Curl_conn_data_pending called twice, second gated on !pp->sendleft) appear partly redundant; whether the first check ever sees ready data with sendleft set is not established here.

<a id="u-f6e71e88371f"></a>
### `Curl_pp_state_timeleft_ms`

`timediff_t Curl_pp_state_timeleft_ms(struct Curl_easy *data, struct pingpong *pp)` · [lib/pingpong.c:L42-L57][f1]

Computes the milliseconds remaining before the current pingpong response times out.

The budget is CURLOPT_SERVER_RESPONSE_TIMEOUT if set, otherwise PINGPONG_TIMEOUT_MS (60 s). It subtracts the elapsed time between now (Curl_pgrs_now, which also refreshes the progress clock) and the response timestamp recorded when the last command finished sending. If the overall transfer has a time left value (Curl_timeleft_ms returns nonzero), the smaller of the two budgets is returned; otherwise the pingpong budget alone. Zero or negative means the timeout has already fired.

calls: [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77), [Curl_timeleft_ms](r6-connection-management.md#u-030f377eec8b)

**Uncertainties.**

- Whether data->set.server_response_timeout is stored in milliseconds is not verifiable from this source alone.

<a id="u-259e510787b3"></a>
### `Curl_pp_flushsend`

`CURLcode Curl_pp_flushsend(struct Curl_easy *data, struct pingpong *pp)` · [lib/pingpong.c:L359-L389][f1]

Sends the remainder of a partially written command.

Returns CURLE_OK immediately if nothing is pending. Sends sendleft bytes starting at sendthis + sendsize - sendleft; CURLE_AGAIN is downgraded to OK with zero written, other errors propagate. A fraction written just decrements sendleft; completing the send clears sendthis/sendsize/sendleft and restarts the response deadline from Curl_pgrs_now, which is what starts response-timeout accounting after a split command.

calls: [lib-cfilters-c-conn-io-entry](r8-cfilters-io.md#u-688833f4c38c), [Curl_pp_flushsend](r12-pingpong-transport.md#u-259e510787b3)

<a id="u-35d3a30c6c79"></a>
### `Curl_pp_moredata`

`bool Curl_pp_moredata(struct pingpong *pp)` · [lib/pingpong.c:L401-L404][f1]

Reports whether another Curl_pp_readresp call will find data without blocking: true when nothing is left to send and recvbuf holds bytes beyond the already-consumed final line (nfinal).

calls: [dynbuf.c-accessors](r3-dynbuf.md#u-5e7007dbb9e6)

<a id="u-61def25ad0af"></a>
### `Curl_pp_pollset`

`CURLcode Curl_pp_pollset(struct Curl_easy *data, struct pingpong *pp, struct easy_pol…` · [lib/pingpong.c:L343-L350][f1]

Updates the easy's pollset for the first socket: watch writability while a command chunk is still unsent (sendleft), otherwise readability.

calls: [Curl_pollset_change](r5-poll-waiting.md#u-addd4abe094e)

<a id="u-7e3b1134e1f4"></a>
### `Curl_pp_disconnect`

`CURLcode Curl_pp_disconnect(struct pingpong *pp)` · [lib/pingpong.c:L391-L399][f1]

Tears down a pingpong struct: if initialized, frees both dynbufs and zeroes the whole struct so a reused connection must be re-initialized.

Always returns CURLE_OK.

calls: [curlx_dyn_free](r3-dynbuf.md#u-21f694d1bd8a)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/pingpong.c
