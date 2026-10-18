# Share API

**Capability.** The Curl_share object: public init/setopt/cleanup, refcount and lock helpers, easy-handle link/unlink, and deep teardown of shared sub-resources.

Use for sharing data between easy handles and the user-supplied locking protocol. Public calls route through the refcount/lock helper group; share_destroy backs cleanup, init failure, and unlink paths.

**Depends on.**

- [Extended Attribute Metadata](r6-tool-xattr-metadata.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Connection Setup and Control](r6-connection-management.md) · model-inferred · 0 edge(s)
- [Auth Emission and Expect-100](r6-http-auth-and-expect.md) · model-inferred · 0 edge(s)
- [Response Parsing and Reaction](r6-http-response-processing.md) · graph-confirmed · 2 edge(s)

Parent: [curl Codebase](r6-curl-codebase.md)

## Units (10)

<a id="u-7082f7e51415"></a>
### `curl_share_init`

`CURLSH *curl_share_init(void)` · [lib/curl_share.c:L71-L96][f1]

Allocates and initializes a new empty share handle, or returns NULL on allocation failure.

Sets the good-share magic, marks CURL_LOCK_DATA_SHARE as shared, initializes the mutex under USE_MUTEX, sets ref_count to 1, initializes the DNS cache with a 23-bucket size, and creates an internal admin easy handle via curl_easy_init. If the admin handle cannot be created, the partially built share is destroyed with share_destroy and NULL is returned. The admin handle gets mid 0 and state.internal TRUE; under DEBUGBUILD it enables verbose when CURL_DEBUG is set in the environment.

calls: [share_destroy](r6-share-api.md#u-89c4869df07a), [curl_easy_init](r14-core-easy-lifecycle.md#u-fbaa1c338bc9), [dnscache.c-cache-lifecycle](r11-dnscache.md#u-14e97f54664f)

**Uncertainties.**

- The DNS cache bucket count 23 and connect pool parameters are hard-coded; their tuning effect is defined elsewhere.

<a id="u-0979b82db2a2"></a>
### `curl_share_setopt`

`CURLSHcode curl_share_setopt(CURLSH *sh, CURLSHoption option, ...)` · [lib/curl_share.c:L194-L357][f1]

Configures a share handle; returns CURLSHE_INVALID for a bad handle and CURLSHE_IN_USE if share_in_use reports other handles are already using it, so options cannot change mid-sharing.

Variadic option dispatch: CURLSHOPT_SHARE enables a data type. For CURL_LOCK_DATA_COOKIE it lazily creates the cookie container (CURLSHE_NOMEM on failure) or returns CURLSHE_NOT_BUILT_IN when cookies are compiled out; HSTS behaves the same with Curl_hsts_init; SSL_SESSION creates a session cache of 25 entries / 2 generations under USE_SSL, else CURLSHE_NOT_BUILT_IN; CONNECT initializes the connection pool once (safe to repeat) when not already initialized; PSL is CURLSHE_NOT_BUILT_IN without USE_LIBPSL; DNS needs no setup; unknown types yield CURLSHE_BAD_OPTION. On success the type's specifier bit is set. CURLSHOPT_UNSHARE mirrors this: it tears down cookies, HSTS, or the SSL session cache if present (CONNECT and DNS need no teardown) and clears the specifier bit on success; unsupported types again give CURLSHE_NOT_BUILT_IN or CURLSHE_BAD_OPTION. CURLSHOPT_LOCKFUNC/UNLOCKFUNC/USERDATA store the callback pointers and client data directly. Any unknown option is CURLSHE_BAD_OPTION. The #undef of curl_share_setopt suggests a macro shim defined elsewhere.

**Notes.**

- side_effect: Successful SHARE/UNSHARE of a valid type mutates share->specifier even when the corresponding sub-resource was already created or already absent.

calls: [Curl_cookie_init](r12-cookie-jar-core.md#u-8570927d82e9), [Curl_hsts_init](r10-hsts-cache.md#u-85f212dd39be), [Curl_cpool_init](r9-conn-pool.md#u-dc761c205d15), [Curl_cookie_cleanup](r12-cookie-jar-core.md#u-7250284b8b00), [Curl_hsts_cleanup](r10-hsts-cache.md#u-08a59bb64394); uses: [curl-share-c-refcount-and-lock-helpers](r6-share-api.md#u-323ff6ba71ae)

**Uncertainties.**

- Failure codes set inside the SHARE switch skip setting the specifier bit but any partially created resource (e.g. a successfully created ssl_scache after a failed create path) is left in place; exact partial-failure residue depends on the callee implementations not shown.

<a id="u-b0391d247790"></a>
### `curl_share_cleanup`

`CURLSHcode curl_share_cleanup(CURLSH *sh)` · [lib/curl_share.c:L359-L372][f1]

Public teardown of a share handle: returns CURLSHE_INVALID for a bad handle and CURLSHE_IN_USE while ref_count is greater than one, so the last owner must clean up.

Otherwise it takes the share-level lock (share_lock_acquire with NULL data, honored only if lock callbacks are configured) and calls share_unlink, which decrements the reference count, releases the lock, and destroys the share when the count reaches zero. Always returns CURLSHE_OK once past the validity and in-use checks.

calls: [curl-share-c-refcount-and-lock-helpers](r6-share-api.md#u-323ff6ba71ae); uses: [share_destroy](r6-share-api.md#u-89c4869df07a)

<a id="u-89c4869df07a"></a>
### `share_destroy`

`static void share_destroy(struct Curl_share *share)` · [lib/curl_share.c:L35-L69][f1]

Destroys a Curl_share structure, releasing every shared sub-resource it owns before freeing the object itself.

Returns immediately on a NULL share. When the share was set up for connection sharing (specifier bit CURL_LOCK_DATA_CONNECT), it destroys the connection pool with the admin easy handle as client context; unconditionally destroys the DNS cache, cookies (unless HTTP/cookies are compiled out), HSTS (unless disabled), the PSL data, and the SSL session cache under USE_SSL (NULLing ssl_scache after destroy). It then closes the internal admin easy handle, destroys the lock mutex under USE_MUTEX, zeroes the whole struct with curlx_memzero, and frees it. Errors from the sub-destroy calls are not surfaced; the function returns void.

calls: [Curl_cpool_destroy](r9-conn-pool.md#u-59c78ead67ef), [dnscache.c-cache-lifecycle](r11-dnscache.md#u-14e97f54664f), [Curl_cookie_cleanup](r12-cookie-jar-core.md#u-7250284b8b00), [Curl_hsts_cleanup](r10-hsts-cache.md#u-08a59bb64394), [Curl_close](r7-easy-handle-lifecycle.md#u-2c32be255a3a)

**Uncertainties.**

- Whether Curl_ssl_scache_destroy and Curl_psl_destroy can fail is not visible; their results are ignored here.

<a id="u-45aa6f6d595e"></a>
### `Curl_share_easy_link`

`CURLcode Curl_share_easy_link(struct Curl_easy *data, struct Curl_share *share)` · [lib/curl_share.c:L450-L495][f1]

Attaches an easy handle to a share, returning CURLE_FAILED_INIT if the handle already has a share (with a DEBUGASSERT that this never happens), otherwise CURLE_OK; a NULL share is a no-op success.

Under the acquired share lock, when connections are shared it resets last_conn_id/last_cpid so identifiers from a previous cache are forgotten. share_ref_inc bumps the count and marks the share as shared, then data->share is set. If the share has cookies, the easy handle's private cookie list is freed (Curl_cookie_cleanup) and replaced by the shared list, implicitly enabling cookies; similarly the private HSTS container is freed (Curl_hsts_cleanup) and replaced by the shared one. Under USE_LIBPSL, the easy handle points at the share's PSL data when PSL sharing is enabled. The lock is released before returning.

calls: [Curl_cookie_cleanup](r12-cookie-jar-core.md#u-7250284b8b00), [Curl_hsts_cleanup](r10-hsts-cache.md#u-08a59bb64394), [curl-share-c-refcount-and-lock-helpers](r6-share-api.md#u-323ff6ba71ae)

**Uncertainties.**

- When share->cookies is NULL the easy handle's own cookie list is left untouched; enabling of cookies therefore happens only for shared-cookie links, per the code comment.

<a id="u-8cd7b4636d92"></a>
### `Curl_share_easy_unlink`

`CURLcode Curl_share_easy_unlink(struct Curl_easy *data)` · [lib/curl_share.c:L415-L448][f1]

Detaches an easy handle from its share, always returning CURLE_OK; does nothing when data->share is NULL.

It first acquires the share-level lock for this easy handle. When the share shares connections, it detaches any existing connection from the easy handle (Curl_detach_connection) and resets the last-connection identifiers (last_conn_id = -1, last_cpid = UINT32_MAX) so stale cache entries are not reused. It then NULLs the easy handle's pointers to the shared cookie list, HSTS container, and (under USE_LIBPSL) repoints psl to the multi handle's PSL or NULL when they referenced the share's. Finally share_unlink NULLs data->share, decrements the reference count, releases the lock, and destroys the share if this was the last reference.

calls: [Curl_detach_connection](r13-multi-engine.md#u-4f1ba947d609), [curl-share-c-refcount-and-lock-helpers](r6-share-api.md#u-323ff6ba71ae); uses: [share_destroy](r6-share-api.md#u-89c4869df07a)

**Uncertainties.**

- The DEBUGASSERT in share_lock_release requires unlockfunc when locked; whether unset unlockfunc with lockfunc set can reach that assert depends on caller setup not shown here.

<a id="u-6146ca450d97"></a>
### `Curl_share_lock_share`

`CURLSHcode Curl_share_lock_share(struct Curl_share *share, struct Curl_easy *data, cu…` · [lib/curl_share.c:L374-L388][f1]

Acquires the user's lock for one data type on a share, returning CURLSHE_OK in all non-NULL-share cases.

It calls the user's lockfunc (with the given easy handle, data type, access type, and clientdata) only when the type's specifier bit is set and a lockfunc is configured; otherwise it silently succeeds, per the comment that non-shared types pretend a successful lock. Returns CURLSHE_INVALID when share is NULL.

uses: [Curl_share_lock_share](r6-share-api.md#u-6146ca450d97)

<a id="u-552c57d51f96"></a>
### `Curl_share_unlock_share`

`CURLSHcode Curl_share_unlock_share(struct Curl_share *share, struct Curl_easy *data, …` · [lib/curl_share.c:L396-L408][f1]

Releases the user's lock for one data type on a share: calls the configured unlockfunc with the easy handle, type, and clientdata only when the type's specifier bit is set and unlockfunc exists, otherwise succeeds silently.

Returns CURLSHE_INVALID for a NULL share, otherwise CURLSHE_OK. Curl_share_unlock is its one-line wrapper taking the easy handle and using data->share.

<a id="u-e9dea3e48831"></a>
### `curl_share.c module code (L1–L34)`

`module_region` · [lib/curl_share.c:L1-L34][f1]

License header and include block for the share API implementation.

<a id="u-323ff6ba71ae"></a>
### `curl-share-c-refcount-and-lock-helpers`

`static uint32_t share_ref_inc(struct Curl_share *share)` · [lib/curl_share.c:L98-L111][f1]

Internal helpers implementing reference counting and share-level locking around the Curl_share object.

share_ref_inc increments ref_count and sets has_been_shared, acquiring the share mutex under USE_MUTEX so the increment is atomic, and returns the new count. share_ref_dec decrements ref_count under the same mutex discipline (with a DEBUGASSERT that the count is nonzero) and returns the new count. share_has_been_shared reads has_been_shared under the mutex. share_lock_acquire invokes the user's lockfunc for CURL_LOCK_DATA_SHARE only when both lockfunc and unlockfunc are set and either a specific easy handle is given or the share has been shared; it returns whether the lock was taken. share_lock_release invokes unlockfunc with the same data when 'locked' is true, with a DEBUGASSERT that unlockfunc exists. share_in_use reports whether ref_count exceeds 1, taking the mutex when available or wrapping the read in the user's share lock otherwise. share_unlink NULLs the caller's share pointer, decrements the reference, releases the share lock if it was held, and destroys the share when the count reaches zero.

calls: [share_destroy](r6-share-api.md#u-89c4869df07a); uses: [function::share_lock_acquire::3526][f1]

**Uncertainties.**

- Without USE_MUTEX, share_in_use relies on the user's lockfunc/unlockfunc; if none is set, the ref_count read is unlocked and subject to races.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curl_share.c
