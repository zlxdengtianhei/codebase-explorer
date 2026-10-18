# Connection Filter Setup

**Capability.** Owns construction and staged driving of the connection filter chain: the SETUP filter decides which proxy (HTTP, SOCKS, HAProxy), Happy-Eyeballs and origin transport filters to insert, in state-machine order, and how the first hop's peer is resolved.

Use this subtree to understand how a connection's filter stack is assembled and connected before data flows. cf-setup.c builds and drives the chain per state; proxy.h supplies the proxy description type; cf-recvbuf.h declares a receive-buffer filter used elsewhere in the chain.

Parent: [curl Codebase](r10-curl-source.md)

## Units (14)

<a id="u-26bd7939e17d"></a>
### `cf-recvbuf-h`

`group` · [lib/cf-recvbuf.h:L1-L40][f1]

Declares a receive-buffer connection filter used to push buffered bytes back into a connection's receive path.

Contents are guarded by !CURL_DISABLE_WEBSOCKETS; only a single add function and the filter type are exposed.

imports: [cf-recvbuf-h](r10-connection-filters.md#u-26bd7939e17d)

**Uncertainties.**

- Implementations of Curl_cf_recvbuf_add are not in this header.

<a id="u-febba2df8592"></a>
### `proxy_info`

`struct proxy_info` · [lib/proxy.h:L35-L39][f2]

Declares proxy_info, the per-connection proxy description: a peer endpoint to connect through, optional credentials, and a uint8_t proxy type.

Also defines CURL_PROXY_IS_HTTPS, CURL_PROXY_IS_HTTP, and CURL_PROXY_IS_ANY_HTTP as type-classification macros over CURLPROXY_* values, and prototypes Curl_proxy_init_conn. The whole header compiles to nothing when CURL_DISABLE_PROXY is defined.

**Uncertainties.**

- The header was parsed as C due to an ambiguous-language diagnostic; semantics are unaffected by the shown content.

<a id="u-dcee4420e014"></a>
### `Curl_cf_setup_add`

`CURLcode Curl_cf_setup_add(struct Curl_easy *data, struct connectdata *conn, int8_t s…` · [lib/cf-setup.c:L446-L462][f3]

Public entry that creates a SETUP filter for the given transport and ssl_mode and adds it to the connection's filter chain at the given sockindex via Curl_conn_cf_add.

Returns the creation error if the filter cannot be created; otherwise the add's outcome is not checked here.

calls: [lib-cfilters-c-chain-management](r8-cfilters-chain-mgmt.md#u-f10f9ecb03f8)

**Uncertainties.**

- Return value of Curl_conn_cf_add is ignored, so add failure is not reported

<a id="u-ec75d906f746"></a>
### `Curl_cf_setup_insert_after`

`CURLcode Curl_cf_setup_insert_after(struct Curl_cfilter *cf_at, struct Curl_easy *dat…` · [lib/cf-setup.c:L464-L479][f3]

Public entry that creates a SETUP filter and inserts it into a filter chain immediately after the given filter cf_at via Curl_conn_cf_insert_after.

Propagates creation errors; the insertion call's result is not checked.

calls: [lib-cfilters-c-chain-management](r8-cfilters-chain-mgmt.md#u-f10f9ecb03f8)

**Uncertainties.**

- Return value of Curl_conn_cf_insert_after is ignored

<a id="u-98475cf005e5"></a>
### `cf_setup_add_haproxy`

`static CURLcode cf_setup_add_haproxy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-setup.c:L59-L82][f3]

Adds the HAProxy protocol filter to the connection filter chain once per setup context.

Skipped when the ctx state has already reached CF_SETUP_CNNCT_HAPROXY or when haproxyprotocol is disabled. If the transport is QUIC and the protocol is enabled, it fails with failf and CURLE_UNSUPPORTED_PROTOCOL. On filter insertion failure it logs and returns the error; success advances the state to CF_SETUP_CNNCT_HAPROXY (even when the filter was not added).

calls: [Curl_cf_haproxy_insert_after](r5-haproxy-filter.md#u-d393f41ba7db)

**Uncertainties.**

- Exact struct fields of conn->set.haproxyprotocol are outside this file

<a id="u-0f2a75571c39"></a>
### `cf_setup_add_http_proxy`

`static CURLcode cf_setup_add_http_proxy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-setup.c:L117-L155][f3]

Adds the HTTP proxy tunnel filter when the state is before CF_SETUP_CNNCT_HTTP_PROXY, an http_proxy peer exists, and the origin is not itself a proxy.

Under USE_SSL, an HTTPS proxy type on a non-SSL socket first inserts an SSL proxy filter; its failure is logged and returned. Then the tunnel filter is inserted with the destination peer, transport, and proxy type; failure is logged and returned, while success logs and sets the state to CF_SETUP_CNNCT_HTTP_PROXY. Both the HTTP and proxy guards can remove this whole body from the build.

calls: [Curl_cf_http_proxy_insert_after](r8-http-proxy-filter.md#u-9906cddf885b), [connect.c-peer-selection-accessors](r6-connection-management.md#u-53e13e98e75a)

**Uncertainties.**

- Curl_cf_ssl_proxy_insert_after behavior is not visible in this file

<a id="u-86bf9c8cf2f8"></a>
### `cf_setup_add_ip_happy`

`static CURLcode cf_setup_add_ip_happy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-setup.c:L173-L226][f3]

Adds the Happy Eyeballs (eyeballer) filter once, only while the state is before CF_SETUP_CNNCT_EYEBALLS.

It resolves the first origin and first peer; a missing first peer returns CURLE_FAILED_INIT. When an HTTP proxy (not origin-as-proxy) is configured, the first-hop transport is derived from the proxy type, the tunnel peer becomes the destination, and a QUIC transport combined with a SOCKS peer fails with CURLE_UNSUPPORTED_PROTOCOL. The eyeball filter is inserted with first origin, first peer, first transport, tunnel peer, and the ctx transport; insertion failure is logged and returned. On success, if tunneling to an HTTP/3 proxy the state jumps to CF_SETUP_CNNCT_HTTP_PROXY, otherwise it becomes CF_SETUP_CNNCT_EYEBALLS.

calls: [Curl_cf_ip_happy_insert_after](r1-happy-eyeballs-filter.md#u-5688d6215cb9), [connect.c-peer-selection-accessors](r6-connection-management.md#u-53e13e98e75a), [conn_get_first_origin](r10-connection-filters.md#u-e701d9ef0358); uses: [Curl_http_proxy_transport](r8-http-proxy-filter.md#u-fd2dad2a4383)

**Uncertainties.**

- Difference between first_origin and first_peer relies on --connect-to semantics described in the comment, not verifiable here

<a id="u-4db986da79fa"></a>
### `cf_setup_add_origin_filters`

`static CURLcode cf_setup_add_origin_filters(struct Curl_cfilter *cf, struct Curl_easy…` · [lib/cf-setup.c:L228-L297][f3]

Adds origin-facing transport filters once, before state reaches CF_SETUP_CNNCT_SSL.

In HTTP3-capable non-proxy-disabled builds, QUIC transport over an HTTP tunnel first inserts a capsule filter and then a QUIC filter with origin and destination peers; either failure is logged and returned. Otherwise, under USE_SSL, an SSL filter is added when SSL is wanted (ssl_mode CURL_CF_SSL_ENABLE, or not CURL_CF_SSL_DISABLE and the protocol flag demands SSL) and the socket is not yet SSL; for origin-as-proxy connections an SSL proxy filter on conn->origin is used, otherwise a regular SSL filter instantiated with the FIRSTSOCKET origin and destination peers so FTP data connections can reuse TLS sessions. Failures are logged and returned; on the non-QUIC path the state always advances to CF_SETUP_CNNCT_SSL after the guarded block.

**Notes.**

- field: ctx->ssl_mode values CURL_CF_SSL_ENABLE/DISABLE select whether the SSL filter is forced or suppressed

contract: [cf_setup_add_ip_happy](r10-connection-filters.md#u-86bf9c8cf2f8)

**Uncertainties.**

- Curl_cf_capsule_insert_after, Curl_cf_quic_insert_after, Curl_cf_ssl_insert_after internals are external

<a id="u-4386205bd86f"></a>
### `cf_setup_add_socks`

`static CURLcode cf_setup_add_socks(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-setup.c:L84-L114][f3]

Adds a SOCKS proxy filter when the setup state is earlier than CF_SETUP_CNNCT_SOCKS and a socks_proxy peer is configured.

The tunnel endpoint is the http_proxy peer if present, otherwise the connection destination; a missing destination yields CURLE_FAILED_INIT. The SOCKS filter is inserted with the connection's ip_version, proxy type, and credentials; insertion failure is logged and returned. Success logs the target host/port and sets state to CF_SETUP_CNNCT_SOCKS. Compiled only when proxies are not disabled.

calls: [Curl_cf_socks_proxy_insert_after](r8-socks-filter-wiring.md#u-53c09c3f7ba2), [connect.c-peer-selection-accessors](r6-connection-management.md#u-53e13e98e75a)

<a id="u-ec55ebf63aa9"></a>
### `cf_setup_connect`

`static CURLcode cf_setup_connect(struct Curl_cfilter *cf, struct Curl_easy *data, boo…` · [lib/cf-setup.c:L361-L387][f3]

Wraps cf_setup_connect_steps with retry handling.

On CURLE_AGAIN it increments ctx->retry_count; past five retries (arbitrary limit) it returns CURLE_COULDNT_CONNECT. Otherwise it discards the whole sub-chain below the SETUP filter via Curl_conn_cf_discard_chain, resets the state to CF_SETUP_INIT, and restarts the connect steps, so a dropped connection rebuilds filters from scratch.

calls: [cf_setup_connect_steps](r10-connection-filters.md#u-a060cbf1783c), [Curl_conn_cf_discard_chain](r8-cfilters-chain-mgmt.md#u-ce0a99eddf7a)

**Uncertainties.**

- Comment notes the retry limit may be better served by a timeout; exact retry semantics of underlying filters are external

<a id="u-a060cbf1783c"></a>
### `cf_setup_connect_steps`

`static CURLcode cf_setup_connect_steps(struct Curl_cfilter *cf, struct Curl_easy *dat…` · [lib/cf-setup.c:L299-L359][f3]

Drives one pass of building and connecting the filter chain below the SETUP filter.

Already-connected filters set done and return immediately. It loops (via goto connect_sub_chain) connecting the current sub-chain with Curl_conn_cf_connect whenever cf->next exists and is not connected, then progressively inserts filters in order: Happy Eyeballs, SOCKS, HTTP proxy, HAProxy, and origin filters (SSL/QUIC), re-entering the loop after each insertion whenever cf->next is absent or not yet connected, so each newly added filter is connected before the next is added. Any filter-add or connect error aborts with that result. Only when everything below is connected does it set ctx->state to CF_SETUP_DONE, mark cf->connected, and set done to TRUE.

calls: [lib-cfilters-c-dispatch-wrappers](r8-cfilters-io.md#u-4223d3ac73f1), [Curl_conn_trc_filters](r8-cfilters-events-state.md#u-e3074e0eb59a), [cf_setup_add_ip_happy](r10-connection-filters.md#u-86bf9c8cf2f8), [cf_setup_add_socks](r10-connection-filters.md#u-4386205bd86f), [cf_setup_add_http_proxy](r10-connection-filters.md#u-0f2a75571c39), [cf_setup_add_haproxy](r10-connection-filters.md#u-98475cf005e5), [cf_setup_add_origin_filters](r10-connection-filters.md#u-4db986da79fa)

<a id="u-39698fcee6a5"></a>
### `cf_setup_create`

`static CURLcode cf_setup_create(struct Curl_cfilter **pcf, struct Curl_easy *data, ui…` · [lib/cf-setup.c:L414-L444][f3]

Allocates a zeroed cf_setup_ctx, initializes state to CF_SETUP_INIT plus the given transport and ssl_mode, and attaches it to a new filter using the Curl_cft_setup type.

On allocation failure it returns CURLE_OUT_OF_MEMORY; on Curl_cf_create failure the ctx is freed. On success ownership of ctx transfers to the filter, and *pcf receives the new filter (NULL on any failure).

calls: [Curl_cf_create](r8-cfilters-chain-mgmt.md#u-e3a618a4a2af)

<a id="u-84b38b589481"></a>
### `cf_setup_destroy`

`static void cf_setup_destroy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-setup.c:L389-L395][f3]

Filter destructor that logs and frees the cf_setup_ctx allocated for the SETUP filter.

<a id="u-e701d9ef0358"></a>
### `conn_get_first_origin`

`static struct Curl_peer *conn_get_first_origin(struct connectdata *conn, int8_t socki…` · [lib/cf-setup.c:L161-L171][f3]

Returns the peer of the first hop the socket connects to: the SOCKS proxy peer if set, else the HTTP proxy peer if set, else origin2 on the secondary socket or origin otherwise.

Proxy branches are removed in no-proxy builds.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cf-recvbuf.h
[f2]: ../../../../../../eval/curl-2c04412/lib/proxy.h
[f3]: ../../../../../../eval/curl-2c04412/lib/cf-setup.c
