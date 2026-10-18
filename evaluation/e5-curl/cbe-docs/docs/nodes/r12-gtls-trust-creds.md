# GnuTLS trust store and shared credentials

**Capability.** Builds and shares client trust anchors: per-multi-handle cached credential objects with refcounting, expiry and CAfile comparison, file loading, and credential population.

Read when changing CA/CRL loading or caching semantics. Curl_gtls_client_trust_setup decides between cached and freshly populated credentials.

**Depended on by.**

- [GnuTLS connect and record IO](r12-gtls-connect-io.md) · model-inferred · 0 edge(s)

Parent: [GnuTLS backend](r12-gtls-backend.md)

## Units (11)

<a id="u-f2861cb7fcb3"></a>
### `Curl_gtls_client_trust_setup`

`CURLcode Curl_gtls_client_trust_setup(struct Curl_cfilter *cf, struct Curl_easy *data…` · [lib/vtls/gtls.c:L652-L697][f1]

Establishes the client trust store for a GnuTLS session, using a cache when eligible.

The store is cacheable only when ssl_ca_cache_timeout is nonzero, verifypeer is on, and no CApath, CA blob, CRLfile, native CA store, or client cert is configured. When a valid cached entry exists and can be up-ref'd, it replaces gtls->shared_creds with it and sets it on the session via gnutls_credentials_set (failure yields CURLE_SSL_CONNECT_ERROR); otherwise it populates fresh credentials with gtls_populate_creds, marks trust_setup, and caches the object when cacheable.

calls: [gtls_get_cached_creds](r12-gtls-trust-creds.md#u-45a129e50e00), [gtls_set_cached_creds](r12-gtls-trust-creds.md#u-11c0b5e7e0e2), [gtls_populate_creds](r12-gtls-trust-creds.md#u-3cc1312cca98)

<a id="u-0ae8a78bdbd1"></a>
### `Curl_gtls_shared_creds_create`

`CURLcode Curl_gtls_shared_creds_create(struct Curl_easy *data, struct gtls_shared_cre…` · [lib/vtls/gtls.c:L396-L419][f1]

Allocates a zeroed gtls_shared_creds with refcount 1, timestamped from Curl_pgrs_now, plus the underlying GnuTLS certificate credentials.

Returns CURLE_OUT_OF_MEMORY if the struct allocation fails; on credential allocation failure it logs the GnuTLS error, frees the struct and returns CURLE_SSL_CONNECT_ERROR.

<a id="u-f01b938c2f77"></a>
### `Curl_gtls_shared_creds_free`

`void Curl_gtls_shared_creds_free(struct gtls_shared_creds **pcreds)` · [lib/vtls/gtls.c:L431-L443][f1]

Down-references and clears the caller's credentials pointer; when the refcount reaches zero it frees the GnuTLS credentials, the cached CAfile string and the struct.

Nulls the caller pointer first and does nothing if it held NULL.

<a id="u-51f2d4aadba5"></a>
### `Curl_gtls_shared_creds_up_ref`

`CURLcode Curl_gtls_shared_creds_up_ref(struct gtls_shared_creds *creds)` · [lib/vtls/gtls.c:L421-L429][f1]

Increments the shared-credentials refcount and returns CURLE_OK; returns CURLE_BAD_FUNCTION_ARGUMENT if the refcount is already SIZE_MAX.

<a id="u-45a129e50e00"></a>
### `gtls_get_cached_creds`

`static struct gtls_shared_creds *gtls_get_cached_creds(struct Curl_cfilter *cf, struc…` · [lib/vtls/gtls.c:L592-L608][f1]

Looks up the shared trust-anchor entry under MPROTO_GTLS_X509_KEY in the multi handle's proto_hash and returns it only if present with credentials, not expired, and matching the current CAfile; otherwise returns NULL.

calls: [gtls_shared_creds_expired](r12-gtls-trust-creds.md#u-ad96b2d69f31), [gtls_shared_creds_different](r12-gtls-trust-creds.md#u-ab77851ce5df)

<a id="u-11c0b5e7e0e2"></a>
### `gtls_set_cached_creds`

`static void gtls_set_cached_creds(struct Curl_cfilter *cf, struct Curl_easy *data, st…` · [lib/vtls/gtls.c:L621-L650][f1]

Publishes a fresh shared-creds object in the multi handle's proto_hash for reuse.

With no multi handle it does nothing. It dup's the current CAfile onto the object (bailing on allocation failure), up-refs it, and adds it to the hash with gtls_shared_creds_hash_free as the cleanup callback; on hash-insert failure it down-refs again, so the object is freed when its remaining reference goes away. The hash-free callback asserts the stored key matches the constant and frees the entry by down-referencing.

<a id="u-ab77851ce5df"></a>
### `gtls_shared_creds_different`

`static bool gtls_shared_creds_different(struct Curl_cfilter *cf, const struct gtls_sh…` · [lib/vtls/gtls.c:L582-L590][f1]

Compares a cached shared-creds entry against the current filter's CAfile: if either side has no CAfile string they differ exactly when the pointers differ; otherwise they differ when strcmp is nonzero.

<a id="u-ad96b2d69f31"></a>
### `gtls_shared_creds_expired`

`static bool gtls_shared_creds_expired(struct Curl_easy *data, const struct gtls_share…` · [lib/vtls/gtls.c:L570-L580][f1]

Reports whether a shared-credentials entry is stale: a negative ssl_ca_cache_timeout means never expire; otherwise expired when the elapsed milliseconds since the entry timestamp reach the timeout in seconds.

<a id="u-3cc1312cca98"></a>
### `gtls_populate_creds`

`static CURLcode gtls_populate_creds(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/vtls/gtls.c:L445-L565][f1]

Fills GnuTLS certificate credentials with trust anchors and CRLs.

If verifypeer is off it returns immediately with no trust material. Otherwise it loads sources in order: the native CA store (under Apple SecTrust it only marks creds non-empty; otherwise gnutls system trust, logging read errors and continuing); the CA blob, rejecting blobs larger than UINT_MAX with CURLE_SSL_CACERT_BADFILE; or, when no blob is set, the CAfile (also enabling V1 CA verification); then the CApath directory. Each CA-source read failure sets certverifyresult and returns CURLE_SSL_CACERT_BADFILE only when no other source produced certificates, else it continues with a warning. On Apple SecTrust builds a CRLfile with the native store fails with CURLE_NOT_BUILT_IN; other CRLfile read errors return CURLE_SSL_CRL_BADFILE.

calls: [Curl_gtls_client_trust_setup](r12-gtls-trust-creds.md#u-f2861cb7fcb3)

<a id="u-e170b11e97b1"></a>
### `load_file`

`static gnutls_datum_t load_file(const char *file)` · [lib/vtls/gtls.c:L198-L228][f1]

Loads a whole file into a heap-allocated gnutls_datum_t.

It opens in binary mode, sizes the file with fseek/ftell, rejects negative sizes and sizes over CURL_MAX_INPUT_LENGTH, then mallocs and reads. On fopen failure, seek failure, size rejection, or allocation failure it returns an empty datum; a short read frees the buffer and also returns empty. The file is always closed.

<a id="u-5d62deb1871b"></a>
### `gnutls_do_file_type`

`static gnutls_x509_crt_fmt_t gnutls_do_file_type(const char *type)` · [lib/vtls/gtls.c:L303-L312][f1]

Maps a certificate-type string to a GnuTLS format: NULL, empty, unknown values, and 'PEM' yield GNUTLS_X509_FMT_PEM; only a case-insensitive 'DER' yields GNUTLS_X509_FMT_DER.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/gtls.c
