# Async DNS Resolver

**Capability.** Resolves hostnames per transfer: cache consultation, localhost/literal shortcuts, IPv6 probing, async resolve state with unique ids, timeout strategies (alarm/SIGALRM or deadline), and result retrieval/pollset integration.

Use this subtree to follow the lifecycle of a name lookup from Curl_resolv down to hostip_resolv_start and result collection. The HTTPS-record helpers and query labeling are auxiliary views over the async state; the alarm-based timeout path is a distinct fallback strategy.

**Depends on.**

- [Addrinfo Conversion Helpers](r5-addrinfo-core.md) · graph-confirmed · 7 edge(s)

Parent: [Connection Name Resolution](r5-connection-resolution.md)

## Units (31)

<a id="u-b93d8516ec19"></a>
### `hostip.c-https-helpers`

`CURLcode Curl_resolv_https(struct Curl_easy *data, struct Curl_peer *peer, bool for_p…` · [lib/vdns/hostip.c:L520-L529][f1]

Three HTTPS-record helpers over the async resolve state.

Curl_resolv_https starts a resolve restricted to the HTTPS query type over TCP, delegating to Curl_resolv. Curl_resolv_get_https returns the stored httpsrr pointer only when Curl_resolv_knows_https confirms the HTTPS answer is known (or will never come), else NULL; it also returns NULL when the async is gone. Curl_resolv_knows_https returns TRUE when there is no async or HTTPS was not queried; when HTTPS was queried it is TRUE once a response arrived or no HTTPS query is still ongoing.

calls: [Curl_resolv](r5-dns-resolver.md#u-a9c16de36d06)

**Uncertainties.**

- Only compiled under USE_HTTPSRR and USE_CURL_ASYNC

<a id="u-d44bbf3e9e12"></a>
### `Curl_async_get`

`struct Curl_resolv_async *Curl_async_get(struct Curl_easy *data, uint32_t resolv_id)` · [lib/vdns/hostip.c:L1074-L1083][f1]

Walks the per-easy list of in-flight async resolves and returns the one whose id matches, or NULL.

<a id="u-5cc77a1b33a7"></a>
### `Curl_host_is_ipnum`

`bool Curl_host_is_ipnum(const char *hostname)` · [lib/vdns/hostip.c:L320-L333][f1]

Returns TRUE when the hostname parses as a numeric IPv4 address, or additionally IPv6 when built with IPv6 support, using curlx_inet_pton; otherwise FALSE.

calls: [curlx_inet_pton](r8-host-resolution.md#u-373dc2821a53)

<a id="u-6a480a1d4b15"></a>
### `Curl_printable_address`

`void Curl_printable_address(const struct Curl_addrinfo *ai, char *buf, size_t bufsize)` · [lib/vdns/hostip.c:L175-L199][f1]

Writes a printable form of the address in an addrinfo entry into buf.

It clears buf first, then converts via curlx_inet_ntop for AF_INET and (with IPv6 support) AF_INET6; other families leave buf empty. Conversion failure also leaves buf empty.

calls: [curlx_inet_ntop](r4-address-formatting.md#u-4a1e424cecdf)

<a id="u-665b3c849f53"></a>
### `Curl_probeipv6`

`CURLcode Curl_probeipv6(struct Curl_multi *multi)` · [lib/vdns/hostip.c:L289-L303][f1]

Probes IPv6 support by creating a PF_INET6/SOCK_DGRAM socket: sets multi->ipv6_works TRUE and closes the socket on success, FALSE on failure, returning CURLE_OUT_OF_MEMORY only when the socket error is ENOMEM, else CURLE_OK.

**Notes.**

- side_effect: Caches the probe result in multi->ipv6_works, which ipv6works() then reports without re-probing.

<a id="u-a9c16de36d06"></a>
### `Curl_resolv`

`CURLcode Curl_resolv(struct Curl_easy *data, struct Curl_peer *peer, uint8_t dns_quer…` · [lib/vdns/hostip.c:L1024-L1070][f1]

Main entry point for name resolution.

Rejects an already-expired timeout (negative) with CURLE_OPERATION_TIMEDOUT and substitutes CURL_TIMEOUT_RESOLVE_MS for zero. Unix-socket peers bypass DNS via resolv_unix (or fail with the resolve-error helper when Unix sockets are disabled). With alarm-based timeout support and address queries, a nonzero timeout is dropped to zero when the application disabled signals; if a timeout remains and DoH is not wanted, resolv_alarm_timeout performs the resolve under SIGALRM. Non-async builds warn that timeout on name lookup is unsupported. Otherwise it delegates to hostip_resolv with DoH allowed. The returned cache entry holds a reference the caller must release with Curl_dns_entry_unlink.

calls: [hostip_resolv](r5-dns-resolver.md#u-a9a31dabe7d5), [resolv_unix](r5-dns-resolver.md#u-04ef7bae81ba), [resolv_alarm_timeout](r5-dns-resolver.md#u-2eba6a203c92)

**Uncertainties.**

- Curl_doh_wanted is defined outside this file

<a id="u-d9e28729e010"></a>
### `Curl_resolv_announce_start`

`CURLcode Curl_resolv_announce_start(struct Curl_easy *data, void *resolver)` · [lib/vdns/hostip.c:L362-L380][f1]

Notifies the application's resolver_start callback, if set, before a resolve begins.

On a nonzero callback return it logs that the application aborted and returns CURLE_ABORTED_BY_CALLBACK; with no callback set it returns CURLE_OK. Uses the multi API guard around the callback invocation.

**Uncertainties.**

- Exact expansion of CURL_CBAPI_START/END macros is not in this file

<a id="u-0fe3d433a76e"></a>
### `Curl_resolv_blocking`

`CURLcode Curl_resolv_blocking(struct Curl_easy *data, uint8_t dns_queries, const char…` · [lib/vdns/hostip.c:L790-L829][f1]

Blocking name resolution for internal callers (e.g. local binding, FTP PORT).

Creates a peer for the hostname/port, runs hostip_resolv with DoH disallowed, and when the async build returns CURLE_AGAIN it waits via Curl_async_await and then destroys the async state. Returns the resolve result and, on success, sets *pdns.

calls: [Curl_peer_create](r3-peer-identity.md#u-bfcb55ed9008), [hostip_resolv](r5-dns-resolver.md#u-a9a31dabe7d5)

**Uncertainties.**

- Curl_async_await is defined outside this file

<a id="u-de1bc9ebd184"></a>
### `Curl_resolv_destroy`

`void Curl_resolv_destroy(struct Curl_easy *data, uint32_t resolv_id)` · [lib/vdns/hostip.c:L1152-L1164][f1]

Removes the async resolve with the given id from the easy handle's list, unlinking it and destroying it; unknown ids leave the list untouched.

calls: [Curl_async_destroy](r3-async-resolve-base.md#u-99a3acda9990)

<a id="u-cffc06ce0248"></a>
### `Curl_resolv_destroy_all`

`void Curl_resolv_destroy_all(struct Curl_easy *data)` · [lib/vdns/hostip.c:L1174-L1181][f1]

Pops and destroys every async resolve on the easy handle's list until it is empty.

calls: [Curl_async_destroy](r3-async-resolve-base.md#u-99a3acda9990)

<a id="u-a75dddb01469"></a>
### `Curl_resolv_dns_queries`

`uint8_t Curl_resolv_dns_queries(struct Curl_easy *data, uint8_t ip_version)` · [lib/vdns/hostip.c:L125-L139][f1]

Maps an IP-version preference to the set of DNS query types to issue.

CURL_IPRESOLVE_V6 yields only AAAA, CURL_IPRESOLVE_V4 only A, and any other value returns A+AAAA when the cached IPv6 probe says IPv6 works, otherwise only A.

calls: [ipv6works](r5-dns-resolver.md#u-9e03a4288144)

<a id="u-ad210d07b99e"></a>
### `Curl_resolv_elapsed_ms`

`timediff_t Curl_resolv_elapsed_ms(struct Curl_easy *data, uint32_t resolv_id, const s…` · [lib/vdns/hostip.c:L472-L480][f1]

Returns milliseconds elapsed since the async resolve with the given id started; when no such resolve exists it returns CURL_TIMEOUT_RESOLVE_MS.

<a id="u-e625ca39063f"></a>
### `Curl_resolv_get_ai`

`const struct Curl_addrinfo *Curl_resolv_get_ai(struct Curl_easy *data, uint32_t resol…` · [lib/vdns/hostip.c:L498-L516][f1]

Returns a stored addrinfo result from an async resolve by family and index.

Returns NULL when the async is missing or its queries contain no address query; AF_INET reads the A list, AF_INET6 (with IPv6 built) the AAAA list, any other family NULL.

calls: [Curl_addrinfo_get](r5-addrinfo-core.md#u-83610907e2a1)

<a id="u-9ce21b2f01ff"></a>
### `Curl_resolv_has_answers`

`bool Curl_resolv_has_answers(struct Curl_easy *data, uint32_t resolv_id, uint8_t dns_…` · [lib/vdns/hostip.c:L482-L496][f1]

Reports whether all queries relevant to a resolve have responses.

A missing or already-done async counts as fully answered. Only the queries actually undertaken (dns_queries & async->dns_queries) are checked; if any of those lack a response it returns FALSE, otherwise TRUE.

<a id="u-9575da930cae"></a>
### `Curl_resolv_pollset`

`CURLcode Curl_resolv_pollset(struct Curl_easy *data, struct easy_pollset *ps)` · [lib/vdns/hostip.c:L1135-L1150][f1]

Adds the sockets of all in-flight async resolves to the caller's pollset, skipping DoH-based resolves (they contribute nothing) and stopping at the first error from the backend pollset update.

uses: [function::Curl_async_pollset][f2]

**Uncertainties.**

- Curl_async_pollset is not defined in this file

<a id="u-4f3e044357d3"></a>
### `Curl_resolv_query_str`

`const char *Curl_resolv_query_str(uint8_t dns_queries)` · [lib/vdns/hostip.c:L142-L165][f1]

Returns a fixed human-readable label for a combination of A/AAAA/HTTPS query bits, '-' for zero; unknown combinations trigger DEBUGASSERT and return '???'.

**Uncertainties.**

- Only compiled under CURLVERBOSE

<a id="u-ae822fb25d91"></a>
### `Curl_resolv_shutdown_all`

`void Curl_resolv_shutdown_all(struct Curl_easy *data)` · [lib/vdns/hostip.c:L1166-L1172][f1]

Asks every in-flight async resolve on the easy handle to stop, without destroying them.

calls: [Curl_async_shutdown](r3-async-resolve-base.md#u-1af738a94656)

<a id="u-4266b9ff182f"></a>
### `Curl_resolv_take_result`

`CURLcode Curl_resolv_take_result(struct Curl_easy *data, uint32_t resolv_id, struct C…` · [lib/vdns/hostip.c:L1085-L1133][f1]

Retrieves the current outcome of an async resolve by id; missing id yields CURLE_FAILED_INIT.

It first rechecks the DNS cache: a hit shuts down the possibly still-running resolver and returns the cached entry. A cache error marks the async failed. Otherwise it collects the backend result via hostip_resolv_take_result, then caches a new positive entry (unlinking it on cache-add failure), and for resolve-failure codes caches a negative entry only when async->negative_answer is set (transient failures must not poison the cache) and logs a host/port failure when address queries were involved; other errors log the code.

calls: [hostip_resolv_take_result](r5-dns-resolver.md#u-7933df3a9adb), [Curl_dnscache_get](r11-dnscache.md#u-3013a47d6c9c), [Curl_async_shutdown](r3-async-resolve-base.md#u-1af738a94656)

**Uncertainties.**

- Negative-entry semantics of Curl_dnscache_add_negative (e.g. TTL) are outside this file

<a id="u-1ca58d1e6081"></a>
### `alarmfunc`

`CURL_NORETURN static void alarmfunc(int sig)` · [lib/vdns/hostip.c:L837-L841][f1]

SIGALRM handler that siglongjmps back into the resolver timeout frame; it never returns, so the interrupted application code effectively continues inside a signal handler context.

**Notes.**

- failure: This technique is nonportable and is only compiled when the USE_ALARM_TIMEOUT build requirements all hold.

<a id="u-1987ed7f2afe"></a>
### `can_resolve_dns_queries`

`static bool can_resolve_dns_queries(struct Curl_easy *data, uint8_t dns_queries)` · [lib/vdns/hostip.c:L353-L360][f1]

Returns FALSE only when the requested query set is exactly AAAA while the cached IPv6 probe says IPv6 does not work; otherwise TRUE.

calls: [ipv6works](r5-dns-resolver.md#u-9e03a4288144)

<a id="u-86472a7c27c4"></a>
### `get_localhost6`

`static struct Curl_addrinfo *get_localhost6(uint16_t port, const char *name)` · [lib/vdns/hostip.c:L211-L241][f1]

Builds a heap-allocated addrinfo for ::1 with the given port.

Allocates struct plus sockaddr_in6 plus canonname in one block; returns NULL on allocation failure. Sets AF_INET6/SOCK_STREAM/IPPROTO_TCP and copies '::1' into the sockaddr.

**Uncertainties.**

- Only compiled under USE_IPV6; otherwise a macro expanding to NULL

<a id="u-b1d73ab5749b"></a>
### `get_localhost`

`static struct Curl_addrinfo *get_localhost(uint16_t port, const char *name)` · [lib/vdns/hostip.c:L247-L283][f1]

Builds a static 127.0.0.1 addrinfo chain for the given name and port.

Returns NULL if the literal IPv4 parse or allocation fails; otherwise prepends the get_localhost6 result (when IPv6 is built) so the caller sees an IPv6 entry whose ai_next points at the IPv4 entry, or the IPv4 entry alone. Canonname is stored after the sockaddr inside the same allocation.

calls: [get_localhost6](r5-dns-resolver.md#u-86472a7c27c4)

<a id="u-d0a11ccf83b5"></a>
### `hostip_async_new`

`static struct Curl_resolv_async *hostip_async_new(struct Curl_easy *data, uint8_t dns…` · [lib/vdns/hostip.c:L384-L424][f1]

Allocates and initializes a new async resolve state: assigns a unique id from a per-multi counter that wraps from UINT32_MAX back to 1 (0 never used), links the peer, stores query set, transport, proxy flag, timeout, and start timestamp, and flags whether the hostname is a literal IP (and IPv4 specifically).

Returns NULL without allocation if data->multi is missing or on calloc failure.

calls: [Curl_is_ipaddr](r5-addrinfo-core.md#u-a606be4702df), [Curl_peer_link](r3-peer-identity.md#u-cdc53111cd17), [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77)

<a id="u-a9a31dabe7d5"></a>
### `hostip_resolv`

`static CURLcode hostip_resolv(struct Curl_easy *data, uint8_t dns_queries, struct Cur…` · [lib/vdns/hostip.c:L704-L788][f1]

Resolve orchestration above the start function: refuses .onion names per RFC 7686, consults the DNS cache first, and otherwise starts a resolution.

A positive cache hit returns the entry; a negative cache entry is reported via hostip_resolv_failed. On failure (other than CURLE_AGAIN) it unlinks any partial entry and, for resolve-failure codes, caches a negative entry only when the resolver answered the name does not exist (transient failures must not poison the cache) and logs a failure when address queries were involved; other errors are logged with their code. On success from a fresh resolve (cache_dns), the entry is added to the cache and unlinked if that fails. In debug builds an environment variable can force IPv6 resolve failure.

calls: [Curl_dnscache_get](r11-dnscache.md#u-3013a47d6c9c), [Curl_dnscache_add](r11-dnscache.md#u-687a2610ef7d), [hostip_resolv_start](r5-dns-resolver.md#u-c083fac55a5d), [hostip_resolv_failed](r5-dns-resolver.md#u-b33542ac21dc)

**Uncertainties.**

- Whether CURLE_AGAIN results leave a cache footprint is not visible here beyond skipping the failure branch

<a id="u-b33542ac21dc"></a>
### `hostip_resolv_failed`

`static CURLcode hostip_resolv_failed(struct Curl_easy *data, struct Curl_peer *peer, …` · [lib/vdns/hostip.c:L344-L351][f1]

Reports a resolve failure to the caller's error buffer, naming proxy or host, and returns CURLE_COULDNT_RESOLVE_PROXY or CURLE_COULDNT_RESOLVE_HOST accordingly.

<a id="u-c083fac55a5d"></a>
### `hostip_resolv_start`

`static CURLcode hostip_resolv_start(struct Curl_easy *data, uint8_t dns_queries, stru…` · [lib/vdns/hostip.c:L558-L702][f1]

Starts the actual name resolution for a peer after higher layers checked caches.

It zeroes all outputs first. With address queries and unless USE_RESOLVE_ON_IPS, a literal IP hostname is converted directly via Curl_str2addr; 'localhost', 'localhost.', or names ending in '.localhost'/'.localhost.' resolve via get_localhost. Both shortcut paths first announce the start and abort on CURLE_ABORTED_BY_CALLBACK. If DoH is enabled and allowed for a non-IP hostname, it creates an async state and calls Curl_doh. If the requested queries cannot be provided (e.g. AAAA-only without working IPv6) it returns the proxy/host resolve-failure code. With an async resolver it creates the async state and calls Curl_async_getaddrinfo; on CURLE_AGAIN it probes for an already-arrived result via hostip_resolv_take_result. With a synchronous resolver it calls Curl_sync_getaddrinfo and, on failure, marks the answer negative because sync resolvers cannot distinguish transient from authoritative failures. At the out label: a local addr result is wrapped into a dns cache entry (OUT_OF_MEMORY on failure); a CURLE_AGAIN result with async links the async into data->state.async and returns its id; any other error tears down the async (recording async->negative_answer into *pnegative) and frees any addr or pdns.

calls: [Curl_doh](r3-doh-resolver.md#u-0f91edaf7a2a), [Curl_sync_getaddrinfo](r12-sync-ipv4-resolver.md#u-ed1ad49f786c), [hostip_resolv_take_result](r5-dns-resolver.md#u-7933df3a9adb), [get_localhost](r5-dns-resolver.md#u-b1d73ab5749b), [Curl_str2addr](r5-addrinfo-core.md#u-975922309983)

**Uncertainties.**

- Curl_async_getaddrinfo and Curl_doh internals are outside this file

<a id="u-7933df3a9adb"></a>
### `hostip_resolv_take_result`

`static CURLcode hostip_resolv_take_result(struct Curl_easy *data, struct Curl_resolv_…` · [lib/vdns/hostip.c:L426-L470][f1]

Collects the outcome of one in-flight async resolve.

Requires the async struct (else CURLE_FAILED_INIT). Delegates to the DoH result path when DoH is active, otherwise to the generic async backend. CURLE_AGAIN is downgraded to CURLE_OK after a trace log; resolve-failure codes are routed through Curl_async_failed; other errors are logged and returned unchanged; success is logged with a debug assertion that *pdns is set.

calls: [Curl_doh_take_result](r3-doh-resolver.md#u-b615d6c1073c), [Curl_async_failed](r3-async-resolve-base.md#u-c163ee90e668)

**Uncertainties.**

- Curl_async_take_result and Curl_async_failed internals live outside this file

<a id="u-9e03a4288144"></a>
### `ipv6works`

`static bool ipv6works(struct Curl_easy *data)` · [lib/vdns/hostip.c:L308-L313][f1]

Returns the cached IPv6 probe result from data->multi->ipv6_works, or FALSE when data is NULL.

**Uncertainties.**

- Only compiled under USE_IPV6; otherwise a macro expanding to FALSE

<a id="u-2eba6a203c92"></a>
### `resolv_alarm_timeout`

`static CURLcode resolv_alarm_timeout(struct Curl_easy *data, uint8_t dns_queries, str…` · [lib/vdns/hostip.c:L843-L974][f1]

Implements resolve timeouts with alarm(2)/SIGALRM when signals are allowed.

A remaining timeout below one second is refused outright with CURLE_OPERATION_TIMEDOUT because alarm has only whole-second resolution. It takes a global lock, installs alarmfunc for SIGALRM (saving the previous handler via sigaction or signal()), and sets an alarm for timeout/1000 seconds. If the alarm fires, siglongjmp lands in the setjmp block, which reports 'name lookup timed out' and returns CURLE_OPERATION_TIMEDOUT. It then runs hostip_resolv. Cleanup: when no previous alarm existed it cancels alarm(0) and restores the saved handler and the lock. When a previous alarm existed it is restored scaled by elapsed connection age; if that remaining time reached zero or wrapped negative, it sets alarm(1), fails with 'Previous alarm fired off', and returns CURLE_OPERATION_TIMEDOUT.

calls: [hostip_resolv](r5-dns-resolver.md#u-a9a31dabe7d5)

**Uncertainties.**

- Behavior with HAVE_SIGACTION vs HAVE_SIGNAL variants differs only in handler save/restore mechanics, inferred from the ifdef structure

<a id="u-04ef7bae81ba"></a>
### `resolv_unix`

`static CURLcode resolv_unix(struct Curl_easy *data, struct Curl_peer *peer, struct Cu…` · [lib/vdns/hostip.c:L979-L1001][f1]

Resolves a Unix domain socket peer without DNS: converts the hostname (abstract flag honored) into an addrinfo via Curl_unix2addr.

A CURLE_TOO_LARGE result (path too long) is reported as a failure and returned as CURLE_COULDNT_RESOLVE_HOST. On success it wraps the address into a dns cache entry, returning CURLE_OK or CURLE_OUT_OF_MEMORY.

**Uncertainties.**

- Curl_unix2addr and Curl_dnsc_mk_addr internals are outside this file

<a id="u-5e9db572d7c5"></a>
### `tailmatch`

`static bool tailmatch(const char *full, size_t flen, const char *part, size_t plen)` · [lib/vdns/hostip.c:L336-L342][f1]

Returns TRUE when 'part' equals, case-insensitively and over plen bytes, the tail of 'full'; FALSE when part is longer than full.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vdns/hostip.c
[f2]: ../../../../../../eval/curl-2c04412/lib/vdns/asyn-base.c
