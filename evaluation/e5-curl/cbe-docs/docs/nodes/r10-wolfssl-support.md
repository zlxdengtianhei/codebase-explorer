# wolfSSL Backend Support

**Capability.** Owns backend-wide helpers: global init/teardown, version and handshake reporting, pinned-key verification, RNG and SHA-256, error formatting, internals access for CURLINFO, and TLS key logging.

Use this child for wolfSSL capabilities that are not tied to one connection: process-level lifecycle, introspection, crypto helpers and keylog output.

Parent: [wolfSSL TLS Backend](r10-tls-wolfssl.md)

## Units (11)

<a id="u-46e6a3e1937a"></a>
### `wssl_init`

`static int wssl_init(void)` · [lib/vtls/wolfssl.c:L2070-L2081][f1]

Global init: opens the TLS key log when built with OPENSSL_EXTRA, then initializes wolfSSL; on success also creates the BIO method table.

Returns nonzero only when both succeed.

calls: [wssl_bio_cf_init_methods](r10-wolfssl-connect-io.md#u-6843547b1651)

<a id="u-b50322ec5a3b"></a>
### `wssl_cleanup`

`static void wssl_cleanup(void)` · [lib/vtls/wolfssl.c:L2083-L2090][f1]

Global teardown: frees the BIO method table, calls wolfSSL_Cleanup, and closes the key log when built with OPENSSL_EXTRA.

The BIO free runs regardless of BIO-chain support (it is a macro no-op without it).

<a id="u-1d3300c215f3"></a>
### `Curl_wssl_version`

`size_t Curl_wssl_version(char *buffer, size_t size)` · [lib/vtls/wolfssl.c:L2065-L2068][f1]

Writes the version string 'wolfSSL/<lib version>' into the buffer and returns the written length.

<a id="u-d4699fe2b43f"></a>
### `Curl_wssl_report_handshake`

`void Curl_wssl_report_handshake(struct Curl_easy *data, struct wssl_ctx *wssl)` · [lib/vtls/wolfssl.c:L2108-L2114][f1]

Logs the negotiated TLS version and cipher name via an info message.

The wssl parameter is unused beyond accessing the handle fields.

<a id="u-d05d04e071b4"></a>
### `Curl_wssl_verify_pinned`

`CURLcode Curl_wssl_verify_pinned(struct Curl_cfilter *cf, struct Curl_easy *data, str…` · [lib/vtls/wolfssl.c:L1548-L1608][f1]

Verifies the peer certificate's public key against the configured pinned public key, selecting the proxy or non-proxy CURLOPT value (unless proxy support is disabled).

No pinning string means success without checks. With KEEP_PEER_CERT: retrieves the peer certificate (missing: fails with SSL pinning-mismatch result), extracts its DER (failure: same), parses it via Curl_parseX509 (parse failure goes to end keeping the mismatch result), extracts the subjectPublicKeyInfo (invalid header: fails), and calls Curl_pin_peer_pubkey, setting a fail message on mismatch. Without KEEP_PEER_CERT it returns CURLE_NOT_BUILT_IN. The X509 object is always freed at end; the initial result is CURLE_OK when no pinning is configured.

**Uncertainties.**

- When Curl_parseX509 fails, the function returns CURLE_SSL_PINNEDPUBKEYNOTMATCH without a failf message; whether that is intended messaging is unclear.

<a id="u-9b862f346734"></a>
### `wssl_random`

`static CURLcode wssl_random(struct Curl_easy *data, unsigned char *entropy, size_t le…` · [lib/vtls/wolfssl.c:L2233-L2247][f1]

Fills a buffer with entropy from a fresh wolfSSL RNG.

Any of RNG init, length above UINT_MAX, block generation, or RNG free failing returns CURLE_FAILED_INIT; success returns CURLE_OK. Note the free failure is reported even though the bytes were generated.

<a id="u-1d9d0f022e46"></a>
### `wssl_sha256sum`

`static CURLcode wssl_sha256sum(const unsigned char *input, size_t len, unsigned char …` · [lib/vtls/wolfssl.c:L2249-L2268][f1]

Computes a SHA-256 digest over an arbitrarily long input by repeatedly updating with at most UINT32_MAX bytes per chunk.

Init or update/final failure returns CURLE_BAD_FUNCTION_ARGUMENT; the digest is written to sha256sum on success.

<a id="u-c1e937f8498d"></a>
### `wssl_strerror`

`static char *wssl_strerror(unsigned long error, char *buf, unsigned long size)` · [lib/vtls/wolfssl.c:L1533-L1546][f1]

Formats a wolfSSL error code into a caller buffer via wolfSSL_ERR_error_string_n (asserting size > 40).

If the buffer stays empty, writes 'Unknown error' for a nonzero code or 'No error' for zero, and returns the buffer.

<a id="u-3e1a3031a61d"></a>
### `wssl_get_internals`

`static void *wssl_get_internals(struct ssl_connect_data *connssl, CURLINFO info)` · [lib/vtls/wolfssl.c:L2270-L2277][f1]

Returns the SSL context for CURLINFO_TLS_SESSION queries and the SSL handle otherwise.

<a id="u-292fb2c9c2ac"></a>
### `wssl_log_tls12_secret`

`static void wssl_log_tls12_secret(WOLFSSL *ssl)` · [lib/vtls/wolfssl.c:L171-L208][f1]

Writes a CLIENT_RANDOM keylog line for TLS 1.2 and older using wolfSSL_get_keys.

Skips silently for other versions (TLS 1.3 and above) because the returned master secret is not directly usable there. Returns without logging if wolfSSL_get_keys fails, or if the master secret is all zero bytes, which the code attributes to curl rejecting the server certificate and aborting the handshake. Otherwise writes the keylog entry with client random and master secret.

<a id="u-4141cd7e6ca8"></a>
### `wssl_tls13_secret_callback`

`static int wssl_tls13_secret_callback(SSL *ssl, int id, const unsigned char *secret, …` · [lib/vtls/wolfssl.c:L122-L168][f1]

Maps a wolfSSL TLS 1.3 secret id to a keylog label and writes the secret to the TLS key log.

Returns 0 immediately when ssl is NULL or key logging is disabled, and for unrecognized secret ids (default case). For the recognized ids (CLIENT_EARLY_TRAFFIC_SECRET, CLIENT/SERVER_HANDSHAKE_TRAFFIC_SECRET, CLIENT/SERVER_TRAFFIC_SECRET, EARLY/EXPORTER_SECRET) it fetches the client random; if wolfSSL_get_client_random returns 0 it silently skips logging, otherwise writes via Curl_tls_keylog_write and returns 0. Only compiled with HAVE_SECRET_CALLBACK and WOLFSSL_TLS13 under OPENSSL_EXTRA.

uses: [wssl_log_tls12_secret](r10-wolfssl-support.md#u-292fb2c9c2ac)

**Uncertainties.**

- Always returns 0; whether wolfSSL expects other return values is not visible here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/wolfssl.c
