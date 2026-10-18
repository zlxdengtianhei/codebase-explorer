# QUIC Packet Ingress/Egress

**Capability.** Moves QUIC packets between ngtcp2 and UDP: reading and feeding received datagrams, collecting and sending packets (with GSO sizing), producing one packet per call via a bufq provider, and maintaining per-call io contexts with timestamp snapshots.

Use this subtree to follow how datagrams flow in and out of the QUIC connection and how time is threaded into ngtcp2 for each I/O call.

Parent: [QUIC via ngtcp2](r8-quic-ngtcp2.md)

## Units (6)

<a id="u-902c04ea16f7"></a>
### `Curl_cf_ngtcp2_progress_ingress`

`CURLcode Curl_cf_ngtcp2_progress_ingress(struct Curl_cfilter *cf, struct Curl_easy *d…` · [lib/vquic/cf-ngtcp2-cmn.c:L1712-L1800][f1]

Reads and processes incoming QUIC packets, from a direct UDP socket or a tunnel.

Prepares the io context if none given, then runs Curl_vquic_tls_before_recv (errors propagate). Direct socket: delegates to Curl_vquic_recv_packets with a 1000-datagram limit and cf_ngtcp2_recv_pkts as consumer. Tunneled QUIC: grows ctx->tunnel_inbuf to at least max(negotiated path max payload, QUIC_TUNNEL_INBUF_SIZE) — realloc failure returns CURLE_OUT_OF_MEMORY — then loops up to QUIC_TUNNEL_INGRESS_PKT_LIMIT times reading via Curl_conn_cf_recv from the next filter: CURLE_AGAIN and zero bytes both end ingress with CURLE_OK (the latter as tunnel closed), other read errors propagate. Each chunk is dispatched with the connected remote address; success marks got_first_byte/first_byte_at on first data and updates last_io.

calls: [cf_ngtcp2_recv_pkts](r8-ngtcp2-packet-io.md#u-ab5927e69667)

<a id="u-9fa8adcac351"></a>
### `Curl_cf_ngtcp2_progress_egress`

`CURLcode Curl_cf_ngtcp2_progress_egress(struct Curl_cfilter *cf, struct Curl_easy *da…` · [lib/vquic/cf-ngtcp2-cmn.c:L1549-L1657][f1]

Collects QUIC packets from ngtcp2 and sends them over UDP, honoring GSO sizing.

Creates or refreshes the io context and zeroes the path storage. First flushes pending data; CURLE_AGAIN schedules a 1ms retry via Curl_expire_set and reports success, other errors propagate. Reads max/path payload sizes and the send quantum, then repeatedly sips a packet into the sendbuf (CURLE_AGAIN ends the loop, other errors abort). The buffered packet count drives GSO splitting: the first packet's size becomes gsolen; when a later packet is larger than gsolen, or previous packets were larger than path_max_payload and sizes now differ, it sends via Curl_vquic_send_tail_split (CURLE_AGAIN retries later as OK); when a packet is smaller than gsolen the loop breaks to flush before the size change. Finally, any buffered bytes are sent with Curl_vquic_send and gsolen — again CURLE_AGAIN becomes a scheduled retry, other errors propagate — and on success packet tx time is updated in ngtcp2.

**Uncertainties.**

- The exact GSO tail-split semantics of Curl_vquic_send_tail_split are external to this file.

<a id="u-ab5927e69667"></a>
### `cf_ngtcp2_recv_pkts`

`static CURLcode cf_ngtcp2_recv_pkts(const unsigned char *buf, size_t buflen, size_t g…` · [lib/vquic/cf-ngtcp2-cmn.c:L1664-L1710][f1]

Callback feeding received UDP datagrams into ngtcp2.

On the first datagram of a batch it refreshes the io clock and zeroes the path. Builds the ngtcp2 path from the local address and the supplied remote address, sets ECN info, then iterates the buffer in gso_size steps (clamping the final chunk), calling ngtcp2_conn_read_pkt per packet and counting them. On read failure it traces, records the error via Curl_cf_ngtcp2_cmn_err_set, and maps NGTCP2_ERR_CRYPTO to CURLE_PEER_FAILED_VERIFICATION (comment: failed certificate verification is a common cause), otherwise CURLE_RECV_ERROR.

calls: [Curl_cf_ngtcp2_cmn_err_set](r8-ngtcp2-errors-tls.md#u-5cbaff237170)

<a id="u-ba24a8871b80"></a>
### `read_pkt_to_send`

`static CURLcode read_pkt_to_send(void *userp, unsigned char *buf, size_t buflen, size…` · [lib/vquic/cf-ngtcp2-cmn.c:L1448-L1547][f1]

Bufq provider producing one UDP packet from ngtcp2/nghttp3.

Loops assembling frames: when an h3conn exists and connection flow credit remains, it collects stream data vectors via nghttp3_conn_writev_stream (error: failf, Curl_cf_ngtcp2_h3_err_set, CURLE_SEND_ERROR), then writes a stream-capable packet with ngtcp2_conn_writev_stream using NGTCP2_WRITE_STREAM_FLAG_MORE. n == 0 returns CURLE_AGAIN (nothing to send); negative returns are handled by case: STREAM_DATA_BLOCKED blocks the stream in nghttp3, marks the local stream quic_flow_blocked when it is one of ours, and continues; STREAM_SHUT_WR shuts the stream's write side and continues; WRITE_MORE continues to let ngtcp2 add another frame; any other error fails via Curl_cf_ngtcp2_cmn_err_set and CURLE_SEND_ERROR. Whenever ndatalen >= 0 the data-byte count is added to the nghttp3 write offset (error: CURLE_SEND_ERROR). When n > 0 the packet is complete and its size is returned via *pnread.

calls: [Curl_cf_ngtcp2_h3_err_set](r8-ngtcp2-errors-tls.md#u-4424220abf66), [Curl_cf_ngtcp2_cmn_err_set](r8-ngtcp2-errors-tls.md#u-5cbaff237170); uses: [cf_ngtcp2_get_stream](r8-ngtcp2-h3-streams.md#u-77142353ba06)

<a id="u-94416fc60ede"></a>
### `Curl_cf_ngtcp2_io_ctx_init`

`void Curl_cf_ngtcp2_io_ctx_init(struct cf_ngtcp2_io_ctx *io_ctx, struct Curl_cfilter …` · [lib/vquic/cf-ngtcp2-cmn.c:L1380-L1393][f1]

Prepares a per-call packet io context: stores cf and data, snapshots the current time via Curl_pgrs_now, zeroes the ngtcp2 path storage, pushes the time into the vquic ctx via Curl_vquic_ctx_set_time, and converts the timeval to an ngtcp2 microsecond timestamp.

<a id="u-8e32d2394ca7"></a>
### `Curl_cf_ngtcp2_io_ctx_update_time`

`void Curl_cf_ngtcp2_io_ctx_update_time(struct Curl_easy *data, struct cf_ngtcp2_io_ct…` · [lib/vquic/cf-ngtcp2-cmn.c:L1395-L1405][f1]

Refreshes an existing io context's clock: re-reads the current time, updates the vquic ctx time, and recomputes the ngtcp2 timestamp; unlike the init variant it does not touch the path storage.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-ngtcp2-cmn.c
