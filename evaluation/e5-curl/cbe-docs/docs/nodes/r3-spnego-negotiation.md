# SPNEGO/Negotiate Auth Providers

**Capability.** Implements the SPNEGO authentication API twice with identical semantics: GSS-API (always reported available) and Windows SSPI (probed via the Negotiate package). Each provides support probing, token decode/handshake advance, base64 output-token creation, and full resource cleanup.

Use this subtree when working with Negotiate authentication. The two files are parallel implementations selected at build time; call sites consume the same Curl_auth_* function names regardless of provider.

Parent: [Crypto Primitives & HTTP Authentication](r3-crypto-auth.md)

## Units (8)

<a id="u-b11331b2a1ca"></a>
### `Curl_auth_is_spnego_supported`

`bool Curl_auth_is_spnego_supported(void)` · [lib/vauth/spnego_gssapi.c:L49-L52][f1]

Unconditionally returns TRUE; with GSS-API compiled in, SPNEGO is always reported as available.

<a id="u-98b39212b763"></a>
### `Curl_auth_decode_spnego_message`

`CURLcode Curl_auth_decode_spnego_message(struct Curl_easy *data, struct Curl_creds *c…` · [lib/vauth/spnego_gssapi.c:L72-L276][f1]

Advances the GSS-API SPNEGO handshake using an optional base64 challenge, updating nego.

If a context exists with status GSS_S_COMPLETE and the server challenged again, state is cleaned up and CURLE_LOGIN_DENIED returned. On first call it builds an SPN (credential SASL service if present, else default) and imports it into nego->spn (CURLE_OUT_OF_MEMORY for build failure; logged gss_import_name failure returns CURLE_AUTH_ERROR). A non-empty chlg64 starting with '=' is treated as an empty challenge (CURLE_BAD_CONTENT_ENCODING); otherwise it is base64-decoded (decoder errors propagate) and installed as the input token. Under GSS_C_CHANNEL_BOUND_FLAG, non-empty channel binding data is attached as GSS channel bindings. Under HAVE_GSS_SET_NEG_MECHS, default credentials are acquired once and the NTLMSSP OID is filtered out of the offered mechanisms via Curl_gss_set_neg_mechs; credential-acquire failure returns CURLE_AUTH_ERROR, while set-neg-mechs failure is only logged and negotiation proceeds unrestricted. Curl_gss_init_sec_context generates the response: GSS_ERROR releases the output token, logs, and returns CURLE_AUTH_ERROR; an empty output token also returns CURLE_AUTH_ERROR. If the established context's mechanism is NTLMSSP, the token is released, state cleaned, and CURLE_AUTH_ERROR returned. Otherwise any previous output token is released and the new token stored; CURLE_OK returned.

calls: [Curl_auth_cleanup_spnego](r3-spnego-negotiation.md#u-8c6673b73ece)

**Uncertainties.**

- If Curl_gss_indicate_mechs or gss_create_empty_oid_set fail, credentials stay acquired but mechanisms remain unrestricted; reachability of that combination is not provable here.

<a id="u-1304b4b8f46c"></a>
### `Curl_auth_create_spnego_message`

`CURLcode Curl_auth_create_spnego_message(struct negotiatedata *nego, char **outptr, s…` · [lib/vauth/spnego_gssapi.c:L294-L322][f1]

Base64-encodes nego->output_token into the caller's outptr/outlen.

On encode failure the GSS output token buffer is released and zeroed before propagating the error. If the encoded result is empty (NULL pointer or zero length), the token is likewise released and zeroed and CURLE_REMOTE_ACCESS_DENIED returned. Success leaves the token in nego for later cleanup.

**Uncertainties.**

- minor_status is passed uninitialized to gss_release_buffer; its use is a GSS-API convention not verifiable here.

<a id="u-8c6673b73ece"></a>
### `Curl_auth_cleanup_spnego`

`void Curl_auth_cleanup_spnego(struct negotiatedata *nego)` · [lib/vauth/spnego_gssapi.c:L334-L370][f1]

Releases all GSS-API resources held in negotiatedata.

It deletes the security context, releases the output token, the SPN name, and credentials — each guarded by its respective sentinel (GSS_C_NO_CONTEXT/NO_NAME/NO_CREDENTIAL) — then resets status and the persist/flag booleans (noauthpersist, havenoauthpersist, havenegdata, havemultiplerequests) to false/0. Safe on partially initialized state.

<a id="u-2c0afa83914d"></a>
### `lib/vauth/spnego_sspi.c:Curl_auth_is_spnego_supported`

`bool Curl_auth_is_spnego_supported(void)` · [lib/vauth/spnego_sspi.c:L44-L60][f2]

Reports whether Windows SSPI exposes the Negotiate package, mirroring the NTLM support probe.

QuerySecurityPackageInfo for SP_NAME_NEGOTIATE returning SEC_E_OK means the buffer is freed and TRUE returned; any other status yields FALSE without logging.

<a id="u-dde7e4fef1cf"></a>
### `lib/vauth/spnego_sspi.c:Curl_auth_decode_spnego_message`

> **ID corrected by CBE.** CBE changed the unit ID from ` lib/vauth/spnego_sspi.c::function::Curl_auth_decode_spnego_message::2335 ` to the inventory ID ` lib/vauth/spnego_sspi.c::function::Curl_auth_decode_spnego_message::2605 `. The model wrote this body under the wrong ID; it may be inaccurate.

`CURLcode Curl_auth_decode_spnego_message(struct Curl_easy *data, struct Curl_creds *c…` · [lib/vauth/spnego_sspi.c:L80-L294][f2]

Advances the SSPI Negotiate handshake with an optional base64 challenge, lazily initializing SPN, token buffer, credentials, and context in nego.

If a context exists with status SEC_E_OK and the server challenged again, state is cleaned and CURLE_LOGIN_DENIED returned. First-call setup: builds the SPN (CURLE_OUT_OF_MEMORY on failure); queries the Negotiate package for the max token size (failure logs via failf and returns CURLE_AUTH_ERROR) and allocates the output token (CURLE_OUT_OF_MEMORY); when credentials are absent it allocates them, building an SSPI identity from the credential's user/password or zeroing a structured identity for single sign-on, always sets PackageList to "!ntlm" to exclude NTLM from negotiation, acquires the credentials handle (failure frees the handle and returns CURLE_AUTH_ERROR), and allocates the context handle (CURLE_OUT_OF_MEMORY). Challenge handling: chlg64 starting with '=' means empty challenge (CURLE_BAD_CONTENT_ENCODING); other non-empty chlg64 is base64-decoded (decoder errors propagate) into one SECBUFFER_TOKEN input buffer. If nego->sslContext is set, endpoint bindings are queried and appended as SECBUFFER_CHANNEL_BINDINGS when the query succeeds, then freed after the call. InitializeSecurityContext runs with ISC_REQ_CONFIDENTIALITY plus DELEGATE|MUTUAL_AUTH when the user enables GSS-API delegation, passing the input descriptor only if buffers exist and the existing context only when a challenge was decoded (otherwise starting a fresh context). Errors: GSS_ERROR status logs via Curl_sspi_strerror and maps SEC_E_INSUFFICIENT_MEMORY to CURLE_OUT_OF_MEMORY, otherwise CURLE_AUTH_ERROR; statuses needing completion run CompleteAuthToken whose failure is reported the same way. On success output_token_length records the produced size and CURLE_OK is returned.

**Uncertainties.**

- GSS_ERROR is applied to SECURITY_STATUS values; the mapping of that macro to SSPI statuses is defined elsewhere and not verifiable in this file.
- The meaning of CURL_SEC_WINNT_AUTH_IDENTITY flags is defined outside this file; only the assignment is observable.

<a id="u-15f1d6f16380"></a>
### `lib/vauth/spnego_sspi.c:Curl_auth_create_spnego_message`

`CURLcode Curl_auth_create_spnego_message(struct negotiatedata *nego, char **outptr, s…` · [lib/vauth/spnego_sspi.c:L312-L325][f2]

Base64-encodes the raw output_token and its recorded length into outptr/outlen.

Encode failure propagates directly. If the encoded result is empty (NULL pointer or zero length), the buffer is freed and CURLE_REMOTE_ACCESS_DENIED returned; the nego token itself is not released here.

**Uncertainties.**

- Whether an empty encode result can occur given a non-empty token is not determinable from this code; the branch handles it defensively.

<a id="u-a658b55f459d"></a>
### `lib/vauth/spnego_sspi.c:Curl_auth_cleanup_spnego`

`void Curl_auth_cleanup_spnego(struct negotiatedata *nego)` · [lib/vauth/spnego_sspi.c:L337-L366][f2]

Releases all SSPI resources in negotiatedata.

It deletes and frees the context and credentials handles (each NULL-guarded), frees the identity via Curl_sspi_free_identity, frees the SPN and output token with curlx_safefree, and resets status, token_max, and the persist/flag booleans (noauthpersist, havenoauthpersist, havenegdata, havemultiplerequests) to 0/FALSE. Safe on partially initialized state.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vauth/spnego_gssapi.c
[f2]: ../../../../../../eval/curl-2c04412/lib/vauth/spnego_sspi.c
