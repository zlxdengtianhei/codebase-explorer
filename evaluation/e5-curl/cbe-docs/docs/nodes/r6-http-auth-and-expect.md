# Auth Emission and Expect-100

**Capability.** Authentication header generation (method preference, Basic/Bearer output, per-side emission) and the Expect: 100-continue client reader gating request bodies.

Consult for how Authorization/Proxy-Authorization values are produced before a request and how 100-continue suspends or resumes the body reader. The exp100 reader is called from body logic, send-error handling, pollsets and 1xx processing.

**Depends on.**

- [Share API](r6-share-api.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Request Construction and Send](r6-http-request-build.md) · graph-confirmed · 2 edge(s)
- [Response Parsing and Reaction](r6-http-response-processing.md) · graph-confirmed · 6 edge(s)

Parent: [HTTP Protocol Engine](r6-http-engine.md)

## Units (6)

<a id="u-192bec66feb1"></a>
### `Curl_http_output_auth`

`CURLcode Curl_http_output_auth(struct Curl_easy *data, struct connectdata *conn, cons…` · [lib/http.c:L903-L919][f1]

Entry point for emitting authentication headers before a request.

With no proxy peer/creds, no Negotiate/HTTPSIG wanted and no creds it marks both auth states done and returns. Builds path?query when a query exists (OOM aborts). For host and proxy with want but no picked method yet, picked is seeded from want (a single bit takes effect immediately). Proxy headers are emitted when talking to an origin proxy or during CONNECT; otherwise the proxy is marked done. Host headers are emitted when creds exist or auth to the host is allowed; otherwise done. Finally req.authneg is set when a multipass auth is still incomplete and the method is not GET/HEAD, which makes the next request a zero-length probe.

calls: [output_auth_headers](r6-http-auth-and-expect.md#u-a8b1fa83863d)

**Uncertainties.**

- Behavior of the disabled-auth fallback variant (void stub) is trivially CURLE_OK.

<a id="u-a8b1fa83863d"></a>
### `output_auth_headers`

`static CURLcode output_auth_headers(struct Curl_easy *data, struct connectdata *conn,…` · [lib/http.c:L646-L801][f1]

Produces the auth header for one side (server or proxy) according to authstatus->picked.

AWS_SIGV4 and HTTPSIG are never used for a proxy; HTTPSIG and Negotiate and NTLM require Curl_auth_allowed_to_host (or proxy context) and are otherwise marked done without output. Negotiate additionally requires no user-supplied Authorization header. Digest always outputs via Curl_output_digest with request and path. Basic outputs only when credentials exist with user or password and no user Authorization header already present, and marks done regardless. Bearer outputs only server-side with bearer creds and no existing Authorization header. When a header was produced it records the picked method in info.httpauthpicked/proxyauthpicked, logs it, and sets multipass to !done; otherwise multipass is FALSE and the picked indicator is cleared.

calls: [http_output_basic](r6-http-auth-and-expect.md#u-978768a5b5c1), [http_output_bearer](r6-http-auth-and-expect.md#u-9b10527f5f48)

**Uncertainties.**

- Curl_output_* functions (digest, ntlm, negotiate, aws, httpsig) are external and their failure semantics are only propagated here.

<a id="u-978768a5b5c1"></a>
### `http_output_basic`

`static CURLcode http_output_basic(struct Curl_easy *data, struct connectdata *conn, b…` · [lib/http.c:L252-L310][f1]

Builds a Basic Authorization (or Proxy-authorization) header value.

Selects the target header slot and credentials: proxy uses req.hd_proxy_auth and conn->http_proxy.creds (compiled out without proxy support, returning CURLE_NOT_BUILT_IN); otherwise req.hd_auth and data->state.creds. With no credentials it DEBUGASSERTs and returns CURLE_FAILED_INIT. Formats 'user:passwd', base64-encodes it (propagating encode errors; a NULL encoding result yields CURLE_REMOTE_ACCESS_DENIED), then replaces the stored header with 'Authorization: Basic <b64>\r\n'. Frees the temporary user:passwd string on every path; OOM on the header format returns CURLE_OUT_OF_MEMORY.

**Notes.**

- side_effect: Frees and replaces data->req.hd_auth or hd_proxy_auth.

<a id="u-9b10527f5f48"></a>
### `http_output_bearer`

`static CURLcode http_output_bearer(struct Curl_easy *data)` · [lib/http.c:L321-L339][f1]

Sets req.hd_auth to 'Authorization: Bearer <token>\r\n' from the transfer's OAuth bearer credentials; returns CURLE_OUT_OF_MEMORY if formatting fails, otherwise CURLE_OK.

The DEBUGASSERT presumes bearer credentials exist.

**Uncertainties.**

- Behavior when Curl_creds_oauth_bearer returns NULL (header would contain '(null)'-style text) is not guarded here.

<a id="u-3a27430cd9fe"></a>
### `pickoneauth`

`static bool pickoneauth(struct auth *pick, unsigned long mask, struct Curl_creds *creds)` · [lib/http.c:L349-L391][f1]

Chooses one auth method from what the server offers, the user allows (pick->want), and mask permits, in fixed preference order: Negotiate, Bearer (needs bearer creds), Digest (needs user/pass), NTLM, Basic (needs user/pass), AWS_SIGV4, HTTPSIG.

If nothing matches it sets picked to CURLAUTH_PICKNONE and returns FALSE. Always clears pick->avail to CURLAUTH_NONE before returning.

**Notes.**

- side_effect: pick->avail is consumed; a second call cannot re-pick from the same offer.

<a id="u-d25da102592f"></a>
### `http-c-exp100-reader`

`struct cr_exp100_ctx` · [lib/http.c:L1527-L1531][f1]

Implements the Expect: 100-continue gating as a client reader.

cr_exp100_ctx holds the reader superclass, the wait start time and an expect100 state. In EXP100_SENDING_REQUEST the read callback yields nothing while the request send buffer is not empty; once fully sent it moves to EXP100_AWAITING_CONTINUE, records the start time and arms EXPIRE_100_TIMEOUT for set.expect_100_timeout ms. While awaiting, reads yield nothing until the timeout elapses, then the state drops to EXP100_SEND_DATA (clearing the timer), logs 'Done waiting for 100-continue', and passes reads through to the next reader. EXP100_FAILED returns CURLE_READ_ERROR. http_exp100_continue forces the state down to SEND_DATA when still waiting; it is invoked by http_exp100_got100 (a real 100 response), http_exp100_send_anyway, and implicitly on timeout. cr_exp100_done marks the state FAILED on premature end, otherwise SEND_DATA, and clears the timer. http_exp100_add_reader creates and installs the reader (protocol stage) initialized to SENDING_REQUEST, freeing it on failure. http_exp100_is_waiting reports the AWAITING_CONTINUE state; http_exp100_is_selected reports whether such a reader exists.

**Uncertainties.**

- Reader chain mechanics (Curl_creader_*) are defined elsewhere.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http.c
