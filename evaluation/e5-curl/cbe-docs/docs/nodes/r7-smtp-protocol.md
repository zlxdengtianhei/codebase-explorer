# SMTP protocol engine

**Capability.** The SMTP client: pingpong-based state machine with per-state response handlers, command senders, SASL authentication, dot-stuffed body upload, and the DO/DOING/DONE/connect/disconnect lifecycle callbacks.

smtp_connect/smtp_do/smtp_done are the protocol vtable entry points; smtp_pp_statemachine dispatches replies to the per-state handlers which drive command senders through smtp_state transitions. Address handling delegates to IDN and percent-decoding to escape.c.

**Depends on.**

- [Connection metadata and scheme descriptors](r7-connection-metadata.md) · graph-confirmed · 13 edge(s)
- [Internationalized domain names](r7-idn-hostnames.md) · graph-confirmed · 8 edge(s)
- [String escaping and encoding](r7-string-escape-utils.md) · graph-confirmed · 2 edge(s)
- [Trace and Debug Logging](r1-trace-logging.md) · graph-only · 26 edge(s)
- [Pingpong command/response transport](r12-pingpong-transport.md) · graph-only · 24 edge(s)

Parent: [curl codebase](r7-curl-codebase.md)

## Units (27)

<a id="u-1593f70aa971"></a>
### `pingpong`

`struct pingpong` · [lib/pingpong.h:L48-L71][f1]

Holds the per-connection pingpong conversation state shared by FTP, IMAP, POP3 and SMTP.

It tracks a partially sent command (sendthis/sendleft/sendsize), a receive buffer accumulating response bytes (recvbuf, nread_resp), where the final response line ends (nfinal, overflow), the response deadline timestamp, and two function pointers (statemachine, endofresp) that each protocol must install, typically via PINGPONG_SETUP. initialized guards whether the dynbufs were set up and thus whether Curl_pp_disconnect frees them; pending_resp is TRUE from command send until the final response line has been read. Overflow/nfinal let callers distinguish cached extra data from the consumed final line. Uncertainty: field updates are driven by the pingpong.c functions, not by this header itself.

contract: [Curl_pp_init](r12-pingpong-transport.md#u-2bd21cb068dd), [Curl_pp_readresp](r12-pingpong-transport.md#u-f696034e55f0)

**Uncertainties.**

- Exact ownership/lifetime of the protocol callbacks beyond PINGPONG_SETUP usage is not shown in this header.

<a id="u-0f5be6cb436f"></a>
### `lib-smtp.c-command-senders`

`static CURLcode smtp_perform_ehlo(struct Curl_easy *data, struct smtp_conn *smtpc)` · [lib/smtp.c:L621-L639][f2]

Small helpers that format and send one SMTP command line through Curl_pp_sendf and advance the state on success.

smtp_perform_ehlo clears the cached SASL mechanisms, used mechanism, TLS and AUTH capability flags before sending 'EHLO <domain>' and moving to SMTP_EHLO. smtp_perform_helo clears authused, sends 'HELO <domain>', and moves to SMTP_HELO. smtp_perform_starttls sends 'STARTTLS' and moves to SMTP_STARTTLS. smtp_perform_auth sends 'AUTH <mech> <initresp>' when an initial response exists (an empty response becomes '='), else 'AUTH <mech>'; it does not itself change state (the SASL layer does). smtp_continue_auth sends the SASL continuation data verbatim and smtp_cancel_auth sends '*' to cancel; both, like perform_auth, return CURLE_FAILED_INIT when the connection meta is missing and ignore the mech argument. smtp_perform_quit sends 'QUIT' and moves to SMTP_QUIT. In every wrapper the Curl_pp_sendf error code is propagated and the state change happens only when sending succeeded.

calls: [Curl_pp_vsendf](r12-pingpong-transport.md#u-38c5e1d73b67)

<a id="u-c3f1632b62b1"></a>
### `lib-smtp.c-cr-eob-reader`

`struct cr_eob_ctx` · [lib/smtp.c:L308-L317][f2]

SMTP End-Of-Body escaping client reader: a Curl_creader subclass installed before message upload that escapes the '\r\n.\r\n' marker.

cr_eob_ctx embeds the reader plus a bufq staging buffer, the running EOB match count, and EOS bookkeeping flags. cr_eob_init resets the match state to 2 (as if a virtual CRLF preceded the first byte, so a body starting with '.' gets escaped) and creates the 16 KiB soft-limited buffer; cr_eob_close frees it. cr_eob_total_length always returns -1 because escaping changes the body length, delegating rewind/pause/etc. to default creader handlers. cr_eob_add builds the reader via Curl_creader_create with the cr_eob vtable in the CURL_CR_CONTENT_ENCODE phase, registers it with Curl_creader_add, and on failure frees it. The byte transformation itself is cr_eob_read.

group: [cr_eob_read](r7-smtp-protocol.md#u-d605a2dcf9ea); calls: [Curl_creader_add](r4-client-reader-stack.md#u-78e5aea0e006), [bufq-c-init-free](r15-bufq-chunk-engine.md#u-1d395f59b0bc)

<a id="u-d49e3db8c3d1"></a>
### `lib-smtp.c-dtors-setup`

`static void smtp_easy_dtor(const void *key, size_t klen, void *entry)` · [lib/smtp.c:L1950-L1956][f2]

Lifetime management of the SMTP meta objects.

smtp_easy_dtor frees the per-easy struct SMTP; smtp_conn_dtor first disconnects the pingpong layer, frees smtpc->domain, then frees the per-connection smtp_conn struct; both are installed as meta destructors. smtp_setup_connection allocates both structs with curlx_calloc and attaches them via Curl_conn_meta_set/Curl_meta_set with those destructors; an allocation failure or a meta-set failure (which takes ownership) yields CURLE_OUT_OF_MEMORY.

calls: [Curl_pp_disconnect](r12-pingpong-transport.md#u-7e3b1134e1f4)

**Uncertainties.**

- Whether Curl_conn_meta_set failing frees the passed entry, or leaks it, depends on url.c internals.

<a id="u-e8493922da20"></a>
### `lib-smtp.c-response-handlers`

`static CURLcode smtp_state_servergreet_resp(struct Curl_easy *data, struct smtp_conn …` · [lib/smtp.c:L1149-L1165][f2]

Per-state response handlers invoked by smtp_pp_statemachine after a full server reply; each receives the status code and either advances the protocol or fails.

servergreet: non-2xx greeting fails with CURLE_WEIRD_SERVER_REPLY, otherwise EHLO is sent. starttls: pipelined replies (pp.overflow) fail immediately; code 220 moves to SMTP_UPGRADETLS; other codes fail with CURLE_USE_SSL_FAILED unless use_ssl is CURLUSESSL_TRY, in which case authentication is attempted instead. ehlo: non-2xx/non-1 falls back to HELO when SSL is not required or already active, else CURLE_REMOTE_ACCESS_DENIED; a 2xx/1 reply of sufficient length scans capability lines setting tls_supported, size_supported, utf8_supported, and for 'AUTH ' decodes each mechanism word into sasl.authmechs; when the reply is final (code != 1) it starts STARTTLS if SSL is wanted and supported, falls back to authentication under CURLUSESSL_TRY, fails with CURLE_USE_SSL_STARTED denied otherwise, or simply authenticates; shorter than 4 bytes is CURLE_WEIRD_SERVER_REPLY. helo: non-2xx is CURLE_REMOTE_ACCESS_DENIED, else the connect phase ends at SMTP_STOP. auth: delegates to Curl_sasl_continue; SASL_DONE ends at SMTP_STOP, SASL_IDLE means cancellation and returns CURLE_LOGIN_DENIED. command: a non-2xx (excluding 553 for recipient commands and internal 1) fails; otherwise the line is written to the client body unless no_body, then the recipient list advances to the next smtp_perform_command or the DO phase ends. mail: non-2xx is CURLE_SEND_ERROR, else RCPT TO begins. rcpt: a non-2xx records rcpt_last_error and, unless mail_rcpt_allowfails allows continuing, fails with CURLE_SEND_ERROR; success sets rcpt_had_ok; then the list advances to the next recipient, or when exhausted fails with the last error if nothing succeeded, else sends 'DATA' and moves to SMTP_DATA. data: only 354 proceeds — upload size is published, the transfer is switched to send mode, and the DO phase ends; other codes are CURLE_SEND_ERROR. postdata: any code other than 250 is CURLE_WEIRD_SERVER_REPLY; the state ends at SMTP_STOP either way, finishing the DONE phase.

calls: [smtp_perform_rcpt_to](r7-smtp-protocol.md#u-62bd7e131da9), [smtp_perform_command](r7-smtp-protocol.md#u-bdef81c8f8db), [lib-smtp.c-command-senders](r7-smtp-protocol.md#u-0f5be6cb436f)

**Uncertainties.**

- Whether smtp_state_command_resp's Curl_client_write result feeds back into transfer accounting depends on transfer.c internals.

<a id="u-f96fe8e03e81"></a>
### `lib-smtp.c-statemach-drivers`

`static CURLcode smtp_multi_statemach(struct Curl_easy *data, bool *done)` · [lib/smtp.c:L1612-L1625][f2]

Entry points that run the pingpong state machine in different modes.

smtp_multi_statemach runs Curl_pp_statemach non-blocking once, reports done when the state reached SMTP_STOP, and returns CURLE_FAILED_INIT without a connection meta. smtp_block_statemach loops Curl_pp_statemach in blocking mode until SMTP_STOP or an error, passing the disconnecting flag through for the disconnect path. smtp_pollset translates the pingpong socket interest into the easy pollset via Curl_pp_pollset and returns CURLE_OK when no SMTP connection exists.

calls: [Curl_pp_statemach](r12-pingpong-transport.md#u-673b0f00a073)

<a id="u-0ca3823bae6a"></a>
### `lib-smtp.c-transfer-wrap`

`static CURLcode smtp_dophase_done(struct Curl_easy *data, struct SMTP *smtp, bool con…` · [lib/smtp.c:L1819-L1830][f2]

Wrappers around the DO phase.

smtp_dophase_done only reconfigures the transfer: when the transfer type is not PPTRANSFER_BODY it installs a no-op transfer setup, and always returns CURLE_OK. smtp_regular_transfer resets data->req.size to unknown and the progress data, runs smtp_perform, and when it succeeded and the DO phase finished calls smtp_dophase_done; any error or the done flag is propagated to the caller.

calls: [smtp_perform](r7-smtp-protocol.md#u-98228cbbc7e4)

<a id="u-d605a2dcf9ea"></a>
### `cr_eob_read`

`static CURLcode cr_eob_read(struct Curl_easy *data, struct Curl_creader *reader, char…` · [lib/smtp.c:L343-L444][f2]

Client-reader read callback that dot-stuffs the outgoing body so a lone '.' line cannot terminate the message early.

While its buffer is empty and EOS has not been seen, it pulls data from the next reader: if not mid-match and the first EOB byte ('\r') is absent, the data passes through untouched; otherwise it scans tracking how many bytes of '\r\n.\r\n' matched (match length 3), and on completing the 3-byte prefix writes the buffered span plus an extra '.' into the 16 KiB soft-limited bufq, incrementing data->state.infilesize when positive so SIZE stays accurate. Once, when EOS arrives, it appends the terminator per match state: after CRLF append '.\r\n', after '\r\n.' append '.\r\n.\r\n' (escaping the final dot), otherwise the full '\r\n.\r\n'. Output is drained from the bufq; *peos becomes TRUE only after EOS was seen and the buffer is exhausted. Errors from the next reader and bufq operations propagate immediately.

**Notes.**

- side_effect: infilesize grows by one per inserted dot to keep the announced SIZE consistent with the escaped body.

calls: [Curl_creader_read](r4-client-reader-stack.md#u-ddcfbe6e63b5), [Curl_bufq_cwrite](r15-bufq-stream-api.md#u-1b21945c00e1), [Curl_bufq_cread](r15-bufq-stream-api.md#u-421bf7a71d29)

**Uncertainties.**

- Whether the partial-prefix handling reproduces exact RFC 5321 dot-stuffing for inputs that begin the EOB prefix but never complete it cannot be proven from this function alone.

<a id="u-625550bc49ec"></a>
### `smtp_connect`

`static CURLcode smtp_connect(struct Curl_easy *data, bool *done)` · [lib/smtp.c:L1672-L1706][f2]

Protocol connect phase: wires up the pingpong layer and SASL, parses URL parameters, and begins waiting for the server greeting.

It sets *done FALSE, fails with CURLE_FAILED_INIT without a connection meta, registers smtp_pp_statemachine and smtp_endofresp via PINGPONG_SETUP, initializes SASL with the saslsmtp parameters, initializes the pingpong layer with a progress timestamp, then parses URL options and path (each error returned immediately, before the greeting wait), sets the state to SMTP_SERVERGREET, and finally runs smtp_multi_statemach, returning its result and done flag.

calls: [smtp_parse_url_options](r7-smtp-protocol.md#u-5e963040eb89), [smtp_parse_url_path](r7-smtp-protocol.md#u-5f94f23b6b84), [lib-smtp.c-statemach-drivers](r7-smtp-protocol.md#u-f96fe8e03e81)

<a id="u-82a859e74b1d"></a>
### `smtp_disconnect`

`static CURLcode smtp_disconnect(struct Curl_easy *data, struct connectdata *conn, boo…` · [lib/smtp.c:L1906-L1926][f2]

Disconnects an SMTP connection, sending QUIT only when it is safe to wait.

Missing connection meta returns CURLE_FAILED_INIT; otherwise QUIT is sent and awaited (blocking statemach, ignoring its result) only when the connection is not dead, the protocol connect started, and no pingpong send is pending — the comment notes waiting on a stale connection would block in vain. The function always returns CURLE_OK regardless of the QUIT outcome.

calls: [lib-smtp.c-command-senders](r7-smtp-protocol.md#u-0f5be6cb436f)

<a id="u-9395e9a208dd"></a>
### `smtp_do`

`static CURLcode smtp_do(struct Curl_easy *data, bool *done)` · [lib/smtp.c:L1876-L1897][f2]

Registered do_it handler: parses the custom request, then runs the regular transfer.

Missing connection or easy meta returns CURLE_FAILED_INIT before any work; smtp_parse_custom_request errors are returned directly. Otherwise it runs smtp_regular_transfer, whose done output becomes *done, and returns the result.

calls: [smtp_parse_custom_request](r7-smtp-protocol.md#u-9d90a51b39b3), [lib-smtp.c-transfer-wrap](r7-smtp-protocol.md#u-0ca3823bae6a)

<a id="u-5551bf5cce97"></a>
### `smtp_doing`

`static CURLcode smtp_doing(struct Curl_easy *data, bool *dophase_done)` · [lib/smtp.c:L1929-L1948][f2]

Multi-interface DOING callback: continues the protocol state machine and finalizes the DO phase.

Missing easy meta returns CURLE_FAILED_INIT. It runs smtp_multi_statemach; on error it logs the failure, and when the DO phase is done it calls smtp_dophase_done (with connected=FALSE, as the socket is already connected) and logs completion.

calls: [lib-smtp.c-statemach-drivers](r7-smtp-protocol.md#u-f96fe8e03e81)

<a id="u-6d545444d610"></a>
### `smtp_done`

`static CURLcode smtp_done(struct Curl_easy *data, CURLcode status, bool premature)` · [lib/smtp.c:L1717-L1755][f2]

DONE phase: cleans the per-request state and, for mail uploads, waits for the server's final reply.

Missing connection meta returns CURLE_FAILED_INIT; missing easy meta returns CURLE_OK. It frees smtp->custom; a non-OK status marks the connection for closure and returns that status unchanged. Otherwise, when not connect_only, a mail recipient is set, and the transfer was an upload or MIME post, it sets the state to SMTP_POSTDATA and runs the blocking state machine to collect the final response. Finally it resets smtp->transfer to PPTRANSFER_BODY for the next request.

**Notes.**

- side_effect: A bad status marks the connection to be closed after this request.

calls: [lib-smtp.c-statemach-drivers](r7-smtp-protocol.md#u-f96fe8e03e81)

<a id="u-25c28e037e9a"></a>
### `smtp_endofresp`

`static bool smtp_endofresp(struct Curl_easy *data, struct connectdata *conn, const ch…` · [lib/smtp.c:L491-L533][f2]

Pingpong callback deciding whether a received line terminates an SMTP reply and extracting its status code.

Lines shorter than 4 bytes or not starting with three digits are not a response. A line whose fourth character is a space, or a 5-byte line (lenient servers appending a fifth digit), is terminal: the digits are parsed via curlx_str_number (max 999 or 99999 by length); a parse failure reverts to 'not ended', and a parsed code of 1 — the internal multiline sentinel — is remapped to 0 so real servers cannot inject it. A '-' as the fourth character ends a multiline reply only while the state is SMTP_EHLO or SMTP_COMMAND, reporting the internal code 1. A missing smtp_conn meta yields FALSE after a debug assert.

**Notes.**

- condition: Code 1 is reserved for multiline continuations and is coerced to 0 when a server sends it literally.

calls: [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

<a id="u-b0a8aaf8c864"></a>
### `smtp_get_message`

`static CURLcode smtp_get_message(struct Curl_easy *data, struct bufref *out)` · [lib/smtp.c:L541-L573][f2]

Extracts the SASL challenge/message text from the pingpong receive buffer into a bufref.

It points at the pp.recvbuf contents, uses pp.nfinal as its length, and for lengths over 4 skips the four status bytes plus blanks, trims trailing newlines/blanks, NUL-terminates, and sets the bufref to the message with no destructor. Lengths of 4 or less yield a zero-length empty message. A missing smtp_conn meta returns CURLE_FAILED_INIT.

calls: [Curl_bufref_set](r14-bufref-buffers.md#u-214d3ce6e368)

<a id="u-21687da44544"></a>
### `smtp_parse_address`

`static CURLcode smtp_parse_address(struct Curl_easy *data, const char *fqma, char **a…` · [lib/smtp.c:L252-L306][f2]

Splits a fully qualified mailbox into local address, hostname, and trailing suffix, guarding against SMTP command injection.

An address containing CR or LF is rejected up front with CURLE_BAD_FUNCTION_ARGUMENT and a failf, preventing command smuggling into MAIL FROM/RCPT TO lines. Input wrapped in '<...>' is unwrapped: a leading '<' is skipped; when the input starts with '<' the last '>' ends the address and anything after it becomes *suffix, while an unwrapped trailing '>' is merely trimmed. If an '@' exists, everything after it becomes host->name and Curl_idnconvert_hostname is attempted; its failure is deliberately ignored so a UTF-8 U-label can be sent when ACE conversion is unavailable. With no '@', the whole input is the address and host->name stays NULL. The caller frees *address and must release the hostname's IDN conversion.

**Notes.**

- failure: IDN conversion failure is ignored on purpose; the address is then sent as UTF-8 rather than ACE.

calls: [Curl_idnconvert_hostname](r7-idn-hostnames.md#u-50af72aa294f)

<a id="u-9d90a51b39b3"></a>
### `smtp_parse_custom_request`

`static CURLcode smtp_parse_custom_request(struct Curl_easy *data, struct SMTP *smtp)` · [lib/smtp.c:L206-L217][f2]

Reads the easy handle's custom request string and stores a URL-decoded copy in smtp->custom.

If no custom request is set the field stays NULL and CURLE_OK is returned; decoding rejects control characters and propagates Curl_urldecode's result including allocation failures.

calls: [Curl_urldecode](r7-string-escape-utils.md#u-0db7582a0fb5)

<a id="u-5e963040eb89"></a>
### `smtp_parse_url_options`

`static CURLcode smtp_parse_url_options(struct connectdata *conn, struct smtp_conn *sm…` · [lib/smtp.c:L144-L173][f2]

Parses the connection URL's login options into SASL settings for the SMTP connection.

It walks conn->options as a semicolon-separated key=value list: for each item it locates '=' and the next ';', and only when the key equals 'AUTH=' passes the value to Curl_sasl_parse_url_auth_option; any other key returns CURLE_URL_MALFORMAT immediately, ending the loop. An empty or missing options string leaves SASL state untouched and returns CURLE_OK.

calls: [Curl_sasl_parse_url_auth_option](r15-sasl-auth.md#u-cb93315649c7), [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

<a id="u-5f94f23b6b84"></a>
### `smtp_parse_url_path`

`static CURLcode smtp_parse_url_path(struct Curl_easy *data, struct smtp_conn *smtpc)` · [lib/smtp.c:L181-L198][f2]

Derives the EHLO client domain from the URL path and stores a decoded copy in smtpc->domain.

When the path (after the leading slash) is empty, it uses the local hostname via Curl_gethostname, falling back to the literal 'localhost' on failure; otherwise the URL path is the domain. In all cases the chosen string is URL-decoded by Curl_urldecode with control characters rejected (REJECT_CTRL), and the function returns that decode result. smtpc->domain is later freed by the connection dtor.

calls: [Curl_gethostname](r10-misc-utilities.md#u-cd704092da51), [Curl_urldecode](r7-string-escape-utils.md#u-0db7582a0fb5)

<a id="u-98228cbbc7e4"></a>
### `smtp_perform`

`static CURLcode smtp_perform(struct Curl_easy *data, struct smtp_conn *smtpc, struct …` · [lib/smtp.c:L1764-L1816][f2]

DO phase: chooses and sends the first SMTP command, then starts the non-blocking state machine.

A no-body request sets the transfer type to PPTRANSFER_INFO (no data). It stores the recipient list, resets rcpt_had_ok and rcpt_last_error, and sets trailing_crlf/eob to 2 because the first data byte is implicitly preceded by CRLF. If uploading or a MIME post with a mail recipient it sends MAIL via smtp_perform_mail, otherwise a command via smtp_perform_command. Send errors skip straight to the exit log; on success it runs smtp_multi_statemach (whose done flag becomes *dophase_done) and reports connection state via Curl_conn_is_connected.

calls: [smtp_perform_mail](r7-smtp-protocol.md#u-33c7d71179b1), [smtp_perform_command](r7-smtp-protocol.md#u-bdef81c8f8db), [lib-smtp.c-statemach-drivers](r7-smtp-protocol.md#u-f96fe8e03e81)

<a id="u-4b94e179a399"></a>
### `smtp_perform_authentication`

`static CURLcode smtp_perform_authentication(struct Curl_easy *data, struct smtp_conn …` · [lib/smtp.c:L800-L825][f2]

Starts the SASL authentication sequence during connect.

If the server did not advertise AUTH or there are no usable credentials (Curl_sasl_can_authenticate), the state moves to SMTP_STOP and CURLE_OK is returned, silently ending the connect phase. Otherwise Curl_sasl_start picks and starts a mechanism; SASL_INPROGRESS moves the state to SMTP_AUTH, while any other progress makes the result Curl_sasl_is_blocked's return. Curl_sasl_start errors propagate.

calls: [Curl_sasl_start](r15-sasl-auth.md#u-a9fa97d48489)

<a id="u-bdef81c8f8db"></a>
### `smtp_perform_command`

`static CURLcode smtp_perform_command(struct Curl_easy *data, struct smtp_conn *smtpc,…` · [lib/smtp.c:L833-L898][f2]

Sends the DO-phase command: VRFY/EXPN with a recipient, or a recipient-less custom command.

With a recipient and no custom request, it parses the mailbox via smtp_parse_address (propagating its CR/LF rejection), decides utf8 as utf8_supported AND (IDN-allocated OR non-ASCII address OR non-ASCII host), sends 'VRFY <address>[@<host>][ SMTPUTF8]', then frees the IDN conversion and address. With a recipient and a custom request, utf8 is utf8_supported AND custom == 'EXPN', and it sends '<custom> <rcpt>[ SMTPUTF8]' using the raw recipient string. With no recipient it sends the custom request, or 'HELP' when custom is empty/absent. On send success the state moves to SMTP_COMMAND; send errors propagate.

calls: [smtp_parse_address](r7-smtp-protocol.md#u-21687da44544), [Curl_is_ASCII_name](r7-idn-hostnames.md#u-03214be67f22)

<a id="u-33c7d71179b1"></a>
### `smtp_perform_mail`

`static CURLcode smtp_perform_mail(struct Curl_easy *data, struct smtp_conn *smtpc, st…` · [lib/smtp.c:L906-L1086][f2]

Builds and sends the MAIL FROM command that starts a message upload, including optional AUTH, SIZE, and SMTPUTF8 parameters, and installs the body client reader.

The FROM address is parsed via smtp_parse_address (CR/LF rejection propagates); with a hostname it formats '<local@host><suffix>', otherwise '<local><suffix>' leaving rejection to the server. A missing FROM string yields the null reverse-path '<>'. When MAIL_AUTH is set and a SASL mechanism was used, the AUTH mailbox is parsed similarly (empty string becomes '<>' per RFC-2554). For MIME posts it attaches headers, adds 'Mime-Version: 1.0' when absent, switches the reader to the mime part and records its length as infilesize; otherwise it switches to fread with the current infilesize. If the server supports SIZE and infilesize is positive a SIZE parameter is added. If FROM/AUTH were all-ASCII, the recipient list is scanned for non-ASCII addresses to decide SMTPUTF8. It then adds the EOB-escaping reader via cr_eob_add and sends 'MAIL FROM:...' with the assembled parameters. All temporary strings are freed on the out path; on success the state moves to SMTP_MAIL. Any parse, mime, reader, or allocation failure aborts before sending.

**Notes.**

- side_effect: Replaces the client reader (mime or fread) and may update data->state.infilesize before DATA.

calls: [smtp_parse_address](r7-smtp-protocol.md#u-21687da44544), [lib-smtp.c-cr-eob-reader](r7-smtp-protocol.md#u-c3f1632b62b1), [Curl_creader_set_mime](r2-mime-creader.md#u-5dd9c38db7b0)

**Uncertainties.**

- Exact interaction of Curl_creader_set_mime/set_fread with prior readers is defined in sendf.c/mime.c, outside this file.

<a id="u-62bd7e131da9"></a>
### `smtp_perform_rcpt_to`

`static CURLcode smtp_perform_rcpt_to(struct Curl_easy *data, struct smtp_conn *smtpc,…` · [lib/smtp.c:L1095-L1128][f2]

Sends the RCPT TO command for the current recipient (smtp->rcpt->data).

The mailbox is parsed with smtp_parse_address (its CR/LF rejection and errors propagate). With a hostname it sends 'RCPT TO:<local@host><suffix>'; without one it sends 'RCPT TO:<local><suffix>', leaving the invalid mailbox for the server to reject with 501. It frees the IDN conversion and address, and on send success moves the state to SMTP_RCPT.

calls: [smtp_parse_address](r7-smtp-protocol.md#u-21687da44544)

<a id="u-a7c725409d74"></a>
### `smtp_perform_upgrade_tls`

`static CURLcode smtp_perform_upgrade_tls(struct Curl_easy *data, struct smtp_conn *sm…` · [lib/smtp.c:L688-L723][f2]

Drives the asynchronous TLS upgrade after STARTTLS.

Only built with USE_SSL; otherwise it returns CURLE_NOT_BUILT_IN. If the first socket is not yet SSL, it adds an SSL connection filter on the origin connection and switches conn->scheme to Curl_scheme_smtps; a filter-add failure aborts. It then runs Curl_conn_connect non-blocking; when the handshake completes (ssldone) it records ssldone on smtpc and immediately performs EHLO, which moves the state out of SMTP_UPGRADETLS. While the handshake is still in progress the state remains SMTP_UPGRADETLS and the result is CURLE_OK with the upgrade unfinished.

calls: [lib-smtp.c-command-senders](r7-smtp-protocol.md#u-0f5be6cb436f)

**Uncertainties.**

- The behavior of Curl_ssl_cfilter_add and Curl_conn_connect (progress/completion semantics) is external to this file.

<a id="u-4a2309575d12"></a>
### `smtp_pp_statemachine`

`static CURLcode smtp_pp_statemachine(struct Curl_easy *data, struct connectdata *conn)` · [lib/smtp.c:L1513-L1609][f2]

Core SMTP protocol state machine, driven by the pingpong layer until no more data or the state stops.

Missing connection or easy meta returns CURLE_FAILED_INIT. If the state is SMTP_UPGRADETLS it first runs smtp_perform_upgrade_tls and returns while the upgrade is unfinished or errored; if send data is still pending it returns Curl_pp_flushsend's result. It then loops reading complete responses via Curl_pp_readresp (errors propagate), storing the code in data->info.httpcode except during QUIT or for internal code 1, breaking on code 0, and dispatching to the per-state handler for SERVERGREET/EHLO/HELO/STARTTLS/AUTH/COMMAND/MAIL/RCPT/DATA/POSTDATA; STARTTLS success that enters UPGRADETLS jumps back to the upgrade step before reading more; QUIT or unknown states fall back to SMTP_STOP. The loop continues while no error, state is not SMTP_STOP, and pingpong data remains.

calls: [lib-smtp.c-response-handlers](r7-smtp-protocol.md#u-e8493922da20), [Curl_pp_readresp](r12-pingpong-transport.md#u-f696034e55f0), [smtp_perform_upgrade_tls](r7-smtp-protocol.md#u-a7c725409d74)

<a id="u-4b2692967d7e"></a>
### `smtp_state`

`static void smtp_state(struct Curl_easy *data, struct smtp_conn *smtpc, smtpstate new…` · [lib/smtp.c:L581-L612][f2]

The single sanctioned way to change the SMTP connection state, assigning newstate to smtpc->state.

Under CURLVERBOSE it logs transitions between state names via a static name table when the state actually changes; otherwise data is unused. No validation of the new state is performed.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/pingpong.h
[f2]: ../../../../../../eval/curl-2c04412/lib/smtp.c
