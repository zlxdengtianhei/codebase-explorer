# Async Resolve Base

**Capability.** Backend-neutral asynchronous resolution state: perform/timeout/pollset integration with the multi engine, remaining-time tracking, failure result construction, and shutdown/destroy lifecycles that release backend (including DoH) resources.

Use this subtree for how a resolve operation is driven, timed, polled, and torn down independent of the specific DNS backend. Cleanup paths delegate into backend-specific releases.

**Depends on.**

- [DNS-over-HTTPS Resolver](r3-doh-resolver.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [DNS-over-HTTPS Resolver](r3-doh-resolver.md) · model-inferred · 0 edge(s)

Parent: [Asynchronous Name Resolution](r3-dns-resolution.md)

## Units (7)

<a id="u-e48157895cba"></a>
### `Curl_async_timeleft_ms`

`timediff_t Curl_async_timeleft_ms(struct Curl_easy *data, struct Curl_resolv_async *a…` · [lib/vdns/asyn-base.c:L60-L69][f1]

Returns the remaining time for an asynchronous resolve.

When async->timeout_ms is set it subtracts the elapsed time since async->start from it; otherwise it falls back to the transfer-wide Curl_timeleft_ms.

<a id="u-434eb2018a92"></a>
### `Curl_ares_pollset`

`CURLcode Curl_ares_pollset(struct Curl_easy *data, ares_channel channel, struct easy_…` · [lib/vdns/asyn-base.c:L85-L112][f1]

Translates the ares channel's active sockets into the easy handle's pollset for curl_multi_fdset.

A NULL channel returns CURLE_FAILED_INIT (debug assertion). ares_getsock fills a 16-socket array (the documented ares limit) and returns a bitmap; each socket with readable bits adds CURL_POLL_IN and writable bits CURL_POLL_OUT via Curl_pollset_change. Iteration stops at the first socket with no flags; a Curl_pollset_change error is returned immediately.

<a id="u-5e77e9762c39"></a>
### `Curl_ares_timeout_ms`

`timediff_t Curl_ares_timeout_ms(struct Curl_easy *data, struct Curl_resolv_async *asy…` · [lib/vdns/asyn-base.c:L114-L136][f1]

Returns the effective wait timeout in ms: the minimum of the async resolve's remaining time and c-ares' own nearest operation timeout.

NULL channel returns -1 (asserted). If the remaining async timeout is positive and below INT_MAX it is passed as the cap to ares_timeout; when ares returns a timeout it is converted to ms, otherwise the async timeout itself is returned. A non-positive or oversized async timeout is returned unchanged.

<a id="u-04a1ab0b3368"></a>
### `Curl_ares_perform`

`int Curl_ares_perform(ares_channel channel, timediff_t timeout_ms)` · [lib/vdns/asyn-base.c:L147-L200][f1]

Drives one step of the ares event loop.

NULL channel returns 0. It asks ares for its sockets (ARES_GETSOCK_MAXNUM) and builds a pollfd array with POLLIN/POLLOUT-derived events, stopping at the first socket without events. If any sockets exist it polls with the given timeout; poll failure (< 0) returns -1. With no ready descriptors it calls ares_process_fd with ARES_SOCKET_BAD for both directions — deliberately, per the comment, so ares can time out its operations; with ready descriptors it calls ares_process_fd per descriptor, passing the fd on the side(s) indicated by revents and ARES_SOCKET_BAD on the other. Returns the number of ready descriptors (0 when none).

<a id="u-1af738a94656"></a>
### `Curl_async_shutdown`

`void Curl_async_shutdown(struct Curl_easy *data, struct Curl_resolv_async *async)` · [lib/vdns/asyn-base.c:L210-L226][f1]

Marks a resolve operation as shut down and releases backend resources while keeping the async struct allocated.

For a non-NULL async it logs, sets shutdown to TRUE, calls the ares and/or threaded backend shutdown depending on build flags, and cleans up DoH state unless disabled. NULL async is a no-op.

calls: [Curl_async_ares_shutdown](r4-name-resolution.md#u-dd2d57e23f89); uses: [doh-h-type-declarations](r12-async-dns-interface.md#u-af2bcb432ef9)

<a id="u-99a3acda9990"></a>
### `Curl_async_destroy`

`void Curl_async_destroy(struct Curl_easy *data, struct Curl_resolv_async *async)` · [lib/vdns/asyn-base.c:L228-L253][f1]

Fully releases a resolve operation.

For a non-NULL async it sets shutdown, destroys the ares and/or threaded backend state, cleans DoH state (unless disabled), frees the collected A and AAAA Curl_addrinfo lists when present, destroys HTTPS RR state under USE_HTTPSRR, unlinks the peer structure, and finally frees the async struct itself.

calls: [Curl_async_ares_destroy](r4-name-resolution.md#u-e115336b1ac6)

<a id="u-c163ee90e668"></a>
### `Curl_async_failed`

`CURLcode Curl_async_failed(struct Curl_easy *data, struct Curl_resolv_async *async, c…` · [lib/vdns/asyn-base.c:L255-L274][f1]

Builds the failure result for an unresolved name.

Default is CURLE_COULDNT_RESOLVE_HOST with the word 'host'; when the resolve targeted a proxy (async->for_proxy, unless proxies are disabled) it becomes CURLE_COULDNT_RESOLVE_PROXY with 'proxy'. A failf message naming the hostname and the optional detail in parentheses is emitted only when A or AAAA queries were requested. Returns the mapped code.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vdns/asyn-base.c
