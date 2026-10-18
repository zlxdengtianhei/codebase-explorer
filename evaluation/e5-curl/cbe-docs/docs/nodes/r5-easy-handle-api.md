# Easy Handle API and Transfer Info

**Capability.** The single-session public API surface: easy handle lifecycle declarations plus the transfer-information subsystem that resets per-transfer state and answers curl_easy_getinfo queries by type.

Use this for anything about configuring/driving one CURL handle or reading its post-transfer statistics. Curl_getinfo fans out to the typed getinfo_* dispatchers; the local unions there are pointer-aliasing tricks, not separate behaviors.

**Depended on by.**

- [LDAP Protocol \(OpenLDAP\)](r5-ldap-protocol.md) · model-inferred · 0 edge(s)
- [Tool Output Directories and SSL Sessions](r5-tool-output.md) · model-inferred · 0 edge(s)

Parent: [curl Library and Tool](r5-curl-codebase.md)

## Units (17)

<a id="u-1697244ca3a2"></a>
### `easy-h`

`struct curl_blob` · [include/curl/easy.h:L34-L39][f1]

Declares the libcurl easy (single-session) API: a POD for binary blobs plus extern prototypes for creating, configuring, driving, inspecting, cloning, resetting, and tearing down CURL handles; no runtime bodies here.

In-source comments state boundary behavior: curl_easy_getinfo's variadic third argument must point to the exact type matching the option, and output is valid only when CURLcode is CURLE_OK and only after a transfer has completed (undefined before); curl_easy_duphandle copies options but not internal state or persistent connections, so it suits per-thread setup; curl_easy_reset restores creation-time defaults while retaining live connections, the session ID cache, DNS cache, and cookies; curl_easy_recv and curl_easy_send work only on an already-connected socket after curl_easy_perform with CURLOPT_CONNECT_ONLY; curl_easy_upkeep runs connection upkeep. curl_blob carries data/len/flags where flag bit 0 selects copy (CURL_BLOB_COPY=1) versus no-copy (CURL_BLOB_NOCOPY=0), remaining flag bits reserved and should be zero. Wrapped in extern "C" under __cplusplus, guarded by CURLINC_EASY_H.

uses: [multi-h](r7-public-api-contracts.md#u-dc584fa25c82)

**Uncertainties.**

- Parser reported a syntax error near line 1; chunk coverage is preserved, but exact attribution of individual prototypes to residual regions is inferred from line ranges.

<a id="u-3e1a47ea9d30"></a>
### `bufref`

`struct bufref` · [lib/bufref.h:L30-L37][f2]

Defines the generic buffer-reference struct: a destructor function pointer for owned buffers, the data pointer, and a byte length.

Under DEBUGBUILD an extra signature field supports API-misuse detection. The header also declares the Curl_bufref_* API and defines Curl_bufref_dup, a macro duplicating the referenced string via curlx_strdup of Curl_bufref_ptr.

**Notes.**

- contract: Ownership is optional: dtor NULL means Curl_bufref_free drops the reference without freeing.

**Uncertainties.**

- Header declarations other than the struct and macro are documented with their lib/bufref.c implementations.

<a id="u-353b7df79eb6"></a>
### `Curl_getinfo`

`CURLcode Curl_getinfo(struct Curl_easy *data, CURLINFO info, ...)` · [lib/getinfo.c:L652-L709][f3]

Public variadic entry point for curl_easy_getinfo, routing a query to the type-specific handler selected by the CURLINFO type mask.

It returns CURLE_BAD_FUNCTION_ARGUMENT immediately when data is NULL, or as the initial result if the type is unrecognized. The va_arg list must supply a pointer of the type implied by the info: const char ** for STRING, long * for LONG, double * for DOUBLE, curl_off_t * for OFF_T, struct curl_slist ** for SLIST, and curl_socket_t * for SOCKET; each is extracted only when the type matches, and a NULL pointer leaves the initial bad-argument result. Otherwise the matching handler's CURLcode becomes the result: handlers return CURLE_UNKNOWN_OPTION for unknown infos of the right type. va_end is always reached before returning.

**Notes.**

- failure: Passing a pointer type mismatched to the CURLINFO type mask reads the wrong va_arg and yields undefined behavior; the code cannot detect this.

calls: [getinfo_char](r5-easy-handle-api.md#u-2282adf70f05), [lib/getinfo.c:getinfo_long](r5-easy-handle-api.md#u-47d1e2ef244d), [getinfo_double](r5-easy-handle-api.md#u-5ac769b7aaf6), [getinfo_offt](r5-easy-handle-api.md#u-ebab30fe6131), [lib/getinfo.c:getinfo_slist](r5-easy-handle-api.md#u-ce89204eb2aa), [getinfo_socket](r5-easy-handle-api.md#u-c3349d5ae600)

<a id="u-52b50ca2d001"></a>
### `Curl_initinfo`

`void Curl_initinfo(struct Curl_easy *data)` · [lib/getinfo.c:L41-L78][f3]

Resets all per-transfer statistical and informational state on a Curl_easy handle.

It zeroes progress delta/total counters and the startransfer flag, clears PureInfo fields (httpcode, httpproxycode, httpversion, header/request sizes, auth avail/picked, numconnects, retry_after, conn_scheme, conn_protocol, used_proxy), sets filetime to -1 as the 'unknown' sentinel, sets timecond to FALSE, and zeroes info->primary. It frees contenttype, wouldredirect, and effective_url via curlx_safefree. Under USE_SSL it additionally frees the certificate info. No return value; called from reset, duphandle, open, and pre-transfer paths, so all callers observe a clean info baseline.

**Notes.**

- side_effect: Frees owned strings and, when SSL support is compiled in, the TLS certificate info attached to the handle.

uses: [lib/vtls/vtls.c][f4]

<a id="u-df0546a87279"></a>
### `effective_url`

`static CURLcode effective_url(struct Curl_easy *data, const char **param_charp)` · [lib/getinfo.c:L80-L117][f3]

Computes the effective URL string for CURLINFO_EFFECTIVE_URL with credentials stripped.

It reads the state url bufref and defaults the out-param to "" when empty. If a URL exists, it creates a CURLU handle (returning CURLE_OUT_OF_MEMORY if creation fails), re-parses the URL with CURLU_NON_SUPPORT_SCHEME plus CURLU_PATH_AS_IS when data->set.path_as_is is set, removes the user and password parts, then re-renders the URL with CURLU_GET_EMPTY. The handle is always cleaned up. If any CURLU step failed or no URL string was produced, it returns CURLE_OUT_OF_MEMORY. If the rendered URL differs from the original string, the previous cached data->info.effective_url is freed, the new copy is cached, and that pointer is returned via the out-param; if identical, the copy is freed and the original pointer is returned. Returns CURLE_OK otherwise.

calls: [lib/urlapi.c][f5], [lib/bufref.c][f6]

**Uncertainties.**

- Whether a nonempty CURLUcode failure is truly an out-of-memory condition is asserted by the code, not by this file; the CURLU failure taxonomy is defined in urlapi.c.

<a id="u-2282adf70f05"></a>
### `getinfo_char`

`static CURLcode getinfo_char(struct Curl_easy *data, CURLINFO info, const char **para…` · [lib/getinfo.c:L119-L216][f3]

Dispatches CURLINFO string-type queries to the matching const char * field.

EFFECTIVE_URL delegates to effective_url(). EFFECTIVE_METHOD returns the custom request string when set; otherwise "HEAD" when opt_no_body is set, or a method name derived from state.httpreq (POST variants -> "POST", PUT -> "PUT", HEAD -> "HEAD", GET and the default fallthrough -> "GET"), with the HTTP mapping compiled out when HTTP is disabled. Other cases return stored pointers: contenttype, private_data, most_recent_ftp_entrypath, wouldredirect, the referer bufref, primary remote and local IP, RTSP session id (NULL when RTSP is disabled), conn_scheme, and the build-time CURL_CA_PATH / CURL_CA_BUNDLE macros or NULL when undefined. Unknown info returns CURLE_UNKNOWN_OPTION; success returns CURLE_OK.

**Notes.**

- contract: The FTP entry path and similar returned pointers may be freed by subsequent libcurl calls; callers must copy them and must never free them.

calls: [effective_url](r5-easy-handle-api.md#u-df0546a87279), [lib/bufref.c][f6]

<a id="u-5ac769b7aaf6"></a>
### `getinfo_double`

`static CURLcode getinfo_double(struct Curl_easy *data, CURLINFO info, double *param_d…` · [lib/getinfo.c:L515-L591][f3]

Handles CURLINFO double queries, scaling microsecond counters to seconds via DOUBLE_SECS (divide by 1000000).

In DEBUGBUILD builds, time and speed infos first honor a CURL_TIME environment override, returning the parsed value directly as double without scaling. Main cases: TOTAL/NAMELOOKUP/CONNECT/APPCONNECT/PRETRANSFER/STARTTRANSFER/REDIRECT times, SIZE_UPLOAD and SIZE_DOWNLOAD, SPEED_DOWNLOAD and SPEED_UPLOAD, and CONTENT_LENGTH_DOWNLOAD/UPLOAD returning -1 when the matching size_known flag is false. Unknown info returns CURLE_UNKNOWN_OPTION; otherwise CURLE_OK.

<a id="u-7273fb1237af"></a>
### `getinfo_long`

`static CURLcode getinfo_long(struct Curl_easy *data, CURLINFO info, long *param_longp)` · [lib/getinfo.c:L218-L223][f3]

Signature and stack declarations of the long-type CURLINFO dispatcher, including a debugbuild-only section and a union aliasing the long output pointer as unsigned long.

The body continues in the following segment; see that unit for query behavior.

<a id="u-47d1e2ef244d"></a>
### `lib/getinfo.c:getinfo_long`

`static CURLcode getinfo_long(struct Curl_easy *data, CURLINFO info, long *param_longp)` · [lib/getinfo.c:L226-L409][f3]

Handles CURLINFO long-type queries, writing through param_longp.

In DEBUGBUILD builds, CURLINFO_LOCAL_PORT first honors a CURL_TIME environment override and CURLINFO_HEADER_SIZE/CURLINFO_REQUEST_SIZE honor CURL_DEBUG_SIZE, returning the parsed value early. Main cases: response code, proxy connect code, FILETIME clamped to LONG_MAX/LONG_MIN when exceeding long range (the LONG_MIN clamp is skipped on MSDOS/AMIGA), header and request sizes, SSL and proxy-SSL certverifyresult (0 when proxies disabled), redirect count, http/proxy auth avail and picked bitmasks written through the unsigned-long alias, os_errno, numconnects clamped to LONG_MAX when long is narrower than curl_off_t, LASTSOCKET from Curl_getconnectinfo with -1 when no socket exists, PRIMARY_PORT and LOCAL_PORT returning -1 when the primary IP quad lacks ports, proxy error code, CONDITION_UNMET (1 on HTTP 304, else 1 or 0 per timecond), RTSP client/server/recv CSeq values (0 when RTSP is disabled), HTTP_VERSION mapped from stored 10/11/20/30 to public constants or CURL_HTTP_VERSION_NONE otherwise, conn_protocol, and USED_PROXY (0 when proxies disabled). Unknown info returns CURLE_UNKNOWN_OPTION; otherwise CURLE_OK.

**Notes.**

- side_effect: In DEBUGBUILD builds, getenv overrides can replace the real stored values for the affected infos.

calls: [lib/connect.c][f7]

**Uncertainties.**

- curlx_str_number failure behavior for malformed env values is defined in curlx/strparse and not visible here.

<a id="u-ebab30fe6131"></a>
### `getinfo_offt`

`static CURLcode getinfo_offt(struct Curl_easy *data, CURLINFO info, curl_off_t *param…` · [lib/getinfo.c:L413-L513][f3]

Handles CURLINFO curl_off_t queries.

In DEBUGBUILD builds, the *_T time and speed infos first honor a CURL_TIME environment override and return early with the parsed value. Main cases: FILETIME_T; SIZE_DELIVERED; upload/download cur_size and speeds; CONTENT_LENGTH_DOWNLOAD_T and CONTENT_LENGTH_UPLOAD_T returning -1 when the corresponding size_known flag is false; TOTAL/NAMELOOKUP/CONNECT/APPCONNECT/PRETRANSFER/POSTTRANSFER/STARTTRANSFER/QUEUE/REDIRECT time values taken directly from microsecond progress counters; RETRY_AFTER; XFER_ID (data->id); CONN_ID (last_conn_id); and EARLYDATA_SENT_T. Unknown info returns CURLE_UNKNOWN_OPTION; otherwise CURLE_OK. No seconds conversion is applied here.

<a id="u-114950fa1353"></a>
### `getinfo_slist`

`static CURLcode getinfo_slist(struct Curl_easy *data, CURLINFO info, struct curl_slis…` · [lib/getinfo.c:L593-L596][f3]

Signature and local union declaration of the slist-type CURLINFO dispatcher; the union reinterprets an slist pointer as a curl_certinfo pointer.

The body continues in the following segment.

<a id="u-ce89204eb2aa"></a>
### `lib/getinfo.c:getinfo_slist`

`static CURLcode getinfo_slist(struct Curl_easy *data, CURLINFO info, struct curl_slis…` · [lib/getinfo.c:L599-L636][f3]

Handles CURLINFO slist-type queries.

SSL_ENGINES returns the SSL engine list; COOKIELIST returns the cookie list; CERTINFO reinterprets a pointer to data->info.certs (curl_certinfo) as an slist pointer via the union, since the structures are layout-compatible by convention here. TLS_SESSION and TLS_SSL_PTR select CF_QUERY_SSL_INFO or CF_QUERY_SSL_CTX_INFO depending on which CURLINFO was requested, store the address of data->tsi into the caller's pointer as a curl_tlssessioninfo pointer, then call Curl_conn_get_ssl_info on the current connection's first socket; when that call returns failure, the backend is set from Curl_ssl_backend() and internals to NULL. Unknown info returns CURLE_UNKNOWN_OPTION; otherwise CURLE_OK.

**Notes.**

- contract: The certinfo and TLS session pointers alias internal memory with unknown lifetime, per the source comments.

calls: [lib/cfilters.c][f8], [lib/cookie.c][f9], [lib/vtls/vtls.c][f4]

**Uncertainties.**

- Whether the failure result of Curl_conn_get_ssl_info is a CURLcode or another status type is not shown in this file.

<a id="u-c3349d5ae600"></a>
### `getinfo_socket`

`static CURLcode getinfo_socket(struct Curl_easy *data, CURLINFO info, curl_socket_t *…` · [lib/getinfo.c:L638-L650][f3]

Handles the single CURLINFO socket-type query, CURLINFO_ACTIVESOCKET, by returning the value of Curl_getconnectinfo(data, NULL).

Unknown info returns CURLE_UNKNOWN_OPTION; otherwise CURLE_OK.

calls: [lib/connect.c][f7]

<a id="u-2964d3f908b2"></a>
### `getinfo.c module code (L1–L40)`

`module_region` · [lib/getinfo.c:L1-L40][f3]

File header region containing the license banner and include directives that pull in urldata, getinfo, connection-filter, TLS, connect, bufref, and string-parsing declarations.

It carries no executable behavior; the surrounding functions define this file's logic.

<a id="u-502a0e529e66"></a>
### `getinfo.c module code (L409–L412)`

`module_region` · [lib/getinfo.c:L409-L412][f3]

Residual region holding the DOUBLE_SECS macro definition, which converts a microsecond counter to seconds by dividing by 1000000 as a double.

The macro is used by getinfo_double and has no other behavior.

<a id="u-9d5c25d7bd66"></a>
### `lib/getinfo.c:<union>`

`union` · [lib/getinfo.c:L223-L226][f3]

Local union declared inside getinfo_long that aliases the caller's long pointer as an unsigned long pointer; it exists only to write auth bitmasks through the same storage and has no independent behavior.

<a id="u-513af92475b6"></a>
### `lib/getinfo.c:<union> (2)`

`union` · [lib/getinfo.c:L596-L599][f3]

Local union inside getinfo_slist aliasing struct curl_slist * and struct curl_certinfo * so the certinfo struct address can be returned through the slist out-parameter; it has no independent behavior.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/include/curl/easy.h
[f2]: ../../../../../../eval/curl-2c04412/lib/bufref.h
[f3]: ../../../../../../eval/curl-2c04412/lib/getinfo.c
[f4]: ../../../../../../eval/curl-2c04412/lib/vtls/vtls.c
[f5]: ../../../../../../eval/curl-2c04412/lib/urlapi.c
[f6]: ../../../../../../eval/curl-2c04412/lib/bufref.c
[f7]: ../../../../../../eval/curl-2c04412/lib/connect.c
[f8]: ../../../../../../eval/curl-2c04412/lib/cfilters.c
[f9]: ../../../../../../eval/curl-2c04412/lib/cookie.c
