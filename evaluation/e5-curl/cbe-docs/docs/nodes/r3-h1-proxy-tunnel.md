# HTTP/1 CONNECT Proxy Filter

**Capability.** Implements the 'H1-PROXY' connection filter: tunnel state and context types, filter-type registration and lifecycle callbacks, and the CONNECT send/receive/response-parsing state machine that tunnels other protocols through an HTTP/1 proxy.

Read this subtree to follow a CONNECT tunnel from init through request send, response parse, and state transitions. Filter callbacks (connect, destroy, adjust_pollset, query, data_pending) integrate the tunnel into the filter chain.

**Depends on.**

- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-confirmed · 21 edge(s)
- [Peer Identity & Refcounting](r3-peer-identity.md) · graph-confirmed · 5 edge(s)
- [Trace and Debug Logging](r1-trace-logging.md) · graph-only · 45 edge(s)

Parent: [Connection & Proxy Infrastructure](r3-connection-infra.md)

## Units (17)

<a id="u-6f3152838942"></a>
### `cf-h1-proxy-c-tunnel-state-and-context`

`enum` · [lib/cf-h1-proxy.c:L46-L53][f1]

Module-level data types for the HTTP/1 CONNECT proxy filter: the tunnel state enum, the per-tunnel state struct, and the filter's persistent context.

h1_tunnel_state holds peer references, receive and request dynbufs, send offset, header count, a chunked-body parser, HTTP version, a keepon selector (KEEPON_DONE/KEEPON_CONNECT/KEEPON_IGNORE) driving the receive loop, remaining content length, tunnel state, and flags for chunked encoding, connection close, header folding, and UDP tunneling. cf_h1_proxy_ctx stores the proxy peer and points at the active tunnel state.

<a id="u-559d5a78cc5e"></a>
### `cf-h1-proxy-c-small-helpers`

`static bool tunnel_is_established(struct h1_tunnel_state *ts)` · [lib/cf-h1-proxy.c:L84-L87][f1]

Small predicate and lifecycle helpers of the H1 proxy filter.

tunnel_is_established and tunnel_is_failed test the tunnel state, returning false for NULL. h1_proxy_is_udp reads the udp_tunnel flag from the filter context and assumes pctx exists. tunnel_reinit resets both dynbufs, moves to H1_TUNNEL_INIT with keepon KEEPON_CONNECT, and clears length, close, folding, chunked, send-offset, and header-count fields. tunnel_free unlinks the peer, frees both dynbufs and the chunker, and frees the state; it tolerates NULL. cf_tunnel_free transitions any existing tunnel state to H1_TUNNEL_FAILED, frees it, and NULLs the context pointer; it tolerates NULL filter/context. tunnel_want_send is true only in H1_TUNNEL_CONNECT.

<a id="u-905feaadb62e"></a>
### `tunnel_init`

`static CURLcode tunnel_init(struct Curl_cfilter *cf, struct Curl_easy *data, struct h…` · [lib/cf-h1-proxy.c:L121-L144][f1]

Allocates and initializes a fresh tunnel state, rejecting protocols that cannot be proxied over CONNECT.

If the connection scheme has PROTOPT_NOTCPPROXY it failf-logs and returns CURLE_UNSUPPORTED_PROTOCOL. It callocs the state (CURLE_OUT_OF_MEMORY on failure), initializes the receive buffer with the proxy-connect-header limit and the request buffer with the HTTP-request limit, initializes the chunk parser, stores the state via *pts, and delegates field reset to tunnel_reinit.

calls: [cf-h1-proxy-c-small-helpers](r3-h1-proxy-tunnel.md#u-559d5a78cc5e)

**Uncertainties.**

- Curl_httpchunk_init's failure behavior is not visible; its return is ignored here.

<a id="u-569f23ab5f41"></a>
### `h1_tunnel_go_state`

`static void h1_tunnel_go_state(struct Curl_cfilter *cf, struct h1_tunnel_state *ts, h…` · [lib/cf-h1-proxy.c:L146-L200][f1]

Transitions the tunnel to a new state; a no-op when already in that state.

Entering H1_TUNNEL_INIT reinitializes everything via tunnel_reinit. H1_TUNNEL_CONNECT sets keepon KEEPON_CONNECT and clears the receive buffer; H1_TUNNEL_RECEIVE and H1_TUNNEL_RESPONSE only set the state. H1_TUNNEL_ESTABLISHED logs completion, sets data->state.authproxy.done and clears multipass, then falls through into the tail shared with H1_TUNNEL_FAILED: both dynbufs reset, data->info.httpcode cleared, and data->req.hd_proxy_auth freed so proxy credentials cannot leak into the document request.

calls: [cf-h1-proxy-c-small-helpers](r3-h1-proxy-tunnel.md#u-559d5a78cc5e)

<a id="u-eb74a0387435"></a>
### `start_CONNECT`

`static CURLcode start_CONNECT(struct Curl_cfilter *cf, struct Curl_easy *data, struct…` · [lib/cf-h1-proxy.c:L233-L269][f1]

Builds the CONNECT request bytes for the tunnel.

It first frees a stale data->req.newurl from prior auth loops, then has Curl_http_proxy_create_tunnel_request build the request (proxy peer, destination peer, HTTP/1 version, UDP flag); any error aborts. It resets the request buffer, zeroes nsent and headerlines, derives the minor version from ts->httpversion % 10, serializes the head with Curl_h1_req_write_head, and on success switches the client reader to null via Curl_creader_set_null. On failure it failf-logs 'Failed sending CONNECT'; the request object is always freed.

uses: [send_CONNECT](r3-h1-proxy-tunnel.md#u-e8c2d61b5df1)

<a id="u-e8c2d61b5df1"></a>
### `send_CONNECT`

`static CURLcode send_CONNECT(struct Curl_cfilter *cf, struct Curl_easy *data, struct …` · [lib/cf-h1-proxy.c:L271-L304][f1]

Sends the buffered CONNECT request through the next filter until fully written.

If ts->nsent already covers the request it finishes immediately. Otherwise the unsent tail goes to cf->next's do_send: CURLE_AGAIN is downgraded to CURLE_OK for a later retry; other errors abort. On success nsent advances and the written bytes are emitted via Curl_debug as CURLINFO_HEADER_OUT. *done is true only when nsent reaches the full request length; any error triggers a failf log.

uses: [start_CONNECT](r3-h1-proxy-tunnel.md#u-eb74a0387435)

<a id="u-afd4d145fc28"></a>
### `on_resp_status`

`static CURLcode on_resp_status(struct Curl_cfilter *cf, struct Curl_easy *data, struc…` · [lib/cf-h1-proxy.c:L306-L328][f1]

Parses the first status line of the CONNECT response.

It accepts only lines matching 'HTTP/1.0 ' or 'HTTP/1.1 ' followed by exactly three digits (a non-digit must follow), computes the three-digit code, and stores it in both data->info.httpproxycode and k->httpcode, logging it with a -UDP suffix for UDP tunnels. Any other shape failf-logs 'Invalid response header' and returns CURLE_WEIRD_SERVER_REPLY.

<a id="u-ff1564c7a40d"></a>
### `on_resp_header`

`static CURLcode on_resp_header(struct Curl_cfilter *cf, struct Curl_easy *data, struc…` · [lib/cf-h1-proxy.c:L330-L419][f1]

Interprets one response header line from the proxy, dispatching on prefix and current status code.

Proxy-authenticate: on a 407 is copied (CURLE_OUT_OF_MEMORY if the copy fails) and fed to Curl_http_input_auth, propagating its error. Content-Length: and Transfer-Encoding: are rejected with CURLE_WEIRD_SERVER_REPLY on 1xx statuses, which cannot carry a body; on 2xx they are ignored per RFC 7231; on 3xx+ Content-Length parses into ts->cl (a bad value is WEIRD_SERVER_REPLY) and Transfer-Encoding: chunked sets ts->chunked_encoding and resets the chunker. Connection: close and Proxy-Connection: close both set ts->close_connection. Capsule-protocol: is inspected only for UDP tunnels, logging ?1 without state change. Other headers are ignored; CURLE_OK is returned.

uses: [cf-h1-proxy-c-small-helpers](r3-h1-proxy-tunnel.md#u-559d5a78cc5e)

<a id="u-8c43b30ea8c9"></a>
### `single_header`

`static CURLcode single_header(struct Curl_cfilter *cf, struct Curl_easy *data, struct…` · [lib/cf-h1-proxy.c:L421-L500][f1]

Processes one fully buffered header line of the CONNECT response.

It counts the line, emits it as CURLINFO_HEADER_IN debug data, validates it with Curl_verify_header, delivers it to the client callback with HEADER|CONNECT flags (plus STATUS for line 1), and accounts for it via Curl_bump_headersize; any of these can abort with its error. When the buffered line starts with a newline it is the end of headers: on line 1 keepon becomes KEEPON_DONE with CURLE_WEIRD_SERVER_REPLY; on a 407 without an auth problem keepon becomes KEEPON_IGNORE to discard the body, unless there is neither content-length nor chunked encoding, in which case keepon becomes KEEPON_DONE; otherwise KEEPON_DONE. A normal line is parsed by on_resp_status (line 1) or on_resp_header, and the receive buffer is reset only on success.

calls: [on_resp_status](r3-h1-proxy-tunnel.md#u-afd4d145fc28), [on_resp_header](r3-h1-proxy-tunnel.md#u-ff1564c7a40d)

<a id="u-9a25b704d362"></a>
### `recv_CONNECT_resp`

`static CURLcode recv_CONNECT_resp(struct Curl_cfilter *cf, struct Curl_easy *data, st…` · [lib/cf-h1-proxy.c:L502-L649][f1]

Reads the CONNECT response one byte at a time via Curl_conn_recv to avoid buffering races.

CURLE_AGAIN returns CURLE_OK with *done false so the caller retries; a read error ends the loop with keepon KEEPON_DONE. On EOF: if a folded header was pending it is finalized; then, when proxy auth was requested and is available with a proxy auth header present, the close is treated as a mere proxy disconnect (ts->close_connection set, logged) instead of the failure path that failf-logs 'Proxy CONNECT aborted' and later maps to CURLE_RECV_ERROR. During body ignoring (KEEPON_IGNORE), chunked bodies go through Curl_httpchunk_read until done; Content-Length bodies count ts->cl down to zero. Header accumulation supports obs-fold: a blank after LF folds the line, leading blanks are replaced by a space, and buffer-overflow failures return CURLE_RECV_ERROR with 'CONNECT response too large'. Each completed LF-terminated line goes through single_header (only when the buffer starts with a newline, i.e. end of headers, in this call path). When done and the proxy status is not 2xx (excluding 101 for UDP tunnels), Curl_http_auth_act processes authentication headers and may set a follow-up URL.

calls: [single_header](r3-h1-proxy-tunnel.md#u-8c43b30ea8c9); uses: [grp:cf-h1-proxy-c-small-helpers][f1]

**Uncertainties.**

- The exact end-of-headers interaction between the LF-branch (only when line starts with newline) and single_header's own ISNEWLINE handling depends on how folded lines are buffered; both paths exist in the source.

<a id="u-130fe7617cc9"></a>
### `H1_CONNECT`

`static CURLcode H1_CONNECT(struct Curl_cfilter *cf, struct Curl_easy *data, struct h1…` · [lib/cf-h1-proxy.c:L651-L771][f1]

Drives the CONNECT tunnel state machine until established, failed, or more I/O is needed.

Already-established tunnels return CURLE_OK; failed tunnels return CURLE_RECV_ERROR so the caller rebuilds the filter chain. Each loop iteration first checks the overall time limit, mapping expiry to CURLE_OPERATION_TIMEDOUT. States progress: INIT builds the request then moves to CONNECT; CONNECT sends until done then moves to RECEIVE; RECEIVE reads until the full response is processed then moves to RESPONSE. In RESPONSE, when data->req.newurl indicates a follow-up (auth) request, a soft request reset happens, and either the filter chain must be closed and reconnected (returning CURLE_AGAIN to avoid recursion) or the tunnel state resets to INIT; the do-while loops while newurl is set. Afterward, non-2xx final statuses free newurl, transition to H1_TUNNEL_FAILED, failf-log, and return CURLE_COULDNT_CONNECT; for UDP tunnels 101 is also accepted per RFC 9298. Success transitions to H1_TUNNEL_ESTABLISHED. Any error path transitions to H1_TUNNEL_FAILED before returning.

calls: [start_CONNECT](r3-h1-proxy-tunnel.md#u-eb74a0387435), [send_CONNECT](r3-h1-proxy-tunnel.md#u-e8c2d61b5df1), [recv_CONNECT_resp](r3-h1-proxy-tunnel.md#u-9a25b704d362), [h1_tunnel_go_state](r3-h1-proxy-tunnel.md#u-569f23ab5f41)

**Uncertainties.**

- The fallthrough ordering means a failure logged in RECEIVE also enters RESPONSE handling only when result is OK and done; error propagation relies on goto out.

<a id="u-4fcf11459610"></a>
### `cf_h1_proxy_connect`

`static CURLcode cf_h1_proxy_connect(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/cf-h1-proxy.c:L773-L817][f1]

Connect filter entry point establishing the proxy tunnel.

If already connected it reports done. It first delegates to the next filter's do_connect; on error or incomplete it returns immediately. Then it lazily creates tunnel state via tunnel_init on first use, and runs H1_CONNECT. On success the stale proxy auth header is freed; *done is true only when the result is OK and the tunnel is established, in which case the filter marks itself connected, soft-resets the request, resets client write state and progress, and frees the tunnel state via cf_tunnel_free so the real request starts clean.

calls: [tunnel_init](r3-h1-proxy-tunnel.md#u-905feaadb62e), [H1_CONNECT](r3-h1-proxy-tunnel.md#u-130fe7617cc9), [cf-h1-proxy-c-small-helpers](r3-h1-proxy-tunnel.md#u-559d5a78cc5e)

<a id="u-d277556e1550"></a>
### `cf_h1_proxy_adjust_pollset`

`static CURLcode cf_h1_proxy_adjust_pollset(struct Curl_cfilter *cf, struct Curl_easy …` · [lib/cf-h1-proxy.c:L819-L849][f1]

Adjusts poll interest while the tunnel is in progress.

When the filter is not connected, it gets the underlying socket: with tunnel state present, sending phase requests write-only interest, otherwise read-only interest (waiting for the response); without tunnel state it requests write-only. When connected, the request is forwarded to the next filter's adjust_pollset, or CURLE_OK if there is none.

uses: [cf-h1-proxy-c-small-helpers](r3-h1-proxy-tunnel.md#u-559d5a78cc5e)

<a id="u-d0c4fe6d1231"></a>
### `cf_h1_proxy_data_pending`

`static bool cf_h1_proxy_data_pending(struct Curl_cfilter *cf, const struct Curl_easy …` · [lib/cf-h1-proxy.c:L851-L855][f1]

Reports pending data by delegating to the next filter's has_data_pending; returns FALSE when there is no next filter.

<a id="u-c077e50f6073"></a>
### `cf_h1_proxy_destroy`

`static void cf_h1_proxy_destroy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-h1-proxy.c:L857-L868][f1]

Destroys the filter context.

When a context exists it first frees any tunnel state through cf_tunnel_free, unlinks the peer reference, and frees the context itself.

calls: [cf-h1-proxy-c-small-helpers](r3-h1-proxy-tunnel.md#u-559d5a78cc5e)

<a id="u-3cedd152a5fe"></a>
### `cf_h1_proxy_query`

`static CURLcode cf_h1_proxy_query(struct Curl_cfilter *cf, struct Curl_easy *data, in…` · [lib/cf-h1-proxy.c:L870-L895][f1]

Answers filter queries, falling through to the next filter for anything unrecognized.

CF_QUERY_HOST_PORT returns the destination peer's port and hostname but only when tunnel state and dest exist, otherwise it also defers to the next filter (or CURLE_UNKNOWN_OPTION with none). CF_QUERY_ALPN_NEGOTIATED always answers NULL ALPN, since this filter itself negotiates none.

<a id="u-901a35be6b63"></a>
### `cf-h1-proxy-c-cftype-and-factory`

`CURLcode Curl_cf_h1_proxy_insert_after(struct Curl_cfilter *cf_at, struct Curl_easy *…` · [lib/cf-h1-proxy.c:L914-L963][f1]

The filter type table Curl_cft_h1_proxy registers the name 'H1-PROXY' with IP_CONNECT and PROXY flags, wiring cf_h1_proxy_destroy/connect/adjust_pollset/data_pending/query and default implementations for shutdown, send, recv, cntrl, and keep-alive.

Curl_cf_h1_proxy_insert_after builds a filter instance: it rejects a missing destination and HTTP versions outside [10,20) with CURLE_FAILED_INIT; allocates the tunnel state, linking the dest peer, recording udp_tunnel and httpversion, initializing both dynbufs and the chunker; allocates the context linking the proxy peer; creates the filter via Curl_cf_create, unlinking and freeing the context on that failure; otherwise inserts it after cf_at. A partially built tunnel state is freed on any exit via tunnel_free.

uses: [cf_h1_proxy_query](r3-h1-proxy-tunnel.md#u-3cedd152a5fe)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cf-h1-proxy.c
