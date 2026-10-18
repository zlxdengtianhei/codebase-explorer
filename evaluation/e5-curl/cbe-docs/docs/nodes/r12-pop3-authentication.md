# POP3 authentication

**Capability.** Negotiates POP3 logins: URL login options, fallback ordering across SASL, APOP (MD5 timestamp digest), and clear-text USER/PASS, with per-mechanism response handlers.

Consult for any change to login behavior or mechanism selection. APOP depends on the MD5 digest module for its timestamp-plus-password hash.

**Depends on.**

- [MD5 digest service](r12-md5-digest.md) · graph-confirmed · 4 edge(s) · POP3 APOP authentication computes its timestamp-plus-password digest with the MD5 service.

Parent: [POP3 client](r12-pop3-client.md)

## Units (11)

<a id="u-380ef274f681"></a>
### `pop3_parse_url_options`

`static CURLcode pop3_parse_url_options(struct connectdata *conn)` · [lib/pop3.c:L171-L223][f1]

Parses the URL login options string into the connection's authentication preference.

Iterates conn->options split on ';', each token as key=value. Any key other than 'AUTH=' (case-insensitive 5-char compare) yields CURLE_URL_MALFORMAT. For AUTH=, the value goes to Curl_sasl_parse_url_auth_option; if that fails but the value is exactly '+APOP', the preference becomes POP3_TYPE_APOP, the SASL preferred mechanism resets to SASL_AUTH_NONE, and the error is cleared. After parsing, unless APOP was chosen, the SASL preferred mechanism maps to a preference: SASL_AUTH_NONE to POP3_TYPE_NONE, SASL_AUTH_DEFAULT to POP3_TYPE_ANY, anything else to POP3_TYPE_SASL. Missing connection meta returns CURLE_FAILED_INIT; the loop stops on the first error but the final preftype mapping still runs.

calls: [Curl_sasl_parse_url_auth_option](r15-sasl-auth.md#u-cb93315649c7)

**Uncertainties.**

- After an error the trailing preftype mapping executes on a partially updated sasl struct; the resulting preference in that case is not pinned by the source

<a id="u-ea6cae735793"></a>
### `pop3_perform_authentication`

`static CURLcode pop3_perform_authentication(struct Curl_easy *data, struct connectdat…` · [lib/pop3.c:L679-L719][f1]

Chooses and starts the authentication sequence with a fallback order.

Without authenticatable credentials it moves to POP3_STOP and returns OK. When both sides accept SASL it runs Curl_sasl_start; a SASL_INPROGRESS result moves to POP3_AUTH. If SASL was not chosen or made no progress, it falls back to APOP when both sides allow it, then to clear-text USER, and finally returns Curl_sasl_is_blocked's result. Missing meta returns CURLE_FAILED_INIT.

calls: [Curl_sasl_start](r15-sasl-auth.md#u-a9fa97d48489), [pop3_perform_apop](r12-pop3-authentication.md#u-35e3ed4ec08e), [pop3_perform_user](r12-pop3-authentication.md#u-6ab638c0a8dc)

<a id="u-35e3ed4ec08e"></a>
### `pop3_perform_apop`

`static CURLcode pop3_perform_apop(struct Curl_easy *data, struct connectdata *conn)` · [lib/pop3.c:L552-L598][f1]

Sends APOP authentication: MD5 of the server's APOP timestamp concatenated with the password, hex-encoded, sent as 'APOP <user> <digest>'.

With no credentials it moves to POP3_STOP and returns OK. MD5 context allocation failure returns CURLE_OUT_OF_MEMORY. On send success it transitions to POP3_APOP. Compiled out when digest auth is disabled.

calls: [Curl_MD5_final](r12-md5-digest.md#u-fabda254dcb3)

**Uncertainties.**

- pop3c->apoptimestamp is dereferenced without a null check here; a missing timestamp would be a programming error established elsewhere

<a id="u-eb6fe0a5e8f6"></a>
### `pop3_perform_auth`

`static CURLcode pop3_perform_auth(struct Curl_easy *data, const char *mech, const str…` · [lib/pop3.c:L608-L631][f1]

Sends the SASL AUTH command for a mechanism.

With a non-empty initial response it sends 'AUTH <mech> <ir>', substituting '=' when the initial response is the empty string (a POP3 convention); without one it sends 'AUTH <mech>'. Does not change state itself — the SASL layer drives transitions. Missing meta returns CURLE_FAILED_INIT.

<a id="u-6ab638c0a8dc"></a>
### `pop3_perform_user`

`static CURLcode pop3_perform_user(struct Curl_easy *data, struct connectdata *conn)` · [lib/pop3.c:L519-L543][f1]

Sends clear-text USER authentication.

If no credentials exist it ends the connect phase by moving to POP3_STOP and returns CURLE_OK; otherwise it sends 'USER <user>' and, on success, transitions to POP3_USER. Missing meta returns CURLE_FAILED_INIT.

<a id="u-9dfd08dda887"></a>
### `pop3_cancel_auth`

`static CURLcode pop3_cancel_auth(struct Curl_easy *data, const char *mech)` · [lib/pop3.c:L659-L669][f1]

Sends '*' to cancel an in-progress SASL authentication; the mech argument is unused.

Missing meta returns CURLE_FAILED_INIT, otherwise the send result.

<a id="u-d04d44ddb690"></a>
### `pop3_continue_auth`

`static CURLcode pop3_continue_auth(struct Curl_easy *data, const char *mech, const st…` · [lib/pop3.c:L639-L651][f1]

Sends one line of SASL continuation data (the bufref payload) during an exchange; the mech argument is unused.

Missing meta returns CURLE_FAILED_INIT, otherwise the send result.

<a id="u-60821fe220cd"></a>
### `pop3_state_user_resp`

`static CURLcode pop3_state_user_resp(struct Curl_easy *data, int pop3code, pop3state …` · [lib/pop3.c:L1025-L1048][f1]

Handles the USER reply.

A non-'+' code fails with CURLE_LOGIN_DENIED; on success it sends 'PASS <password>'. In both cases, whenever no error accumulated, the state moves to POP3_PASS — including after a failed PASS send. Missing meta returns CURLE_FAILED_INIT.

**Uncertainties.**

- The unconditional transition to POP3_PASS after a failed send means the error is reported while the state already advanced

<a id="u-c5b5c66c3d64"></a>
### `pop3_state_pass_resp`

`static CURLcode pop3_state_pass_resp(struct Curl_easy *data, int pop3code, pop3state …` · [lib/pop3.c:L1051-L1066][f1]

Handles the PASS reply: a non-'+' code fails with CURLE_LOGIN_DENIED, '+' ends the connect phase by moving to POP3_STOP.

<a id="u-00dc6ff5ccf8"></a>
### `pop3_state_apop_resp`

`static CURLcode pop3_state_apop_resp(struct Curl_easy *data, int pop3code, pop3state …` · [lib/pop3.c:L1006-L1021][f1]

Handles the APOP reply: a non-'+' code fails with CURLE_LOGIN_DENIED, while '+' ends the connect phase by moving to POP3_STOP.

Does not need connection meta, so it never fails on missing state.

<a id="u-040335c8737a"></a>
### `pop3_state_auth_resp`

`static CURLcode pop3_state_auth_resp(struct Curl_easy *data, int pop3code, pop3state …` · [lib/pop3.c:L963-L1002][f1]

Handles SASL authentication responses by delegating to Curl_sasl_continue with the POP3 code.

On SASL_DONE it moves to POP3_STOP (authenticated). On SASL_IDLE — no mechanism left, e.g. after cancellation — it falls back to APOP then clear-text USER, and if neither is available fails with CURLE_LOGIN_DENIED after 'Authentication cancelled'. Other progress values leave the state as the SASL layer set it. Missing meta returns CURLE_FAILED_INIT.

calls: [Curl_sasl_continue](r15-sasl-auth.md#u-d687179d440b), [pop3_perform_apop](r12-pop3-authentication.md#u-35e3ed4ec08e)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/pop3.c
