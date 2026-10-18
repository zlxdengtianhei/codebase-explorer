# SSPI DIGEST

**Capability.** Windows SSPI implementation of HTTP DIGEST and DIGEST-MD5: support probing, challenge decoding with realm-to-domain override, response message generation with persistent security contexts, and state cleanup.

Read this subtree for the SSPI-side DIGEST flow on Windows. Realm handling populates the SSPI identity domain when unset.

Parent: [Authentication \(vauth\)](r8-authentication.md)

## Units (6)

<a id="u-0c7085980362"></a>
### `lib/vauth/digest_sspi.c:Curl_auth_is_digest_supported`

`bool Curl_auth_is_digest_supported(void)` · [lib/vauth/digest_sspi.c:L50-L67][f1]

Probes whether the Windows SSPI Digest package is available.

It queries the security function table for SP_NAME_DIGEST; on SEC_E_OK it frees the returned package info buffer and returns true, otherwise false. The return value is exactly the query status equality, and no other failure produces diagnostics.

<a id="u-dbabd7c5e9e1"></a>
### `lib/vauth/digest_sspi.c:Curl_auth_decode_digest_http_message`

`CURLcode Curl_auth_decode_digest_http_message(const char *chlg, struct digestdata *di…` · [lib/vauth/digest_sspi.c:L313-L362][f1]

Decodes an HTTP DIGEST challenge and stores it on the digest state.

If a previous input_token exists (meaning a prior response was sent), the new challenge is scanned pair by pair for a 'stale' directive with value 'true'; when found, Curl_auth_digest_cleanup resets the digest state and processing continues to store the new challenge, otherwise the function returns CURLE_LOGIN_DENIED (bad credentials or stale-unconfirmed). With no prior token the challenge is copied verbatim (including NUL) into digest->input_token with its length recorded; memory-duplicate failure returns CURLE_OUT_OF_MEMORY. Success returns CURLE_OK with the challenge persisted for later response generation.

calls: [lib/vauth/digest_sspi.c:Curl_auth_digest_cleanup](r8-auth-sspi-digest.md#u-485c4c396161)

**Uncertainties.**

- The stale loop advances past blanks and commas but does not validate malformed directives; only the exact 'stale=true' pair matters.
- Whether the digest struct was partially modified before the CURLE_LOGIN_DENIED return is not defended; only input_token examination occurs before that point.

<a id="u-a206a8007e46"></a>
### `Curl_override_sspi_http_realm`

`CURLcode Curl_override_sspi_http_realm(const char *chlg, SEC_WINNT_AUTH_IDENTITY_EX *…` · [lib/vauth/digest_sspi.c:L246-L298][f1]

Populates the SSPI identity's domain from the HTTP challenge's realm directive when the domain is unset or blank.

It walks the challenge string pair by pair via Curl_auth_digest_get_pair, skipping blanks; each pair whose key case-insensitively equals 'realm' is converted to a TCHAR duplicate and stored into identity->Domain/DomainLength, freeing any previous domain and the temporary conversions; unknown specifiers are silently ignored and the loop continues past a comma separator, ending when get_pair fails. Returns CURLE_OK unless either UTF-8-to-TCHAR conversion or the string duplicate fails, in which case it returns CURLE_OUT_OF_MEMORY. The identity is mutated in place.

**Uncertainties.**

- The allocation-failure branch does not restore a freed prior identity->Domain, leaving the identity with a dangling Domain pointer only if an earlier realm already replaced it — not provable from this excerpt since Domain was blank on entry.
- No parsing failures other than allocation are reported; malformed challenges are simply ignored.

<a id="u-86c06c66f656"></a>
### `lib/vauth/digest_sspi.c:Curl_auth_create_digest_http_message`

`CURLcode Curl_auth_create_digest_http_message(struct Curl_easy *data, struct Curl_cre…` · [lib/vauth/digest_sspi.c:L384-L604][f1]

Produces an HTTP DIGEST Authorization header value via SSPI, reusing a persistent security context across requests when possible.

After querying the package for the max token size (failure: CURLE_AUTH_ERROR) and allocating an output token (failure: CURLE_OUT_OF_MEMORY), it discards the saved context and its linked creds if the credentials changed. If a context exists, it builds a 5-buffer descriptor (request, uripath, padding) and calls MakeSignature; SEC_E_OK yields the token from buffer 4, any failure logs, deletes the context, and falls through to full setup. Full setup (no context) builds an identity from creds (or NULL for single sign-on), applies the realm override using the stored input token (both identity steps map failures to CURLE_OUT_OF_MEMORY and free prior allocations), links creds into digest state, acquires credentials (failure: CURLE_LOGIN_DENIED), allocates an SPN from uripath and a context handle (both allocation failures free everything and return CURLE_OUT_OF_MEMORY), then runs InitializeSecurityContext with ISC_REQ_USE_HTTP_STYLE. COMPLETE statuses trigger CompleteAuthToken; other errors free everything, delete the context, and return CURLE_OUT_OF_MEMORY for insufficient memory or CURLE_AUTH_ERROR otherwise. Finally the token bytes are duplicated into a NUL-terminated response for *outptr/*outlen; that duplication failing returns CURLE_OUT_OF_MEMORY. Success keeps digest->http_context and digest->creds alive for reuse.

calls: [Curl_override_sspi_http_realm](r8-auth-sspi-digest.md#u-a206a8007e46)

**Uncertainties.**

- On MakeSignature failure the function falls through and re-initializes a fresh context using digest->input_token, whose validity for a mid-session context is not proven here.
- output_token_len is left 0 if no context existed and all setup succeeded but resp_buf.cbBuffer was never set — that assignment happens on every full-setup path, so only a failed-context path with no resp buffer is unaccounted for; actual behavior depends on SSPI filling resp_buf.
- When creds is NULL the code still calls Curl_creds_link(&digest->creds, creds) only if creds is non-null, so the previous digest->creds is unlinked without replacement.

<a id="u-0c976d293065"></a>
### `lib/vauth/digest_sspi.c:Curl_auth_create_digest_md5_message`

`CURLcode Curl_auth_create_digest_md5_message(struct Curl_easy *data, const struct buf…` · [lib/vauth/digest_sspi.c:L86-L230][f1]

Generates a DIGEST-MD5 response token for a SASL challenge via Windows SSPI.

The service comes from creds' SASL service if present, else default_service. An empty challenge fails with CURLE_BAD_CONTENT_ENCODING after an infof; a failed QuerySecurityPackageInfo fails with CURLE_AUTH_ERROR; buffer or SPN/identity allocation failures return CURLE_OUT_OF_MEMORY (freeing prior allocations). Without stored user credentials p_identity is NULL (single sign-on). AcquireCredentialsHandle failure frees SPN, token, and identity and returns CURLE_LOGIN_DENIED. InitializeSecurityContext is run against the challenge buffer: COMPLETE_NEEDED/COMPLETE_AND_CONTINUE trigger CompleteAuthToken; other non-OK/non-CONTINUE statuses free everything and return CURLE_OUT_OF_MEMORY for SEC_E_INSUFFICIENT_MEMORY, else CURLE_AUTH_ERROR with a logged SSPI error. On success the output token (owned, curl_free) is stored in out with the response buffer's length, and context, credentials, identity, and SPN are all released. Local variables only; nothing persists across calls.

uses: [Curl_override_sspi_http_realm](r8-auth-sspi-digest.md#u-a206a8007e46)

**Uncertainties.**

- resp_buf.cbBuffer is used as the published length but is only valid if CompleteAuthToken modified it; the code trusts SSPI semantics not visible here.
- The final context handle is used without checking InitializeSecurityContext filled it on the CONTINUE path (status != SEC_E_OK still reaches DeleteSecurityContext if status was SEC_I_CONTINUE_NEEDED); correctness depends on SSPI guarantees.

<a id="u-485c4c396161"></a>
### `lib/vauth/digest_sspi.c:Curl_auth_digest_cleanup`

`void Curl_auth_digest_cleanup(struct digestdata *digest)` · [lib/vauth/digest_sspi.c:L616-L633][f1]

Releases all SSPI-backed DIGEST state on the digest struct.

It frees input_token, zeroes input_token_len, and, when http_context exists, deletes the SSPI context and frees the handle. It also unlinks the saved credential set and the peer/origin data. The struct is left in a fresh state suitable for a new handshake.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vauth/digest_sspi.c
