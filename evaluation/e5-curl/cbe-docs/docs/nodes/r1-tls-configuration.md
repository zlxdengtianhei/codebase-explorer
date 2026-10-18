# TLS Configuration Management

**Capability.** Owns the SSL configuration structs' lifecycle: defaults, temp sharing of easy-handle values for matching, deep cloning onto connections, cleanup, connection-cache matching, live verification updates, and the ssl_peer identity description in vtls.h.

Use this to understand how TLS settings move from the easy handle onto a reusable connection. The conn_config_* functions are the public surface; blobdup/blobcmp and the clone/match helpers implement the underlying deep-copy and equivalence semantics.

Parent: [curl Codebase](r1-curl-codebase.md)

## Units (15)

<a id="u-35293302c4e9"></a>
### `openssl.c-ctx-init`

`group`

placeholder

<a id="u-ac433892bf97"></a>
### `ssl_peer`

`struct ssl_peer` · [lib/vtls/vtls.h:L97-L104][f1]

Defines struct ssl_peer, the identity description a TLS filter uses for one connection: origin (the authority being talked to), peer (the actual machine), a heap-allocated SNI string or NULL when unusable, a session-cache lookup key, a type enum distinguishing DNS/IPv4/IPv6 peer data, and a transport tag using TRNSPRT_* values.

Pure data layout; lifetime is managed by Curl_ssl_peer_init/Curl_ssl_peer_cleanup declared later in the same header.

<a id="u-8654d3d7ce7b"></a>
### `Curl_ssl_config_cleanup`

`void Curl_ssl_config_cleanup(struct ssl_filter_config *sslc)` · [lib/vtls/vtls_config.c:L111-L138][f2]

Frees all owned heap strings and blobs of an ssl_filter_config, but only when sslc->deep_copy is set; shallow configs that merely borrow easy-handle references are left untouched.

Frees CApath, CAfile, issuercert, clientcert, cipher lists, pinned_key, cert/ca/issuer/key blobs, curves, signature algorithms, CRLfile, cert/key type and passwd strings, and under USE_ECH the ech_config/ech_public, then clears deep_copy. Graph evidence linking these frees to fwrite_xattr reflects the curlx_safefree macro expansion and is not a real call.

**Notes.**

- side_effect: Only the deep_copy flag guards freeing; calling it on a shallow config leaks nothing but frees nothing.

<a id="u-5974e86d3042"></a>
### `Curl_ssl_config_init`

`void Curl_ssl_config_init(struct ssl_easy_config *sslc)` · [lib/vtls/vtls_config.c:L100-L109][f2]

Resets an ssl_easy_config to libcurl defaults: peer and host verification enabled and session caching on, reflecting the 7.10 change to verify by default.

No allocation, no failure path.

<a id="u-5a7e07fe783c"></a>
### `Curl_ssl_conn_config_cleanup`

`void Curl_ssl_conn_config_cleanup(struct connectdata *conn)` · [lib/vtls/vtls_config.c:L445-L451][f2]

Releases a connection's owned SSL configuration by running Curl_ssl_config_cleanup on both the primary and (when proxy support is compiled in) proxy ssl_filter_config members.

No-op freeing occurs for shallow configs per the cleanup's deep_copy guard.

calls: [Curl_ssl_config_cleanup](r1-tls-configuration.md#u-8654d3d7ce7b)

<a id="u-01bf0746cb06"></a>
### `Curl_ssl_conn_config_clone`

`CURLcode Curl_ssl_conn_config_clone(struct ssl_filter_config *ssl_config, struct ssl_…` · [lib/vtls/vtls_config.c:L426-L443][f2]

Clones the primary (and proxy, if provided) filter configs from a temporary into a connectdata so the connection owns copies that can outlive the easy handle.

Failure of either clone_ssl_primary_config returns CURLE_OUT_OF_MEMORY; without proxy support the proxy argument is ignored. Returns CURLE_OK on success.

calls: [clone_ssl_primary_config](r1-tls-configuration.md#u-0e127d441f1b)

**Uncertainties.**

- On proxy-clone failure the already-cloned primary config is left populated on the connection; cleanup responsibility is not visible here.

<a id="u-827fd96840eb"></a>
### `Curl_ssl_conn_config_match`

`bool Curl_ssl_conn_config_match(struct Curl_easy *data, struct ssl_filter_config *con…` · [lib/vtls/vtls_config.c:L181-L195][f2]

Dispatches primary-config matching for connection-cache lookup: when built with proxy support and proxy is true, the candidate's proxy_ssl_config is compared; otherwise its ssl_config is compared.

Comparison itself is match_ssl_primary_config's full field-by-field equality.

calls: [match_ssl_primary_config](r1-tls-configuration.md#u-41466868370f)

<a id="u-69e1eda38557"></a>
### `Curl_ssl_conn_config_update`

`void Curl_ssl_conn_config_update(struct Curl_easy *data, bool for_proxy)` · [lib/vtls/vtls_config.c:L453-L474][f2]

Pushes changed easy-handle verification settings onto the current connection's live filter config: verifyhost, verifypeer, verifystatus, and ech under USE_ECH are copied from set.proxy_ssl or set.ssl depending on for_proxy (or always set.ssl without proxy support).

If data->conn is NULL the call does nothing, as the comment notes it may run before a connection exists.

<a id="u-5f320c9e53b0"></a>
### `Curl_ssl_filter_config_tmp_init`

`CURLcode Curl_ssl_filter_config_tmp_init( struct Curl_easy *data, struct Curl_peer *o…` · [lib/vtls/vtls_config.c:L272-L424][f2]

Populates temporary ssl_filter_config instances for the connection origin and its proxy from the easy handle's set.ssl / set.proxy_ssl, sharing (not copying) strings and blobs so matching can use them.

For the primary origin it first applies complementary options, then, unless the backend is SCHANNEL: under USE_APPLE_SECTRUST or CURL_CA_NATIVE enables native_ca_store when no custom CA path/file/blob is set, and under CURL_CA_PATH/CURL_CA_BUNDLE sets the default CA path/bundle on the easy handle via Curl_setstropt when not already set, propagating any setstropt error as the return value. It copies version/verify/session fields and steals the CAfile, CRLfile, CApath, cipher lists, signature algorithms, CA blob, curves, issuercert and its blob. Client credential fields (pinned_key, cert blob/type, key, key type/passwd, clientcert, key blob, ECH settings) are filled only when the origin equals data->state.initial_origin; for other origins they are explicitly NULLed. Under proxy support the same sequence runs for ssl_proxy using the *_PROXY strings and blobs, with ECH always disabled; without proxy support ssl_proxy is unused. Returns CURLE_OK unless a setstropt default-CA assignment fails.

**Notes.**

- side_effect: Curl_setstropt calls mutate the easy handle's string table to install compiled-in CA defaults; these persist beyond this function.
- condition: The SCHANNEL backend check skips all built-in CA defaults because SCHANNEL uses the native certificate store.

calls: [ssl_easy_config_compl_options](r1-tls-configuration.md#u-d225d57bba78), [ssl_easy_steal](r1-tls-configuration.md#u-d2e5f797ef24); uses: [module_residual::::104-244][f1]

**Uncertainties.**

- CURL_UNCONST borrowing means these configs dangle if the easy handle's options change or are freed before the connection config is consumed.

<a id="u-2de1a266c63b"></a>
### `blobcmp`

`static bool blobcmp(struct curl_blob *first, struct curl_blob *second)` · [lib/vtls/vtls_config.c:L89-L98][f2]

Compares two curl_blobs for identity: both NULL are equal, exactly one NULL unequal, differing lengths unequal, otherwise a memcmp of the data decides.

Returns TRUE only for full byte equality.

**Uncertainties.**

- Assumes non-NULL blobs have non-NULL data; a blob with len>0 and NULL data would crash in memcmp.

<a id="u-21a66a68bd3b"></a>
### `blobdup`

`static CURLcode blobdup(struct curl_blob **dest, struct curl_blob *src)` · [lib/vtls/vtls_config.c:L67-L86][f2]

Deep-copies a curl_blob into a single allocation holding the struct and its data contiguously.

If src is NULL the destination pointer is left untouched and CURLE_OK returned; on malloc failure CURLE_OUT_OF_MEMORY is returned. The copy always uses CURL_BLOB_COPY so the data outlives the easy handle that supplied it. DEBUGASSERT asserts dest is non-NULL and *dest currently NULL.

<a id="u-0e127d441f1b"></a>
### `clone_ssl_primary_config`

`static bool clone_ssl_primary_config(struct ssl_filter_config *source, struct ssl_fil…` · [lib/vtls/vtls_config.c:L197-L242][f2]

Deep-copies one ssl_filter_config into another for storage on a connection that may outlive the easy handle.

Copies all scalar fields (version bounds, verify flags, ssl_options, native_ca_store, cache_session, auto_client_cert, earlydata, beast/partialchain/revoke options), then duplicates the four blobs via CLONE_BLOB and the strings (CApath, CAfile, issuercert, cipher lists, pinned_key, curves, signature_algorithms, CRLfile, clientcert, cert/key type, key_passwd, key blob) via CLONE_STRING; under USE_ECH also ech mode and both ech strings. Sets deep_copy=TRUE first; any strdup or blobdup allocation failure returns FALSE immediately, leaving the destination partially populated and still marked deep_copy so cleanup can free it. DEBUGASSERT refuses a destination that is already a deep copy.

**Uncertainties.**

- On mid-copy failure the destination is left with a mix of copied and NULL fields; whether callers must still run cleanup is not visible here.

<a id="u-41466868370f"></a>
### `match_ssl_primary_config`

`static bool match_ssl_primary_config(struct Curl_easy *data, struct ssl_filter_config…` · [lib/vtls/vtls_config.c:L140-L179][f2]

Decides whether two ssl_filter_config instances are equivalent for connection reuse.

Numeric/boolean fields (version, version_max, ssl_options, native_ca_store, verifypeer/verifyhost/verifystatus, auto_client_cert, and ech under USE_ECH) must match exactly; strings are compared case-insensitively via Curl_safecmp/curl_strequal, key_passwd with Curl_timestrcmp (constant-time), and the four blobs with blobcmp. All comparisons are ANDed; any mismatch returns FALSE. The data parameter is unused.

calls: [blobcmp](r1-tls-configuration.md#u-2de1a266c63b)

<a id="u-d225d57bba78"></a>
### `ssl_easy_config_compl_options`

`static void ssl_easy_config_compl_options(struct Curl_peer *origin, struct Curl_peer …` · [lib/vtls/vtls_config.c:L244-L263][f2]

Derives the option bitfields of a filter config directly from sslc->ssl_options: native_ca_store, earlydata, enable_beast, no_partialchain, no_revoke, revoke_best_effort each become the corresponding CURLSSLOPT_* bit.

auto_client_cert additionally requires that origin equals initial_origin (compared with Curl_peer_equal), so the auto client-cert selection only applies to the original origin, not one changed by redirects. Passing NULL peers (as the proxy path does) makes Curl_peer_equal's NULL-handling decide auto_client_cert.

calls: [Curl_peer_equal](r3-peer-identity.md#u-c6bb91e928c8)

**Uncertainties.**

- Behavior of Curl_peer_equal when both arguments are NULL is defined in lib/peer.c, not shown here.

<a id="u-d2e5f797ef24"></a>
### `ssl_easy_steal`

`static char *ssl_easy_steal(struct Curl_easy *data, enum dupstring id)` · [lib/vtls/vtls_config.c:L265-L270][f2]

Returns an un-consted borrowed pointer to an easy-handle string (via CURL_EASY_STR) instead of duplicating it, per the in-code comment acknowledging this is for connection matching only.

The returned pointer shares lifetime with the easy handle's set.* storage; no allocation or failure path.

**Uncertainties.**

- Whether callers ever free these pointers is determined by the deep_copy flag on the owning config, set only by clone_ssl_primary_config.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/vtls.h
[f2]: ../../../../../../eval/curl-2c04412/lib/vtls/vtls_config.c
