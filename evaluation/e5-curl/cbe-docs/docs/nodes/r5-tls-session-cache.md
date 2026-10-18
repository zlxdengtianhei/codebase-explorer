# TLS Session Cache

**Capability.** Per-peer TLS session reuse: peer-key construction capturing all reuse-relevant config, peer-slot management with LRU replacement, session object lifecycle, locking, opaque objects, and salt/HMAC-based export/import.

Read ssl_peer_key_build first to understand what makes sessions comparable; then cf_scache_add_session/Curl_ssl_scache_take for put/take flow. Session lifecycle and cache lifecycle are independent layers; export adds an interchange format on top.

Parent: [curl Library and Tool](r5-curl-codebase.md)

## Units (29)

<a id="u-332701712a46"></a>
### `vtls_scache-export`

`static CURLcode cf_ssl_scache_peer_set_hmac(struct Curl_ssl_scache_peer *peer)` · [lib/vtls/vtls_scache.c:L1146-L1166][f1]

Session-ticket export/import under USE_SSLS_EXPORT: per-peer salt+HMAC generation, HMAC-based peer lookup, ticket unpack/add on import, and iteration of exportable peers calling the user export callback.

**Uncertainties.**

- Whether Curl_ssl_session_unpack/pack failure modes leave partial state in the cache is not determinable from this file

<a id="u-1789c5727c7b"></a>
### `vtls_scache-locking`

`void Curl_ssl_scache_lock(struct Curl_easy *data)` · [lib/vtls/vtls_scache.c:L695-L713][f1]

Cache locking: share-lock integration plus optional mutex-based recursive-state tracking (locking thread id and is_locked flag with debug assertions).

**Uncertainties.**

- Whether the mutex path is re-entrant when the same thread locks twice: the DEBUGASSERT(!is_locked) suggests single-lock expectation but no runtime guarantee is visible

<a id="u-df0a690c7e60"></a>
### `vtls_scache-peer-key`

`static CURLcode cf_ssl_peer_key_add_string(struct dynbuf *buf, const char *name, cons…` · [lib/vtls/vtls_scache.c:L67-L72][f1]

Builds the peer identification key string that selects which cached TLS sessions match a connection.

Spans the key-fragment helpers, transport/verify/config appenders, and the assembly function.

group: [ssl_peer_key_build](r5-tls-session-cache.md#u-5e052568d6d4)

**Uncertainties.**

- The final curlx_dyn_addf call passes CURL_SSLS_LOCAL_SUFFIX/GLOBAL_SUFFIX as the format argument; behavior relies on them containing no format specifiers

<a id="u-c427e499e55d"></a>
### `vtls_scache-peer-store`

`static void cf_ssl_scache_clear_peer(struct Curl_ssl_scache_peer *peer)` · [lib/vtls/vtls_scache.c:L511-L526][f1]

Internal peer-slot management of the cache: clearing, initialization, object attachment, exportability updates, session-list maintenance (expiry, non-1.3 removal, capacity trim), and slot selection/replacement.

calls: [vtls_scache-session-lifecycle](r5-tls-session-cache.md#u-8d4794b50a22)

<a id="u-6fe821db9460"></a>
### `vtls_scache-scache-lifecycle`

`CURLcode Curl_ssl_scache_create(size_t max_peers, size_t max_sessions_per_peer, struc…` · [lib/vtls/vtls_scache.c:L632-L666][f1]

Creation and destruction of the whole Curl_ssl_scache instance: allocation of the peer array, magic/lifetime/age initialization, per-peer session list setup, and symmetric teardown.

<a id="u-8d4794b50a22"></a>
### `vtls_scache-session-lifecycle`

`static void cf_ssl_scache_session_ldestroy(void *udata, void *obj)` · [lib/vtls/vtls_scache.c:L392-L400][f1]

Creation, duplication, and destruction of individual Curl_ssl_session objects, independent of the cache.

Covers the list-node destructor used by peer session lists.

calls: [vtls_scache-session-lifecycle](r5-tls-session-cache.md#u-8d4794b50a22)

<a id="u-ca92c639c682"></a>
### `Curl_ssl_scache_add_obj`

`CURLcode Curl_ssl_scache_add_obj(struct Curl_cfilter *cf, struct Curl_easy *data, con…` · [lib/vtls/vtls_scache.c:L1062-L1094][f1]

Attaches an opaque caller object with a destructor callback to the peer slot for a key.

No scache yields CURLE_BAD_FUNCTION_ARGUMENT with the object destroyed via the callback. After a peer is found or created, cf_ssl_scache_peer_set_obj installs the object (destroying any previous one); on failure the callback destroys sobj. Success returns CURLE_OK with ownership transferred.

**Uncertainties.**

- The call does not take the cache lock, unlike put/take; cross-thread safety is not established here

<a id="u-71548024fc20"></a>
### `Curl_ssl_scache_get_obj`

`void *Curl_ssl_scache_get_obj(struct Curl_cfilter *cf, struct Curl_easy *data, const …` · [lib/vtls/vtls_scache.c:L1096-L1119][f1]

Returns the opaque object stored for a peer key, or NULL when there is no scache, the lookup fails, or the peer has no object.

Find errors are swallowed into NULL.

<a id="u-9ab703f27dc3"></a>
### `Curl_ssl_scache_put`

`CURLcode Curl_ssl_scache_put(struct Curl_cfilter *cf, struct Curl_easy *data, const c…` · [lib/vtls/vtls_scache.c:L985-L1004][f1]

Public insert: destroys the session and returns OK when there is no scache or caching is disabled for the connection; otherwise takes the cache lock, delegates to cf_scache_add_session, and releases the lock.

Return value is cf_scache_add_session's result.

<a id="u-27310e9460a5"></a>
### `Curl_ssl_scache_remove_all`

`void Curl_ssl_scache_remove_all(struct Curl_cfilter *cf, struct Curl_easy *data, cons…` · [lib/vtls/vtls_scache.c:L1121-L1140][f1]

Removes all cached data (sessions and object) for a peer key: locks the cache, finds the peer, clears the slot, unlocks.

No-op without a scache; lookup errors leave the cache untouched.

<a id="u-45e22422388b"></a>
### `Curl_ssl_scache_return`

`void Curl_ssl_scache_return(struct Curl_cfilter *cf, struct Curl_easy *data, const ch…` · [lib/vtls/vtls_scache.c:L1006-L1017][f1]

Returns a taken session for reuse.

Per RFC 8446 C.4, TLS 1.3 tickets (ietf_tls_id >= 0x304) are not re-cached and are destroyed; older sessions are put back into the cache, which destroys them if that fails.

<a id="u-fc4277c1cb89"></a>
### `Curl_ssl_scache_take`

`CURLcode Curl_ssl_scache_take(struct Curl_cfilter *cf, struct Curl_easy *data, const …` · [lib/vtls/vtls_scache.c:L1019-L1060][f1]

Takes the head session for a peer key: locks the cache, finds the peer, prunes expired sessions, then detaches the head session, bumping the global age and stamping it as the peer's age (LRU recency).

No scache returns OK with *ps NULL. Lock is always released; the find error is propagated.

<a id="u-59f86aff3fb0"></a>
### `Curl_ssl_scache_use`

`bool Curl_ssl_scache_use(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/vtls_scache.c:L684-L692][f1]

Reports whether session caching applies to this connection: the transfer must resolve to a valid scache and the connection's SSL filter config must have cache_session enabled; otherwise FALSE.

<a id="u-457608dec5ba"></a>
### `cf_scache_add_session`

`static CURLcode cf_scache_add_session(struct Curl_cfilter *cf, struct Curl_easy *data…` · [lib/vtls/vtls_scache.c:L929-L983][f1]

Adds one session to the cache under its peer key.

Empty/absent cache destroys the session and returns OK. valid_until <= 0 becomes now plus the cache default lifetime, then is clamped to the TLS-version maximum (1.3 vs 1.2 limit). An already-expired session is destroyed silently. Peer lookup/add failure destroys the session and fails with failf; success appends via cf_scache_peer_add_session and logs trace details.

**Uncertainties.**

- Exact CURL_SCACHE_MAX_13/12_LIFETIME_SEC values are defined elsewhere

<a id="u-4e355512c31b"></a>
### `cf_ssl_add_peer`

`static CURLcode cf_ssl_add_peer(struct Curl_easy *data, struct Curl_ssl_scache *scach…` · [lib/vtls/vtls_scache.c:L860-L907][f1]

Finds or creates the peer slot for a key.

With a key it first looks up an existing slot (returning its error, or CURLE_OK when the cache has no slots). If not found, takes a free slot; when the config uses a cert blob without a clientcert path it synthesizes a 'cert-<ptr>' name as the clientcert identity (strduped by init). Slot init failure clears the peer and returns the error. No free slot yields *ppeer NULL with CURLE_OK.

**Uncertainties.**

- ssl_peer_key NULL (import path) skips lookup and always allocates a fresh slot, even if an HMAC twin exists

<a id="u-371785272978"></a>
### `cf_ssl_find_peer_by_key`

`static CURLcode cf_ssl_find_peer_by_key(struct Curl_easy *data, struct Curl_ssl_scach…` · [lib/vtls/vtls_scache.c:L766-L828][f1]

Finds the peer slot for a key within a validated cache.

First pass: exact strcmp match on ssl_peer_key also passing the auth-config match. Second pass: slots with hmac_set but no ssl_peer_key — it lazily computes the key's HMAC-SHA256 with the slot's salt and, on match, recovers the key by strdup-ing it into the slot, recomputes exportability, and returns the slot. Bad magic returns CURLE_BAD_FUNCTION_ARGUMENT; HMAC or strdup failure propagates. No match leaves *ppeer NULL with CURLE_OK.

**Uncertainties.**

- The auth match (conn_config) is not applied when recovering the key for an HMAC-only slot beyond cf_ssl_scache_match_auth, which is applied

<a id="u-42e45deae626"></a>
### `cf_ssl_get_free_peer`

`static struct Curl_ssl_scache_peer *cf_ssl_get_free_peer( struct Curl_ssl_scache *sca…` · [lib/vtls/vtls_scache.c:L830-L858][f1]

Selects a reusable peer slot: first fully empty slot (no key, no hmac); else the first slot with neither an sobj nor sessions; otherwise tracks the slot with the lowest age as victim.

The chosen slot is cleared via cf_ssl_scache_clear_peer before return. With peer_count 0 the loop leaves peer NULL (DEBUGASSERT fires) and NULL is returned.

<a id="u-95329063ada4"></a>
### `cf_ssl_peer_key_add_hash`

`static CURLcode cf_ssl_peer_key_add_hash(struct dynbuf *buf, const char *name, struct…` · [lib/vtls/vtls_scache.c:L109-L132][f1]

Appends a name tag plus the SHA-256 hex digest of a blob.

NULL or zero-length blob adds nothing. Any dynbuf or hashing failure aborts via the out label and is returned.

<a id="u-b47092ea9757"></a>
### `cf_ssl_peer_key_add_mtls`

`static CURLcode cf_ssl_peer_key_add_mtls(struct dynbuf *buf, struct ssl_filter_config…` · [lib/vtls/vtls_scache.c:L134-L174][f1]

Appends the mutual-TLS identity of the config: client cert and key as paths (delegating is_local), key blob as hash, and cert/key types as uppercased, length-prefixed strings.

Each present field is appended in order; first error short-circuits to out.

<a id="u-c8c2c756a595"></a>
### `cf_ssl_peer_key_add_path`

`static CURLcode cf_ssl_peer_key_add_path(struct dynbuf *buf, const char *name, const …` · [lib/vtls/vtls_scache.c:L74-L107][f1]

Appends a file-path fragment, preferring the absolute form so the key stays valid across processes with different working directories.

Empty/NULL path adds nothing (CURLE_OK). On Windows it uses _fullpath; on realpath systems only relative paths are resolved. If absolutization fails, is_local is set TRUE and the path is added as-is; that flag later selects the ':L' local instead of ':G' global key suffix.

**Uncertainties.**

- is_local is never reset here; once any path fails to absolutize the whole key becomes local

<a id="u-7eb29806f742"></a>
### `cf_ssl_peer_key_add_string`

`static CURLcode cf_ssl_peer_key_add_string(struct dynbuf *buf, const char *name, cons…` · [lib/vtls/vtls_scache.c:L67-L72][f1]

Appends a length-prefixed, name-tagged string fragment (":name-len:value") to the peer-key dynbuf so adjacent fields stay unambiguous.

Returns the dynbuf result.

<a id="u-8a7fbeb263c3"></a>
### `cf_ssl_peer_key_is_global`

`static bool cf_ssl_peer_key_is_global(const char *peer_key)` · [lib/vtls/vtls_scache.c:L179-L185][f1]

Tests whether a peer key ends with the ':G' global suffix (no relative paths) rather than ':L'; NULL or keys of length <= 2 are not global.

<a id="u-4c9e1b739c7a"></a>
### `cf_ssl_scache_get`

`static struct Curl_ssl_scache *cf_ssl_scache_get(struct Curl_easy *data)` · [lib/vtls/vtls_scache.c:L375-L390][f1]

Resolves the cache instance a transfer uses: the share's ssl_scache if present, otherwise the multi's; NULL when neither exists.

A resolved instance failing the magic check is reported via failf, triggers DEBUGASSERT, and yields NULL, denying cache use.

**Uncertainties.**

- No fallback if the share exists but has no ssl_scache and the multi has one; the multi cache is used

<a id="u-7f92c9c72254"></a>
### `cf_ssl_scache_match_auth`

`static bool cf_ssl_scache_match_auth(struct Curl_ssl_scache_peer *peer, struct ssl_fi…` · [lib/vtls/vtls_scache.c:L751-L764][f1]

Checks whether a peer slot's authentication material matches a connection config.

With a NULL config it matches only slots lacking clientcert and key_passwd. Otherwise clientcert is compared with Curl_safecmp and key_passwd with Curl_timestrcmp (constant-time); either mismatch rejects the slot.

<a id="u-0b8cb2adaf0b"></a>
### `ssl_peer_key_add_transport`

`static CURLcode ssl_peer_key_add_transport(struct dynbuf *buf, uint8_t transport)` · [lib/vtls/vtls_scache.c:L187-L202][f1]

Appends a transport marker to the peer key.

TCP adds nothing (default), UDP/QUIC/UNIX add fixed tags; other transports add ':TRNSPRT-<n>'.

<a id="u-dc43f29cfd62"></a>
### `ssl_peer_key_add_vrfy`

`static CURLcode ssl_peer_key_add_vrfy(struct dynbuf *buf, struct ssl_filter_config *s…` · [lib/vtls/vtls_scache.c:L204-L234][f1]

Encodes verification settings affecting session reuse: ':NO-VRFY-PEER' when verifypeer is off, ':NO-VRFY-HOST' when verifyhost is off, ':VRFY-STATUS' when verifystatus is on.

When either peer or host verification is off and the connect origin differs from the peer hostname, it appends the connect host and port (CHOST/CPORT), since such sessions must not be reused for other hosts.

<a id="u-5e052568d6d4"></a>
### `ssl_peer_key_build`

`static CURLcode ssl_peer_key_build(struct ssl_filter_config *ssl, const struct ssl_pe…` · [lib/vtls/vtls_scache.c:L236-L352][f1]

Assembles the complete peer key in a 10 KiB dynbuf: 'hostname:port:KEY-V2', then transport, verification markers, TLS version range (version_max high 16 bits), ssl_options, cipher lists (TLS 1.2/1.3), curves, sigalgs; CA/CApath/CRL/issuer paths and CA/issuer blobs only when verifypeer is on; cert blob hash and pinned key; mTLS identity; backend tls_id as IMPL.

Missing/empty tls_id fails with CURLE_FAILED_INIT. Final suffix is ':L' if any path was added non-absolutely, else ':G'. On any error the buffer is freed and *ppeer_key stays NULL; success yields a NUL-terminated string owned by the caller.

<a id="u-6de6c5892e5b"></a>
### `Curl_ssl_scache`

`struct Curl_ssl_scache` · [lib/vtls/vtls_scache.c:L362-L373][f1]

The TLS session cache: fixed-size peer-slot array, global age counter for LRU-style replacement, default session lifetime (one day, set at creation), and optional mutex-based locking state.

Instances are magic-guarded via GOOD_SCACHE; destroy clears the magic first so a destroyed cache is rejected.

<a id="u-86dccb8b7122"></a>
### `Curl_ssl_scache_peer`

`struct Curl_ssl_scache_peer` · [lib/vtls/vtls_scache.c:L47-L60][f1]

One peer slot in the session cache: identifying peer key string, mTLS auth material (clientcert, key_passwd), the session list, a caller-owned opaque object, export salt+HMAC, and recency/limits fields.

ssl_peer_key is NULL for entries known only by salt+hmac (imported); hmac_set marks those. exportable is recomputed whenever key or auth material changes.

**Notes.**

- field: max_sessions and the sessions list destructor are initialized by Curl_ssl_scache_create, not by this struct definition.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/vtls_scache.c
