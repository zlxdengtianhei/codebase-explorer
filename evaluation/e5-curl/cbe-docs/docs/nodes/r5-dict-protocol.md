# DICT Protocol

**Capability.** Implements RFC 2229 DICT dictionary lookups: request construction from the URL path (MATCH/DEFINE/free-form), RFC-compliant word escaping, and retrying send with writability polling.

Enter at dict_do to see request mode selection; sendf and unescape_word are its transmission and encoding helpers, and the dispatch table registers the protocol handler.

**Depends on.**

- [Polling and Pollsets](r5-poll-waiting.md) · graph-confirmed · 1 edge(s)

Parent: [Protocol and Filter Implementations](r5-protocol-implementations.md)

## Units (4)

<a id="u-ffd161c5d44f"></a>
### `dict_do`

`static CURLcode dict_do(struct Curl_easy *data, bool *done)` · [lib/dict.c:L164-L300][f1]

Builds and sends a DICT protocol request derived from the URL path, selecting MATCH, DEFINE, or free-form command modes, then arms the receive path; always sets done TRUE.

**Notes.**

- condition: Path is URL-decoded first (Curl_urldecode with REJECT_CTRL); decode failure returns that error directly.
- condition: MATCH paths (/MATCH:, /M:, /FIND:) parse word:database:strategy[:nth] by splitting on colons; missing/empty word sends 'default', empty database sends '!', empty strategy sends '.'.
- condition: DEFINE paths (/DEFINE:, /D:, /LOOKUP:) parse word:database and send a DEFINE command; any other path sends everything after the first '/' with colons replaced by spaces; if no '/' exists nothing is sent but eword/path are still freed.
- failure: unescape_word NULL yields CURLE_OUT_OF_MEMORY; sendf failure logs 'Failed sending DICT request' via Curl_failf and propagates the send error; both paths fall through to the shared cleanup that frees eword and path.
- side_effect: Parsing mutates the decoded path in place by NUL-terminating at colons; on success Curl_xfer_setup_recv arms receiving on FIRSTSOCKET.

calls: [Curl_urldecode](r7-string-escape-utils.md#u-0db7582a0fb5), [unescape_word](r5-dict-protocol.md#u-884088510f12), [sendf](r5-dict-protocol.md#u-2c8f4a757cf8), [Curl_failf](r1-trace-logging.md#u-c8338023c157), [lib/curl_trc.c:Curl_infof](r1-trace-logging.md#u-b6145e5eb5c9), [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167), [Curl_xfer_setup_recv](r10-xfer-direction-api.md#u-13855c9f3fa4)

**Uncertainties.**

- The sixth curl_strnequal call site in graph evidence corresponds to the three DEFINE-mode prefix checks; nthdef is parsed but never sent, so its protocol effect (if any) is not visible here.

<a id="u-2c8f4a757cf8"></a>
### `sendf`

`static CURLcode sendf(struct Curl_easy *data, const char *fmt, ...)` · [lib/dict.c:L96-L162][f1]

Formats and sends data to the DICT server on the first socket, retrying partial writes while polling for writability and honoring the transfer timeout.

**Notes.**

- failure: Format allocation failure returns CURLE_OUT_OF_MEMORY before any send.
- condition: Partial write advances the buffer; then Curl_timeleft_ms < 0 yields CURLE_OPERATION_TIMEDOUT, a zero timeout is treated as unlimited (TIMEDIFF_T_MAX), SOCKET_WRITABLE < 0 yields CURLE_SEND_ERROR, and 0 yields CURLE_OPERATION_TIMEDOUT.
- side_effect: Each successful send is logged via Curl_debug as CURLINFO_DATA_OUT; the formatted string is freed before return.

calls: [lib-mprintf-c-dynbuf-alloc-family](r9-mprintf-formatter-families.md#u-ce09737881fa), [Curl_xfer_send](r10-xfer-direction-api.md#u-859255dc1b0d), [Curl_debug](r1-trace-logging.md#u-20b8ae9f02d8), [Curl_timeleft_ms](r6-connection-management.md#u-030f377eec8b), [Curl_socket_check](r5-poll-waiting.md#u-0a038eae5033)

**Uncertainties.**

- SOCKET_WRITABLE's exact mapping to a wait function is macro-resolved outside the supplied source; its <0 and 0 semantics are inferred from the branch handling.

<a id="u-884088510f12"></a>
### `unescape_word`

`static char *unescape_word(const char *input)` · [lib/dict.c:L70-L90][f1]

Escapes a DICT lookup word per RFC 2229 section 2.2 by backslash-escaping characters, returning an allocated string or NULL on failure.

**Notes.**

- condition: Characters <= 32, 127, single quote, double quote, and backslash each get a preceding backslash.
- failure: On the first dynbuf append failure it returns NULL immediately, leaving partial buffer contents unreported to the caller.

calls: [curlx_dyn_init](r3-dynbuf.md#u-dba8ba103985), [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947)

**Uncertainties.**

- The returned buffer lifetime is governed by dynbuf semantics not visible here; no explicit free is shown in this function.

<a id="u-67a1371842f6"></a>
### `dictc-protocol-struct`

`group` · [lib/dict.c:L300-L325][f1]

File-tail group holding the DICT protocol dispatch table registration.

uses: [dict_do](r5-dict-protocol.md#u-ffd161c5d44f)

**Uncertainties.**

- All other vtable slots are ZERO_NULL, so connection setup, done, and pollset behavior are whatever the generic caller does with NULL.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/dict.c
