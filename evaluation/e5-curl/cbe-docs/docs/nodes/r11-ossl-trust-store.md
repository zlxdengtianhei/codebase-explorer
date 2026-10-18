# trust store management

**Capability.** Building, populating and caching X509 verification stores from CA files/blobs and Windows system stores, with TTL/config-change-aware caching on the multi handle.

Curl_ssl_setup_x509_store decides between a cached and a freshly populated store; ossl_populate_x509_store and ossl_load_trust_anchors do the loading, including Windows ROOT/CA stores. Use the cached_* predicates and share destructor to understand cache invalidation.

**Depends on.**

- [client cert, key, engine and provider config](r11-ossl-cert-key-config.md) · model-inferred · 0 edge(s)

Parent: [TLS backends \(OpenSSL-based\)](r11-tls-security.md)

## Units (12)

<a id="u-31071a2ced40"></a>
### `openssl.c-load-cacert`

`static CURLcode load_cacert_from_memory(X509_STORE *store, const struct curl_blob *ca…` · [lib/vtls/openssl.c:L2733-L2794][f1]

placeholder

<a id="u-63d24e2f70da"></a>
### `Curl_ssl_setup_x509_store`

`CURLcode Curl_ssl_setup_x509_store(struct Curl_cfilter *cf, struct Curl_easy *data, s…` · [lib/vtls/openssl.c:L3318-L3355][f1]

Ensures the SSL_CTX has a populated verification store, using the multi-handle cache when allowed.

The store is cacheable when a nonzero CA cache timeout is set, peer verification is on, and no CA blob, CRL file or native CA store is involved. It marks the OpenSSL error queue with ERR_set_mark for the duration. On a cache hit whose store can be up-ref'd, it installs the cached store and copies its emptiness flag; otherwise it populates the SSL_CTX's own store via ossl_populate_x509_store and, when cacheable, records it in the cache. Errors from population propagate; the error mark is always popped.

calls: [ossl_get_cached_x509_store](r11-ossl-trust-store.md#u-844c244cd94d), [ossl_set_cached_x509_store](r11-ossl-trust-store.md#u-6f6d00a1db2b), [ossl_populate_x509_store](r11-ossl-trust-store.md#u-228203bf0e7d)

<a id="u-228203bf0e7d"></a>
### `ossl_populate_x509_store`

`static CURLcode ossl_populate_x509_store(struct Curl_cfilter *cf, struct Curl_easy *d…` · [lib/vtls/openssl.c:L3096-L3163][f1]

Fully configures a verification store: a missing store is CURLE_OUT_OF_MEMORY, and peer verification disabled returns OK immediately leaving the store untouched.

It loads anchors via ossl_load_trust_anchors (propagating errors). With Apple SecTrust a CRL file combined with the native store is rejected as CURLE_NOT_BUILT_IN (the platform verifier has no CRL attachment API). A configured CRL file is loaded as a PEM X509 lookup (failure is CURLE_SSL_CRL_BADFILE) and enables X509_V_FLAG_CRL_CHECK | CRL_CHECK_ALL. X509_V_FLAG_TRUSTED_FIRST is always set; X509_V_FLAG_PARTIAL_CHAIN is added unless no_partialchain is set or a CRL check is active (OpenSSL bug 5081 prevents the combination). Flags are applied ignoring the return value.

calls: [ossl_load_trust_anchors](r11-ossl-trust-store.md#u-4020db23c9ae)

<a id="u-4020db23c9ae"></a>
### `ossl_load_trust_anchors`

`static CURLcode ossl_load_trust_anchors(struct Curl_cfilter *cf, struct Curl_easy *da…` · [lib/vtls/openssl.c:L2986-L3094][f1]

Fills an X509_STORE with trust anchors, tracking emptiness in octx->store_is_empty.

CURLOPT_CAINFO_BLOB suppresses CAfile use. A requested native CA store loads Windows ROOT+CA anchors (clearing the empty flag when anything was added) or, on Apple, flags a native verifier instead of loading anchors. A CA blob is imported via load_cacert_from_memory, failing hard with CURLE_SSL_CACERT_BADFILE on any error; success clears the empty flag. CAfile/CApath are loaded per-platform (X509_STORE_load_file/load_path on OpenSSL 3, load_locations otherwise): a load failure is fatal (CURLE_SSL_CACERT_BADFILE) only when the store is still empty and there is no native verifier; otherwise it logs and continues, and any successful source clears the empty flag. Under CURL_CA_FALLBACK an empty store falls back to OpenSSL's built-in default paths; a still-empty store without a native check logs that no anchors are configured.

calls: [load_cacert_from_memory](r11-ossl-trust-store.md#u-965002b761f6), [ossl_windows_load_anchors](r11-ossl-trust-store.md#u-7794ff6c53a0)

<a id="u-965002b761f6"></a>
### `load_cacert_from_memory`

> **ID corrected by CBE.** CBE changed the unit ID from ` lib/vtls/openssl.c::function::load_cacert_from_memory::2794-placeholder ` to the inventory ID ` lib/vtls/openssl.c::function::load_cacert_from_memory::79788 `. The model wrote this body under the wrong ID; it may be inaccurate.

`static CURLcode load_cacert_from_memory(X509_STORE *store, const struct curl_blob *ca…` · [lib/vtls/openssl.c:L2733-L2794][f1]

placeholder

<a id="u-ed4595a165a6"></a>
### `ossl_win_load_store`

`static CURLcode ossl_win_load_store(struct Curl_easy *data, struct Curl_cfilter *cf, …` · [lib/vtls/openssl.c:L2797-L2947][f1]

Imports eligible CA certificates from a Windows system store (e.g. ROOT or CA) into an X509_STORE, Windows crypto only.

It opens the named store; if that fails it returns OK with *padded FALSE. It enumerates every certificate context, skipping: contexts without encoded data, certificates not yet valid or expired (FileTime comparison against now), certificates whose key usage exists but lacks the cert-sign bit (or whose key-usage query errors), and certificates whose enhanced key usage does not include the server-auth OID 1.3.6.1.5.5.7.3.1 (unless CRYPT_E_NOT_FOUND, meaning all uses allowed). The EKU buffer is grown with realloc as needed; an allocation failure is the only hard error (CURLE_OUT_OF_MEMORY, breaking the loop). Surviving certificates are decoded with d2i_X509 and added with X509_STORE_add_cert; add failures (e.g. duplicates) are skipped silently, successful adds set *padded. All resources are released on exit and the totals traced.

**Uncertainties.**

- CertEnumCertificatesInStore's final NULL context is freed via CertFreeCertificateContext, relying on documented behavior that the enumerated context is freed by the call returning NULL? The code frees pContext explicitly; whether that double-frees depends on the Windows API contract and is not verifiable here

<a id="u-7794ff6c53a0"></a>
### `ossl_windows_load_anchors`

`static CURLcode ossl_windows_load_anchors(struct Curl_cfilter *cf, struct Curl_easy *…` · [lib/vtls/openssl.c:L2949-L2982][f1]

Loads Windows trust anchors from the ROOT and CA system stores in order, Windows crypto only.

For each store it calls ossl_win_load_store; a hard error returns immediately. A store that contributed certificates sets *padded and is traced; an empty store logs that importing failed but continues. Returns the last result.

<a id="u-844c244cd94d"></a>
### `ossl_get_cached_x509_store`

`static X509_STORE *ossl_get_cached_x509_store(struct Curl_cfilter *cf, struct Curl_ea…` · [lib/vtls/openssl.c:L3230-L3251][f1]

Returns the multi-handle-cached X509_STORE when it exists, has a store, is not expired, and matches the current CA configuration; otherwise NULL.

*pempty is set from the cached share's emptiness on a hit, and preset TRUE on every miss or absence of a multi handle.

<a id="u-6f6d00a1db2b"></a>
### `ossl_set_cached_x509_store`

> **ID corrected by CBE.** CBE changed the unit ID from ` lib/vtls/openssl.c::function::ossl_set_cached_x509_store::96360-placeholder ` to the inventory ID ` lib/vtls/openssl.c::function::ossl_set_cached_x509_store::97127 `. The model wrote this body under the wrong ID; it may be inaccurate.

`static void ossl_set_cached_x509_store(struct Curl_cfilter *cf, struct Curl_easy *dat…` · [lib/vtls/openssl.c:L3253-L3316][f1]

placeholder

<a id="u-0bcc4d54dd2b"></a>
### `ossl_cached_x509_store_expired`

`static bool ossl_cached_x509_store_expired(struct Curl_easy *data, const struct ossl_…` · [lib/vtls/openssl.c:L3192-L3203][f1]

Reports whether a cached X509 store has outlived its TTL.

A negative ssl_ca_cache_timeout disables expiry entirely (returns FALSE); otherwise elapsed time since the share's timestamp must stay below timeout seconds.

<a id="u-adeb4c7c3a0e"></a>
### `ossl_cached_x509_store_different`

`static bool ossl_cached_x509_store_different(struct Curl_cfilter *cf, const struct Cu…` · [lib/vtls/openssl.c:L3205-L3228][f1]

Reports whether the cached store was built under different CA settings than the current filter config: a changed no_partialchain flag, or a changed CAfile/CApath.

NULL pointers are compared by identity (both NULL match); non-NULL pairs by strcmp.

<a id="u-0824af75f8c0"></a>
### `oss_x509_share_free`

`static void oss_x509_share_free(const void *key, size_t key_len, void *p)` · [lib/vtls/openssl.c:L3177-L3190][f1]

Hash-entry destructor for a cached X509 store share: frees the X509_STORE, both cached path strings and the share struct itself.

Debug-build assertions check the key is the expected x509-share key.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/openssl.c
