# QUIC Connection Lifecycle

**Capability.** Initializes and cleans up QUIC filter contexts, drives the connect state machine including TLS wiring and happy-eyeballs restarts, handles graceful shutdown and immediate close, liveness for reuse, timer scheduling via Curl_expire, keep-alive configuration, and settings/qlog setup.

Start here for anything about when a QUIC connection is created, reused, timed, or torn down. The 0-RTT decision on session reuse and the transport-parameter settings live here.

**Depends on.**

- [Filter Events, State and Queries](r8-cfilters-events-state.md) · model-inferred · 0 edge(s)

Parent: [QUIC via ngtcp2](r8-quic-ngtcp2.md)

## Units (15)

<a id="u-fbeb99efcf14"></a>
### `Curl_cf_ngtcp2_ctx_init`

`CURLcode Curl_cf_ngtcp2_ctx_init(struct cf_ngtcp2_ctx *ctx, struct Curl_peer *origin,…` · [lib/vquic/cf-ngtcp2-cmn.c:L118-L136][f1]

Initializes a QUIC connection filter context.

Asserts not already initialized, then resets qlogfd to -1, tunnel input buffer, version to NGTCP2_PROTO_VER_MAX, the stream buffer pool and scratch dynbuf, and initializes the stream set with h3_stream_set_free as destructor. Stores the h3-connection init callback, marks initialized, and returns the result of Curl_vquic_tls_peer_init; a peer-init failure leaves the ctx marked initialized.

uses: [h3_stream_set_free](r8-ngtcp2-h3-streams.md#u-9b1274ce72be)

<a id="u-f6f86ba2eb7e"></a>
### `Curl_cf_ngtcp2_ctx_cleanup`

`void Curl_cf_ngtcp2_ctx_cleanup(struct cf_ngtcp2_ctx *ctx)` · [lib/vquic/cf-ngtcp2-cmn.c:L138-L170][f1]

Releases all resources of an initialized QUIC filter context.

No-op if ctx is NULL or not initialized. Closes the qlog fd, cleans TLS first (comment: ngtcp2 objects may be registered there), frees the vquic io ctx, deletes the nghttp3 and ngtcp2 connections, deletes the OpenSSL QUIC ctx under OPENSSL_QUIC_API2, frees the buffer pool, scratch buffer, stream set, SSL peer data and tunnel input buffer, zeroing pointers as it goes.

<a id="u-2eafd25429ef"></a>
### `Curl_cf_ngtcp2_cmn_connect`

`CURLcode Curl_cf_ngtcp2_cmn_connect(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/vquic/cf-ngtcp2-cmn.c:L1129-L1243][f1]

Drives the QUIC connect state machine for the filter.

Returns done immediately if already connected; connects the sub-chain first and returns if that is unfinished. Delays (CURLE_OK, not done) while HTTPS-RR records are still being resolved. With no qconn yet it records the start time, runs cf_connect_start, and on success performs an initial egress pass (done only if the session-reuse path already connected the filter). With an existing qconn it runs ingress then egress, and when ngtcp2 reports handshake completion the result becomes ctx->tls_vrfy_result; only a zero verify marks cf->connected and done. Error mapping at the end: a tls_vrfy_result overrides any error; RECV/SEND errors during the draining period become CURLE_COULDNT_CONNECT, except error code NGTCP2_CONNECTION_REFUSED which becomes CURLE_WEIRD_SERVER_REPLY so the connection attempt keeps trying (server shutdown case); version-negotiation and TLS-alert errors are only traced. Finally sets the QUIC expiry and restores saved call data.

calls: [cf_connect_start](r8-ngtcp2-conn-lifecycle.md#u-bc47041aafb9), [Curl_cf_ngtcp2_progress_ingress](r8-ngtcp2-packet-io.md#u-902c04ea16f7), [Curl_cf_ngtcp2_progress_egress](r8-ngtcp2-packet-io.md#u-9fa8adcac351), [Curl_cf_ngtcp2_cmn_set_expiry](r8-ngtcp2-conn-lifecycle.md#u-8b04bd59b320)

<a id="u-62c2ba2cab8a"></a>
### `Curl_cf_ngtcp2_cmn_shutdown`

`CURLcode Curl_cf_ngtcp2_cmn_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data,…` · [lib/vquic/cf-ngtcp2-cmn.c:L1245-L1346][f1]

Gracefully shuts the QUIC connection down, returning done=TRUE when nothing remains.

No-op done if already shut down or no qconn; with no next filter it just resets the sendbuf and is done. Once per connection (shutdown_started flag): first it flushes any queued egress — if the sendbuf stays non-empty the shutdown waits (CURLE_OK, not done); on flush error it marks done. Then it writes a CONNECTION_CLOSE packet from last_error into the (asserted-empty) sendbuf, ignoring ngtcp2 write failures by design; on success it disables GSO (no_gso, gsolen=packet size, split_len=0). It then flushes the sendbuf via Curl_vquic_flush: CURLE_AGAIN waits as OK, other errors mark done; once empty the shutdown is complete.

calls: [Curl_cf_ngtcp2_progress_egress](r8-ngtcp2-packet-io.md#u-9fa8adcac351)

<a id="u-220f46099cea"></a>
### `Curl_cf_ngtcp2_cmn_conn_close`

`void Curl_cf_ngtcp2_cmn_conn_close(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vquic/cf-ngtcp2-cmn.c:L1348-L1353][f1]

Closes the QUIC connection immediately by invoking the graceful shutdown path with a discarded done flag; no additional cleanup of its own.

<a id="u-e01b2da99f65"></a>
### `Curl_cf_ngtcp2_cmn_conn_is_alive`

`bool Curl_cf_ngtcp2_cmn_conn_is_alive(struct Curl_cfilter *cf, struct Curl_easy *data…` · [lib/vquic/cf-ngtcp2-cmn.c:L1981-L2027][f1]

Liveness check for connection reuse.

Saves call data and clears *input_pending. Dead when there is no qconn or shutdown has started. If the peer announced a max_idle_timeout and the time since q.last_io exceeds it (in ms), the connection is considered dead. Otherwise it asks the next filter's is_alive; a dead sub-chain means dead. When the sub-chain reports pending input, that flag is cleared and one ingress pass runs (comment: only protocol frames should appear before a request is sent); the connection stays alive only if that pass succeeds.

calls: [Curl_cf_ngtcp2_progress_ingress](r8-ngtcp2-packet-io.md#u-902c04ea16f7)

<a id="u-bb4b53870750"></a>
### `Curl_cf_ngtcp2_cmn_cntrl`

`CURLcode Curl_cf_ngtcp2_cmn_cntrl(struct Curl_cfilter *cf, struct Curl_easy *data, in…` · [lib/vquic/cf-ngtcp2-cmn.c:L2097-L2126][f1]

Handles filter control events; currently only CF_CTRL_REPORT_STATS.

On a connected filter with stats not yet reported: for a proxy filter with a direct socket and first byte, it records TIMER_CONNECT at first_byte_at; otherwise, when a handshake time exists, it records TIMER_CONNECT at first_byte_at (direct socket only) and TIMER_APPCONNECT at handshake_at. Either way stats_reported becomes TRUE. Other events are ignored; always returns CURLE_OK.

**Notes.**

- side_effect: Sets ctx->stats_reported exactly once per connection.

<a id="u-d1fcd795f10b"></a>
### `Curl_cf_ngtcp2_cmn_query`

`CURLcode Curl_cf_ngtcp2_cmn_query(struct Curl_cfilter *cf, struct Curl_easy *data, in…` · [lib/vquic/cf-ngtcp2-cmn.c:L2068-L2095][f1]

Answers filter queries about connection timing, delegating unknown ones down the chain.

CF_QUERY_CONNECT_REPLY_MS reports the ms between connect start and first received byte, clamped to INT_MAX, only when a direct socket exists and the first byte arrived. CF_QUERY_REALLY_CONNECTED reports got_first_byte, only for a direct socket. Both fall through (as do unknown queries) to cf->next's query, or CURLE_UNKNOWN_OPTION when there is no next filter.

uses: [Curl_cf_ngtcp2_cmn_connect](r8-ngtcp2-conn-lifecycle.md#u-2eafd25429ef)

<a id="u-8b04bd59b320"></a>
### `Curl_cf_ngtcp2_cmn_set_expiry`

`CURLcode Curl_cf_ngtcp2_cmn_set_expiry(struct Curl_cfilter *cf, struct Curl_easy *dat…` · [lib/vquic/cf-ngtcp2-cmn.c:L1809-L1860][f1]

Schedules the next QUIC timer via the Curl_expire mechanism, since QUIC maintenance is not socket-POLL driven.

Creates or refreshes the io context. When ngtcp2 reports an expiry (not UINT64_MAX) that has already passed, it runs ngtcp2_conn_handle_expiry (failure: failf, Curl_cf_ngtcp2_cmn_err_set, CURLE_SEND_ERROR), then performs one ingress and one egress pass; on error the tls_vrfy_result wins over generic errors and is returned. The expiry is then re-queried, and any future expiry is converted to a millisecond timeout rounded up to whole milliseconds and armed with Curl_expire_set.

calls: [Curl_cf_ngtcp2_cmn_err_set](r8-ngtcp2-errors-tls.md#u-5cbaff237170), [Curl_cf_ngtcp2_progress_ingress](r8-ngtcp2-packet-io.md#u-902c04ea16f7), [Curl_cf_ngtcp2_progress_egress](r8-ngtcp2-packet-io.md#u-9fa8adcac351)

<a id="u-bc47041aafb9"></a>
### `cf_connect_start`

`static CURLcode cf_connect_start(struct Curl_cfilter *cf, struct Curl_easy *data, str…` · [lib/vquic/cf-ngtcp2-cmn.c:L987-L1127][f1]

Creates the ngtcp2 client connection and wires TLS; may run twice for happy eyeballs.

Generates random dcid and scid (aborting on randomness failure), opens the qlog fd via Curl_qlogdir (qlogfd stays -1 on failure), builds settings via quic_settings, and initializes the vquic io ctx. Socket sourcing: if Curl_cf_socket_peek yields a socket it takes the local address via getsockname (failure: CURLE_QUIC_CONNECT_ERROR) and builds the connected path from local/remote addresses; otherwise (tunneled CONNECT-UDP) it queries the next filter for the remote address and synthesizes a local address matching AF_INET/AF_INET6, failing with CURLE_QUIC_CONNECT_ERROR for other families. Creates the client connection with ngtcp2_conn_client_new (failure: CURLE_QUIC_CONNECT_ERROR), sets conn_ref/get_conn, and initializes TLS with the fixed h3/h3-29 ALPN spec and the session-reuse/setup callbacks. Per-backend it creates/attaches the native TLS handle (OpenSSL QUIC_API2 also creates the ossl ctx and configures the client session; legacy OpenSSL disables the legacy QUIC codepoint). Finally, under OpenSSL QUIC_API2 with early data, if SSL refuses early data it clears use_earlydata and cf->connected. Sets last_error default and returns CURLE_OK.

calls: [quic_settings](r8-ngtcp2-conn-lifecycle.md#u-5f79c7f95667); uses: [get_conn](r8-ngtcp2-errors-tls.md#u-ecc550fdfd50), [cf_ngtcp2_tls_ctx_setup](r8-ngtcp2-conn-lifecycle.md#u-000aaf77ac62), [cf_ngtcp2_on_session_reuse](r8-ngtcp2-conn-lifecycle.md#u-38fc50b908cf)

<a id="u-38fc50b908cf"></a>
### `cf_ngtcp2_on_session_reuse`

`static CURLcode cf_ngtcp2_on_session_reuse(struct Curl_cfilter *cf, struct Curl_easy …` · [lib/vquic/cf-ngtcp2-cmn.c:L917-L982][f1]

Decides whether a reused TLS session permits 0-RTT early data and, if so, prepares the connection for it.

Sets *do_early_data FALSE first and reads earlydata_max per backend (session field for OpenSSL-with-earlydata and wolfSSL-with-WOLFSSL_EARLY_DATA, gnutls_record_get_max_early_data_size for GnuTLS, 0 for wolfSSL without the feature). Early data is then enabled only if earlydata_max is non-zero, the session's ALPN is contained in the offered alpn spec, and the session carries 0-RTT transport parameters that ngtcp2_conn_decode_and_set_0rtt_transport_params accepts. On success it initializes the h3 connection via ctx->init_h3_conn_cb when set, or assumes readiness when not, then sets use_earlydata, cf->connected and *do_early_data. Any failed precondition just logs and disables early data; TLS backends without support do nothing.

**Uncertainties.**

- The exact combination of backend macros compiled in is not visible here; multiple branches are mutually exclusive per build.

<a id="u-000aaf77ac62"></a>
### `cf_ngtcp2_tls_ctx_setup`

`static CURLcode cf_ngtcp2_tls_ctx_setup(struct Curl_cfilter *cf, struct Curl_easy *da…` · [lib/vquic/cf-ngtcp2-cmn.c:L861-L915][f1]

Configures the TLS backend's client context for ngtcp2 crypto.

OpenSSL: configures the ssl_ctx via the boringssl/quictls configure call (OPENSSL_QUIC_API2 needs nothing), failing with CURLE_FAILED_INIT and a failf message on error; when the session cache is usable it enables client session caching in external-storage mode and installs quic_ossl_new_session_cb. GnuTLS: configures the client session and installs quic_gtls_handshake_cb as a post hook when caching is enabled. wolfSSL: configures the context and registers wssl_quic_new_session_cb. Returns CURLE_OK on success.

uses: [quic_ossl_new_session_cb](r8-ngtcp2-errors-tls.md#u-2d40106e3183), [quic_gtls_handshake_cb](r8-ngtcp2-errors-tls.md#u-2d12c53a5aa5), [wssl_quic_new_session_cb](r8-ngtcp2-errors-tls.md#u-e28b505b533f)

<a id="u-aafa1ab3032e"></a>
### `cf_ngtcp2_setup_keep_alive`

`static void cf_ngtcp2_setup_keep_alive(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vquic/cf-ngtcp2-cmn.c:L1862-L1897][f1]

Configures the QUIC keep-alive so a peer's idle timeout cannot silently kill an idle HTTP/3 connection.

Returns early without a qconn. If the peer announced no max_idle_timeout, or there are no active streams, it disables keep-alive (UINT64_MAX). Otherwise it sets the keep-alive timeout to half the peer's idle timeout, or 1ns when that is 1 or less.

**Notes.**

- condition: Stream count is read from ctx->streams via Curl_u32_ptrset_count.

<a id="u-5f79c7f95667"></a>
### `quic_settings`

`static void quic_settings(struct cf_ngtcp2_ctx *ctx, struct Curl_easy *data, struct c…` · [lib/vquic/cf-ngtcp2-cmn.c:L229-L265][f1]

Populates ngtcp2 settings and transport parameters for a connection attempt.

Resets both to defaults; log_printf is quic_printf under DEBUG_NGTCP2 else NULL. Handshake timeout is the user connect timeout in ms when set, else QUIC_HANDSHAKE_TIMEOUT. Sets max_window to H3_CONN_WINDOW_SIZE_MAX, disables ngtcp2 stream-window auto-tuning, enables PMTUD, and under NGTCP2_SETTINGS_V3 raises glitch rate limits to 10x ngtcp2 defaults (comment: Caddy workaround). Transport params mirror these: initial data/stream windows, QUIC_MAX_STREAMS for bidi and uni, and no idle timeout from our side. Installs qlog_callback when qlogfd is open.

uses: [qlog_callback](r8-ngtcp2-errors-tls.md#u-fb664a96c9e0)

<a id="u-7e7cf4fee714"></a>
### `Curl_ngtcp2_ver`

`void Curl_ngtcp2_ver(char *p, size_t len)` · [lib/vquic/cf-ngtcp2-cmn.c:L78-L84][f1]

Formats the ngtcp2 and nghttp3 library version strings into a caller buffer.

Queries both libraries via their version(0) entry points and curl_msnprintf's 'ngtcp2/<v> nghttp3/<v>' into p limited by len; no error path.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-ngtcp2-cmn.c
