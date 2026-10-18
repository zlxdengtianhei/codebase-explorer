# QUIC datagram capsule filter

**Capability.** Connection-filter implementation encapsulating outgoing data as RFC 9297 HTTP Datagram capsules over UDP and decapsulating incoming ones, with bufq flushing, pollset adjustment, and filter lifecycle.

Read when touching proxy tunneling of datagrams. capsule.h declares the codec interface; cf-capsule.c implements the filter callbacks that drain the send bufq through the next filter.

Parent: [Protocol engines](r12-protocol-engines.md)

## Units (11)

<a id="u-f4c17f4eea52"></a>
### `capsule-h`

`module_region` · [lib/vquic/capsule.h:L1-L70][f1]

Declares the HTTP Datagram capsule (RFC 9297) codec interface, compiled only when proxy and HTTP are enabled.

`Curl_capsule_encap_udp_datagram` wraps a UDP payload into a capsule written to a bufq, returning CURLE_OK or an error. `Curl_capsule_process_udp_raw` decodes one capsule from a receive bufq into a caller buffer, returning payload byte count and setting `err`; the header comment says to check `err` for status, implying a zero return can accompany an error or a need for more data. `HTTP_CAPSULE_HEADER_MAX_SIZE` (10) bounds the capsule header size. Function bodies are not in this header; behavior beyond the documented contracts is unproven.

**Uncertainties.**

- Actual encode/decode implementations live elsewhere; return-value semantics of the process function beyond the doc comment (e.g. partial reads, zero-byte results) cannot be verified from this header.

<a id="u-f3700643acd7"></a>
### `cf-capsule-ctx-and-lifecycle`

`struct cf_capsule_ctx` · [lib/vquic/cf-capsule.c:L41-L44][f2]

Per-filter state and lifecycle for the CAPSULE connect filter.

cf_capsule_ctx holds two bufqs: recvbuf for decapsulated ingress and sendbuf for encapsulated egress, sized 4 x 16KB each (CAPSULE_CHUNK_SIZE/SEND/RECV_CHUNKS) with BUFQ_OPT_SOFT_LIMIT. cf_capsule_create allocates the ctx with curlx_calloc (out of memory -> CURLE_OUT_OF_MEMORY), initializes both bufqs, and creates the filter via Curl_cf_create with Curl_cft_capsule; on failure it frees both bufqs and the ctx and sets *pcf to NULL. cf_capsule_destroy frees both bufqs and the ctx. Curl_cf_capsule_insert_after creates the filter and, on success, inserts it after cf_at via Curl_conn_cf_insert_after. Curl_cft_capsule wires these callbacks; is_alive/keep_alive use the defaults.

calls: [bufq-c-init-free](r15-bufq-chunk-engine.md#u-1d395f59b0bc), [Curl_cf_create](r8-cfilters-chain-mgmt.md#u-e3a618a4a2af), [lib-cfilters-c-chain-management](r8-cfilters-chain-mgmt.md#u-f10f9ecb03f8)

**Uncertainties.**

- Curl_cft_capsule lists Curl_cf_def_conn_is_alive/Curl_cf_def_conn_keep_alive; their behavior lives outside this file

<a id="u-62687a8b0b9f"></a>
### `cf_capsule_adjust_pollset`

`static CURLcode cf_capsule_adjust_pollset(struct Curl_cfilter *cf, struct Curl_easy *…` · [lib/vquic/cf-capsule.c:L212-L224][f2]

Pollset adjustment: when the send bufq is non-empty the filter's socket is fetched and, if valid, added for output writability so flushing can proceed; otherwise the pollset is left unchanged.

calls: [lib-cfilters-c-socket-address](r8-cfilters-events-state.md#u-e5810b18a0c1), [Curl_bufq_is_empty](r15-bufq-stream-api.md#u-972cf7343ce0)

<a id="u-462d8206f9e7"></a>
### `cf_capsule_cntrl`

`static CURLcode cf_capsule_cntrl(struct Curl_cfilter *cf, struct Curl_easy *data, int…` · [lib/vquic/cf-capsule.c:L171-L187][f2]

Filter control callback.

Only CF_CTRL_FLUSH is handled, by flushing the send buffer; all other events return CURLE_OK with no action.

calls: [cf_capsule_flush](r12-quic-capsule-filter.md#u-fb5f455d6037)

<a id="u-66997feeabd8"></a>
### `cf_capsule_connect`

`static CURLcode cf_capsule_connect(struct Curl_cfilter *cf, struct Curl_easy *data, b…` · [lib/vquic/cf-capsule.c:L58-L74][f2]

Connect step for the CAPSULE filter.

If already connected, reports done with CURLE_OK. Otherwise delegates to the next filter's do_connect; on success with done set it marks this filter connected. With no next filter it reports not done and CURLE_OK.

<a id="u-75aeda8ed353"></a>
### `cf_capsule_data_pending`

`static bool cf_capsule_data_pending(struct Curl_cfilter *cf, const struct Curl_easy *…` · [lib/vquic/cf-capsule.c:L161-L169][f2]

Reports whether buffered data remains.

Returns TRUE if its recvbuf is non-empty; otherwise delegates to the next filter's has_data_pending, or FALSE if there is no next filter.

calls: [Curl_bufq_is_empty](r15-bufq-stream-api.md#u-972cf7343ce0)

<a id="u-fb5f455d6037"></a>
### `cf_capsule_flush`

`static CURLcode cf_capsule_flush(struct Curl_cfilter *cf, struct Curl_easy *data)` · [lib/vquic/cf-capsule.c:L76-L96][f2]

Drains the send bufq through the next filter.

An empty buffer returns CURLE_OK immediately. Curl_cf_send_bufq sends the buffered data; any error propagates (CURLE_AGAIN traced with leftover length). On success returns CURLE_OK only if the buffer is empty, else CURLE_AGAIN for the remaining data.

calls: [lib-cfilters-c-bufq-io](r8-cfilters-io.md#u-90abeb80795a), [Curl_bufq_is_empty](r15-bufq-stream-api.md#u-972cf7343ce0)

<a id="u-c047ee619798"></a>
### `cf_capsule_query`

`static CURLcode cf_capsule_query(struct Curl_cfilter *cf, struct Curl_easy *data, int…` · [lib/vquic/cf-capsule.c:L189-L210][f2]

Filter query callback.

CF_QUERY_NEED_FLUSH answers TRUE (via *pres1) when the send bufq is non-empty, then falls through to the next filter's query unless answered; other queries are forwarded to the next filter, or CURLE_UNKNOWN_OPTION when there is none. Note the sendbuf non-empty case still forwards to cf->next afterwards, since it only breaks the switch, not the forwarding path.

calls: [Curl_bufq_is_empty](r15-bufq-stream-api.md#u-972cf7343ce0)

**Uncertainties.**

- Whether CF_QUERY_NEED_FLUSH reaching the next filter after setting *pres1=TRUE is intended is not visible in this file

<a id="u-b44f3f544669"></a>
### `cf_capsule_recv`

`static CURLcode cf_capsule_recv(struct Curl_cfilter *cf, struct Curl_easy *data, char…` · [lib/vquic/cf-capsule.c:L132-L159][f2]

Reads one decapsulated UDP datagram.

It first refills its recvbuf from the next filter via Curl_cf_recv_bufq in a loop until the buffer is full, CURLE_AGAIN arrives, or a read returns zero bytes; non-AGAIN errors propagate immediately. It then extracts one capsule with Curl_capsule_process_udp_raw, returning its byte count in *pnread and its error code directly.

calls: [lib-cfilters-c-bufq-io](r8-cfilters-io.md#u-90abeb80795a), [Curl_capsule_process_udp_raw](r8-http-datagram-capsules.md#u-7cd3440e2d5a)

<a id="u-d9f02175ab51"></a>
### `cf_capsule_send`

`static CURLcode cf_capsule_send(struct Curl_cfilter *cf, struct Curl_easy *data, cons…` · [lib/vquic/cf-capsule.c:L98-L130][f2]

Encapsulates outgoing data as a UDP datagram capsule.

If the send bufq is full it first flushes; a flush error aborts. Then Curl_capsule_encap_udp_datagram buffers header+payload; an error aborts. A following flush returning CURLE_AGAIN is downgraded to CURLE_OK because the payload is now buffered and will be flushed later; other flush errors propagate. On success *pnwritten is set to the full len, even if part remains buffered.

calls: [Curl_capsule_encap_udp_datagram](r8-http-datagram-capsules.md#u-3d10c43d5bf7), [cf_capsule_flush](r12-quic-capsule-filter.md#u-fb5f455d6037), [Curl_bufq_is_full](r15-bufq-stream-api.md#u-d0e22f7ff218)

<a id="u-e23e99a62bf5"></a>
### `cf_capsule_shutdown`

`static CURLcode cf_capsule_shutdown(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/vquic/cf-capsule.c:L226-L241][f2]

Shutdown: if not connected or already shutting down, reports done with CURLE_OK.

Otherwise flushes the send buffer; done is TRUE when the flush succeeds, CURLE_AGAIN is downgraded to CURLE_OK (with done FALSE so shutdown retried later), and other flush errors propagate.

calls: [cf_capsule_flush](r12-quic-capsule-filter.md#u-fb5f455d6037)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/capsule.h
[f2]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-capsule.c
