# Happy Eyeballs IP Filter

**Capability.** Runs parallel connect attempts ('ballers') across resolved addresses of both families, declares a winner, and splices the winning sub-filter into the chain; owns the address iterators, attempt bookkeeping, the connect/poll/query/shutdown filter callbacks, and the transport-to-factory table.

Read this to understand racing multiple connection attempts. Start at Curl_cf_ip_happy_insert_after for insertion, cf_ip_happy_connect for the callback flow, and cf_ip_ballers_run for the state machine that starts and reaps attempts.

**Depends on.**

- [Connection Filter Framework](r1-connection-filters.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-happy-eyeballs-filter ` → ` r1-connection-filters `)
- [DNS Resolve Connection Filter](r1-dns-resolve-filter.md) · graph-confirmed · 3 edge(s) · The Happy Eyeballs filter obtains resolved addresses from the DNS resolve filter to start its parallel connect attempts.
- [Trace and Debug Logging](r1-trace-logging.md) · graph-confirmed · 21 edge(s)

Parent: [Connection Filter Framework](r1-connection-filters.md)

## Units (15)

<a id="u-ab6997c6fdd8"></a>
### `cf-ip-happy.c-cf-ai-iter`

`struct cf_ai_iter` · [lib/cf-ip-happy.c:L119-L124][f1]

Cursor over resolved DNS addresses of one address family, used to hand out the next candidate address to a connect attempt.

`cf_ai_iter_init` stores the filter, peer (not linked; lifetime owned by the ballers struct), family and resets the index to 0. `cf_ai_iter_next` returns NULL immediately if the stored filter is NULL; otherwise it asks `Curl_conn_dns_get_ai` for address number `n` of the family and increments `n` only on success, so repeated calls walk the address list in order. `cf_ai_iter_has_more` non-destructively probes whether an address at the current index exists; it also returns FALSE when the filter is NULL. Both probes depend on the DNS cfilter's ability to enumerate by index.

calls: [function::Curl_conn_dns_get_ai][f2]

**Uncertainties.**

- Curl_conn_dns_get_ai's NULL-vs-error distinction is not visible here; has_more treats NULL as 'no more', so a transient lookup failure would be read as exhaustion.

<a id="u-9c5a7683420e"></a>
### `cf-ip-happy.c-cf-ip-attempt`

`struct cf_ip_attempt` · [lib/cf-ip-happy.c:L160-L177][f1]

One parallel connect attempt (a 'baller'): the peers involved, the socket address, and the sub-cfilter currently connecting.

`cf_ip_attempt_free` discards the attempt's filter chain via `Curl_conn_cf_discard_chain` if present, unlinks all three peer references and frees the struct; it tolerates NULL. `cf_ip_attempt_new` zero-allocates the attempt (failing with CURLE_OUT_OF_MEMORY), links origin/peer/tunnel_peer, copies the sockaddr, family, transport values and factory, then invokes the factory to build the sub-filter; on factory success it walks the new chain to adopt the parent filter's conn and sockindex (a factory may create sub-filters). Any failure frees the attempt and clears the out-pointer. `cf_ip_attempt_connect` returns the cached connected flag without work when a result is already recorded or already connected; otherwise it runs `Curl_conn_cf_connect`, marks `connected` on success, marks the attempt `inconclusive` when the result is CURLE_WEIRD_SERVER_REPLY (a restarting server, not a hard failure), and on any failure discards the filter chain immediately. `cf_ip_attempt_restart` discards the old chain, resets result/connected/inconclusive, rebuilds the filter via the factory, re-adopts conn/sockindex on sub-filters, and immediately performs one connect pass.

**Notes.**

- failure: CURLE_WEIRD_SERVER_REPLY is classified inconclusive rather than dead, which changes whether callers retry or report the failure.
- side_effect: After a connect failure the sub-filter chain is always discarded inside cf_ip_attempt_connect, so a later restart must recreate it.

calls: [function::Curl_conn_cf_connect][f3], [function::Curl_conn_cf_discard_chain][f3], [function::Curl_peer_link][f4], [function::Curl_peer_unlink][f4]

<a id="u-f4a0894d82f3"></a>
### `cf-ip-happy.c-cf-ip-ballers-helpers`

`struct cf_ip_ballers` · [lib/cf-ip-happy.c:L268-L288][f1]

Lifecycle and inspection helpers for the happy-eyeballs attempt set.

`cf_ip_ballers_init` zeroes the struct, resolves the factory with `get_cf_create(transport_peer, !!tunnel_peer)` and fails with CURLE_UNSUPPORTED_PROTOCOL (via failf) when none matches; otherwise it links the three peers, stores transports, the per-attempt delay and the concurrency cap, and sets the last-attempt family to AF_INET so the first IPv6 pick alternates correctly. `cf_ip_ballers_clear` frees every running attempt, frees the winner, resets running_tail and unlinks the peers. `cf_ip_ballers_prune` counts attempts that are still running (no result, not connected) and, while above the cap, removes the oldest still-running attempts from the list head (fixing running_tail when removing the last element). `cf_ip_ballers_shutdown` drives `do_shutdown` on each running attempt that has a filter and has not shut down; a shutdown error is treated as done for that attempt and shutdown continues over the rest, with *done staying FALSE only while some attempt still needs calls. `cf_ip_ballers_pollset` asks the first non-failed attempt's `Curl_conn_cf_adjust_pollset` and stops at the first error. `cf_ip_ballers_pending` reports TRUE if any non-failed attempt reports pending data. `cf_ip_ballers_min_reply_ms` queries each attempt for CF_QUERY_CONNECT_REPLY_MS and returns the smallest non-negative value, or -1 if none.

**Notes.**

- failure: cf_ip_ballers_init is the only helper returning a code; its failure means the transport is unsupported in this build.
- condition: prune only discards attempts that have neither failed nor connected, so successful or hard-failed attempts are never reclaimed.

calls: [function::get_cf_create][f1], [function::Curl_conn_cf_adjust_pollset][f3], [function::Curl_peer_link][f4], [function::Curl_peer_unlink][f4]

<a id="u-444ee07cc154"></a>
### `cf-ip-happy.c-transport-providers`

`struct transport_provider` · [lib/cf-ip-happy.c:L63-L67][f1]

Maps (transport, tunnel) combinations to filter factory functions via a compile-time table.

`get_cf_create` scans `transport_providers` and returns the `cf_create` of the first entry whose transport and tunnel flags both match, or NULL when none match. The table contents vary by build: TCP always (plain and tunneled), QUIC and H3-proxy only under USE_HTTP3 / USE_PROXY_HTTP3 with HTTP enabled, UDP unless TFTP is disabled, and Unix sockets (plain and tunneled) under USE_UNIX_SOCKETS. `debug_set_transport_provider`, compiled only for UNITTESTS, overwrites `cf_create` of every entry with the matching transport, allowing tests to substitute factories. Uncertainty: no locking, so concurrent use during test substitution would race.

**Notes.**

- condition: A NULL return from get_cf_create means the transport/tunnel pair is unsupported by this build, which callers turn into CURLE_UNSUPPORTED_PROTOCOL.

uses: [function::Curl_cf_create][f3]; calls: [function::cf_ip_ballers_init][f1]

<a id="u-5688d6215cb9"></a>
### `Curl_cf_ip_happy_insert_after`

`CURLcode Curl_cf_ip_happy_insert_after(struct Curl_cfilter *cf_at, struct Curl_easy *…` · [lib/cf-ip-happy.c:L1019-L1039][f1]

Public entry point that creates the happy-eyeballs filter for the given origin/peer/transport (with optional tunnel) and inserts it immediately after `cf_at` in the connection's filter chain via Curl_conn_cf_insert_after.

A create error propagates and nothing is inserted.

calls: [function::cf_ip_happy_create][f1], [function::Curl_conn_cf_insert_after][f3]

<a id="u-4c54365f85f4"></a>
### `cf_ip_ballers_run`

`static CURLcode cf_ip_ballers_run(struct cf_ip_ballers *bs, struct Curl_cfilter *cf, …` · [lib/cf-ip-happy.c:L396-L616][f1]

Drives the happy-eyeballs state machine: checks running attempts, declares a winner, starts new attempts, and schedules re-entry.

Returns CURLE_OK immediately if a winner exists. Each `evaluate` pass first checks the overall connection timeout and returns CURLE_OPERATION_TIMEDOUT with a failf message when expired. It then connects every running attempt via cf_ip_attempt_connect: a first-time success makes that attempt the winner, detaches it, frees all other running attempts, and returns CURLE_OK; a no-result attempt counts as ongoing; an inconclusive attempt counts separately; a hard failure is removed and its result recorded as `last_dead_result` with `had_dead` set. When no attempt is ongoing it always starts a new one; otherwise it starts another only if more addresses remain and the happy-eyeballs delay since `last_attempt_started` has elapsed. When starting, it alternates families: under IPv6 it takes the next AAAA address when the last attempt was AF_INET or the A list is exhausted, otherwise the next A address. Before creating an attempt it prunes to max_concurrent-1 and converts the address via `Curl_socket_addr_from_ai` (error aborts); on success the attempt is appended to the running list, timestamps/family updated, and evaluation restarts. If no addresses remain but inconclusive attempts exist, it either restarts the first inconclusive attempt once the remaining delay has elapsed (error aborts) or schedules a retry via `Curl_expire_set(EXPIRE_HAPPY_EYEBALLS)`. If nothing remains and DNS was resolved, it returns `last_dead_result` if any hard failure occurred, else CURLE_COULDNT_CONNECT. In the non-error exit path it recomputes the remaining timeout (timeout expired returns CURLE_OPERATION_TIMEDOUT), and when more addresses exist computes the next expire as the minimum of the timeout and the remaining attempt delay, re-evaluating immediately if it is already due, else scheduling a timer.

**Notes.**

- side_effect: Sets transfer timers (EXPIRE_HAPPY_EYEBALLS), updates progress timestamps repeatedly, and calls Curl_reset_fail to drop stale error text before starting new attempts.
- failure: Errors from address conversion or attempt creation propagate immediately and leave the attempt unregistered; errors from restarting an inconclusive attempt also abort.
- condition: dns_resolved only influences the final CURLE_COULDNT_CONNECT case; without it, exhaustion keeps the caller polling.

calls: [cf-ip-happy.c-cf-ip-attempt](r1-happy-eyeballs-filter.md#u-9c5a7683420e), [cf-ip-happy.c-cf-ai-iter](r1-happy-eyeballs-filter.md#u-ab6997c6fdd8), [function::Curl_socket_addr_from_ai][f5], [function::Curl_timeleft_now_ms][f6], [function::Curl_expire_set][f7]

**Uncertainties.**

- The DEBUGASSERT(0) after the inconclusive-restart loop implies a state that should be unreachable; behavior if reached is unproven in release builds.

<a id="u-3cbdb26cb0ce"></a>
### `cf_ip_happy_adjust_pollset`

`static CURLcode cf_ip_happy_adjust_pollset(struct Curl_cfilter *cf, struct Curl_easy …` · [lib/cf-ip-happy.c:L822-L835][f1]

Before connection, adjusts the pollset from the running ballers; when already connected it is a no-op returning CURLE_OK, and the ballers helper's first error propagates.

calls: [cf-ip-happy.c-cf-ip-ballers-helpers](r1-happy-eyeballs-filter.md#u-f4a0894d82f3)

<a id="u-32f54abb9b90"></a>
### `cf_ip_happy_connect`

`static CURLcode cf_ip_happy_connect(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/cf-ip-happy.c:L837-L916][f1]

The filter's connect callback: resolves DNS, runs the baller state machine, and on success splices the winning sub-filter into the chain.

A NULL data aborts with CURLE_FAILED_INIT; an already-connected filter returns done immediately. DNS resolution runs once: CURLE_AGAIN is downgraded to OK (wait again), any other error propagates. In SCFST_INIT it calls cf_ip_happy_init (error propagates) and falls through to SCFST_WAITING, which calls is_connected. When is_connected reports success with done, the winner's filter becomes cf->next, cf is marked connected, SSH-protocol transfers get TIMER_APPCONNECT recorded, verbose logging fetches the remote ip-quadruple, all attempts are freed via cf_ip_happy_ctx_clear, the HAPPY_EYEBALLS timer is cleared, error text is reset, and numconnects is incremented. SCFST_DONE just reports done.

**Notes.**

- side_effect: Mutates the filter chain (cf->next = winner->cf) and transfer state (numconnects, timers, error buffer) exactly once on the winning pass.

calls: [function::is_connected][f1], [function::cf_ip_happy_init][f1], [function::Curl_conn_dns_addr_result][f2], [function::Curl_conn_cf_get_ip_info][f3]

<a id="u-33d69c937283"></a>
### `cf_ip_happy_create`

`static CURLcode cf_ip_happy_create(struct Curl_cfilter **pcf, struct Curl_easy *data,…` · [lib/cf-ip-happy.c:L981-L1017][f1]

Allocates the happy-eyeballs filter.

It zero-allocates the context (CURLE_OUT_OF_MEMORY on failure), initializes the ballers with the configured happy_eyeballs_timeout as per-attempt delay and IP_HE_MAX_CONCURRENT_ATTEMPTS (6) as cap — cf_ip_ballers_init failing propagates — then builds the filter with Curl_cf_create. On any failure it frees the partially created filter and destroys the context.

calls: [cf-ip-happy.c-cf-ip-ballers-helpers](r1-happy-eyeballs-filter.md#u-f4a0894d82f3), [function::Curl_cf_create][f3]

<a id="u-980f5bd863ea"></a>
### `cf_ip_happy_data_pending`

`static bool cf_ip_happy_data_pending(struct Curl_cfilter *cf, const struct Curl_easy …` · [lib/cf-ip-happy.c:L918-L927][f1]

Reports pending data: while connecting it asks the running ballers; once connected it asks the installed next filter.

calls: [cf-ip-happy.c-cf-ip-ballers-helpers](r1-happy-eyeballs-filter.md#u-f4a0894d82f3)

<a id="u-e1002484255e"></a>
### `cf_ip_happy_destroy`

`static void cf_ip_happy_destroy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-ip-happy.c:L952-L962][f1]

Frees the filter's context: clears all baller attempts and peers, then frees the context struct itself; both steps tolerate a missing context.

The folded helpers `cf_ip_happy_ctx_clear` and `cf_ip_happy_ctx_destroy` perform exactly these two steps and are only used here and in the create error path.

<a id="u-a7c635945e74"></a>
### `cf_ip_happy_init`

`static CURLcode cf_ip_happy_init(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-ip-happy.c:L757-L785][f1]

Initializes the address iterators for the filter's first connect pass.

Returns CURLE_OPERATION_TIMEDOUT if the connection timeout is already exhausted. For a Unix transport it initializes the single iterator with AF_UNIX (or returns CURLE_UNSUPPORTED_PROTOCOL when Unix sockets are not compiled in); otherwise it initializes the IPv6 iterator with AF_INET6 when IPv6 is compiled in and the main iterator with AF_INET.

calls: [cf-ip-happy.c-cf-ai-iter](r1-happy-eyeballs-filter.md#u-ab6997c6fdd8)

<a id="u-34225fd609c9"></a>
### `cf_ip_happy_query`

`static CURLcode cf_ip_happy_query(struct Curl_cfilter *cf, struct Curl_easy *data, in…` · [lib/cf-ip-happy.c:L929-L950][f1]

Answers filter queries: before connection, CF_QUERY_CONNECT_REPLY_MS returns the minimum reply latency across running ballers; all other queries, or any query after connection, are forwarded to the next filter, or return CURLE_UNKNOWN_OPTION when there is none.

calls: [cf-ip-happy.c-cf-ip-ballers-helpers](r1-happy-eyeballs-filter.md#u-f4a0894d82f3)

<a id="u-3ed77639b7f5"></a>
### `cf_ip_happy_shutdown`

`static CURLcode cf_ip_happy_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data,…` · [lib/cf-ip-happy.c:L804-L820][f1]

Shuts down all running ballers unless the filter already connected.

If cf->connected it reports done immediately; otherwise it delegates to cf_ip_ballers_shutdown, which reports done=FALSE while any attempt still needs shutdown calls and treats failed shutdowns as done.

calls: [cf-ip-happy.c-cf-ip-ballers-helpers](r1-happy-eyeballs-filter.md#u-f4a0894d82f3)

<a id="u-bacd8ebdbec9"></a>
### `is_connected`

`static CURLcode is_connected(struct Curl_cfilter *cf, struct Curl_easy *data, bool *c…` · [lib/cf-ip-happy.c:L696-L753][f1]

Runs the ballers and, on failure, converts the raw result into a detailed connection-failure report.

It calls cf_ip_ballers_run; success returns CURLE_OK with the connected flag from the run. On failure it fetches the first connected peer; missing origin or peer returns CURLE_FAILED_INIT. It identifies a proxy peer (SOCKS preferred over HTTP) and, when the connected peer differs from both origin and proxy, builds a 'via host:port' or unix-socket suffix. It then failf's a message with origin, via-suffix, proxy, elapsed ms and the result's strerror text. Under SOCKETIMEDOUT, an os_errno equal to that value rewrites the result to CURLE_OPERATION_TIMEDOUT. The original (or rewritten) result propagates.

**Notes.**

- side_effect: Writes the detailed failure message into the transfer error buffer via failf.

calls: [function::cf_ip_ballers_run][f1], [function::Curl_conn_get_first_peer][f6], [function::Curl_peer_equal][f4]

**Uncertainties.**

- Whether the proxy peer selection must match the ballers' tunnel_peer is not verified from this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cf-ip-happy.c
[f2]: ../../../../../../eval/curl-2c04412/lib/vdns/cf-dns.c
[f3]: ../../../../../../eval/curl-2c04412/lib/cfilters.c
[f4]: ../../../../../../eval/curl-2c04412/lib/peer.c
[f5]: ../../../../../../eval/curl-2c04412/lib/cf-socket.c
[f6]: ../../../../../../eval/curl-2c04412/lib/connect.c
[f7]: ../../../../../../eval/curl-2c04412/lib/multi.c
