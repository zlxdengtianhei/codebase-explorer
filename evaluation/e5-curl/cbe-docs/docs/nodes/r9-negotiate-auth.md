# Negotiate/SPNEGO (HTTP)

**Capability.** Consumes Negotiate challenge headers, resets and maintains per-connection SPNEGO security context, and produces the Authorization/Proxy-Authorization Negotiate header while driving the handshake state machine.

Read this child for the HTTP Negotiate scheme flow: input, output, and reset are mutually interlinked per the inferred relations. Unit grp:http-negotiate-c-residual is the file's closing guard with no behavior.

**Depends on.**

- [Case-insensitive strings](r9-caseless-strings.md) · model-inferred · 0 edge(s)

Parent: [HTTP/SOCKS authentication](r9-http-auth.md)

## Units (4)

<a id="u-908968ebff23"></a>
### `http-negotiate-c-residual`

`module_region` · [lib/http_negotiate.c:L264-L266][f1]

Trailing closing region of lib/http_negotiate.c containing only the #endif for the !CURL_DISABLE_HTTP && USE_SPNEGO guard; no executable behavior.

<a id="u-8b73e3873935"></a>
### `Curl_input_negotiate`

`CURLcode Curl_input_negotiate(struct Curl_easy *data, struct connectdata *conn, bool …` · [lib/http_negotiate.c:L52-L153][f1]

Consumes a received Negotiate challenge or success header and advances the per-connection Negotiate state.

It selects credentials, host, and saved state per target: proxy uses conn->http_proxy.creds and proxy peer hostname (returning CURLE_NOT_BUILT_IN when proxy support is compiled out); otherwise data->state.creds and the origin hostname. It fetches neg_ctx via Curl_auth_nego_get (NULL yields CURLE_OUT_OF_MEMORY), strips the 'Negotiate' token from the header, and sets havenegdata to whether a token of nonzero length follows. With an empty token: state CURL_NEGO_AUTH_SUCC logs 'Negotiate auth restarted' and resets; any other state other than CURL_NEGO_AUTH_NONE means rejection, so it resets and returns CURLE_LOGIN_DENIED. Under USE_WINDOWS_SSPI it copies conn->sslContext into neg_ctx; under GSS_C_CHANNEL_BOUND_FLAG it initializes channel_binding_data (with SSL channel-binding data fetched when the first socket uses SSL, returning the error after a reset if that fetch fails; capacity 1 otherwise). It then decodes the message with Curl_auth_decode_spnego_message; on decode failure it frees the binding data and resets. On success for the non-proxy case it enforces that creds_origin matches the current origin and stored creds match the current creds (DEBUGASSERT plus CURLE_FAILED_INIT otherwise) and then links the connection's creds_origin and creds to the origin and creds used, tying the connection to those credentials.

**Notes.**

- failure: Channel-binding fetch or message decode failure triggers http_auth_nego_reset before propagating the error code.
- contract: For non-proxy use, mismatched creds_origin or creds on an in-flight context returns CURLE_FAILED_INIT; the header data was already consumed at that point.

calls: [http_auth_nego_reset](r9-negotiate-auth.md#u-acbd58110aa3); uses: [lib/vauth/vauth.h][f2], [lib/vtls/vtls.h][f3]

**Uncertainties.**

- Behavior of Curl_auth_decode_spnego_message on malformed or non-Negotiate payload strings is outside this file.
- The non-Windows, non-GSS_C_CHANNEL_BOUND_FLAG build path (neither macro set) skips channel-binding handling entirely; that combination's behavior follows from the same code but its #else-free nesting makes the exact preprocessor expansion build-dependent.

<a id="u-c9f47d9e3265"></a>
### `Curl_output_negotiate`

`CURLcode Curl_output_negotiate(struct Curl_easy *data, struct connectdata *conn, bool…` · [lib/http_negotiate.c:L155-L264][f1]

Produces the Authorization (or Proxy-Authorization) Negotiate header for the next request and drives the handshake state machine.

Target selection mirrors the input function: proxy uses authproxy and proxy_negotiate_state (CURLE_NOT_BUILT_IN when proxy support is disabled), otherwise authhost and http_negotiate_state; neg_ctx comes from Curl_auth_nego_get (NULL gives CURLE_OUT_OF_MEMORY). authp->done is cleared first. When the state is CURL_NEGO_AUTH_RECV and havenegdata is set, havemultiplerequests becomes TRUE; when the state is CURL_NEGO_AUTH_SUCC and havenoauthpersist is unset, noauthpersist is computed as the negation of havemultiplerequests. Generation is skipped when noauthpersist is set or the state is neither DONE nor SUCC; in that path, noauthpersist with SUCC logs and resets the context, and a missing context causes a re-priming call to Curl_input_negotiate with the bare header 'Negotiate' — a CURLE_AUTH_ERROR there is swallowed (authp->done = TRUE, returns CURLE_OK) to continue unauthenticated, while other errors propagate. Curl_auth_create_spnego_message then builds the base64 token (errors propagate); the formatted header replaces data->req.hd_auth or hd_proxy_auth after freeing the previous value, and base64 is freed. Note the out-of-memory check on userp happens after assigning it into the request header, so a NULL header would be stored before returning CURLE_OUT_OF_MEMORY. The state becomes CURL_NEGO_AUTH_SENT, upgraded to CURL_NEGO_AUTH_DONE when the underlying status reports completion or continue-needed (GSS_S_COMPLETE/GSS_S_CONTINUE_NEEDED under HAVE_GSSAPI, SEC_E_OK/SEC_I_CONTINUE_NEEDED under USE_WINDOWS_SSPI). Finally, states DONE or SUCC set authp->done so no header is sent, havenegdata is cleared, and CURLE_OK is returned.

**Notes.**

- failure: CURLE_AUTH_ERROR from the priming Curl_input_negotiate is converted to CURLE_OK with authp->done = TRUE; all other errors propagate.
- side_effect: Replaces data->req.hd_auth or data->req.hd_proxy_auth with the newly formatted header, freeing the old value.

calls: [Curl_input_negotiate](r9-negotiate-auth.md#u-8b73e3873935), [http_auth_nego_reset](r9-negotiate-auth.md#u-acbd58110aa3); uses: [lib/vauth/vauth.h][f2]

**Uncertainties.**

- The NULL check on userp occurs after curlx_free(base64) and after assignment into the request field, so on allocation failure the field is left NULL before returning CURLE_OUT_OF_MEMORY; whether any earlier userp dereference exists is not visible here.
- If neither HAVE_GSSAPI nor USE_WINDOWS_SSPI is defined, the DONE upgrade block is empty and the state stays CURL_NEGO_AUTH_SENT; resulting multi-request behavior is build-dependent.

<a id="u-acbd58110aa3"></a>
### `http_auth_nego_reset`

`static void http_auth_nego_reset(struct connectdata *conn, struct negotiatedata *neg_…` · [lib/http_negotiate.c:L37-L50][f1]

Resets SPNEGO/Negotiate authentication state for a connection and cleans up the negotiated security context.

If proxy is set it only clears conn->proxy_negotiate_state to CURL_NEGO_AUTH_NONE; otherwise it clears conn->http_negotiate_state and unlinks both the connection's creds_origin peer and creds links, tying the connection to no credentials. When neg_ctx is non-NULL it also calls Curl_auth_cleanup_spnego to discard the security context.

uses: [lib/vauth/vauth.h][f2]

**Uncertainties.**

- Effect of Curl_peer_unlink/Curl_creds_unlink/Curl_auth_cleanup_spnego on linked objects is not visible in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http_negotiate.c
[f2]: ../../../../../../eval/curl-2c04412/lib/vauth/vauth.h
[f3]: ../../../../../../eval/curl-2c04412/lib/vtls/vtls.h
