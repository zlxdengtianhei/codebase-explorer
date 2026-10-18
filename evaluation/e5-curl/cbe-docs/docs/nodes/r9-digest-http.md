# HTTP Digest

**Capability.** Parses WWW/Proxy-Authenticate Digest challenges into per-easy state, regenerates state on peer/credential change, and produces the Authorization/Proxy-Authorization header via the algo-dispatched vauth generator.

Read this child for the HTTP-facing Digest flow: input parsing, stale/peer flush, and output header generation. It delegates to the digest-core child for actual parsing and response building.

**Depends on.**

- [Digest core \(vauth/digest\)](r9-digest-core.md) · graph-confirmed · 6 edge(s)
- [printf engine \(mprintf\)](r9-mprintf.md) · graph-confirmed · 1 edge(s)

Parent: [HTTP/SOCKS authentication](r9-http-auth.md)

## Units (4)

<a id="u-09a6ca481652"></a>
### `Curl_http_auth_cleanup_digest`

`void Curl_http_auth_cleanup_digest(struct Curl_easy *data)` · [lib/http_digest.c:L183-L187][f1]

Clears both host and proxy Digest state of an easy handle by invoking Curl_auth_digest_cleanup on data->state.digest and data->state.proxydigest.

Called from connection/easy teardown and reset paths.

calls: [Curl_auth_digest_cleanup](r9-digest-core.md#u-c99d51194936)

<a id="u-4ac8edc7dedb"></a>
### `Curl_input_digest`

`CURLcode Curl_input_digest(struct Curl_easy *data, bool proxy, const char *header) /*…` · [lib/http_digest.c:L70-L108][f1]

Parses a WWW-Authenticate/Proxy-Authenticate header value into the appropriate digest state.

It selects data->state.proxydigest for proxy or data->state.digest otherwise; with proxy support compiled out, a proxy header is cleaned and ignored with CURLE_OK. If the header does not start with 'Digest' followed by a blank, it cleans the digest state and returns CURLE_AUTH_ERROR. Otherwise it skips blanks and delegates decoding to Curl_auth_decode_digest_http_message, which resets the digest struct first; its result is propagated. Afterwards the peer (not creds) is linked into digest->origin so subsequent requests keep working across credential changes.

**Notes.**

- failure: Any header not matching 'Digest'+blank yields CURLE_AUTH_ERROR after clearing prior digest state.

calls: [Curl_auth_decode_digest_http_message](r9-digest-core.md#u-ad216e8b7263), [Curl_auth_digest_cleanup](r9-digest-core.md#u-c99d51194936), [Curl_peer_link](r3-peer-identity.md#u-cdc53111cd17), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16); uses: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

**Uncertainties.**

- checkprefix and ISBLANK are unresolved macros here; the exact blank-set and case handling are inferred, not proven.

<a id="u-bdfad0d7ab7c"></a>
### `Curl_output_digest`

`CURLcode Curl_output_digest(struct Curl_easy *data, bool proxy, const unsigned char *…` · [lib/http_digest.c:L110-L181][f1]

Generates the Authorization (or Proxy-Authorization) header for a Digest-authenticated request.

It binds digest, origin, creds, the output header pointer (hd_proxy_auth vs hd_auth), and the auth state (authproxy vs authhost) per proxy flag; without proxy support it returns CURLE_NOT_BUILT_IN for proxy. digest_flush_stale resets state on peer/credential change, and the previous header string is freed. If no challenge is recorded (digest->nonce, or input_token under Windows SSPI), authp->done is set FALSE and CURLE_OK returned with no header. Otherwise Curl_auth_create_digest_http_message builds the response; on error that result propagates. On success the header is formatted with curl_maprintf including the 'Proxy-' prefix when proxy, response memory is freed, allocation failure returns CURLE_OUT_OF_MEMORY, and authp->done becomes TRUE.

**Notes.**

- condition: Challenge detection differs by build: digest->input_token under USE_WINDOWS_SSPI, digest->nonce otherwise.
- side_effect: Frees *allocuserpwd before writing and sets authp->done FALSE or TRUE depending on outcome.

calls: [digest_flush_stale](r9-digest-http.md#u-913be0e8d703), [Curl_auth_create_digest_http_message](r9-digest-core.md#u-e3cd8f61a7a9), [lib-mprintf-c-dynbuf-alloc-family](r9-mprintf-formatter-families.md#u-ce09737881fa)

**Uncertainties.**

- Curl_auth_create_digest_http_message failure conditions are defined in lib/vauth/digest.c, not visible here.

<a id="u-913be0e8d703"></a>
### `digest_flush_stale`

`static void digest_flush_stale(struct Curl_easy *data, struct digestdata *digest, str…` · [lib/http_digest.c:L38-L63][f1]

Resets cached Digest state when the peer or credentials changed, then links the current peer and creds into the digest.

It computes flush=TRUE if digest->origin is NULL or differs from the given peer, or else if digest->creds is set and differs from the given creds (each with a trace log line). When flush is set it calls Curl_auth_digest_cleanup(digest) to discard stale nonce state. Unconditionally it then relinks via Curl_peer_link and Curl_creds_link, so a peer change alone does not reject the new creds; they are adopted. Static helper, no return value.

calls: [Curl_auth_digest_cleanup](r9-digest-core.md#u-c99d51194936), [Curl_peer_equal](r3-peer-identity.md#u-c6bb91e928c8), [Curl_creds_same](r7-credential-store.md#u-338fbc38108d), [Curl_peer_link](r3-peer-identity.md#u-cdc53111cd17), [Curl_creds_link](r7-credential-store.md#u-ed4d022e2a5a), [Curl_trc_multi](r1-trace-logging.md#u-385de27aa970)

**Uncertainties.**

- Curl_peer_link/Curl_creds_link refcount semantics are not visible here, so ownership transfer consequences are inferred from the names only.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http_digest.c
