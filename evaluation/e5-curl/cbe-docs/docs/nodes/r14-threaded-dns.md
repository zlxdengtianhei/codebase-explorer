# Threaded DNS Resolver

**Capability.** Owns the thread-pool-based name resolution backend: queueing A/AAAA work items, worker-side getaddrinfo, result integration with scope/family filtering, HTTPS-RR side queries via c-ares, and multi-handle/global lifecycle wiring.

Follow a resolve from Curl_async_getaddrinfo through async_thrdd_query into the worker item processing, and results back via Curl_async_thrdd_multi_process and Curl_async_take_result. Pollset and event callbacks keep the multi loop informed while resolves are in flight.

**Depends on.**

- [Thread Pool & Threaded Queue](r14-thread-queue-infra.md) · model-inferred · 0 edge(s)

Parent: [curl Codebase](r14-curl-codebase.md)

## Units (28)

<a id="u-b89ab19c68ed"></a>
### `lib/vdns/asyn-thrdd.c:Curl_async_await`

`CURLcode Curl_async_await(struct Curl_easy *data, uint32_t resolv_id, struct Curl_dns…` · [lib/vdns/asyn-thrdd.c:L319-L351][f1]

Blocking wait for a resolve to finish; the comment warns it risks hanging the multi interface.

If no async state exists for resolv_id it returns CURLE_FAILED_INIT. Otherwise it loops while the result is CURLE_AGAIN: while queries are ongoing and not done it drives Curl_async_thrdd_multi_process to drain finished items, and if still not done sleeps via curlx_wait_ms with a back-off chosen from the elapsed time since async->start — 0ms below 3ms, ms/3 up to 50ms, then 50ms up to 250ms, then 200ms. When no queries remain it calls Curl_async_take_result; if that still yields CURLE_AGAIN the loop repeats.

calls: [Curl_async_thrdd_multi_process](r14-threaded-dns.md#u-c06b09af6c5d)

**Uncertainties.**

- There is no timeout exit inside the loop; whether the resolve timeout aborts the wait depends on Curl_async_take_result behavior partly outside this file.

<a id="u-405ec59b27ac"></a>
### `lib/vdns/asyn-thrdd.c:Curl_async_getaddrinfo`

`CURLcode Curl_async_getaddrinfo(struct Curl_easy *data, struct Curl_resolv_async *async)` · [lib/vdns/asyn-thrdd.c:L639-L696][f1]

Starts a threaded name resolution for a transfer.

If queries are already ongoing or the resolve is done it returns CURLE_FAILED_INIT. Under USE_HTTPSRR_ARES, when the HTTPS query bit is set and the peer is not a literal IP address, it first initializes the c-ares channel (async_rr_init, failure goes to out with that error) and uses it as the resolver handed to Curl_resolv_announce_start; a failure there is returned immediately. If a resolver exists, async_rr_start submits the HTTPS query (failure goes to out). Under CURLRES_IPV6 an AAAA query is queued unless the peer is an IPv4 literal and an A query is also wanted; an A query is queued when requested. At out, done is set when no queries are ongoing; errors are traced with the peer name and result code.

calls: [async_thrdd_query](r14-threaded-dns.md#u-7c4be797111f), [async_rr_start](r14-threaded-dns.md#u-759038ce855e)

**Uncertainties.**

- Failure of async_rr_start leaves the initialized channel allocated until a later destroy; re-entry in that state is guarded only by DEBUGASSERT.

<a id="u-8ff399ec86b5"></a>
### `lib/vdns/asyn-thrdd.c:Curl_async_global_cleanup`

`void Curl_async_global_cleanup(void)` · [lib/vdns/asyn-thrdd.c:L95-L100][f1]

Releases the global resolver environment from curl_global_cleanup().

Under the same build condition as the matching init it calls ares_library_cleanup(); with other build configurations the body is empty. Returns nothing and has no failure path.

contract: [lib/vdns/asyn-thrdd.c:Curl_async_global_init](r14-threaded-dns.md#u-24635f614098)

<a id="u-24635f614098"></a>
### `lib/vdns/asyn-thrdd.c:Curl_async_global_init`

`int Curl_async_global_init(void)` · [lib/vdns/asyn-thrdd.c:L80-L88][f1]

Initializes the global resolver environment on behalf of curl_global_init().

Only when built with c-ares and CARES_HAVE_ARES_LIBRARY_INIT does it call ares_library_init(ARES_LIB_INIT_ALL); failure returns CURLE_FAILED_INIT, otherwise CURLE_OK. Without c-ares the body is empty and it always succeeds.

<a id="u-9eaece04b481"></a>
### `lib/vdns/asyn-thrdd.c:Curl_async_pollset`

> **ID corrected by CBE.** CBE changed the unit ID from ` lib/vdns/asyn-thrdd.c::function::Curl_async_pollset::698 ` to the inventory ID ` lib/vdns/asyn-thrdd.c::function::Curl_async_pollset::19190 `. The model wrote this body under the wrong ID; it may be inaccurate.

`CURLcode Curl_async_pollset(struct Curl_easy *data, struct Curl_resolv_async *async, …` · [lib/vdns/asyn-thrdd.c:L698-L743][f1]

Updates the transfer's poll set and expiry timeout while a threaded resolve is in flight.

It starts from Curl_async_timeleft_ms. Under USE_HTTPSRR_ARES, when the c-ares HTTPS channel exists it merges the channel's sockets into the poll set via Curl_ares_pollset (failure aborts with that error) and replaces the timeout with Curl_ares_timeout_ms. When the resolve is not done it sets an EXPIRE_ASYNC_NAME timer: without ENABLE_INTERNAL_WAKEUP it caps the timeout by a poll stutter derived from elapsed time since async->start (1ms below 3ms, elapsed/3 up to 50ms, 50ms up to 250ms, else 200ms); with internal wakeup, if queries are ongoing but the thread queue has not started workers (thread start failed again), it caps the timeout at 100ms so the start is retried soon instead of sleeping the full timeout.

**Uncertainties.**

- Without USE_HTTPSRR_ARES the poll set is explicitly ignored (ps cast to void).

<a id="u-0147c9a46151"></a>
### `lib/vdns/asyn-thrdd.c:Curl_async_take_result`

`CURLcode Curl_async_take_result(struct Curl_easy *data, struct Curl_resolv_async *asy…` · [lib/vdns/asyn-thrdd.c:L857-L943][f1]

Repeatedly called to collect a finished threaded resolve, converting it into a DNS cache entry.

It clears *pdns, then under USE_HTTPSRR_ARES best-effort drives the c-ares channel with Curl_ares_perform (errors ignored), and without ENABLE_INTERNAL_WAKEUP drains the queue via Curl_async_thrdd_multi_process. async_thrdd_check_done integrates results; any non-OK result is returned immediately. It then clears the EXPIRE_ASYNC_NAME timer and computes async->negative_answer: negative only when every requested A/AAAA query responded, all responses were authoritative negatives (ai absent and item->negative set) and at least one A/AAAA query exists. If async->result is set it is returned via out. When address lists exist, Curl_dnsc_mk_addr2 builds the DNS entry (failure is CURLE_OUT_OF_MEMORY); otherwise, under HTTPSRR_ARES with a channel, it traces and builds an HTTPS record entry via Curl_dnsc_mk_https. On success *pdns receives the entry. At out the entry is unlinked on failure, Curl_async_thrdd_shutdown destroys the state, and a NULL result with no *pdns is converted by Curl_async_failed; other errors (except COULDNT_RESOLVE_HOST/PROXY) are traced.

calls: [async_thrdd_check_done](r14-threaded-dns.md#u-144716257474), [Curl_async_thrdd_shutdown](r14-threaded-dns.md#u-dd79692b2231)

**Uncertainties.**

- The exact semantics of Curl_async_failed and Curl_dnsc_mk_* are outside this file.

<a id="u-250048ada8e2"></a>
### `Curl_async_thrdd_destroy`

`void Curl_async_thrdd_destroy(struct Curl_easy *data, struct Curl_resolv_async *async)` · [lib/vdns/asyn-thrdd.c:L290-L313][f1]

Releases all threaded-resolver state attached to a transfer's async context.

If queries are still ongoing and not done and the multi handle has a resolver thread queue, it builds a match context of (mid, resolv_id) and calls Curl_thrdq_clear with async_thrdd_match_item, removing still-queued work items for this resolve so their results cannot dangle. Under USE_HTTPSRR_ARES it destroys and NULLs the c-ares HTTPS channel if present. Finally it destroys and NULLs both res_A and res_AAAA items, freeing their address lists.

calls: [async_thrdd_match_item](r14-threaded-dns.md#u-252599d070c6)

<a id="u-a473bb0b5bac"></a>
### `Curl_async_thrdd_multi_destroy`

`void Curl_async_thrdd_multi_destroy(struct Curl_multi *multi, bool join)` · [lib/vdns/asyn-thrdd.c:L511-L521][f1]

Tears down the multi handle's resolver thread queue.

If multi->resolv_thrdq is set it destroys the queue via Curl_thrdq_destroy, joining active worker threads or detaching them according to the join flag, then NULLs the pointer. In CURLVERBOSE builds it first traces the destroy call and the queue state. No-op when no queue exists.

<a id="u-7fcc41c520db"></a>
### `Curl_async_thrdd_multi_init`

`CURLcode Curl_async_thrdd_multi_init(struct Curl_multi *multi, uint32_t min_threads, …` · [lib/vdns/asyn-thrdd.c:L482-L508][f1]

Creates the multi handle's DNS resolver thread queue.

It creates multi->resolv_thrdq via Curl_thrdq_create with the name 'DNS', the given min/max threads and idle time, and async_thrdd_item_free, async_thrdd_item_process and async_thrdd_event as free/worker/event callbacks with the multi handle as user data; its result code is returned. In DEBUGBUILD builds, after success, CURL_DBG_RESOLV_MAX_THREADS overrides the maximum thread count by calling Curl_async_thrdd_multi_set_props with the original minimum, the parsed value and the same idle time; the override's result becomes the return value.

uses: [async_thrdd_item_process](r14-threaded-dns.md#u-24fd15323701)

<a id="u-c06b09af6c5d"></a>
### `Curl_async_thrdd_multi_process`

`void Curl_async_thrdd_multi_process(struct Curl_multi *multi)` · [lib/vdns/asyn-thrdd.c:L567-L600][f1]

Drains completed resolve items from the multi handle's thread queue and dispatches them.

It repeatedly receives queued items with Curl_thrdq_recv until the queue is empty. For each item it looks up the transfer by item->mid via Curl_multi_get_easy and then its async state by resolv_id; if found, the item is stored into res_A or res_AAAA (AAAA when its dns_queries include CURL_DNSQ_AAAA under CURLRES_IPV6) — a duplicate destination hits DEBUGASSERT — then queries_ongoing is decremented and the transfer is marked dirty via Curl_multi_mark_dirty. An item that found no owner (or a duplicate) is freed immediately.

**Uncertainties.**

- Behavior when the DEBUGASSERT duplicate case is compiled out is not specified: the duplicate item is freed but queries_ongoing is still decremented.

<a id="u-cb40360a87da"></a>
### `Curl_async_thrdd_multi_set_props`

`CURLcode Curl_async_thrdd_multi_set_props(struct Curl_multi *multi, uint32_t min_thre…` · [lib/vdns/asyn-thrdd.c:L602-L609][f1]

Adjusts the thread queue's min/max thread counts and idle time by forwarding all arguments to Curl_thrdq_set_props on multi->resolv_thrdq and returning its result; it performs no validation of its own.

<a id="u-dd79692b2231"></a>
### `Curl_async_thrdd_shutdown`

`void Curl_async_thrdd_shutdown(struct Curl_easy *data, struct Curl_resolv_async *async)` · [lib/vdns/asyn-thrdd.c:L272-L276][f1]

Shuts down one transfer's threaded-resolver state by delegating entirely to Curl_async_thrdd_destroy; all cleanup behavior comes from that function.

calls: [Curl_async_thrdd_destroy](r14-threaded-dns.md#u-250048ada8e2)

<a id="u-b5b62119e44e"></a>
### `async_rr_init`

`static CURLcode async_rr_init(struct Curl_easy *data, struct Curl_resolv_async *async)` · [lib/vdns/asyn-thrdd.c:L217-L239][f1]

Creates the c-ares channel for HTTPS RR side queries without submitting any query.

ares_init_options failure resets the channel pointer to NULL and returns CURLE_FAILED_INIT. In DEBUGBUILD builds, if CURL_DNS_SERVER is set the channel is reconfigured via ares_set_servers_ports_csv; a non-zero status there also returns CURLE_FAILED_INIT (the channel remains allocated in that path).

**Uncertainties.**

- In the DEBUGBUILD server-set failure path the channel is left non-NULL; later destroy/poll behavior in that state is not provable here.

<a id="u-759038ce855e"></a>
### `async_rr_start`

`static CURLcode async_rr_start(struct Curl_easy *data, struct Curl_resolv_async *async)` · [lib/vdns/asyn-thrdd.c:L242-L269][f1]

Submits the HTTPS RR query on the pre-initialized c-ares channel.

If the peer port is not 443 the query name is '_<port>._https.<hostname>' built with curl_maprintf; allocation failure returns CURLE_OUT_OF_MEMORY with no query sent. Otherwise queries_ongoing is incremented before ares_query_dnsrec requests ARES_REC_TYPE_HTTPS with async_thrdd_rr_done as callback, so the callback can account for the in-flight query. The formatted name is always freed.

calls: [async_thrdd_rr_done](r14-threaded-dns.md#u-18d08eaf368d); contract: [async_rr_init](r14-threaded-dns.md#u-b5b62119e44e)

<a id="u-144716257474"></a>
### `async_thrdd_check_done`

`static CURLcode async_thrdd_check_done(struct Curl_easy *data, struct Curl_resolv_asy…` · [lib/vdns/asyn-thrdd.c:L785-L850][f1]

Integrates arrived A and AAAA results into the async state, deciding when the resolve is complete.

For an unprocessed res_A it logs the item, ORs its dns_queries into async->dns_responses, moves its addrinfo list to async->ai_A (clearing the item's pointer) and marks it processed. For an unprocessed res_AAAA under IPv6 with scope-id support it first validates the result: when only AAAA was queried and the result has link-local IPv6 addresses lacking a scope id (async_thrdd_item_missing_scope), the item is reused — its dns_queries gain CURL_DNSQ_A, its old result is freed, and it is re-queued via Curl_thrdq_send for an AF_UNSPEC resolve, incrementing queries_ongoing and returning CURLE_AGAIN; a re-queue failure frees the item and returns the error. If the AAAA result is accepted, any AF_INET entries are stripped, the item logged, and its list moved to async->ai_AAAA. Finally, with queries still ongoing it returns CURLE_AGAIN; otherwise it sets done and returns CURLE_OK.

calls: [async_thrdd_item_missing_scope](r14-threaded-dns.md#u-140ca1326053), [async_thrdd_item_strip_results](r14-threaded-dns.md#u-0e921d456eaa)

<a id="u-273636c854aa"></a>
### `async_thrdd_event`

`static void async_thrdd_event(const struct curl_thrdq *tqueue, Curl_thrdq_event ev, v…` · [lib/vdns/asyn-thrdd.c:L458-L471][f1]

Thread-queue event callback that wakes the multi handle.

When ENABLE_INTERNAL_WAKEUP is enabled it reacts only to CURL_THRDQ_EV_ITEM_DONE by calling Curl_multi_wakeup_internal(multi), so a sleeping multi loop notices finished resolves; all other events are ignored. Without that build option the symbol is #defined to NULL and the queue gets no callback.

<a id="u-a571c87d9fae"></a>
### `async_thrdd_item_create`

`static struct async_thrdd_item *async_thrdd_item_create( struct Curl_easy *data, uint…` · [lib/vdns/asyn-thrdd.c:L140-L193][f1]

Allocates and fills one threaded-resolver work item.

It allocates zeroed sizeof(*item)+hostlen bytes, returning NULL on failure; the hostname is copied into the inline tail (the terminator is covered by the struct size). mid, resolv_id, dns_queries, port and transport are stored. In CURLVERBOSE builds a description is formatted from data->id, resolv_id, query type, host and port. In DEBUGBUILD builds, CURL_DBG_RESOLV_DELAY sets delay_ms via curlx_str_number (parse failure leaves it 0); CURL_DBG_RESOLV_FAIL_DELAY sets delay_fail_ms plus a random byte from Curl_rand_bytes; CURL_DBG_RESOLV_FAIL_NEGATIVE sets dbg_negative. These debug fields later make item processing stall or produce a synthetic negative answer.

contract: [async_thrdd_item_destroy](r14-threaded-dns.md#u-d8d48c407014)

**Uncertainties.**

- The random byte added to delay_fail_ms comes from one byte of Curl_rand_bytes; the intended range effect is not provable from this file.

<a id="u-d8d48c407014"></a>
### `async_thrdd_item_destroy`

`static void async_thrdd_item_destroy(struct async_thrdd_item *item)` · [lib/vdns/asyn-thrdd.c:L130-L137][f1]

Releases an async_thrdd_item and the address list it owns.

A NULL item is ignored; a non-NULL res is freed via Curl_freeaddrinfo before the item itself is freed. It also serves as the destructor for items discarded by the thread queue.

uses: [async_thrdd_item](r14-threaded-dns.md#u-3e6dba3551dd)

<a id="u-140ca1326053"></a>
### `async_thrdd_item_missing_scope`

`static bool async_thrdd_item_missing_scope(struct Curl_easy *data, struct async_thrdd…` · [lib/vdns/asyn-thrdd.c:L746-L763][f1]

Detects AAAA results that would be unusable for link-local addressing.

If the connection already has a non-zero scope_id it returns FALSE immediately. Otherwise it scans the item's addrinfo list; for any AF_INET6 entry that is a link-local address (IN6_IS_ADDR_LINKLOCAL) with sin6_scope_id == 0 it returns TRUE, else FALSE. This works around the glibc bug that omits scope ids on AF_INET6-only queries.

<a id="u-24fd15323701"></a>
### `async_thrdd_item_process`

`static void async_thrdd_item_process(void *arg)` · [lib/vdns/asyn-thrdd.c:L376-L425][f1]

Worker-side processing of one resolve item using Curl_getaddrinfo_ex().

In DEBUGBUILD builds, delay_ms stalls the worker for the configured time; a configured delay_fail_ms stalls and then forces item->negative to dbg_negative and returns without resolving at all. Otherwise it builds addrinfo hints: family is PF_INET6 for AAAA-only queries, PF_UNSPEC for A+AAAA, PF_INET otherwise (IPv6 branch only under CURLRES_IPV6); socktype/protocol come from the item's transport; on macOS ai_flags adds AI_ADDRCONFIG to avoid IPv4-mapped results. The port is formatted as a numeric service string with AI_NUMERICSERV. On resolution failure sockerr is set to SOCKERRNO, or the raw rc if SOCKERRNO is 0, or RESOLVER_ENOMEM if both are 0, and negative is set from gai_negative(rc). On success the port is patched into the resulting addrinfo list.

calls: [gai_negative](r14-threaded-dns.md#u-1e91377a0798)

<a id="u-0831370c3d60"></a>
### `lib/vdns/asyn-thrdd.c:async_thrdd_item_process`

`static void async_thrdd_item_process(void *arg)` · [lib/vdns/asyn-thrdd.c:L430-L453][f1]

Fallback worker-side processing of one resolve item using Curl_ipv4_resolve_r(), compiled when getaddrinfo is unavailable.

In DEBUGBUILD builds delay_ms stalls; delay_fail_ms stalls, forces negative to dbg_negative and returns without resolving. It calls Curl_ipv4_resolve_r(hostname, port); a NULL result sets sockerr to SOCKERRNO or RESOLVER_ENOMEM if that is 0, and unconditionally sets negative TRUE because this resolver cannot distinguish transient failures from authoritative negatives.

<a id="u-0e921d456eaa"></a>
### `async_thrdd_item_strip_results`

`static void async_thrdd_item_strip_results(struct async_thrdd_item *item, int ai_family)` · [lib/vdns/asyn-thrdd.c:L765-L781][f1]

Removes all addrinfo entries of one address family from an item's result list.

It walks the list keeping a pointer-to-pointer anchor: entries whose ai_family matches are unlinked (their ai_next cut off and freed with Curl_freeaddrinfo), while non-matching entries advance the anchor. Used to drop AF_INET entries from an AAAA result that was actually resolved with AF_UNSPEC.

<a id="u-252599d070c6"></a>
### `async_thrdd_match_item`

`static bool async_thrdd_match_item(void *qitem, void *match_data)` · [lib/vdns/asyn-thrdd.c:L283-L288][f1]

Queue-removal predicate matching a queued async_thrdd_item against a struct async_thrdd_match_ctx holding mid and resolv_id: it returns true only when both the item's mid and resolv_id equal the context values, identifying work items belonging to one specific resolve of one transfer.

<a id="u-7c4be797111f"></a>
### `async_thrdd_query`

`static CURLcode async_thrdd_query(struct Curl_easy *data, struct Curl_resolv_async *a…` · [lib/vdns/asyn-thrdd.c:L611-L637][f1]

Queues one A or AAAA work item for a transfer.

It creates an async_thrdd_item from the async peer's hostname, port, transport and the query bitmap; allocation failure returns CURLE_OUT_OF_MEMORY. On success it traces the description and submits the item via Curl_thrdq_send with the async timeout; a send failure also returns that error. Only when the send succeeded is ownership given to the queue, queries_ongoing incremented, and the local item pointer NULLed so the out path does not free it.

<a id="u-a5c2bc03fecb"></a>
### `async_thrdd_report_item`

`static void async_thrdd_report_item(struct Curl_easy *data, struct async_thrdd_item *…` · [lib/vdns/asyn-thrdd.c:L524-L561][f1]

Verbose-only helper logging the resolved addresses of one item.

It returns immediately when DNS tracing is not verbose. The reported family is AF_INET6 when the item included a AAAA query (or when IPv6 is built), else AF_INET. It appends the printable address of each result entry matching that family into a 1024-byte dynbuf, comma separated; if appending fails it logs 'too many IP, cannot show' instead. Otherwise it logs the host, port, IPv4/IPv6 letter and the joined list or '(none)'. The dynbuf is freed on every path.

<a id="u-18d08eaf368d"></a>
### `async_thrdd_rr_done`

`static void async_thrdd_rr_done(void *user_data, ares_status_t status, size_t timeout…` · [lib/vdns/asyn-thrdd.c:L197-L213][f1]

c-ares completion callback for the HTTPS RR side query.

If the user_data yields no async/thrdd context it returns immediately. Otherwise it marks CURL_DNSQ_HTTPS in dns_responses, decrements queries_ongoing, and sets done when no queries remain. Only when status is ARES_SUCCESS and a DNS record was delivered does it decode the record into async->httpsrr via Curl_httpsrr_from_ares; on failure the previous httpsrr state is left untouched. The timeouts argument is ignored.

calls: [Curl_httpsrr_from_ares](r12-https-rr.md#u-b7398d44289b)

**Uncertainties.**

- A decode failure here is not recorded in async->result in this callback; how it surfaces later depends on code not in this file.

<a id="u-1e91377a0798"></a>
### `gai_negative`

`static bool gai_negative(int rc)` · [lib/vdns/asyn-thrdd.c:L359-L373][f1]

Classifies a getaddrinfo() failure as an authoritative negative answer.

It returns TRUE only for EAI_NONAME and, when defined and distinct from EAI_NONAME, EAI_NODATA; all other codes (transient failures like EAI_AGAIN, local troubles) return FALSE so they never count as negative answers eligible for negative caching.

<a id="u-3e6dba3551dd"></a>
### `async_thrdd_item`

`struct async_thrdd_item` · [lib/vdns/asyn-thrdd.c:L109-L127][f1]

Defines async_thrdd_item, one queued DNS resolve unit processed on a worker thread.

It holds the resulting Curl_addrinfo (res), a routing key pair (mid, resolv_id) used to match the result back to its transfer, port, transport, the A/AAAA query bitmap, and a negative bit meaning an authoritative 'name does not exist' answer. The description string exists only in CURLVERBOSE builds. In DEBUGBUILD builds the extra delay_ms/delay_fail_ms/dbg_negative fields simulate slow or failing resolvers. The trailing hostname[1] is an inline tail: creation allocates sizeof(*item)+hostlen so the whole name fits.

**Uncertainties.**

- Bit values of CURL_DNSQ_* are defined elsewhere.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vdns/asyn-thrdd.c
