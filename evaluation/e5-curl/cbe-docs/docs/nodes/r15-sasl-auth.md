# Generic SASL authentication

**Capability.** Protocol-independent SASL engine: mechanism table decoding, URL auth-option parsing, per-connection init, the sasl_choose_* mechanism chooser family, start/continue state machine, message encode/decode helpers, and diagnostics.

Protocols call Curl_sasl_init at connect and Curl_sasl_start/continue to drive authentication; Curl_sasl_can_authenticate and Curl_sasl_is_blocked act as gates. Mechanism selection is isolated in the chooser family.

**Depended on by.**

- [IMAP authentication and TLS upgrade](r15-imap-auth.md) · graph-confirmed · 4 edge(s)
- [IMAP commands and URL parsing](r15-imap-commands.md) · graph-confirmed · 1 edge(s)
- [IMAP response handlers](r15-imap-resp-handlers.md) · graph-confirmed · 1 edge(s)

Parent: [curl codebase](r15-curl-codebase.md)

## Units (12)

<a id="u-a6cb78154ebb"></a>
### `curl-sasl.c-mechanism-choosers`

`struct sasl_ctx` · [lib/curl_sasl.c:L287-L296][f1]

A family of sasl_choose_* helpers that, given an sasl_ctx with enabledmechs (offered ∩ preferred mechanisms), test whether one specific mechanism is selectable and, if so, fill the context with the mechanism string, the state-machine entry states, mark sasl->authused, and optionally build an initial response when sasl->force_ir or data->set.sasl_ir is set.

Each returns TRUE only when it 'owns' the selection (even on failure, e.g. gsasl allocation failure sets sctx->result = CURLE_OUT_OF_MEMORY and returns TRUE), letting Curl_sasl_start try candidates in security order via short-circuit OR.

**Notes.**

- condition: Per-mechanism gate conditions: EXTERNAL requires creds without a password; GSSAPI requires Kerberos5 support and a user containing a domain; SCRAM requires libgsasl and per-mechanism support; DIGEST-MD5 requires digest support (falling back to CRAM-MD5); NTLM requires NTLM support; OAUTHBEARER/XOAUTH2 require oauth bearer creds in data->state.creds or conn->creds respectively; PLAIN and LOGIN have no extra gate.
- side_effect: Each chosen helper mutates sctx->mech/state1/state2/resp/result and sasl->authused; krb5 also clears sasl->mutual_auth to FALSE.

calls: [Curl_auth_is_digest_supported](r9-digest-core.md#u-f7e818c075b5), [Curl_conn_get_current_host](r8-cfilters-events-state.md#u-fd2ae9056973)

**Uncertainties.**

- Compile-time variants (USE_KERBEROS5, USE_GSASL, USE_NTLM, digest enabled) change which helpers exist, so the selection order differs per build.

<a id="u-8325e3b05815"></a>
### `Curl_sasl_init`

`void Curl_sasl_init(struct SASL *sasl, struct Curl_easy *data, const struct SASLproto…` · [lib/curl_sasl.c:L142-L176][f1]

Initializes a per-connection SASL state machine from protocol parameters and transfer settings.

It stores params, sets state to SASL_STOP, clears curmech/authmechs/authused, takes prefmech from params->defmechs, and clears resetprefs (set TRUE), mutual_auth and force_ir. If data->set.httpauth equals exactly CURLAUTH_BASIC the defaults stand; otherwise it maps each set CURLAUTH_* bit onto SASL mechanisms (BASIC→PLAIN|LOGIN, DIGEST→DIGEST-MD5, NTLM→NTLM, BEARER→OAUTHBEARER|XOAUTH2, GSSAPI→GSSAPI) and, when any mapped, replaces prefmech with that set.

**Uncertainties.**

- httpauth values other than the mapped bits silently keep the protocol defaults.

<a id="u-dcd56164044a"></a>
### `Curl_sasl_decode_mech`

`unsigned short Curl_sasl_decode_mech(const char *ptr, size_t maxlen, size_t *len)` · [lib/curl_sasl.c:L81-L103][f1]

Matches a server-advertised SASL mechanism name against the static mechtable and returns its flag bit.

It scans each table entry whose length fits in maxlen and whose prefix compares case-insensitively via curl_strnequal. On a prefix match it stores the name length in *len when that pointer is non-NULL, then returns the entry's bit immediately if the whole buffer was the name; otherwise it inspects the character right after the name and only accepts the match if it is not an uppercase letter, digit, '-' or '_', preventing false matches on longer names such as a prefix of another mechanism. Unmatched input yields 0.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

**Uncertainties.**

- Behavior when ptr is not NUL-terminated but maxlen covers only the name depends on curl_strnequal semantics not shown here.

<a id="u-cb93315649c7"></a>
### `Curl_sasl_parse_url_auth_option`

`CURLcode Curl_sasl_parse_url_auth_option(struct SASL *sasl, const char *value, size_t…` · [lib/curl_sasl.c:L110-L135][f1]

Parses a URL login option into SASL mechanism preferences.

An empty value (len 0) returns CURLE_URL_MALFORMAT immediately. If sasl->resetprefs is set it is cleared and prefmech is reset to SASL_AUTH_NONE first. A value of '*' (compared with strncmp bounded by len) sets prefmech to SASL_AUTH_DEFAULT; otherwise the value is decoded with Curl_sasl_decode_mech and accepted only when the returned bit is nonzero and the matched length equals the full option length, in which case the bit is OR-ed into prefmech; any other value yields CURLE_URL_MALFORMAT.

calls: [Curl_sasl_decode_mech](r15-sasl-auth.md#u-dcd56164044a)

**Uncertainties.**

- strncmp(value, "*", len) reads up to len bytes of value; behavior for values shorter than len relies on strncmp stopping at the NUL of the literal.

<a id="u-e437b68a0eb0"></a>
### `Curl_sasl_can_authenticate`

`bool Curl_sasl_can_authenticate(struct SASL *sasl, struct Curl_easy *data)` · [lib/curl_sasl.c:L274-L285][f1]

Reports whether authentication can be attempted at all.

It returns TRUE when data->conn->creds is set regardless of content, and otherwise TRUE only when the intersection of offered mechanisms (authmechs) and preferences (prefmech) includes SASL_MECH_EXTERNAL, since EXTERNAL needs no username or password. Any other combination returns FALSE.

**Uncertainties.**

- Whether a non-NULL creds value always implies usable credentials is decided by the creds layer, not here.

<a id="u-a9fa97d48489"></a>
### `Curl_sasl_start`

`CURLcode Curl_sasl_start(struct SASL *sasl, struct Curl_easy *data, bool force_ir, sa…` · [lib/curl_sasl.c:L510-L572][f1]

Selects a mechanism and, if possible, sends the AUTH command with an initial response.

It latches force_ir into sasl, resets authused, sets *progress to SASL_IDLE, and fills an sasl_ctx with enabledmechs = authmechs & prefmech. It then tries the chooser helpers in short-circuit order (EXTERNAL, then build-dependent krb5/gsasl/digest/ntlm, then oauth, oauth2, plain, login); DEBUGASSERT expects either a mech or an error. If a mechanism was chosen without error it stores sasl->curmech, base64-encodes any initial response via build_message, discards the response when mech+response exceed params->maxirlen, sends with params->sendauth, and on success sets *progress to SASL_INPROGRESS, entering state2 when an initial response was sent and state1 otherwise. The context bufref is always freed; sctx.result is returned.

calls: [curl-sasl.c-mechanism-choosers](r15-sasl-auth.md#u-a6cb78154ebb), [build_message](r15-sasl-auth.md#u-035dc7a2e935), [sasl_state](r15-sasl-auth.md#u-5604a10f2d68)

**Uncertainties.**

- Behavior when a chooser set result but also a mech, or when sendauth partially sent data, is not defined in this file.

<a id="u-d687179d440b"></a>
### `Curl_sasl_continue`

`CURLcode Curl_sasl_continue(struct SASL *sasl, struct Curl_easy *data, int code, sasl…` · [lib/curl_sasl.c:L579-L809][f1]

Drives one step of the SASL state machine after a server reply with status code.

It first treats a SASL_FINAL state: any code other than params->finalcode yields CURLE_LOGIN_DENIED, progress becomes SASL_DONE and the machine stops. Outside SASL_CANCEL/SASL_OAUTH2_RESP, a code differing from params->contcode likewise stops with CURLE_LOGIN_DENIED. The main switch builds the mechanism-specific response: PLAIN/LOGIN/EXTERNAL create clear-text messages, LOGIN advancing to SASL_LOGIN_PASSWD; GSASL, CRAM-MD5, DIGEST-MD5 (optionally an extra empty RESP state), NTLM (type-1 then type-2 decode/type-3), GSSAPI (user, token, optional no-data steps) all decode the server message via get_server_message first; SASL_STOP just completes; OAUTH2 branches on authused between bearer and xoauth messages; OAUTH2_RESP treats the final code as success, a continuation by sending the single byte 0x01, anything else as CURLE_LOGIN_DENIED; SASL_CANCEL strips the failed mechanism from authmechs, clears authused/curmech and restarts authentication by calling Curl_sasl_start. Afterwards CURLE_BAD_CONTENT_ENCODING sends params->cancelauth and moves to SASL_CANCEL; CURLE_OK base64-encodes via build_message and sends params->contauth; other errors stop with SASL_DONE. State is updated last; both bufrefs are always freed.

calls: [get_server_message](r15-sasl-auth.md#u-ca38d6473226), [build_message](r15-sasl-auth.md#u-035dc7a2e935), [Curl_sasl_start](r15-sasl-auth.md#u-a9fa97d48489), [sasl_state](r15-sasl-auth.md#u-5604a10f2d68), [Curl_failf](r1-trace-logging.md#u-c8338023c157)

**Uncertainties.**

- The SASL_CANCEL and OAUTH2_RESP early returns skip the Curl_bufref_free(&serverdata) cleanup call at the bottom; the bufrefs were only initialized there, so leak severity depends on Curl_bufref_init semantics defined in bufref.c.

<a id="u-7a02fbd48e90"></a>
### `Curl_sasl_is_blocked`

`CURLcode Curl_sasl_is_blocked(struct SASL *sasl, struct Curl_easy *data)` · [lib/curl_sasl.c:L844-L906][f1]

Always returns CURLE_LOGIN_DENIED; its value is the diagnostics it emits when CURLVERBOSE is defined.

It computes enabledmechs = authmechs & prefmech and logs the first matching summary: no mechanism offered or recognized, no overlap between offered and configured mechanisms, or no offered mechanism could be selected. In the last case it additionally explains EXTERNAL rejection when the connection credentials carry a password, then calls sasl_unchosen for GSSAPI, both SCRAM variants, DIGEST-MD5, CRAM-MD5, NTLM, OAUTHBEARER and XOAUTH2 with per-mechanism builtin/platform flags and an OAUTH hint pointing at CURLOPT_XOAUTH2_BEARER when no bearer credential is set. Without CURLVERBOSE it is a no-op that returns the same code.

calls: [sasl_unchosen](r15-sasl-auth.md#u-b67393a1fb17)

**Uncertainties.**

- The compile-time flag mapping for NTLM is inverted relative to the others (CURL_SASL_NTLM is TRUE when USE_NTLM is undefined), which looks deliberate to render 'not builtin' but cannot be fully confirmed here.

<a id="u-035dc7a2e935"></a>
### `build_message`

`static CURLcode build_message(struct SASL *sasl, struct bufref *msg)` · [lib/curl_sasl.c:L248-L267][f1]

Converts an outgoing SASL message to the wire form required by the protocol.

When SASL_FLAG_BASE64 is not set the buffer is left untouched. With the flag: a NULL message becomes a zero-length static "" buffer; a non-empty message is base64-encoded via curlx_base64_encode and the bufref is repointed at the encoded text with curl_free; a non-NULL zero-length message is left as-is. Encoding failure is returned; otherwise CURLE_OK.

calls: [curlx_base64_encode](r4-base64-codec.md#u-6cff14e8366f)

<a id="u-ca38d6473226"></a>
### `get_server_message`

`static CURLcode get_server_message(struct SASL *sasl, struct Curl_easy *data, struct …` · [lib/curl_sasl.c:L223-L244][f1]

Fetches the peer's SASL challenge and normalizes it to binary in the caller's bufref.

It first calls the protocol's getmessage callback. If that succeeded and the protocol has SASL_FLAG_BASE64, an empty decoded string is replaced by a NULL/0-length buffer, otherwise the text is base64-decoded via curlx_base64_decode and the out bufref is repointed at the decoded bytes with curl_free as releaser. Decode failure propagates as the returned CURLcode; without the base64 flag the raw message is passed through.

calls: [curlx_base64_decode](r4-base64-codec.md#u-153cda566bc5), [Curl_bufref_set](r14-bufref-buffers.md#u-214d3ce6e368)

**Uncertainties.**

- getmessage is a callback; its failure modes are defined in each protocol module, not here.

<a id="u-5604a10f2d68"></a>
### `sasl_state`

`static void sasl_state(struct SASL *sasl, struct Curl_easy *data, saslstate newstate)` · [lib/curl_sasl.c:L183-L218][f1]

Single sanctioned way to assign sasl->state.

In debug builds with CURLVERBOSE it logs the old and new state names from a static table when they differ; in other builds data is unused. It then stores newstate unconditionally; out-of-range states would index the debug name table incorrectly, which the code does not guard.

**Uncertainties.**

- Debug name table assumes saslstate enum order matches the strings; a mismatch would mislabel logs only.

<a id="u-b67393a1fb17"></a>
### `sasl_unchosen`

`static void sasl_unchosen(struct Curl_easy *data, unsigned short mech, unsigned short…` · [lib/curl_sasl.c:L812-L841][f1]

Verbose-only diagnostic that explains why one mechanism was not selected, compiled only with CURLVERBOSE.

It returns early if the mechanism is not in enabledmechs or cannot be named in mechtable. Otherwise it reports, in order of precedence: not built in, not supported by the platform/libraries, or missing a caller-supplied parameter string and/or a username on the connection credentials.

**Uncertainties.**

- The platform argument values are fixed per mechanism at the Curl_sasl_is_blocked call site; their correctness is not checked here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curl_sasl.c
