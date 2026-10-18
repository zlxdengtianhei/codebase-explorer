# Schannel certificates and caching

**Capability.** Certificate inspection and cross-connection caching: traversing the peer certificate store for certinfo, computing CryptoAPI checksums, and sharing a CA certificate store via the multi handle's hash.

Consult when dealing with peer certificate information or CA-store reuse. traverse_cert_store feeds certinfo; the cached-cert-store pair stores and retrieves the shared store in the multi's protocol hash.

**Depends on.**

- [Schannel handshake and credentials](r4-schannel-handshake.md) · model-inferred · 0 edge(s)

Parent: [Schannel TLS backend](r4-schannel-tls.md)

## Units (6)

<a id="u-761fa9168afc"></a>
### `schannel.c-certinfo-support`

`struct Adder_args` · [lib/vtls/schannel.c:L1542-L1547][f1]

Residual declarations around the certificate-traversal helpers: the Read_crt_func callback typedef and the Adder_args struct carrying the Curl_easy pointer, current index, total count, and first error for add_cert_to_certinfo.

Non-behavioral scaffolding.

uses: [traverse_cert_store](r4-schannel-certs-cache.md#u-ade86c33b91f)

<a id="u-3e983809aab3"></a>
### `schannel.c-trivial-backend-helpers`

`static void schannel_cleanup(void)` · [lib/vtls/schannel.c:L2646-L2649][f1]

Small backend callbacks folded together.

schannel_cleanup tears down the global SSPI layer; schannel_version writes the literal 'Schannel'; schannel_random forwards to curlx_win32_random; schannel_sha256sum delegates to schannel_checksum with PROV_RSA_AES and CALG_SHA_256; schannel_get_internals returns the address of the SSPI context handle, ignoring the requested info and dereferencing the backend context without a NULL check.

calls: [schannel_checksum](r4-schannel-certs-cache.md#u-a9a54d0d0789)

<a id="u-178b053170b3"></a>
### `Curl_schannel_get_cached_cert_store`

`HCERTSTORE Curl_schannel_get_cached_cert_store(struct Curl_cfilter *cf, struct Curl_e…` · [lib/vtls/schannel.c:L2749-L2811][f1]

Returns a shared CA certificate store from the multi handle's protocol hash when it is still valid, or NULL.

It fails when there is no multi handle, no cached share with a store, or when ssl_ca_cache_timeout is zero (caching fully disabled). A nonnegative timeout means the entry expires once the elapsed time since it was stored reaches the timeout; a negative timeout retains it forever. Validity also requires the CA source to match: for a ca_info_blob, the cached blob size and SHA-256 digest (computed via schannel_sha256sum, with a hashing failure treated as a miss) must be identical; otherwise the cached CAfile string must equal the configured CAfile.

calls: [schannel.c-trivial-backend-helpers](r4-schannel-certs-cache.md#u-3e983809aab3)

<a id="u-6146f39939a2"></a>
### `Curl_schannel_set_cached_cert_store`

`bool Curl_schannel_set_cached_cert_store(struct Curl_cfilter *cf, struct Curl_easy *d…` · [lib/vtls/schannel.c:L2827-L2893][f1]

Stores a certificate store in the multi's shared cache for reuse across connections, returning FALSE when there is no multi handle, when hashing a CA blob fails, or on allocation or hash-insertion failure.

For a CA blob it records the SHA-256 digest and length; for a CAfile it stores a duplicated copy of the path. An existing share entry is reused (freed via schannel_cert_share_free when evicted), the previous store is closed with CertCloseStore, and the new store plus a fresh timestamp replace the cached values.

calls: [schannel.c-trivial-backend-helpers](r4-schannel-certs-cache.md#u-3e983809aab3); contract: [Curl_schannel_get_cached_cert_store](r4-schannel-certs-cache.md#u-178b053170b3)

**Uncertainties.**

- Ownership of the passed cert_store transfers to the cache on success; whether the caller must still close it on a FALSE return is not established by this file.

<a id="u-a9a54d0d0789"></a>
### `schannel_checksum`

`static CURLcode schannel_checksum(const unsigned char *input, size_t inputlen, unsign…` · [lib/vtls/schannel.c:L2664-L2728][f1]

Computes a CryptoAPI hash of the input into the caller's buffer using the given provider type and algorithm id.

The output buffer is zeroed first so no stale data can be returned. CryptAcquireContext (verify-context, silent) and CryptCreateHash failures leave the initial CURLE_FAILED_INIT; input larger than 4 GiB is hashed in chunks, with CryptHashData failure jumping to cleanup where the hash and provider handles are always released. An oversized output buffer versus the actual hash size fails; success requires CryptGetHashParam(HP_HASHVAL) to fill exactly the reported hash size, yielding CURLE_OK, otherwise CURLE_BAD_FUNCTION_ARGUMENT persists from the post-create point.

uses: [schannel.c-trivial-backend-helpers](r4-schannel-certs-cache.md#u-3e983809aab3)

<a id="u-ade86c33b91f"></a>
### `traverse_cert_store`

`static void traverse_cert_store(const CERT_CONTEXT *context, Read_crt_func func, void…` · [lib/vtls/schannel.c:L1505-L1529][f1]

Enumerates all certificates in the remote certificate's store, invoking the caller's callback per certificate until the callback returns FALSE or enumeration ends.

On the first item it compares the remote context's pbCertEncoded pointer with the enumerated one to detect leaf-to-root enumeration order (Windows 11 22H2+) versus root-to-leaf, passing a reverse_order flag to the callback so callers can index consistently. The last enumerated context is freed before returning. valid_cert_encoding in the same scope gates both callbacks: a certificate counts only when it has X509 encoding, a data pointer, and nonzero length. cert_counter_callback increments the count and stops enumeration past MAX_ALLOWED_CERT_AMOUNT. add_cert_to_certinfo extracts each valid certificate via Curl_extract_certinfo at the order-corrected index, records the first error in its args, and stops the traversal on error.

uses: [schannel_connect_step3](r4-schannel-handshake.md#u-33a3a012d6eb)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/schannel.c
