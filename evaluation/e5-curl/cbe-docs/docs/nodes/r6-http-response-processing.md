# Response Parsing and Reaction

**Capability.** Incremental parsing of the received response: status-line recognition, header extraction and dispatch, per-letter header handlers, size limits, and central reactions (auth act, failure, first-write, send-error, 1xx/101, done, redirect following).

Trace received bytes: http_parse_headers buffers lines, http_rw_hd validates and dispatches, http_on_response applies decisions. Location handling and rewind planning live here. Uses shared header utilities and depends on connection control and auth/Expect-100 helpers.

**Depends on.**

- [Connection Setup and Control](r6-connection-management.md) · graph-confirmed · 17 edge(s)
- [Auth Emission and Expect-100](r6-http-auth-and-expect.md) · graph-confirmed · 6 edge(s)
- [HTTP Request/Response Objects](r6-http-req-resp-objects.md) · model-inferred · 0 edge(s)
- [Shared HTTP Header Utilities](r6-http-shared-header-utils.md) · graph-confirmed · 8 edge(s)
- [Share API](r6-share-api.md) · graph-confirmed · 2 edge(s)
- [CURLU Handle Management and Setters](r6-url-handle-api.md) · graph-confirmed · 16 edge(s)
- [Trace and Debug Logging](r1-trace-logging.md) · graph-only · 56 edge(s)
- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-only · 29 edge(s)

Parent: [HTTP Protocol Engine](r6-http-engine.md)

## Units (30)

<a id="u-252e5c7db34e"></a>
### `http_parse_headers`

`static CURLcode http_parse_headers(struct Curl_easy *data, const char *buf, size_t bl…` · [lib/http.c:L4493-L4660][f1]

Increments through the receive buffer extracting header lines, accumulating into state.headerb.

Folded (obs-fold) continuation lines are handled two ways: when the next byte is already buffered and blank, the held line's trailing CRLF/blanks are trimmed and folding continues; when the buffer ends exactly after a line, maybe_folded defers the decision to the next invocation, and after an unfold exactly one space is inserted before the continuation. Incomplete lines are buffered, with an early protocol check on the first line: a non-matching first line closes the stream and either fails (CURLE_WEIRD_SERVER_REPLY if a version was seen or the connection is reused; CURLE_UNSUPPORTED_PROTOCOL when 0.9 is not allowed) or treats the bytes as an HTTP/0.9 body. Complete non-status lines that are followed by a blank next line fold; otherwise http_rw_hd processes each line and the header buffer resets. Consumption counts include folded whitespace. On leaving the header phase without a 0.9 leftover the header buffer is freed.

**Uncertainties.**

- Exact interaction when http_rw_hd recursively re-enters via version switch is only guarded by resetting headerb.

<a id="u-f41b6942b3f8"></a>
### `http_rw_hd`

`static CURLcode http_rw_hd(struct Curl_easy *data, const char *hd, size_t hdlen, cons…` · [lib/http.c:L4301-L4468][f1]

Processes one buffered header line.

A line starting with LF or CR ends the header block: the line is copied, the shared headerb is reset (allowing recursion on version switch), and http_on_response runs with the remaining buffer to consume body/upgrade bytes; the consumed count is forwarded. Otherwise, the first line must be a status line: for HTTP it parses 'HTTP/1.x NNN' (single following blank tolerated loosely) or 'HTTP/2'/'HTTP/3' with three digits; unsupported subversions fail with CURLE_UNSUPPORTED_PROTOCOL; unrecognized lines fall back to the HTTP200ALIASES check, treating a match as HTTP/1.0 code 200. For RTSP it parses 'RTSP/1.0 NNN' and treats it as version 11. A fine status line runs http_statusline and marks the write as a STATUS line; otherwise the header phase ends and CURLE_WEIRD_SERVER_REPLY is returned. Every subsequent line passes Curl_verify_header, then http_header, is debug-dumped, written to the client (with the 1XX flag when applicable) and accounted via Curl_bump_headersize.

calls: [http_on_response](r6-http-response-processing.md#u-aa04613f8744), [http_statusline](r6-http-response-processing.md#u-8bc24656a611), [http_header](r6-http-response-processing.md#u-f0dc471dfa1a)

<a id="u-f0dc471dfa1a"></a>
### `http_header`

`static CURLcode http_header(struct Curl_easy *data, const char *hd, size_t hdlen)` · [lib/http.c:L3717-L3763][f1]

Dispatches one response header line to the per-letter handler based on its first character (case-insensitive A/C/L/P/R/S/T/W), then, for RTSP connections, additionally runs Curl_rtsp_parseheader.

Errors from any handler propagate and stop further processing.

group: [http-c-header-parsers-small](r6-http-response-processing.md#u-b83d2fd51d2b); calls: [http_header_c](r6-http-response-processing.md#u-a8063aef6ea7), [http_header_l](r6-http-response-processing.md#u-c6f04d889615), [http_header_p](r6-http-response-processing.md#u-fedcd4d4b27f), [http_header_s](r6-http-response-processing.md#u-3343f7195b5e), [http_header_t](r6-http-response-processing.md#u-ae1e4611f1fe)

<a id="u-a8063aef6ea7"></a>
### `http_header_c`

`static CURLcode http_header_c(struct Curl_easy *data, const char *hd, size_t hdlen)` · [lib/http.c:L3283-L3414][f1]

Handles Content-* and Connection headers.

Content-Length (skipped for bodyless responses, ignorecl, or user opt-out) is parsed allowing a comma-separated list of identical values: an overflow value fails with CURLE_FILESIZE_EXCEEDED when max_filesize is set, otherwise the connection is closed and the header ignored; a valid value matching any previously seen value (or when unset) is accepted, and at end-of-value sets k->size and k->maxdownload; negative, differing or junk values fail with CURLE_WEIRD_SERVER_REPLY. Content-Encoding (when decompression is configured and not bodyless) builds the unencoding stack, errors deferred. Content-Type is stored in info.contenttype via Curl_copy_header_value (OOM propagates, empty ignored). On HTTP/1.x 'Connection: close' closes the pool connection; HTTP/1.0 'Connection: keep-alive' keeps it. Content-Range (non-bodyless) is scanned for the first digit or '*': a digit sets k->offset and marks content_range when it matches the resume point; '*' on a <300 code resets resume_from to fetch everything.

**Notes.**

- failure: Duplicate or contradictory Content-Length values abort with CURLE_WEIRD_SERVER_REPLY.

<a id="u-c6f04d889615"></a>
### `http_header_l`

`static CURLcode http_header_l(struct Curl_easy *data, const char *hd, size_t hdlen)` · [lib/http.c:L3419-L3474][f1]

Handles Last-Modified and Location.

Last-Modified is parsed only when a time condition or filetime request exists; an unparseable date yields 0, and the value is stored in k->timeofdoc and, when requested, info.filetime. Location is always processed: the value is copied (OOM propagates); empty values or an exact repeat of a previous Location are ignored; a second distinct Location is an error (CURLE_WEIRD_SERVER_REPLY). The first Location is stored in req.location; on a 3xx with following enabled it clones the URL into req.newurl, runs http_perhapsrewind (result propagates) and marks this_is_a_follow.

calls: [http_perhapsrewind](r6-http-response-processing.md#u-8f2ff4645684)

<a id="u-fedcd4d4b27f"></a>
### `http_header_p`

`static CURLcode http_header_p(struct Curl_easy *data, const char *hd, size_t hdlen)` · [lib/http.c:L3479-L3547][f1]

Handles Proxy-* and Persistent-Auth headers.

Proxy-Connection on HTTP/1.0 from a proxy with 'keep-alive' keeps the connection; on HTTP/1.1 with 'close' closes it; otherwise the header is consumed with no effect. Proxy-authenticate on a 407 is processed only when the response really comes from a forward proxy: the value is copied and passed to Curl_http_input_auth with proxy=TRUE (OOM propagates). With SPNEGO, Persistent-Auth is honored when Negotiate was picked: 'false' sets noauthpersist on the negotiate data, recorded with havenoauthpersist.

calls: [Curl_http_input_auth](r6-http-response-processing.md#u-06479200bfce)

<a id="u-3343f7195b5e"></a>
### `http_header_s`

`static CURLcode http_header_s(struct Curl_easy *data, const char *hd, size_t hdlen)` · [lib/http.c:L3585-L3644][f1]

Handles Set-Cookie and Strict-Transport-Security.

Set-Cookie is consumed when a cookie engine is active: the host is the custom cookiehost or origin hostname, the secure flag derives from the secure context, and the cookie is added under the cookie share lock, propagating errors. HSTS parses Strict-Transport-Security only when HSTS is enabled and the transfer is secure (or the debug env override allows HTTP); parse errors other than OOM are logged and skipped, OOM propagates.

**Notes.**

- side_effect: Takes/releases the cookie share lock; mutates cookie and HSTS stores.

<a id="u-ae1e4611f1fe"></a>
### `http_header_t`

`static CURLcode http_header_t(struct Curl_easy *data, const char *hd, size_t hdlen)` · [lib/http.c:L3649-L3691][f1]

Handles Transfer-Encoding and Trailer.

Transfer-Encoding is processed only when the response can have a body (not bodyless, not a HEAD request, not 304): the encoding stack is built (propagating errors); if the result is not chunked, Content-Length cannot be trusted, so the connection is closed and ignore_cl is set, meaning the body ends only at connection close. Trailer merely marks req.resp_trailer so trailing headers are expected later.

<a id="u-8bc24656a611"></a>
### `http_statusline`

`static CURLcode http_statusline(struct Curl_easy *data, struct connectdata *conn)` · [lib/http.c:L3769-L3853][f1]

Processes the parsed status line.

Accepts versions 10/11 (and 20/30 when built in); a mid-connection major-version switch from what was sent fails with CURLE_WEIRD_SERVER_REPLY, and unknown versions fail with CURLE_UNSUPPORTED_PROTOCOL. Records info.httpcode/httpversion, conn->httpversion_seen and the lowest version seen for the transfer. A 416 to a resume GET marks ignorebody. HTTP/1.0 defaults to closing after the body. Codes 100-199 mark the response bodyless; 304 additionally flags timecond when set and falls through to 204 handling, which forces size, maxdownload and bodyless to zero.

**Notes.**

- field: k->http_bodyless is true for all 1xx plus 204 and 304.

<a id="u-58d9eb6aecce"></a>
### `Curl_http_decode_status`

`CURLcode Curl_http_decode_status(int32_t *pstatus, const char *s, size_t len)` · [lib/http.c:L4740-L4762][f1]

Decodes exactly three ASCII digits into a status code.

Any other length or non-digit fails with CURLE_BAD_FUNCTION_ARGUMENT; on failure *pstatus is -1, on success the parsed value.

<a id="u-9655fc83ca4e"></a>
### `Curl_verify_header`

`CURLcode Curl_verify_header(struct Curl_easy *data, const char *hd, size_t hdlen)` · [lib/http.c:L3881-L3917][f1]

Syntax-validates a received header line.

A NUL byte anywhere, or a CR not immediately preceding the final LF position, fails with CURLE_WEIRD_SERVER_REPLY. The status line (headerline < 2) is exempt from colon requirements; folded continuation lines (leading blank after line 2) are accepted; any other line without a colon fails.

**Uncertainties.**

- The exact CR index condition allows CR only at hdlen-2 or hdlen-1; boundary intent inferred from the loop.

<a id="u-8e9f7a423b87"></a>
### `Curl_bump_headersize`

`CURLcode Curl_bump_headersize(struct Curl_easy *data, size_t delta, bool connect_only)` · [lib/http.c:L3919-L3944][f1]

Accounts response header bytes and enforces size limits.

Deltas under MAX_HTTP_RESP_HEADER_SIZE are added to info.header_size, req.allheadercount and, unless connect_only, req.headerbytecount. Failure conditions: total per-request headers exceed the max, total connection headers exceed 20x the max (limit then reported as 20x), or a single delta at or above the max (checked against the running total). On failure it fails with 'Too large response headers' and returns CURLE_RECV_ERROR; otherwise CURLE_OK.

<a id="u-aa04613f8744"></a>
### `http_on_response`

`static CURLcode http_on_response(struct Curl_easy *data, const char *last_hd, size_t …` · [lib/http.c:L4166-L4299][f1]

Central handler invoked when a complete response's headers have been read.

For an already-upgraded connection with a non-h2 response it just logs. 1xx codes write the header block to the client first, then delegate to http_on_1xx_response; codes under 100 fail with CURLE_UNSUPPORTED_PROTOCOL. For final responses the header phase ends; a requested-but-ungranted upgrade is cleared. On HTTP/1.1 without Content-Length, chunking or close, connection close is assumed to end the body. Auth negotiation closure is checked (http_check_auth_closure: connection close during NTLM/SPNEGO type-2/recv states sets authproblem; completed Negotiate promotes its state on non-401/407). http_should_fail can fail the transfer; Curl_http_auth_act picks auth and possibly sets newurl; codes >= 300 run http_handle_send_error; then http_firstwrite, http_size and RTSP body adjustments run; no_body or zero maxdownload (pre-HTTP/2) finalize the download. On exit the last header block is written unless already done (a write error only overrides when the main result is not already fatal), and a connection change pokes the multi handle.

calls: [http_handle_send_error](r6-http-response-processing.md#u-942b5f991fd7), [Curl_http_auth_act](r6-http-response-processing.md#u-4c9bddf46ee3), [http_firstwrite](r6-http-response-processing.md#u-3e78e5d0a315)

**Uncertainties.**

- Curl_1st_fatal precedence between the main result and the trailing header write is defined elsewhere.

<a id="u-f776a1798349"></a>
### `http_on_1xx_response`

`static CURLcode http_on_1xx_response(struct Curl_easy *data, const char *buf, size_t …` · [lib/http.c:L4013-L4040][f1]

Prepares for a 1xx intermediate response: keeps the header phase active and restarts the header line counter.

A 100 notifies the Expect: 100-continue reader via http_exp100_got100; a 101 delegates to the upgrade handler with buffer, consumed and connection-change outputs; other 1xx codes (e.g. 103) are ignored with more responses expected.

calls: [http_on_101_upgrade](r6-http-response-processing.md#u-09f394fd5375); uses: [http-c-exp100-reader](r6-http-auth-and-expect.md#u-d25da102592f)

<a id="u-09f394fd5375"></a>
### `http_on_101_upgrade`

`static CURLcode http_on_101_upgrade(struct Curl_easy *data, const char *buf, size_t b…` · [lib/http.c:L3950-L4007][f1]

Performs a 101 Switching Protocols upgrade.

Requires that HTTP/1.1 was sent, else CURLE_WEIRD_SERVER_REPLY. Marks upgr101 as RECEIVED, clears upgrade_in_progress and signals a connection change. When HTTP/2 was requested, the buffered bytes are handed to Curl_http2_upgrade and counted as consumed on success; when WebSocket was requested, Curl_ws_accept takes them likewise. An unsolicited 101 is silently treated as the final response (header phase ends).

**Uncertainties.**

- Upgrade response header verification is intentionally absent, as the comment states.

<a id="u-3e78e5d0a315"></a>
### `http_firstwrite`

`static CURLcode http_firstwrite(struct Curl_easy *data)` · [lib/http.c:L2727-L2785][f1]

First-write bookkeeping when a final response begins.

With a pending req.newurl and a closing connection it stops receiving, marks the request done and returns; otherwise it sets ignorebody so the superseded body is discarded. For a GET resume where the server did not honor ranges: if the document size equals the resume point it declares the download complete, closes the stream and finishes; otherwise CURLE_RANGE_ERROR. When a time condition is set without a range and the document's modification time fails the condition, it simulates a 304: sets info.httpcode, marks done and closes the connection.

**Notes.**

- side_effect: May close the connection stream and finalize req state.

<a id="u-942b5f991fd7"></a>
### `http_handle_send_error`

`static CURLcode http_handle_send_error(struct Curl_easy *data)` · [lib/http.c:L4090-L4164][f1]

Reacts to an error response (>= 300) arriving while the request body is still being sent, only when not in authneg, the connection is not already closing, and no rewind is planned.

For upload methods before sending finished: a 417 with the exp100 reader selected retries without Expect — if nothing was written yet while waiting it just logs, otherwise it closes the stream and runs http_perhapsrewind — then disables future Expect, aborts sending and clones the URL into req.newurl for the retry (OOM propagates). With keep_sending_on_error it continues sending and releases the 100-wait; otherwise it stops sending and closes the connection. Independently, when a rewind is pending and sending is unfinished, sending continues so the data can be tossed away.

calls: [http_perhapsrewind](r6-http-response-processing.md#u-8f2ff4645684); uses: [http-c-exp100-reader](r6-http-auth-and-expect.md#u-d25da102592f)

<a id="u-c705cfe36b72"></a>
### `http_should_fail`

`static bool http_should_fail(struct Curl_easy *data, int httpcode)` · [lib/http.c:L486-L547][f1]

Decides whether an HTTP response code is terminal.

Returns FALSE when fail_on_error is off or code < 400, and for a 416 to a resume GET. Codes >= 400 other than 401/407 always fail. For 401 it fails when no state.creds exist; for 407 when no proxy creds exist; otherwise the outcome is the stored state.authproblem flag.

<a id="u-4b4b110e65c5"></a>
### `http_size`

`static CURLcode http_size(struct Curl_easy *data)` · [lib/http.c:L3860-L3879][f1]

Finalizes the response length after all headers.

When Content-Length was ignored or the body is chunked, size and maxdownload are set to -1 (unknown, read to close). Otherwise, with a known size: exceeding max_filesize fails with CURLE_FILESIZE_EXCEEDED unless the body is being ignored; the download size is reported and maxdownload set to the size.

<a id="u-4c9bddf46ee3"></a>
### `Curl_http_auth_act`

`CURLcode Curl_http_auth_act(struct Curl_easy *data)` · [lib/http.c:L555-L639][f1]

After all response headers, picks authentication for host and proxy.

Ignores 1xx codes; on state.authproblem returns CURLE_HTTP_RETURNED_ERROR only if fail_on_error. Bearer is removed from the mask when no bearer creds exist. For host creds on a 401 (or any <300 during authneg) it picks an auth; a failed pick sets authproblem, success records info.httpauthpicked; an NTLM pick on HTTP/2+ forces HTTP/1.1 and closes the connection. Proxy handling mirrors this on 407. If any auth was picked it runs http_perhapsrewind and clones state.url into req.newurl to trigger the next request; with no pick, during authneg on a <300 response to a non-GET/HEAD it also clones the URL once (marking authhost.done). Finally http_should_fail can turn the code into CURLE_HTTP_RETURNED_ERROR.

calls: [pickoneauth](r6-http-auth-and-expect.md#u-3a27430cd9fe), [http_perhapsrewind](r6-http-response-processing.md#u-8f2ff4645684), [http_should_fail](r6-http-response-processing.md#u-c705cfe36b72)

**Uncertainties.**

- Curl_bufref_dup failure details depend on bufref.c.

<a id="u-06479200bfce"></a>
### `Curl_http_input_auth`

`CURLcode Curl_http_input_auth(struct Curl_easy *data, bool proxy, const char *auth) /…` · [lib/http.c:L1072-L1156][f1]

Processes an Authenticate header value (first non-space, NUL-terminated) for host or proxy depending on the proxy flag, writing availability into info.httpauthavail/proxyauthavail and the auth state.

Iterates over possibly comma-separated scheme tokens; for each, the matching handler (Negotiate, NTLM, Digest, Basic, Bearer) runs unless a previous handler returned an error, in which case the loop breaks and the error propagates. When all auth support is compiled out it returns CURLE_OK without touching state.

group: [http-c-input-auth-handlers](r6-http-response-processing.md#u-58e2b645bfef)

<a id="u-917d31ab5724"></a>
### `Curl_http_done`

`CURLcode Curl_http_done(struct Curl_easy *data, CURLcode status, bool premature)` · [lib/http.c:L1726-L1762][f1]

Per-request cleanup after the response.

Clears multipass on both auth states. If a leftover header block exists in state.headerb it is flushed through http_write_header and the buffer reset. A non-ok status propagates immediately. Otherwise, when the end was not premature, the connection is not being retried, connect_only is off, and body plus header bytes (minus deducted 1xx headers) total zero or less, it fails with 'Empty reply from server', closes the stream and returns CURLE_GOT_NOTHING.

calls: [http_write_header](r6-http-response-processing.md#u-bcffee049837)

<a id="u-bcffee049837"></a>
### `http_write_header`

`static CURLcode http_write_header(struct Curl_easy *data, const char *hd, size_t hdlen)` · [lib/http.c:L1694-L1719][f1]

Delivers one received header block to the client: debug-dumps it, writes it with CLIENTWRITE_HEADER plus CLIENTWRITE_1XX when the current code is 1xx, then accounts the length via Curl_bump_headersize.

For 1xx codes it snapshots req.headerbytecount into deductheadercount so the interim headers are not counted in the final tally. Errors from write or size accounting propagate.

calls: [Curl_bump_headersize](r6-http-response-processing.md#u-8e9f7a423b87)

<a id="u-8f2ff4645684"></a>
### `http_perhapsrewind`

`static CURLcode http_perhapsrewind(struct Curl_easy *data, struct connectdata *conn)` · [lib/http.c:L401-L476][f1]

Decides, when a request must be redone (redirect or auth negotiation), whether to rewind the upload and whether to abort the remaining upload.

If the client reader needs a rewind it enables it. If the connection is already marked close it returns without vetoing. Default abort condition: not upload_done and more than 2000 bytes remain (or remaining is unknown). While aborting, an in-progress NTLM or NEGOTIATE handshake on host or proxy overrides the abort so the same connection can continue. On final abort it closes the stream, zeroes req.size and marks the request bodyless, logging how many bytes were skipped. Always returns CURLE_OK.

**Uncertainties.**

- Interaction with compile-time-disabled NTLM/SPNEGO blocks changes which overrides apply.

<a id="u-b580c0b2eee9"></a>
### `Curl_http_follow`

`CURLcode Curl_http_follow(struct Curl_easy *data, const char *newurl, followtype type)` · [lib/http.c:L1383-L1458][f1]

Handles following a Location (or recording it when not following).

Counts real follows; for FOLLOW_REDIR it enforces maxredirs (switching to FAKE at the limit, which records wouldredirect and can fail with CURLE_TOO_MANY_REDIRECTS), otherwise increments the redirect counter and, when auto-referer is on, sets the referer from the previous URL. For non-retry follows not caused by 401/407 with an absolute target URL, custom ports are disallowed. The URL is parsed via follow_parse_url; FAKE type ends in follow_fake. Real follows install the new URL into state.url, soft-reset the request (which may fail to rewind), log the new request, drop a custom request method when follow mode is FIRSTONLY, apply method conversion via follow_switch_get, and fail with the rewind error if rewinding failed and no GET switch happened. Finally records redirect timing and resets transfer sizes.

group: [http-c-follow-helpers](r6-http-response-processing.md#u-6ff68a8cf2d0); calls: [Curl_req_soft_reset](r10-request-state.md#u-08c8fe509555)

**Uncertainties.**

- Whether Curl_pgrsTime failure is possible is not visible.

<a id="u-b83d2fd51d2b"></a>
### `http-c-header-parsers-small`

`static CURLcode http_header_a(struct Curl_easy *data, const char *hd, size_t hdlen)` · [lib/http.c:L3251-L3278][f1]

Response header handlers for A-, R- and W-leading fields.

http_header_a parses Alt-Svc only when alt-svc storage exists and the transfer is secure (or a debug env override), mapping the request's ALPN (h3/h2/h1) and delegating to Curl_altsvc_parse; otherwise it does nothing. http_header_r parses Retry-After, trying an HTTP-date first (converted to seconds into the future only if not past) and otherwise a decimal number, clamping to at most 21600 seconds and storing it in info.retry_after; zero means unknown/now. http_header_w handles WWW-Authenticate on 401 responses: it copies the header value and feeds it to Curl_http_input_auth as a host challenge, propagating OOM or auth processing errors.

calls: [Curl_http_input_auth](r6-http-response-processing.md#u-06479200bfce)

<a id="u-127d01a590b8"></a>
### `http-c-status-prefix`

`static bool checkprefixmax(const char *prefix, const char *buffer, size_t len)` · [lib/http.c:L3173-L3177][f1]

Recognizes the first response line of a protocol.

checkprefixmax compares at most min(prefix length, buffer length) bytes case-insensitively. checkhttpprefix matches HTTP200ALIASES entries and then a literal 'HTTP/' prefix; a match on at least 5 bytes yields STATUS_DONE, otherwise STATUS_UNKNOWN; no match is STATUS_BAD. checkrtspprefix does the same for 'RTSP/'. checkprotoprefix dispatches to the RTSP variant for RTSP connections, else to the HTTP variant.

<a id="u-1ce99fa7de5d"></a>
### `http-c-write-resp`

`CURLcode Curl_http_write_resp_hd(struct Curl_easy *data, const char *hd, size_t hdlen…` · [lib/http.c:L4662-L4677][f1]

Response delivery entry points.

Curl_http_write_resp_hd feeds one NUL-terminated header line through http_rw_hd and, when is_eos is set, follows with a zero-length body EOS write. Curl_http_write_resp_hds parses a buffer as headers: with the header phase already finished it consumes nothing; otherwise it runs http_parse_headers and, upon finishing, writes any residual buffered bytes as body data (only possible when HTTP/0.9-style responses are allowed) and frees the header buffer. Curl_http_write_resp layers body handling: after header parsing it advances past consumed bytes and, once headers are done and body or EOS remains, writes them with CLIENTWRITE_BODY (plus EOS); if the request already finished it stops early. Errors propagate from each stage.

calls: [http_parse_headers](r6-http-response-processing.md#u-252e5c7db34e), [Curl_client_write](r4-client-writer-stack.md#u-5e34efff1274)

<a id="u-58e2b645bfef"></a>
### `http-c-input-auth-handlers`

`static bool authcmp(const char *auth, const char *line)` · [lib/http.c:L926-L931][f1]

Per-scheme handlers for received WWW-/Proxy-Authenticate challenges.

authcmp matches a scheme token at the line start, case-insensitive, requiring a non-alphanumeric character after the token. auth_spnego registers Negotiate as available when offered or compile-time supported; when Negotiate was picked it consumes the token via Curl_input_negotiate, on success clones the URL into req.newurl, clears authproblem and advances the per-connection negotiate state to CURL_NEGO_AUTH_RECV, on failure sets authproblem. auth_ntlm is analogous (OOM is propagated; other NTLM errors only set authproblem). auth_digest registers Digest availability and stores challenge data even before Digest is activated; OOM propagates, other failures set authproblem; a duplicate Digest header is ignored with a log. auth_basic and auth_bearer always register availability, but if that scheme was already picked a 40x means the credentials were rejected: they clear authp->avail and set authproblem.

**Uncertainties.**

- Negotiate/NTLM state enums live in other headers.

<a id="u-6ff68a8cf2d0"></a>
### `http-c-follow-helpers`

`static void http_switch_to_get(struct Curl_easy *data, int code)` · [lib/http.c:L1158-L1173][f1]

Helpers behind redirect handling.

http_switch_to_get downgrades the request to GET: if a custom request method exists (or method is not GET) and follow mode is OBEYCODE it logs the switch for the given code and sets http_ignorecustom; otherwise a custom method is kept when follow mode is not FIRSTONLY. It always sets HTTPREQ_GET and disables reader rewind. set_auto_referer builds data->state.referer from the current URL stripped of fragment, user and password (OOM on any failure). follow_parse_url sets the new URL into state.uh with flags depending on type (FAKE allows non-support schemes, REDIR urlencodes, both allow spaces, PATH_AS_IS honored); on parse failure it fails for non-FAKE types but for FAKE duplicates the string as-is; on success it compares origin against the previous URL and clears Digest state when the origin differs. follow_switch_get decides method conversion by code: 301 and 302 convert POST-family to GET unless post301/post302 is set; 303 converts to GET unless the request is POST-family and post303 is set; other codes do not convert.

calls: [http-c-follow-helpers](r6-http-response-processing.md#u-6ff68a8cf2d0)

**Uncertainties.**

- The HTTPREQ_IS_POST macro covers POST, POST_FORM and POST_MIME only.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http.c
