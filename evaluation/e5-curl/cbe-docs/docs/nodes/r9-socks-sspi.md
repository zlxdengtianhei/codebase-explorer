# SOCKS5 GSS-API/SSPI

**Capability.** Performs the full SOCKS5 GSS-API negotiation over the proxy connection: principal setup and credential acquisition, token handshake loop with 4-byte SOCKS5 framing, protection-level negotiation, SSPI error checking, and pass-through buffer cleanup.

Read this child to trace the SOCKS5 GSS-API exchange from setup through encrypt-level negotiation. All sub-steps funnel through check_sspi_err and the socks5_free* helpers.

**Depends on.**

- [HTTP/SOCKS authentication](r9-http-auth.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r9-socks-sspi ` → ` r9-http-auth `)

Parent: [HTTP/SOCKS authentication](r9-http-auth.md)

## Units (7)

<a id="u-e9b33c069530"></a>
### `lib/socks_sspi.c:Curl_SOCKS5_gssapi_negotiate`

`CURLcode Curl_SOCKS5_gssapi_negotiate(struct Curl_cfilter *cf, struct Curl_easy *data…` · [lib/socks_sspi.c:L472-L535][f1]

Public entry point performing full SOCKS5 GSS-API/SSPI negotiation over the proxy connection: setup, handshake loop, credential-attribute username query, and protection-level negotiation.

It zeroes the credential handle, context and names struct, then runs socks5_sspi_setup and socks5_sspi_loop; any failure jumps to the error path. On success it frees the service name, queries SECPKG_CRED_ATTR_NAMES for the authenticated username (an SSPI error here yields CURLE_COULDNT_CONNECT after a failf), logs the username (converted to UTF-8 only when verbose logging is compiled), frees the name buffer, and runs socks5_sspi_encrypt; its failure also goes to error. Success restores blocking mode via curlx_nonblock(sock, TRUE), deletes the security context and credential handle, and returns CURLE_OK. The error path also restores blocking, frees the service name and SSPI handle/context, and frees names.sUserName if still set, returning the propagated result.

**Notes.**

- side_effect: Both success and error paths switch the socket back to non-blocking mode before returning.

calls: [socks5_sspi_setup](r9-socks-sspi.md#u-86a3af6ce80c), [socks5_sspi_loop](r9-socks-sspi.md#u-deb31721f130), [socks5_sspi_encrypt](r9-socks-sspi.md#u-023a08163d6b), [check_sspi_err](r9-socks-sspi.md#u-6dfbb9ea5bab)

**Uncertainties.**

- The infof of user_utf8 is wrapped in VERBOSE() macros; logging behavior depends on compile-time verbose support not shown here.

<a id="u-6dfbb9ea5bab"></a>
### `check_sspi_err`

`static int check_sspi_err(struct Curl_easy *data, SECURITY_STATUS status, const char …` · [lib/socks_sspi.c:L42-L56][f1]

Checks an SSPI SECURITY_STATUS and logs failures.

Any status other than SEC_E_OK, SEC_I_COMPLETE_AND_CONTINUE, SEC_I_COMPLETE_NEEDED or SEC_I_CONTINUE_NEEDED is treated as an error: it emits a failf message naming the failing function and the SSPI error string, and returns 1. Acceptable statuses return 0 so the caller continues.

<a id="u-dc760bc84a08"></a>
### `socks5_free`

`static CURLcode socks5_free(SecBuffer *sspi_w_token, CURLcode result)` · [lib/socks_sspi.c:L252-L259][f1]

Frees the first three buffers of a SecBuffer array with curlx_safefree and returns the supplied CURLcode unchanged, serving as a pass-through cleanup for the EncryptMessage path's three-buffer descriptor.

<a id="u-27090537f2f5"></a>
### `socks5_free_token`

`static CURLcode socks5_free_token(SecBuffer *send_token, CURLcode result)` · [lib/socks_sspi.c:L93-L101][f1]

Frees an SSPI-allocated send token buffer via FreeContextBuffer when present, nulls the pointer, and passes the given CURLcode result through unchanged, enabling idioms like 'return socks5_free_token(&tok, CURLE_COULDNT_CONNECT)'.

<a id="u-023a08163d6b"></a>
### `socks5_sspi_encrypt`

`static CURLcode socks5_sspi_encrypt(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/socks_sspi.c:L261-L470][f1]

Negotiates the SOCKS5 GSS-API data-protection level after authentication and stores the agreed protection byte in the connection.

The protection level derives from the negotiated flags: ISC_REQ_CONFIDENTIALITY gives gss_enc 2, else ISC_REQ_INTEGRITY gives 1, else 0. If data->set.socks5_gssapi_nec is set, it sends a 4-byte request advertising length 1 and then the single gss_enc byte; otherwise it queries context sizes, builds a 3-buffer EncryptMessage request (trailer, 1-byte gss_enc data, padding), encrypts with KERB_WRAP_NO_ENCRYPT, concatenates the three buffers into etbuf (rejecting sizes over 0xffff with CURLE_COULDNT_CONNECT), sends the 4-byte header and then etbuf. It then reads the 4-byte reply: type 255 is a user rejection, any type other than 2 an invalid response, zero length an invalid token — all CURLE_COULDNT_CONNECT. The reply token is allocated and read in full; on read error it jumps to the fail label freeing the buffer and returning CURLE_COULDNT_CONNECT. Unless NEC mode, the token is decrypted in place via DecryptMessage with a STREAM/DATA descriptor pair and the 1-byte DATA result is copied; in NEC mode the raw single byte is checked instead; a length mismatch in either path fails with CURLE_COULDNT_CONNECT. On success it logs the granted protection and sets cf->conn->socks5_gssapi_enctype to the byte. Any allocation failure in the encrypt path returns CURLE_OUT_OF_MEMORY after socks5_free cleanup.

**Notes.**

- side_effect: Sets cf->conn->socks5_gssapi_enctype to the server-acknowledged protection byte on success.

calls: [check_sspi_err](r9-socks-sspi.md#u-6dfbb9ea5bab), [socks5_free](r9-socks-sspi.md#u-dc760bc84a08); uses: [socks5_free_token](r9-socks-sspi.md#u-27090537f2f5), [Curl_sspi_global_init](r1-platform-utilities.md#u-04f713aba199), [curl_sspi.h module code (L46–L103)](r5-protocol-headers.md#u-858c1a5dfaef)

**Uncertainties.**

- The NEC branch never reads a second payload beyond the decrypted token; whether NEC servers always send exactly one byte is assumed from the 1-byte check.
- qop output of DecryptMessage is not validated.

<a id="u-deb31721f130"></a>
### `socks5_sspi_loop`

`static CURLcode socks5_sspi_loop(struct Curl_cfilter *cf, struct Curl_easy *data, Cre…` · [lib/socks_sspi.c:L103-L250][f1]

Drives the SOCKS5 GSS-API/SSPI subnegotiation handshake: it repeatedly calls InitializeSecurityContext, sends produced tokens wrapped in 4-byte SOCKS5 headers (version 1, auth type 1, network-order 16-bit length), and reads server replies until the status is not SEC_I_CONTINUE_NEEDED.

Before the loop the socket is switched to blocking. Each iteration duplicates the service name in TCHAR; on conversion failure it frees the received token and returns CURLE_OUT_OF_MEMORY. An SSPI error, an outgoing token larger than 0xffff, or a failed/partial 4-byte header or token send returns CURLE_COULDNT_CONNECT, freeing the send token. When the loop continues, it blocks reading a 4-byte response: short reads return the read error or CURLE_COULDNT_CONNECT; response type 255 means the user was rejected and any type other than 1 is invalid, both CURLE_COULDNT_CONNECT; a zero-length token is likewise rejected. The advertised token length is then allocated (NULL allocation returns CURLE_OUT_OF_MEMORY) and read in full, with the same read-failure handling. After each continued iteration the context_handle is set to sspi_context so subsequent calls continue the existing context.

calls: [check_sspi_err](r9-socks-sspi.md#u-6dfbb9ea5bab), [socks5_free_token](r9-socks-sspi.md#u-27090537f2f5); uses: [Curl_sspi_global_init](r1-platform-utilities.md#u-04f713aba199)

**Uncertainties.**

- SEC_I_COMPLETE_NEEDED / SEC_I_COMPLETE_AND_CONTINUE statuses pass check_sspi_err but no CompleteAuthToken call is visible; completeness handling depends on SSPI internals not shown.

<a id="u-86a3af6ce80c"></a>
### `socks5_sspi_setup`

`static CURLcode socks5_sspi_setup(struct Curl_cfilter *cf, struct Curl_easy *data, st…` · [lib/socks_sspi.c:L59-L91][f1]

Builds the Kerberos service principal name and acquires outbound SSPI credentials for SOCKS5 GSS-API negotiation.

The SASL service name comes from Curl_creds_sasl_service(creds) when available, otherwise 'rcmd'; if it lacks a '/' it is appended to '/<proxy hostname>' via curl_maprintf, otherwise duplicated as-is; allocation failure returns CURLE_OUT_OF_MEMORY. AcquireCredentialsHandle is called with the 'Kerberos' package and SECPKG_CRED_OUTBOUND; an SSPI error is logged twice (by check_sspi_err and a second failf) and yields CURLE_COULDNT_CONNECT, leaving *service_namep allocated for the caller to free.

calls: [check_sspi_err](r9-socks-sspi.md#u-6dfbb9ea5bab); uses: [Curl_sspi_global_init](r1-platform-utilities.md#u-04f713aba199)

**Uncertainties.**

- Which package Curl_creds_has_sasl_service/Curl_creds_sasl_service return is defined elsewhere and not visible here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/socks_sspi.c
