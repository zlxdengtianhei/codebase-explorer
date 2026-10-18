# Backend selection and delegates

**Capability.** Lazy backend selection for multi-SSL builds, global init and backend queries, and thin forwarding wrappers with fallbacks when the active backend lacks a hook.

Read this to see how curl picks and reaches the active Curl_ssl backend. All filter code ultimately resolves to these delegates; query functions report backend capabilities.

**Depended on by.**

- [SSL connection filter](r15-tls-cfilter.md) · model-inferred · 0 edge(s)

Parent: [TLS layer \(vtls\)](r15-tls-layer.md)

## Units (5)

<a id="u-4fb380d2385e"></a>
### `vtls.c-multissl`

`static int multissl_init(void)` · [lib/vtls/vtls.c:L593-L600][f1]

Implements lazy backend selection for multi-SSL builds.

The global Curl_ssl starts as &Curl_ssl_multi, a placeholder whose ops each call multissl_setup(NULL) first and then forward to the resolved backend; setup failure maps to CURLE_FAILED_INIT for most ops, CURLE_OK for adjust_pollset, NULL for get_internals, and silent return for close. multissl_setup is a no-op success once a real backend is installed; otherwise it requires at least one available backend, honors the CURL_SSL_BACKEND environment variable by name, then CURL_DEFAULT_SSL_BACKEND, and finally falls back to available_backends[0]; an explicit backend argument installs directly. multissl_version caches a space-separated version string over all built backends, parenthesizing non-selected ones, rebuilt only when the selection changes, and copies at most 'size' bytes into the buffer, returning 0. Curl_ssl_cleanup runs the backend cleanup only if init previously succeeded, restores Curl_ssl to &Curl_ssl_multi in multi-SSL builds, and clears init_ssl so a later init can run again.

uses: [Curl_ssl_backend](r15-tls-backend-selection.md#u-7cf507da57de)

**Uncertainties.**

- multissl_version uses function-local statics; thread-safety of the cache rebuild is not addressed in this source.
- If CURL_SSL_BACKEND names an unknown backend and no default is compiled in, the fallback to the first available backend is silent.

<a id="u-581338b7ee79"></a>
### `vtls.c-backend-delegates`

`CURLcode Curl_ssl_get_channel_binding(struct Curl_easy *data, int8_t sockindex, struc…` · [lib/vtls/vtls.c:L219-L225][f1]

Thin generic wrappers that forward to the active SSL backend (global Curl_ssl) with well-defined fallbacks when a backend hook is absent.

get_channel_binding returns CURLE_OK if the backend lacks the hook; close_all and set_engine/set_engine_default return/propagate nothing or CURLE_NOT_BUILT_IN when unsupported; engines_list returns NULL; random asserts length == sizeof(int) and returns CURLE_NOT_BUILT_IN without randomness if the hook is missing; cert_status_request returns FALSE. Curl_ssl_version writes the version string via the backend, except in CURL_WITH_MULTI_SSL builds where it delegates to multissl_version.

calls: [vtls.c-multissl](r15-tls-backend-selection.md#u-4fb380d2385e)

**Uncertainties.**

- Whether get_channel_binding's CURLE_OK fallback is distinguishable from success by callers is decided outside this file.

<a id="u-7cf507da57de"></a>
### `Curl_ssl_backend`

`curl_sslbackend Curl_ssl_backend(void)` · [lib/vtls/vtls.c:L130-L138][f1]

Returns the identifier of the currently selected SSL backend.

Under USE_SSL it first forces multissl_setup(NULL) so a multi-SSL build resolves the backend lazily, then returns Curl_ssl->info.id; without SSL support it returns CURLSSLBACKEND_NONE.

calls: [vtls.c-multissl](r15-tls-backend-selection.md#u-4fb380d2385e)

<a id="u-0d2c89e9f1eb"></a>
### `Curl_ssl_init`

`int Curl_ssl_init(void)` · [lib/vtls/vtls.c:L151-L161][f1]

Performs global one-time SSL backend initialization, returning 1 on success and 0 on failure.

Guarded by the static init_ssl flag: a repeat call returns 1 without re-running. On the first call it sets init_ssl and invokes Curl_ssl->init() if present; if the backend has no init hook it returns 1.

**Notes.**

- side_effect: Sets the file-static init_ssl flag permanently until Curl_ssl_cleanup resets it.

uses: [vtls.c-multissl](r15-tls-backend-selection.md#u-4fb380d2385e)

<a id="u-86c8f62788b1"></a>
### `Curl_init_sslset_nolock`

`CURLsslset Curl_init_sslset_nolock(curl_sslbackend id, const char *name, const curl_s…` · [lib/vtls/vtls.c:L825-L852][f1]

Selects the SSL backend before global init, called under the global lock by curl_global_sslset.

It optionally reports the available_backends table via 'avail'. If a backend is already installed (Curl_ssl != &Curl_ssl_multi), it returns CURLSSLSET_OK when the requested id or name matches the current backend, else CURLSSLSET_TOO_LATE in multi-SSL builds or CURLSSLSET_UNKNOWN_BACKEND otherwise. While the multi placeholder is active, the first backend matching id or name is installed via multissl_setup and OK returned; no match yields CURLSSLSET_UNKNOWN_BACKEND. The USE_SSL-disabled variant of the same name ignores all arguments and always returns CURLSSLSET_NO_BACKENDS.

calls: [vtls.c-multissl](r15-tls-backend-selection.md#u-4fb380d2385e)

**Uncertainties.**

- Behavior when both id and name are supplied and they disagree is not specified beyond the OR matching shown.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/vtls.c
