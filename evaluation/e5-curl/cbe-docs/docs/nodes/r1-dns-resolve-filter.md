# DNS Resolve Connection Filter

**Capability.** Owns per-peer DNS resolution as a connection filter: creating, chaining and driving cf_dns filters, starting async resolves, gating sub-filter connect on results (with a Happy Eyeballs wait for AAAA), and the public query/reporting API for address and HTTPS-RR results.

Use this subtree to see how resolution is layered into the filter chain. cf_dns_add_resolve/Curl_conn_dns_add_* manage filters, cf_dns_connect drives them, and Curl_conn_dns_get_ai serves addresses to consumers like the happy-eyeballs filter.

**Depends on.**

- [Trace and Debug Logging](r1-trace-logging.md) · graph-confirmed · 13 edge(s)

**Depended on by.**

- [Happy Eyeballs IP Filter](r1-happy-eyeballs-filter.md) · graph-confirmed · 3 edge(s) · The Happy Eyeballs filter obtains resolved addresses from the DNS resolve filter to start its parallel connect attempts.

Parent: [Connection Filter Framework](r1-connection-filters.md)

## Units (22)

<a id="u-7de883f36618"></a>
### `Curl_conn_dns_add_addr_resolve`

`CURLcode Curl_conn_dns_add_addr_resolve(struct Curl_easy *data, struct connectdata *c…` · [lib/vdns/cf-dns.c:L557-L568][f1]

Public wrapper that adds an address-only (A/AAAA) resolve for the peer, masking off any non-address query bits.

**Notes.**

- contract: DEBUGASSERT rejects input bits outside CURL_DNSQ_ADDR in debug builds; in release builds they are silently masked.

calls: [cf_dns_add_resolve](r1-dns-resolve-filter.md#u-ef387f3c2d0d)

<a id="u-73ecc852150a"></a>
### `Curl_conn_dns_add_https_resolve`

`CURLcode Curl_conn_dns_add_https_resolve(struct Curl_easy *data, struct connectdata *…` · [lib/vdns/cf-dns.c:L638-L645][f1]

Adds an HTTPS-RR resolve for the peer using the connection's wanted transport (USE_HTTPSRR builds only).

calls: [cf_dns_add_resolve](r1-dns-resolve-filter.md#u-ef387f3c2d0d)

<a id="u-7ff1bfb81e29"></a>
### `Curl_conn_dns_addr_result`

`CURLcode Curl_conn_dns_addr_result(struct connectdata *conn, int8_t sockindex, struct…` · [lib/vdns/cf-dns.c:L577-L594][f1]

Reports the resolution status for a peer by scanning the chain for a matching address-query DNS filter.

**Notes.**

- condition: Matching filter with an entry or a stored error returns that error/result; otherwise CURLE_AGAIN; no matching filter at all returns CURLE_FAILED_INIT.

calls: [Curl_peer_same_destination](r3-peer-identity.md#u-c6979fe1ea92)

**Uncertainties.**

- When ctx->dns is set but resolv_result is 0, the function returns CURLE_OK (0) as 'the result' — success is implied by resolv_result==0 rather than by checking dns.

<a id="u-6aeea9e85d59"></a>
### `Curl_conn_dns_get_ai`

`const struct Curl_addrinfo *Curl_conn_dns_get_ai(struct Curl_easy *data, struct Curl_…` · [lib/vdns/cf-dns.c:L600-L635][f1]

Fetches the index-th addrinfo of a family for a peer from the matching DNS filter, distinguishing cached entries from in-flight resolves.

**Notes.**

- condition: Returns NULL if the filter's resolve errored, or if the family was never queried (AF_INET without CURL_DNSQ_A, AF_INET6 without CURL_DNSQ_AAAA) even though the cache entry may hold it.
- condition: With a dns entry uses Curl_addrinfo_get on it; without one, queries the async resolve by resolv_id via Curl_resolv_get_ai; no matching filter yields NULL.

calls: [Curl_addrinfo_get](r5-addrinfo-core.md#u-83610907e2a1), [Curl_resolv_get_ai](r5-dns-resolver.md#u-e625ca39063f)

<a id="u-ca4d89032550"></a>
### `Curl_conn_dns_get_https`

`const struct Curl_https_rrinfo *Curl_conn_dns_get_https(struct Curl_easy *data, int8_…` · [lib/vdns/cf-dns.c:L651-L669][f1]

Returns the HTTPS-RR info for a peer from the matching HTTPS-query DNS filter, or NULL if unresolved or absent.

**Notes.**

- condition: With a dns entry returns dns->hinfo (possibly NULL); otherwise asks the in-flight resolve via Curl_resolv_get_https.

uses: [function::Curl_resolv_get_https][f2]

<a id="u-68ab1f21d060"></a>
### `Curl_conn_dns_resolved_https`

`bool Curl_conn_dns_resolved_https(struct Curl_easy *data, int8_t sockindex, struct Cu…` · [lib/vdns/cf-dns.c:L671-L689][f1]

Reports whether HTTPS-RR resolution for a peer is known complete, defaulting to TRUE when no matching filter exists.

**Notes.**

- condition: Matching filter with a dns entry returns TRUE; otherwise Curl_resolv_knows_https decides; no matching filter returns TRUE (treated as nothing to wait for).

uses: [function::Curl_resolv_knows_https][f2]

<a id="u-9920f74f078c"></a>
### `cf_dns_add`

`static CURLcode cf_dns_add(struct Curl_easy *data, struct connectdata *conn, int8_t s…` · [lib/vdns/cf-dns.c:L458-L482][f1]

Adds a DNS resolve filter on top of a connection's filter chain for the given peer and socket index.

**Notes.**

- condition: Returns CURLE_FAILED_INIT when peer is NULL.
- side_effect: for_proxy is set when the peer is the connection's SOCKS or HTTP proxy peer (unless proxy support is disabled).

calls: [cf_dns_create](r1-dns-resolve-filter.md#u-5b1a3dbe2528), [lib-cfilters-c-chain-management](r8-cfilters-chain-mgmt.md#u-f10f9ecb03f8)

<a id="u-ef387f3c2d0d"></a>
### `cf_dns_add_resolve`

`static CURLcode cf_dns_add_resolve(struct Curl_easy *data, struct connectdata *conn, …` · [lib/vdns/cf-dns.c:L507-L555][f1]

Ensures the connection's chain resolves the requested query bits for the peer, reusing or extending existing DNS filters first-served.

**Notes.**

- condition: HTTPS bit is dropped when the peer hostname is already an IP address.
- condition: Scans the chain for DNS filters: same-destination filters subtract their query bits from the request; if nothing remains, returns OK; if a not-yet-started address filter remains, its query bits are extended in place.
- condition: Remaining queries get a new filter inserted after the last existing DNS filter, or added at the chain top when none exists.

calls: [cf_dns_add](r1-dns-resolve-filter.md#u-9920f74f078c), [cf_dns_insert_after](r1-dns-resolve-filter.md#u-634b0bb57259), [Curl_peer_same_destination](r3-peer-identity.md#u-c6979fe1ea92)

**Uncertainties.**

- The loop reads data->conn->cfilter[sockindex] rather than the passed conn's slot; whether these always match is not provable from this file.

<a id="u-1fe3b8904a71"></a>
### `cf_dns_adjust_pollset`

`static CURLcode cf_dns_adjust_pollset(struct Curl_cfilter *cf, struct Curl_easy *data…` · [lib/vdns/cf-dns.c:L357-L386][f1]

Pollset callback that lazily starts the resolve and refreshes the poll set from the async resolver.

**Notes.**

- condition: Only acts when the filter is not connected (USE_CURL_ASYNC); otherwise returns CURLE_OK unchanged.
- condition: If the resolve was not yet started, starts it; if that yields a result or an entry, marks the multi handle dirty so the connection is retried.
- contract: Starting here is necessary because DNS filters can be added mid-connect and would otherwise wait forever on the wakeup socketpair.

calls: [cf_dns_start](r1-dns-resolve-filter.md#u-9d351cdc3a34), [Curl_resolv_pollset](r5-dns-resolver.md#u-9575da930cae)

<a id="u-a69187a16310"></a>
### `cf_dns_cntrl`

`static CURLcode cf_dns_cntrl(struct Curl_cfilter *cf, struct Curl_easy *data, int eve…` · [lib/vdns/cf-dns.c:L388-L410][f1]

Control-event callback that releases the held DNS entry when the data transfer ends.

**Notes.**

- side_effect: On CF_CTRL_DATA_DONE, unlinks ctx->dns; per the comment this happens only on failed connects since successful connects already unlinked it. All other events are ignored.

calls: [Curl_dns_entry_unlink](r11-dnscache.md#u-aa63516cade8)

<a id="u-69e6f5081ad1"></a>
### `cf_dns_connect`

`static CURLcode cf_dns_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bool …` · [lib/vdns/cf-dns.c:L287-L347][f1]

Drives the DNS filter: start the resolve once, collect results, announce them, then connect sub-filters when ready.

**Notes.**

- condition: Already-connected filters set *done TRUE and return OK.
- condition: First call sets started and stores cf_dns_start's result; if no dns entry and no error yet, attempts Curl_resolv_take_result to pick up an async result.
- failure: A resolv error on an A/AAAA query is a hard failure returned directly; HTTPS-query errors are not returned here.
- side_effect: On first dns presence: announces via cf_dns_report, and for FIRSTSOCKET address queries sets conn->bits.dns_resolved and records TIMER_NAMELOOKUP.
- condition: If not ready to connect (AAAA wait), returns CURLE_OK with *done FALSE; otherwise connects cf->next via Curl_conn_cf_connect, propagating its result or returning while sub_done is FALSE; on full completion marks itself connected and destroys the resolve via Curl_resolv_destroy.

calls: [cf_dns_start](r1-dns-resolve-filter.md#u-9d351cdc3a34), [Curl_resolv_take_result](r5-dns-resolver.md#u-4266b9ff182f), [lib-cfilters-c-dispatch-wrappers](r8-cfilters-io.md#u-4223d3ac73f1), [cf_dns_ready_to_connect](r1-dns-resolve-filter.md#u-6ad2ca668843)

**Uncertainties.**

- The success path relies on cf_dns_ready_to_connect gating; whether ctx->dns is unlinked on success elsewhere (comment suggests so) is not visible in this file.

<a id="u-5b1a3dbe2528"></a>
### `cf_dns_create`

`static CURLcode cf_dns_create(struct Curl_cfilter **pcf, struct Curl_easy *data, stru…` · [lib/vdns/cf-dns.c:L429-L454][f1]

Creates a DNS cfilter instance from a context; on any failure returns an error and *pcf NULL, freeing the context.

calls: [cf_dns_ctx_create](r1-dns-resolve-filter.md#u-4a247b9cfd68), [Curl_cf_create](r8-cfilters-chain-mgmt.md#u-e3a618a4a2af)

<a id="u-4a247b9cfd68"></a>
### `cf_dns_ctx_create`

`static struct cf_dns_ctx *cf_dns_ctx_create(struct Curl_easy *data, struct Curl_peer …` · [lib/vdns/cf-dns.c:L56-L89][f1]

Allocates and initializes the DNS filter context for a peer.

calls: [Curl_peer_link](r3-peer-identity.md#u-cdc53111cd17), [Curl_resolv_query_str](r5-dns-resolver.md#u-4f3e044357d3)

<a id="u-2bb71f13dc8d"></a>
### `cf_dns_ctx_destroy`

`static void cf_dns_ctx_destroy(struct Curl_easy *data, struct cf_dns_ctx *ctx)` · [lib/vdns/cf-dns.c:L91-L99][f1]

Frees a DNS filter context, unlinking the peer reference and any held DNS entry.

**Notes.**

- side_effect: Curl_peer_unlink and Curl_dns_entry_unlink are called before curlx_free; safe to call with NULL ctx.

calls: [Curl_peer_unlink](r3-peer-identity.md#u-63430ed0e6c2), [Curl_dns_entry_unlink](r11-dnscache.md#u-aa63516cade8)

<a id="u-cf4e4306b494"></a>
### `cf_dns_destroy`

`static void cf_dns_destroy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vdns/cf-dns.c:L349-L355][f1]

Filter destroy callback that logs and frees the filter's DNS context.

calls: [cf_dns_ctx_destroy](r1-dns-resolve-filter.md#u-2bb71f13dc8d)

<a id="u-634b0bb57259"></a>
### `cf_dns_insert_after`

`static CURLcode cf_dns_insert_after(struct Curl_cfilter *cf_at, struct Curl_easy *dat…` · [lib/vdns/cf-dns.c:L490-L505][f1]

Creates a DNS resolve filter (never for_proxy) and inserts it directly after a given filter in the chain.

calls: [cf_dns_create](r1-dns-resolve-filter.md#u-5b1a3dbe2528), [lib-cfilters-c-chain-management](r8-cfilters-chain-mgmt.md#u-f10f9ecb03f8)

<a id="u-6ad2ca668843"></a>
### `cf_dns_ready_to_connect`

`static bool cf_dns_ready_to_connect(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vdns/cf-dns.c:L246-L256][f1]

Decides whether the connection may proceed to sub-filters, applying a short Happy Eyeballs wait for missing AAAA answers.

**Notes.**

- condition: TRUE immediately if resolv_result is set or ctx->dns is present.
- condition: Async address queries: TRUE when Curl_resolv_has_answers reports AAAA answered, or when the remaining wait (he_aaaa_await_ms minus elapsed) is <= 0; otherwise schedules an EXPIRE_HAPPY_EYEBALLS timer for the remainder and returns FALSE.
- condition: Without USE_CURL_ASYNC the function DEBUGASSERTs and returns FALSE; non-address query types return TRUE.

calls: [Curl_resolv_has_answers](r5-dns-resolver.md#u-9ce21b2f01ff), [Curl_expire_set](r13-multi-timers-wait.md#u-8d88bc1ba951)

<a id="u-3fe21319d18a"></a>
### `cf_dns_report`

`static void cf_dns_report(struct Curl_cfilter *cf, struct Curl_easy *data, struct Cur…` · [lib/vdns/cf-dns.c:L129-L158][f1]

Verbose-only function that logs the resolution outcome of a DNS filter's entry.

**Notes.**

- condition: Returns early when tracing is not verbose, hostname is empty, or the hostname is a numerical IP.
- condition: Unix-socket peers log 'resolved unix://...' (DEBUGASSERT(0) when unix sockets are not compiled in); otherwise address queries log the host plus IPv6/IPv4 lists, and HTTPS queries log hinfo state via Curl_httpsrr_print, with 'Error printing HTTPS-RR information' on print failure.

calls: [cf_dns_report_addr](r1-dns-resolve-filter.md#u-c36f46669395)

**Uncertainties.**

- Behavior when CURL_DNSQ_IS_ADDR and CURL_DNSQ_HTTPS bits coexist: address branch runs, HTTPS branch is skipped (else-if ordering).

<a id="u-c36f46669395"></a>
### `cf_dns_report_addr`

`static void cf_dns_report_addr(struct Curl_easy *data, struct dynbuf *tmp, const char…` · [lib/vdns/cf-dns.c:L102-L127][f1]

Verbose helper that logs all resolved addresses of one address family as a comma-separated list.

**Notes.**

- failure: If curlx_dyn_addf fails while appending, logs 'too many IP, cannot show' and returns early.

calls: [Curl_printable_address](r5-dns-resolver.md#u-6a480a1d4b15)

<a id="u-9d351cdc3a34"></a>
### `cf_dns_start`

`static CURLcode cf_dns_start(struct Curl_cfilter *cf, struct Curl_easy *data, struct …` · [lib/vdns/cf-dns.c:L184-L214][f1]

Starts the DNS resolve for the filter's peer, mapping query type to the resolver API and normalizing the result codes.

**Notes.**

- condition: Unix-socket peers force CURL_DNSQ_A; a numerical IPv4 hostname adds CURL_DNSQ_A; under USE_IPV6 a non-IPv4 hostname on an IPv6 peer adds CURL_DNSQ_AAAA.
- condition: CURL_DNSQ_IS_ADDR uses Curl_resolv, CURL_DNSQ_HTTPS uses Curl_resolv_https, anything else fails with CURLE_FAILED_INIT after failf.
- failure: CURLE_AGAIN is converted to CURLE_OK (async in progress, resolv_id usable later); CURLE_OPERATION_TIMEDOUT is propagated with a message including elapsed time; other errors are propagated, with a 'Could not resolve' failf when address queries were involved.
- side_effect: Stores the async resolve id in ctx->resolv_id and the entry in *pdns on immediate success.

calls: [Curl_resolv](r5-dns-resolver.md#u-a9c16de36d06)

**Uncertainties.**

- Whether Curl_resolv/Curl_resolv_https can return CURLE_OK with *pdns NULL is asserted via DEBUGASSERT but not proven here.

<a id="u-493176b6f769"></a>
### `cf-dns.c module code (L410–L428)`

`module_region` · [lib/vdns/cf-dns.c:L410-L428][f1]

Defines Curl_cft_dns, the cfilter type table for the DNS filter, wiring the callbacks documented above and Curl_cf_def_* defaults for send/recv/shutdown/query and liveness.

<a id="u-439e0c1b0030"></a>
### `cf_dns_ctx`

`struct cf_dns_ctx` · [lib/vdns/cf-dns.c:L43-L54][f1]

Per-filter state for the DNS connection filter, one instance per cf_dns filter.

**Notes.**

- field: Fields include the dns entry pointer, linked peer, resolv_result, resolv_id, dns_queries bitmask, transport, for_proxy, and BIT flags started/announced plus the Happy Eyeballs AAAA wait timeout.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vdns/cf-dns.c
[f2]: ../../../../../../eval/curl-2c04412/lib/vdns/hostip.c
