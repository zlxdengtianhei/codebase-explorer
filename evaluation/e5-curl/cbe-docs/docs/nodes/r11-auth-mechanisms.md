# authentication mechanisms

**Capability.** SASL/auth state declarations and concrete message builders: Kerberos V5 over Windows SSPI and OAUTHBEARER/XOAUTH2 token formatting.

vauth.h defines the per-mechanism state structs and prototypes shared by all builders; krb5_sspi.c implements the Kerberos handshake lifecycle (support probe, user/security messages, cleanup) and oauth2.c formats the two bearer message styles. Consult vauth.h first for the contract each mechanism implements.

Parent: [curl codebase](r11-curl-codebase.md)

## Units (7)

<a id="u-e36bf8160fde"></a>
### `vauth-h-auth-state-structs-and-prototypes`

`struct gsasldata` · [lib/vauth/vauth.h:L129-L132][f1]

Header declaring the SASL/authentication state structs (gsasldata, ntlmdata, kerberos5data, negotiatedata) and prototypes for all auth message builders, decoders, support checks, and cleanup functions, with conditional compilation per mechanism.

**Notes.**

- contract: Structs are conditionally defined: gsasldata only under USE_GSASL, ntlmdata under USE_NTLM (with Windows SSPI vs native field layouts), kerberos5data under USE_KERBEROS5 (SSPI vs GSS-API variants), negotiatedata under USE_SPNEGO (GSS-API vs SSPI variants)
- contract: When mechanisms are compiled out, stub macros substitute support checks and cleanup: Curl_auth_is_digest_supported() FALSE, Curl_auth_digest_cleanup(x) no-op, Curl_auth_is_ntlm_supported() FALSE, Curl_auth_is_gssapi_supported() FALSE
- field: Connection meta keys are declared as macros: CURL_META_GSASL_CONN, CURL_META_NTLM_CONN, CURL_META_NTLM_PROXY_CONN, CURL_META_KRB5_CONN, CURL_META_NEGO_CONN, CURL_META_NEGO_PROXY_CONN
- contract: Curl_auth_build_spn returns TCHAR* on Windows SSPI builds and char* otherwise; GSS_ERROR is defined for SSPI builds as (status) & 0x80000000

**Uncertainties.**

- Implementation behavior of the declared functions lives in other files; only signatures and compile-time selection are observable here
- The diagnostic notes the file parsed as C; any C++ semantics cannot be confirmed

<a id="u-e496bbccb567"></a>
### `lib/vauth/krb5_sspi.c:Curl_auth_is_gssapi_supported`

`bool Curl_auth_is_gssapi_supported(void)` · [lib/vauth/krb5_sspi.c:L42-L58][f2]

Probes Kerberos V5 availability under Windows SSPI by querying the package named SP_NAME_KERBEROS.

On SEC_E_OK the returned package-info buffer is freed and true is returned; any other status returns false without diagnostics.

<a id="u-0a953d3d7783"></a>
### `lib/vauth/krb5_sspi.c:Curl_auth_create_gssapi_user_message`

`CURLcode Curl_auth_create_gssapi_user_message(struct Curl_easy *data, struct Curl_cre…` · [lib/vauth/krb5_sspi.c:L81-L223][f2]

Advances the Kerberos V5 SASL handshake, caching SPN, token buffer, credentials, and context on the krb5 struct across calls.

Lazy setup: if no SPN it is built from service (creds' SASL service or default_service) and host; if no output token the package is queried (failure: CURLE_AUTH_ERROR after failf) and token_max/token buffer allocated; if no credentials handle an identity is built from creds or NULL is used for single sign-on, a credentials handle is allocated and acquired (acquire failure frees the handle and returns CURLE_LOGIN_DENIED), and a context handle is allocated. When a challenge is present it must be non-empty (else CURLE_BAD_CONTENT_ENCODING after infof) and becomes an input buffer. InitializeSecurityContext is called with mutual-auth flag, NULL input on the first leg. SEC_E_INSUFFICIENT_MEMORY returns CURLE_OUT_OF_MEMORY; other non-OK/non-CONTINUE statuses return CURLE_AUTH_ERROR. If the produced context differs from the stored one the old is deleted and the new copied in. Output: a non-empty response is memdup'd (NUL-terminated) into out via Curl_bufref_memdup0; an empty response sets an empty string when mutual_auth is requested, otherwise a NULL bufref. The result of the memdup is returned.

uses: [Curl_bufref_set](r14-bufref-buffers.md#u-214d3ce6e368)

**Uncertainties.**

- Identity built into krb5->identity is not freed on later failures (e.g., calloc of credentials or context failing), so partial state may persist on error.
- Whether the local context copy must match krb5->context on the second leg, and the consequence if memcmp differs on a continued handshake, depends on SSPI semantics not shown.

<a id="u-ab41f818d5a4"></a>
### `lib/vauth/krb5_sspi.c:Curl_auth_create_gssapi_security_message`

`CURLcode Curl_auth_create_gssapi_security_message(struct Curl_easy *data, const char …` · [lib/vauth/krb5_sspi.c:L241-L418][f2]

Completes the Kerberos V5 SASL security-layer negotiation by decrypting the server's security message and returning an encrypted client reply.

An empty challenge returns CURLE_BAD_CONTENT_ENCODING after infof. QueryContextAttributes for sizes maps insufficient memory to CURLE_OUT_OF_MEMORY and other failures to CURLE_AUTH_ERROR. DecryptMessage decrypts in place; failure returns CURLE_BAD_CONTENT_ENCODING. The decrypted payload must be exactly 4 bytes (else CURLE_BAD_CONTENT_ENCODING); byte 0 is the security layer, which must include KERB_WRAP_NO_ENCRYPT (else CURLE_BAD_CONTENT_ENCODING), and the 3-byte max size is forcibly zeroed because no encryption layer is requested. Then trailer, message (security-layer byte plus zeroed size plus optional authzid), and padding buffers are allocated; any allocation failure jumps to a shared cleanup returning CURLE_OUT_OF_MEMORY. EncryptMessage failure maps to CURLE_OUT_OF_MEMORY or CURLE_AUTH_ERROR and also goes to cleanup. On success the three wrapped buffers are concatenated into appdata which is handed to the caller's bufref with curl_free. All local buffers (padding, message, trailer) are freed on every path via the out label.

**Uncertainties.**

- Whether DEBUGASSERT(chlg) compiles in a check or is a no-op depends on build flags not visible here.
- appdatalen is computed before the concatenation memcpys; if EncryptMessage returned success but left buffer sizes inconsistent the concatenation could exceed appdata — this relies on SSPI contract, not code shown.

<a id="u-48d27301484c"></a>
### `lib/vauth/krb5_sspi.c:Curl_auth_cleanup_gssapi`

`void Curl_auth_cleanup_gssapi(struct kerberos5data *krb5)` · [lib/vauth/krb5_sspi.c:L430-L454][f2]

Releases all Kerberos V5 SSPI state held on the krb5 struct: deletes and frees the security context when present, frees the credentials handle likewise, releases and nulls the identity, frees the SPN and output token, and zeroes token_max.

The struct is reset for a subsequent handshake.

<a id="u-983099134dbd"></a>
### `Curl_auth_create_oauth_bearer_message`

`CURLcode Curl_auth_create_oauth_bearer_message(struct Curl_creds *creds, const char *…` · [lib/vauth/oauth2.c:L50-L71][f3]

Formats an OAUTHBEARER (RFC 7628) client response from the credentials' user and bearer token.

When port is 0 or 80 the message omits the port field; otherwise a port=%ld field is inserted. Fields are delimited with SOH (\1) bytes. curl_maprintf failure returns CURLE_OUT_OF_MEMORY; success transfers the allocated string into out via Curl_bufref_set with curl_free as destructor.

uses: [Curl_auth_create_xoauth_bearer_message](r11-auth-mechanisms.md#u-395cd8dc679e)

<a id="u-395cd8dc679e"></a>
### `Curl_auth_create_xoauth_bearer_message`

`CURLcode Curl_auth_create_xoauth_bearer_message(struct Curl_creds *creds, struct bufr…` · [lib/vauth/oauth2.c:L87-L99][f3]

Formats the legacy XOAUTH2 string 'user=<user>\1auth=Bearer <token>\1\1' from the credentials' user and bearer token.

Allocation failure via curl_maprintf returns CURLE_OUT_OF_MEMORY; otherwise the string is placed in out with Curl_bufref_set and a curl_free destructor, returning CURLE_OK.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vauth/vauth.h
[f2]: ../../../../../../eval/curl-2c04412/lib/vauth/krb5_sspi.c
[f3]: ../../../../../../eval/curl-2c04412/lib/vauth/oauth2.c
