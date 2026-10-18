# OpenSSL backend miscellany

**Capability.** Backend identity string, random bytes, SHA-256, legacy SSL-pointer accessors and OCSP capability reporting.

Use these small backend services when interfacing with the vtable surface: version reporting, RNG/digest requests, CURLINFO_TLS_SESSION internals and stapling capability. They have no cross-cutting state.

Parent: [TLS backends \(OpenSSL-based\)](r11-tls-security.md)

## Units (5)

<a id="u-8b6b7e00fd40"></a>
### `Curl_ossl_version`

`size_t Curl_ossl_version(char *buffer, size_t size)` · [lib/vtls/openssl.c:L5446-L5476][f1]

Formats the TLS backend identity string into the caller buffer.

LibreSSL prints "LibreSSL/<version>" with blanks converted to underscores; AWS-LC prints its version macro; BoringSSL prints CURL_BORINGSSL_VERSION if defined, else just "BoringSSL"; OpenSSL 3+ prints "OpenSSL/<version string>". Returns the written length.

<a id="u-2507cfd1842f"></a>
### `ossl_random`

`static CURLcode ossl_random(struct Curl_easy *data, unsigned char *entropy, size_t le…` · [lib/vtls/openssl.c:L5479-L5494][f1]

Fills a buffer with RAND_bytes output.

With a data handle it first seeds via ossl_seed (failure is CURLE_FAILED_INIT); with a NULL handle it requires RAND_status directly. RAND_bytes returning anything but 1 is CURLE_FAILED_INIT. Safe with a NULL easy handle.

<a id="u-5697948fee97"></a>
### `ossl_sha256sum`

`static CURLcode ossl_sha256sum(const unsigned char *input, size_t len, unsigned char …` · [lib/vtls/openssl.c:L5496-L5518][f1]

Computes a SHA-256 digest through the EVP interface.

Context creation failure is CURLE_OUT_OF_MEMORY; init failure is CURLE_FAILED_INIT; update or final failure is CURLE_BAD_FUNCTION_ARGUMENT. The last parameter is ignored.

<a id="u-ca5d0d30d586"></a>
### `ossl_get_internals`

`static void *ossl_get_internals(struct ssl_connect_data *connssl, CURLINFO info)` · [lib/vtls/openssl.c:L5529-L5537][f1]

Legacy accessor: CURLINFO_TLS_SESSION returns the SSL_CTX pointer, anything else the live SSL pointer of the connection's backend.

<a id="u-78f0f4d2ce24"></a>
### `ossl_cert_status_request`

`static bool ossl_cert_status_request(void)` · [lib/vtls/openssl.c:L5520-L5527][f1]

Reports OCSP stapling capability: TRUE unless OCSP is disabled at compile time.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/openssl.c
