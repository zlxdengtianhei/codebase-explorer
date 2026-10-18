# Public API and option contracts

**Capability.** Declarations of the public surface: the multi interface, easy-handle entry points, option setting, the generated easy-option table, and the cookie engine's data contracts.

Use this subtree to learn what the library exposes and how options and cookies are represented. It is mostly declarative; behavior lives in the connection core and protocol implementations.

Parent: [curl codebase](r7-curl-codebase.md)

## Units (10)

<a id="u-dc584fa25c82"></a>
### `multi-h`

`enum` · [include/curl/multi.h:L59-L78][f1]

Declares the libcurl multi (pull-style, many-transfers) API.

Types: CURLM opaque handle; CURLMcode enum (CURLM_CALL_MULTI_PERFORM=-1 meaning 'call perform/socket functions again soon'; codes for bad handles, bad easy handle, out-of-memory, internal error, bad socket, unknown option, already-added handle, recursive API call from a callback, wakeup failure, bad function argument, aborted-by-callback, unrecoverable poll) with the CURLM_CALL_MULTI_SOCKET alias macro; CURLPIPE_* bitmask for CURLMOPT_PIPELINING; CURLMSG enum and CURLMsg struct whose union exposes either message-specific data or the transfer's CURLcode result; curl_waitfd (fd/events/revents) with CURL_WAIT_POLLIN/POLLPRI/POLLOUT bits chosen to mirror poll(2) without requiring poll support; CURL_POLL_* and CURL_CSELECT_* constants, CURL_SOCKET_TIMEOUT, and the curl_socket_callback and curl_multi_timer_callback typedefs for the socket API; CURLMoption enum of CURLMOPT_* options 1..21 (socket/timer/push/notify callbacks and data, pipelining, connection/pipeline/stream limits, CURLMOPT_NETWORK_CHANGED with CURLMNWC_CLEAR_ALL/CLEAR_CONNS/CLEAR_DNS bit semantics, CURLMOPT_RESOLVE_THREADS_MAX, CURLMOPT_QUICK_EXIT which leaves resolver threads unjoined on cleanup); CURLMINFO_* counters for curl_multi_get_offt; CURL_PUSH_OK/DENY/ERROROUT, opaque curl_pushheaders, curl_pushheader_bynum/byname, curl_push_callback; CURLMNOTIFY_* ids and curl_notify_callback. Functions: lifecycle (init, add/remove handle, cleanup — cleanup frees the stack but does not free or touch easy handles); readiness (fdset filling fd_sets plus max_fd; wait and poll with extra fds and timeout; wakeup; waitfds, which with a zero size reports the needed fd count via fd_count); driving (perform writing running-handle count, socket_action, deprecated socket and socket_all; unless CURL_ALLOW_OLD_MULTI_SOCKET is defined, the curl_multi_socket macro redirects to curl_multi_socket_action with event bitmask 0); introspection (info_read returns a filled CURLMsg* or NULL when empty or failed, writes remaining queue count, and returned data does not survive curl_multi_cleanup; get_handles returns a NULL-terminated allocated array, first entry NULL when no handles are added, NULL on failure; strerror; timeout reporting the max wait before perform/socket calls); setopt, assign (socket-to-private-pointer for the socket API), notify_enable/disable, and get_offt for per-transfer statistics. Per the header comments, curl_multi_perform returns errors about the whole multi stack only; individual transfer failures surface through curl_multi_info_read.

uses: [easy-h](r5-easy-handle-api.md#u-1697244ca3a2)

**Uncertainties.**

- Parser reported a syntax error near line 1; mapping of the unnamed 'enum' region ids to the CURLMcode/CURLMSG/CURLMoption/CURLMinfo_offt enums is inferred from line ranges.
- The CURLMoption enum body uses the CURLOPT(...) macro, whose expansion lives in curl.h and is not in this file; concrete option numeric values beyond the written arguments cannot be verified here.

<a id="u-f7defc81f001"></a>
### `easyif.h module code (L1–L40)`

`module_region` · [lib/easyif.h:L1-L40][f2]

Declares library-wide easy-handle entry points from easy.c for internal use.

The region is an include guard wrapping three function declarations: Curl_senddata takes an easy handle, a const buffer, its length, and an out-parameter size, returning CURLcode; Curl_connect_only_attach takes an easy handle and is compiled out when CURL_DISABLE_WEBSOCKETS is defined; curl_easy_perform_ev is exposed via CURL_EXTERN only under DEBUGBUILD. No definitions or executable logic appear here, so all behavior lives in easy.c and is not observable from this source.

**Uncertainties.**

- Return codes, side effects, and buffer semantics of the three declared functions depend on definitions in easy.c, which are not supplied.
- The exact effect of Curl_connect_only_attach beyond its name is not established from the declaration alone.

<a id="u-af3c171fee13"></a>
### `setopt.h module code (L1–L41)`

`module_region` · [lib/setopt.h:L1-L41][f3]

Option-setting API declarations.

Curl_setstropt stores a string option into the handle, Curl_setblobopt copies a blob option, Curl_vsetopt dispatches a va_list option setter; all three are WARN_UNUSED_RESULT, so callers must check the CURLcode. Curl_setopt_SSLVERSION exists only with SSL support; otherwise a macro returns CURLE_NOT_BUILT_IN.

<a id="u-23e79766a9b0"></a>
### `easyoptions-c-table`

`module_region` · [lib/easyoptions.c:L1-L389][f4]

Generated (optiontable.pl), alphabetically ordered const array Curl_easyopts[] enumerating every easy setopt option as { name, CURLoption id, type, flags }.

Entries include canonical options with flags 0 and deprecated aliases flagged CURLOT_FLAG_ALIAS (e.g. ENCODING -> CURLOPT_ACCEPT_ENCODING, INFILE -> CURLOPT_READDATA, WRITEHEADER -> CURLOPT_HEADERDATA), several aliases sharing one id. The table ends with the sentinel { NULL, CURLOPT_LASTENTRY, CURLOT_LONG, 0 }, which terminates lookups and iteration in easygetopt.c. This region also carries the curl_setup.h/easyoptions.h includes.

<a id="u-280c184fa261"></a>
### `easyoptions-h-header`

`module_region` · [lib/easyoptions.h:L1-L35][f5]

Header declaring the generated easy-options table extern const struct curl_easyoption Curl_easyopts[] and, under DEBUGBUILD only, the prototype for int Curl_easyopts_check(void).

Content is guarded by HEADER_CURL_EASYOPTIONS_H; it exposes no behavior itself.

<a id="u-5075f40c6484"></a>
### `Curl_easyopts_check`

`int Curl_easyopts_check(void)` · [lib/easyoptions.c:L390-L393][f4]

Debug-only consistency check that verifies the generated option table matches curl/curl.h: it returns non-zero when (CURLOPT_LASTENTRY % 10000) does not equal the hard-coded expected value 333.

Callers, notably lookup's DEBUGASSERT in easygetopt.c, treat non-zero as a build-time table desynchronization. Defined only under DEBUGBUILD; in release builds neither this function nor its call sites exist.

**Notes.**

- side_effect: None: the check is a pure arithmetic comparison, with no state access.

**Uncertainties.**

- The magic constant 332 + 1 is generated by optiontable.pl; why % 10000 is the correct comparison against CURLOPT_LASTENTRY is not provable from this source alone.

<a id="u-7f62cfccaa62"></a>
### `cookie-h-api-and-limits`

`group` · [lib/cookie.h:L45-L55][f6]

The remainder of cookie.h defines the public contract of the cookie engine plus compile-time size limits.

Behavior-changing macros: when CURL_DISABLE_HTTP or CURL_DISABLE_COOKIES is defined, Curl_cookie_list becomes a macro returning NULL, Curl_cookie_loadfiles becomes CURLE_OK, and Curl_cookie_init returns NULL, while run/cleanup/flush collapse to Curl_nop_stmt, so callers get inert behavior without linking cookie code; otherwise real prototypes are declared. Limits enforce RFC 6265 sizing: MAX_COOKIE_LINE 5000 bounds an incoming header or jar line, MAX_NAME 4096 causes longer cookie names/content to be ignored, MAX_SET_COOKIE_AMOUNT 50 caps Set-Cookie lines per response (comment requires it below 256 because an unsigned char counter is used), MAX_COOKIE_HEADER_LEN 8190 bounds the outgoing Cookie header, and MAX_COOKIE_SEND_AMOUNT 150 caps cookies sent per request. Flags passed to Curl_cookie_add alter parsing: COOKIE_HTTPHEADER selects HTTP-header-style input (making domain/path arguments relevant, per the comment), COOKIE_NOEXPIRE skips remove_expired(), COOKIE_SECURE marks a secure-origin connection, COOKIE_NOPSL skips the Public Suffix List check, and COOKIE_NOSESSION drops session cookies. Curl_cookie_add and Curl_cookie_getlist are WARN_UNUSED_RESULT, so ignoring their CURLcode is flagged; getlist fills a caller-provided Curl_llist and reports success via a bool 'okay' out-parameter. Curl_secure_context takes the transfer handle and a host name and returns bool. Forward declarations of Curl_easy and connectdata keep the header self-contained.

**Notes.**

- contract: Curl_cookie_add and Curl_cookie_getlist are WARN_UNUSED_RESULT; callers must consume the CURLcode.
- condition: The disable macros produce a fully stubbed API only when CURL_DISABLE_HTTP or CURL_DISABLE_COOKIES is defined; otherwise the function prototypes apply.

**Uncertainties.**

- Return-value and failure semantics of the declared functions are implemented in cookie.c and cannot be verified from this header.
- Whether Curl_secure_context relates to the COOKIE_SECURE flag or the __Secure- prefix is not documented here.

<a id="u-bf9199342f72"></a>
### `cookie.h module code (L1–L29)`

`module_region` · [lib/cookie.h:L1-L29][f6]

Include guard and copyright header; includes curl_setup.h and llist.h, which provide the configuration and Curl_llist types used by the structs below.

uses: [Cookie](r7-public-api-contracts.md#u-40b7b07931de)

<a id="u-40b7b07931de"></a>
### `Cookie`

`struct Cookie` · [lib/cookie.h:L30-L45][f6]

In-memory representation of a single HTTP cookie held by libcurl's cookie engine.

Each Cookie embeds two list nodes: 'node' links it into the main per-domain hashed cookie lists, and 'getnode' links it into a temporary list returned by the getlist operation, so one cookie can belong to two lists simultaneously without copying. Payload fields hold the name, value, canonical path, domain, and an expires timestamp as curl_off_t, plus a creationtime counter used to order cookies within the jar. Boolean flags: tailmatch enables domain-suffix matching, secure records the Secure attribute, livecookie distinguishes cookies received from a server from ones loaded from a stored file, httponly records the HttpOnly directive, and prefix_secure/prefix_host record whether the __Secure- or __Host- cookie prefix was set, which carry stricter handling rules downstream.

**Notes.**

- field: The two embedded Curl_llist_node members let a cookie live in the hashed main list and a per-request getlist at the same time.
- field: prefix_secure and prefix_host correspond to the COOKIE_PREFIX__SECURE and COOKIE_PREFIX__HOST bit masks defined later in this header.

**Uncertainties.**

- The exact matching semantics of tailmatch, prefix flags, and creationtime are implemented outside this header; only field comments document them.

<a id="u-d8b9b8959ea9"></a>
### `CookieInfo`

`struct CookieInfo` · [lib/cookie.h:L56-L64][f6]

State container for a cookie jar.

Cookies are stored in cookielist, an array of COOKIE_HASH_SIZE (63) linked lists, hashed presumably by domain so lookups touch one bucket instead of scanning everything. next_expiration caches the soonest expiry time so the engine can defer expiration sweeps; numcookies counts cookies in the jar and lastct records the last creation-time issued, giving monotonically increasing creation times. The running flag is state used while adding cookies, and newsession marks a fresh session so session cookies are discarded on load rather than persisted.

**Notes.**

- field: Bucket count is fixed at 63 via COOKIE_HASH_SIZE; the hashing function itself is not in this header.

uses: [Cookie](r7-public-api-contracts.md#u-40b7b07931de)

**Uncertainties.**

- The key used to index cookielist buckets (e.g. domain hash) is implemented elsewhere and cannot be confirmed from this header.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/include/curl/multi.h
[f2]: ../../../../../../eval/curl-2c04412/lib/easyif.h
[f3]: ../../../../../../eval/curl-2c04412/lib/setopt.h
[f4]: ../../../../../../eval/curl-2c04412/lib/easyoptions.c
[f5]: ../../../../../../eval/curl-2c04412/lib/easyoptions.h
[f6]: ../../../../../../eval/curl-2c04412/lib/cookie.h
