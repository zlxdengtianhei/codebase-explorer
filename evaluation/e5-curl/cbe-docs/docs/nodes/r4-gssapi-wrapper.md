# GSSAPI wrapper and debug stub

**Capability.** libcurl's wrappers around the GSS-API entry points, uniformly routing to an in-memory scripted stub implementation when CURL_GSS_STUB and CURL_STUB_GSS_CREDS are active, plus GSS error logging helpers.

Consult this node to see how every GSS call is funneled through a single dispatch pattern (real vs stub) and how GSS errors are rendered; the stub types support debug-only handshakes.

**Depended on by.**

- [Kerberos V5 GSSAPI auth](r4-krb5-gssapi-auth.md) · model-inferred · 0 edge(s)

Parent: [Authentication and crypto primitives](r4-auth-crypto.md)

## Units (17)

<a id="u-4ede8ee6790e"></a>
### `lib-curl-gssapi-stub-types`

`enum min_err_code` · [lib/curl_gssapi.c:L71-L80][f1]

Type definitions used only by the CURL_GSS_STUB debug implementation.

enum min_err_code enumerates the minor status codes (OK through NO_MECH) written into the minor-status output. struct stub_gss_ctx_id_t_desc models a fake context: a 'sent' state machine value (NONE, KRB5, NTLM1, NTLM3), have_krb5/have_ntlm capability flags, saved request flags, and a 250-byte creds string copied from the environment. struct stub_gss_cred_id_t_desc models a fake credential with allow_krb5/allow_ntlm flags that gate which mechanisms a new context may use.

<a id="u-5b47a720cc67"></a>
### `Curl_gss_acquire_cred`

`OM_uint32 Curl_gss_acquire_cred(OM_uint32 *minor_status, gss_name_t desired_name, OM_…` · [lib/curl_gssapi.c:L587-L606][f1]

Acquires GSS credentials, routing to stub_gss_acquire_cred when the stub is compiled and CURL_STUB_GSS_CREDS is set; all eight parameters are forwarded unchanged in either path.

calls: [stub_gss_acquire_cred](r4-gssapi-wrapper.md#u-5ab59036f350)

<a id="u-0d1d40e1d983"></a>
### `Curl_gss_delete_sec_context`

`OM_uint32 Curl_gss_delete_sec_context(OM_uint32 *min, gss_ctx_id_t *context, gss_buff…` · [lib/curl_gssapi.c:L556-L568][f1]

Deletes a GSS security context, routing to the stub implementation when CURL_GSS_STUB is compiled and CURL_STUB_GSS_CREDS is present in the environment; otherwise calls the real gss_delete_sec_context with the same arguments.

calls: [stub_gss_delete_sec_context](r4-gssapi-wrapper.md#u-27eb36245657)

<a id="u-1c63dfd7901f"></a>
### `Curl_gss_indicate_mechs`

`OM_uint32 Curl_gss_indicate_mechs(OM_uint32 *minor_status, gss_OID_set *mech_set)` · [lib/curl_gssapi.c:L608-L617][f1]

Reports available GSS mechanisms, dispatching to stub_gss_indicate_mechs when the stub is compiled and CURL_STUB_GSS_CREDS is set; otherwise calls gss_indicate_mechs with the same minor status and mech set.

calls: [stub_gss_indicate_mechs](r4-gssapi-wrapper.md#u-dec29b9ef2a3)

<a id="u-58a90f7b3150"></a>
### `Curl_gss_init_sec_context`

`OM_uint32 Curl_gss_init_sec_context(struct Curl_easy *data, OM_uint32 *minor_status, …` · [lib/curl_gssapi.c:L494-L554][f1]

libcurl's wrapper around gss_init_sec_context that assembles request flags before dispatching.

req_flags always includes GSS_C_REPLAY_FLAG; mutual_auth adds GSS_C_MUTUAL_FLAG. Delegation: CURLGSSAPI_DELEGATION_POLICY_FLAG adds GSS_C_DELEG_POLICY_FLAG when the macro exists, otherwise logs a warning and omits it; CURLGSSAPI_DELEGATION_FLAG adds GSS_C_DELEG_FLAG. When compiled with CURL_GSS_STUB and CURL_STUB_GSS_CREDS is set in the environment, it redirects to stub_gss_init_sec_context with actual_mech_type and time_rec passed as NULL; otherwise it forwards all arguments to the real gss_init_sec_context with the same NULL slots and time_req 0.

calls: [stub_gss_init_sec_context](r4-gssapi-wrapper.md#u-3c010d60b139)

**Uncertainties.**

- Behavior when data->set.gssapi_delegation was not initialized by the caller is not visible here

<a id="u-6873e479ad78"></a>
### `Curl_gss_inquire_context`

`OM_uint32 Curl_gss_inquire_context(OM_uint32 *minor_status, gss_ctx_id_t context, gss…` · [lib/curl_gssapi.c:L570-L585][f1]

Queries a context's mechanism OID, dispatching to stub_gss_inquire_context when the stub is compiled and CURL_STUB_GSS_CREDS is set, passing NULL for all outputs except mech_type; otherwise forwards identically to gss_inquire_context.

calls: [stub_gss_inquire_context](r4-gssapi-wrapper.md#u-d971ad42568a)

<a id="u-b62330c927f6"></a>
### `Curl_gss_log_error`

`void Curl_gss_log_error(struct Curl_easy *data, const char *prefix, OM_uint32 major, …` · [lib/curl_gssapi.c:L686-L698][f1]

Logs a GSS-API error as an info message under CURLVERBOSE.

It formats the major status via display_gss_error only when it differs from GSS_S_FAILURE, then always formats the minor status as a mech code into the same 1024-byte buffer, and finally emits 'prefix + text' through infof on the session handle.

calls: [display_gss_error](r4-gssapi-wrapper.md#u-161b82225baa)

<a id="u-235d9967a844"></a>
### `Curl_gss_release_cred`

`OM_uint32 Curl_gss_release_cred(OM_uint32 *minor_status, gss_cred_id_t *cred_handle)` · [lib/curl_gssapi.c:L633-L642][f1]

Releases GSS credentials, routing to stub_gss_release_cred when the stub is compiled and CURL_STUB_GSS_CREDS is set; otherwise calls gss_release_cred with the same minor-status pointer and handle.

calls: [stub_gss_release_cred](r4-gssapi-wrapper.md#u-94400d568f7c)

<a id="u-c59d2a759511"></a>
### `Curl_gss_set_neg_mechs`

`OM_uint32 Curl_gss_set_neg_mechs(OM_uint32 *minor_status, gss_cred_id_t cred_handle, …` · [lib/curl_gssapi.c:L620-L630][f1]

Restricts the mechanisms a credential will negotiate, compiled only with HAVE_GSS_SET_NEG_MECHS.

Dispatches to stub_gss_set_neg_mechs when the stub is active and CURL_STUB_GSS_CREDS is set, else forwards to gss_set_neg_mechs with identical arguments.

calls: [stub_gss_set_neg_mechs](r4-gssapi-wrapper.md#u-5c51fbcd204b)

<a id="u-161b82225baa"></a>
### `display_gss_error`

`static size_t display_gss_error(OM_uint32 status, int type, char *buf, size_t len)` · [lib/curl_gssapi.c:L646-L672][f1]

Renders GSS status codes into a text buffer under CURLVERBOSE.

It repeatedly calls gss_display_status (starting with msg_ctx 0) for the given status and code type, appending each non-empty message as '%.*s. ' via curl_msnprintf only while the running total stays within the fixed 1024-byte GSS_LOG_BUFFER_LEN; oversized messages are skipped but the buffer is still released. The loop continues while the major status is not an error and msg_ctx is non-zero, returning the updated length. When the gss_display_status call itself fails, the loop terminates after releasing the buffer.

**Uncertainties.**

- Whether curl_msnprintf can truncate and thus return a length larger than requested is not determinable from this file

<a id="u-5ab59036f350"></a>
### `stub_gss_acquire_cred`

`static OM_uint32 stub_gss_acquire_cred( OM_uint32 *min, gss_name_t desired_name, OM_u…` · [lib/curl_gssapi.c:L371-L405][f1]

Allocates a stub credential that allows all mechanisms.

NULL minor status fails; otherwise minor is cleared. If output_cred_handle is non-NULL, a zeroed stub credential is allocated with allow_krb5 and allow_ntlm both set to 1; allocation failure sets STUB_GSS_NO_MEMORY and fails. All other GSS parameters are ignored. Returns GSS_S_COMPLETE.

<a id="u-27eb36245657"></a>
### `stub_gss_delete_sec_context`

`static OM_uint32 stub_gss_delete_sec_context( OM_uint32 *min, struct stub_gss_ctx_id_…` · [lib/curl_gssapi.c:L300-L323][f1]

Frees a stub GSS security context.

A NULL minor-status pointer returns GSS_S_FAILURE without touching it; a NULL context pointer or a NULL *context sets STUB_GSS_INVALID_CTX and fails. Otherwise it safe-frees the context, clears the minor status, and returns GSS_S_COMPLETE; the output token parameter is ignored.

<a id="u-dec29b9ef2a3"></a>
### `stub_gss_indicate_mechs`

`static OM_uint32 stub_gss_indicate_mechs( OM_uint32 *min, gss_OID_set *mech_set)` · [lib/curl_gssapi.c:L407-L436][f1]

Builds the set of supported mechanism OIDs from CURL_STUB_GSS_CREDS.

NULL minor status fails; a missing env value sets STUB_GSS_INVALID_CREDS and fails. It creates an empty OID set via gss_create_empty_oid_set (propagating its major status on error), always adds the Kerberos mech OID, and adds the NTLMSSP OID only when the creds string contains 'NTLM'. Returns GSS_S_COMPLETE.

uses: [stub_gss_acquire_cred](r4-gssapi-wrapper.md#u-5ab59036f350)

**Uncertainties.**

- Failure of gss_add_oid_set_member calls is not checked; their outcome does not change the return value

<a id="u-3c010d60b139"></a>
### `stub_gss_init_sec_context`

`static OM_uint32 stub_gss_init_sec_context( OM_uint32 *min, gss_cred_id_t initiator_c…` · [lib/curl_gssapi.c:L101-L298][f1]

Drives a scripted, in-memory GSS security-context handshake for debug builds.

It reads credentials from the CURL_STUB_GSS_CREDS environment variable and produces base64-space tokens of the form 'creds:target:type:padding' padded with 'A'. Validation order: a NULL minor-status pointer fails without setting it; missing context/target/output pointers set STUB_GSS_INVALID_ARGS; missing or oversized CURL_STUB_GSS_CREDS sets STUB_GSS_INVALID_CREDS; a mismatch between an existing context's stored creds and the current env value sets STUB_GSS_INVALID_CREDS. With no input token (first call) it requires no existing context, allocates a stub context, marks have_krb5/have_ntlm by substring search of creds, applies credential restrictions, picks the initial sent state (KRB5 preferred, else NTLM1), copies the creds into the context, and returns GSS_S_CONTINUE_NEEDED; having neither mech frees the context and sets STUB_GSS_NO_MECH. With an input token only 'D' (done) or 'C' (continue) are accepted; other first bytes set STUB_GSS_SERVER_ERR. 'D' completes only from KRB5 or NTLM3 states (returning saved flags and indefinite lifetime) and fails otherwise; 'C' advances KRB5 to NTLM1 when NTLM is available (else SERVER_ERR) and NTLM1 to NTLM3, other states fail. A continue with a token but no context sets STUB_GSS_INVALID_CTX. Token allocation or gss_display_name failure frees the context and sets STUB_GSS_NO_MEMORY; likewise if the rendered token would overflow the creds-size bound or fill the buffer. On success it stores the context, returns the padded token, and always returns CONTINUE_NEEDED on token-producing calls.

uses: [Curl_gss_init_sec_context](r4-gssapi-wrapper.md#u-58a90f7b3150)

**Uncertainties.**

- Whether curlx_calloc/curlx_free/strcopy can fail beyond the checked NULL returns is not visible in this file

<a id="u-d971ad42568a"></a>
### `stub_gss_inquire_context`

`static OM_uint32 stub_gss_inquire_context( OM_uint32 *min, struct stub_gss_ctx_id_t_d…` · [lib/curl_gssapi.c:L330-L370][f1]

Reports the mechanism OID of a stub context.

NULL minor status fails; a NULL context sets STUB_GSS_INVALID_CTX and fails. All inquiry outputs except mech_type are ignored. When mech_type is requested, NTLM1/NTLM3 states map to the NTLMSSP OID and any other state (KRB5, NONE) maps to the Kerberos mech OID; returns GSS_S_COMPLETE.

uses: [lib-curl-gssapi-stub-types](r4-gssapi-wrapper.md#u-4ede8ee6790e)

<a id="u-94400d568f7c"></a>
### `stub_gss_release_cred`

`static OM_uint32 stub_gss_release_cred( OM_uint32 *min, gss_cred_id_t *cred_handle)` · [lib/curl_gssapi.c:L477-L490][f1]

Frees a stub credential.

NULL minor status fails; otherwise minor is cleared, and a non-NULL handle other than GSS_C_NO_CREDENTIAL is freed and reset to GSS_C_NO_CREDENTIAL. Always returns GSS_S_COMPLETE on the minor-status path.

<a id="u-5c51fbcd204b"></a>
### `stub_gss_set_neg_mechs`

`static OM_uint32 stub_gss_set_neg_mechs(OM_uint32 *min, gss_cred_id_t cred_handle, co…` · [lib/curl_gssapi.c:L440-L474][f1]

Records which mechanisms a stub credential may negotiate by comparing each OID in mech_set against the Kerberos and NTLMSSP OIDs.

NULL minor status fails; GSS_C_NO_CREDENTIAL fails without clearing minor after it was zeroed. A NULL mech_set leaves both allow flags at 0. Otherwise allow_krb5/allow_ntlm are set to 1 only for exact OID length+byte matches, and GSS_S_COMPLETE is returned.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curl_gssapi.c
