# HTTP/HTTPS Proxy Filter

**Capability.** Implements the HTTP-PROXY connection filter: building CONNECT and CONNECT-UDP (MASQUE) tunnel requests with custom headers and negotiated HTTP version, inspecting tunnel responses for auth retries, and installing version-specific sub-filters on connect.

Read this subtree to follow how a plain or secure HTTP proxy tunnel is established, including user-configured header injection and tunnel response classification. It uses the filter chain API to insert itself and queries transport metadata to pick QUIC vs TCP.

**Depends on.**

- [Auth Core Helpers](r8-auth-core.md) · graph-confirmed · 1 edge(s)
- [Filter Chain Lifecycle](r8-cfilters-chain-mgmt.md) · graph-confirmed · 2 edge(s)
- [Filter Events, State and Queries](r8-cfilters-events-state.md) · graph-confirmed · 1 edge(s)

Parent: [Proxy Tunneling](r8-proxy-tunneling.md)

## Units (13)

<a id="u-9906cddf885b"></a>
### `Curl_cf_http_proxy_insert_after`

`CURLcode Curl_cf_http_proxy_insert_after(struct Curl_cfilter *cf_at, struct Curl_easy…` · [lib/http_proxy.c:L723-L757][f1]

Creates and inserts an HTTP-PROXY filter after cf_at.

Returns CURLE_FAILED_INIT if either peer pointer is NULL. Allocates a zeroed context, links copies of the proxy and tunnel peers into it, stores proxytype and tunnel_transport, creates the filter via Curl_cf_create, and inserts it after cf_at with Curl_conn_cf_insert_after. On any failure the freshly allocated context is freed (peers unlinked) and the error returned; on success the ownership moved to the filter so freeing the local pointer is a no-op (ctx set to NULL).

calls: [Curl_cf_create](r8-cfilters-chain-mgmt.md#u-e3a618a4a2af), [lib-cfilters-c-chain-management](r8-cfilters-chain-mgmt.md#u-f10f9ecb03f8), [Curl_peer_link](r3-peer-identity.md#u-cdc53111cd17)

<a id="u-d9526d146efd"></a>
### `Curl_http_proxy_create_tunnel_request`

`CURLcode Curl_http_proxy_create_tunnel_request( struct httpreq **preq, struct Curl_cf…` · [lib/http_proxy.c:L442-L459][f1]

Public dispatcher that builds either a plain CONNECT or a CONNECT-UDP request depending on udp_tunnel, then logs the tunnel target.

Delegates to http_proxy_create_CONNECTUDP or http_proxy_create_CONNECT with the same arguments; a delegate error propagates unchanged. On success it logs 'Establishing <HTTP|HTTP/2|HTTP/3> proxy [UDP ]tunnel to host:port' and returns CURLE_OK.

calls: [http_proxy_create_CONNECT](r8-http-proxy-filter.md#u-b40e76d595a6), [http_proxy_create_CONNECTUDP](r8-http-proxy-filter.md#u-db8fa748014d)

<a id="u-d599df548f75"></a>
### `Curl_http_proxy_inspect_tunnel_response`

`CURLcode Curl_http_proxy_inspect_tunnel_response( struct Curl_cfilter *cf, struct Cur…` · [lib/http_proxy.c:L461-L543][f1]

Classifies a proxy tunnel response and drives auth retry decisions.

It logs the status and all response headers, then: on status 407 it looks up Proxy-Authenticate; if present it forwards the challenge to Curl_http_input_auth (error propagates) and, when data->req.newurl was set, clears it and reports PROXY_INSPECT_AUTH_RETRY. For UDP tunnels, a 2xx response is success when the capsule-protocol value is exactly '?1' (PROXY_INSPECT_OK) or when no capsule-protocol header exists at all (also OK, tolerating proxies that omit it); any other capsule value fails with PROXY_INSPECT_FAILED and CURLE_COULDNT_CONNECT. Non-2xx UDP responses likewise fail. For plain CONNECT, any 2xx status is PROXY_INSPECT_OK; otherwise PROXY_INSPECT_FAILED with CURLE_COULDNT_CONNECT.

**Notes.**

- failure: CURLE_COULDNT_CONNECT is returned only for final failures; auth retry is signalled via *presult, not the return code.

calls: [Curl_dynhds_cget](r10-dynamic-headers.md#u-6dad57e59440), [Curl_http_input_auth](r6-http-response-processing.md#u-06479200bfce)

**Uncertainties.**

- Whether callers retry based on PROXY_INSPECT_AUTH_RETRY is outside this file.

<a id="u-fd2dad2a4383"></a>
### `Curl_http_proxy_transport`

`uint8_t Curl_http_proxy_transport(uint8_t proxytype)` · [lib/http_proxy.c:L759-L767][f1]

Maps a proxy type to its underlying transport: CURLPROXY_HTTPS3 uses TRNSPRT_QUIC; every other proxy type uses TRNSPRT_TCP.

<a id="u-4caa6eecc742"></a>
### `cf_http_proxy_query`

`static CURLcode cf_http_proxy_query(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/http_proxy.c:L663-L685][f1]

Answers filter queries for the HTTP-PROXY filter.

CF_QUERY_HOST_PORT returns the tunnel destination's port in *pres1 and hostname via pres2. CF_QUERY_ALPN_NEGOTIATED always reports no ALPN (NULL) because ALPN is handled inside this filter. All other queries forward to the next filter, or return CURLE_UNKNOWN_OPTION when there is none.

<a id="u-d29617dcd073"></a>
### `cf_https_proxy_ctx_free`

`static void cf_https_proxy_ctx_free(struct cf_proxy_ctx *ctx)` · [lib/http_proxy.c:L687-L694][f1]

Releases a cf_proxy_ctx: unlinks both peer references and frees the struct.

Safe to call with NULL.

calls: [Curl_peer_unlink](r3-peer-identity.md#u-63430ed0e6c2)

<a id="u-09e094317f66"></a>
### `dynhds_add_custom`

`static CURLcode dynhds_add_custom(struct Curl_easy *data, bool is_connect, int httpve…` · [lib/http_proxy.c:L41-L176][f1]

Collects user-configured custom headers into a dynhds list for an outgoing proxy or server request, applying curl's header quirks and suppression rules.

The proxy context picked depends on the flags: connect without UDP selects HEADER_CONNECT, connect with UDP selects HEADER_CONNECT_UDP, otherwise HEADER_PROXY when the origin uses a proxy, else HEADER_SERVER. For HEADER_PROXY, data->set.proxyheaders is scanned additionally when sep_headers is set; for CONNECT cases the proxy list is used when sep_headers, else the normal list. Each slist entry is parsed with a name up to ':' or ';': 'name:' with empty value suppresses the header (quirk 1); 'name;' with empty tail sends an empty value (quirk 2); anything else after ';' or no delimiter is silently skipped, as is an empty name. The trimmed name is skipped when it is Host while http_host is set, Content-Type during POST_FORM/POST_MIME, Content-Length during auth negotiation, Transfer-Encoding on HTTP/2+ (no chunked there), or Authorization/Cookie when Curl_auth_allowed_to_host rejects the host. Surviving entries are appended via Curl_dynhds_add; on its error the function returns immediately with that code.

**Notes.**

- side_effect: Appends to the caller-provided dynhds in list order; no other state is modified.

uses: [Curl_checkProxyheaders](r6-http-request-build.md#u-d4ede5b0c4c2); calls: [Curl_dynhds_add](r10-dynamic-headers.md#u-d5f87d712974), [Curl_auth_allowed_to_host](r8-auth-core.md#u-36ccb0ce8dab)

**Uncertainties.**

- The h[2] array is only partially initialized for HEADER_SERVER and HEADER_CONNECT paths (numlists stays 1), so behavior is safe only if the compiler zero-initializes the stack array; this is not guaranteed by the visible source.

<a id="u-6f1ac63ad667"></a>
### `http_proxy_cf_connect`

`static CURLcode http_proxy_cf_connect(struct Curl_cfilter *cf, struct Curl_easy *data…` · [lib/http_proxy.c:L545-L661][f1]

Connect filter for HTTP proxies: connects the sub-chain, then installs the version-specific tunnel protocol filter based on ALPN.

If already connected it sets *done immediately. udp_tunnel is derived from ctx->tunnel_transport via TRNSPRT_IS_DGRAM. After the next filter's do_connect succeeds with done, it installs a sub-filter once (guarded by ctx->sub_filter_installed): ALPN is taken from the next filter, or faked from ctx->proxytype (HTTP_1_0 -> http/1.0, HTTPS2 -> h2, HTTPS3 -> h3, default http/1.1). http/1.0 and http/1.1 install Curl_cf_h1_proxy_insert_after (version 10 or 11, the latter also for the 1_0 proxytype quirk mapping to 11), 'h2' installs Curl_cf_h2_proxy_insert_after when built with nghttp2, 'h3' installs the h3 proxy filter under the QUIC build guards; any other ALPN fails with CURLE_COULDNT_CONNECT. After installation it jumps back to connect the sub-chain again; once sub_filter_installed and connected, cf->connected is set TRUE and *done TRUE on success. Sub-filter install errors propagate.

calls: [cf-h1-proxy-c-cftype-and-factory](r3-h1-proxy-tunnel.md#u-901a35be6b63), [lib-cfilters-c-transport-mapping](r8-cfilters-events-state.md#u-9a6bc0bfdce5); uses: [cf-h2-proxy.h module code (L1–L40)][f2]

**Uncertainties.**

- The h3 branch (Curl_cf_h3_proxy_insert_after) is compiled only under USE_PROXY_HTTP3 and related guards, so its behavior cannot be confirmed from this file.
- The faked-ALPN branch has 'else if(!alpn)' after checking 'if(alpn)', so the else-if condition is always true there; intent versus redundancy is unconfirmed.

<a id="u-1416bd50ae83"></a>
### `http_proxy_cf_destroy`

`static void http_proxy_cf_destroy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/http_proxy.c:L696-L704][f1]

Filter destroy callback: logs the destroy event and delegates context release to cf_https_proxy_ctx_free when a context exists.

calls: [cf_https_proxy_ctx_free](r8-http-proxy-filter.md#u-d29617dcd073)

<a id="u-b40e76d595a6"></a>
### `http_proxy_create_CONNECT`

`static CURLcode http_proxy_create_CONNECT(struct httpreq **preq, struct Curl_cfilter …` · [lib/http_proxy.c:L199-L276][f1]

Builds the HTTP CONNECT request for a classic proxy tunnel to dest, using the negotiated proxy HTTP version.

The authority is 'host:port' with brackets added around IPv6 hostnames; allocation failure yields CURLE_OUT_OF_MEMORY. After Curl_http_req_make creates a CONNECT request, Curl_http_output_auth attaches proxy authorization. Unless the user supplies their own Host header, HTTP/1.x CONNECTs get Host set to the authority; the stored hd_proxy_auth line is added verbatim; User-Agent is added when not user-overridden and non-empty; HTTP/1.x also gets 'Proxy-Connection: Keep-Alive' when not overridden. Finally dynhds_add_custom merges custom headers with is_connect=TRUE, is_udp=FALSE. Any failure frees the request and sets *preq to NULL; on success *preq receives the built request.

calls: [dynhds_add_custom](r8-http-proxy-filter.md#u-09e094317f66), [http-c-httpreq-lifecycle](r6-http-req-resp-objects.md#u-4a9c07117d37), [Curl_checkProxyheaders](r6-http-request-build.md#u-d4ede5b0c4c2); uses: [function::Curl_http_output_auth][f3]

<a id="u-db8fa748014d"></a>
### `http_proxy_create_CONNECTUDP`

`static CURLcode http_proxy_create_CONNECTUDP(struct httpreq **preq, struct Curl_cfilt…` · [lib/http_proxy.c:L278-L440][f1]

Builds the CONNECT-UDP (RFC 9298 MASQUE) tunnel request.

Proxy scheme is 'https' when the configured proxytype is CURLPROXY_HTTPS/HTTPS2/HTTPS3, else 'http'. The authority uses the peer (proxy) host with IPv6 brackets; the path is /.well-known/masque/udp/<dest host>/<port>/, percent-encoding each ':' of an IPv6 dest host as %3A using a manually sized (len*3+1) buffer. Method depends on version: GET with full URL parts for PROXY_HTTP_V1, CONNECT for V2/V3, any other version returns CURLE_FAILED_INIT. Proxy auth is attached, then HTTP/1.x requests additionally get Host (unless overridden), User-Agent (V1 only), Proxy-Connection, Connection: Upgrade, Upgrade: connect-udp, Capsule-Protocol: ?1; V2/V3 instead get the :Protocol connect-udp pseudo header plus Capsule-Protocol for ver >= V2. dynhds_add_custom runs with is_udp=TRUE. All allocation failures return CURLE_OUT_OF_MEMORY; on any failure the request is freed and *preq set to NULL.

calls: [dynhds_add_custom](r8-http-proxy-filter.md#u-09e094317f66), [http-c-httpreq-lifecycle](r6-http-req-resp-objects.md#u-4a9c07117d37), [Curl_checkProxyheaders](r6-http-request-build.md#u-d4ede5b0c4c2)

**Uncertainties.**

- The encoded_host buffer of hlen*3+1 is sufficient only because each source byte expands to at most 3 bytes and only ':' expands; other bytes pass through unchanged.

<a id="u-6cecedaad805"></a>
### `proxy_http_ver_major`

`static int proxy_http_ver_major(proxy_http_ver ver)` · [lib/http_proxy.c:L186-L197][f1]

Maps a proxy_http_ver enum value to the numeric HTTP major-minor version code: PROXY_HTTP_V1 to 11, V2 to 20, V3 to 30.

Returns 0 for any other value, which callers use as an httpversion input to dynhds_add_custom (0 < 20, so HTTP/1.x rules apply).

<a id="u-409e432ef6dd"></a>
### `cf_proxy_ctx`

`struct cf_proxy_ctx` · [lib/http_proxy.c:L178-L184][f1]

Per-filter context for the HTTP-PROXY connection filter, holding linked references to the proxy peer and the tunnel destination peer, the configured proxy type and tunnel transport ids, and a flag recording whether the protocol sub-filter has been installed below this filter.

Peer links are created by Curl_peer_link in Curl_cf_http_proxy_insert_after and released via Curl_peer_unlink in cf_https_proxy_ctx_free.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http_proxy.c
[f2]: ../../../../../../eval/curl-2c04412/lib/cf-h2-proxy.h
[f3]: ../../../../../../eval/curl-2c04412/lib/http.c
