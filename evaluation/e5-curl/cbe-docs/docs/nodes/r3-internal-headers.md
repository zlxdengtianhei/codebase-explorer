# Internal Support Headers

**Capability.** Small internal headers declaring shared libcurl contracts: weekday/month tables and capped date parsing, the HTTP headers store API, blocking wakeup socketpair helpers, the threaded queue (USE_THREADS only), the internal CURLU representation with part flags, and the Windows/Watt-32/lwIP socket-API selection preamble.

Consult these when a module needs one of these shared declarations rather than a local redefinition. They are interfaces and layout definitions; behavior lives in the corresponding .c files.

**Depended on by.**

- [Peer Identity & Refcounting](r3-peer-identity.md) · model-inferred · 0 edge(s)

Parent: [Shared Core Utilities](r3-core-utilities.md)

## Units (10)

<a id="u-f4df8a69b72e"></a>
### `parsedate.h module code (L1–L35)`

`module_region` · [lib/parsedate.h:L1-L35][f1]

Header guard, license, and declarations: extern arrays Curl_wkday[7] and Curl_month[12], and the prototype for Curl_getdate_capped with a comment noting it returns TIME_T_MAX on oversized values instead of erroring (the implementation returns the extreme in *tp with a 0 return).

<a id="u-e964b8d2a723"></a>
### `headers-h-header-store-and-api`

`struct Curl_header_store` · [lib/headers.h:L30-L39][f2]

Declares the HTTP headers API.

When HTTP and the headers API are enabled, struct Curl_header_store is a linked-list node holding a header blob: 'name' and 'value' point into the trailing flexible 'buffer', 'nh_amount'/'nh_index' cache curl_easy_nextheader() lookup data, 'request' numbers the request on the handle (0 first), and 'type' holds a CURLH_* tag. Prototyped: Curl_headers_init installs a client writer catching CLIENTWRITE_HEADER writes, Curl_headers_push stores one full header, Curl_headers_cleanup frees all stored headers. When compiled out, the macros make init/push no-ops returning CURLE_OK and cleanup expand to Curl_nop_stmt, so callers need no conditional code.

group: [headers-h-header-store-and-api](r3-internal-headers.md#u-e964b8d2a723)

**Uncertainties.**

- Exact allocation and buffer-copy strategy for the store is in headers.c, not visible here.

<a id="u-3f4b1d01d7e7"></a>
### `socketpair.h module code (L1–L43)`

`module_region` · [lib/socketpair.h:L1-L43][f3]

Header for wakeup socketpair helpers.

When socketpair support is enabled it declares Curl_wakeup_init (returns <0 on failure), Curl_wakeup_destroy, Curl_wakeup_signal (0 or errno), and Curl_wakeup_consume; otherwise Curl_wakeup_destroy becomes a no-op macro.

<a id="u-ecb2f3af010d"></a>
### `thrdqueue.h module code (L1–L35)`

`module_region` · [lib/thrdqueue.h:L1-L35][f4]

Public header for the threaded queue, active when USE_THREADS.

Declares the event enum (CURL_THRDQ_EV_ITEM_DONE) and callback contracts: the event callback may fire from any thread without the queue lock; process and free callbacks likewise run unlocked from any thread. Declares create/destroy/send/recv/clear/set_props/trace/await_done plus check_started, whose documented contract is to return TRUE when no items wait or the pool accepted a start signal and FALSE when a thread start just failed. Defines CURL_THRDQ_TRACE as a guarded verbose call under CURLVERBOSE, else a no-op.

**Uncertainties.**

- The header declares CURL_THRDQ_EV_ITEM_DONE only with a comment; the implementation in thrdqueue.c always emits exactly that event.

<a id="u-8c18d2a2ee47"></a>
### `lib/thrdqueue.h:<enum>`

`enum` · [lib/thrdqueue.h:L35-L37][f4]

Empty bracket captured at the start of the Curl_thrdq_event enum definition; the actual enum content is documented in the header unit above.

<a id="u-880e79f5b7c2"></a>
### `thrdqueue.h module code (L37–L134)`

`module_region` · [lib/thrdqueue.h:L37-L134][f4]

Trailing region of the queue header: the closing USE_THREADS conditional and the include guard.

Contains no declarations or executable behavior beyond the guard macro.

<a id="u-000d6e5f9297"></a>
### `urlapi-int.h module code (L1–L29)`

`module_region` · [lib/urlapi-int.h:L1-L29][f5]

Header preamble and includes for the internal URL API.

<a id="u-957d5a9f5169"></a>
### `Curl_URL`

`struct Curl_URL` · [lib/urlapi-int.h:L30-L45][f5]

Internal CURLU representation holding URL-encoded part strings (scheme, user, password, options, host, zoneid for numeric IPv6, path, query, fragment), the numeric port, and presence flags that distinguish an explicitly empty query/fragment and a missing port, plus guessed_scheme marking URLs whose scheme was inferred.

The header also defines HOST_* classification codes, QUERY_* parse states, and declares absolute-URL detection, authority setting, junk scanning, same-origin testing, and port extraction helpers.

<a id="u-09916505a46b"></a>
### `urlapi-int.h module code (L45–L70)`

`module_region` · [lib/urlapi-int.h:L45-L70][f5]

Host/query classification constants and declarations of internal URL helper functions.

<a id="u-f7cfbd4a776a"></a>
### `setup-win32.h module code (L1–L110)`

`module_region` · [lib/setup-win32.h:L1-L110][f6]

Windows/Watt-32/lwIP build-configuration header that selects the socket API and includes the corresponding system headers before anything is redefined.

USE_WINSOCK is first undefined; then exactly one of three mutually exclusive branches applies: USE_WATT32 includes tcp.h and sys/socket.h, undefines the byte/word macros, enables several HAVE_* feature macros, and redefines SOCKET as int; USE_LWIPSOCK undefines HAVE_GETHOSTNAME, enables gethostbyname_r with the 6-arg variant, disables lwIP's POSIX I/O name overrides, and pins int/size_t types for RECV/SEND arguments; plain _WIN32 defines USE_WINSOCK to 2 and includes winsock2.h and ws2tcpip.h. A second _WIN32-gated block includes windows.h, winerror.h, and tchar.h, but first fails compilation with #error when exactly one of UNICODE and _UNICODE is defined (a mismatch is treated as a build error, not corrected). Cygwin is intentionally excluded from Winsock headers per the comment because __CYGWIN__ implies POSIX sockets. The file ends by defining _WIN32_WINNT_* version constants (Vista/WS08=0x0600, Win7=0x0601, Win8=0x0602, 8.1=0x0603, Win10=0x0A00) only if not already defined, so build systems lacking these symbols still compile. The whole file is wrapped in an include guard, so repeated inclusion has no effect after the first.

**Notes.**

- condition: The Watt-32, lwIP, and _WIN32 branches are if/elif/endif, so at most one socket stack is configured per translation unit.
- failure: #error aborts compilation when UNICODE and _UNICODE disagree; only both-defined or both-undefined builds proceed past that block.
- side_effect: All _WIN32_WINNT_* definitions are guarded with #ifndef, so values supplied by the build system are preserved.

imports: [lib/setup-win32.h][f6]

**Uncertainties.**

- Whether USE_WATT32, USE_LWIPSOCK, or _WIN32 are defined externally (e.g. by curl_setup.h or the build system) is not visible in this file, so which branch activates in a given build cannot be determined from this source alone.
- The effect of SOCKET being redefined to int under Watt-32 on code that assumes Winsock SOCKET handles is not established here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/parsedate.h
[f2]: ../../../../../../eval/curl-2c04412/lib/headers.h
[f3]: ../../../../../../eval/curl-2c04412/lib/socketpair.h
[f4]: ../../../../../../eval/curl-2c04412/lib/thrdqueue.h
[f5]: ../../../../../../eval/curl-2c04412/lib/urlapi-int.h
[f6]: ../../../../../../eval/curl-2c04412/lib/setup-win32.h
