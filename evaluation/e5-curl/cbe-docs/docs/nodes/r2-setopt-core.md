# Setopt Dispatch & Storage

**Capability.** The option-setting entry points and typed storage primitives: varargs entry, type-range classification, and string/blob/slist/pointer/long/offt dispatch with shared validation helpers.

Read to see how an option is classified and where values are stored; the storage helpers (setstropt, setblobopt) and range/timeout validators are the foundation all sub-handlers use.

**Depended on by.**

- [Setopt Domain Handlers](r2-setopt-domains.md) · graph-confirmed · 73 edge(s)
- [Tool-Side Diagnostics & Config](r2-tool-side.md) · model-inferred · 0 edge(s)
- [DNS-over-HTTPS Resolver](r3-doh-resolver.md) · graph-only · 27 edge(s)

Parent: [Easy Handle Option Setting](r2-easy-setopt.md)

## Units (15)

<a id="u-82b62740d48c"></a>
### `Curl_setstropt`

`CURLcode Curl_setstropt(struct Curl_easy *data, enum dupstring id, const char *s)` · [lib/setopt.c:L81-L90][f1]

Stores a string option into the easy handle's string set, validating length before storage.

**Notes.**

- contract: s == NULL stores an empty/cleared entry with slen 0; a string longer than CURL_MAX_INPUT_LENGTH returns CURLE_BAD_FUNCTION_ARGUMENT without storing.

uses: [Curl_u8_strset_setx](r11-u8-strset.md#u-71cd8182b082)

**Uncertainties.**

- Exact semantics of CURL_EASY_STR_SET (replacement vs append on existing entries) live in the u8_strset implementation, not this file.

<a id="u-086c5d4c1702"></a>
### `Curl_setblobopt`

`CURLcode Curl_setblobopt(struct curl_blob **blobp, const struct curl_blob *blob)` · [lib/setopt.c:L92-L121][f1]

Replaces a stored blob option, freeing the old blob first and optionally copying the new data inline.

**Notes.**

- side_effect: The previous *blobp is freed unconditionally before validation; an invalid blob (NULL data, zero len, or len over CURL_MAX_INPUT_LENGTH) therefore leaves *blobp NULL and returns CURLE_BAD_FUNCTION_ARGUMENT.
- condition: With CURL_BLOB_COPY the data is copied into memory directly after the struct; otherwise the caller's buffer is referenced. Allocation failure returns CURLE_OUT_OF_MEMORY.

<a id="u-ceb2158e7388"></a>
### `Curl_setopt_SSLVERSION`

`CURLcode Curl_setopt_SSLVERSION(struct Curl_easy *data, CURLoption option, long arg)` · [lib/setopt.c:L293-L326][f1]

Validates and stores an SSL version (low 16 bits) and optional max (bits 16+) into the connection or proxy SSL config.

**Notes.**

- condition: Options other than CURLOPT_SSLVERSION target data->set.proxy_ssl when proxy support is compiled in.
- failure: SSLv2/SSLv3, versions at/above CURL_SSLVERSION_LAST, or max values below MAX_NONE or at/above MAX_LAST return CURLE_BAD_FUNCTION_ARGUMENT; DEFAULT maps to TLSv1_2.

<a id="u-86c13b752f56"></a>
### `curl_easy_setopt`

`CURLcode curl_easy_setopt(CURL *curl, CURLoption option, ...)` · [lib/setopt.c:L2932-L2951][f1]

Public varargs entry for setting easy-handle options, with API guard and bad-argument logging.

**Notes.**

- failure: Curl_vsetopt's result is returned unchanged; when it is CURLE_BAD_FUNCTION_ARGUMENT the option is logged with failf. If CURL_EAPI_ENTER declines entry, result comes from the guard setup; va_start/va_end run only inside the guarded block.
- side_effect: Allowed to be called from within callbacks per the file comment.

calls: [Curl_vsetopt](r2-setopt-core.md#u-86a624d4fa46), [Curl_failf](r1-trace-logging.md#u-c8338023c157)

**Uncertainties.**

- The behavior of CURL_EAPI_ENTER/CURL_EAPI_LEAVE when entry is refused (including what result then holds) is defined in lib/api.c, not visible here.

<a id="u-86a624d4fa46"></a>
### `Curl_vsetopt`

`CURLcode Curl_vsetopt(struct Curl_easy *data, CURLoption option, va_list param)` · [lib/setopt.c:L2883-L2922][f1]

Classifies an option by its type range and routes it to the matching typed handler.

**Notes.**

- condition: Options below CURLOPTTYPE_OBJECTPOINT go to setopt_long; object-pointers are split explicitly: the listed slist options to setopt_slist, a fixed set of special pointers (HTTPPOST, MIMEPOST, STDERR, SHARE, CURLU) to setopt_pointers, STREAM_DEPENDS(_E) silently accepted as CURLE_OK, and everything else treated as char* to setopt_cptr; function pointers to setopt_func; off_t range to setopt_offt; the remainder to setopt_blob. Not static: also called from projects/OS400/ccsidcurl.c.

calls: [setopt_long](r2-setopt-core.md#u-6579fce4a528), [setopt_slist](r2-setopt-core.md#u-00f5cd5ed52c), [setopt_pointers](r2-setopt-core.md#u-22e3b8b0a08e), [setopt_cptr](r2-setopt-core.md#u-83a6c4a44be0), [setopt_func](r2-setopt-core.md#u-1260a33e2af8), [setopt_offt](r2-setopt-core.md#u-440771a8e92e), [setopt_blob](r2-setopt-core.md#u-4e85ce78005b)

**Uncertainties.**

- The pointer-type split relies on the explicit case list; a libcurl option missing from that list would be misread as char*. Whether that list is complete for all compiled options is not provable from this file.

<a id="u-83a6c4a44be0"></a>
### `setopt_cptr`

`static CURLcode setopt_cptr(struct Curl_easy *data, CURLoption option, char *ptr)` · [lib/setopt.c:L2492-L2525][f1]

Dispatches a char-pointer option through the sub-handlers until one recognizes it.

**Notes.**

- condition: Handlers are tried in a likeliness order (misc first, then SSL/SSH, proxy, net, FTP, SSH, HTTP/MQTT as compiled); each returns CURLE_UNKNOWN_OPTION for unhandled options, letting the loop continue; after all handlers CURLE_UNKNOWN_OPTION is returned.

calls: [setopt_cptr_misc](r2-setopt-domains.md#u-f09d229fdd80), [setopt_cptr_ssl](r2-setopt-domains.md#u-9f7d5d3ea02f), [setopt_cptr_proxy](r2-setopt-domains.md#u-45438112f531), [setopt_cptr_net](r2-setopt-domains.md#u-0639344d37a2), [setopt_cptr_ftp](r2-setopt-domains.md#u-c7018faa9f8d), [setopt_cptr_ssh](r2-setopt-domains.md#u-05a8edfab35f), [setopt_cptr_http_mqtt](r2-setopt-domains.md#u-fb810e915f8d)

<a id="u-6579fce4a528"></a>
### `setopt_long`

`static CURLcode setopt_long(struct Curl_easy *data, CURLoption option, long arg)` · [lib/setopt.c:L1258-L1280][f1]

Dispatches a long-typed option through the sub-handlers until one recognizes it.

**Notes.**

- condition: Handlers are tried in a fixed order; each returns CURLE_UNKNOWN_OPTION for options it does not handle, which lets the loop continue. Any other result, including success, is returned immediately; after all handlers the loop returns CURLE_UNKNOWN_OPTION.

calls: [setopt_long_bool](r2-setopt-domains.md#u-27930137a17a), [setopt_long_net](r2-setopt-domains.md#u-f332e153df94), [setopt_long_http](r2-setopt-domains.md#u-6bdcb1ce02dd), [setopt_long_proxy](r2-setopt-domains.md#u-08ef844a2c87), [setopt_long_ssl](r2-setopt-domains.md#u-1149805f64c0), [setopt_long_proto](r2-setopt-domains.md#u-f0f4322fbdc5), [setopt_long_misc](r2-setopt-domains.md#u-d3e2ed69328a)

<a id="u-440771a8e92e"></a>
### `setopt_offt`

`static CURLcode setopt_offt(struct Curl_easy *data, CURLoption option, curl_off_t offt)` · [lib/setopt.c:L2716-L2801][f1]

Applies curl_off_t options: large time value, post/infile sizes, resume, and bandwidth throttles.

**Notes.**

- failure: POSTFIELDSIZE_LARGE, INFILESIZE_LARGE, RESUME_FROM_LARGE reject values below -1; MAX_SEND/RECV_SPEED_LARGE and MAXFILESIZE_LARGE reject negatives; unknown options return CURLE_UNKNOWN_OPTION.
- side_effect: Setting a larger POSTFIELDSIZE_LARGE frees str_copypostfields and NULLs postfields, invalidating a prior COPYPOSTFIELDS. Speed limit options also initialize per-direction rate limiters with a 32 KiB minimum burst and the current progress time.

calls: [Curl_rlimit_init](r4-transfer-rate-limiting.md#u-2eda63d61d3c), [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77)

<a id="u-1260a33e2af8"></a>
### `setopt_func`

`static CURLcode setopt_func(struct Curl_easy *data, CURLoption option, va_list param)` · [lib/setopt.c:L2527-L2714][f1]

Stores callback function pointers into the easy handle, applying per-callback defaults for NULL.

**Notes.**

- condition: PROGRESSFUNCTION and XFERINFOFUNCTION toggle data->progress.callback TRUE for non-NULL, FALSE for NULL (internal meter). WRITEFUNCTION NULL resets to fwrite. READFUNCTION NULL resets to fread and clears is_fread_set; non-NULL sets it to 1. DEBUGFUNCTION, seek, ioctl, SSH key function NULLs are accepted with defaults applied by the users.
- failure: SSL_CTX_FUNCTION returns CURLE_NOT_BUILT_IN when the backend lacks SSLSUPP_SSL_CTX; unknown options return CURLE_UNKNOWN_OPTION.

<a id="u-22e3b8b0a08e"></a>
### `setopt_pointers`

`static CURLcode setopt_pointers(struct Curl_easy *data, CURLoption option, va_list pa…` · [lib/setopt.c:L1432-L1485][f1]

Handles object-pointer options of special types: CURLU, form/MIME POST bodies, stderr, and share.

**Notes.**

- side_effect: CURLU frees the current state URL bufref and clears STRING_SET_URL before storing the new CURLU*. HTTPPOST sets HTTPREQ_POST_FORM, clears opt_no_body, and cleans the old form data. STDERR falls back to stderr when given NULL.
- failure: MIMEPOST delegates to setopt_mimepost and propagates its result; SHARE delegates to setopt_share; unknown options return CURLE_UNKNOWN_OPTION.

calls: [setopt_mimepost](r2-setopt-domains.md#u-8fe9ace0aa8c), [setopt_share](r2-setopt-domains.md#u-532041b3fbad), [Curl_bufref_free](r14-bufref-buffers.md#u-2c7e087ba1d6), [Curl_mime_cleanpart](r2-mime-api.md#u-358147b42434)

<a id="u-00f5cd5ed52c"></a>
### `setopt_slist`

`static CURLcode setopt_slist(struct Curl_easy *data, CURLoption option, struct curl_s…` · [lib/setopt.c:L1282-L1377][f1]

Stores a curl_slist pointer into the matching list option in data->set, without copying the list.

**Notes.**

- condition: All cases assign the caller's list pointer directly; ownership stays with the caller. CURLOPT_RESOLVE additionally mirrors the list into data->state.resolve.
- failure: Unrecognized options return CURLE_UNKNOWN_OPTION; no other failure path exists.

<a id="u-4e85ce78005b"></a>
### `setopt_blob`

`static CURLcode setopt_blob(struct Curl_easy *data, CURLoption option, struct curl_bl…` · [lib/setopt.c:L2803-L2877][f1]

Routes blob options for certificates, keys, CA material, and issuer certs into the blob slots.

**Notes.**

- failure: CAINFO (and proxy variant) blobs return CURLE_NOT_BUILT_IN without SSLSUPP_CAINFO_BLOB; ISSUERCERT blobs require SSLSUPP_ISSUERCERT_BLOB; on successful CAINFO store the matching custom_cablob flag is set. Storage itself delegates to Curl_setblobopt and its results propagate.

calls: [Curl_setblobopt](r2-setopt-core.md#u-086c5d4c1702)

<a id="u-67afd426a41e"></a>
### `value_range`

`static CURLcode value_range(long *value, long below_error, long min, long max)` · [lib/setopt.c:L752-L761][f1]

Clamps a long option value into a range with a hard error floor.

**Notes.**

- contract: Values below below_error return CURLE_BAD_FUNCTION_ARGUMENT unmodified; values between below_error and min become min; values above max become max; otherwise CURLE_OK.

<a id="u-b878e4fd8733"></a>
### `setopt_set_timeout_ms`

`static CURLcode setopt_set_timeout_ms(timediff_t *ptimeout_ms, long ms)` · [lib/setopt.c:L67-L79][f1]

Converts a timeout in milliseconds, rejecting negatives and clamping overflow to the timediff maximum.

**Notes.**

- failure: ms < 0 returns CURLE_BAD_FUNCTION_ARGUMENT; clamping to TIMEDIFF_T_MAX applies only when compiled with LONG_MAX > TIMEDIFF_T_MAX.

<a id="u-d1d1066db815"></a>
### `setopt_set_timeout_sec`

`static CURLcode setopt_set_timeout_sec(timediff_t *ptimeout_ms, long secs)` · [lib/setopt.c:L53-L65][f1]

Converts a timeout in seconds to milliseconds with validation and overflow clamping.

**Notes.**

- failure: Negative seconds return CURLE_BAD_FUNCTION_ARGUMENT; when long exceeds timediff range, values above TIMEDIFF_T_MAX/1000 are clamped to TIMEDIFF_T_MAX instead of overflowing (that branch exists only under LONG_MAX > TIMEDIFF_T_MAX/1000).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/setopt.c
