# rustls Client Config Builder

**Capability.** Owns assembling the rustls client configuration: version bounds and cipher selection, ALPN, client certificates, trust anchors with CRL loading, platform verifier, ECH, and keylog registration.

cr_init_backend orchestrates these helpers to build one client config; use this subtree when changing how ciphers, verification or ECH are configured. cr_get_selected_ciphers supplies the restricted crypto provider's suites.

**Depended on by.**

- [rustls Connection Transport](r14-tls-rustls-transport.md) · model-inferred · 0 edge(s)

Parent: [rustls TLS Backend](r14-tls-rustls.md)

## Units (15)

<a id="u-69fe9ed37f89"></a>
### `cr_init_backend`

`static CURLcode cr_init_backend(struct Curl_cfilter *cf, struct Curl_easy *data, stru…` · [lib/vtls/rustls.c:L1046-L1152][f1]

Builds the rustls client config and connection for the filter's backend.

Assembles the config builder (versions/ciphers), then conditionally: sets ALPN when offered; when verifypeer is off installs cr_verify_none, else when native_ca_store is set uses the platform verifier (rejecting CRLfile with CURLE_NOT_BUILT_IN since the platform verifier has no CRL API), else uses the file/blob root-store verifier when CA material is present. Client auth is configured when any cert/key material exists; ECH (when enabled) fails hard only for CURLECH_HARD, softer modes continue; keylog is attached last. The config is built, then a client connection is created for the origin hostname; connection creation failure frees the config, resets it to NULL and returns CURLE_COULDNT_CONNECT. On success the connection is stored in the backend with the backend as userdata. Every intermediate failure path frees the config builder before returning.

calls: [init_config_builder](r14-tls-rustls-config.md#u-8a01d4cfd6d8), [init_config_builder_verifier](r14-tls-rustls-config.md#u-5a2fd41e5668)

**Uncertainties.**

- Whether a failing soft-ECH setup leaves ECH silently disabled is decided by earlier configuration state, not provable from this function alone.

<a id="u-8a01d4cfd6d8"></a>
### `init_config_builder`

`static CURLcode init_config_builder(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/vtls/rustls.c:L530-L662][f1]

Builds the base rustls client config builder: validates TLS version bounds and forces TLS1.3-only when ECH is enabled, selects cipher suites, then constructs a custom crypto provider restricted to those suites and the allowed versions.

Version handling: minimum versions TLS1.0-1.2 are accepted (TLS1.3 restricts tls_versions to one entry); any other minimum fails with CURLE_BAD_FUNCTION_ARGUMENT. Maximum DEFAULT/NONE/TLS1.3 pass through; MAX_TLSv1.2 caps the list only when the minimum is TLS1.2, otherwise it falls through to failure. On any later rustls failure the result is CURLE_SSL_CIPHER with the rustls error logged. cleanup frees the cipher array, provider builder and provider regardless of outcome; the produced builder in *config_builder survives.

calls: [cr_get_selected_ciphers](r14-tls-rustls-config.md#u-a97f327a20a4)

**Uncertainties.**

- CURLE_SSL_CIPHER is returned for several rustls provider failures that are not strictly cipher-list errors.

<a id="u-a34b69517b9e"></a>
### `init_config_builder_alpn`

`static void init_config_builder_alpn(struct Curl_easy *data, const struct ssl_connect…` · [lib/vtls/rustls.c:L664-L681][f1]

Copies the connection's ALPN entries into rustls_slice_bytes and sets them on the config builder, then logs the offered protocol list.

No return value: rustls setup errors here are not checked.

**Uncertainties.**

- Return value of rustls_client_config_builder_set_alpn_protocols is ignored; failure would be silent.

<a id="u-823e30af7292"></a>
### `init_config_builder_client_auth`

`static CURLcode init_config_builder_client_auth(struct Curl_easy *data, const struct …` · [lib/vtls/rustls.c:L848-L953][f1]

Configures TLS client certificates.

Requires certificate and key to be given together (either alone fails with CURLE_SSL_CERTPROBLEM); only 'PEM' cert_type/key_type is accepted. Material comes from cert_blob/key_blob when present, otherwise the clientcert/key files are read into size-capped dynbufs; blob copy failure distinguishes 'too large' from 'out of memory', file read failure reports the path. rustls_certified_key_build, the keys-match check, and installing the key on the builder each fail with CURLE_SSL_CERTPROBLEM after rustls_failf logging. Dynbufs and the certified key are always freed on cleanup.

**Uncertainties.**

- read_file_into is called with conn_config->clientcert / ->key that may be NULL when only blobs are absent; fopen(NULL) behavior is outside this file.

<a id="u-8201ebd584ca"></a>
### `init_config_builder_ech`

`static CURLcode init_config_builder_ech(struct Curl_easy *data, struct Curl_cfilter *…` · [lib/vtls/rustls.c:L957-L1043][f1]

Configures Encrypted Client Hello on the builder (compiled only with USE_ECH).

Fails with CURLE_SSL_CONNECT_ERROR when rustls lacks an HPKE provider or when an ECH outer/public name is configured (unsupported). CURLECH_GREASE enables grease and returns immediately. Otherwise the ECHConfigList comes either from base64-decoded ech_config (an empty string or failed decode fails) or from the HTTPS RR echconfiglist for the peer, failing when no matching RR with ECH config exists. Enabling ECH in rustls fails with CURLE_SSL_CONNECT_ERROR after logging. cleanup frees the base64-decoded buffer only when ech_config came from the command line and unlinks any DNS entry.

**Uncertainties.**

- The dns variable is never assigned in the visible code, so the Curl_dns_entry_unlink path appears unreachable here.

<a id="u-9aaf5615e6b4"></a>
### `init_config_builder_keylog`

`static CURLcode init_config_builder_keylog(struct Curl_easy *data, struct rustls_clie…` · [lib/vtls/rustls.c:L825-L846][f1]

Opens the TLS keylog facility and, only when it is enabled, registers cr_keylog_log_cb with rustls.

If keylog is disabled it returns CURLE_OK without touching rustls; if registering the callback fails it closes the keylog and returns map_error(rr).

calls: [cr_keylog_log_cb](r14-tls-rustls-config.md#u-fa9338b825d9), [map_error](r14-tls-rustls-backend.md#u-721f2a4493c3)

<a id="u-d6da763e89b9"></a>
### `init_config_builder_platform_verifier`

`static CURLcode init_config_builder_platform_verifier( struct Curl_easy *data, struct…` · [lib/vtls/rustls.c:L800-L823][f1]

Installs the OS-native certificate verifier on the config builder.

Failure to create it returns CURLE_SSL_CACERT_BADFILE after logging; the verifier is freed after being handed to the builder.

<a id="u-5a2fd41e5668"></a>
### `init_config_builder_verifier`

`static CURLcode init_config_builder_verifier(struct Curl_easy *data, struct rustls_cl…` · [lib/vtls/rustls.c:L714-L798][f1]

Builds the server certificate verifier from explicit trust anchors.

Trust material comes from ca_info_blob (PEM added to a fresh root store) or ssl_cafile (roots loaded from file); without either the root store stays empty. Failures at any rustls step yield CURLE_SSL_CACERT_BADFILE (or CURLE_OUT_OF_MEMORY for verifier allocation). When conn_config->CRLfile is set it attaches CRLs through init_config_builder_verifier_crl before building the verifier and installing it on the config builder. All intermediate rustls objects are freed on cleanup.

calls: [init_config_builder_verifier_crl](r14-tls-rustls-config.md#u-0928748c432c)

**Uncertainties.**

- Behavior of webpki verification with an empty root store (no blob and no CAfile) is decided inside rustls, not here.

<a id="u-0928748c432c"></a>
### `init_config_builder_verifier_crl`

`static CURLcode init_config_builder_verifier_crl( struct Curl_easy *data, const struc…` · [lib/vtls/rustls.c:L683-L712][f1]

Loads the CRL file into a size-capped dynbuf via read_file_into and adds it to a webpki verifier builder.

Read failure or rustls parse failure returns CURLE_SSL_CRL_BADFILE after logging; the dynbuf is always freed.

<a id="u-a97f327a20a4"></a>
### `cr_get_selected_ciphers`

`static void cr_get_selected_ciphers(struct Curl_easy *data, const char *ciphers12, co…` · [lib/vtls/rustls.c:L422-L515][f1]

Builds the rustls cipher suite selection array from the TLS1.2 and TLS1.3 cipher list strings, overwriting *selected_size with the final count.

With no TLS1.3 list, all default provider TLS1.3 suites are preselected (default13_count records how many). It walks cipher strings with Curl_cipher_suite_walk_str: an unknown or unsupported suite logs 'unknown cipher in list' and is skipped; duplicates in the selection are skipped, logging 'duplicate cipher in list' only when the duplicate is not a preselected TLS1.3 default. After the TLS1.3 list the same walk reruns over ciphers12 if present. When no TLS1.2 list is given, default TLS1.2 suites are appended, skipping duplicates. Selection stops at the supported_len capacity, so overflow cannot occur.

uses: [map_error](r14-tls-rustls-backend.md#u-721f2a4493c3)

**Uncertainties.**

- Whether entries with id 0 that end the walk string are skipped silently depends on Curl_cipher_suite_walk_str behavior, not shown here.

<a id="u-fa9338b825d9"></a>
### `cr_keylog_log_cb`

`static void cr_keylog_log_cb(struct rustls_str label, const uint8_t *client_random, s…` · [lib/vtls/rustls.c:L517-L528][f1]

Rustls key-log callback: formats the rustls_str label into a bounded C string and forwards label, client random and secret to Curl_tls_keylog_write.

Asserts the client random length equals CLIENT_RANDOM_SIZE.

<a id="u-2a56ab2406d2"></a>
### `cr_verify_none`

`static uint32_t cr_verify_none(void *userdata, const rustls_verify_server_cert_params…` · [lib/vtls/rustls.c:L392-L398][f1]

Server-certificate verify callback that unconditionally returns RUSTLS_RESULT_OK, disabling certificate verification.

Installed only when verifypeer is off.

<a id="u-06d3bee0f6f8"></a>
### `read_file_into`

`static int read_file_into(const char *filename, struct dynbuf *out)` · [lib/vtls/rustls.c:L400-L420][f1]

Reads a whole file into a dynbuf in 256-byte chunks.

Returns 0 when the file cannot be opened, when a short fread occurs without EOF, or when the dynbuf append fails (e.g. size limit); otherwise returns whether fclose succeeded. Always closes an opened file.

<a id="u-a8899cf625a0"></a>
### `rustls.c module code (L953–L956)`

`module_region` · [lib/vtls/rustls.c:L953-L956][f1]

Short region around the USE_ECH conditional opening; non-behavioral.

<a id="u-13f6a86a3b49"></a>
### `rustls.c module code (L1043–L1045)`

`module_region` · [lib/vtls/rustls.c:L1043-L1045][f1]

Short region closing the USE_ECH conditional; non-behavioral.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/rustls.c
