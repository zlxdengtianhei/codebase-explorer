# Auth Core Helpers

**Capability.** Provides connection-scoped state helpers for NTLM/Kerberos5/GSASL/SPNEGO, SPN formatting, domain detection in user names, and the policy deciding whether auth data may cross to a host or origin.

Consult this subtree for the shared building blocks used by all mechanisms. The allowed-to-host/origin policy is consumed by proxy header handling when building tunnel requests.

**Depended on by.**

- [HTTP/HTTPS Proxy Filter](r8-http-proxy-filter.md) · graph-confirmed · 1 edge(s)

Parent: [Authentication \(vauth\)](r8-authentication.md)

## Units (6)

<a id="u-e80142ce45ab"></a>
### `vauth.c-conn-meta-helpers`

`static void ntlm_conn_dtor(const void *key, size_t klen, void *entry)` · [lib/vauth/vauth.c:L153-L161][f1]

Connection-scoped authentication state helpers for NTLM, Kerberos5, GSASL and SPNEGO, all following the same pattern.

Each *_get function looks up a named metadata key on the connection (proxy variants use a distinct key) via Curl_conn_meta_get; when absent it allocates a zeroed struct with curlx_calloc and attaches it with Curl_conn_meta_set along with a destructor, returning NULL if either allocation or attachment fails. The corresponding static *_conn_dtor destructors invoke the protocol's cleanup routine (Curl_auth_cleanup_ntlm, Curl_auth_cleanup_gssapi, Curl_auth_gsasl_cleanup, Curl_auth_cleanup_spnego) and free the struct, so connection teardown releases per-connection auth state automatically. Curl_auth_ntlm_remove detaches the NTLM entry (proxy-aware key) which triggers its destructor. The Kerberos5 getter has no proxy variant.

**Notes.**

- failure: Each getter returns NULL when calloc fails or Curl_conn_meta_set fails, leaving no partially attached entry observable from the getter's contract.

calls: [Curl_auth_cleanup_ntlm][f2]

**Uncertainties.**

- Whether Curl_conn_meta_set takes ownership on failure (freeing the allocation) is not shown in this source; the code simply returns NULL in that case.

<a id="u-b40ef243f4ef"></a>
### `vauth.c-curl-auth-build-spn`

`char *Curl_auth_build_spn(const char *service, const char *host, const char *realm)` · [lib/vauth/vauth.c:L49-L64][f1]

Two conditional definitions of Curl_auth_build_spn share this symbol.

The non-SSPI variant formats 'service/host@realm', 'service/host' or 'service@realm' with curl_maprintf and returns NULL when neither host nor realm is supplied. The Windows SSPI variant ignores realm, always builds 'service/host' as UTF-8, returns NULL on allocation failure, then converts the string to a TCHAR buffer with curlx_convert_UTF8_to_tchar and frees the UTF-8 intermediate; the caller receives the TCHAR allocation.

uses: [Curl_auth_build_spn](r8-auth-core.md#u-54b25784cc6d)

**Uncertainties.**

- The SSPI variant assumes host is non-NULL; passing NULL yields a formatted 'service/(null)' result whose behavior is not established by this source.

<a id="u-36ccb0ce8dab"></a>
### `Curl_auth_allowed_to_host`

`bool Curl_auth_allowed_to_host(struct Curl_easy *data)` · [lib/vauth/vauth.c:L140-L143][f1]

Tells whether sensitive data such as authentication or cookies may be sent to the connection's origin host.

It simply delegates to Curl_auth_allowed_to_origin using data->state.origin as the target, so the outcome equals the allow_auth_to_other_hosts setting or equality with the initial origin.

calls: [Curl_auth_allowed_to_origin](r8-auth-core.md#u-ca20a501f98c); uses: [Curl_add_custom_headers](r6-http-request-build.md#u-2ee07804c56c)

<a id="u-ca20a501f98c"></a>
### `Curl_auth_allowed_to_origin`

`bool Curl_auth_allowed_to_origin(struct Curl_easy *data, struct Curl_peer *origin)` · [lib/vauth/vauth.c:L145-L150][f1]

Decides whether credentials may cross to an arbitrary origin: it returns TRUE when data->set.allow_auth_to_other_hosts is set, or when the given origin peer equals data->state.initial_origin as determined by Curl_peer_equal.

Setting allow_auth_to_other_hosts bypasses the origin comparison entirely.

calls: [Curl_peer_equal](r3-peer-identity.md#u-c6bb91e928c8)

<a id="u-54b25784cc6d"></a>
### `Curl_auth_build_spn`

`char *Curl_auth_build_spn(const char *service, const char *host, const char *realm)` · [lib/vauth/vauth.c:L49-L64][f1]

Non-Windows-SSPI build: formats an SPN from service, host and realm.

When both host and realm are given it produces 'service/host@realm'; host only gives 'service/host'; realm only gives 'service@realm'; if neither is present the result is NULL. The string is allocated by curl_maprintf and the caller owns it; allocation failure yields NULL.

group: [vauth.c-curl-auth-build-spn](r8-auth-core.md#u-b40ef243f4ef)

**Uncertainties.**

- Which of the two Curl_auth_build_spn definitions a given build compiles depends on USE_WINDOWS_SSPI; only the non-SSPI variant is fully visible here and the SSPI variant delegates via curlx_convert_UTF8_to_tchar.

<a id="u-1e92b0795a02"></a>
### `Curl_auth_user_contains_domain`

`bool Curl_auth_user_contains_domain(struct Curl_creds *creds)` · [lib/vauth/vauth.c:L115-L134][f1]

Reports whether the credentials carry a usable domain or UPN.

If credentials have a user, it searches for the first '\', '/' or '@'; the result is TRUE only when such a separator exists and is neither the first nor the last character of the user string, so a leading or trailing separator fails. Without a user, the result is FALSE unless the build has GSS-API or Windows SSPI, in which case the domain comes from the credentials cache or the logged-in user and TRUE is returned.

**Notes.**

- contract: An empty or separator-free user name is treated as containing no domain.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vauth/vauth.c
[f2]: ../../../../../../eval/curl-2c04412/lib/vauth/ntlm.c
