# HAProxy PROXY Filter

**Capability.** A connection filter that emits the PROXY protocol header: a three-phase state (INIT/SEND/DONE), context holding the unsent dynbuf, filter creation/insertion into the chain, connect driving, pollset adjustment, and teardown.

Read cf_haproxy_create and the vtable region to see the filter contract; cf_haproxy_connect resumes the partial send across calls. Insert_after is how callers splice this filter into an existing chain.

**Depends on.**

- [Polling and Pollsets](r5-poll-waiting.md) · graph-confirmed · 1 edge(s)

Parent: [Protocol and Filter Implementations](r5-protocol-implementations.md)

## Units (14)

<a id="u-e1c48496acdc"></a>
### `lib/cf-haproxy.c:<enum>`

`enum` · [lib/cf-haproxy.c:L37-L41][f1]

Filter state machine values: HAPROXY_INIT (no header built), HAPROXY_SEND (header partially sent), HAPROXY_DONE (all work complete).

<a id="u-d393f41ba7db"></a>
### `Curl_cf_haproxy_insert_after`

`CURLcode Curl_cf_haproxy_insert_after(struct Curl_cfilter *cf_at, struct Curl_easy *d…` · [lib/cf-haproxy.c:L226-L239][f1]

Creates an HAProxy filter and splices it into the filter chain immediately after cf_at.

A create error aborts before insertion and is returned; on success the chain takes ownership via Curl_conn_cf_insert_after and OK is returned.

calls: [lib-cfilters-c-chain-management](r8-cfilters-chain-mgmt.md#u-f10f9ecb03f8), [cf_haproxy_create](r5-haproxy-filter.md#u-93a8544e95a7)

<a id="u-8f2af5dc8c31"></a>
### `cf_haproxy_adjust_pollset`

`static CURLcode cf_haproxy_adjust_pollset(struct Curl_cfilter *cf, struct Curl_easy *…` · [lib/cf-haproxy.c:L169-L180][f1]

Updates the poll interest while the handshake is pending.

Only when the next filter is connected and this filter is not yet connected does it set the pollset to out-only interest on this filter's socket; in every other state it leaves the pollset unchanged and returns OK.

calls: [lib-cfilters-c-socket-address](r8-cfilters-events-state.md#u-e5810b18a0c1)

<a id="u-509297d6edd4"></a>
### `cf_haproxy_connect`

`static CURLcode cf_haproxy_connect(struct Curl_cfilter *cf, struct Curl_easy *data, b…` · [lib/cf-haproxy.c:L105-L160][f1]

Drives the HAProxy handshake: waits for the next filter to connect, then sends one PROXY header line, resuming across calls.

If cf->connected is already set it returns OK with *done TRUE. It calls the next filter's do_connect and returns immediately on error or while *done is FALSE. In HAPROXY_INIT it builds the header (error propagates via goto out) and advances to HAPROXY_SEND. In HAPROXY_SEND it sends the buffered bytes via Curl_conn_cf_send: any non-CURLE_AGAIN error jumps to out; CURLE_AGAIN is converted to OK with zero written. Sent bytes are trimmed with curlx_dyn_tail; if data remains it returns OK with the handshake unfinished. Once drained, the state becomes HAPROXY_DONE and the dynbuf is freed (also on the default fallthrough). At out, *done is (no error AND state==HAPROXY_DONE), cf->connected mirrors *done, and the result is returned. State and buffer persist in ctx, so a partially sent header resumes on the next invocation.

**Notes.**

- side_effect: ctx->state and the residual dynbuf persist between calls until HAPROXY_DONE frees the buffer.
- failure: CURLE_AGAIN during send is swallowed and retried on the next call; any other error propagates with *done FALSE.

calls: [lib-cfilters-c-dispatch-wrappers](r8-cfilters-io.md#u-4223d3ac73f1), [curlx_dyn_tail](r3-dynbuf.md#u-3a3e5b30ff85); uses: [cf-haproxy.c module code (L54–L104)](r5-haproxy-filter.md#u-512c8c393ca7)

**Uncertainties.**

- Whether the next filter's do_connect can be re-entered after a partial HAProxy send is not settled by this code alone.

<a id="u-93a8544e95a7"></a>
### `cf_haproxy_create`

`static CURLcode cf_haproxy_create(struct Curl_cfilter **pcf, struct Curl_easy *data)` · [lib/cf-haproxy.c:L199-L224][f1]

Allocates an HAProxy filter with a fresh context.

calloc failure yields CURLE_OUT_OF_MEMORY with *pcf NULL. The context starts in HAPROXY_INIT with a dynbuf capped at DYN_HAXPROXY. Curl_cf_create attaches the context to the filter; on success ctx is nulled so the cleanup path frees nothing, on failure the context is freed. *pcf is NULL whenever result is nonzero.

calls: [Curl_cf_create](r8-cfilters-chain-mgmt.md#u-e3a618a4a2af), [cf_haproxy_ctx_free](r5-haproxy-filter.md#u-73b264e835ef)

<a id="u-73b264e835ef"></a>
### `cf_haproxy_ctx_free`

`static void cf_haproxy_ctx_free(struct cf_haproxy_ctx *ctx)` · [lib/cf-haproxy.c:L48-L54][f1]

Releases an HAProxy filter context: frees the dynbuf and the context allocation itself.

A NULL context is accepted and ignored.

calls: [curlx_dyn_free](r3-dynbuf.md#u-21f694d1bd8a)

<a id="u-4a9cef46f5d4"></a>
### `cf_haproxy_destroy`

`static void cf_haproxy_destroy(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/cf-haproxy.c:L162-L167][f1]

Tears down the filter: logs a destroy trace and frees the filter's context.

uses: [lib/curl_trc.c:Curl_trc_cf_infof](r1-trace-logging.md#u-2262abad19b2)

<a id="u-3f974a8cca2f"></a>
### `cf-haproxy.c module code (L1–L37)`

`module_region` · [lib/cf-haproxy.c:L1-L37][f1]

HAProxy PROXY protocol connection filter: header includes and the compile guard excluding this file when proxy support is disabled.

<a id="u-e12812a24fae"></a>
### `cf-haproxy.c module code (L41–L42)`

`module_region` · [lib/cf-haproxy.c:L41-L42][f1]

Trailing region closing the enum declaration.

<a id="u-5610916de7a9"></a>
### `cf-haproxy.c module code (L46–L47)`

`module_region` · [lib/cf-haproxy.c:L46-L47][f1]

Trailing region after the context struct definition.

<a id="u-512c8c393ca7"></a>
### `cf-haproxy.c module code (L54–L104)`

`module_region` · [lib/cf-haproxy.c:L54-L104][f1]

Region containing cf_haproxy_date_out_set and the Curl_cft_haproxy vtable.

cf_haproxy_date_out_set builds the v1 PROXY header into ctx->data_out. Under USE_UNIX_SOCKETS, when the connection's first peer is a unix socket it appends the literal 'PROXY UNKNOWN\r\n'; otherwise it obtains the connection's IP quadruple and ipv6 flag via Curl_conn_cf_get_ip_info (propagating its error), then overrides both addresses with the user-set STRING_HAPROXY_CLIENT_IP if present (deriving the protocol from Curl_is_ipv4addr on that string, so a non-IPv4 user string yields TCP6), else uses the quadruple's local/remote IPs. It formats 'PROXY TCP4|TCP6 <src> <dst> <lport> <rport>\r\n' via curlx_dyn_addf and returns that result. Curl_cft_haproxy wires this filter's name, PROXY|SETUP flags, and its connect/destroy/adjust_pollset implementations, delegating shutdown, data_pending, send, recv, cntrl, liveness, keepalive, and query to the generic defaults.

calls: [lib-cfilters-c-transport-mapping](r8-cfilters-events-state.md#u-9a6bc0bfdce5), [Curl_is_ipv4addr](r5-addrinfo-core.md#u-92b66e543229)

**Uncertainties.**

- Whether a user-supplied client IP that is a hostname should map to TCP6 is decided solely by Curl_is_ipv4addr; its semantics live elsewhere.

<a id="u-0da4000c0829"></a>
### `cf-haproxy.c module code (L180–L198)`

`module_region` · [lib/cf-haproxy.c:L180-L198][f1]

Region between the pollset adjuster and the create function.

<a id="u-82d2a884c3b1"></a>
### `cf-haproxy.c module code (L239–L241)`

`module_region` · [lib/cf-haproxy.c:L239-L241][f1]

Closing #endif for the CURL_DISABLE_PROXY guard.

<a id="u-e6ffed4badc7"></a>
### `cf_haproxy_ctx`

`struct cf_haproxy_ctx` · [lib/cf-haproxy.c:L43-L46][f1]

Filter context: an int state selecting the haproxy_state machine phase and a dynbuf data_out holding the not-yet-sent PROXY header bytes.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cf-haproxy.c
