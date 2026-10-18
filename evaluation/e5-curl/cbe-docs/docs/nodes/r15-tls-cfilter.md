# SSL connection filter

**Capability.** Creation and installation of SSL connection filters, ssl_connect_data lifecycle, handshake and deferred-connect steps, send path with early data, query/control callbacks, pollset updates, blocking shutdown, preference checks, and ssl_peer identity management.

This is the connect-filter implementation: ssl_cf_connect performs the handshake once the next filter is connected, send handles deferred handshakes and 0-RTT. ssl_peer records feed TLS identity and session-cache keying.

**Depends on.**

- [ALPN and session reuse](r15-tls-alpn-session.md) · model-inferred · 0 edge(s)
- [Backend selection and delegates](r15-tls-backend-selection.md) · model-inferred · 0 edge(s)
- [Generic TLS verification utilities](r15-tls-verify-generic.md) · model-inferred · 0 edge(s)

Parent: [TLS layer \(vtls\)](r15-tls-layer.md)

## Units (14)

<a id="u-cba3d0322e17"></a>
### `vtls.c-cfilter-creation`

`static CURLcode cf_ssl_create(struct Curl_cfilter **pcf, struct Curl_easy *data, stru…` · [lib/vtls/vtls.c:L1349-L1382][f1]

Factories that create and install SSL connection filters.

cf_ssl_create builds a context via cf_ctx_new with the ALPN spec from the connection's HTTP negotiation (or NULL under CURL_DISABLE_HTTP) and wraps it in a Curl_cft_ssl filter; context allocation failure yields CURLE_OUT_OF_MEMORY and the context is freed. cf_ssl_peer_init queries the backend's version string into a local tls_id buffer and initializes the peer via Curl_ssl_peer_init with TRNSPRT_TCP. Curl_ssl_cfilter_add picks via_peer or via_peer2 by sockindex, creates and initializes the filter, adds it to the connection, and discards the chain on failure. Curl_cf_ssl_insert_after inserts the filter after a given one and, when built with USE_HTTPSRR and USE_ECH and the origin is HTTP with ECH requiring HTTPS-RR, additionally kicks off an HTTPS-RR resolve (its result becomes the function result). cf_ssl_proxy_create builds a Curl_cft_ssl_proxy filter: ALPN defaults to the user's ssl_enable_alpn setting with HTTP/1.x wanted, but CURLPROXY_HTTPS2 proxies force ALPN with both v1 and v2 wanted. Curl_cf_ssl_proxy_insert_after mirrors insert_after using the proxy SSL config and NULL peer. All insertion helpers discard the created chain on failure.

calls: [alpn_get_spec](r15-tls-alpn-session.md#u-bf6005a27063), [vtls.c-ssl-peer](r15-tls-cfilter.md#u-2317ae187737)

**Uncertainties.**

- The tls_id buffer is filled with version(buffer, sizeof-1); whether the backend NUL-terminates depends on its version hook.
- Curl_conn_dns_add_https_resolve behavior is outside this file.

<a id="u-32884e251aa5"></a>
### `vtls.c-ssl-connect-data-lifecycle`

`static struct ssl_connect_data *cf_ctx_new(struct Curl_easy *data, const struct alpn_…` · [lib/vtls/vtls.c:L188-L207][f1]

Allocates and frees the per-filter ssl_connect_data context.

cf_ctx_new zero-allocates the context, records the active backend (Curl_ssl) and the ALPN spec, initializes the earlydata bufq with CURL_SSL_EARLY_MAX and no spares, and allocates the backend-specific data of size sizeof_ssl_backend_data; on backend allocation failure it frees the context and returns NULL. cf_ctx_free releases the negotiated ALPN string, the earlydata bufq, the backend data, and the context itself, tolerating NULL.

**Uncertainties.**

- The 'data' parameter of cf_ctx_new is unused in the shown source; any data-dependent behavior is not visible.

<a id="u-157bfad0863b"></a>
### `vtls.c-ssl-cfilter-minor`

`static void ssl_cf_destroy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/vtls.c:L943-L957][f1]

Secondary operations of the SSL connection filter, all operating on cf->ctx (ssl_connect_data) and saving/restoring the filter data context.

destroy closes via the backend, resets state to none/connecting_1/prefs_checked=FALSE, cleans the peer, destroys the cached session, frees the context and clears cf->ctx and cf->connected; a NULL ctx still clears connected. set_earlydata (debug-asserting await state and an empty bufq) truncates writes to earlydata_max and buffers into the earlydata bufq, returning errors; empty input is a no-op success. data_pending is TRUE if the backend reports pending data, else defers to the next filter's has_data_pending. recv mirrors send: in deferred state it triggers ssl_cf_connect_deferred with no payload, returning CURLE_AGAIN if the handshake is not finished, then delegates to backend recv_plain with *pnread zeroed first. shutdown marks done=TRUE and only invokes the backend shut_down when the handshake completed, the filter is connected, not already shutting down, and the backend supports it; cf->shutdown is set when finished or failed. adjust_pollset forwards to the backend implementation. is_alive pessimistically returns FALSE when there is no next filter, otherwise delegates to it.

**Uncertainties.**

- The recv unit's inventory id in the source excerpt pairs with ssl_cf_recv at lines 1167-1194; its grouping here follows its body, which is nearly identical to ssl_cf_send's deferred handling.

<a id="u-2317ae187737"></a>
### `vtls.c-ssl-peer`

`void Curl_ssl_peer_cleanup(struct ssl_peer *peer)` · [lib/vtls/vtls.c:L868-L876][f1]

Builds and tears down the ssl_peer record used for TLS identity and session-cache keying.

Cleanup unlinks the origin and peer references, frees sni and scache_key, resets transport to TRNSPRT_NONE and type to CURL_SSL_PEER_DNS. get_peer_type classifies a hostname: AF_INET parse yields CURL_SSL_PEER_IPV4, and under USE_IPV6 an AF_INET6 parse yields CURL_SSL_PEER_IPV6; anything else (including empty/NULL) is CURL_SSL_PEER_DNS. Curl_ssl_peer_init expects a once-only clean struct, asserting on NULL peer/origin (CURLE_FAILED_INIT) and on pre-set fields; it links origin and peer, sets the type, and for DNS peers builds the SNI per RFC 6066: strips one trailing dot, lowercases, and only when length < USHRT_MAX allocates a copy (allocation failure goes to the out path). It then makes the session cache key via Curl_ssl_peer_key_make using the backend tls_id; on any failure it runs cleanup and returns the error.

**Uncertainties.**

- When a DNS hostname is USHRT_MAX or longer, sni stays NULL and the code proceeds to key generation with no SNI; whether that is acceptable is decided by the backend.
- The exact content of scache_key depends on Curl_ssl_peer_key_make, defined elsewhere.

<a id="u-8843317b1be8"></a>
### `vtls.c-cf-config-accessors`

`bool Curl_ssl_cf_is_proxy(struct Curl_cfilter *cf)` · [lib/vtls/vtls.c:L1606-L1609][f1]

Small accessors distinguishing the proxy SSL filter from the end-to-end one.

Curl_ssl_cf_is_proxy is TRUE only when the filter type carries both CF_TYPE_SSL and CF_TYPE_PROXY. The config accessors return the proxy-specific settings (data->set.proxy_ssl / conn->proxy_ssl_config) for proxy filters and the regular connection SSL settings otherwise; under CURL_DISABLE_PROXY they unconditionally return the non-proxy structs.

**Uncertainties.**

- Curl_ssl_cf_get_easy_config ignores cf under CURL_DISABLE_PROXY, so a proxy filter there would get the wrong struct — no caller evidence in this file.

<a id="u-a8f9b2e0bf09"></a>
### `vtls.c-supports-queries`

`bool Curl_ssl_supports(struct Curl_easy *data, unsigned int ssl_option)` · [lib/vtls/vtls.c:L1497-L1501][f1]

Capability queries against the active backend and config.

Curl_ssl_supports simply tests whether the backend's supports mask contains ssl_option. Under USE_ECH, Curl_ssl_ech_enabled returns TRUE only when the backend supports ECH and the filter's ssl_filter_config has ech set. Curl_ssl_need_httpsrr refines this: FALSE when ECH is unsupported or disabled, FALSE when ech is CURLECH_GREASE or an ech_config is already present, TRUE only when ECH is on but no config is available yet.

uses: [vtls.c-cf-config-accessors](r15-tls-cfilter.md#u-8843317b1be8)

<a id="u-40a63e640ab1"></a>
### `ssl_cf_cntrl`

`static CURLcode ssl_cf_cntrl(struct Curl_cfilter *cf, struct Curl_easy *data, int eve…` · [lib/vtls/vtls.c:L1268-L1298][f1]

Handles control events for the SSL filter.

On CF_CTRL_CONN_INFO_UPDATE it maps the negotiated ALPN to the connection's httpversion_seen when an ALPN is set and sockindex is 0: 'http/1.1'→11, 'h2'→20, 'h3'→30; other ALPN values leave it unchanged. On CF_CTRL_REPORT_STATS it reports TIMER_APPCONNECT from handshake_done, once per filter, only when connected, not yet reported, this is the non-proxy SSL filter, and handshake_done is non-zero. Always returns CURLE_OK.

**Notes.**

- side_effect: Mutates cf->conn->httpversion_seen and connssl->stats_reported.

<a id="u-469605397018"></a>
### `ssl_cf_connect`

`static CURLcode ssl_cf_connect(struct Curl_cfilter *cf, struct Curl_easy *data, bool …` · [lib/vtls/vtls.c:L959-L1021][f1]

Connect filter step that performs the SSL handshake once the next filter is connected.

Short-circuits with done=TRUE if already connected and not in deferred state; fails with CURLE_FAILED_INIT (done=FALSE) when there is no next filter or no peer origin. It drives the next filter's connect first if needed, then saves filter data context, checks TLS version prefs once per connection (failure yields CURLE_SSL_CONNECT_ERROR), and invokes the backend's do_connect. On success with done, it marks the filter connected, records the handshake completion time when the state is ssl_connection_complete, and logs SSLKEYLOGFILE status when key logging is enabled, with a LibreSSL TLS<=1.2 note.

calls: [ssl_prefs_check](r15-tls-cfilter.md#u-6afd0c277cfc); uses: [vtls.c-multissl](r15-tls-backend-selection.md#u-4fb380d2385e)

**Uncertainties.**

- The assertion that completion implies complete-or-deferred state suggests backend contract, not verified here.

<a id="u-20ec67fb7b0b"></a>
### `ssl_cf_connect_deferred`

`static CURLcode ssl_cf_connect_deferred(struct Curl_cfilter *cf, struct Curl_easy *da…` · [lib/vtls/vtls.c:L1045-L1095][f1]

Completes a deferred TLS connection, typically to carry early data.

Requires state ssl_connection_deferred (debug-asserted) and starts with done=FALSE. In ssl_earlydata_await state it first buffers the given data via ssl_cf_set_earlydata (propagating errors), then moves to ssl_earlydata_sending and records earlydata_skip equal to the buffered length before calling ssl_cf_connect. After a successful, complete connect it reports TIMER_APPCONNECT once for the non-proxy SSL filter, then accounts early data: accepted logs and credits earlydata_skip via Curl_pgrsEarlyData (unless proxy), rejected logs and negates the counter and zeroes earlydata_skip, none does nothing, and any other state trips a DEBUGASSERT.

calls: [ssl_cf_connect](r15-tls-cfilter.md#u-469605397018), [function::ssl_cf_set_earlydata][f1]

<a id="u-c6d800256c6c"></a>
### `ssl_cf_query`

`static CURLcode ssl_cf_query(struct Curl_cfilter *cf, struct Curl_easy *data, int que…` · [lib/vtls/vtls.c:L1232-L1266][f1]

Answers queries aimed at the SSL filter.

CF_QUERY_SSL_INFO and CF_QUERY_SSL_CTX_INFO fill a curl_tlssessioninfo with Curl_ssl_backend() and the backend get_internals (CURLINFO_TLS_SSL_PTR vs CURLINFO_TLS_SESSION per query) — but only for the non-proxy SSL filter; proxy filters fall through. CF_QUERY_ALPN_NEGOTIATED returns connssl->negotiated.alpn. All other queries, and the proxy fall-through, delegate to the next filter or return CURLE_UNKNOWN_OPTION when none exists.

calls: [Curl_ssl_backend](r15-tls-backend-selection.md#u-7cf507da57de)

<a id="u-a20fd25bbe67"></a>
### `ssl_cf_send`

`static CURLcode ssl_cf_send(struct Curl_cfilter *cf, struct Curl_easy *data, const ui…` · [lib/vtls/vtls.c:L1114-L1165][f1]

Send path of the SSL connection filter, handling deferred handshakes and TLS early data.

It always zeroes *pnwritten and saves filter data context. In deferred state it triggers ssl_cf_connect_deferred with the outgoing buffer; error propagates, incomplete connect returns CURLE_AGAIN. While earlydata_skip covers the whole buffer, the bytes are treated as already written (OK, count them) without touching the network; otherwise the skip prefix is consumed first and only the remainder is sent. Zero-length remainder is skipped because TLS libraries dislike 0-length writes; otherwise the backend send_plain result is added to *pnwritten.

calls: [ssl_cf_connect_deferred](r15-tls-cfilter.md#u-20ec67fb7b0b); uses: [vtls.c-multissl](r15-tls-backend-selection.md#u-4fb380d2385e)

<a id="u-6afd0c277cfc"></a>
### `ssl_prefs_check`

`static bool ssl_prefs_check(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vtls/vtls.c:L163-L186][f1]

Validates the configured TLS version preferences before a handshake, using the connection's ssl_filter_config.

Fails (returns FALSE with a client-side failf message) when conn_config->version is >= CURL_SSLVERSION_LAST. For version_max values other than CURL_SSLVERSION_MAX_NONE or CURL_SSLVERSION_MAX_DEFAULT, it also fails when (version_max >> 16) is below the base version, rejecting an incompatible max/version pair. Returns TRUE otherwise.

uses: [ssl_cf_connect](r15-tls-cfilter.md#u-469605397018)

<a id="u-016b38c6bda4"></a>
### `vtls_shutdown_blocking`

`static CURLcode vtls_shutdown_blocking(struct Curl_cfilter *cf, struct Curl_easy *dat…` · [lib/vtls/vtls.c:L1527-L1579][f1]

Performs a blocking, bounded SSL shutdown for a filter.

Already-shutdown filters return done=TRUE immediately. It loops up to 10 iterations while no error and not done: each iteration computes the remaining shutdown timeout; a negative timeout fails with 'SSL shutdown timeout' and CURLE_OPERATION_TIMEDOUT. It calls the backend shut_down; result or done ends the loop. If the backend still needs I/O, it polls on the connection socket: poll failure (<0) fails with CURLE_RECV_ERROR and the errno logged, zero (timeout) fails with CURLE_OPERATION_TIMEDOUT, and readiness continues the loop. Regardless of path, cf->shutdown is set to (result || done) on exit.

**Notes.**

- side_effect: Sets cf->shutdown even on failure, preventing retry loops.

uses: [vtls.c-ssl-cfilter-minor](r15-tls-cfilter.md#u-157bfad0863b)

**Uncertainties.**

- The fixed loop counter of 10 caps iterations; combined with the timeout this bounds shutdown duration, but interaction with very small timeouts is not specified here.

<a id="u-4b846ebca060"></a>
### `Curl_ssl_adjust_pollset`

`CURLcode Curl_ssl_adjust_pollset(struct Curl_cfilter *cf, struct Curl_easy *data, str…` · [lib/vtls/vtls.c:L233-L257][f1]

Updates a pollset while an SSL handshake is in progress.

When connssl->io_need is set, it fetches the underlying socket from the next filter; if the socket is valid, CURL_SSL_IO_NEED_SEND makes the pollset out-only (POLLOUT), otherwise in-only (POLLIN), with a trace log each time. A bad socket yields CURLE_OK without touching the pollset; when io_need is clear it returns CURLE_OK immediately.

**Uncertainties.**

- The return of Curl_pollset_set_* is propagated but their failure conditions are defined outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/vtls.c
