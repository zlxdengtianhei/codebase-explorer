# SOCKS Filter Wiring

**Capability.** Wires the SOCKS handshake into the connection-filter framework: the 'SOCKS' filter type table, create/insert-after and destroy callbacks, context release, pollset adjustment keyed on handshake state, and filter queries for host/port and ALPN.

Use this subtree to see how the SOCKS filter is installed in a filter chain and how the multi interface polls it while the handshake is in progress. The connect callback defers to the next filter until TCP is established, then drives the handshake.

**Depends on.**

- [SOCKS4/5 Handshake State Machine](r8-socks-handshake.md) · graph-confirmed · 2 edge(s)

Parent: [SOCKS Proxy Filter](r8-socks-proxy-filter.md)

## Units (11)

<a id="u-53c09c3f7ba2"></a>
### `Curl_cf_socks_proxy_insert_after`

`CURLcode Curl_cf_socks_proxy_insert_after(struct Curl_cfilter *cf_at, struct Curl_eas…` · [lib/socks.c:L1330-L1390][f1]

Creates and inserts a SOCKS proxy connection filter after cf_at for the given destination, credentials, and proxy type.

Proxy type determines local resolution: SOCKS5 and SOCKS4 resolve locally (with SOCKS4 clearing the AAAA query bit since it is IPv4-only); SOCKS5_HOSTNAME and SOCKS4A resolve remotely at the proxy; unknown types fail with CURLE_COULDNT_CONNECT after logging. The zeroed context takes a linked reference to dest and creds, records ip_version/proxy_type/resolve_local, and initializes the buffer queue with soft-limit chunking. On successful filter creation the filter is inserted and, for local resolution, an address-resolution job is added for the connection; on creation failure the context is freed. NULL dest fails with CURLE_FAILED_INIT; allocation failure returns CURLE_OUT_OF_MEMORY.

**Uncertainties.**

- Whether the resolve job addition failing after insertion leaves the inserted filter in place is not handled in the visible code; the result is returned either way.

<a id="u-66221ba1fc0a"></a>
### `socks_proxy_cf_connect`

`static CURLcode socks_proxy_cf_connect(struct Curl_cfilter *cf, struct Curl_easy *dat…` · [lib/socks.c:L1182-L1247][f1]

Connection-filter connect callback: if the filter is already connected it reports done immediately; otherwise it delegates to the next filter's do_connect and returns early on error or incomplete TCP connection.

Once TCP is up, it dispatches to socks5_connect for CURLPROXY_SOCKS5/SOCKS5_HOSTNAME or socks4_connect for SOCKS4/SOCKS4A; an unexpected type (guarded by DEBUGASSERT, checked at creation) fails with CURLE_COULDNT_CONNECT. A nonzero proxy code is converted to CURLE_PROXY with the code stored in data->info.pxcode; a handshake not yet at SOCKS_ST_SUCCESS returns CURLE_OK with done FALSE to resume later. On success, verbose mode logs the opened tunnel (with the 2nd-connection prefix for SECONDARYSOCKET; IP info unavailable falls back to a shorter message) and cf->connected is set. done always reflects cf->connected, and credentials are unlinked when done or on error.

<a id="u-01367e385807"></a>
### `socks_proxy_cf_destroy`

`static void socks_proxy_cf_destroy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/socks.c:L1277-L1283][f1]

Filter destroy callback that frees the socks_ctx via socks_proxy_ctx_free and clears cf->ctx.

<a id="u-5ab98fe10e2d"></a>
### `socks_proxy_ctx_free`

`static void socks_proxy_ctx_free(struct socks_ctx *ctx)` · [lib/socks.c:L1167-L1175][f1]

Releases a socks_ctx: unlinks the destination peer and credentials references, frees the buffer queue, and frees the context itself; a NULL pointer is ignored.

<a id="u-ff075b1104f4"></a>
### `socks_cf_adjust_pollset`

`static CURLcode socks_cf_adjust_pollset(struct Curl_cfilter *cf, struct Curl_easy *da…` · [lib/socks.c:L1249-L1275][f1]

Pollset callback for the unconnected SOCKS filter: it waits on the socket below, requesting output-only for the send states (SOCKS4_ST_SEND, SOCKS5_ST_REQ0_SEND, SOCKS5_ST_AUTH_SEND, SOCKS5_ST_REQ1_SEND) and input-only in all other states (including all receive and resolve waits).

A connected filter or missing ctx leaves the pollset untouched and returns CURLE_OK.

<a id="u-f0e8da5a566d"></a>
### `socks_cf_query`

`static CURLcode socks_cf_query(struct Curl_cfilter *cf, struct Curl_easy *data, int q…` · [lib/socks.c:L1285-L1311][f1]

Filter query callback: CF_QUERY_HOST_PORT returns the destination hostname and port from the context when present; CF_QUERY_ALPN_NEGOTIATED always reports no ALPN.

Unhandled queries (and HOST_PORT with no context) forward to the next filter's query, or return CURLE_UNKNOWN_OPTION when there is none.

<a id="u-2f1d6ec32093"></a>
### `socks.c module code (L1–L46)`

`module_region` · [lib/socks.c:L1-L46][f1]

File header, feature gate (CURL_DISABLE_PROXY), and includes for the SOCKS proxy connection filter implementation.

<a id="u-65b9c0810b4c"></a>
### `socks.c module code (L1012–L1017)`

`module_region` · [lib/socks.c:L1012-L1017][f1]

Blank separator between socks5_recv_resp1 and the socks5_connect state machine.

<a id="u-30363ce1f149"></a>
### `socks.c module code (L1175–L1181)`

`module_region` · [lib/socks.c:L1175-L1181][f1]

Comment preceding socks_proxy_cf_connect describing the resume-until-done contract and that sub-functions report errors via failf.

<a id="u-f9b3f34d1a36"></a>
### `socks.c module code (L1311–L1329)`

`module_region` · [lib/socks.c:L1311-L1329][f1]

Definition of Curl_cft_socks_proxy: the filter type table named "SOCKS" with IP_CONNECT and PROXY flags, wiring the socks-specific destroy, connect, adjust_pollset, and query callbacks and the default send/recv/shutdown/data-pending/cntrl/keep-alive implementations.

<a id="u-9f33173998b6"></a>
### `socks.c module code (L1390–L1392)`

`module_region` · [lib/socks.c:L1390-L1392][f1]

Closing #endif for the CURL_DISABLE_PROXY conditional wrapping the file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/socks.c
