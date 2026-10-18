# Request Construction and Send

**Capability.** Assembles the outgoing request: method/version selection, Host/Cookie/Range/Connection headers, custom and time-condition headers, body length and transfer-encoding, request-target, reader installation, and fresh-connection negotiation.

Use to understand what bytes go on the wire for a request. Curl_http orchestrates; header-slot emission flows through http_add_hd. Depends on the URL API for targets and connection setup for multiplex configuration.

**Depends on.**

- [Connection Setup and Control](r6-connection-management.md) · graph-confirmed · 1 edge(s)
- [Auth Emission and Expect-100](r6-http-auth-and-expect.md) · graph-confirmed · 2 edge(s)
- [Shared HTTP Header Utilities](r6-http-shared-header-utils.md) · graph-confirmed · 7 edge(s)
- [CURLU Handle Management and Setters](r6-url-handle-api.md) · graph-confirmed · 14 edge(s)
- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-only · 50 edge(s)

Parent: [HTTP Protocol Engine](r6-http-engine.md)

## Units (18)

<a id="u-eed3269af713"></a>
### `Curl_http`

`CURLcode Curl_http(struct Curl_easy *data, bool *done)` · [lib/http.c:L3082-L3164][f1]

Builds and sends the complete HTTP request for the DO phase.

Marks the phase done up front, initializes the request dynbuf, resets leftover header state and folding flags. On a fresh connection runs http_check_new_conn; (re)initializes client header collecting; clears the TE/Upgrade/H2-settings flags; determines method via Curl_http_method; selects the Host header; emits auth headers; installs the body reader, checks resume legality and ranges; computes the request version; then appends every header slot H1_HD_REQUEST through H1_HD_LAST. Finally sets up send/recv transfer and sends the buffer with Curl_req_send; chunky upload is re-disabled for HTTP/2+. On CURLE_TOO_LARGE it logs 'HTTP request too large'. The request buffer is always freed; any error propagates.

calls: [http_add_hd](r6-http-request-build.md#u-e79cfa404027), [Curl_req_send](r10-request-send-path.md#u-4a6982939b27), [Curl_xfer_setup_sendrecv](r10-xfer-direction-api.md#u-c56645f36b43)

<a id="u-0d3c0cf27087"></a>
### `Curl_http_method`

`void Curl_http_method(struct Curl_easy *data, const char **method, Curl_HttpReq *reqp)` · [lib/http.c:L2023-L2068][f1]

Determines the request method string and internal request kind.

WebSocket schemes force GET; HTTP/FTP schemes with state.upload force PUT. Unless the custom request was ignored for this transfer (http_ignorecustom) and a STRING_CUSTOMREQUEST is set, that custom string is the method. Otherwise req.no_body forces HEAD; else the kind maps to POST (all POST variants), PUT, GET (default) or HEAD.

**Uncertainties.**

- The DEBUGASSERT bounds httpreq to GET..HEAD; other values would hit the default GET path.

<a id="u-e79cfa404027"></a>
### `http_add_hd`

`static CURLcode http_add_hd(struct Curl_easy *data, struct dynbuf *req, http_hd_t id,…` · [lib/http.c:L2927-L3075][f1]

Emit switch for one header slot in the fixed request order (H1_HD_REQUEST ..

H1_HD_LAST enum at lines 2898-2925). REQUEST writes '<method> ' + target via http_target + ' HTTP/<version>'. HOST, PROXY_AUTH, AUTH, RANGE append their prebuilt lines when set. USER_AGENT, ACCEPT, TE (with libz and option), ACCEPT_ENCODING, REFERER add defaults unless a custom header exists. PROXY_CONNECTION adds Keep-Alive only through an origin proxy without custom headers. TRANSFER_ENCODING delegates to http_req_set_TE. ALT_USED emits Alt-Used for alt-svc connections. UPGRADE performs the HTTP/2 Upgrade magic on non-TLS HTTP/1.x when h2 upgrade is negotiated, and WebSocket request setup for ws/wss schemes. COOKIES, CONDITIONALS, CUSTOM, CONTENT and CONNECTION delegate to http_cookies, Curl_add_timecondition, Curl_add_custom_headers, http_add_content_hds and http_add_connection_hd. LAST writes the terminating empty line.

group: [http-c-body-and-te](r6-http-request-build.md#u-b0157126eca4); calls: [http_target](r6-http-request-build.md#u-8e3ad0dd14d8)

<a id="u-a88f88b1383e"></a>
### `http_add_connection_hd`

`static CURLcode http_add_connection_hd(struct Curl_easy *data, struct dynbuf *req)` · [lib/http.c:L2836-L2895][f1]

Composes the Connection header.

The first non-empty custom 'Connection' header's value is copied (via copy_custom_value, propagating parse errors) into 'Connection: <value>'. Internal tokens TE, Upgrade and HTTP2-Settings are appended when the corresponding state flags were set, comma-separated. If anything was written, CRLF terminates. Remaining custom Connection headers are then appended verbatim, skipping the already-used first one; empty values are skipped in both passes.

uses: [http-c-header-value-helpers](r6-http-shared-header-utils.md#u-bbcfa3186b14)

<a id="u-9774051d9d55"></a>
### `http_cookies`

`static CURLcode http_cookies(struct Curl_easy *data, struct dynbuf *r)` · [lib/http.c:L2594-L2663][f1]

Builds the Cookie request header.

A custom STRING_COOKIE is used only when no custom Cookie header exists and cross-host sending is allowed. When a cookie engine is active, matching cookies for the custom cookiehost or origin hostname are fetched under the cookie share lock and appended as 'Cookie: name=value; ...' pairs, stopping and logging when MAX_COOKIE_HEADER_LEN would be exceeded (linecap). Custom cookies are appended afterwards unless capped, and a terminating CRLF is added when any cookie was written. Errors propagate; compiled out it is a macro returning CURLE_OK.

**Notes.**

- side_effect: Takes and releases the CURL_LOCK_DATA_COOKIE share lock.

<a id="u-8e3ad0dd14d8"></a>
### `http_target`

`static CURLcode http_target(struct Curl_easy *data, struct dynbuf *r)` · [lib/http.c:L2161-L2281][f1]

Appends the request-target to the outgoing request.

A STRING_TARGET option replaces both path and query. Via a non-tunneling proxy it reconstructs the absolute URL from state.uh: for non-IPv6 origins with a decoded (IDN) hostname it rewrites the host part, drops the fragment, removes userinfo for plain http (or injects non-URL-cred source credentials for other schemes with URLENCODE), and extracts the URL without default port; the target option still overrides. FTP over proxy with proxy_transfer_mode appends ';type=a' or ';type=i' unless one is already present. Without a proxy it appends the path plus '?query' when present. Memory and URL errors propagate; several proxy-path failures map to CURLE_OUT_OF_MEMORY.

**Uncertainties.**

- Mapping some curl_url_set failures to OUT_OF_MEMORY may mask other CURLUcode causes.

<a id="u-f854c092c8e0"></a>
### `http_set_aptr_host`

`static CURLcode http_set_aptr_host(struct Curl_easy *data)` · [lib/http.c:L2070-L2156][f1]

Computes the Host header for the request and the cookie host.

Frees previous values first. When this is not a redirect (initial origin equals current origin) a custom Host header is looked up; if found, its value (parsed via copy_custom_value) becomes req.cookiehost after stripping brackets or a trailing port, and unless the header is literally 'Host:' the http_host is set to 'Host:<value>'. Without a custom header, http_host is built as 'Host: [ipv6]' + hostname, appending ':%u' when the port differs from the scheme default or the scheme family differs from the connection scheme. OOM propagates from either path; the generated path takes ownership of the dynbuf.

**Notes.**

- side_effect: Frees and replaces data->state.http_host and data->req.cookiehost.

**Uncertainties.**

- Behavior when copy_custom_value fails mid-way (cookiehost already freed) is a plain error return.

<a id="u-c60c56589e5d"></a>
### `http_range`

`static CURLcode http_range(struct Curl_easy *data, Curl_HttpReq httpreq)` · [lib/http.c:L2668-L2725][f1]

Prepares Range or Content-Range headers when state.use_range is set, never overriding a user-supplied header.

For GET/HEAD without a custom Range it formats 'Range: bytes=<range>'. For POST/PUT without a custom Content-Range it picks by state: negative set_resume_from formats 'bytes 0-(len-1)/len'; resume_from formats 'bytes <range><len-1>/<len>' using infilesize during authneg; otherwise 'bytes <range>/<len>' with the reader length. OOM on formatting propagates; the produced line is stored in state.rangeline for later emission.

<a id="u-67f3be70fb51"></a>
### `set_reader`

`static CURLcode set_reader(struct Curl_easy *data, Curl_HttpReq httpreq)` · [lib/http.c:L2362-L2421][f1]

Installs the client reader that produces the request body.

During authneg a null reader is used (zero-length probe). PUT uses an fread reader of postsize bytes, or a null reader when postsize is zero. Form/MIME posts delegate to set_post_reader: MIME uses the user's mime structure; FORM converts the form once into a mime part (OOM or form errors abort), marks it body-only, prepares its headers using a custom Content-Type value (or 'multipart/form-data' for multiparts) and attaches the form headers, then sets a mime reader; without mime support a null reader is used; infilesize is set from the resulting reader length. Plain POST with no size uses a null reader; with postfields a buffer reader (size clamped to SIZE_MAX, OOM on overflow); otherwise an fread reader whose length is -1 when the custom Transfer-Encoding header requests chunked (deliberately ignoring postsize in that legacy case). All other methods clear infilesize and use a null reader.

calls: [set_reader](r6-http-request-build.md#u-67f3be70fb51), [Curl_compareheader](r6-http-shared-header-utils.md#u-4a483dec7872)

<a id="u-142ee6faee76"></a>
### `http_check_new_conn`

`static CURLcode http_check_new_conn(struct Curl_easy *data)` · [lib/http.c:L2787-L2834][f1]

Configures protocol behavior for a fresh connection based on negotiated ALPN.

'h3' logs HTTP/3 (asserting the connection version outside proxying). 'h2' through a proxy whose version is not yet 20 switches to HTTP/2 via Curl_http2_switch. Without ALPN h2, if an HTTP/2 upgrade over clean TCP is allowed it switches, marks httpversion_seen 20 and enables multiplexing; otherwise it logs HTTP/1.x. Errors from the switch propagate.

**Uncertainties.**

- DEBUGASSERT on h3 version is active only in debug builds.

<a id="u-2ee07804c56c"></a>
### `Curl_add_custom_headers`

`CURLcode Curl_add_custom_headers(struct Curl_easy *data, bool is_connect, int httpver…` · [lib/http.c:L1808-L1942][f1]

Appends user-set custom headers to the request buffer, choosing the list(s) by role: server requests use set.headers; proxy requests add proxyheaders when sep_headers is on; CONNECT (and CONNECT-UDP) use proxyheaders if separated, else headers.

A header ending in a bare ';' (with no colon in the name) is a blank-value header emitted as 'name:\r\n'; a normal 'name: value' header with an empty trimmed value is skipped; a line without a colon is skipped. Field names are trimmed of surrounding blanks before matching, so 'Authorization :' cannot evade the sensitive-header checks. Suppression rules: Host (already sent), Content-Type for form/mime posts, Content-Length during authneg, Connection (handled separately), Transfer-Encoding on HTTP/2+, and Authorization or Cookie when cross-host forwarding is not allowed. Blank headers are appended as name plus ':\r\n'; others verbatim plus CRLF. First OOM aborts with the error.

**Notes.**

- contract: Sensitive header suppression depends on Curl_auth_allowed_to_host for redirected cross-host sends.

calls: [curlx_dyn_addf](r3-dynbuf.md#u-063790a51674)

**Uncertainties.**

- HEADER_CONNECT_UDP selection path is not visible in this file's callers.

<a id="u-efade3ef2989"></a>
### `Curl_add_timecondition`

`CURLcode Curl_add_timecondition(struct Curl_easy *data, struct dynbuf *req)` · [lib/http.c:L1945-L2011][f1]

Adds a conditional request header from the configured time condition and value.

Returns early when the condition is NONE. Converts timevalue with curlx_gmtime (failing with 'Invalid TIMEVALUE' on error) and maps IFMODSINCE/IFUNMODSINCE/LASTMOD to their header names; other values give CURLE_BAD_FUNCTION_ARGUMENT. If the user already supplied the same header, the custom one wins. Otherwise formats a GMT date string and appends it to the request buffer. The alternate inventory entry for this symbol is the stub compiled when parsedate support is disabled, which always returns CURLE_OK.

**Uncertainties.**

- Weekday indexing assumes tm_wday 0 is Sunday (index minus one, else index 6).

<a id="u-d4ede5b0c4c2"></a>
### `Curl_checkProxyheaders`

`char *Curl_checkProxyheaders(struct Curl_easy *data, const struct connectdata *conn, …` · [lib/http.c:L150-L166][f1]

Searches the custom header list for a header whose name equals thisheader (length thislen, case-insensitive, followed by a header separator) and returns the matching raw header line or NULL.

When a proxy peer exists and separate headers are enabled it scans proxyheaders, otherwise the normal headers list. Compiled out with CURL_DISABLE_PROXY.

**Uncertainties.**

- Curl_headersep is defined elsewhere.

<a id="u-1369787fcf66"></a>
### `Curl_http_neg_init`

`void Curl_http_neg_init(struct Curl_easy *data, struct http_negotiation *neg)` · [lib/http.c:L88-L124][f1]

Initializes the per-transfer HTTP version negotiation structure from user settings.

Zeroes *neg, copies http09_allowed into accept_09, then a switch on data->set.httpwant sets wanted/allowed version bitmasks: 1.0 sets only_10; 2.0 sets h2_upgrade; 2TLS allows h2 only implicitly via connect logic; PRIOR_KNOWLEDGE forces V2x only and sets state h2_prior_knowledge; 3/3ONLY restrict to V3x (3 allows downgrade, 3ONLY does not); NONE/default wants V1x|V2x and also allows V3x.

**Uncertainties.**

- Exact semantics of the CURL_HTTP_V* bit constants are defined in headers not supplied.

<a id="u-6f49bd965ca5"></a>
### `Curl_http_setup_conn`

`CURLcode Curl_http_setup_conn(struct Curl_easy *data, struct connectdata *conn)` · [lib/http.c:L126-L138][f1]

Validates protocol constraints before connection setup: if the negotiation wants only HTTP/3 it calls Curl_conn_may_http3 and propagates any failure, otherwise returns CURLE_OK.

No allocation despite the comment about the per-request struct.

calls: [Curl_conn_may_http3](r10-quic-filter-lifecycle.md#u-be8c618bdb9f)

<a id="u-b0157126eca4"></a>
### `http-c-body-and-te`

`static CURLcode http_resume(struct Curl_easy *data, Curl_HttpReq httpreq)` · [lib/http.c:L2423-L2432][f1]

Request body length and transfer-encoding helpers.

http_resume rejects a resume_from on any upload method with CURLE_BAD_FUNCTION_ARGUMENT. http_req_set_TE honors a custom Transfer-Encoding header, setting upload_chunky only when it says 'chunked', and suppresses chunky on HTTP/2+; without a custom header it enables chunky for indeterminate body length on HTTP/1.1 (not 2+), fails with CURLE_UPLOAD_FAILED on HTTP/1.0, and disables chunky for known lengths, appending 'Transfer-Encoding: chunked' when enabled. addexpect decides Expect: 100-continue: skipped entirely when an upgrade is pending; a custom Expect header announces exp100 only if it contains '100-continue'; otherwise on HTTP/1.1 (unless disabled) bodies over EXPECT_100_THRESHOLD or of unknown length get the header appended and announce it. http_add_content_hds adds a chunked reader when chunky, then for PUT/POST variants emits Content-Length when the length is known, not chunky, and either authneg or no custom header; appends mime-generated headers for form/mime; adds the default urlencoded Content-Type for plain POST when absent; calls addexpect; finally records the upload size and installs the exp100 reader when the expectation was announced.

calls: [Curl_compareheader](r6-http-shared-header-utils.md#u-4a483dec7872); uses: [http-c-exp100-reader](r6-http-auth-and-expect.md#u-d25da102592f)

<a id="u-e5402211e9fb"></a>
### `http-c-request-version-helpers`

`static bool http_may_use_1_1(const struct Curl_easy *data)` · [lib/http.c:L1765-L1782][f1]

Chooses the HTTP version for the outgoing request.

http_may_use_1_1 returns FALSE when a previous response on this transfer or this connection used HTTP/1.0, when only 1.0 is wanted and no higher version was seen on the connection, and otherwise only when only_10 is false — i.e. 1.1 is allowed unless pinned to 1.0 by settings or observed responses. http_request_version asks the connection filter for its HTTP version and falls back to 11 or 10 based on http_may_use_1_1 when no specific filter is installed. get_http_string maps the numeric version (30/20/11/other) to the wire string '3'/'2'/'1.1'/'1.0'.

**Uncertainties.**

- Curl_conn_http_version's return encoding is defined in cfilters headers.

<a id="u-d5871a921e49"></a>
### `http-c-pollsets`

`CURLcode Curl_http_doing_pollset(struct Curl_easy *data, struct easy_pollset *ps)` · [lib/http.c:L1670-L1675][f1]

Pollset contributions while an HTTP request is in flight.

Curl_http_doing_pollset always waits for writability of the first socket. Curl_http_perform_pollset adds read interest when the request wants to receive, and adds write interest when the request wants to send, except during an active Expect: 100-continue timed wait, where outgoing polling is suppressed. Errors from pollset changes propagate.

uses: [http-c-exp100-reader](r6-http-auth-and-expect.md#u-d25da102592f)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http.c
