# Connection pool (cpool)

**Capability.** Owns the lifetime of pooled connections: creation, bundle-indexed storage, limit enforcement, idle tracking and eviction, reuse selection with health checks, dead-connection reaping, and periodic keep-alive upkeep.

Use this subtree to understand when a connection is added, found for reuse, returned to idle, evicted under limits, or closed. All table walks run under the pool lock via cpool_foreach; bundle helpers manage per-destination storage.

**Depends on.**

- [Transfer progress](r9-progress.md) · graph-confirmed · 1 edge(s)
- [Time utilities](r9-time-utils.md) · graph-confirmed · 12 edge(s)

Parent: [curl codebase](r9-curl-source.md)

## Units (22)

<a id="u-53126aceb576"></a>
### `conncache-c-bundle-helpers`

`static void cpool_bundle_unlink(struct cpool_bundle **pbundle)` · [lib/conncache.c:L69-L83][f1]

Manages cpool_bundle objects: refcounted sets of per-destination connection pool ids.

cpool_bundle_unlink drops one reference and, when the count reaches zero, destroys the id set and frees the bundle. cpool_bundle_link re-points a slot to a source bundle only when different, unlinking the old value and incrementing the source's refcount. cpool_create_bundle allocates a zeroed bundle with refcount 1, returning NULL on allocation failure. cpool_bundle_add_id adds a pool id; on the first id it registers the bundle under the destination in cpool->dest2bundle via Curl_hash_add, unlinking the extra reference and returning FALSE if the insert fails. cpool_bundle_remove_id removes an id and, when the set becomes empty, deletes the destination's hash entry. cpool_bundle_hash_dtor is the hash destructor unlinking each entry; cpool_get_bundle returns a new reference to the bundle found for a destination, or NULL.

calls: [Curl_hash_add](r4-generic-containers.md#u-2b0745caec1d), [Curl_hash_delete](r4-generic-containers.md#u-b8312f0e5e92); uses: [function::Curl_hash_pick::0000][f2]

**Uncertainties.**

- Whether Curl_hash_add can fail for reasons other than memory is not shown in this file.

<a id="u-4f7625e91636"></a>
### `conncache-c-conn-age`

`void Curl_cpool_conn_was_used(struct Curl_easy *data, struct connectdata *conn, const…` · [lib/conncache.c:L1089-L1095][f1]

Small accessors over a connection's timestamps relative to creation.

Curl_cpool_conn_was_used refreshes conn->lastupkeep_ms to the elapsed time since creation, marking the connection recently used. Curl_cpool_conn_age_ms returns the elapsed milliseconds since conn->created. Both ignore the data handle.

<a id="u-2f9c5c459c06"></a>
### `conncache-c-nw-changed`

`static int cpool_reap_no_reuse(struct cpool *cpool, struct Curl_easy *admin, struct c…` · [lib/conncache.c:L988-L997][f1]

Marks every pooled connection non-reusable after a network change.

cpool_reap_no_reuse sets conn->bits.no_reuse and, when the connection can be closed, closes it non-aborted; it always returns 0 so iteration covers the whole pool. Curl_cpool_nw_changed locks the pool, runs cpool_foreach with that callback, and unlocks; it does nothing when cpool or admin is NULL. Connections still in use keep the no_reuse flag for later disposition.

calls: [cpool_conn_close](r9-conn-pool.md#u-78aff9b80aec)

<a id="u-0deb8a63c769"></a>
### `conncache-c-oldest-idle`

`static bool cpool_conn_can_be_closed(struct connectdata *conn)` · [lib/conncache.c:L332-L336][f1]

Finds the least-recently-used closable idle connection.

cpool_conn_can_be_closed is the shared predicate: non-NULL, not in use by transfers, and not CONNECT_ONLY. cpool_bundle_get_oldest_idle scans one destination's bundle id set, scoring each closable connection by (now - created) - lastused_ms and keeping the maximum; a set entry with no table entry is removed from the bundle (debug assert). cpool_get_oldest_idle scans the pool-wide idles bitset the same way, additionally requiring idle_ms >= min_age_ms, and removes stale bitset entries whose connections are no longer closable. Both return the table entry for the best id, which is NULL when none qualified.

calls: [Curl_uint32_spbset_remove](r14-uint-set-containers.md#u-8c68a0d78702)

<a id="u-c9df6e307510"></a>
### `conncache-c-reap`

`struct cpool_reaper_ctx` · [lib/conncache.c:L848-L851][f1]

Removes dead or unusable connections from the pool.

struct cpool_reaper_ctx carries a reaped counter and the current time. cpool_reap_dead_cb runs per connection: for a closable connection it closes (cpool_conn_close, non-aborted) and counts it when it is marked no_reuse or close, or when Curl_cpool_conn_seems_healthy reports unhealthy; it always returns 0 to continue iteration. cpool_prune_dead throttles the scan to at most once per second: only when at least 1000 ms elapsed since cpool->last_cleanup does it run cpool_foreach with the reaper callback and then stamp last_cleanup with the current time.

calls: [cpool_conn_close](r9-conn-pool.md#u-78aff9b80aec), [Curl_cpool_conn_seems_healthy](r9-conn-pool.md#u-ce37d835af6e)

**Uncertainties.**

- The reaped counter is recorded but no consumer of it appears in this file.

<a id="u-1260d353ee69"></a>
### `conncache-c-upkeep`

`static int conn_upkeep(struct cpool *cpool, struct Curl_easy *admin, struct connectda…` · [lib/conncache.c:L892-L915][f1]

Periodic keep-alive maintenance for all pooled connections.

conn_upkeep runs per connection: it refreshes the admin's progress clock, and when the time since the connection's last upkeep reaches admin->set.upkeep_interval_ms it records the new upkeep time, briefly attaches the admin handle to the connection, calls Curl_conn_keep_alive, and detaches; if keep-alive failed and the connection can be closed, it is closed non-aborted. It always returns 0 so iteration continues. Curl_cpool_upkeep locks the pool, runs cpool_foreach with conn_upkeep, and unlocks, returning CURLE_OK (also when no pool resolves).

calls: [lib-cfilters-c-alive-concurrency](r8-cfilters-events-state.md#u-e51cd1b49683), [cpool_conn_close](r9-conn-pool.md#u-78aff9b80aec)

**Uncertainties.**

- Curl_cpool_upkeep always returns CURLE_OK; keep-alive failures are not surfaced to the caller.

<a id="u-b9cc5c592983"></a>
### `Curl_cpool_add`

`CURLcode Curl_cpool_add(struct Curl_easy *data, struct connectdata *conn, uint32_t ma…` · [lib/conncache.c:L572-L666][f1]

Adds a connection to the pool under the pool lock.

It stamps conn->created and resets shutdown start times, fetches the destination bundle, and runs cpool_check_limits: CPOOL_LIMIT_DEST or CPOOL_LIMIT_TOTAL yield CURLE_NO_CONNECTION_AVAILABLE. If the connection table is at capacity (UINT32_MAX is the hard ceiling) it returns NO_CONNECTION_AVAILABLE; otherwise it grows the idles bitset first and then the table (growth is max(capacity,16), capped at UINT32_MAX), returning CURLE_OUT_OF_MEMORY if either resize fails. It creates a bundle when none exists (OOM -> CURLE_OUT_OF_MEMORY), inserts the connection obtaining cpid, and registers cpid in the bundle; if that registration fails the table insert is rolled back and conn->cpid reset. On all exits it unlinks the bundle reference and unlocks. Failure of conn->cpid == UINT32_MAX precondition is only asserted in debug.

calls: [cpool_check_limits](r9-conn-pool.md#u-8e22a96ed8cd), [Curl_uint32_tbl_add](r15-uint-containers.md#u-aa04762f59cf)

**Uncertainties.**

- Whether a bundle creation failure after a successful table insert could leave the pool inconsistent is prevented only by the shown rollback path; rollback of the bundle itself on later failure is not present.

<a id="u-ce37d835af6e"></a>
### `Curl_cpool_conn_seems_healthy`

`bool Curl_cpool_conn_seems_healthy(struct connectdata *conn, struct Curl_easy *data, …` · [lib/conncache.c:L1041-L1087][f1]

Decides whether an idle connection is fit for reuse.

cpool_conn_too_old (folded here) first rejects connections idle longer than data->set.conn_max_idle_ms, then those created longer than data->set.conn_max_age_ms ago, each limit skipped when zero; both log an info message. seems_healthy returns FALSE immediately when a closable connection is too old. For an idle non-multiplexed connection (not marked connection_is_dead) input is polled on every reuse per RFC 9112 9.2; otherwise the remaining checks are throttled to once per second via conn->lastchecked_ms. The scheme's connection_is_dead callback is consulted under a temporary attach, else Curl_conn_is_alive is called with pending-input detection: pending input on a polled connection marks it unhealthy. When healthy, lastchecked_ms is updated; the verdict is returned.

calls: [lib-cfilters-c-alive-concurrency](r8-cfilters-events-state.md#u-e51cd1b49683), [lib-cfilters-c-chain-state-queries](r8-cfilters-events-state.md#u-b752791790cf)

**Uncertainties.**

- conn->scheme->run callback semantics (connection_is_dead) are defined outside this file.

<a id="u-59c78ead67ef"></a>
### `Curl_cpool_destroy`

`void Curl_cpool_destroy(struct cpool *cpool, struct Curl_easy *admin)` · [lib/conncache.c:L260-L288][f1]

Tears down an initialized pool when a non-NULL admin handle is supplied.

Under the pool lock (SIGPIPE suppressed around the loop) it iterates all pooled connections, removing each from the tables and discarding it non-aborted, then unlocks and destroys the dest2bundle hash, the idles bitset, and the connection table. Non-initialized pools or a NULL admin are silently ignored.

calls: [cpool_remove_conn](r9-conn-pool.md#u-f1169ce33fae), [cpool_discard_conn](r9-conn-pool.md#u-0cd9086989f4)

**Uncertainties.**

- Whether discarded connections finish closing synchronously depends on cshutdn behavior not shown here.

<a id="u-58d7dd3f53ef"></a>
### `Curl_cpool_find`

`bool Curl_cpool_find(struct Curl_easy *data, const char *destination, bool prune_dead…` · [lib/conncache.c:L779-L846][f1]

Searches for a reusable connection under the pool lock, optionally pruning dead connections first.

It first checks the connection recorded in data->state.last_cpid (valid only if its connection_id still matches), making connection reuse sticky; a mismatched entry resets the sticky state. It then iterates the destination bundle's id set, skipping the current last_conn_id, and consults conn_cb(conn, userdata) for each candidate. cpool_find_act applies the verdict: CPOOL_MATCH_FOUND returns TRUE; CPOOL_MATCH_TOO_OLD falls through to closing only when the connection can be closed, otherwise returns FALSE; CPOOL_MATCH_CLOSE closes the connection and returns FALSE. If a bundle set entry has no table entry it is removed (debug assert). At the end done_cb, if set, overrides the found result. Returns the final verdict with the lock released.

calls: [conncache-c-reap](r9-conn-pool.md#u-c9df6e307510), [cpool_conn_close](r9-conn-pool.md#u-78aff9b80aec)

**Uncertainties.**

- The conn_cb/done_cb callback contracts are declared elsewhere; verdict semantics beyond the switch are taken from the enumerated cases.

<a id="u-983f25d589e8"></a>
### `Curl_cpool_get_last_conn`

`struct connectdata *Curl_cpool_get_last_conn(struct Curl_easy *data)` · [lib/conncache.c:L931-L946][f1]

Returns the transfer's most recently used connection if it is still valid.

When data->state.last_cpid is set, it looks the entry up under the pool lock; the connection is returned only when its connection_id matches data->state.last_conn_id. On a mismatch (or absent pool) it resets last_cpid to UINT32_MAX and last_conn_id to -1 and returns NULL.

<a id="u-dc761c205d15"></a>
### `Curl_cpool_init`

`void Curl_cpool_init(struct cpool *cpool, struct Curl_share *share, size_t size)` · [lib/conncache.c:L246-L258][f1]

Initializes a connection pool: the connection table, the idle bitset, and the destination-to-bundle hash with the bundle destructor, then stores the owning share and clears initialized/in_shutdown/locked state.

<a id="u-97205a68870c"></a>
### `Curl_cpool_return`

`void Curl_cpool_return(struct Curl_easy *data, struct connectdata *conn, Curl_cpool_r…` · [lib/conncache.c:L948-L986][f1]

Returns a used connection to pool custody under the pool lock.

It first stamps lastchecked_ms, lastupkeep_ms, and lastused_ms with the elapsed time since creation, then dispatches on the caller-supplied cb verdict: CPOOL_DO_KEEP does nothing further; CPOOL_DO_IDLE makes the connection idle via cpool_conn_now_idle, logging that it was kept or resetting the transfer's sticky last-connection state when it was removed; CPOOL_DO_CLOSE closes it non-aborted; CPOOL_DO_TERMINATE closes it aborted. The callback itself decides reuse, so its contract governs the outcome.

calls: [cpool_conn_now_idle](r9-conn-pool.md#u-453107f1ae6d), [cpool_conn_close](r9-conn-pool.md#u-78aff9b80aec)

**Uncertainties.**

- The return-callback's decision criteria live with the caller, not in this file.

<a id="u-753708c3301c"></a>
### `Curl_cpool_xfer_init`

`void Curl_cpool_xfer_init(struct Curl_easy *data)` · [lib/conncache.c:L308-L330][f1]

Assigns a transfer its pool identifier.

Under the pool lock it sets data->id from cpool->next_easy_id (wrapping to 0 at CURL_OFF_T_MAX) and resets data->state.last_conn_id to -1 and last_cpid to UINT32_MAX. If no pool can be resolved it asserts in debug builds and applies the same resets with id 0 in non-debug builds.

<a id="u-8e22a96ed8cd"></a>
### `cpool_check_limits`

`static int cpool_check_limits(struct Curl_easy *data, uint32_t max_total, struct conn…` · [lib/conncache.c:L479-L570][f1]

Enforces per-destination and total connection limits before a connection is added, returning CPOOL_LIMIT_OK, CPOOL_LIMIT_DEST, or CPOOL_LIMIT_TOTAL.

With no pool or no limits set it returns OK. For the destination limit it counts live connections in the bundle; at or above max_host it evicts the oldest idle connections from the bundle (live - max_host + 1 of them), then counts pending shutdowns for that destination and closes the oldest of those via Curl_cshutdn_close_oldest. If live + shutdowns still reaches max_host it returns CPOOL_LIMIT_DEST. The total limit skips internal transfers: it evicts pool-wide oldest idle connections when the table count reaches max_total, then closes oldest shutdown entries; if the sum still reaches max_total it returns CPOOL_LIMIT_TOTAL.

calls: [cpool_evict_conn](r9-conn-pool.md#u-3f16ef2c7ac2), [cshutdn.c-destroy-oldest](r8-conn-shutdown.md#u-448b6a0d1dd5)

**Uncertainties.**

- Exact concurrency between pool counts and shutdown-list counts (double counting at the boundary) is not provable from this file alone.

<a id="u-78aff9b80aec"></a>
### `cpool_conn_close`

`static void cpool_conn_close(struct cpool *cpool, struct Curl_easy *data, struct conn…` · [lib/conncache.c:L397-L449][f1]

Closes a connection.

It refuses when the connection is in use and not aborted (debug assert and log, no action). Because the caller may already hold the pool lock (e.g. from a find callback), it takes the lock only when not held. It removes the connection from the pool if still pooled (cpid != UINT32_MAX), treats CONNECT_ONLY as aborted so no graceful shutdown is attempted, then either hands the connection to the transfer's multi pool via cpool_discard_conn (logging closing vs shutting down per the aborted flag) or, with no multi available, terminates it directly with Curl_cshutdn_terminate(admin, conn, !aborted). Curl_conn_close is the public wrapper resolving the pool and delegating.

calls: [Curl_cshutdn_terminate](r8-conn-shutdown.md#u-a031613cb853)

<a id="u-453107f1ae6d"></a>
### `cpool_conn_now_idle`

`static bool cpool_conn_now_idle(struct cpool *cpool, struct Curl_easy *data, struct c…` · [lib/conncache.c:L709-L752][f1]

Handles a connection becoming idle: adds its cpid to cpool->idles and enforces the pool size.

With no data or no multi it keeps the connection. When multi->maxconnects is unset it guesses a limit of twice the currently attached transfers, and only evicts connections idle for at least 1000 ms in that guessing mode. If the pool exceeds maxconnects, it finds the oldest qualifying idle connection with a min age and evicts it; kept is TRUE only when the evicted connection was not this one. Returns TRUE if the idle connection stays in the pool, FALSE if it was removed.

calls: [conncache-c-oldest-idle](r9-conn-pool.md#u-0deb8a63c769), [cpool_evict_conn](r9-conn-pool.md#u-3f16ef2c7ac2)

**Uncertainties.**

- The attached-transfers heuristic doubling and the 1000 ms minimum age are heuristic, exact business impact unprovable here.

<a id="u-0cd9086989f4"></a>
### `cpool_discard_conn`

`static void cpool_discard_conn(struct cpool *cpool, struct Curl_easy *data, struct co…` · [lib/conncache.c:L187-L244][f1]

Moves an already-unpooled connection (cpid == UINT32_MAX) into shutdown handling.

It refuses to discard a connection still in use by transfers, logging and returning instead (debug assert). CONNECT_ONLY connections are forcibly treated as aborted, and conn->bits.aborted records the verdict. When aborted, no shutdown attempt is made, because a graceful shutdown could make the server believe an aborted operation (e.g. an ftps: upload) succeeded. Otherwise Curl_cshutdn_try_once attempts immediate shutdown and sets done. If done or data->multi is absent, Curl_cshutdn_terminate finishes the connection; otherwise it is queued on the multi's shutdown list with a cap derived from multi->max_total_connections: the remaining budget after subtracting live pool connections, clamped to 1 when the limit is already reached, or CURLMAX(conns/4, 128) when no limit is configured.

calls: [Curl_cshutdn_try_once](r8-conn-shutdown.md#u-b363435953a0), [cshutdn.c-add](r8-conn-shutdown.md#u-649ff17c65cb), [Curl_cshutdn_terminate](r8-conn-shutdown.md#u-a031613cb853)

**Uncertainties.**

- CONN_INUSE semantics and the shutdown-list capacity behavior live outside this file.

<a id="u-3f16ef2c7ac2"></a>
### `cpool_evict_conn`

`static void cpool_evict_conn(struct cpool *cpool, struct Curl_easy *admin, struct con…` · [lib/conncache.c:L463-L473][f1]

Evicts an idle connection to make room, expecting the pool to be locked.

For a share-owned pool there is no multi to perform a controlled shutdown, so it removes the connection from the pool and terminates it right away; otherwise it defers to cpool_conn_close, which routes the connection through the multi's shutdown handling.

calls: [cpool_conn_close](r9-conn-pool.md#u-78aff9b80aec), [Curl_cshutdn_terminate](r8-conn-shutdown.md#u-a031613cb853)

<a id="u-255c27d15bd4"></a>
### `cpool_foreach`

`static bool cpool_foreach(struct Curl_easy *data, struct cpool *cpool, void *param, i…` · [lib/conncache.c:L680-L701][f1]

Iterates every entry in the pool's connection table, invoking func(cpool, data, conn, param) with the pool lock still held so the callback can safely continue the traversal.

Returns TRUE only when the callback returned 1 to abort the loop; 0 continues. A NULL pool returns FALSE immediately.

<a id="u-9dc998473e9f"></a>
### `cpool_get_instance`

`static struct cpool *cpool_get_instance(struct Curl_easy *data)` · [lib/conncache.c:L290-L301][f1]

Resolves the pool a transfer belongs to: the share's pool when the share keeps connections, otherwise multi_easy's pool, else multi's pool, else NULL (admin handles do not necessarily resolve the right pool, per the comment).

Curl_cpool_get_instance is the public wrapper returning the same value.

<a id="u-f1169ce33fae"></a>
### `cpool_remove_conn`

`static void cpool_remove_conn(struct cpool *cpool, struct connectdata *conn)` · [lib/conncache.c:L159-L185][f1]

Removes a pooled connection from the pool tables.

If conn->cpid is UINT32_MAX the connection is not pooled and nothing happens. Otherwise (in debug builds it first asserts the table entry at cpid equals the connection) it removes cpid from cpool->conns and cpool->idles, resets conn->cpid to UINT32_MAX, then fetches the destination bundle and removes cpid from it, which may unregister the bundle entirely when it becomes empty.

**Notes.**

- side_effect: Mutates cpool->conns, cpool->idles, the destination bundle, and conn->cpid; assumes the pool lock is already held.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/conncache.c
[f2]: ../../../../../../eval/curl-2c04412/lib/hash.c
