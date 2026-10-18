# IMAP authentication and TLS upgrade

**Capability.** Chooses and drives the authentication path: SASL AUTHENTICATE with or without initial response, plaintext LOGIN fallback, STARTTLS negotiation and the non-blocking TLS upgrade, plus SASL continuation/cancellation callbacks and challenge extraction.

This subtree bridges IMAP to the generic SASL engine: imap_perform_authentication calls Curl_sasl_start, and the AUTH/STARTTLS response handlers feed server replies back into SASL. LOGIN is the non-SASL fallback.

**Depends on.**

- [IMAP core, types and framing](r15-imap-core.md) · graph-confirmed · 13 edge(s)
- [Generic SASL authentication](r15-sasl-auth.md) · graph-confirmed · 4 edge(s)

**Depended on by.**

- [IMAP response handlers](r15-imap-resp-handlers.md) · graph-confirmed · 6 edge(s)

Parent: [IMAP protocol implementation](r15-imap-protocol.md)

## Units (10)

<a id="u-5a4e54eb6478"></a>
### `imap_perform_authenticate`

`static CURLcode imap_perform_authenticate(struct Curl_easy *data, const char *mech, c…` · [lib/imap.c:L616-L638][f1]

Sends the SASL AUTHENTICATE command for the given mechanism, with or without an initial response.

It returns CURLE_FAILED_INIT if per-connection IMAP data is missing. When initresp holds a non-empty initial response it sends "AUTHENTICATE mech ir"; an empty initial response is sent as "=" per the SASL-IR convention. Without an initial response it sends "AUTHENTICATE mech". Only send errors are returned; state is managed by the SASL layer through the statemachine.

calls: [imap_sendf](r15-imap-core.md#u-63898d847813)

<a id="u-efaa09f5691c"></a>
### `imap_perform_authentication`

`static CURLcode imap_perform_authentication(struct Curl_easy *data, struct imap_conn …` · [lib/imap.c:L685-L713][f1]

Chooses and starts the authentication path for the connection.

If the connection is already PREAUTH or SASL has no usable credentials, it moves to IMAP_STOP and ends the connect phase successfully. Otherwise Curl_sasl_start picks a mechanism (allowing initial response when ir_supported is set): progress SASL_INPROGRESS moves the state to IMAP_AUTHENTICATE; when SASL could not start and cleartext is allowed (login not disabled and preftype includes IMAP_TYPE_CLEARTEXT) it falls back to imap_perform_login; the remaining case defers to Curl_sasl_is_blocked, whose result is propagated. Errors from the SASL start are returned unchanged.

calls: [Curl_sasl_start](r15-sasl-auth.md#u-a9fa97d48489), [imap_perform_login](r15-imap-auth.md#u-ec4f68dcd86a)

**Uncertainties.**

- The exact outcome of Curl_sasl_is_blocked (error vs. silent stop) is external to this file.

<a id="u-ec4f68dcd86a"></a>
### `imap_perform_login`

`static CURLcode imap_perform_login(struct Curl_easy *data, struct imap_conn *imapc, s…` · [lib/imap.c:L575-L607][f1]

Sends a plaintext LOGIN command, or silently ends the connect phase when no credentials exist.

With conn->creds absent it moves to IMAP_STOP and returns CURLE_OK. Otherwise the username and password are atom-quoted with imap_atom (escape_only false), NULL atoms are sent as empty strings, and "LOGIN user passwd" is transmitted; on success the state moves to IMAP_LOGIN. The password buffer is wiped via curlx_strzero before being freed regardless of send outcome.

calls: [imap_atom](r15-imap-core.md#u-7f2ff3b2f5ba), [imap_sendf](r15-imap-core.md#u-63898d847813)

**Uncertainties.**

- Whether imap_atom failure (NULL) is distinguished from an empty credential is not handled here: both send as empty strings.

<a id="u-2dc16fc7c7b1"></a>
### `imap_perform_starttls`

`static CURLcode imap_perform_starttls(struct Curl_easy *data, struct imap_conn *imapc)` · [lib/imap.c:L514-L524][f1]

Sends the STARTTLS command and, on success, moves to IMAP_STARTTLS to await the server's tagged reply.

A send failure propagates and leaves the state unchanged.

calls: [imap_sendf](r15-imap-core.md#u-63898d847813)

<a id="u-238bba4bb07d"></a>
### `imap_perform_upgrade_tls`

`static CURLcode imap_perform_upgrade_tls(struct Curl_easy *data, struct imap_conn *im…` · [lib/imap.c:L532-L567][f1]

Performs the TLS upgrade on the connection, in multi (non-blocking) style.

Compiled only with USE_SSL; without SSL support it always returns CURLE_NOT_BUILT_IN. If the first socket is not already SSL it adds the SSL connection filter, switching conn->scheme to imaps, and aborts with that error if filter addition fails. It then runs Curl_conn_connect non-blocking: only when the connect succeeded and ssldone became true does it mark imapc->ssldone and immediately issue CAPABILITY via imap_perform_capability, which advances the state out of IMAP_UPGRADETLS. While the handshake is still running the function returns CURLE_OK with state left in IMAP_UPGRADETLS so callers retry.

calls: [imap_perform_capability](r15-imap-commands.md#u-7f3fe5078b59)

**Uncertainties.**

- Behavior of Curl_conn_connect and filter addition comes from unproven external boundaries; only the state and return handling is evidenced here.

<a id="u-3bab78f9d647"></a>
### `imap_cancel_authenticate`

`static CURLcode imap_cancel_authenticate(struct Curl_easy *data, const char *mech)` · [lib/imap.c:L665-L675][f1]

Cancels an in-progress SASL authentication by sending the literal "*" line.

Missing per-connection data yields CURLE_FAILED_INIT; otherwise the pingpong send result is returned and the mechanism name is ignored.

calls: [Curl_pp_vsendf](r12-pingpong-transport.md#u-38c5e1d73b67)

<a id="u-1db25d2f5704"></a>
### `imap_continue_authenticate`

`static CURLcode imap_continue_authenticate(struct Curl_easy *data, const char *mech, …` · [lib/imap.c:L646-L657][f1]

Sends one line of SASL continuation data on the pingpong channel.

The mechanism name is ignored; if per-connection IMAP data is missing it returns CURLE_FAILED_INIT, otherwise it forwards the bufref payload verbatim through Curl_pp_sendf and propagates the send result.

calls: [Curl_pp_vsendf](r12-pingpong-transport.md#u-38c5e1d73b67)

<a id="u-7dce9819dfbf"></a>
### `imap_get_message`

`static CURLcode imap_get_message(struct Curl_easy *data, struct bufref *out)` · [lib/imap.c:L409-L441][f1]

Extracts the SASL challenge or message text from the received response line into a bufref.

It returns CURLE_FAILED_INIT if the per-connection IMAP data is missing. Otherwise it takes the pingpong receive buffer, drops the final two bytes (typically CRLF) when more than two bytes remain, skips leading blanks after the first two characters, trims trailing newlines and blanks, NUL-terminates in place, and stores the message pointer and length in out with no allocator (NULL free function). Input of two bytes or fewer yields a zero-length output string instead.

calls: [Curl_bufref_set](r14-bufref-buffers.md#u-214d3ce6e368)

<a id="u-7835814425bb"></a>
### `imap_state_auth_resp`

`static CURLcode imap_state_auth_resp(struct Curl_easy *data, struct imap_conn *imapc,…` · [lib/imap.c:L1114-L1144][f1]

Advances SASL authentication by feeding the tagged response code to Curl_sasl_continue.

On SASL_DONE the state moves to IMAP_STOP, completing authentication. On SASL_IDLE, meaning no mechanism remains after cancellation, it falls back to plaintext login when allowed (login not disabled and cleartext preftype), otherwise fails with CURLE_LOGIN_DENIED after logging 'Authentication cancelled'. Other progress values and SASL-layer errors are propagated unchanged.

uses: [function::Curl_sasl_continue::15414][f2]; calls: [imap_perform_login](r15-imap-auth.md#u-ec4f68dcd86a)

<a id="u-6592d5d6c993"></a>
### `imap_state_starttls_resp`

`static CURLcode imap_state_starttls_resp(struct Curl_easy *data, struct imap_conn *im…` · [lib/imap.c:L1086-L1111][f1]

Handles the tagged reply to STARTTLS.

Any pipelined data already buffered behind the reply (pp.overflow) is rejected outright with CURLE_WEIRD_SERVER_REPLY. A non-OK reply fails with CURLE_USE_SSL_FAILED and 'STARTTLS denied' unless use_ssl is CURLUSESSL_TRY, in which case authentication proceeds in plaintext via imap_perform_authentication. An OK reply moves the state to IMAP_UPGRADETLS so the statemachine performs the TLS handshake next.

calls: [imap_perform_authentication](r15-imap-auth.md#u-efaa09f5691c), [imap_state](r15-imap-core.md#u-648840e562ec)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/imap.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curl_sasl.c
