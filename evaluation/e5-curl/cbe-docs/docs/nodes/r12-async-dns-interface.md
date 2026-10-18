# Async DNS interface and caches

**Capability.** Declares the backend-agnostic asynchronous resolver contract (Curl_resolv_async state and lifecycle), the DNS cache data model, and DoH types kept outside build guards.

Read these headers to understand what any async DNS backend must implement and how cached/DoH results are shaped; no backend implementation lives here.

**Depended on by.**

- [HTTPS RR records](r12-https-rr.md) · model-inferred · 0 edge(s) · HTTPS-RR record parsing consumes the async DNS interface types; the exact linkage is uncertain.

Parent: [Name resolution](r12-name-resolution.md)

## Units (4)

<a id="u-57f8e6c30126"></a>
### `asyn-h-generic-interface`

`struct async_ares_ctx` · [lib/vdns/asyn.h:L107-L113][f1]

Declares the internal asynchronous DNS resolver contract that every async backend must implement, plus backend-specific context structs.

Under CURLRES_ASYNCH it prototypes the lifecycle pair Curl_async_global_init/Curl_async_global_cleanup (a non-OK init return fails curl_global_init per the comment), the core Curl_async_getaddrinfo whose returned hostent must be freed only via Curl_freeaddrinfo, and, when USE_HTTPSRR, Curl_async_knows_https. Compiling with both USE_RESOLV_ARES and USE_RESOLV_THREADED is rejected with #error, so exactly one backend build applies. Under USE_ARES it additionally declares shared helpers Curl_ares_pollset, Curl_ares_timeout_ms, and Curl_ares_perform operating on an ares_channel. Under USE_RESOLV_ARES, struct async_ares_ctx holds the c-ares channel, an ares status code (ARES_SUCCESS, ARES_ENOTFOUND, etc.), a CURLcode result, and a transient_err bit marking an A/AAAA query that failed without the resolver saying the name does not exist; shutdown/destroy functions for this backend are declared. Under USE_RESOLV_THREADED, struct async_thrdd_ctx collects final IPv4/IPv6 results as async_thrdd_item pointers with processed_A/processed_AAAA flags, and, when HTTPSRR plus c-ares are enabled, an embedded struct holding a second ares_channel for RR lookups; it declares per-easy shutdown/destroy functions and multi-level thread-pool management (init, destroy with optional join, process, and set_props taking min/max threads and idle time). These are declarations only; all behavior lives in asyn-ares.c and asyn-thread.c.

imports: [httpsrr-h-https-rr-interface](r8-host-resolution.md#u-0a192429bc3e)

**Uncertainties.**

- Actual semantics of the declared functions depend on implementations in asyn-ares.c/asyn-thread.c, which are not in this source.
- Whether the rr.channel in async_thrdd_ctx is distinct from any async_ares_ctx channel cannot be confirmed since the two backends are mutually exclusive at compile time.

<a id="u-f221369a5b66"></a>
### `asyn-h-resolv-async-struct`

`struct Curl_resolv_async` · [lib/vdns/asyn.h:L214-L249][f1]

Defines the shared per-resolve state struct Curl_resolv_async and the generic lifecycle API around it, with compile-time fallbacks.

The struct links instances via next, references the peer, stores separate Curl_addrinfo results for A (ai_A) and AAAA (ai_AAAA) queries, optionally an HTTPS RR info, backend-specific context (async_ares_ctx or async_thrdd_ctx depending on backend), and DoH probe data unless disabled. Timing/coordination fields include start time, interval_end, timeout_ms, result code, poll_interval, a per-easy unique id, and counters: dns_queries issued, dns_responses received, transport, queries_ongoing. Flags distinguish the literal-IP cases (is_ipaddr, is_ipv4addr), proxy use, completion (done), shutdown state, and negative_answer, which per the comment gates which failures may be cached as negative DNS entries (only 'name does not exist', not transient or local resolver failures). Declared operations: Curl_async_timeleft_ms; Curl_async_shutdown and Curl_async_destroy (shutdown, then free resources and the struct); and Curl_async_failed reporting a failure with a detail string. When USE_CURL_ASYNC is off, Curl_async_shutdown becomes a no-op macro; when CURLRES_ASYNCH is off entirely, earlier macros make global init return CURLE_OK, cleanup a no-op, await/take_result return CURLE_COULDNT_RESOLVE_HOST, pollset a no-op returning CURLE_OK, and Curl_async_knows_https TRUE. The struct and these declarations exist only when USE_CURL_ASYNC is defined (CURLRES_ASYNCH or non-disabled DoH).

**Notes.**

- contract: negative_answer marks only resolver-confirmed nonexistence; such answers alone may be cached as negative entries per the in-struct comment.

uses: [httpsrr-h-https-rr-interface](r8-host-resolution.md#u-0a192429bc3e)

**Uncertainties.**

- The exact values and update order of counters like dns_responses and queries_ongoing are set by backend implementations not present here.
- Behavior of Curl_async_failed (which CURLcode it returns) is declared, not defined, in this header.

<a id="u-1de7a588c0a5"></a>
### `dnscache.h-structures`

`struct Curl_dns_entry` · [lib/vdns/dnscache.h:L45-L60][f2]

Defines the DNS cache data model.

CURL_DNST_* constants name entry types (INIT/ADDR/HTTPS) and MAX_HOSTCACHE_LEN is 255+3 bytes (FQDN + type + port). Curl_dns_entry holds the resolved Curl_addrinfo list (and hinfo under USE_HTTPSRR), the insertion time, a refcount whose zeroing frees the entry, hostlen/port/type, the CURL_DNSQ_* query and response masks, a permanent flag exempting the entry from pruning, and a trailing flexible hostname buffer (may be empty for Unix domain sockets). dnsc_id is a lookup identity (name, port, type); dnsc_key is the fixed MAX_HOSTCACHE_LEN byte array plus length used as the hash key. Curl_dnscache wraps a single hash of entries. The remaining declarations describe the ownership contract: mk functions take ownership of the address/HTTPS-RR lists even on failure and always clear the caller's pointer, entries come with refcount 1 released via Curl_dns_entry_unlink, dnscache_get returns CURLE_OK or CURLE_COULDNT_RESOLVE_HOST for negative entries, and dnscache_add increases the refcount on success.

**Uncertainties.**

- MAX_HOSTCACHE_LEN is referenced by dnscache.c but resolved externally (unresolved symbol in the batch graph); its value here is from the macro definition.

<a id="u-af2bcb432ef9"></a>
### `doh-h-type-declarations`

`enum` · [lib/vdns/doh.h:L33-L52][f3]

Header for DNS-over-HTTPS support, kept outside build guards so its types exist even in non-DoH builds.

DOHcode enumerates DoH parsing/protocol error codes (including DOH_DNS_NXDOMAIN for authoritative non-existence and DOH_DNS_BAD_RCODE for unsuccessful rcodes); DNStype lists the DNS record types used (A, NS, CNAME, AAAA, DNAME, HTTPS). enum doh_slot_num fixes DOH_SLOT_IPV4=0 and DOH_SLOT_IPV6=1 (matching hard-coded constants), optionally adds DOH_SLOT_HTTPS_RR=2 under USE_HTTPSRR, and ends with DOH_SLOT_COUNT. struct doh_request is per-probe easy meta holding the encoded DNS request body (DOH_MAX_DNSREQ_SIZE = 256+16, the RFC 1034/1035 maximum), headers, response dynbuf, request length, resolve id, and query type; struct doh_probes maps one probe message id and result code per slot. struct dohaddr holds an address with a v4/v6 union; struct dohhttps_rr holds a raw-encoded HTTPS RR with length; struct dohentry accumulates up to DOH_MAX_ADDR (24) addresses with a TTL and, under USE_HTTPSRR, up to DOH_MAX_HTTPS (4) HTTPS RRs. Function declarations Curl_doh/Curl_doh_take_result/Curl_doh_cleanup and macro Curl_doh_wanted are replaced by inert stubs (NULL, CURLE_COULDNT_RESOLVE_HOST, FALSE) when CURL_DISABLE_DOH is defined.

**Uncertainties.**

- Struct field semantics beyond names and comments are inferred from layout only; DoH runtime behavior lives in doh.c, not supplied.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vdns/asyn.h
[f2]: ../../../../../../eval/curl-2c04412/lib/vdns/dnscache.h
[f3]: ../../../../../../eval/curl-2c04412/lib/vdns/doh.h
