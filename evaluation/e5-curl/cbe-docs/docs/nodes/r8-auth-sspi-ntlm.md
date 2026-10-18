# SSPI NTLM

**Capability.** Windows SSPI implementation of NTLM: support probing, type-1 message generation, type-2 challenge validation, type-3 response generation via InitializeSecurityContext, and resource cleanup.

Read this subtree for the SSPI-side NTLM three-message handshake state held in the ntlm struct.

Parent: [Authentication \(vauth\)](r8-authentication.md)

## Units (5)

<a id="u-7ad8b69acd4a"></a>
### `lib/vauth/ntlm_sspi.c:Curl_auth_is_ntlm_supported`

`bool Curl_auth_is_ntlm_supported(void)` · [lib/vauth/ntlm_sspi.c:L42-L58][f1]

Reports whether the Windows SSPI security library exposes an NTLM package.

It calls QuerySecurityPackageInfo for SP_NAME_NTLM; on SEC_E_OK it releases the returned package info with FreeContextBuffer and returns TRUE, otherwise FALSE. Any non-OK status yields FALSE with no logging.

**Uncertainties.**

- The buffer is only freed on success; behavior for statuses that populate the buffer without SEC_E_OK is unobservable here.

<a id="u-45b220a64032"></a>
### `lib/vauth/ntlm_sspi.c:Curl_auth_create_ntlm_type1_message`

`CURLcode Curl_auth_create_ntlm_type1_message(struct Curl_easy *data, struct Curl_cred…` · [lib/vauth/ntlm_sspi.c:L78-L182][f1]

Builds the initial NTLM type-1 message via SSPI, storing state in ntlm and the result in out.

It first resets prior state via Curl_auth_cleanup_ntlm, then queries the NTLM package; failure logs via failf and returns CURLE_AUTH_ERROR. It caches the package's max token size, allocates the output token (CURLE_OUT_OF_MEMORY on failure), and builds an identity only when the credentials carry a user, otherwise passing NULL for single sign-on. It allocates and acquires a credentials handle (CURLE_LOGIN_DENIED on acquire failure, after freeing the handle), allocates a context handle, and builds an SPN from the credential's SASL service if present, else the default service. InitializeSecurityContext generates the token: SEC_I_COMPLETE_NEEDED/SEC_I_COMPLETE_AND_CONTINUE trigger CompleteAuthToken; SEC_E_INSUFFICIENT_MEMORY returns CURLE_OUT_OF_MEMORY; any other status than SEC_E_OK or SEC_I_CONTINUE_NEEDED returns CURLE_AUTH_ERROR. On success the raw output token buffer (not copied) is published into out.

**Notes.**

- side_effect: On success out aliases ntlm->output_token without copying; its lifetime is tied to ntlm state.

calls: [lib/vauth/ntlm_sspi.c:Curl_auth_cleanup_ntlm](r8-auth-sspi-ntlm.md#u-e77c4ca2ad4e); uses: [lib/vauth/ntlm_sspi.c:Curl_auth_create_ntlm_type3_message](r8-auth-sspi-ntlm.md#u-837c115b0056)

**Uncertainties.**

- CompleteAuthToken's return value is discarded here; whether its failure leaves valid state is not provable from this code.

<a id="u-208e03a5a0a0"></a>
### `lib/vauth/ntlm_sspi.c:Curl_auth_decode_ntlm_type2_message`

`CURLcode Curl_auth_decode_ntlm_type2_message(struct Curl_easy *data, const struct buf…` · [lib/vauth/ntlm_sspi.c:L197-L215][f1]

Validates and stores the server's NTLM type-2 challenge.

An empty bufref logs an info message and returns CURLE_BAD_CONTENT_ENCODING. Otherwise the challenge is duplicated into ntlm->input_token via curlx_memdup0 (CURLE_OUT_OF_MEMORY on allocation failure), its length stored in ntlm->input_token_len, and CURLE_OK returned. Despite the name, no decoding is performed.

<a id="u-837c115b0056"></a>
### `lib/vauth/ntlm_sspi.c:Curl_auth_create_ntlm_type3_message`

`CURLcode Curl_auth_create_ntlm_type3_message(struct Curl_easy *data, struct Curl_cred…` · [lib/vauth/ntlm_sspi.c:L233-L313][f1]

Completes NTLM authentication by feeding the stored type-2 challenge to InitializeSecurityContext to produce the type-3 response.

The input descriptor holds the challenge; if ntlm->sslContext is set, endpoint bindings are queried (SECPKG_ATTR_ENDPOINT_BINDINGS) and, on SEC_E_OK, a second SECBUFFER_CHANNEL_BINDINGS buffer is appended for IIS extended protection. The bindings buffer is released with FreeContextBuffer once the handshake call returns. Any non-SEC_E_OK status logs an info message and maps SEC_E_INSUFFICIENT_MEMORY to CURLE_OUT_OF_MEMORY, everything else to CURLE_AUTH_ERROR. On success the token is copied into out via Curl_bufref_memdup0, all NTLM state is released through Curl_auth_cleanup_ntlm, and the copy result is returned.

calls: [lib/vauth/ntlm_sspi.c:Curl_auth_cleanup_ntlm](r8-auth-sspi-ntlm.md#u-e77c4ca2ad4e)

**Uncertainties.**

- creds is explicitly cast to void; any credential influence on the type-3 message is outside this file.

<a id="u-e77c4ca2ad4e"></a>
### `lib/vauth/ntlm_sspi.c:Curl_auth_cleanup_ntlm`

`void Curl_auth_cleanup_ntlm(struct ntlmdata *ntlm)` · [lib/vauth/ntlm_sspi.c:L325-L351][f1]

Releases all SSPI resources held in the ntlmdata struct.

It deletes and frees the context and credentials handles (each guarded by a non-NULL check), frees the identity via Curl_sspi_free_identity, frees input/output tokens and the SPN with curlx_safefree, and resets token_max to 0. Safe to call on partially initialized or already-cleaned state.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vauth/ntlm_sspi.c
