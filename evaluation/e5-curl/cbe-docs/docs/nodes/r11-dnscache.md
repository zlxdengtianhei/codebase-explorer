# DNS cache

**Capability.** Cache selection/locking and entry lifetime, identity-key construction, entry creation/insertion (address and HTTPS-RR variants), negative caching, stale pruning and CURLOPT_RESOLVE loading.

Use fetch_entry and Curl_dnscache_get for lookup semantics including stale removal and negative-cache misses; use entry-add/entry-create and Curl_dnscache_add for insertion; Curl_loadhostpairs seeds the cache from resolve lists. Key helpers and cache lifecycle are shared by all of these.

**Depends on.**

- [string parsing primitives](r11-strparse-word-scanning.md) · graph-confirmed · 25 edge(s)
- [u8 string set](r11-u8-strset.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [c-ares getaddrinfo shim](r11-fake-resolver.md) · model-inferred · 0 edge(s)

Parent: [DNS resolution](r11-dns-resolution.md)

## Units (13)

<a id="u-14e97f54664f"></a>
### `dnscache.c-cache-lifecycle`

`static void dnscache_entry_free(struct Curl_dns_entry *dns)` · [lib/vdns/dnscache.c:L117-L124][f1]

Manages cache selection, locking and entry lifetime.

dnscache_get picks the cache: the share's dnscache when data->share has CURL_LOCK_DATA_DNS in its specifier, otherwise the multi handle's dnscache, else NULL. dnscache_lock/dnscache_unlock take or release the share's DNS lock only when the given cache is the share's cache; multi-owned caches need no lock here. dnscache_entry_free frees the entry's address list, its HTTPS-RR info under USE_HTTPSRR, and the entry itself; it is the shared teardown for both the hash destructor and manual unlinks. dnscache_entry_dtor is the hash callback: it decrements refcount and frees only at zero, asserting refcount was positive. Curl_dnscache_init initializes the entries hash with the given size and that destructor; Curl_dnscache_destroy destroys the hash, freeing every entry whose refcount drops to zero. Curl_dnscache_clear locks, empties the hash with Curl_hash_clean, and unlocks, doing nothing when no cache exists. The dnscache_prune_data struct is only the parameter block for stale checks (current time, oldest age seen, max age).

**Notes.**

- side_effect: Destroying the hash only frees entries whose refcount reaches zero via the destructor; entries with external references stay alive until unlinked.

calls: [Curl_hash_clean](r4-generic-containers.md#u-96a1e754ffac), [Curl_hash_init](r4-generic-containers.md#u-90f5f7290602), [Curl_hash_destroy](r4-generic-containers.md#u-5e8ba01b3862), [Curl_share_lock_share](r6-share-api.md#u-6146ca450d97), [Curl_share_unlock_share](r6-share-api.md#u-552c57d51f96), [Curl_freeaddrinfo](r5-addrinfo-core.md#u-bcc8e63d9f75)

<a id="u-5145ae2f185b"></a>
### `dnscache.c-key-helpers`

`UNITTEST void dnsc_peer2id(struct dnsc_id *pid, char type, struct Curl_peer *peer)` · [lib/vdns/dnscache.c:L64-L70][f1]

Builds and compares DNS cache identity structures.

dnsc_peer2id fills a dnsc_id from a peer's hostname, port and a caller-chosen type char; dnsc_str2id does the same from a Curl_str name and explicit port. dnsc_id2key serializes a dnsc_id into a byte-array hash key: first byte is the type, next two bytes the big-endian port, then up to MAX_HOSTCACHE_LEN-3 bytes of the hostname lower-cased in place via Curl_strntolower, with key->len set to 3 plus the (possibly truncated) name length. dnsc_id_matches_entry decides whether a lookup id matches a cache entry: a null entry never matches; when neither the requested nor the cached key was truncated (both lengths <= MAX_HOSTCACHE_LEN-3) it matches unconditionally; otherwise it matches only if port and hostname length agree and the names compare equal case-insensitively (exact strcmp tried first, then curl_strequal). Callers must not assume a truncated key identifies a unique entry — that is exactly what dnsc_id_matches_entry guards.

calls: [Curl_strntolower](r3-string-error-utils.md#u-ed93218a3450), [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

**Uncertainties.**

- dnsc_id_matches_entry returns TRUE when both keys are untruncated without comparing hostname or port; correctness relies on the cache key itself encoding type+port+lowercased name, visible only via dnsc_id2key.

<a id="u-9ef584e5a354"></a>
### `dnscache.c-stale-prune`

`static int dnscache_entry_is_stale(void *datap, void *hc)` · [lib/vdns/dnscache.c:L139-L167][f1]

Removes aged entries from the DNS cache.

dnscache_entry_is_stale is the hash iteration callback: permanent entries are never stale; for others the age in milliseconds since dns->added is computed with curlx_ptimediff_ms, doubled for negative entries (CURL_DNST_ADDR with no addr, or CURL_DNST_HTTPS with no hinfo under USE_HTTPSRR), the entry is removed when age >= prune->max_age_ms, and otherwise the callback tracks the oldest kept age in prune->oldest_ms. dnscache_prune runs that callback over the whole hash via Curl_hash_clean_with_criterium and returns the oldest kept age; it assumes the caller already holds the cache lock. Curl_dnscache_prune is the public wrapper: it resolves the cache, returns immediately if there is none or the configured timeout is -1 (forever), then loops — after each pass, if the hash still holds more than MAX_DNS_CACHE_SIZE (29999) entries it halves the effective timeout to oldest_ms/2 and prunes again, stopping when the size is acceptable or the halved timeout reaches 0. Locks are taken and released around the loop.

**Notes.**

- failure: If oldest_ms is 0 while the cache is over capacity, timeout_ms becomes 0 and the loop exits, so an oversized cache with very fresh entries can remain above MAX_DNS_CACHE_SIZE.

calls: [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3), [Curl_hash_clean_with_criterium](r4-generic-containers.md#u-a39cbcc6ceda), [Curl_hash_count](r4-generic-containers.md#u-de5497d63974)

<a id="u-5ec3a43663df"></a>
### `dnscache.c-entry-add`

`static struct Curl_dns_entry *dnsc_add_entry(struct Curl_easy *data, struct Curl_dnsc…` · [lib/vdns/dnscache.c:L591-L598][f1]

Inserts entries into the cache hash and provides the HTTPS-RR variant.

dnsc_add_entry stamps entry->added with the current time via Curl_pgrs_now and inserts via Curl_hash_add, returning the hash's stored pointer (NULL on failure). dnsc_add_addr and dnsc_add_peer_addr both create an entry (permanent flag from the caller or FALSE), attach addresses, insert under the caller-provided or freshly computed key, free the entry when insertion fails, and otherwise bump refcount to mark the returned reference in use; they return NULL when creation or insertion failed. Under USE_HTTPSRR, dnsc_entry_assign_https sets type to CURL_DNST_HTTPS with queries/responses = CURL_DNSQ_HTTPS, replaces any previous hinfo (destroying it), takes ownership of *phinfo and nulls it, and at out always destroys any hinfo the caller still owns. Curl_dnsc_mk_https builds such an entry; dnsc_add_https creates, assigns, and inserts it under the id's key with the same NULL-on-failure, refcount++ on success pattern as the address adders.

calls: [Curl_hash_add](r4-generic-containers.md#u-2b0745caec1d), [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77), [dnscache.c-cache-lifecycle](r11-dnscache.md#u-14e97f54664f)

<a id="u-1bc0e89c58b4"></a>
### `dnscache.c-entry-create`

`static bool dnscache_ai_has_family(struct Curl_addrinfo *ai, int ai_family)` · [lib/vdns/dnscache.c:L459-L466][f1]

Creates address-type cache entries.

dnsc_entry_create builds a zeroed Curl_dns_entry sized with extra room for the hostname; it returns NULL if the name exceeds UINT16_MAX or allocation fails, otherwise sets refcount 1, port, hostlen (copying the name bytes), type-independent permanent flag, and leaves type at CURL_DNST_INIT. dnsc_entry_assign_addr attaches address lists: it asserts refcount 1 and type INIT, sets type to CURL_DNST_ADDR and dns_queries to the address bits, takes ownership of *paddr1 and appends *paddr2 to the list (nulling both pointers). It records which of A/AAAA queries have matching-family addresses in dns_responses via dnscache_ai_has_family (linear scan of the list). If shuffling is enabled and requested, dns_shuffle_addr failure frees the whole entry (no lock held, sole owner) and returns NULL. The out path always frees and nulls any address lists still owned by the caller, so ownership transfers even on failure. Curl_dnsc_mk_addr and Curl_dnsc_mk_addr2 are the public wrappers building a non-permanent entry for a peer with one or two address lists respectively.

**Notes.**

- contract: On failure the input address lists are still freed and *paddr1/*paddr2 cleared, so callers never own the lists after the call regardless of outcome.

calls: [dns_shuffle_addr](r11-dnscache.md#u-e5d5d02e1447), [Curl_freeaddrinfo](r5-addrinfo-core.md#u-bcc8e63d9f75)

<a id="u-8e8a711366bb"></a>
### `dnscache.c-add-negative`

`CURLcode Curl_dnscache_add_negative(struct Curl_easy *data, uint8_t dns_queries, stru…` · [lib/vdns/dnscache.c:L759-L782][f1]

Caches a negative (unresolved) result for a peer so later lookups fail fast.

It resolves the cache and returns CURLE_FAILED_INIT if absent (with a debug assert). After locking: if dns_queries contains any address bit it creates an address-typed entry with a NULL address list via dnsc_add_peer_addr; under USE_HTTPSRR, if the query is exactly CURL_DNSQ_HTTPS it creates an HTTPS-typed entry with NULL hinfo via dnsc_add_https; any other query combination caches nothing and hits a DEBUGASSERT(0), leaving result CURLE_OK. An entry that could not be created yields CURLE_OUT_OF_MEMORY. On success the returned reference is released immediately (refcount--), leaving only the cache's reference alive, and a trace logs the negative resolve before unlocking.

calls: [dnscache.c-entry-add](r11-dnscache.md#u-5ec3a43663df), [dnscache.c-key-helpers](r11-dnscache.md#u-5145ae2f185b), [dnscache.c-cache-lifecycle](r11-dnscache.md#u-14e97f54664f)

<a id="u-e5d5d02e1447"></a>
### `dns_shuffle_addr`

`UNITTEST CURLcode dns_shuffle_addr(struct Curl_easy *data, struct Curl_addrinfo **addr)` · [lib/vdns/dnscache.c:L405-L456][f1]

Randomizes the order of addresses in a Curl_addrinfo list by re-linking it; compiles out when CURL_DISABLE_SHUFFLE_DNS is defined.

It counts nodes with num_addresses; with zero or one address it returns CURLE_OK unchanged. Otherwise it builds an array of node pointers, then an array of random unsigned ints sized to the node count; if either allocation fails it returns CURLE_OUT_OF_MEMORY without touching the list. If Curl_rand succeeds it performs a Fisher-Yates shuffle using rnd[i] % (i+1), relinks the nodes in the new order, terminates the last node's ai_next with NULL, and updates *addr to the new head. If Curl_rand fails, the list is left unchanged (nodes array freed, no relink) and CURLE_OK is still returned since result was never set — a caller cannot detect the failed shuffle from the return code.

**Notes.**

- failure: Curl_rand failure leaves the address order untouched but the function still returns CURLE_OK; only malloc failures produce CURLE_OUT_OF_MEMORY.

uses: [function::Curl_rand_bytes::3884][f2], [dnscache.c-entry-create](r11-dnscache.md#u-1bc0e89c58b4)

<a id="u-aa63516cade8"></a>
### `Curl_dns_entry_unlink`

`void Curl_dns_entry_unlink(struct Curl_easy *data, struct Curl_dns_entry **pdns)` · [lib/vdns/dnscache.c:L813-L826][f1]

Releases one reference to a cached DNS entry and always clears *pdns.

If *pdns is non-NULL it resolves the cache for the given data (which may be NULL for a global cache context), locks it, decrements the refcount, and frees the entry via dnscache_entry_free when the count reaches zero, then unlocks. With no cache resolvable, dnscache_get returns NULL and the lock/unlock helpers are no-ops, so the decrement and free still happen unlocked — correct only for contexts that need no shared lock.

calls: [dnscache.c-cache-lifecycle](r11-dnscache.md#u-14e97f54664f)

**Uncertainties.**

- When data yields no cache but the entry lives in a shared cache elsewhere, the free happens without the share lock; whether callers guarantee this cannot occur is not visible here.

<a id="u-687a2610ef7d"></a>
### `Curl_dnscache_add`

`CURLcode Curl_dnscache_add(struct Curl_easy *data, struct Curl_dns_entry *entry)` · [lib/vdns/dnscache.c:L728-L757][f1]

Adds an already-built entry (from Curl_dnsc_mk_addr/mk_https) to the resolved cache.

Without a cache it returns CURLE_FAILED_INIT; a NULL entry or one still at CURL_DNST_INIT returns CURLE_BAD_FUNCTION_ARGUMENT. It rebuilds the id/key from the entry's own hostname, hostlen, type and port, locks the cache, inserts via dnsc_add_entry, and on insertion failure unlocks and returns CURLE_OUT_OF_MEMORY; on success it bumps entry->refcount for the cache's reference, unlocks, and emits a trace with host, port and query types.

calls: [dnscache.c-entry-add](r11-dnscache.md#u-5ec3a43663df), [dnscache.c-key-helpers](r11-dnscache.md#u-5145ae2f185b), [dnscache.c-cache-lifecycle](r11-dnscache.md#u-14e97f54664f); uses: [curl-trc-c-simple-tracers](r1-trace-logging.md#u-added0315fa4)

<a id="u-3013a47d6c9c"></a>
### `Curl_dnscache_get`

`CURLcode Curl_dnscache_get(struct Curl_easy *data, uint8_t dns_queries, struct Curl_p…` · [lib/vdns/dnscache.c:L351-L375][f1]

Public cache lookup that hands out a referenced entry.

It resolves the cache, locks it, and delegates to fetch_entry; on success with an entry it increments the entry's refcount because the reference is passed out; if fetch_entry returned an error it asserts no entry is set and clears dns. It unlocks, emits a DNS trace line reporting hostname, port, query types, result code and whether an entry was found, and stores the outcome in *pentry. Callers must release the returned entry with Curl_dns_entry_unlink or the memory leaks. With no cache configured, dnscache_lock/unlock are no-ops and fetch_entry returns CURLE_OK with NULL.

calls: [fetch_entry](r11-dnscache.md#u-83067019d2e2), [dnscache.c-cache-lifecycle](r11-dnscache.md#u-14e97f54664f)

<a id="u-34dd448da4b1"></a>
### `Curl_loadhostpairs`

`CURLcode Curl_loadhostpairs(struct Curl_easy *data)` · [lib/vdns/dnscache.c:L851-L1040][f1]

Populates the DNS cache from CURLOPT_RESOLVE entries in data->state.resolve, then clears that list.

Without a cache it returns CURLE_FAILED_INIT; otherwise data->state.wildcard_resolve starts FALSE. Each entry is parsed in place: entries starting with '-' remove a mapping — the source is an [IPv6] bracketed host or a plain host up to ':', followed by a port number; only when the port parses (0..0xffff) is the matching cache key deleted under lock (missing entries ignored), otherwise the entry is skipped silently. Entries otherwise add mappings: a leading '+' marks the entry non-permanent; the source host is parsed like above (without port), then host, port and a second ':' are required. A comma-separated address list follows; each address, optionally bracketed, is copied to a 64-byte buffer (overlong addresses are an error) and converted by Curl_str2addr; without IPv6 support addresses containing ':' are skipped with an infof. Parse or conversion failure at any point frees the collected list, fails with failf and returns CURLE_SETOPT_OPTION_SYNTAX. After the address list, the entry is inserted: any existing cache entry for the key is first deleted under lock (stale timing, permanent/non-permanent replacement, and freshness reasons are documented in the comment), dnsc_add_addr inserts with the full CURL_DNSQ_ADDR mask, the returned reference is released, and NULL from insertion returns CURLE_OUT_OF_MEMORY. A source of '*' sets data->state.wildcard_resolve = TRUE. On full success data->state.resolve is set to NULL.

calls: [Curl_str2addr](r5-addrinfo-core.md#u-975922309983), [Curl_freeaddrinfo](r5-addrinfo-core.md#u-bcc8e63d9f75), [Curl_hash_pick](r4-generic-containers.md#u-b27c1a441dda), [Curl_hash_delete](r4-generic-containers.md#u-b8312f0e5e92), [dnscache.c-entry-add](r11-dnscache.md#u-5ec3a43663df), [dnscache.c-key-helpers](r11-dnscache.md#u-5145ae2f185b), [Curl_failf](r1-trace-logging.md#u-c8338023c157), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

**Uncertainties.**

- In the '-' removal branch, a non-numeric port makes the whole entry silently ignored rather than an error; this is the literal code path but no comment confirms intent.
- The in-list 'continue' when a trailing comma is missing after an address (curlx_str_single(',') fails then goto err vs the inner continue around curlx_str_until failure) mixes skip and error paths in ways that are hard to fully verify from the listing.

<a id="u-83067019d2e2"></a>
### `fetch_entry`

`static CURLcode fetch_entry(struct Curl_easy *data, struct Curl_dnscache *dnscache, u…` · [lib/vdns/dnscache.c:L258-L335][f1]

Cache lookup core: finds a live Curl_dns_entry for a peer and query mask, deleting stale or incomplete entries and signalling negative-cache misses.

It derives the entry type (ADDR or HTTPS from the query mask), builds id/key and picks from the hash; a picked entry failing dnsc_id_matches_entry is treated as absent (long-hostname truncation case). If no entry and the query is an address lookup while data->state.wildcard_resolve is set, it retries with a '*' id on the peer's port. When dns_cache_timeout_ms != -1 it re-checks staleness inline; a stale entry is logged as zapped and deleted from the hash (the hash handles deallocation), and the pointer is dropped. Address queries then validate coverage: if the entry's dns_queries does not cover all requested address bits it is a plain miss (NULL, CURLE_OK); else if the entry has no responses for the wanted queries it logs a trace, returns NULL with CURLE_COULDNT_RESOLVE_HOST; else if the entry holds no addresses (negative entry) the same code is returned. With no cache at all it returns CURLE_OK with *pdns NULL.

calls: [dnscache.c-key-helpers](r11-dnscache.md#u-5145ae2f185b), [Curl_hash_pick](r4-generic-containers.md#u-b27c1a441dda), [Curl_hash_delete](r4-generic-containers.md#u-b8312f0e5e92), [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77); uses: [dnscache.c-stale-prune](r11-dnscache.md#u-9ef584e5a354)

**Uncertainties.**

- The '*' wildcard id is built with dnsc_str2id on a stack Curl_str pointing at a literal; whether any later code could modify that name is not visible here.

<a id="u-f5cc0820fafc"></a>
### `cf-dns.h module code (L1–L71)`

`module_region` · [lib/vdns/cf-dns.h:L1-L71][f3]

Declares the connection-level DNS filter API.

Curl_conn_dns_add_addr_resolve performs a per-connection DNS resolve and stores the result on the connection at a sockindex; Curl_conn_dns_addr_result retrieves it into the peer; Curl_conn_dns_get_ai returns a specific address from the stored list by family and index. Under USE_HTTPSRR, three more functions add and query HTTPS-RR data and report whether it resolved; without HTTPSRR the header instead defines Curl_conn_dns_get_https to NULL and Curl_conn_dns_resolved_https to TRUE, so callers compile unchanged and always behave as 'no HTTPS data'. Also declares the Curl_cft_dns filter object. Only signatures and fallback macros are present; implementations live elsewhere.

**Uncertainties.**

- Behavior of the declared functions is defined in cf-dns.c, not in this batch.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vdns/dnscache.c
[f2]: ../../../../../../eval/curl-2c04412/lib/rand.c
[f3]: ../../../../../../eval/curl-2c04412/lib/vdns/cf-dns.h
