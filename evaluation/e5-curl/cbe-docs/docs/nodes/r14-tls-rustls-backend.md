# rustls Backend Registration & Misc

**Capability.** Owns the Curl_ssl backend table wiring, error mapping, small informational accessors (version, internals, data-pending, random), teardown of backend-global resources, and the internal OpenSSL backend header.

Use this subtree for the module's external surface: which features the backend advertises and which cr_* handlers are wired in. map_error and rustls_failf translate rustls results for the rest of curl.

**Depended on by.**

- [QUIC / HTTP/3 Filter \(ngtcp2\)](r14-quic-http3.md) · model-inferred · 0 edge(s)

Parent: [rustls TLS Backend](r14-tls-rustls.md)

## Units (11)

<a id="u-ab1ef2a07bc5"></a>
### `openssl-h`

`struct ossl_ctx` · [lib/vtls/openssl.h:L116-L136][f1]

Internal header for curl's OpenSSL TLS backend, guarded by USE_OPENSSL.

It includes wincrypt.h under USE_WIN32_CRYPTO only to immediately #undef X509_NAME, X509_EXTENSIONS, PKCS7_ISSUER_AND_SERIAL, PKCS7_SIGNER_INFO, OCSP_REQUEST and OCSP_RESPONSE, because wincrypt.h #defines these as LPCSTR casts and OpenSSL/LibreSSL typedef conflicting types with the same names; the comment notes each compilation unit may need the same undef between the first wincrypt include and the first OpenSSL include. It then includes the OpenSSL headers and urldata.h, and defines feature macros derived from build-time conditions: HAVE_OPENSSL3 for OpenSSL 3.0+, HAVE_BORINGSSL_LIKE for AWS-LC/BoringSSL, HAVE_KEYLOG_UPSTREAM for 3.5.0+ built-in SSLKEYLOGFILE support (when OPENSSL_NO_SSLKEYLOG is not defined), HAVE_KEYLOG_CALLBACK whenever LIBRESSL_VERSION_NUMBER is not defined, and HAVE_OPENSSL_EARLYDATA when TLS1_3_VERSION exists and the backend is not BoringSSL-like. ctx_option_t is long under LibreSSL, uint32_t for BoringSSL-like, otherwise uint64_t. The ossl_ctx struct holds per-connection backend state: SSL_CTX, SSL, a custom BIO_METHOD, the last BIO cfilter result in io_result, blocked_ssl_write_len to retry a blocked write with the same length, keylog_done (only when no upstream or callback keylog support exists, to avoid duplicate keylog entries), and BIT flags tracking x509 store setup/emptiness, session reuse, and, under USE_APPLE_SECTRUST, sectrust verification state. The rest declares the backend API: function-pointer typedefs for setup, new-session and session-reuse callbacks, Curl_ossl_ctx_init, Curl_ossl_ctx_configure, Curl_ssl_setup_x509_store, Curl_ossl_add_session (takes ownership of the SSL_SESSION), Curl_ossl_check_peer_cert (per its comment, failf() only when verifypeer/verifyhost is set, otherwise informational), Curl_ossl_report_handshake, a compatibility #define mapping SSL_get1_peer_certificate to SSL_get_peer_certificate before OpenSSL 3, and the extern Curl_ssl_openssl backend instance.

**Notes.**

- side_effect: Including this header under USE_WIN32_CRYPTO mutates the macro namespace via #undef, an intentional workaround for wincrypt/OpenSSL symbol collisions.
- contract: The ossl_ctx fields blocked_ssl_write_len and keylog_done exist to change retry and dedup behavior, not just store state.

uses: [vtls-int-h](../../catalog.json), [vtls-scache-h](../../catalog.json), [vtls-config-h](../../catalog.json)

**Uncertainties.**

- The implementations of the declared functions live in other files; their runtime behavior is not verifiable from this header.

<a id="u-99db22f30e8d"></a>
### `rustls.c module code (L1–L53)`

`module_region` · [lib/vtls/rustls.c:L1-L53][f2]

File header, license and conditional compilation setup: the whole body compiles only when USE_RUSTLS is defined.

Includes rustls and curl internal headers, defines RAW_EAGAIN to treat EAGAIN and EWOULDBLOCK as equivalent when they differ, and the vtls backend table lives at the end of the file.

<a id="u-1c9c426b7b4a"></a>
### `rustls.c module code (L1456–L1490)`

`module_region` · [lib/vtls/rustls.c:L1456-L1490][f2]

Definition of the Curl_ssl backend table for rustls: backend id/name, supported features (CAINFO_BLOB, HTTPS_PROXY, cipher lists, CERTINFO, ECH, CRLFILE), backend size, and function pointers wiring cr_* handlers; unimplemented slots are NULL.

Closing #endif ends the USE_RUSTLS body.

uses: [cr_connect](r14-tls-rustls-transport.md#u-5034945dd123), [cr_recv](r14-tls-rustls-transport.md#u-7eac62854edd), [cr_send](r14-tls-rustls-transport.md#u-ab962705525a)

<a id="u-721f2a4493c3"></a>
### `map_error`

`static CURLcode map_error(const rustls_result r)` · [lib/vtls/rustls.c:L63-L76][f2]

Maps a rustls_result code to the closest CURLcode.

Certificate-related results (rustls_result_is_cert_error) map to CURLE_PEER_FAILED_VERIFICATION; RUSTLS_RESULT_OK maps to CURLE_OK; RUSTLS_RESULT_NULL_PARAMETER maps to CURLE_BAD_FUNCTION_ARGUMENT; every other result returns CURLE_RECV_ERROR.

<a id="u-b69191d1aea6"></a>
### `rustls_failf`

`static void rustls_failf(struct Curl_easy *data, const rustls_result rr, const char *…` · [lib/vtls/rustls.c:L78-L85][f2]

Formats a rustls_result's error text via rustls_error and reports it with failf prefixed by the caller's message.

Purely diagnostic; no control-flow effect.

<a id="u-969a6f395799"></a>
### `cr_close`

`static void cr_close(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/rustls.c:L1420-L1436][f2]

Frees the backend's rustls connection and client config, nulling both pointers; no close-notify is sent here (that is cr_shutdown's job).

<a id="u-a98f446c928c"></a>
### `cr_cleanup`

`static void cr_cleanup(void)` · [lib/vtls/rustls.c:L1453-L1456][f2]

Backend-global cleanup that closes the TLS keylog file opened by init_config_builder_keylog.

<a id="u-63903504210b"></a>
### `cr_data_pending`

`static bool cr_data_pending(struct Curl_cfilter *cf, const struct Curl_easy *data)` · [lib/vtls/rustls.c:L87-L97][f2]

Reports whether decrypted plaintext is still buffered in the rustls connection by returning the backend's data_in_pending flag.

Ignores the data argument and assumes the backend is set (DEBUGASSERT).

<a id="u-97d03e546c0b"></a>
### `cr_get_internals`

`static void *cr_get_internals(struct ssl_connect_data *connssl, CURLINFO info)` · [lib/vtls/rustls.c:L1348-L1355][f2]

Returns the backend's rustls_connection pointer for CURLINFO use, ignoring the specific info requested.

<a id="u-67467645d56f"></a>
### `cr_random`

`static CURLcode cr_random(struct Curl_easy *data, unsigned char *entropy, size_t length)` · [lib/vtls/rustls.c:L1444-L1451][f2]

Fills the caller's entropy buffer using rustls' default crypto provider random generator and maps the rustls result to a CURLcode via map_error.

calls: [map_error](r14-tls-rustls-backend.md#u-721f2a4493c3)

<a id="u-72cdb80684a2"></a>
### `cr_version`

`static size_t cr_version(char *buffer, size_t size)` · [lib/vtls/rustls.c:L1438-L1442][f2]

Writes the rustls library version string into the caller's buffer via curl_msnprintf and returns the written length.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/openssl.h
[f2]: ../../../../../../eval/curl-2c04412/lib/vtls/rustls.c
