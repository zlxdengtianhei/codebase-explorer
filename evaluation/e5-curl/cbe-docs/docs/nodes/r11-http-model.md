# HTTP model and HTTP/1 codec

**Capability.** Core request/response/negotiation data types (httpreq, http_resp, http_negotiation) with the dynamic header collection (dynhds), the per-request easy-handle state types, transfer-info API declaration, and the incremental HTTP/1 request parser plus head serializer.

Use the headers (dynhds.h, http.h, request.h, getinfo.h, imap.h) for the shared data model, and http1.c for byte-level parsing/serialization of HTTP/1 request heads. IMAP's header interface is parked here as a protocol-front declaration consistent with the model headers.

**Depended on by.**

- [RTSP protocol](r11-rtsp-protocol.md) · model-inferred · 0 edge(s)

Parent: [protocol implementations](r11-protocol-layer.md)

## Units (16)

<a id="u-83faa480290d"></a>
### `dynhds_entry`

`struct dynhds_entry` · [lib/dynhds.h:L36-L41][f1]

Represents one stored header.

name and value are documented as non-NULL, always null-terminated strings, with namelen and valuelen caching their lengths so consumers can use length-delimited access.

<a id="u-e4b1f2b80420"></a>
### `dynhds`

`struct dynhds` · [lib/dynhds.h:L43-L51][f1]

Dynamic header collection: a growable array hds of dynhds_entry pointers with hds_len/hds_allc tracking use and capacity, optional max_entries and max_strs_size limits bounding entry count and total string bytes, strs_len accumulating total string length, and opts flags where DYNHDS_OPT_LOWERCASE requests lowercased names at insertion time (not retroactively).

<a id="u-94d726659055"></a>
### `http_negotiation`

`struct http_negotiation` · [lib/http.h:L52-L61][f2]

Tracks HTTP version negotiation state: rcvd_min records the minimum response version seen; wanted/allowed/preferred are http_majors bitmasks governing server communication; flags select HTTP/1.1-to-2 Upgrade, direct HTTP/2 without ALPN/SSL, acceptance of HTTP/0.9 responses, and 1.0-only operation within the 1x major.

<a id="u-8994a6a626a7"></a>
### `http_resp`

`struct http_resp` · [lib/http.h:L256-L262][f2]

Core HTTP response model: numeric status, description string, dynhds headers and trailers, and a prev pointer chaining earlier responses (e.g. across redirects).

Created by Curl_http_resp_make, freed by Curl_http_resp_free.

**Uncertainties.**

- The meaning of the prev chain (redirect vs CONNECT history) is not established from this header alone.

<a id="u-372d6b70f0ca"></a>
### `httpreq`

`struct httpreq` · [lib/http.h:L205-L212][f2]

Core HTTP request model excluding body and trailers-attached state: dynhds for headers and trailers, plus scheme, authority, and path strings and a flexible method array (declared size 1, extended at allocation).

Created by Curl_http_req_make/make2 and freed by Curl_http_req_free.

**Uncertainties.**

- method[1] relies on allocation beyond the declared size; the exact layout is decided in http.c, not visible here.

<a id="u-75c233bc520c"></a>
### `request.h-single-request-types`

`enum expect100` · [lib/request.h:L53-L59][f3]

Type and macro definitions describing the per-request state kept in the easy handle.

SingleRequest carries transfer sizes/counters, timing, header counters, HTTP code/version, the 101-upgrade state, io_flags for poll interest, the client reader/writer stacks, the sendbuf queue plus its header-byte count, redirect/auth/cookie strings, and many per-request BIT flags (done, eos_read/eos_sent/eos_written, upload_done/upload_aborted, chunked, shutdown, etc.). The REQ_IO_* / CURL_REQ_* macros read, set, and clear REQ_IO_RECV and REQ_IO_SEND bits in io_flags, with clears masking through uint8_t. enum expect100 tracks the 100-Continue phase (data, awaiting continue, sending request, or failed on 417); enum upgrade101 tracks WebSocket/HTTP2 upgrade state through UPGR101_RECEIVED. The struct exists because a connection may be shared between easy handles, so request-specific state is cleared between requests.

<a id="u-ece817c1ade7"></a>
### `getinfo.h module code (L1–L29)`

`module_region` · [lib/getinfo.h:L1-L29][f4]

Declares the transfer-info API surface: Curl_getinfo extracts per-handle session information and Curl_initinfo resets it.

The header contains only include-guard, license comment, and these two prototypes; all behavior lives in the implementation.

<a id="u-1914bb5b922c"></a>
### `lib-imap-h-header`

`module_region` · [lib/imap.h:L1-L39][f5]

Declares the IMAP protocol's header interface for curl: authentication-type macro constants and a conditional extern protocol handle.

The four macros are compile-time constants: IMAP_TYPE_CLEARTEXT and IMAP_TYPE_SASL are bit flags (bits 0 and 1), IMAP_TYPE_NONE is 0, and IMAP_TYPE_ANY combines the two flags. The extern declaration of Curl_protocol_imap is guarded by #ifndef CURL_DISABLE_IMAP, so when IMAP support is compiled out the symbol is not declared; otherwise consumers can link against its definition elsewhere. The include guard prevents double inclusion. No runtime behavior exists in this header.

group: [lib-imap-h-header](r11-http-model.md#u-1914bb5b922c)

**Uncertainties.**

- The definition and behavior of Curl_protocol_imap are outside this header and cannot be inspected; only the extern declaration is visible.

<a id="u-7a9c455f6641"></a>
### `Curl_h1_req_parse_init`

`void Curl_h1_req_parse_init(struct h1_req_parser *parser, size_t max_line_len)` · [lib/http1.c:L36-L41][f6]

Zero-initializes an HTTP/1 request parser and records its maximum line length.

It memsets the whole parser, stores max_line_len, and initializes the scratch dynbuf with that same limit.

**Notes.**

- side_effect: Wipes all prior parser state, including any pending scratch buffer contents and the done flag.

calls: [curlx_dyn_init](r3-dynbuf.md#u-dba8ba103985)

<a id="u-03de60a3c064"></a>
### `Curl_h1_req_parse_free`

`void Curl_h1_req_parse_free(struct h1_req_parser *parser)` · [lib/http1.c:L43-L51][f6]

Releases an HTTP/1 request parser's resources.

When parser is non-NULL it frees the parsed request via Curl_http_req_free, frees the scratch dynbuf, clears parser->req, and resets done to FALSE. A NULL parser is silently ignored.

calls: [http-c-httpreq-lifecycle](r6-http-req-resp-objects.md#u-4a9c07117d37), [curlx_dyn_free](r3-dynbuf.md#u-21f694d1bd8a)

<a id="u-e73c5ea70c5f"></a>
### `Curl_h1_req_parse_read`

`CURLcode Curl_h1_req_parse_read(struct h1_req_parser *parser, const uint8_t *buf, siz…` · [lib/http1.c:L262-L320][f6]

Feeds a byte buffer into the HTTP/1 request parser until the header block is complete or input is exhausted.

A NULL buf returns CURLE_BAD_FUNCTION_ARGUMENT. The loop calls next_line for each line; CURLE_AGAIN is normalized to CURLE_OK (input exhausted) and returned, while other errors abort. Consumed bytes advance buf/buflen and accumulate in *pnread. Per line: if no complete line was found and buflen is now zero, it returns having consumed everything; otherwise the first complete line is parsed into a request via start_req (failures abort); an empty line after headers marks the request done, resets the scratch buffer, and ends the loop; any other line is appended as a header via Curl_dynhds_h1_add_line (failures abort). On success the parser keeps leftover state so the caller can resume with more data.

**Notes.**

- contract: *pnread reports total bytes consumed from buf; callers should pass only that many bytes onward.

calls: [next_line](r11-http-model.md#u-e28d5f27d882), [start_req](r11-http-model.md#u-ce242466daff), [Curl_dynhds_h1_add_line](r10-dynamic-headers.md#u-6411eda4200d), [curlx_dyn_reset](r3-dynbuf.md#u-76d5fbff65c6)

**Uncertainties.**

- The dead branch checking !parser->req after headers are underway (parser->done path) appears unreachable given start_req runs first; its intended semantics are unclear from this file.

<a id="u-edecd4d8e388"></a>
### `Curl_h1_req_write_head`

`CURLcode Curl_h1_req_write_head(struct httpreq *req, int http_minor, struct dynbuf *d…` · [lib/http1.c:L322-L345][f6]

Serializes an HTTP request's head into a dynbuf as 'METHOD TARGET HTTP/1.<minor>\r\n' plus headers and blank line.

The request-URI is composed as scheme + '://' + authority + path, each part omitted when NULL; http_minor selects the minor version. It appends the start line with curlx_dyn_addf, prints headers with Curl_dynhds_h1_dprint, then appends the terminating CRLF; any dynbuf failure aborts and is returned immediately.

calls: [curlx_dyn_addf](r3-dynbuf.md#u-063790a51674), [Curl_dynhds_h1_dprint](r10-dynamic-headers.md#u-840ea3a562ff), [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947)

**Uncertainties.**

- Whether a NULL path with non-NULL scheme yields a well-formed absolute URI is decided by caller-provided request fields, not here.

<a id="u-97bcbb5a2e62"></a>
### `detect_line`

`static CURLcode detect_line(struct h1_req_parser *parser, const uint8_t *buf, const s…` · [lib/http1.c:L77-L92][f6]

Scans the input buffer for a complete newline-terminated line.

It sets *pnread to 0 first; if no '\n' exists in buf it returns CURLE_AGAIN. On success it points parser->line at buf, sets line_len through the '\n' inclusive, reports that many bytes as consumed via *pnread, and returns CURLE_OK. Asserts no line is already pending.

<a id="u-adc70e5d1c14"></a>
### `trim_line`

`static CURLcode trim_line(struct h1_req_parser *parser, int options)` · [lib/http1.c:L53-L75][f6]

Trims CRLF line endings from the parser's current line and enforces the maximum line length.

It strips a trailing '\n', then a trailing '\r'. In H1_PARSE_OPT_STRICT mode, a missing '\r', a line consisting only of '\n', or an empty line each returns CURLE_URL_MALFORMAT; non-strict mode accepts them. Any line longer than max_line_len after trimming is rejected with CURLE_URL_MALFORMAT. Returns CURLE_OK otherwise; asserts parser->line is set.

<a id="u-e28d5f27d882"></a>
### `next_line`

`static CURLcode next_line(struct h1_req_parser *parser, const uint8_t *buf, const siz…` · [lib/http1.c:L94-L129][f6]

Retrieves the next complete line, buffering partial input across calls.

It first clears any previous line and resets the scratch dynbuf, then detects a line in buf. If a line is found and scratch already holds earlier bytes, the detected line is appended to scratch and parser->line/line_len are repointed at the scratch contents, giving the full line; then trim_line validates and trims it. If no newline is found (CURLE_AGAIN), the whole buf is appended to scratch and *pnread is set to buflen, consuming everything. Other errors propagate; dynbuf append failures are returned as-is.

calls: [detect_line](r11-http-model.md#u-97bcbb5a2e62), [trim_line](r11-http-model.md#u-adc70e5d1c14), [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947)

**Uncertainties.**

- Whether curlx_dyn_addn can fail only with OOM-type errors is not shown; any error returned aborts next_line without state recovery beyond propagation.

<a id="u-ce242466daff"></a>
### `start_req`

`static CURLcode start_req(struct h1_req_parser *parser, const char *scheme_default, c…` · [lib/http1.c:L131-L260][f6]

Parses the request line 'METHOD TARGET HTTP_VERSION' into a struct httpreq stored in parser->req.

If custom_method matches the line prefix, the method length is fixed to that prefix; otherwise the method is text up to the first space (a line without a leading space fails as CURLE_URL_MALFORMAT). The version is located by scanning backwards from the line end for a space, so targets may contain spaces; a missing target or version fails. Target forms: '*' is asterisk-form (path); a CONNECT method yields authority-form (authority only); a leading '/' is origin-form (path); otherwise the target is copied into a stack buffer (targets >= H1_MAX_URL_LEN fail) and, if Curl_is_absolute_url accepts it, parsed with curl_url_set using NON_SUPPORT_SCHEME|PATH_AS_IS|NO_DEFAULT_PORT plus CURLU_ALLOW_SPACE when not strict; a non-strict parse also allows relative targets as paths. In strict mode a non-absolute target without a leading '/' fails. When a URL handle was built, the request is created via Curl_http_req_make2; otherwise scheme defaults to scheme_default when set and the request is built with Curl_http_req_make from explicit scheme/authority/path parts. On any failure it returns CURLE_URL_MALFORMAT (or CURLE_OUT_OF_MEMORY if curl_url fails) and cleans up the CURLU handle.

**Notes.**

- side_effect: On success sets parser->req; the CURLU handle is always cleaned up locally, transferring ownership of parsed data into the request.

calls: [Curl_is_absolute_url](r6-url-parse-pipeline.md#u-a006636e95c1), [curl_url](r6-url-handle-api.md#u-c69ca9bdf3f3), [curl_url_set](r6-url-handle-api.md#u-68d6b32905a9), [curl_url_cleanup](r6-url-handle-api.md#u-9d451bd158e3), [http-c-httpreq-lifecycle](r6-http-req-resp-objects.md#u-4a9c07117d37)

**Uncertainties.**

- How Curl_http_req_make/make2 treat the scheme/authority/path parts is defined in lib/http.c and not visible here.
- Exact CURLUcode-to-CURLcode mapping for url parse failure is hidden because uc is discarded at the goto out.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/dynhds.h
[f2]: ../../../../../../eval/curl-2c04412/lib/http.h
[f3]: ../../../../../../eval/curl-2c04412/lib/request.h
[f4]: ../../../../../../eval/curl-2c04412/lib/getinfo.h
[f5]: ../../../../../../eval/curl-2c04412/lib/imap.h
[f6]: ../../../../../../eval/curl-2c04412/lib/http1.c
