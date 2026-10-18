# client cert, key, engine and provider config

**Capability.** Configuring the SSL_CTX with client certificates and private keys from files, blobs, PKCS#12, crypto engines or OpenSSL 3 providers, plus engine/provider selection, randomness/file-type helpers, error strings and PKCS#11 UI plumbing.

client_cert is the dispatcher; trace its calls to enginecheck/engineload, providercheck/providerload, pkcs12load and the blob loaders to follow each credential source. Engine/provider selection and teardown on the easy handle live here too.

**Depended on by.**

- [trust store management](r11-ossl-trust-store.md) · model-inferred · 0 edge(s)

Parent: [TLS backends \(OpenSSL-based\)](r11-tls-security.md)

## Units (17)

<a id="u-866389fbea65"></a>
### `openssl.c-seed-filetype`

`static bool rand_enough(void)` · [lib/vtls/openssl.c:L806-L809][f1]

Randomness seeding and certificate file-type parsing.

rand_enough reports RAND_status() != 0. ossl_seed is idempotent per multi handle: if data->multi exists and ssl_seeded is set it returns OK; if randomness suffices it flags ssl_seeded and returns OK; otherwise it fails with "Insufficient randomness" and CURLE_SSL_CONNECT_ERROR. ossl_do_file_type maps a certificate-type string to an OpenSSL file-type constant: empty/NULL means PEM, then case-insensitive PEM, DER/ASN1, PROV, ENG and P12 map to their constants; any other string returns -1. The non-standard ENGINE/PKCS12/PROVIDER constants are locally defined if the headers lack them.

<a id="u-8f7a64fa1ca7"></a>
### `openssl.c-strerror`

`static const char *SSL_ERROR_to_str(int err)` · [lib/vtls/openssl.c:L719-L755][f1]

Error-string helpers and the PEM password callback.

SSL_ERROR_to_str maps an SSL error code to a static name, covering Want_* and async variants conditionally compiled per library, returning "SSL_ERROR unknown" otherwise. ossl_strerror prefixes the buffer with the curl/OpenSSL flavor via Curl_ossl_version plus ": " when it fits, then appends ERR_error_string_n output; when nothing was written it substitutes "Unknown error" or "No error" for nonzero/zero codes. passwd_callback supplies a configured password to OpenSSL's PEM reader: only when not encrypting, num >= 0 and a password exists, and the buffer is larger than the password, it copies password plus NUL and returns its length; every other case returns 0.

**Uncertainties.**

- DEBUGASSERT(len < (size - 2)) means a too-long version string corrupts memory only in debug builds; release builds rely on the guard to skip prefixing

<a id="u-9a53f4a91c82"></a>
### `openssl.c-ui-pkcs11`

`static int ssl_ui_reader(UI *ui, UI_STRING *uis)` · [lib/vtls/openssl.c:L859-L875][f1]

UI plumbing and PKCS#11 URI detection used when engines or providers are built.

ssl_ui_reader answers UI prompt/verify strings with the configured password when the DEFAULT_PWD input flag is set (returning 1 immediately); otherwise, like ssl_ui_writer (which suppresses the interactive write under the same conditions), it falls through to the default OpenSSL UI method's reader/writer. is_pkcs11_uri is a case-insensitive prefix check for "pkcs11:".

<a id="u-937c2889ef5c"></a>
### `client_cert`

`static CURLcode client_cert(struct Curl_easy *data, SSL_CTX* ctx, char *cert_file, co…` · [lib/vtls/openssl.c:L1418-L1589][f1]

Configures the SSL_CTX with a client certificate and matching private key from files, blobs, engines, providers or PKCS#12.

It resolves the certificate type via ossl_do_file_type; the whole body runs only if a cert file, blob, or ENGINE/PROVIDER type is present, else it returns OK. When a password exists it installs passwd_callback on the context. The certificate is loaded by type: PEM (blob via use_certificate_chain_blob or file via SSL_CTX_use_certificate_chain_file), ASN1 (blob via use_certificate_blob or file), ENGINE via engineload, PROVIDER via providerload, P12 via pkcs12load, anything else is CURLE_BAD_FUNCTION_ARGUMENT. If no key was given separately, the key defaults to the cert source; otherwise the key type is re-derived. The key is then loaded per type (PEM/ASN1 from blob or file, ENGINE via enginecheck, PROVIDER via providercheck; P12 only if the cert was P12). It creates a temporary SSL to copy certificate parameters to the private key and, unless the RSA key has RSA_METHOD_FLAG_NO_CHECK, verifies the pair with SSL_CTX_check_private_key, failing with CURLE_SSL_CERTPROBLEM on mismatch. Every load failure failf's and returns CURLE_SSL_CERTPROBLEM or CURLE_BAD_FUNCTION_ARGUMENT as appropriate.

calls: [openssl.c-seed-filetype](r11-ossl-cert-key-config.md#u-866389fbea65), [lib/vtls/openssl.c:engineload](r11-ossl-cert-key-config.md#u-d154c0498638), [providerload](r11-ossl-cert-key-config.md#u-07399faf14ac), [pkcs12load](r11-ossl-cert-key-config.md#u-4db5cbb16871), [enginecheck](r11-ossl-cert-key-config.md#u-51c90585b23a), [providercheck](r11-ossl-cert-key-config.md#u-427a7d2f3f4d), [use_certificate_blob](r11-ossl-cert-key-config.md#u-040f13c2a6b8), [use_certificate_chain_blob](r11-ossl-cert-key-config.md#u-debfd659aa40), [use_privatekey_blob](r11-ossl-cert-key-config.md#u-8958335d3040); uses: [openssl.c-strerror](r11-ossl-cert-key-config.md#u-8f7a64fa1ca7)

<a id="u-51c90585b23a"></a>
### `enginecheck`

`static int enginecheck(struct Curl_easy *data, SSL_CTX* ctx, const char *key_file, co…` · [lib/vtls/openssl.c:L1029-L1080][f1]

Loads a private key through a crypto engine (SSL_FILETYPE_ENGINE).

Only compiled with engine support; otherwise it always fails with "SSL_FILETYPE_ENGINE not supported for private key". With support: if no engine is set and the key file is a PKCS#11 URI, it implicitly selects the "pkcs11" engine (a failed selection returns 0). Without an engine it fails. With one, it builds a "curl user interface" method copying OpenSSL's opener/closer and curl's reader/writer, loads the key via ENGINE_load_private_key passing the password as UI data, and fails on any of: method creation, key load, or SSL_CTX_use_PrivateKey, each with a failf. On success the key handle is freed after the context takes its reference. Returns 1 on success.

calls: [ossl_set_engine](r11-ossl-cert-key-config.md#u-83ffd4657073); uses: [openssl.c-ui-pkcs11](r11-ossl-cert-key-config.md#u-9a53f4a91c82)

<a id="u-d154c0498638"></a>
### `lib/vtls/openssl.c:engineload`

`static int engineload(struct Curl_easy *data, SSL_CTX* ctx, const char *cert_file)` · [lib/vtls/openssl.c:L1183-L1229][f1]

Loads a client certificate through a crypto engine (SSL_FILETYPE_ENGINE for certificates); without engine support or ENGINE_CTRL_GET_CMD_FROM_NAME it always fails.

It implicitly selects the "pkcs11" engine for PKCS#11 URI cert files. With an engine, it probes support for the LOAD_CERT_CTRL command via ENGINE_ctrl; an unsupported engine fails. It then issues ENGINE_ctrl_cmd with a {cert_id, cert} struct, failing if the command fails or leaves cert NULL, then sets the certificate on the SSL_CTX (freeing the X509 on failure). Missing engine or any failure returns 0 with a failf; success returns 1 after freeing the certificate handle.

calls: [ossl_set_engine](r11-ossl-cert-key-config.md#u-83ffd4657073)

<a id="u-427a7d2f3f4d"></a>
### `providercheck`

`static int providercheck(struct Curl_easy *data, SSL_CTX* ctx, const char *key_file)` · [lib/vtls/openssl.c:L1082-L1163][f1]

Loads a private key through an OpenSSL 3 provider store (SSL_FILETYPE_PROVIDER); without provider support it always fails with a failf.

If no provider is loaded and the key file is a PKCS#11 URI, it implicitly selects the "pkcs11" provider (failure returns 0). Without a loaded provider it fails. With one, it builds the curl UI method, opens an OSSL_STORE on the key file with the state's libctx and propq (open failure reports the OpenSSL error and returns 0), sets the store expectation to PKEY (failure is logged but ignored), loads one object and keeps it only if it is a PKEY, then closes store and UI. A missing key, SSL_CTX_use_PrivateKey failure, or no loaded provider each failf and return 0; success frees the key handle and returns 1.

calls: [ossl_set_provider](r11-ossl-cert-key-config.md#u-4d93b948c373); uses: [openssl.c-strerror](r11-ossl-cert-key-config.md#u-8f7a64fa1ca7)

<a id="u-07399faf14ac"></a>
### `providerload`

`static int providerload(struct Curl_easy *data, SSL_CTX* ctx, const char *cert_file)` · [lib/vtls/openssl.c:L1231-L1301][f1]

Loads a client certificate through an OpenSSL 3 provider (SSL_FILETYPE_PROVIDER for certificates); without provider support it always fails.

It implicitly selects the "pkcs11" provider for PKCS#11 URI cert files. With a loaded provider it opens an OSSL_STORE on the cert file using the state libctx (no propq, no UI here), sets the expectation to CERT (failure logged but ignored), loads one object keeping it only if it is a CERT, and closes the store. A missing certificate or an SSL_CTX_use_certificate failure each failf with the OpenSSL error and return 0; a missing loaded provider fails; otherwise returns 1 after freeing the X509.

calls: [ossl_set_provider](r11-ossl-cert-key-config.md#u-4d93b948c373)

<a id="u-4db5cbb16871"></a>
### `pkcs12load`

`static int pkcs12load(struct Curl_easy *data, SSL_CTX* ctx, const struct curl_blob *c…` · [lib/vtls/openssl.c:L1303-L1416][f1]

Loads a PKCS#12 client certificate and key from a file or blob into the SSL_CTX.

It wraps the blob in a memory BIO or opens the file via a file BIO (each failure failf's and returns 0). It parses the PKCS12 with d2i_PKCS12_bio and PKCS12_parse using key_passwd; parse failures (wrong password) failf and return 0. It then installs the certificate, the private key, and verifies they match, failing via goto fail on any mismatch. If the parse produced a CA stack, it pops each certificate and adds it both as a client CA and as an extra chain cert, failing if either add fails. cert_done is set only after everything succeeds; the shared cleanup frees key, cert and CA stack, and returns 0 on any failure path.

**Uncertainties.**

- SSL_CTX_add_extra_chain_cert takes ownership of the popped cert; on the second add's failure the cert is freed explicitly, which relies on that ownership contract

<a id="u-040f13c2a6b8"></a>
### `use_certificate_blob`

`static int use_certificate_blob(SSL_CTX *ctx, const struct curl_blob *blob, int type,…` · [lib/vtls/openssl.c:L911-L945][f1]

Loads a single client certificate from a memory blob into the SSL_CTX.

It wraps the blob in a memory BIO (failure returns CURLE_OUT_OF_MEMORY, a CURLcode where callers expect 0/1 so it is truthy-failure compatible). For SSL_FILETYPE_ASN1 it decodes with d2i_X509_bio; for SSL_FILETYPE_PEM with PEM_read_bio_X509 using passwd_callback and the key password; any other type or a failed decode returns 0 without setting the certificate. On success it calls SSL_CTX_use_certificate and returns its result, always freeing the X509 and BIO.

**Uncertainties.**

- Returning CURLE_OUT_OF_MEMORY (a nonzero CURLcode) from an int-returning helper means callers treat it as a failure, but the exact value is not surfaced as a CURLcode

<a id="u-debfd659aa40"></a>
### `use_certificate_chain_blob`

`static int use_certificate_chain_blob(SSL_CTX *ctx, const struct curl_blob *blob, con…` · [lib/vtls/openssl.c:L974-L1027][f1]

Loads a PEM client certificate plus its chain from a memory blob.

It reads the first certificate with PEM_read_bio_X509_AUX and sets it via SSL_CTX_use_certificate; any queued OpenSSL error at that point forces ret to 0. On success it clears existing chain certs (failure aborts), then loops PEM_read_bio_X509 adding each remaining certificate with SSL_CTX_add0_chain_cert (taking ownership; failure frees and aborts). After the loop, an ending PEM_R_NO_START_LINE error is cleared as normal termination; any other trailing error zeroes ret. Returns 0/1 with the BIO and first X509 always freed.

**Uncertainties.**

- add0 chain certificates transfer ownership to the SSL_CTX; double-free is avoided by not freeing ca on success

<a id="u-8958335d3040"></a>
### `use_privatekey_blob`

> **ID corrected by CBE.** CBE changed the unit ID from ` lib/vtls/openssl.c::function::use_privatekey_blob::25170-placeholder ` to the inventory ID ` lib/vtls/openssl.c::function::use_privatekey_blob::25989 `. The model wrote this body under the wrong ID; it may be inaccurate.

`static int use_privatekey_blob(SSL_CTX *ctx, const struct curl_blob *blob, int type, …` · [lib/vtls/openssl.c:L947-L972][f1]

placeholder

<a id="u-83ffd4657073"></a>
### `ossl_set_engine`

`static CURLcode ossl_set_engine(struct Curl_easy *data, const char *name)` · [lib/vtls/openssl.c:L1653-L1689][f1]

Selects a crypto engine by name for the easy handle, falling back to provider selection when engines are unavailable.

With engine support: ENGINE_by_id failure falls through to the provider path (or fails with CURLE_SSL_ENGINE_NOTFOUND). On finding an engine it first finishes and frees any previously set engine, then ENGINE_init; an init failure frees the engine, failf's with the OpenSSL error, and returns CURLE_SSL_ENGINE_INITFAILED; success stores the initialized engine in data->state.engine and returns OK. Without engine support but with providers, it delegates to ossl_set_provider; with neither it failf's and returns CURLE_SSL_ENGINE_NOTFOUND.

calls: [ossl_set_provider](r11-ossl-cert-key-config.md#u-4d93b948c373)

<a id="u-2f07fe639d4b"></a>
### `ossl_set_engine_default`

`static CURLcode ossl_set_engine_default(struct Curl_easy *data)` · [lib/vtls/openssl.c:L1693-L1711][f1]

Makes the currently selected engine the default for all cryptographic operations.

Without engine support it is a no-op returning OK; with an engine set, ENGINE_set_default success logs the engine id, failure failf's and returns CURLE_SSL_ENGINE_SETFAILED. With no engine selected it returns OK silently.

<a id="u-a4f9f4a030af"></a>
### `ossl_engines_list`

`static struct curl_slist *ossl_engines_list(struct Curl_easy *data)` · [lib/vtls/openssl.c:L1715-L1733][f1]

Builds a curl_slist of available engine ids by walking ENGINE_get_first/next; without engine support it returns NULL.

If appending an id fails mid-walk it frees the whole list and returns NULL.

<a id="u-4d93b948c373"></a>
### `ossl_set_provider`

`static CURLcode ossl_set_provider(struct Curl_easy *data, const char *iname)` · [lib/vtls/openssl.c:L1763-L1832][f1]

Selects an OpenSSL 3 provider, optionally with a property query given as "name:propq" (no colon means no property).

A NULL name clears all provider state via ossl_provider_cleanup and returns OK; a name longer than 127 characters or a malformed colon split returns CURLE_BAD_FUNCTION_ARGUMENT. If no libctx exists yet it creates one (and duplicates the propq), with OOM returning CURLE_OUT_OF_MEMORY. Unless config auto-load is disabled it loads the default config into the libctx, logging but ignoring failure. If the provider is already available through configuration it just marks provider_loaded. Otherwise it try-loads the named provider, failing with CURLE_SSL_ENGINE_NOTFOUND and cleaning up all provider state on failure, then try-loads the "base" provider with the same failure handling before marking provider_loaded and returning OK.

calls: [ossl_provider_cleanup](r11-ossl-cert-key-config.md#u-4b7c8ec2ac0c)

<a id="u-4b7c8ec2ac0c"></a>
### `ossl_provider_cleanup`

`static void ossl_provider_cleanup(struct Curl_easy *data)` · [lib/vtls/openssl.c:L1737-L1751][f1]

Releases provider state on the easy handle: unloads the base and extra providers (nulling each), frees the custom OSSL_LIB_CTX, frees the propq string, and clears provider_loaded.

Provider-only, under OPENSSL_HAS_PROVIDERS.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/openssl.c
