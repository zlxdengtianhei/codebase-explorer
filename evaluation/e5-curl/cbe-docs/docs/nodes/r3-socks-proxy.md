# SOCKS Proxy & GSS-API Negotiation

**Capability.** Declares the SOCKS proxy filter interface (blocking exact-length reads, credential-by-reference insertion, filter type) and implements the RFC1961 GSS-API SOCKS5 handshake: service-name construction, token loop, peer-identity verification, and protection-level negotiation.

Use this subtree for SOCKS proxying, especially authenticated SOCKS5 via GSS-API or Windows SSPI builds. The header defines the integration contract; socks_gssapi.c implements the handshake and error reporting over the connection filter chain.

**Depends on.**

- [Connection & Proxy Infrastructure](r3-connection-infra.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r3-socks-proxy ` → ` r3-connection-infra `)

Parent: [Connection & Proxy Infrastructure](r3-connection-infra.md)

## Units (9)

<a id="u-68b45d64db5e"></a>
### `socks-h`

`group` · [lib/socks.h:L1-L69][f1]

Declares the SOCKS proxy interface: a deliberately blocking read helper that loops until exactly blen bytes are read, an optional GSS-API SOCKS5 negotiation available only with GSSAPI or Windows SSPI, an insertion helper for a SOCKS proxy filter (credentials passed by reference, not duplicated, and must outlive the connect phase), and the filter type.

All guarded by !CURL_DISABLE_PROXY.

imports: [socks-h](r3-socks-proxy.md#u-68b45d64db5e)

**Uncertainties.**

- Blocking behavior of Curl_blockread_all is asserted by its comment, not verified here.

<a id="u-624698bfccd0"></a>
### `socks_gssapi.c module code (L1–L47)`

`module_region` · [lib/socks_gssapi.c:L1-L47][f2]

Compilation guard and includes for the SOCKS5 GSS-API implementation.

The whole file is compiled only when HAVE_GSSAPI is defined and proxy support is not disabled; otherwise it expands to nothing. It includes GSS glue, connection/filter, tracing, nonblock, socks, and strdup headers, and raises the -Wdeprecated-declarations diagnostic suppression on Apple builds without the Apple GSS implementation.

<a id="u-db74ecb5dfa4"></a>
### `check_gss_err`

`static int check_gss_err(struct Curl_easy *data, OM_uint32 major_status, OM_uint32 mi…` · [lib/socks_gssapi.c:L48-L99][f2]

Converts a GSS-API error into a formatted failf message; returns 1 on error, 0 on success.

Runs only when GSS_ERROR(major_status) is true; otherwise returns 0 immediately. On error it builds a bounded (MAX_GSS_LEN) dynamic buffer with gss_display_status text for the major code (GSS_C_GSS_CODE) then the minor code (GSS_C_MECH_CODE), appending ".\n" between/after. If any dynbuf append fails it returns 1 early without freeing the buffer; otherwise it logs "GSS-API error: <function> failed: <text>" via failf and frees the buffer. The gss_display_status loops exit after the first complete conversion (msg_ctx becomes nonzero or break), so multi-message rendering is not performed.

**Notes.**

- failure: On dynbuf allocation/append failure the function returns 1 (treated as GSS error by callers) without calling curlx_dyn_free, leaking the buffer.

uses: [socks5_gss_create_service_name](r3-socks-proxy.md#u-1be3a39b854b)

**Uncertainties.**

- Whether curlx_dyn_addn failure paths also need gss_release_buffer for a still-held status_string is not shown for the early-return branches.

<a id="u-1be3a39b854b"></a>
### `socks5_gss_create_service_name`

`static CURLcode socks5_gss_create_service_name(struct Curl_easy *data, struct connect…` · [lib/socks_gssapi.c:L101-L141][f2]

Builds a GSS server name for the SOCKS5 proxy from a service string.

If serviceptr contains '/', it is imported verbatim with GSS_C_NULL_OID after a memdup; otherwise it is formatted as "service@proxy-hostname" and imported as GSS_C_NT_HOSTBASED_SERVICE. Either allocation failure returns CURLE_OUT_OF_MEMORY before any GSS call. If gss_import_name fails per check_gss_err, it fails with "Failed to create service name.", releases the (possibly partially set) name, and returns CURLE_COULDNT_CONNECT. On success *server holds the imported name and CURLE_OK is returned; the service buffer is always freed.

calls: [check_gss_err](r3-socks-proxy.md#u-db74ecb5dfa4); uses: [Curl_SOCKS5_gssapi_negotiate](r3-socks-proxy.md#u-08f8446c4626)

**Uncertainties.**

- gss_release_name is called on *server even though the code cannot prove gss_import_name left it valid on failure.

<a id="u-cd87d228bdcd"></a>
### `socks5_gss_auth_loop`

`static CURLcode socks5_gss_auth_loop(struct Curl_cfilter *cf, struct Curl_easy *data,…` · [lib/socks_gssapi.c:L143-L302][f2]

Drives the RFC1961 GSS-API context-establishment token loop over the connection filter chain.

Each iteration calls Curl_gss_init_sec_context with the Kerberos mechanism OID, mutual auth TRUE, and no credential; the first pass passes no input token, later passes pass the token read from the server. Failure exits (all returning CURLE_COULDNT_CONNECT unless noted) release the name, buffers, and context: init error or token exceeding 0xffff (16-bit length field limit); partial/failed send of the 4-byte header (VER=1, MTYP=1, htons length) or of the token bytes; short/failed read of the 4-byte response; response type byte socksreq[1] equal to 255 ("User was rejected") or not 1; zero-length received token; or allocation failure of the token buffer (CURLE_OUT_OF_MEMORY). After sending a token, the loop breaks when the major status is not GSS_S_CONTINUE_NEEDED; otherwise it reads the server token and continues. On completion it releases the server name and returns CURLE_OK, leaving the established context and ret flags for the caller.

calls: [curl_gssapi.h module code (L1–L96)](r15-protocol-support-headers.md#u-fcb4afac4875), [check_gss_err](r3-socks-proxy.md#u-db74ecb5dfa4); uses: [Curl_SOCKS5_gssapi_negotiate](r3-socks-proxy.md#u-08f8446c4626)

**Uncertainties.**

- gss_recv_token.value is freed only when a prior token was received (guarded by gss_token != GSS_C_NO_BUFFER); on the first iteration the initial GSS_C_EMPTY_BUFFER is assumed to need no free.
- Token length is truncated via (unsigned short) cast before the >0xffff check, which is safe because the check uses the original length, but only exact fits are validated.

<a id="u-bfde4a8a223b"></a>
### `socks5_gss_auth_verify`

`static CURLcode socks5_gss_auth_verify(struct Curl_easy *data, gss_ctx_id_t *gss_cont…` · [lib/socks_gssapi.c:L304-L340][f2]

Logs the authenticated peer identity after context establishment.

gss_inquire_context extracts the client name from the context; on check_gss_err failure it deletes the context, releases the name, reports "Failed to determine username." and returns CURLE_COULDNT_CONNECT. gss_display_name then renders the name; its failure path additionally releases the display buffer before the same CURLE_COULDNT_CONNECT. On success it infof-logs "SOCKS5 server authenticated user ... with GSS-API.", releases the name and buffer, and returns CURLE_OK.

calls: [check_gss_err](r3-socks-proxy.md#u-db74ecb5dfa4); uses: [Curl_SOCKS5_gssapi_negotiate](r3-socks-proxy.md#u-08f8446c4626)

**Uncertainties.**

- Direct gss_inquire_context/gss_display_name are used rather than the Curl_gss_* wrappers, so platform-specific wrapping behavior does not apply here.

<a id="u-1b6d7016a6af"></a>
### `socks5_gss_negotiate_enc`

`static CURLcode socks5_gss_negotiate_enc(struct Curl_cfilter *cf, struct Curl_easy *d…` · [lib/socks_gssapi.c:L342-L565][f2]

Negotiates the SOCKS5 GSS data-protection level (RFC1961 message type 2) and records the result on the connection.

Protection choice: gss_enc=2 if the context flags include GSS_C_CONF_FLAG, else 1 if GSS_C_INTEG_FLAG, else 0 (none); the level is logged. Outgoing message: 4-byte header (VER=1, MTYP=2, length). If data->set.socks5_gssapi_nec is set, the header carries length 1 and the raw protection byte is sent un-wrapped in a follow-up 1-byte send (the known NEC-variant weakness documented in the comment); otherwise a one-byte protection value is gss_wrap'd (conf_req FALSE) and the wrapped token is sent. Failure paths return CURLE_COULDNT_CONNECT (or CURLE_OUT_OF_MEMORY for the wrap-value allocation) after releasing buffers and deleting the context: partial header or type send; short/failed 4-byte response read; response type 255 ("User was rejected") or not 2; zero-length token; token allocation failure; short token-body read; and, for the non-NEC path, gss_unwrap error or unwrapped length != 1; for the NEC path, received length != 1. On success the server's reply byte is stored in conn->socks5_gssapi_enctype and logged; if the granted level is 0, the GSS context is deleted since no further protection is needed.

calls: [check_gss_err](r3-socks-proxy.md#u-db74ecb5dfa4); uses: [curl_gssapi.h module code (L1–L96)](r15-protocol-support-headers.md#u-fcb4afac4875), [Curl_SOCKS5_gssapi_negotiate](r3-socks-proxy.md#u-08f8446c4626)

**Uncertainties.**

- In the NEC memory-failure branch gss_status is used uninitialized when calling Curl_gss_delete_sec_context; actual effect depends on that wrapper.
- conn->socks5_gssapi_enctype is stored raw (0/1/2 or other server bytes) without validation against the locally requested level.

<a id="u-08f8446c4626"></a>
### `Curl_SOCKS5_gssapi_negotiate`

`CURLcode Curl_SOCKS5_gssapi_negotiate(struct Curl_cfilter *cf, struct Curl_easy *data…` · [lib/socks_gssapi.c:L567-L595][f2]

Public entry point performing the full SOCKS5 GSS-API handshake.

It selects the service name from creds via Curl_creds_has_sasl_service/Curl_creds_sasl_service, defaulting to "rcmd", then runs the stages in order: create service name, switch the socket to blocking, run the auth token loop, verify the authenticated user, and negotiate encryption. Each stage runs only if the previous returned CURLE_OK; the first failing stage's code propagates. Finally the socket is unconditionally restored to non-blocking (result ignored), and the last result is returned.

calls: [socks5_gss_create_service_name](r3-socks-proxy.md#u-1be3a39b854b), [socks5_gss_auth_loop](r3-socks-proxy.md#u-cd87d228bdcd), [socks5_gss_auth_verify](r3-socks-proxy.md#u-bfde4a8a223b), [socks5_gss_negotiate_enc](r3-socks-proxy.md#u-1b6d7016a6af)

**Uncertainties.**

- The creds parameter handling depends on Curl_creds_* helpers whose behavior is defined elsewhere.
- If the GSS context was not deleted by a failing stage, it is not explicitly cleaned up here; cleanup responsibility on that path is unclear.

<a id="u-8c2891021767"></a>
### `socks_gssapi.c module code (L595–L601)`

`module_region` · [lib/socks_gssapi.c:L595-L601][f2]

Trailer of the file: restores the Apple deprecation diagnostic state and closes the HAVE_GSSAPI && !CURL_DISABLE_PROXY conditional so the file compiles to nothing when GSS-API or proxy support is absent.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/socks.h
[f2]: ../../../../../../eval/curl-2c04412/lib/socks_gssapi.c
