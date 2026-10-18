# Poll/Select and Waiting

**Capability.** Owns socket readiness abstraction: pollfd fallback definitions, easy pollsets, growable curl_pollfds and curl_waitfds collections, Curl_poll/socket-check prototypes, and millisecond sleeping when no descriptor can be waited on.

Use this subtree when code needs to wait on sockets or collect which sockets to poll. The easy_pollset type is what connection filters fill in for multi-socket waiting.

**Depended on by.**

- [HTTP Datagram Capsules](r8-http-datagram-capsules.md) · model-inferred · 0 edge(s)

Parent: [Core Utilities and Portability](r8-core-utilities.md)

## Units (10)

<a id="u-979ce3b20d38"></a>
### `select.h module code (L1–L46)`

`module_region` · [lib/select.h:L1-L46][f1]

Header guard, includes, and conditional definitions of poll constants and struct pollfd for platforms lacking them; POLLRDNORM/POLLWRNORM/POLLRDBAND fall back to POLLIN/POLLOUT/POLLPRI when undefined.

<a id="u-b0de062f62a6"></a>
### `pollfd`

`struct pollfd` · [lib/select.h:L47-L51][f1]

Fallback struct pollfd (fd, events, revents) defined only when no system poll header or POLLIN exists.

<a id="u-27a3625cb50c"></a>
### `select.h module code (L51–L115)`

`module_region` · [lib/select.h:L51-L115][f1]

Declares CURL_CSELECT_IN2 (internal bit, CURL_CSELECT_ERR << 1), the Curl_socket_check prototype with SOCKET_READABLE/SOCKET_WRITABLE convenience macros, Curl_poll, and the VALID_SOCK/FDSET_SOCK/VERIFY_SOCK macros.

On Winsock a valid socket is < INVALID_SOCKET; elsewhere non-negative, and VERIFY_SOCK also enforces FD_SETSIZE, setting SOCKEINVAL and returning -1 on violation.

<a id="u-3e2e8d0a2968"></a>
### `easy_pollset`

`struct easy_pollset` · [lib/select.h:L116-L126][f1]

Per-easy socket interest set: pointers to sockets/actions arrays, used count n, capacity count (with a debug magic), and built-in two-slot default arrays so small sets need no allocation.

Actions are bitmaps of CURL_POLL_IN/CURL_POLL_OUT.

<a id="u-e715f7860c7e"></a>
### `select.h module code (L126–L197)`

`module_region` · [lib/select.h:L126-L197][f1]

Pollset API declarations and convenience macros.

Curl_pollset_change is WARN_UNUSED_RESULT; macros add_in/add_out/add_inout/remove_in/remove_out map onto it, and set_in_only/set_out_only express replace semantics. CURL_EASY_POLLSET_MAGIC guards debug builds.

<a id="u-755f0b197d4b"></a>
### `curl_pollfds`

`struct curl_pollfds` · [lib/select.h:L198-L203][f1]

Grow-able pollfd collection: pfds array, used n, capacity count, and an allocated_pfds flag marking heap ownership.

<a id="u-9de9cd80e977"></a>
### `select.h module code (L203–L218)`

`module_region` · [lib/select.h:L203-L218][f1]

curl_pollfds API prototypes: init with optional static storage, reset, cleanup, add from a pollset, and add a single socket.

<a id="u-c46461c457ad"></a>
### `Curl_waitfds`

`struct Curl_waitfds` · [lib/select.h:L219-L223][f1]

Collection of curl_waitfd entries: wfds array, used n, capacity count; no ownership flag, so it relies on caller-provided storage.

<a id="u-0af39c4557bb"></a>
### `select.h module code (L223–L232)`

`module_region` · [lib/select.h:L223-L232][f1]

Curl_waitfds API prototypes: init with static storage and add from a pollset returning the number of additional slots needed.

<a id="u-a9358bf2b8fe"></a>
### `curlx_wait_ms`

`int curlx_wait_ms(timediff_t timeout_ms)` · [lib/curlx/wait.c:L54-L90][f2]

Delays execution for timeout_ms milliseconds; used where no file descriptor is available to wait on.

timeout_ms == 0 returns 0 immediately; a negative value sets the socket errno to SOCKEINVAL and returns -1. On MSDOS it calls delay(); on Windows it calls Sleep(), clamping timeouts >= ULONG_MAX to ULONG_MAX - 1 because ULONG_MAX means INFINITE; otherwise it uses select(0, NULL, NULL, NULL, tv) built by curlx_mstotv (avoiding poll(), which misbehaves with no sockets on Apple systems). Afterwards, a nonzero r is normalized: r == -1 with errno SOCKEINTR becomes 0 (interrupted wait is not fatal), any other nonzero result becomes -1. Timeout resolution and maximum value are system dependent.

calls: [curlx_mstotv](r9-time-utils.md#u-0359163c83a8)

**Uncertainties.**

- Which backend branch is compiled depends on MSDOS/_WIN32 macros not resolvable here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/select.h
[f2]: ../../../../../../eval/curl-2c04412/lib/curlx/wait.c
