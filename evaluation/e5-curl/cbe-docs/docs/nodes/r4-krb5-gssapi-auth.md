# Kerberos V5 GSSAPI auth

**Capability.** Generates the Kerberos V5 GSSAPI authentication tokens and the RFC 4752 security-layer message, and releases the per-auth state, building on the GSSAPI wrapper.

Read this for the SPNEGO/Kerberos5 authentication flow: SPN import, context initiation, security-layer negotiation, and cleanup. Compiled only under HAVE_GSSAPI and USE_KERBEROS5.

**Depends on.**

- [GSSAPI wrapper and debug stub](r4-gssapi-wrapper.md) · model-inferred · 0 edge(s)

Parent: [Authentication and crypto primitives](r4-auth-crypto.md)

## Units (9)

<a id="u-033e177d6f8c"></a>
### `Curl_auth_cleanup_gssapi`

`void Curl_auth_cleanup_gssapi(struct kerberos5data *krb5)` · [lib/vauth/krb5_gssapi.c:L304-L320][f1]

Releases the Kerberos V5 GSSAPI state: deletes the security context and releases the SPN name, resetting both to their GSS empty sentinels.

**Notes.**

- side_effect: Only touches krb5->context and krb5->spn, and only when they differ from GSS_C_NO_CONTEXT / GSS_C_NO_NAME; after the call both are reset to those sentinels

<a id="u-2aa37b67cd6a"></a>
### `Curl_auth_create_gssapi_security_message`

`CURLcode Curl_auth_create_gssapi_security_message(struct Curl_easy *data, const char …` · [lib/vauth/krb5_gssapi.c:L178-L292][f1]

Generates the RFC 4752 security-layer reply: unwraps the server's 4-octet challenge, validates the security layer, then wraps and returns a response of layer, zero max size, and the optional authzid.

**Notes.**

- failure: Empty challenge, gss_unwrap error (CURLE_BAD_CONTENT_ENCODING), non-4-octet unwrapped data, or a sec_layer without GSSAUTH_P_NONE each log an info message and return CURLE_BAD_CONTENT_ENCODING
- condition: Only the N (none) layer is accepted; sec_layer is masked to GSSAUTH_P_NONE and any server-advertised max_size is reported back as zero since no encryption is used
- failure: curlx_malloc failure returns CURLE_OUT_OF_MEMORY; gss_wrap failure frees message and returns CURLE_AUTH_ERROR
- side_effect: On success the wrapped token is memdup0'd into out and both the GSS output buffer and the local message buffer are freed

uses: [vauth-h-auth-state-structs-and-prototypes](r11-auth-mechanisms.md#u-e36bf8160fde)

**Uncertainties.**

- Whether authzid is length-checked against buffer size: messagelen accounts for strlen(authzid) and the copy uses messagelen - 4, consistent only if authzid is non-NULL when counted

<a id="u-e79c08cad7ec"></a>
### `Curl_auth_create_gssapi_user_message`

`CURLcode Curl_auth_create_gssapi_user_message(struct Curl_easy *data, struct Curl_cre…` · [lib/vauth/krb5_gssapi.c:L76-L160][f1]

Generates the GSSAPI Kerberos V5 user token: imports the service SPN once into krb5->spn, runs gss_init_sec_context against the optional challenge, and copies the produced token into out.

**Notes.**

- condition: If krb5->spn is unset, the SPN is built from service (the creds' SASL service when present, else default_service) and host; SPN build failure returns CURLE_OUT_OF_MEMORY
- failure: gss_import_name or gss_init_sec_context failure logs the GSS error and returns CURLE_AUTH_ERROR; on init_sec_context failure the output_token is released first
- condition: A non-NULL chlg with zero length logs 'empty challenge message' and returns CURLE_BAD_CONTENT_ENCODING
- contract: On success: a non-empty output token is memdup'd (NUL-terminated) into out and released; an empty token sets out to "" for mutual_auth or NULL otherwise, and CURLE_OK is returned unless memdup fails

uses: [vauth-h-auth-state-structs-and-prototypes](r11-auth-mechanisms.md#u-e36bf8160fde); imports: [cram.c module code (L1–L48)](r9-cram-auth.md#u-383916a337a8)

**Uncertainties.**

- Curl_gss_init_sec_context and Curl_auth_build_spn implementations are outside this batch; their exact state transitions and return conventions are inferred from usage here

<a id="u-3713ca353da5"></a>
### `Curl_auth_is_gssapi_supported`

`bool Curl_auth_is_gssapi_supported(void)` · [lib/vauth/krb5_gssapi.c:L50-L53][f1]

Reports GSSAPI support for the Kerberos V5 mechanism; always returns TRUE in this GSSAPI build.

<a id="u-c480a92cbfc3"></a>
### `krb5_gssapi.c module code (L1–L49)`

`module_region` · [lib/vauth/krb5_gssapi.c:L1-L49][f1]

License header, includes, and compile guards for the GSSAPI Kerberos V5 module; body compiled only under HAVE_GSSAPI and USE_KERBEROS5, with an Apple deprecation-warning suppression when diagnostics are enabled.

**Notes.**

- condition: The #pragma GCC diagnostic push/ignored block suppresses -Wdeprecated-declarations on Apple builds without HAVE_GSSAPPLE, balanced by a pop near file end

<a id="u-6439a785bdc4"></a>
### `krb5_gssapi.c module code (L292–L303)`

`module_region` · [lib/vauth/krb5_gssapi.c:L292-L303][f1]

Comment block documenting Curl_auth_cleanup_gssapi; non-behavioral.

<a id="u-f84655f429ab"></a>
### `krb5_gssapi.c module code (L320–L326)`

`module_region` · [lib/vauth/krb5_gssapi.c:L320-L326][f1]

Diagnostic pop and closing guards for HAVE_GSSAPI && USE_KERBEROS5; non-behavioral.

<a id="u-587c8d6bbbcc"></a>
### `krb5_gssapi.c module code (L53–L75)`

`module_region` · [lib/vauth/krb5_gssapi.c:L53-L75][f1]

Comment block documenting Curl_auth_create_gssapi_user_message parameters; non-behavioral.

<a id="u-418a102eccc1"></a>
### `krb5_gssapi.c module code (L160–L177)`

`module_region` · [lib/vauth/krb5_gssapi.c:L160-L177][f1]

Comment block documenting Curl_auth_create_gssapi_security_message parameters; non-behavioral.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vauth/krb5_gssapi.c
